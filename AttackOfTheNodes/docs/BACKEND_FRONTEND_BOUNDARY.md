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

Backend changes that stay (design decision 2026-06-11):

- `tombstone_node` remains a registered backend type by design. See the
  Tombstone Node section below for the rationale and new contract.

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

### Tombstone Node — Intentional Backend Type (design decision 2026-06-11)

`tombstone_node` was previously targeted for Phase B decommission. After design
review, that plan was reversed. The tombstone is now an intentional registered
backend type, not a cleanup target.

**What we had and why we're switching:**

Phase A (done) established a visual-delete model where saves materialized
deleted nodes into `branch_end_node` records with a `_system_role:
"deleted_node_branch_end"` marker. This works for session-scoped undo and
requires zero backend changes. The limitation is that the save file is the only
persistence layer in this project. If a user saves after a delete, closes, and
reopens, the frontend undo context is gone. The materialized `branch_end_node`
can carry restore data, but the connection-level context and the ability to
surface meaningful validator errors are limited by the `branch_end_node` port
shape.

**The tombstone contract going forward:**

`tombstone_node` is the save-persistent record of a deleted node. When a node
is deleted and the workflow is saved, the tombstone stores the complete original
node data in its config so that:

1. **Undo survives save/reload.** Restoring a tombstone swaps it back to the
   original type with original alias, config, input connections, and output
   connections fully intact. The user can reload a workflow and still undo a
   delete from a previous session.
2. **The validator surfaces connection context.** Rather than a generic
   unknown-type error, the tombstone error block reports the original node name,
   its original inputs, and its original output targets — giving users a repair
   guide, not just an identifier.
3. **Dangling connections remain meaningful.** Because the tombstone holds the
   original port declarations, port-validity checks can describe exactly which
   connections broke and why.

**Tombstone config shape:**

```json
{
  "original_type": "logger_node",
  "original_display_name": "Trace",
  "original_alias": "Trace",
  "original_config": { "...full config dict..." },
  "original_inputs": [ "...connection records..." ],
  "original_outputs": [ "...connection records..." ]
}
```

**Boundary rules for tombstone:**

- `tombstone_node` is execution-blocked. The validator must always flag it as
  an error. `MasterState` / `Supervisor` must refuse to run a workflow
  containing tombstones (this is already enforced).
- The backend may register this type because it is part of the portable
  save-file format, not Textual-specific behavior. A CLI runner or API frontend
  consuming save files encounters the same tombstone records and can handle
  them with the same generic error path.
- `node_identity.py` should mark tombstone with `editor_only: True` (or an
  equivalent flag) so non-editor frontends can filter it from their node lists.
- The node selector must always exclude tombstone from the user-facing add list
  (this is already enforced in `NodeSelectorScreen`).

**Validator follow-up work:**

The current tombstone error in `validator.py` reports `original_display_name`
and `original_type`. It should be extended to surface the original input
sources and output targets from the tombstone config so the validator output
reads as a full repair guide.

**Single-node delete rule:**

Deleting a node removes only that one node. Downstream nodes are never
automatically deleted or modified. The tombstone occupies the deleted node's
position as a swap-out and insert-staging placeholder. The graph beyond the
tombstone remains intact. This is an editor invariant that the frontend adapter
must enforce — no cascading deletes, no automatic downstream rewiring.

**Branch-node delete exception (keep selector):**

A `branch_node` is the one case where this rule cannot apply unchanged: it fans
out into multiple paths, so there is no single "downstream" to preserve. The
first delete soft-tombstones the branch node like any other node (undoable, all
paths stay live). The second (permanent) delete opens the **branch keep
selector** modal: the user picks exactly one path to keep, and the unkept paths
and their downstream nodes are pruned (stopping at structural boundaries —
`merge_node`, `branch_end_node`, `start_node`). The branch node's upstream input
is rewired directly to the head of the kept path so the graph stays connected.
This pruning is explicit, user-chosen, and confirmed by the modal — not an
automatic cascade. `merge_node` deletion has no equivalent flow yet and stays
blocked in the editor. Implemented by `prune_branch_tombstone()` (adapter) and
`BranchKeepSelectorScreen`.

**Restore severity context:**

Most heavyweight data in a workflow travels through the vault (MemoryBank
persistent store) rather than transient payloads. Transient payloads are
primarily used for conditional logic — booleans, counters, branch-decision
flags — not large strings or file contents. Many nodes read from the vault
directly and do not depend on the immediately previous node's transient output
at all. This means:

- A tombstone blocks the execution path at that point, but vault state that
  surrounding nodes read is usually unaffected.
- Restore-validation failures on transient ports are often non-critical.
  The downstream node may not have been consuming that transient payload, or
  may be reading the equivalent data from the vault via a dead-drop key.
