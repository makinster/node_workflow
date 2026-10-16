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

## What a build checks

In one pass, reporting every problem at once:

1. The spec's shape, handles, node types (internal types are refused).
2. Config: unknown keys and number fields (the C5 policy: finite, in range,
   integers whole) are errors.
3. Node references and connection ports.
4. The full validator (`validate_workflow`): its errors fail the build, its
   warnings are reported (codes from `backend/validation_codes.py`).
5. Save through `SaveManager` (atomic write), refusing a name that is
   already saved, then reload the file into a fresh map and check that it
   matches and validates the same.

Nothing is written unless all of that passes. A passing build does not run
anything: model calls, HTTP requests and file writes happen only in a run.

## Limits (v1)

- Keys a type uses but does not describe in its schema (Merge's are listed by
  `describe` as "unchecked") are accepted without type checks.
- Building never edits an existing workflow; it always creates a new one.
- Inspect reports, checked-in example specs, templates, automatic planning and
  live editing of an open workflow are later work (see the plan).
