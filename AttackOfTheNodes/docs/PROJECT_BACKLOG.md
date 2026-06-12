# AttackOfTheNodes Project Backlog

## Completed Project — Documentation Modernization

The docs folder previously had split-brain history from the Chrome-extension
concept, tkinter prototype, and current Textual TUI. Phase 10 refreshed the
active reference docs; the 2026-06-09 documentation overhaul then made the docs
task-first and archived deep history.

`docs/README.md` is now the entry point, `TASK_INDEX.md` is the task router,
and `MASTER_BUILD_PLAN.md` is the concise roadmap.

Completed cleanup:

- Refreshed `PROJECT_KNOWLEDGE.md` so it is again safe as the current-state
  single-source overview.
- Rewrote `ARCHITECTURE.md` around the Python/Textual implementation instead of
  the older IndexedDB/Dexie/BackendBridge architecture.
- Rewrote `SIGNAL_FLOW.md` around local backend services, Textual screens, and
  the current event bus.
- Regenerated `FILE_TREE.md` from the current workspace and included the
  standardization/debug-node files.
- Archived historical tkinter roadmap material in `archive/V05_BUILD_PLAN.md`
  so it is available as history without sitting in the default read path.
- Added `UI_QUICK_REFERENCE.md` so routine frontend fixes can start from a
  short current keybinding/config summary instead of the full TUI design file.

Ongoing rule: implementation phases should keep `SESSION_LOG.md` current and
update `MASTER_BUILD_PLAN.md`, `TASK_INDEX.md`, or `AGENT_HANDOFF.md` when
roadmap status or task routes change.

## Planned Project — Backend / Frontend Boundary Cleanup

The backend should remain reusable for future CLI, web, or API frontends.

Use `BACKEND_FRONTEND_BOUNDARY.md` as the plan. Audit refreshed 2026-06-10:
Phase A (frontend tombstone adapter) is done, and `replace_with_tombstone()`,
tombstone-specific `replace_node_type()`, and backend-written
`_timing_invalidated` are already gone.

**Tombstone design decision (2026-06-11):** `tombstone_node` was previously
targeted for Phase B decommission (remove from backend, replace with generic
unknown-type error). That plan has been reversed. `tombstone_node` is now an
intentional backend type — the save-persistent deleted-node record. Saves write
a tombstone with full original node data (type, alias, config, connections)
instead of materializing to a `branch_end_node` with a `_system_role` marker.
This gives undo-after-reload, richer validator error messages, and meaningful
port-validity errors from the original port shape. Phase B decommission is
cancelled. See `BACKEND_FRONTEND_BOUNDARY.md` for the full rationale and
tombstone config contract.

Remaining Phase B work (redefined — frontend migration):

- Update `editor_workflow_adapter.py` to write `tombstone_node` (with full
  original-data config) on save instead of `branch_end_node` with
  `_system_role` marker.
- Migrate any existing saves with `_system_role: "deleted_node_branch_end"`
  `branch_end_node` records to `tombstone_node` format on load.
- Extend the validator's tombstone error block to surface original input and
  output connection context from the tombstone config.
- Confirm `node_identity.py` marks tombstone with `editor_only: True` so
  non-editor frontends can filter it.
- Implement tombstone restore with connection validation and partial restore
  (see below).
- Decide whether layout metadata such as `position` and navigation metadata
  such as `bookmarked` belong in portable workflow saves or editor sidecars
  (Phase C).

**Tombstone restore — connection validation (design spec 2026-06-11):**

Before reconnecting a restored tombstone's stored connections, the frontend
adapter must validate each one because the workflow may have drifted since the
node was deleted. Three drift categories:

- **Upstream output drift:** the source node that fed into the deleted node may
  have removed or renamed its output port, or changed the dead-drop payload type.
- **Downstream input drift:** the target node that received from the deleted node
  may have removed or renamed its input port, or that port may now be occupied
  by a different source.
- **Memory bank drift:** `membank_inputs` the deleted node read may no longer be
  declared by any surviving node's `membank_outputs`.

Restore procedure:
1. Always restore node type, alias, and config — never blocked by connection drift.
2. Per stored input connection: verify source node exists AND declares the
   referenced output port → reconnect if yes, leave unconnected if no.
3. Per stored output connection: verify target node exists AND declares the
   referenced input port AND that port is not already occupied → reconnect if
   all pass, leave unconnected if any fail.
4. Per stored membank input: check if any surviving node declares the variable
   in `membank_outputs` → restore the declaration regardless, but flag if the
   source is missing.
5. Surface a frontend alert after restore if any connections could not be
   re-established, with two named sections:
   - **Input connection errors** — original source node alias + port + reason
     (source gone / port gone).
   - **Output connection errors** — original target node alias + port + reason
     (target gone / port gone / port already occupied).
   - **Memory input warnings** — membank variable names whose declared source is
     no longer present.
6. A partial restore (node back, some connections missing) is always preferred
   over leaving a tombstone. The validator will surface remaining loose ends.

## Near-Term Project — Frontend Command UI Toolkit

