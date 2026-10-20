# Workflow Authoring Tool

Build preconfigured workflows from a small JSON spec instead of clicking them
together or hand-writing save files. For people, scripts and AI agents.
Core: `backend/authoring.py`. CLI adapter: `aotn_author.py` (`aotn nodes`,
`aotn describe`, `aotn build`). Plan and scope: `NODE_CONTRACT_PLAN.md`,
"Workflow authoring tool".

## Commands

```bash
aotn nodes                                   # every placeable node type, by family
aotn describe sleep_node                     # fields, limits, ports, Vault effects, errors
aotn describe branch_node --set branch_count=3   # describe with config overrides
aotn build my_workflow.json                  # build, check, save as a new workflow
aotn build my_workflow.json --check          # build and check only; writes nothing
aotn build - < my_workflow.json              # spec on stdin
aotn inspect "Pause and wait"                # explain a saved workflow (id, name or .json path)
```

Every command takes `--json` (machine-readable) and `--data-dir` (same as
`aotn run`). `aotn build` exits 1 when anything failed. Run a built workflow
with `aotn run "<name>"` or open it from the app's Workflow Library.

## Spec format (`aotn-workflow/1`)

```json
{
  "format": "aotn-workflow/1",
  "name": "Pause and wait",
  "nodes": {
    "start": {"type": "start_node", "config": {"greeting": "hi"}},
    "nap":   {"type": "sleep_node", "alias": "Nap", "config": {"duration": 0.2}},
    "fan":   {"type": "branch_node", "config": {"branch_count": 2}},
    "a":     {"type": "no_op_node"},
    "b":     {"type": "no_op_node"},
    "wait":  {"type": "wait_until_node", "config": {"target_node_ids": ["a"]}},
    "end":   {"type": "end_node"}
  },
  "connections": [
    {"from": "start.default", "to": "nap.input"},
    {"from": "nap.default", "to": "fan.input"},
    {"from": "fan.path_a", "to": "a.input"},
    {"from": "fan.path_b", "to": "b.input"},
    {"from": "b.default", "to": "wait.input"},
    {"from": "wait.default", "to": "end.input"}
  ]
}
```

- **Handles** (`start`, `nap`): lowercase letters, digits and `_`, starting
  with a letter; local to the spec. Node ids are generated and reported back.
