# Local MCP workflow tools (C4)

`aotn mcp` lets a local MCP client discover and run saved AOTN workflows.
It is a CLI client over the existing backend services, with no engine or TUI
changes. No Hermes dependency, network listener, shell tool or arbitrary file
reader is added. Use a library of workflows you intend the connected client
to run: the workflows' own file, network and other effects remain real.

The MCP Python SDK is absent from `requirements.lock`. This implementation
therefore uses the **standard library**, not an unpinned SDK dependency:
newline-delimited UTF-8 JSON-RPC over stdin/stdout, following the
[MCP stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).
It implements the [initialization lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle)
and [tools interface](https://modelcontextprotocol.io/specification/2025-11-25/server/tools),
with JSON Schema inputs/outputs and structured content plus a JSON text result.
Supported handshake versions: `2025-11-25`, `2025-06-18`, `2024-11-05`.
For an unknown requested version it offers `2025-11-25`; the client decides
whether to continue. The oldest version receives text results without the
newer structured-content/output-schema fields. This is a small tools server;
resources, prompts, sampling, elicitation, HTTP and MCP tasks are not advertised.

## Start the server

After installing the checkout's normal locked dependencies and package:

```bash
aotn mcp --data-dir /absolute/path/to/aotn-data --call-timeout 60
```

For a worktree sharing the owner's venv, use the selected tree's `main.py`
explicitly; an installed editable `aotn` may still point to another checkout:

```bash
/home/makin/src/node_workflow/.venv/bin/python \
  /absolute/path/to/checkout/AttackOfTheNodes/main.py mcp \
  --data-dir /absolute/path/to/aotn-data --call-timeout 60
```

`python -m aotn_mcp` is also supported from the app directory or an installed
package. The module is included in the wheel. These are long-lived stdio
servers: clients keep stdin open until shutdown. There is no startup banner;
stdout contains only protocol messages. Logging and worker diagnostics go to
stderr, including incidental node stdout.

`--data-dir` has CLI precedence over `AOTN_DATA_DIR`. Both are resolved before
any backend import. It selects the usual data root containing `workflows/`,
`stash/`, `settings/`, `run_history/` and the other run records. MCP refuses a
root whose configured library resolves into a Git checkout's
`AttackOfTheNodes/workflows/`, including symlinks and direct/nested selections
of that folder. It otherwise accepts the selected library, including a library
elsewhere inside a checkout. With no override, the source checkout's default
repository library is refused; choose `--data-dir` or `AOTN_DATA_DIR` explicitly.
No workflow is installed, built or edited by the MCP tools.

## Tools

| Tool | Arguments | Result |
|---|---|---|
| `list_workflows` | `{}` | `workflows`: each saved `id`, `name`, `callable`, `inputs`, `results`, `asks`, from `backend.contracts.call_contract` |
| `run_workflow` | `name_or_id` string; optional `inputs` object | `run_id`, `final_state`, `exit_code`, `outputs`, `values`, and the existing RunResult metadata/errors |
| `get_run_status` | `run_id` string | `run`: the persisted run-history summary |
| `get_recent_events` | optional integer `limit`, 1–100, default 10 | `runs`: newest run-history summaries; no `events.jsonl` log yet |

Example `tools/call` arguments:

```json
{"name":"run_workflow","arguments":{"name_or_id":"Calculate totals","inputs":{"count":12,"enabled":true,"options":{"round":false},"report":"@stash:Monthly report"}}}
```

Inputs are native JSON values checked by the Start contract; a JSON string
`"12"` is not a number. `false`, zero, empty strings and nested JSON remain
intact. Defaults and required-input checks use the existing contract code;
callable workflows reject undeclared inputs, as the CLI does. A file input
accepts the contract's file path/reference representation. `@stash:name`
resolves the named Stash entry; text is parsed by the declared input type and
file entries retain their typed reference. Missing/invalid entries fail with
exit code 5 before starting. Names follow CLI precedence: when an ordinary and
callable workflow share a name, the ordinary workflow wins; use an ID to choose
explicitly. Arbitrary JSON file paths are not workflow selectors.

Runs use `RunService` with the `terminate_workflow` policy and `NoInputProvider`.
C25 checks the selected workflow and nested saved subworkflows for potential
input prompts **before starting**, even if a prompt might be skipped at runtime.
Unexpected runtime prompts also fail through the unattended provider.
Workflow failures set MCP `isError: true` and preserve the workflow's exit code
in its structured result. Bad tool arguments, missing names, C25 rejection and
transport/timeout failures return an MCP tool error, not a successful run.
Pre-start contract/validation errors include `run_id: null`, empty outputs/values
and `NOT_STARTED`; a nonexistent run ID is a tool error.

History tools read persisted summaries afresh on every call. They do not claim
live progress, delivery receipts or the full run output. A hard timeout or
cancellation can end before the backend persists a final summary; no synthetic
history record is invented.

## Deadlines and shutdown

Each call, including queue time, has the server's `--call-timeout` deadline
(default 60 seconds; positive finite values only). One worker subprocess runs
at a time, isolating backend singletons and blocking workflow code. Up to 16
calls may be pending. On timeout, MCP cancellation, EOF, external stop or an
adapter error, the worker process group is killed and reaped. Linux additionally
uses child-subreaper adoption and `/proc` ancestry to clean descendants that
leave that group/session. Other POSIX systems retain process-group cleanup.
Native Windows stdio/process behavior has not been verified; use WSL.

Cleanup has a separate one-second bound. If cleanup cannot be confirmed, that
server refuses further tool starts; inspect remaining processes before
restarting it. Timeouts/cancellations terminate work rather than rolling back
workflow effects. Request lines are limited to 1 MiB and worker reports to
16 MiB; excess is a protocol/tool error. An oversized request closes the session.

## Claude Code

Use the [documented local stdio registration command](https://code.claude.com/docs/en/mcp#option-3-add-a-local-stdio-server),
substituting your actual checkout and data root:

```bash
claude mcp add --transport stdio aotn -- \
  /home/makin/src/node_workflow/.venv/bin/python \
  /absolute/path/to/checkout/AttackOfTheNodes/main.py mcp \
  --data-dir /absolute/path/to/aotn-data --call-timeout 60
claude mcp get aotn
```

Use `/mcp` inside Claude Code to inspect the connection and tool permissions.
This document supplies setup instructions; the PR does not register a server
or change client configuration on the owner's machine.

## Hermes

Add a local stdio entry to `~/.hermes/config.yaml` using the
[Hermes MCP configuration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp):

```yaml
mcp_servers:
  aotn:
    command: /home/makin/src/node_workflow/.venv/bin/python
    args:
      - /absolute/path/to/checkout/AttackOfTheNodes/main.py
      - mcp
      - --data-dir
      - /absolute/path/to/aotn-data
      - --call-timeout
      - "60"
    timeout: 65
```

Choose a client timeout longer than the server deadline plus cleanup. Start a
new Hermes session to discover the four tools. Ask it to list workflows before
running one. This is independent of the H0 cron wrappers and does not modify
`cron.wrap_response`, cron jobs, Telegram destinations or the live checkout.
