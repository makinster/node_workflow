"""Command-line client: ``aotn run <workflow>``.

Runs a saved workflow (by id or name) or a workflow JSON file through the
backend run service, with no Textual import on its path. Errors go to stderr
as they are logged; run outputs go to stdout; the exit code says how the run
ended (see ``backend/run_service.py``).

Interactive terminals answer input and recovery requests on stdin. Otherwise
(or with ``--policy``) the run is unattended: errors follow the policy and
input requests fail their node.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, TextIO


RECOVERY_KEYS = {
    "r": "RETRY",
    "s": "SKIP",
    "b": "TERMINATE_BRANCH",
    "w": "TERMINATE_WORKFLOW",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aotn run",
        description="Run an AttackOfTheNodes workflow without the TUI.",
    )
    parser.add_argument(
        "workflow",
        help="saved workflow id or name, or a path to a workflow .json file",
    )
    parser.add_argument(
        "--data-dir",
        help="data directory (workflows, settings, secrets, logs, run records); "
        "overrides $AOTN_DATA_DIR",
    )
    parser.add_argument(
        "--policy",
        choices=["terminate_branch", "terminate_workflow"],
        help="run unattended: what happens when a node errors "
        "(default when stdin is not a terminal: terminate_workflow)",
    )
    parser.add_argument(
        "--input",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="run input for a Start input row (repeatable), typed by the row: "
        "number, true/false, JSON for var, a path for file; wins over --inputs-file",
    )
    parser.add_argument(
        "--inputs-file",
        metavar="PATH",
        help="JSON object of input values (used where --input gives none)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="start even if the validator reports errors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print the run result as JSON on stdout instead of the outputs",
    )
    return parser


def _inputs_from_file(path: Optional[str]) -> Dict[str, Any]:
    """The --inputs-file values (typed JSON); {} without the option."""
    if not path:
        return {}
    try:
        data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read --inputs-file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"--inputs-file {path} must hold a JSON object of input values")
    return data


def _parse_inputs(pairs: Sequence[str]) -> Dict[str, str]:
    inputs: Dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key.strip():
            raise ValueError(f"--input expects KEY=VALUE, got {pair!r}")
        inputs[key.strip()] = value
    return inputs


async def _readline_in_daemon_thread(stream: TextIO) -> str:
    """Read one line without blocking the loop or the process exit.

    ``asyncio.to_thread`` uses the default executor, which ``asyncio.run``
    waits for at shutdown, so a reader blocked in ``readline`` after Ctrl+C
    would hang the process. A daemon thread never holds up exit.
    """
    loop = asyncio.get_running_loop()
    future: asyncio.Future = loop.create_future()

    def read() -> None:
        try:
            line = stream.readline()
        except Exception as exc:  # pragma: no cover - passed to the waiter
            loop.call_soon_threadsafe(_settle, future, None, exc)
        else:
            loop.call_soon_threadsafe(_settle, future, line, None)

    threading.Thread(target=read, name="aotn-stdin", daemon=True).start()
    return await future


def _settle(future: asyncio.Future, value: Any, exc: Optional[BaseException]) -> None:
    if future.done():
        return
    if exc is not None:
        future.set_exception(exc)
    else:
        future.set_result(value)


def _stdin_policies(stdin: TextIO, stderr: TextIO):
    """Recovery and input answered on the terminal."""
    from backend.run_policies import (
        InputProvider,
        InputRequest,
        RecoveryPolicy,
        RecoveryRequest,
        UnattendedInputError,
    )

    # Parallel branches may ask at the same time; one prompt at a time keeps
    # each typed line going to the branch that asked for it.
    prompt_lock = asyncio.Lock()

    async def read_line(prompt: str) -> Optional[str]:
        async with prompt_lock:
            stderr.write(prompt)
            stderr.flush()
            line = await _readline_in_daemon_thread(stdin)
        if line == "":
            return None
        return line.rstrip("\r\n")

    class StdinInputProvider(InputProvider):
        async def provide(self, request: InputRequest) -> str:
            answer = await read_line(f"{request.prompt} ")
            if answer is None:
                raise UnattendedInputError("Input required but stdin is closed")
            return answer

    class StdinRecoveryPolicy(RecoveryPolicy):
        # Nothing in the CLI can resume a paused run, so breakpoints are skipped.
        pause_at_breakpoints = False

        async def decide(self, request: RecoveryRequest) -> str:
            choices = ", ".join(
                f"[{key}] {action.lower().replace('_', ' ')}"
                for key, action in RECOVERY_KEYS.items()
                if action in request.options
            )
            while True:
                answer = await read_line(f"Recover how? {choices}: ")
                if answer is None:
                    return "TERMINATE_WORKFLOW"
                action = RECOVERY_KEYS.get(answer.strip().lower()[:1])
                if action in request.options:
                    return action

    return StdinRecoveryPolicy(), StdinInputProvider()


async def _run(args: argparse.Namespace, stdin: TextIO, stdout: TextIO, stderr: TextIO) -> int:
    from backend.events import ERROR_LOGGED
    from backend.logging_setup import configure_logging
    from backend.run_policies import unattended_policies
    from backend.contracts import ContractInputError, display_value
    from backend.run_service import (
        EXIT_INTERRUPTED,
        EXIT_INVALID_INPUT,
        EXIT_INVALID_WORKFLOW,
        EXIT_NOT_FOUND,
        RunService,
        WorkflowNotFoundError,
        WorkflowValidationError,
    )

    service = RunService.create()
    if service.configuration is not None:
        configure_logging(service.configuration)

    try:
        loaded = service.load(args.workflow)
    except WorkflowNotFoundError as exc:
        stderr.write(f"aotn run: {exc}\n")
        return EXIT_NOT_FOUND

    interactive = args.policy is None and stdin.isatty()
    if interactive:
        recovery_policy, input_provider = _stdin_policies(stdin, stderr)
    else:
        recovery_policy, input_provider = unattended_policies(
            args.policy or "terminate_workflow"
        )

    def describe(node_id: Optional[str]) -> str:
        data = service.workflow_map.get_node_data(node_id or "") or {}
        alias = str(data.get("alias") or "").strip()
        return f"{alias} ({node_id})" if alias else str(node_id or "workflow")

    def print_error(payload: Dict[str, Any]) -> None:
        if payload.get("run_id") != service.current_run_id:
            return
        error = payload.get("error") or {}
        stderr.write(f"error: {describe(error.get('node_id'))}: {error.get('message')}\n")
        stderr.flush()

    service.subscribe(ERROR_LOGGED, print_error)

    interrupted = False

    def on_interrupt() -> None:
        nonlocal interrupted
        interrupted = True
        service.stop()

    loop = asyncio.get_running_loop()
    try:
        loop.add_signal_handler(signal.SIGINT, on_interrupt)
    except (NotImplementedError, RuntimeError, ValueError):
        pass  # Windows event loops: Ctrl+C ends the process instead.

    try:
        inputs = _inputs_from_file(args.inputs_file)
    except ValueError as exc:
        stderr.write(f"aotn run: {exc}\n")
        return EXIT_INVALID_INPUT
    # Fill order (C10): --input, then --inputs-file, then each row's default.
    inputs.update(_parse_inputs(args.input))

    try:
        await service.start(
            inputs=inputs,
            recovery_policy=recovery_policy,
            input_provider=input_provider,
            validate=not args.no_validate,
        )
    except ContractInputError as exc:
        stderr.write(f"aotn run: {loaded['name']} cannot start: {exc}\n")
        return EXIT_INVALID_INPUT
    except WorkflowValidationError as exc:
        stderr.write(f"aotn run: {loaded['name']} failed validation:\n")
        for error in exc.result.get("errors") or []:
            stderr.write(f"  - {describe(error.get('node_id')) if error.get('node_id') else 'workflow'}: "
                         f"{error.get('message')}\n")
        return EXIT_INVALID_WORKFLOW
    except RuntimeError as exc:
        stderr.write(f"aotn run: {loaded['name']}: {exc}\n")
        return EXIT_INVALID_WORKFLOW

    result = await service.wait()
    service.close()

    if args.json:
        stdout.write(json.dumps(result.to_dict(), indent=2, default=str) + "\n")
    else:
        for value in result.outputs:
            stdout.write(f"{_display(value)}\n")
        for name, value in result.values.items():
            stdout.write(f"{name} = {display_value(value)}\n")
    stdout.flush()
    stderr.write(
        f"aotn run: {result.workflow_name} {result.final_state.lower()}"
        f" ({_error_summary(result)}, run {result.run_id})\n"
    )
    if interrupted:
        return EXIT_INTERRUPTED
    return result.exit_code


def _error_summary(result: Any) -> str:
    total = len(result.errors)
    handled = total - len(result.unhandled_errors)
    if handled:
        return f"{total} error(s), {handled} handled"
    return f"{total} error(s)"


def _display(value: Any) -> str:
    if isinstance(value, dict) and "value" in value:
        value = value["value"]
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str)
    return str(value)


def main(
    argv: Optional[List[str]] = None,
    stdin: Optional[TextIO] = None,
    stdout: Optional[TextIO] = None,
    stderr: Optional[TextIO] = None,
) -> int:
    """Entry point for ``aotn run``; returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        _parse_inputs(args.input)
    except ValueError as exc:
        parser.error(str(exc))
    if args.data_dir:
        # Must be set before the backend is imported: data paths resolve once.
        loaded = sys.modules.get("backend.persistence")
        wanted = os.path.realpath(os.path.expanduser(args.data_dir))
        if loaded is not None and os.path.realpath(loaded.DATA_DIR) != wanted:
            parser.error("--data-dir must be set before the backend is loaded")
        os.environ["AOTN_DATA_DIR"] = wanted
    try:
        return asyncio.run(
            _run(args, stdin or sys.stdin, stdout or sys.stdout, stderr or sys.stderr)
        )
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