- **`alias`** is the display name (optional; defaults to the type's).
- **`config`** uses the node's real config keys (see `aotn describe`), merged
  over its defaults. Shared routing and Vault keys (`vault_write`,
  `vault_write_key`, `transient_output`, ...) are allowed on every node.
- **Node references**: fields `describe` lists under "Node references"
  (Wait Until's `target_node_ids`) take handles; the build writes the ids.
- **Connections** name both ports: `"handle.port"`. The ports must exist for
  that node's config (Branch with 3 paths has `path_a`..`path_c`; every node
  also has `error`).
- **One destination per ordinary output.** The engine follows only the first
  connection of an output, so wiring one output to two nodes fails the build
  (`ignored_fan_out`; the editor's validator warns about it). Use a Parallel
  Branch to run several paths. Exceptions: the `error` port (routes by code
  to several Error Mux nodes) and an inline Error Mux on a normal output.

## Contracts: inputs, results and callable workflows

A workflow's **inputs** are Start's `rows`; a **callable** workflow also has
a **Return End** whose `results` are what it returns. The backend and CLI
support these contracts now; calling one workflow from another is a later
Step 4 stage. See
[SUBWORKFLOWS_PROPOSAL.md](SUBWORKFLOWS_PROPOSAL.md) for the design.

```json
{
  "format": "aotn-workflow/1",
  "name": "Greeter helper",
  "callable": true,
  "nodes": {
    "start": {"type": "start_node", "config": {"rows": [
      {"name": "who",   "type": "string", "required": true, "to": "Vault"},
      {"name": "times", "type": "number", "value": "2",     "to": "Vault"}
    ]}},
    "end": {"type": "end_node", "config": {"return_end": true, "results": [
      {"name": "greeted", "type": "string", "source": "Vault key", "vault_key": "who"}
    ]}}
  },
  "connections": [{"from": "start.default", "to": "end.input"}]
}
```

- **Start rows**: `name`, `type` (`string`, `number`, `bool`, `var` for any
  JSON value, `file`), `value` (the default when run directly; blank means
  none), `required`, `to` (`Downstream`, `Vault` or `Both`) and `vault_key`
  (blank means the row's name). One downstream row is sent as itself,
  several as one object. A Start with no rows keeps its `greeting`, unless
  `no_inputs: true` says every input was removed (then it sends nothing).
- **Return End** (`end_node` with `return_end: true`): each result has
  `name`, `type`, `required` (default true) and `source` (`Vault key` or
  `Incoming payload`). A callable workflow has at most one Return End, and
  it must come after any Parallel Branch has merged.
- **`callable`** (top level, default false) marks a workflow as callable:
  a **subworkflow**, listed on the File window's Subworkflows tab. In the app,
  C on the Workflows tab copies a workflow there (same name, numbered `(2)`
  for a repeat copy); Start's Inputs tab, the End's Results tab and "Send
  back to calling workflow" on a Vault payload edit the same keys.

Running one: `aotn run <workflow> --input who=Kim --input times=3` parses
each value by its row (numbers, `true`/`false`, JSON for `var`, a path for
`file`). `--inputs-file run.json` supplies a JSON object of **already-typed**
values (a number must be a JSON number; a `var` string stays a string);
`--input` wins over it, and a row's value fills anything left. Return End
results are enforced only when the workflow is callable. Absent or JSON `null`
means missing, as does a blank stored default; an explicitly supplied `""`,
`0` or `false` is a value. A run
with a missing required input, a wrongly typed value, or (callable only) an
undeclared input stops before it starts with **exit code 5**. A workflow and
its subworkflow copy may share a name: `aotn run "<name>"` picks the
workflow, `aotn run "<name> [sub]"` the subworkflow, so no name may end with
`[sub]` (`aotn build` reports `name_invalid`). Results print
as `name = value` after the outputs, and in `--json` output as `values`, with
the `revision` of the definition that ran.

### Calling a subworkflow

A `subworkflow_node` runs a saved subworkflow by id as a child run and waits
for its results (Step 4b; the TUI picker comes in 4c):

```json
"call": {"type": "subworkflow_node", "alias": "Greet", "config": {
  "workflow_id": "wf_3f2a...",
  "inputs":  [{"name": "who", "source": "Configured", "value": "Kim"},
              {"name": "times", "source": "Vault", "vault_key": "count"}],
  "results": [{"name": "greeted", "to": "Vault", "vault_key": "greeting"}]
}}
```

- **inputs**: `source` is `Configured` (`value` is text, parsed by the
  child's row type), `Upstream payload` (the node's input) or `Vault`
  (`vault_key`). Unlisted inputs use the child's defaults.
- **results**: `to` is `Downstream` (the default for unlisted results),
  `Vault` or `Both`; a blank `vault_key` means the result's own name
  (owner, 2026-10-20). The
  `default` output carries the downstream results: one as itself, several
  as one object.
- Failures are coded and routable on `error`: `child_not_found`,
  `child_input_missing`, `child_input_invalid`, `child_failed`,
  `child_output_conflict`, `depth_limit`, `capacity_limit`. Settings
  `max_subworkflow_depth` (default 4) and `max_live_subworkflow_runs`
  (default 64) limit a root run; a call past either fails at once.
- The validator rejects a missing child, a standard workflow as the child,
  any loop of calls, inputs the child doesn't have or needs (names match
  exactly), configured values of the wrong type, and result routes the child
  doesn't send back; it warns when an input keeps its default.

## What a build checks

In one pass, reporting every problem at once:

1. The spec's shape, handles, node types (internal types are refused).
2. Config: unknown keys and number fields (the C5 policy: finite, in range,
   integers whole) are errors.
3. Node references and connection ports.
4. The full validator (`validate_workflow`): its errors fail the build, its
   warnings are reported (codes from `backend/validation_codes.py`).
5. Save through `SaveManager` (atomic write, a unique temporary file per
   save), refusing a name already saved for the same kind of workflow
   (case-insensitive, as `aotn run` matches names; the app's rename and New
   use the same rule,
   `backend/workflow_names.py`), then reload the file into a fresh map and check that it
   matches and validates the same.

With `--json`, stdout carries only the JSON report; warnings (for example an
unreadable saved workflow) go to stderr.

Nothing is written unless all of that passes. A passing build does not run
anything: model calls, HTTP requests and file writes happen only in a run.

## Inspect

`aotn inspect <workflow>` explains a saved workflow the way the engine runs
it (any workflow, not only built ones):

- **Execution** from Start: an ordinary output follows its first connection
  (extra ones are listed as never running); a Parallel Branch splits into
  parallel paths; Conditional, Error Mux and similar take one of their used
  outputs; `error` connections show as "on error"; loops and joins are
  marked; nodes Start never reaches are listed.
- **Vault**: each key's writers and readers, and for every reader whether a
  writer is guaranteed to run first ("before"), only runs on a parallel path
  ("not guaranteed") or does not exist ("no writer").
- **Data flow**: each Upstream connection's types: ok, ok (accepts any),
  mismatch, or unchecked (the port wants a type the sender does not declare).
- **Unchecked config**: keys with no schema (custom editor sections, such as
  Error Mux `routes`), which nothing type-checks.
- **Validation**: the validator's issues with their codes.

Nodes sharing a name get their id's last four characters (`No-Op #3f2a`).

## Examples

`examples/` holds specs for small real use cases (parallel wait, ask and
branch, Vault handoff, fetch and save, catching HTTP errors, summarising a
file); see `examples/README.md`. The test suite builds and inspects every
one, so they stay current with the node contracts.

## Custom config keys

Some config is edited by a custom editor section rather than the generated
form (Error Mux `routes` / `unmatched_route`). Nodes declare such keys in
`custom_config_keys` (key → meaning); the builder accepts them, `describe`
lists them, and both report them as unchecked.

## Limits (v1)

- Keys a type uses but does not describe in its schema (Merge's are listed by
  `describe` as "unchecked") are accepted without type checks.
- Building never edits an existing workflow; it always creates a new one.
- Templates, automatic graph planning and live editing of an open workflow
  are later work (see the plan).