Current config and modal UX should converge on small shared helpers instead of
per-screen key handling. `frontend/widgets/command_navigation.py` is the first
step and currently supports command-mode screens. The completed frontend audit
plan is archived at `archive/plans/FRONTEND_AUDIT_BUILD_PLAN.md`; active rules
live in `AGENT_START_GUIDE.md`, `NODE_HELPER.md`, `TASK_INDEX.md`, and
`TUI_DESIGN.md`.

Recommended cleanup:

- Continue using shared command helpers for new modal screens. `SettingsScreen`,
  path prompts, user input, generated config fields, and modal selectors already
  have baseline helper coverage.
- Keep future notification copy routed through `frontend/notifications.py`.
- Keep schema-generated node config as the default path; extend field schemas or
  frontend render helpers before adding per-node custom modal logic.
- Add a focused keyboard-only smoke suite for common modal flows: open, move,
  activate, type, escape typing mode, save/cancel, and scroll to off-screen
  fields.

## Near-Term Project — Helper-Backed UI Standardization

Goal: evolve `aotn_node_helper` from a backend node generator into a guardrail
for repeatable Textual UI work. The recurring failure modes are keyboard
navigation, autoscroll, widget sizing, and dynamic UI that changes after a
checkbox/select/input changes.

Done (2026-06-12):

- `aotn_node_helper/check_ui.py <node_type>` mounts `NodeConfigScreen`, checks
  top-level tab placement for schema fields, verifies generated controls
  participate in keyboard focus, and validates dynamic rule state at mount.
- Generic dynamic-form schema keys `enabled_when`, `visible_when`, and
  `mutually_exclusive_with` are implemented in `form_generator.py`, applied
  live by `NodeConfigScreen` (across tabs), and covered by
  `tests/test_form_rules.py`.
- Helper specs expand the NODE_STANDARDS standard model through
  `input_sources` and `output_routing` sections.
- A config-UI smoke test (`test_<node_type>_ui.py`) is generated for specs
  that use `config_tabs` or the standard sections.

Recommended cleanup:

- Extend the generated UI smoke test to full keyboard simulation: switch tabs
  with A/D, move through fields with W/S, activate with E/Enter, exit edit
  mode, and reach Save/Cancel.
- Consider a `repeats_from` schema key for counted dynamic rows, complementing
  `visible_when`/`enabled_when`.
- Add label/value pairs for select options in `form_generator.py` so backend
  reads stable machine values instead of display strings.
- Add a screen scaffold command for non-node screens. The scaffold should create
  a `CommandScreenMixin` screen with a status bar, visible Cancel control,
  vertical button order, and a generated keyboard-navigation test.
- Add a small UI manifest format for screens and generated config surfaces:
  first focus target, last focus target, scroll container, dynamic controls,
  selection lists, and expected Save/Cancel behavior.
- Make widget sizing testable with mounted-screen assertions: long labels do not
  overflow command controls, dynamic rows do not resize the whole layout, and
  scroll-to-focus keeps the active control visible.
- Keep generated UI support frontend-only. The helper may inspect node metadata
  and generate frontend tests, but backend nodes should not depend on Textual.

## Near-Term Project — Branch Health Visualization

Goal: make branch validity visible while editing, before users need to run full
validation.

Recommended cleanup:

- Derive branch health from workflow structure, not stored UI state.
- Represent at least three branch states:
  - valid branch ending: end/output node or connected Merge Beacon node;
  - branch ended but not merged: Merge Beacon exists but is not connected to a
    Merge node;
  - floating branch: no valid output/end node and no Merge Beacon.
- Surface those states in the editor with clear but restrained color: green for
  valid, yellow/orange for branch-ended-but-unmerged, and red/orange for
  floating/incomplete branches.
- Extend `NodeCard` or a future editor display adapter so branch-health color is
  separate from execution status icons.
- Fold this into the FA-7 visual pass: VS Code-like dark styling, readable node
  type colors, type-specific brackets/icons, larger editor rows, and dimmer
  command text fields when not editing.

## Later Project — Schema-Driven Node UI Expansion

Goal: make adding a node feel like adding backend metadata, not hand-editing
frontend menus.

Recommended cleanup:

- Continue the Phase 17 taxonomy work from
  `PHASE_17_NODE_VISUAL_IDENTITY.md`. The user-facing selector families are
  Inputs, Flow Control, Outputs, and Complex; reusable subcategories should
  carry capabilities such as Triggered, File I/O, Internet, AI, Passive Output,
  Active Output, Parallel, Conditional, Runtime Resource, and Utility.
- Redesign the node library around that taxonomy. Flow Control should
  eventually distinguish always-parallel branch nodes, conditional branch nodes,
  merge/wait nodes, loop nodes, and utility markers instead of forcing all
  branching behavior through one generic node.
- Extend config schema only with generic keys: placeholder text, min/max/step for
  numeric fields, optional blank-select behavior, and multiline height hints.
  Visibility/enablement conditions and mutual exclusion are done (2026-06-12):
  `enabled_when`, `visible_when`, `mutually_exclusive_with`.
