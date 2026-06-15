# Backend / Frontend Boundary

AttackOfTheNodes should support multiple frontends in the future. The backend is
the reusable workflow engine; the Textual app is one control-room implementation.

## Principle

Backend code may expose engine capability. It should not implement behavior that
exists only to make the current Textual UI convenient.

Good backend responsibilities:

- Workflow graph storage, traversal, and validation.
- Node execution, branching, merging, waiting, pause/resume, breakpoints, timing,
  output persistence, and run history.
- Node metadata that any frontend can consume: `node_type`, `display_name`,
  `description`, `category`, ports, `default_config`, `config_schema`, and
  generic `ui_hints`.
- Derived save/validation metadata such as `input_sources` when it is part of
  workflow integrity.

Frontend responsibilities:

- Visual placeholders, list compaction, selection, focus, keyboard behavior,
  modals, notifications, and editor-only display state.
- Textual-specific rendering of config schema, branch selectors, memory-bank
  registries, and command-navigation helpers.
- Hiding, dimming, grouping, and naming UI controls.

## Current Audit

Backend changes that should stay:

- Memory cleanup: `OutputManager.finalize_run()`, `ErrorHandler.finalize_run()`,
  run-history caps, and output/error persistence cleanup.
- `WorkflowMap.nodes_reachable_from()`: graph reachability is reusable engine
  logic.
- Save/validation derivation of `input_sources`: structural workflow metadata.
- Port and membank validation: backend integrity checks.
- Breakpoints and node timing: runtime/debug capabilities useful to every
  frontend.
- Completion registry, `WaitUntilNode`, `MergeNode`, and merge coordination:
  execution semantics, not UI behavior.
- Node metadata/category/schema validation: frontend-neutral node contract.

Backend changes to migrate or quarantine:

- `tombstone_node` as an executable registered backend node (still
  registered; see Phase B status below).
- Validator messages that talk about opening a tombstone in the editor
  (`backend/validator.py`, tombstone-stub error block).

Already migrated (audit refreshed 2026-06-10):

- `WorkflowMap.replace_with_tombstone()` — removed; placeholder swaps now
  live in `frontend/editor_workflow_adapter.py`.
- Tombstone-specific `WorkflowMap.replace_node_type()` restore behavior —
  removed; `EditorWorkflowAdapter.replace_placeholder()` owns restore.
- `_timing_invalidated` as a backend-written node-data field — the backend
  no longer writes it; the frontend adapter pops it defensively on
  placeholder replacement and tests assert its absence.

## Migration Plan

### Boundary Phase A — Frontend Tombstone Adapter (done)

`frontend/editor_workflow_adapter.py` exists and owns placeholder behavior:
`is_placeholder()`, `replace_with_placeholder()`, `remove_placeholder()`,
`replace_placeholder()` (with original-type restore), soft visual deletes,
and save-time materialization to a marked `branch_end_node`. Backend
`WorkflowMap.delete_node()` remains the pure destructive graph operation.
Regression coverage lives in `tests/test_debug_nodes.py`.

For new editor deletes, the adapter no longer writes
`type: "tombstone_node"` into workflow node data. Legacy
`tombstone_node` registration remains only as a compatibility/decommission
target until old-save loading behavior is decided.

### Boundary Phase B — Backend Tombstone Decommission (remaining)

Remaining backend tombstone footprint:

