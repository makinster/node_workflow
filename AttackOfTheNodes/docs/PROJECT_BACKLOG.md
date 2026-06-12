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

The backend should remain reusable for future CLI, web, or API frontends. The
current Textual editor introduced tombstone behavior that is useful visually,
but not inherently an execution-engine concept.

Use `BACKEND_FRONTEND_BOUNDARY.md` as the plan. Audit refreshed 2026-06-10:
Phase A (frontend tombstone adapter) is done, and `replace_with_tombstone()`,
tombstone-specific `replace_node_type()`, and backend-written
`_timing_invalidated` are already gone. New frontend deletes are soft editor
overlays that materialize to marked `branch_end_node` records on save.

Remaining cleanup (Phase B — gated until Phase 17 selector/editor work
settles; see the coordination gate in `BACKEND_FRONTEND_BOUNDARY.md`):

- Deregister `tombstone_node` from `backend/nodes/__init__.py` and delete the
  class, once old-save handling for legacy `tombstone_node` records is
  decided.
- Replace tombstone-specific backend validator copy with the generic
  unknown-type error.
- Remove the `tombstone_node` entry from `backend/node_identity.py`.
- Decide how old saves containing `tombstone_node` load (adapter migration
  vs. unknown-type placeholder rendering).
- Decide whether layout metadata such as `position` and navigation metadata
  such as `bookmarked` belong in portable workflow saves or editor sidecars
  (Phase C).

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

Recommended cleanup:

- Add `aotn_node_helper/check_ui.py <node_type>` that mounts
  `NodeConfigScreen`, checks top-level tab placement for schema fields, and
  verifies all generated controls are reachable with command navigation.
- Generate a UI smoke test when a node spec uses `config_tabs`: switch tabs with
  A/D, move through fields with W/S, activate with E/Enter, exit edit mode, and
  reach Save/Cancel.
- Introduce generic schema keys for dynamic sections, for example
  `visible_when`, `enabled_when`, or `repeats_from`, then test them in
  `form_generator.py` before using them in node specs.
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
  numeric fields, optional blank-select behavior, multiline height hints, and
  section visibility conditions.
- Add tests for every schema key in `frontend/widgets/form_generator.py`.
- Move branch-label generation and pass-through notes toward documented generic
  `ui_hints` where possible.
- Simplify generated config surfaces: ordinary nodes should show only the fields
  they declare, semantic transient input/output metadata, memory-bank sections
  when enabled, and generic topology selectors when required.
- Create a "node author checklist" in docs: metadata, schema, ports, categories,
  pass-through behavior, memory-bank declarations, and expected generated UI.
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

`get_resource(key)` is already implemented — retrieves a previously registered
handle by key (see `tests/test_run_session.py::test_register_and_get_resource`).
Nodes that receive a typed vault reference key will call
`context.run_session.get_resource(ref_key)` to resolve the actual Python handle.

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

## Near-Term Project — Typed Vault Entries and AI Session Handles

Architecture finalized 2026-06-11. No implementation has landed yet.

**Typed vault entries.** `MemoryBank` (the Vault) gains a `type` field on
every entry. Types at minimum: `string`, `number`, `boolean`, `file`,
`ai_session`. Existing `string`/`number`/`boolean` entries remain pure JSON
values — behavior unchanged. `file` and `ai_session` entries store the type
tag plus a string reference key; the actual Python handle (file object or AI
provider session) lives in `RunSession` and is retrieved by calling
`context.run_session.get_resource(ref_key)`.

From the user's perspective the type is invisible; they see `filename (file)`
or `chat_name (ai_session)` in the Vault dropdown.

**Input dropdown type filtering.** Config dropdowns that select a Vault source
filter by declared input type. An input that accepts `file` shows only `file`
entries; an LLM continuation input shows only `ai_session` entries. This
prevents type mismatches and keeps the Vault navigable as it grows.

**AI session as config-driven output on LLM nodes.** There is no separate Chat
Session Node. Any LLM node can opt into session persistence via a config
checkbox ("keep active AI session") and a user-supplied session key. When
checked and the node executes:
- A `(type: ai_session, ref_key: <session_key>)` entry is written to the Vault.
- The session handle (provider client + message history) is registered in
  `RunSession` under that key.

Downstream LLM nodes that select the same Vault key append their turn to the
existing history. The first node with a given key starts the session; all
subsequent nodes continue it. Message history lives in the session object in
`RunSession`, not in `MemoryBank`. `MemoryBank` holds only the type tag and
reference key.

**Validator error/warning split.** Applies uniformly to all typed vault
references (string, number, file, ai_session):
- Error: no node in the workflow declares the vault key at all. Structurally
  impossible at runtime. Blocks the workflow.
- Warning: a node declares the key but lives on a parallel branch where
  execution order cannot be guaranteed. Recommend a Wait Until node or branch
  merge before the key is read or written.

The validator must not infer timing from node count, node type, or branch
depth. Static analysis cannot know which branch is slower. Warning plus
Wait Until guidance is the correct ceiling.

**Work items:**
- Add `type` field to `MemoryBank` vault entries.
- Add `get_resource(key)` to `RunSession`.
- Add "keep active AI session" checkbox and session key field to LLM node
  config.
- Add Vault write path for `ai_session`-typed entries on LLM node execute.
- Extend input source dropdowns to filter by declared input type.
- Extend validator to cover typed vault reference ordering (error/warning split).

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
