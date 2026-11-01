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
- **Each node's output ports (port model).** Metadata `output_ports` is the
  type's full list; `NodeFactory.node_output_ports(node_data)` (or
  `output_ports_for(type, config)`, `WorkflowMap.output_ports(node_id)`)
  returns the ports one node actually has, from its config, via
  `Node.resolve_output_ports(config)`. Frontends call it and never re-derive
  the rule (for example the Branch path count). The engine-level `error` port
  is not listed. Per-port names come from
  `NodeFactory.node_output_port_metadata(node)` (Error Mux route labels).
- Each node's input ports, mirroring outputs: `Node.resolve_input_ports`,
  `NodeFactory.node_input_ports(node)` / `input_ports_for` /
  `declared_input_ports`, `WorkflowMap.input_ports`. Merge's slot count
  (`input_slots`) is the only config-driven case. A connection into a slot the
  config hides is a validator warning (never read).
- What an Error Mux route is (`node_errors.mux_routes`: ids, codes,
  per-branch `forward`, matching, the `default` No error port, migration of
  old `path_*_codes`) and how the engine catches a failure inline. The config
  UI — readable error names, the Source picker, branch rows on Parameters and
  Payloads — is frontend-only (`frontend/error_mux_ui.py` and node config's
  Error Mux tabs); the validator re-checks the result.

Frontend responsibilities:

- Visual placeholders, list compaction, selection, focus, keyboard behavior,
  modals, notifications, and editor-only display state.
- Textual-specific rendering of config schema, branch selectors, memory-bank
  registries, and command-navigation helpers.
- Hiding, dimming, grouping, and naming UI controls.

## Historical boundary audit

Backend changes that should stay:

- Memory cleanup: `OutputManager.finalize_run()`, `ErrorHandler.finalize_run()`,
  run-history caps, and output/error persistence cleanup.
- `WorkflowMap.nodes_reachable_from()`: graph reachability is reusable engine
  logic.
- Save/validation derivation of `input_sources`: structural workflow metadata.
- Port and membank validation: backend integrity checks. A connection on a
  port the type has but this node's config hides is a warning (it never
  runs); a port the type never had is an error.
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

### Boundary Phase A — Frontend Tombstone Adapter (historical)

This intermediate save model is superseded by the intentional tombstone
contract below. Do not implement its decommission instructions as new work.

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
  an error. App Run and clients that validate reject the workflow before a run.
  Raw `MasterState.start_workflow` does not perform general validation; a
  tombstone reached by a supervisor fails execution. Callers wanting full
  preflight must use the shared validator, as App Run now does.
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

**Editor deletion groups (phase 2, 2026-10-19):**

An ordinary node keeps its soft-delete overlay until Save/Validate; its versioned
`delete_group` metadata survives materialization. Structural deletes immediately
create one blocking `tombstone_node`: the owner and all exclusively dropped
members form one restore operation. Records contain JSON graph/config snapshots,
never runtime resources. Existing ungrouped tombstones keep their legacy path.

Branch and Conditional first-delete pickers require exactly one kept path. The
adapter reuses `stub_removal_plan` and `nodes_only_reached_from`, combining
all dropped heads before checking ownership. Shared live nodes, including nodes
with disconnected outside parents, survive. Start is protected. End and Merge
Beacon are inclusive boundaries; an orphan Merge cascades only when no input
survives. A Resolver keeps No error automatically and groups its owned recovery
routes; a shared live Resolver survives. Soft-deleted peers are not live guards.

Deleting a Merge preserves every previously connected Beacon and resets all of
those Beacons' Merge targets, including other targets on the same Beacon.
Related Merge selections belong to the same restore record. An ambiguous Merge
with several non-Beacon home inputs requires repair before deletion. Deleting
a Beacon ends its branch, including before Save; permanent removal never bridges
its parents into the Merge. Unconnected Beacon and unreachable warnings retain
their existing nonblocking severity; active tombstones still block execution.

Z on a selected group restores compatible nodes, both halves of connections and
related settings. Three-way comparison preserves newer wiring and config.
Conflicts are shown before partial restore; unresolved work remains in
`delete_recovery`, survives reload and can be retried after repair. Reused IDs,
missing types/ports, occupied outputs and Merge inputs are reported. Compatible
inserted Resolver inputs remain valid. Final stub removal confirms discarding
stored members, bridges at most the recorded continuation and never rewalks the
current graph. Different-type replacement confirms the same irreversible loss;
original-type replacement restores the group.

