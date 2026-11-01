# Newcomer Guide

AttackOfTheNodes is for long, predictable, complex workflows.
A workflow is a recipe of small machines; the terminal UI is its control room.
The aim is to see what ran, supply input, inspect results and recover from errors.
Explicit node contracts keep the editor and engine describing the same behavior.
Read [Vision](VISION.md) for the purpose, distributed direction and Stash design.

Use [README](README.md) to choose a task reference and [Current State](CURRENT_STATE.md)
to check the baseline, open PRs, owner decisions and verification limits.

## Setup and daily commands

Python 3.12+ is required by `pyproject.toml`. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r AttackOfTheNodes/requirements.lock
.venv/bin/python -m pip install -e AttackOfTheNodes/
cd AttackOfTheNodes
../.venv/bin/python main.py                 # launch this checkout's app
../.venv/bin/python -m pytest -n auto       # full suite (requires dev dependencies)
../.venv/bin/python -m pytest tests/test_forwarding.py -q  # focused example
git diff --check
```

For tests, install `AttackOfTheNodes/requirements-dev.txt` from the repository
root. Quick run: `pytest -n auto -m "not slow"` from `AttackOfTheNodes/`.
Reviewers run the full `pytest -n auto` set before merge; see
[testing/isolation](CONTRIBUTING.md#parallel-tests-and-isolation).

These are installation instructions; a clean installation was not repeated for
this docs change. The tested environment is in Current State. In the owner's
separate worktrees use `/home/makin/src/node_workflow/.venv/bin/python` in place
of `../.venv/bin/python`. `python main.py` selects the current worktree; an
installed `aotn` entry point may resolve to its editable-install checkout.

Set `AOTN_DATA_DIR` **before importing the backend** to isolate runtime data.
Without it, persistence uses the app directory. Never use owner workflows as
a test scratchpad. The CLI's `--data-dir` also configures storage before imports.

## First workflow

The authoring CLI reads live node contracts. From `AttackOfTheNodes/`, use the
chosen interpreter (shown below as `python`) to avoid launching another checkout:

```bash
python main.py nodes
python main.py describe logger_node
python main.py build examples/summarise_file.json --check
python main.py run --help
```

The summarisation spec requires a configured secret to run. For a first offline
workflow, save this as `/tmp/aotn-first.json`:

```json
{
  "format": "aotn-workflow/1",
  "name": "First workflow",
  "nodes": {
    "start": {"type": "start_node", "config": {"greeting": "Hello"}},
    "out": {"type": "text_output_node"}
  },
  "connections": [{"from": "start.default", "to": "out.input"}]
}
```

Choose a fresh scratch directory for `AOTN_DATA_DIR`, then build, inspect and run:

```bash
export AOTN_DATA_DIR="$(mktemp -d)"
python main.py build /tmp/aotn-first.json
python main.py inspect 'First workflow'
python main.py run 'First workflow' --json
```

[Workflow Authoring](WORKFLOW_AUTHORING.md) explains the spec and CLI in detail.
`--input KEY=VALUE` supplies a declared Start row, parsed by its type;
`--inputs-file` supplies already-typed JSON values. Start routes those values
downstream and/or into the Vault. See [workflow contracts](WORKFLOW_AUTHORING.md#contracts-inputs-results-and-callable-workflows)
for defaults, missing inputs and Return End results. Child-workflow calls are
later work; the checked delivery status is in Current State.

## The mental model

- **Backend = factory floor.** `Supervisor` walks one execution path;
  `MasterState` starts runs, spawns branches and coordinates completion.
- **Frontend = control room.** Textual screens use backend services and the
  EventBus. See [the boundary contract](BACKEND_FRONTEND_BOUNDARY.md).
- **Nodes are graph-ignorant.** A `NodeContext` supplies resolved inputs and
  callbacks. Call `context.signal_done({"data": {"default": value}})` or
  `context.signal_error(exc)`; neither signal callback is awaited.
- **Per-run state.** `RunContext` owns run identity, waits and delivery state;
  `RunSession` owns resources. Sibling supervisors share the run's `MemoryBank`.
- **Vault is per run.** “Persistent” keys mean named values within that run;
  `MasterState` clears memory at run start. It is not a cross-run Stash.

## Where things live

| Path (relative to the app) | Responsibility |
|---|---|
| `backend/nodes/` | Executable node classes |
| `backend/supervisor.py`, `backend/master_state.py` | Path execution and run coordination |
| `backend/run_context.py`, `backend/run_service.py` | Run state and client-facing run service |
| `backend/validator.py`, `backend/validation_codes.py` | Preflight and issue codes |
| `backend/port_types.py`, `backend/data_types.py` | Producer tracing and type compatibility |
| `backend/field_types.py` | Shared numeric field rules |
| `backend/authoring.py`, `aotn_author.py`, `aotn_cli.py` | Build/inspect and run adapters |
| `frontend/screens/`, `frontend/widgets/` | Screens and reusable controls |
| `../aotn_node_helper/` | Node generator and schema/UI checks |
| `tests/`, `tests/generated/` | Feature tests and generated smoke tests |

## Vocabulary

| UI word | Code meaning |
|---|---|
| Vault | Named `MemoryBank` entries, `vault_write`, `membank_inputs` / `membank_outputs` |
| Dead-drop payload | Transient data keyed by `(source_node_id, port)` |
| Source | Upstream, Vault or Configured, where the node supports those choices |
| Parallel Branch / Join Merge | `branch_node` / `branch_end_node` |
| Error path | Engine `error` output carrying a failure record |
| Family / group | `primary_family` / frontend navigation `group`; the rename was cancelled |
| Tombstone | Saved deleted-node record, retained for repair/restore |

## Engine traps

1. An ordinary output follows its **first** connection. Extra wires do not
   create parallel execution; use Parallel Branch (`ignored_fan_out` warns).
2. A node that signals branches ends its own path. Branch children need data
   stored on the spawning output port for their wired first input; `initial_data`
   alone is insufficient. Deep Branch now publishes its `branch` payload.
3. Siblings share Vault values. A read on a parallel branch has no guaranteed
   ordering unless the graph coordinates it. Merge forwards one selected value,
   rather than aggregating all inputs.
4. Type mismatches can be warnings. `any` is permissive; validation is not proof
   that every runtime value fits the receiver. Check issue codes and severity.
5. Pause is cooperative, checked between nodes; it does not freeze an active
   `execute()`. `node_timeout_seconds` supplies default waits inside nodes
   (completion/merge); it is neither a whole-run deadline nor a universal
   execution timeout. Wait Until can supply its own timeout, including zero.
6. Returning from the run screen to the editor **stops a live run**.
7. `update_node_config` replaces the config dictionary. To change one key,
   supply `{**old_config, "key": new_value}`. Retained unknown keys do not imply
   that a node uses them; authoring rejects unsupported config keys.
8. `check_number` validates finite values and declared ranges; blank uses the
   default and integer fields require whole numbers. Invalid text is not silently
   replaced with zero.
9. The `error` route carries failure information, never the original payload
   as implicit forwarding. Echo also is not identity forwarding: it returns text.
10. End explicitly terminates and authoring can place it, but the TUI selector
    hides it. Output nodes have no generic termination checkbox; an unconnected
    route ends naturally. The selector decision is recorded in Current State.

## Adding a node or changing the UI

Read [Node Standards](NODE_STANDARDS.md), then [Node Helper](NODE_HELPER.md).
Declare ports, types, config and effects honestly. Fixed forwarding needs the
`pass_through` summary and `forwarded_input_port` hint, with an execution test
that proves non-string identity preservation. Declare `spawns_branches` for
branch-spawning nodes. Use the shared Vault declarations and type rules.

**Generation overwrites whole classes and generated tests.** Existing specs
can drift; legacy output metadata drops type fields. Generate into a temporary
location, inspect the diff and manually preserve custom execution, hooks and
tests. Never regenerate over hand-written work on the strength of a smoke test.

Ordinary config renders from metadata/schema. Keep nodes frontend-free and
reuse form/navigation helpers. Forms use W/S to move, E/Enter to edit and Esc
to end editing. The selector has five tabs: In, Flow Control, Utility, Out,
Complex. Consult [UI Quick Reference](UI_QUICK_REFERENCE.md) for screen keys.
The owner's preference is plain, compact UI with sample screens before changes.

## Process and environment

Work in your own checkout or worktree; never edit another worker's. Preserve
owner workflows and unrelated changes. One PR per phase; the owner or an
explicitly requested reviewer merges. Reproduce behavior bugs before fixes.
Update Current State, Session Log and the owning plan row in each PR.
[Contributing](CONTRIBUTING.md) owns the full process, testing habits and the
owner's WSL/shared-venv setup. Old execution prompts are historical.
