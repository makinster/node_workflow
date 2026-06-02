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

- `tombstone_node` as an executable registered backend node.
- `WorkflowMap.replace_with_tombstone()`.
- Tombstone-specific `WorkflowMap.replace_node_type()` restore behavior.
- `_timing_invalidated` as a node-data field.
- Validator messages that talk about opening a tombstone in the editor.

## Migration Plan

### Boundary Phase A — Frontend Tombstone Adapter

Add a frontend-owned editor adapter, for example
`frontend/editor_workflow_adapter.py`, that manages visual deleted-node
placeholders without registering them as executable backend nodes.

The adapter should:

- Keep backend `WorkflowMap.delete_node()` as the pure destructive graph
  operation.
- Represent editor tombstones in frontend display state or a frontend metadata
  sidecar.
- Preserve enough original node display data for undo/replace UI.
- Hide stale timing in frontend display when a visual tombstone is swapped to a
  different node type.

### Boundary Phase B — Backend Tombstone Decommission

After the adapter has regression coverage:

- Remove `tombstone_node` from backend node registration.
- Remove `replace_with_tombstone()` or mark it deprecated until all editor code
  has moved.
- Replace tombstone-specific validation with generic graph validation:
  unresolved nodes, invalid ports, unknown types, and broken connections.
- Remove `_timing_invalidated` from persisted node data.

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

## Review Checklist

Before adding backend code, ask:

- Would a CLI, web UI, or API frontend need this exact behavior?
- Is this execution/state integrity, or only presentation/navigation?
- Can the frontend derive this from graph structure and node metadata?
- Is the stored data part of the workflow definition, or only an editor view?

If the answer is mostly presentation, put it in `frontend/`.