A live Branch stores count-reduction archives in versioned `branch_recovery`
config: entries have stable path IDs, original labels/seeds, head connections
and member IDs; groups retain the affected graph snapshots. These archived
members are absent from the live graph, never run and add no blocking stub.
The editor-owned Branch config subclass defers count saves before Node Config
can establish a saved baseline; it does not edit Node Config or its private
snapshot state. An exact-N picker maps selected old paths to contiguous ports
in their old order and remaps labels, seeds, edges, Merge keys and editor views.
Cancel preserves the unsaved draft and live graph. Successful save-and-stay
reopens from committed data with the same tab/focus.

Count increases offer Recover / Leave empty / Cancel. If more paths are saved
than new ports, an optional picker accepts zero through the new-port count.
Only selected paths are relinked; unchosen paths stay saved. A partially restored
head is not offered twice; unresolved members remain repair data. Saved paths
appear as a collapsed editor row, not a live port or insert target. Explicit
removal confirms discarding recovery data. No silent expiry is implemented.
All plan previews are pure and commits reject graph/overlay drift.

**Merge candidate selection is graph-position-constrained:** `merge_input_options()`
must only offer a Join Merge to close on a `merge_node` when that beacon's
owning branch node is upstream of (or unrelated to) the merge being configured.
A branch node that only appears in the merge node's forward-reachable
descendant set starts *after* this merge runs, so it cannot have closed by the
time the merge executes — offering it as a close candidate would let the
editor wire a structurally impossible merge. Computed via a forward BFS from
the merge node (`_descendant_node_ids()`), not the (incomplete) branch-context
map, since that map's DFS stops at every beacon and never assigns a context to
a merge node or anything downstream of one.

**Editor selector coloring tracks the merge it connects to, not its own
branch:** When a Join Merge is wired to a `merge_node`, the beacon's editor
selector row (text + connector line) and its own gutter/numline color match
the branch that *contains the merge node*, not the beacon's own branch. This
keeps the editor view visually tying a beacon to its destination rather than
its origin. Implemented by `EditorScreen._merge_node_branch_color_key()`.

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
   has a connection from another node, the connection cannot be safely restored,
   unless the port is an ordinary input that two parents may share (a fan-in;
   see step 3 of the procedure).

3. **Memory bank drift.** The deleted node may have declared `membank_inputs`
   (variables it read). If no remaining node in the workflow now declares those
   same variable names in `membank_outputs`, the membank input is broken. The
   deleted node's own `membank_outputs` are less risky — restoring re-establishes
   them — but downstream nodes that depended on those outputs should be checked
   for continued validity.

**Restore procedure (frontend adapter):**

1. Always restore the node type, alias, and config from tombstone data. The node
   itself is never blocked by connection drift.
2. Keep any input the tombstone gained while deleted (an insert placed it
   after a new node). Then, for each stored input connection
   (`original_inputs`): verify the source node exists in the current workflow
   AND still declares the referenced output port AND that port does not now
   lead to another node. If all pass, reconnect. Otherwise leave it, and record
   the failure (`source_port_taken` for the last) unless the node already has
   an input. An output never gets a second target this way (owner report,
   2026-10-18: the Error Resolver vanished from the editor).
3. For each stored output connection (`original_outputs`): verify the target
   node exists AND still declares the referenced input port AND that the port
   is not fed by another source. Exception: an ordinary input (never a Merge
   slot) may be shared with another parent (a fan-in) when the restored node
   has an input back and that parent did not take its place (it is not fed by
   one of the restored node's inputs). If all checks
   pass, reconnect. If any check fails, leave the output port unconnected and
   record the failure.
4. For each stored `membank_inputs` entry: check whether any surviving node
   declares that variable in `membank_outputs`. If not, restore the declaration
   anyway (the user can repair it) but include it in the alert.
5. After restore, if any connections could not be re-established, surface a
   frontend alert with two sections:
   - **Input connection errors:** list each failed input by original source node
     alias/id and port name, with the reason (source gone / port gone / port now leads elsewhere).
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