- `backend/nodes/debug/tombstone_node.py` — the executable class.
- `backend/nodes/__init__.py` — import and `ALL_NODE_CLASSES` registration.
- `backend/validator.py` — tombstone-specific error block ("Deleted node
  stub (was: ...) — replace with a valid node type").
- `backend/node_identity.py` — Phase 17 identity entry for
  `tombstone_node`.

Decommission steps, in order:

1. Preserve or migrate old save files containing `tombstone_node`, either by
   converting them to frontend deleted-node overlays on load or by rendering
   unknown types as replaceable placeholders.
2. Remove `TombstoneNode` from `backend/nodes/__init__.py` registration and
   delete `backend/nodes/debug/tombstone_node.py`.
3. Replace the validator's tombstone-specific block with the generic
   unknown-node-type error (already produced by the existing type check);
   the frontend can map that generic error back to placeholder UI copy.
4. Remove the `tombstone_node` entry from `backend/node_identity.py`.

Coordination gate: do not start Phase B while Phase 17 selector/editor work
is in flight. The decommission touches `node_identity.py` (Phase 17 metadata),
changes which types appear in `NodeFactory.get_node_types_metadata()` (the
selector's data source), and changes editor placeholder rendering inputs.
There are ~26 tombstone references in `tests/test_debug_nodes.py` that will
need a coordinated sweep.

Known wart until Phase B lands: because `tombstone_node` is registered, it
still appears in node-type metadata, though the selector now filters it from
the user-facing add list.

### Boundary Phase C — Editor Metadata Policy

Decide how editor-only fields are stored:

- Either in a top-level workflow `editor_state` object keyed by frontend name.
- Or in a frontend sidecar file/cache outside the engine workflow save.

Candidates for editor-only metadata:

- Tombstone visual placeholders.
- Expanded/collapsed state.
- Cursor/list selection.
- Panel layout preferences.
- Possibly `position` and `bookmarked`, unless they are intentionally part of
  the portable workflow format.

## Deleted-Node Save Contract (audited 2026-06-10)

The visual-deleted-node model: deleting is frontend-only while editing (the
original node data stays in memory under a frontend overlay). On save, the
frontend materializes each deleted visual row into an ordinary
`branch_end_node` record whose config carries a marker:

```json
{
  "_system_role": "deleted_node_branch_end",
  "deleted_node": { "...original type/alias/config/ports..." }
}
```

After load, the frontend renders marked nodes as
`Deleted node: <alias> (<node type>)` with delete/undo/new-node actions,
hiding undo when `deleted_node` restore data is missing.

Audit result: **this works today with zero backend changes.** Findings:

- **SaveManager preserves arbitrary config.** Save, export, and duplicate
  all pass node config through `deepcopy` and a JSON round-trip with no
  schema filtering. Import rewrites only top-level `id`/`name`. Any
  JSON-serializable config keys survive.
- **WorkflowMap preserves the marker.** `load_data` deepcopies nodes,
  `save`/`get_workflow_data_for_save` write `_nodes` through unmodified, and
  `update_node_config` stores the dict as given. `persistence.py` is raw
  JSON. No new persistence code needed.
- **Config must carry the marker — not a top-level save key.** Both
  `WorkflowMap.save` and `get_workflow_data_for_save()` emit only
  `id`/`name`/`nodes`, so any extra top-level key (e.g. `editor_state`)
  is silently dropped on the next save. The node-config marker is the
  correct vehicle.
- **Validator accepts extra config keys.** `validate_workflow` never
  diffs config against `config_schema` and `branch_end_node` declares an
  empty schema, so `_system_role`/`deleted_node` are ignored. Caveat: keep
  the original node's `membank_inputs`/`membank_outputs` nested inside
  `deleted_node`, not at the top level of the materialized config —
  top-level membank keys are validated and would produce spurious errors.
- **Execution stops safely with no outgoing connection.** `BranchEndNode`
  signals plain data; the supervisor then resolves the next node via the
  `default` port, gets `None`, and terminates the branch cleanly. Merge
  barriers do not deadlock: `MasterState._account_for_branch_termination`
  removes terminated branches from pending merge groups. Materialization
  MUST drop the node's outgoing connections — if one is left in place,
  execution continues downstream silently.
- **Port-shape caveat.** `branch_end_node` declares exactly `input` /
  `default`. Surviving connections that reference any other port name
  (e.g. a deleted Branch node's `path_a`, or inbound `path_1` on a deleted
  Merge) fail the validator's port-validity check as errors, making the
  workflow unrunnable until resolved. Materialization should rewrite or
  drop non-matching connections, or accept that multi-port deletions
  produce blocking validation errors rather than quiet stops.
- **Downstream nodes become unreachable warnings.** Dropping the outgoing
  connections leaves the formerly-downstream section flagged by the
  existing loose-node warning — useful signal, not a blocker.

Future (optional, not required for the frontend plan): a validator warning
for marked nodes is an ~8-line block — when `type == "branch_end_node"` and
`config._system_role == "deleted_node_branch_end"`, append a warning such as
"Deleted node placeholder will stop this branch during execution," and
optionally a second check that `deleted_node` restore data is present.

## Review Checklist

Before adding backend code, ask:

- Would a CLI, web UI, or API frontend need this exact behavior?
- Is this execution/state integrity, or only presentation/navigation?
- Can the frontend derive this from graph structure and node metadata?
- Is the stored data part of the workflow definition, or only an editor view?

If the answer is mostly presentation, put it in `frontend/`.
