"""
In-process run service for AttackOfTheNodes.

The one API every client uses to run workflows: load, validate, start (with
inputs and policies), subscribe to events, submit input or recovery, stop, and
get the result. The CLI uses it today; the future server wraps it. It never
imports a frontend module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .configuration_manager import ConfigurationManager
from .error_handler import unhandled_errors
from .event_bus import EventBus
from .events import ERROR_LOGGED
from .master_state import MasterState
from .memory_bank import MemoryBank
from .node_factory import NodeFactory
from .output_manager import OutputManager
from .persistence import list_workflows, load_workflow
from .run_policies import InputProvider, RecoveryPolicy
from .secrets_manager import SecretsManager
from .validator import validate_workflow
from .workflow_map import WorkflowMap


# Exit codes shared by every client that turns a run into a process status.
EXIT_OK = 0
EXIT_FINISHED_WITH_ERRORS = 1
EXIT_RUN_FAILED = 2
EXIT_INVALID_WORKFLOW = 3  # also: the workflow could not be started
EXIT_NOT_FOUND = 4
EXIT_USAGE = 64
EXIT_INTERRUPTED = 130


class WorkflowNotFoundError(LookupError):
    """No saved workflow or file matches the reference."""


class WorkflowLoadError(WorkflowNotFoundError):
    """A workflow was found but its data cannot be loaded."""


class WorkflowValidationError(RuntimeError):
    """The validator reported errors, so the run was not started."""

    def __init__(self, result: Dict[str, Any]) -> None:
        errors = result.get("errors") or []
        super().__init__(f"Workflow failed validation with {len(errors)} error(s)")
        self.result = result


@dataclass
class RunResult:
    """What a finished (or stopped) run produced. JSON-serializable fields."""

    run_id: Optional[str]
    workflow_id: Optional[str]
    workflow_name: str
    final_state: str
    errors: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Any] = field(default_factory=list)
    node_timings: Dict[str, float] = field(default_factory=dict)

    @property
    def unhandled_errors(self) -> List[Dict[str, Any]]:
        """Errors no error path handled; routed errors do not fail a run."""
        return unhandled_errors(self.errors)

    @property
    def exit_code(self) -> int:
        if self.final_state == "STOPPED":
            return EXIT_INTERRUPTED
        if self.final_state == "FINISHED":
            return EXIT_FINISHED_WITH_ERRORS if self.unhandled_errors else EXIT_OK
        return EXIT_RUN_FAILED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "final_state": self.final_state,
            "errors": list(self.errors),
            "unhandled_error_count": len(self.unhandled_errors),
            "outputs": list(self.outputs),
            "node_timings": dict(self.node_timings),
            "exit_code": self.exit_code,
        }


class RunService:
    """Starts and controls runs over one backend stack."""

    def __init__(
        self,
        master_state: MasterState,
        workflow_map: WorkflowMap,
        factory: NodeFactory,
        event_bus: EventBus,
        secrets_manager: Optional[SecretsManager] = None,
        configuration_manager: Optional[ConfigurationManager] = None,
    ) -> None:
        self._master = master_state
        self._workflow_map = workflow_map
        self._factory = factory
        self._bus = event_bus
        self._secrets_manager = secrets_manager
        self._configuration = configuration_manager
        self._errors_by_run: Dict[str, List[Dict[str, Any]]] = {}
        self._stopped_runs: set[str] = set()
        self._bus.subscribe(ERROR_LOGGED, self._on_error_logged)

    @classmethod
    def create(cls) -> "RunService":
        """Build a complete backend stack (no frontend) and a service over it."""
        bus = EventBus()
        factory = NodeFactory()
        workflow_map = WorkflowMap(factory, bus)
        memory_bank = MemoryBank(bus)
        configuration = ConfigurationManager()
        secrets_manager = SecretsManager()
        master = MasterState(
            workflow_map,
            memory_bank,
            bus,
            output_manager=OutputManager(),
            configuration_manager=configuration,
            secrets_manager=secrets_manager,
        )
        return cls(master, workflow_map, factory, bus, secrets_manager, configuration)

    # -- accessors -----------------------------------------------------------

    @property
    def master_state(self) -> MasterState:
        return self._master

    @property
    def workflow_map(self) -> WorkflowMap:
        return self._workflow_map

    @property
    def event_bus(self) -> EventBus:
        return self._bus

    @property
    def configuration(self) -> Optional[ConfigurationManager]:
        return self._configuration

    @property
    def current_run_id(self) -> Optional[str]:
        return self._master.current_run_id

    # -- load and validate -----------------------------------------------------

    def list_workflows(self) -> List[Dict[str, str]]:
        return list_workflows()

    def load(self, reference: str) -> Dict[str, str]:
        """Load a workflow by saved id, saved name, or path to a JSON file.

        Loading never changes settings (unlike the TUI's SaveManager, it does
        not touch ``last_active_workflow_id``).
        """
        data = self._resolve(reference)
        if not isinstance(data, dict) or not data.get("id"):
            raise WorkflowLoadError(f"{reference!r} is not a workflow (no id)")
        try:
            self._workflow_map.load_data(data)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise WorkflowLoadError(f"Cannot load workflow {reference!r}: {exc!r}") from exc
        return {
            "id": str(self._workflow_map.workflow_id or ""),
            "name": self._workflow_map.workflow_name,
        }

    def _resolve(self, reference: str) -> Dict[str, Any]:
        return resolve_workflow_data(reference)

    def validate(self) -> Dict[str, Any]:
        return validate_workflow(self._workflow_map, self._factory, self._secrets_manager)

    # -- run control -------------------------------------------------------------

    async def start(
        self,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        recovery_policy: Optional[RecoveryPolicy] = None,
        input_provider: Optional[InputProvider] = None,
        validate: bool = True,
    ) -> str:
        """Validate (by default) and start the loaded workflow; return its run id."""
        if validate:
            result = self.validate()
            if not result.get("success", not result.get("errors")):
                raise WorkflowValidationError(result)
        started = await self._master.start_workflow(
            recovery_policy=recovery_policy,
            input_provider=input_provider,
            inputs=inputs,
        )
        if not started or not self._master.current_run_id:
            raise RuntimeError("The workflow could not be started")
        run_id = self._master.current_run_id
        # Only the current run's errors are kept (per-run cache eviction).
        self._errors_by_run = {run_id: []}
        self._stopped_runs.clear()
        return run_id

    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> Callable[[], None]:
        """Subscribe to a backend event; returns a function that unsubscribes."""
        self._bus.subscribe(event_name, callback)
        return lambda: self._bus.unsubscribe(event_name, callback)

    def submit_input(self, branch_id: str, value: str) -> bool:
        return self._master.submit_user_input(branch_id, value)

    def submit_recovery(self, branch_id: str, action: str) -> bool:
        return self._master.submit_recovery_action(branch_id, action)

    def pause(self) -> None:
        self._master.pause()

    def resume(self) -> None:
        self._master.resume()

    def stop(self) -> None:
        """Stop the current run; its result reports ``STOPPED``."""
        if self._master.current_run_id:
            self._stopped_runs.add(self._master.current_run_id)
        self._master.stop()

    async def wait(self) -> RunResult:
        """Wait for the current run to end and return its result."""
        await self._master.wait_for_completion()
        return self.result()

    def result(self) -> RunResult:
        run_id = self._master.current_run_id
        final_state = self._master.state.value
        # The engine has no STOPPED state yet (step 1 follow-up), so a stopped
        # run that ended cleanly is reported as STOPPED here, not FINISHED.
        if run_id in self._stopped_runs and final_state == "FINISHED":
            final_state = "STOPPED"
        return RunResult(
            run_id=run_id,
            workflow_id=self._workflow_map.workflow_id,
            workflow_name=self._workflow_map.workflow_name,
            final_state=final_state,
            errors=list(self._errors_by_run.get(run_id or "", [])),
            outputs=list(self._master.run_outputs),
            node_timings=dict(self._master.node_timings),
        )

    def close(self) -> None:
        self._bus.unsubscribe(ERROR_LOGGED, self._on_error_logged)

    def _on_error_logged(self, payload: Dict[str, Any]) -> None:
        run_id = (payload or {}).get("run_id")
        if run_id in self._errors_by_run:
            self._errors_by_run[run_id].append(dict(payload.get("error") or {}))


def resolve_workflow_data(reference: str) -> Dict[str, Any]:
    """Workflow JSON for a saved id, a saved name (case-insensitive) or a
    path to a workflow .json file; shared by ``aotn run`` and ``aotn inspect``."""
    reference = str(reference or "").strip()
    if not reference:
        raise WorkflowNotFoundError("No workflow given")
    path = Path(reference).expanduser()
    if path.suffix.lower() == ".json" and path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkflowNotFoundError(f"Cannot read workflow file {path}: {exc}") from exc
    data = load_workflow(reference)
    if data is not None:
        return data
    matches = [
        item for item in list_workflows()
        if item["name"].casefold() == reference.casefold()
    ]
    if len(matches) > 1:
        ids = ", ".join(item["id"] for item in matches)
        raise WorkflowNotFoundError(
            f"More than one workflow is named {reference!r} ({ids}); use an id"
        )
    if matches:
        data = load_workflow(matches[0]["id"])
        if data is not None:
            return data
    raise WorkflowNotFoundError(f"No workflow matches {reference!r}")