- The frontend alert should surface connection failures clearly but without
  alarming the user. A partially-restored node with missing transient
  connections is a minor repair in most workflows, not a broken graph.

**Tombstone restore — connection validation and partial restore:**

Restoring a tombstone is not a simple type-swap. Between the time a node was
deleted and the time a user triggers restore, the surrounding workflow may have
drifted. Three categories of drift can make stored connections invalid:

1. **Upstream output drift.** The node that originally fed into the deleted
   node may have had its output port removed, renamed, or its dead-drop payload
   type changed. The stored `original_inputs` connection records the source node
   id and port name. If the source node no longer exists, or no longer declares
   that output port, the connection cannot be safely restored.

2. **Downstream input drift.** The node that originally received output from
   the deleted node may have changed its expected input port, or the port may
   now be occupied by a different source. The stored `original_outputs`
   connection records the target node id and port name. If the target node no
   longer exists, no longer declares that input port, or that input port already
   has a connection from another node, the connection cannot be safely restored.

3. **Memory bank drift.** The deleted node may have declared `membank_inputs`
   (variables it read). If no remaining node in the workflow now declares those
   same variable names in `membank_outputs`, the membank input is broken. The
   deleted node's own `membank_outputs` are less risky — restoring re-establishes
   them — but downstream nodes that depended on those outputs should be checked
   for continued validity.

**Restore procedure (frontend adapter):**

1. Always restore the node type, alias, and config from tombstone data. The node
   itself is never blocked by connection drift.
2. For each stored input connection (`original_inputs`): verify the source node
   exists in the current workflow AND still declares the referenced output port.
   If both checks pass, reconnect. If either fails, leave the input port
   unconnected and record the failure.
3. For each stored output connection (`original_outputs`): verify the target
   node exists AND still declares the referenced input port AND that port is not
   already occupied by another source connection. If all checks pass, reconnect.
   If any check fails, leave the output port unconnected and record the failure.
4. For each stored `membank_inputs` entry: check whether any surviving node
   declares that variable in `membank_outputs`. If not, restore the declaration
   anyway (the user can repair it) but include it in the alert.
5. After restore, if any connections could not be re-established, surface a
   frontend alert with two sections:
   - **Input connection errors:** list each failed input by original source node
     alias/id and port name, with the reason (source gone / port gone).
   - **Output connection errors:** list each failed output by original target
     node alias/id and port name, with the reason (target gone / port gone /
     port already occupied).
   - **Memory input warnings:** list any membank input variables whose declared
     source is no longer present in the workflow.
6. Partial restores are valid. A node restored with some connections missing is
   better than a tombstone — the user can see what is wired and what is not, and
   the validator will flag the unresolved inputs as loose ends rather than a
   tombstone error.

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

## Deleted-Node Save Contract (revised 2026-06-11)

Deleting a node in the editor is visual-only while editing — the original node
data stays live in `WorkflowMap` under a frontend overlay. On save, the
frontend materializes each deleted visual row into a `tombstone_node` record
whose config stores the full original node data (see tombstone config shape
above).

After load, the frontend detects `tombstone_node` records and renders them as
deleted-node rows with restore/replace/permanent-delete actions.

**Why tombstone_node instead of branch_end_node:**

The previous plan (2026-06-10 audit) used `branch_end_node` with a
`_system_role` marker because it required zero backend changes. That approach
has been superseded by the design decision to keep `tombstone_node` as an
intentional backend type. The tombstone format is cleaner: it is self-describing
(the type itself signals "deleted node"), it carries the original port shape so
port-validity errors remain meaningful, it supports undo-after-reload natively,
and the validator can surface richer repair context from the stored original
connection data.

The `branch_end_node` materialization path and the `_system_role:
"deleted_node_branch_end"` convention are superseded. Any existing saves that
contain marked `branch_end_node` records should be migrated to `tombstone_node`
on next load.

**Frontend implementation notes:**

- The frontend adapter (`editor_workflow_adapter.py`) should write
  `type: "tombstone_node"` with the full original-data config on save, not
  `branch_end_node`.
- The node selector already filters tombstone from the user-facing add list.
- The validator's tombstone error block should be extended to report original
  input and output connection context from the stored config.
- Execution is already blocked on workflows containing tombstones.

## Review Checklist

Before adding backend code, ask:

- Would a CLI, web UI, or API frontend need this exact behavior?
- Is this execution/state integrity, or only presentation/navigation?
- Can the frontend derive this from graph structure and node metadata?
- Is the stored data part of the workflow definition, or only an editor view?

If the answer is mostly presentation, put it in `frontend/`.