- Add tests for every schema key in `frontend/widgets/form_generator.py`.
- Move branch-label generation and pass-through notes toward documented generic
  `ui_hints` where possible.
- Simplify generated config surfaces: ordinary nodes should show only the fields
  they declare, semantic transient input/output metadata, memory-bank sections
  when enabled, and generic topology selectors when required.
- Node author checklist exists in `NODE_STANDARDS.md` (Authoring Checklist
  section); extend it with categories/pass-through/memory-bank specifics as the
  node overhaul progresses.
- Add a validation test that every registered node can mount its generated config
  without frontend custom code unless it is explicitly listed as a structural
  topology editor.

## Later Project — Runtime Resources And Hidden Helper Nodes

Goal: support richer node behavior without making the editor visually noisy.
Visible nodes should stay user-friendly, while reusable utility behavior can be
attached behind the scenes when a node needs it.

Full design note: `archive/plans/RUNTIME_RESOURCE_SESSION.md`

Done — the core `RunSession` is implemented:

- `backend/run_session.py` holds per-run handles (`open_file`,
  `register_resource`, `validate_path`, `close_all`).
- `MasterState` creates the session at run start, passes it to all
  supervisors, and closes it in `_record_run` on every terminal path.
- Nodes reach it through `context.run_session`; `FileReaderNode` is the
  first consumer. The validator checks schema fields hinted with
  `path_hint: "file"` (empty required path = error, missing on disk =
  warning). Coverage lives in `tests/test_run_session.py`.

Remaining design notes:
- Keep the resource session backend-generic. It should not know about Textual,
  OS dialogs, or editor UI. Frontends choose files; nodes receive portable file
  references or session-managed handles through execution context.
- Treat files as a first-class input family during the node overhaul. Nodes can
  accept a selected file path/resource and perform validation before execution.
  Users should see files by their normal names/paths in config; actual open
  handles and access continuity are runtime concerns.
- Consider long-lived listening resources later: keyboard triggers, folders,
  sockets, or other automation inputs. Keep this opt-in and lightweight so idle
  workflows do not hold unnecessary resources.
- Add path-field affordances in config UI: when focus is on a schema field that
  declares a file/path picker hint, show a short placeholder such as
  `choose file` until the user overrides it. The exact key is not final; avoid
  committing to `I` or `X` until the key map is reviewed.
- Introduce hidden helper nodes only as portable workflow structure, not
  frontend-only magic. A visible node may own an internal input-configuration
  helper such as a memory-bank mux, but save files and validation must make the
  helper relationship inspectable and deterministic.
- Support at least two input mux styles:
  - non-gating mux: gathers configured memory/transient inputs when available;
  - gating mux: waits until all configured inputs have updated before allowing
    the visible node to run.
- Let visible nodes expose simple options that configure helper behavior, such
  as `wait for all inputs before running`, while the detailed helper UI can open
  as an "Input Configuration" view.
- Validation must understand hidden helpers so errors point back to the visible
  node and the specific helper setting that caused the problem.
- Execution views should be able to reveal hidden helper activity when debugging,
  but the editor should default to the simpler visible node graph.

## Later Project — Unified Toast / Alert System

The project has `frontend/notifications.py` and frontend screens route common
notifications through it. Add richer toast behavior on top of that helper.

Recommended cleanup:

- Add a frontend alert helper with standard severities, duration defaults, and
  copy conventions.
- Route common actions through named helpers: saved, loaded, validation passed,
  missing selection, destructive action canceled, destructive action completed,
  run started/stopped, import/export failed.
- Add de-duplication for repeated keyboard mistakes such as "No node selected".
- Keep the helper frontend-only; backend services should continue publishing
  structured events, not UI copy.

## Later Project — Backend LLM Chat Session Persistence

Goal: allow a workflow to maintain an active LLM chat session across multiple
node visits, preserving message history so the model retains context between
calls within a run.

Use case: workflows that make several incremental calls to the same LLM for
iterative tasks — refining a document, multi-step reasoning, or accumulating
a conversation — benefit from the model seeing prior turns rather than treating
each node call as a fresh prompt.

Design direction:

- Session handles should live in `RunSession` alongside file handles. A chat
  session is a per-run resource: created on first use, reused by later nodes
  in the same run, and released on run completion.
- Nodes opt into session reuse via a config flag (e.g., `use_chat_session: true`
  and a `session_key` that names the session within the run). Nodes without
  this flag behave as stateless single-call LLM nodes.
- Message history is stored in the session object in `RunSession`, not in
  `MemoryBank`. `MemoryBank` holds the final outputs; the chat session holds the
  intermediate turn history that the LLM provider needs.
- Multiple nodes using the same `session_key` in a run share one history.
  Nodes with different keys maintain independent sessions.
- The validator should warn if a node declares `use_chat_session: true` but
  `RunSession` is not available in the execution context.
- Keep the LLM provider client backend-only. Frontend nodes declare the session
  intent through metadata; the backend resolves the provider and manages
  the connection.
