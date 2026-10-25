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
| `get_recent_events` | optional integer `limit`, 1–100, default 10 | `runs`: newest run-history summaries only (unchanged) |
| `get_activity` | optional `since` ISO 8601 time with a zone; optional integer `limit`, 1–100, default 10 | `activity`: merged run summaries, investigation results and C1 events/receipts, newest first; damage counts and scan-limit flags |

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

### Activity across runs and Hermes

Use `get_activity` for questions such as “what happened today?” A completed
investigation is saved independently of its requesting run and can finish
after that run ends. `get_recent_events` retains its original run-history-only
behavior and result shape for existing clients.

```json
{"name":"get_activity","arguments":{"since":"2026-10-23T00:00:00Z","limit":20}}
```

`since` is inclusive and must specify a time zone (`Z` or an offset); dates,
naive times and phrases such as `today` are rejected. Omit it to include all
activity within the bounded scan. Items sort by their normalized UTC `time`
(with six fractional digits), newest first; `limit` applies to the merged
list, not separately to each source. Equal-time ordering has no semantic
meaning. Each item has `type`, `time` and a fixed `source` label:

| Type / source | Included fields |
|---|---|
| `run` / `run_history` | `run_id`, workflow name/id, final state, start/end times and available error/output counts. Activity time is end time, falling back to start time for older summaries. |
| `investigation` / `investigation_results` | `request_id`, `state`, `finished_at`, redacted `finding` (at most 2,000 characters), `finding_truncated`, and `failure` (the failure code, or null). Failed findings are empty. |
| `event` / `events.jsonl` | `kind`, `stage`, `workflow`, `summary`; Record event also includes `name`. Receipts have a stage string, while Record event has `stage: null`. Notify me receipts do not store the message, so their summary is empty unless the receipt contains one. |

Run history comes from the server's selected AOTN data root. Shared activity
comes from `$HERMES_HOME/aotn`, defaulting to `~/.hermes/aotn`, using the
[same rule as the nodes](HERMES_SHARED_FOLDER.md#the-folder). Configure the
server process's environment for the intended shared root; the investigator's
child profile is a separate home. No tool argument accepts a path. Missing
sources return no items and are never created. The reader opens regular files
read-only, refuses symlink traversal and special files, and never repairs,
locks, chmods, truncates or moves shared records.

The result also includes `skipped` and `skipped_by_source`: counts of damaged,
unknown-version, oversized or unreadable records/lines within the scan. An
unreadable source counts as one skipped source error. Bad JSON/UTF-8, duplicate
keys, non-finite numbers, invalid timestamps, mismatched IDs and unfinished
JSONL tails are skipped without returning/logging their contents. LF alone
frames event lines; Unicode line separators remain text. These counters cover
examined data, not records omitted by a scan cap.

Per call, each directory scan examines at most 2,000 entries and reads at most
8 MiB of record bytes; each JSON record is capped at 256 KiB. The event reader
examines the newest 8 MiB and at most the latest 20,000 complete LF lines, with
a 64 KiB cap per line. A leading fragment cut by the byte window is omitted,
not counted as damaged. An unfinished EOF line still counts once as damaged,
even when it exceeds the entire byte window and its beginning is omitted.
`truncated_sources` lists any sources limited by these
scan bounds. The returned list is newest-first among examined records; it is
not a complete history or pagination API when a source is truncated. The
server's normal tool deadline and response cap still apply.

Only the listed summary fields are projected. Raw request evidence, event
`value`, outbox messages, error details, run outputs and credential files are
never returned. Text is redacted before its display cap using known values in
the selected AOTN Secrets store and the existing investigation redactor for
labelled credentials, bearer/basic tokens, URL passwords and private keys.
This is the shared C3c investigation-inbox redactor, including case-insensitive
password/passwd/secret/token/api_key/apikey/authorization/bearer labels in
`key: value`, `key=value` and JSON forms; spaced `api key`, AWS access/secret
key labels and mixed-case private-key blocks are covered too. Multiline
credential values are masked as a whole: YAML literal/folded blocks (including
chomp/indent indicators and header comments), indented continuations after a
credential key, and plain `key:` continuation blocks, including values that
start on the same line as their label. Indented values end on
dedent; unindented values end at a blank line or the next field. Inline values
do not consume the field on the next line when a credential header is empty.
URL userinfo is removed for any `scheme://` case and scheme name, including
HTTP/HTTPS, FTP, SSH and compound schemes; username-only userinfo is masked
too. URL userinfo is masked before credential-label matching, so passwords
containing strings such as `token=` cannot expose the username. Public URLs,
hosts, paths and following non-secret fields are preserved. Known Secrets
values are supplied to that same redactor without instantiating a writer.
Findings and event summaries are redacted before text caps and before the
worker returns, so both MCP text and structured results carry the safe text.
Unknown unlabelled secrets cannot be inferred from arbitrary prose. A damaged,
oversized or unsafe Secrets store fails this tool closed with a plain error;
its contents are not logged. This tool does not read Hermes profile credentials.

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
new Hermes session to discover the five tools. Ask it to list workflows before
running one. This is independent of the H0 cron wrappers and does not modify
`cron.wrap_response`, cron jobs, Telegram destinations or the live checkout.
For an existing read-only client allowlist, add `get_activity` alongside
`list_workflows`, `get_run_status` and `get_recent_events`, then reload MCP or
start a fresh client session. This does not require exposing `run_workflow`.
