# AttackOfTheNodes Master Build Plan

**Last updated:** 2026-06-12
**Project root:** `AttackOfTheNodes/`
**Runtime:** Python 3.14, Textual 8.2.7, asyncio, JSON persistence

This is the concise active roadmap. Completed phase details were collapsed into
`archive/BUILD_PLAN_HISTORY.md` during the documentation overhaul.

## Current State

AttackOfTheNodes is a Python workflow engine with a Textual terminal UI.
Workflows are directed node graphs. A `MasterState` starts runs, supervisors
walk execution paths, branching nodes spawn branch supervisors, and all
supervisors share a per-run `MemoryBank`.

Runs now also own a backend `RunSession` for per-run resource handles. It is
created by `MasterState`, passed through `NodeContext`, and closed on every run
terminal path. `FileReaderNode` is the first consumer; workflow saves still
store plain path strings.

The backend is UI-agnostic. Frontend-only behavior belongs under `frontend/`.
Read `BACKEND_FRONTEND_BOUNDARY.md` before adding backend code for editor/UI
needs.

## Current Active Work

Phase 17 is in progress. It establishes node visual identity and selector
taxonomy before the next node-library overhaul: primary node families,
subcategory filters, metadata exposure, and editor rows that make node roles
scannable without changing runtime behavior. The feature surface is
implemented, but live-TUI verification found rendering bugs, so the phase
stays open until the editor view is verified clean in the running app.

Completed in Phase 17 so far:

- `NodeFactory.get_node_types_metadata()` exposes portable identity metadata:
  family/category, legacy category, subcategory tags, icon name, and color hint.
- Registered nodes have transitional Phase 17 metadata.
- The current saved `branch_node` is user-facing as **Parallel Branch** and
  carries the `Parallel` subcategory, reserving `Conditional` for a later
  dedicated node.
- `NodeSelectorScreen` has family tabs, tab-specific subcategory checkbox
  filters with `AND` semantics, and command-mode search activation.
- Editor rows render two-line family/subcategory identity with aligned frames,
  truncation, quiet utility styling, and preserved Merge Beacon health colors.
- The editor details panel shows full primary family and subcategory metadata.
- Focused tests cover metadata exposure, selector filtering, row rendering,
  details-panel identity, truncation, and keyboard/selection stability.

Remaining Phase 17 work:

- Fix live-TUI rendering bugs found after the implementation pass. First bug
  (fixed): identity rows padded text to a fixed 48-char width, so narrower
  node-list panels soft-wrapped the closing frame onto its own line and pushed
  the family/subcategory line out of the two-line row; rows now re-fit to the
  rendered panel width on resize.
- Manually verify the editor view in the running app at several terminal
  widths: two-line rows, aligned frames, identity line visible, selection
  highlight, and branch selector rows.
- Keep future runtime-resource expansion and node-library redesign work
  separate from the Phase 17 visual identity foundation.

Read `PHASE_17_NODE_VISUAL_IDENTITY.md` before implementing selector, node row,
or node metadata changes for this phase.

## Phase Status

| Phase | Title | Status |
|---|---|---|
| 0 | Memory leak fixes | Done |
| 1 | Forward-reachability helper | Done |
| 2 | Dependency list + validation | Done |
| 3 | Membank I/O + registry + descriptions | Done |
| 4 | Delete + insert nodes | Done |
| 4.5 | Config modal and selector usability | Done |
| 5 | Config tabs | Done |
| 5.5 | Keyboard nav hardening + config modal UX | Done |
| 6 | Breakpoints | Done |
| 7 | Per-node execution timing | Done |
| 8 | Completion registry + wait-until node | Done |
| 9 | Merge dynamic list + lineage barrier | Done |
| FA-0..FA-5 | Frontend standardization helpers | Done |
| 10 | Documentation modernization | Done |
| 10.5 | Backend/frontend boundary cleanup (Phase A) | Done |
| 10.6 | Tombstone design decision + Phase B migration | Planned |
| 11 | Real AI node execution | Deferred |
| 12 | Packaging and release hardening | Deferred |
| 13 | Cursor model foundation | Done |
| 14 | Key binding remap | Done |
| 15 | Editor rework | Done |
| 16 | File modal + node config tabs | Done |
| Docs | Task-first documentation overhaul | Done |
| 17 | Node visual identity + selector taxonomy | In progress |
| 18 | Acceleration + help rewrite | Planned |
| 19 | Nested workflows: built-in subworkflow node | Planned |
| 20 | Nested workflows: user-created subworkflows | Planned |

## Recently Completed

- Task-first docs overhaul: `README.md`, `TASK_INDEX.md`, active roadmap, and
  archived historical build/session detail.
- Node helper generator at `../aotn_node_helper/`.
- Generated node specs support `config_tabs` for Source / Parameters / Payloads.
- `NodeConfigScreen` honors schema `tab` hints.
- Focused generated-node tests live under `tests/generated/`.
- Dynamic-form schema keys `enabled_when`, `visible_when`, and
  `mutually_exclusive_with` are implemented in the form generator and applied
  live by `NodeConfigScreen`, including across tabs (2026-06-12).
- Helper specs expand the NODE_STANDARDS input/output model via
  `input_sources` / `output_routing`; `check_ui.py` and generated config-UI
  smoke tests verify tab placement, focus, and rule state (2026-06-12).
- Branch config v1 supports 2-5 always-parallel spawn points and per-branch
  seed payloads.
- Merge Beacon is the user-facing name for persisted `branch_end_node`.
- File import/export uses picker-first behavior with typed-path fallback.
- RunSession backend resource lifecycle is implemented and verified. File
  reader nodes use it when available; path validation uses schema
  `path_hint: "file"`.
- Phase 17 metadata exposure and selector taxonomy are implemented. The
  selector now browses by Inputs / Flow Control / Outputs / Complex and filters
  by tab-specific subcategories.
- Phase 17 editor row identity and details-panel identity are implemented and
  covered by focused tests.

See `SESSION_LOG.md` for recent entries and `archive/SESSION_LOG_HISTORY.md`
for older entries.

## Current Phase: Phase 17 — Node Visual Identity + Selector Taxonomy

Goal: make the node library easier to browse and editor rows easier to scan,
while laying the metadata foundation for the planned node overhaul.

Done:

- Primary selector tabs: Inputs, Flow Control, Outputs, Complex.
- Multi-subcategory metadata and filters such as Triggered, File I/O, Internet,
  AI, Passive Output, Active Output, Parallel, Conditional, Runtime Resource,
  and Utility.
- Node selector keeps string search, adds tab-specific subcategory checkboxes,
  initially highlights the first subcategory control, and uses command-mode
  activation for search.
- Subcategory filters use `AND` semantics.
- Editor rows use two-line alias plus family/subcategory identity with aligned
  frames and truncation for long identity text.
- The details panel shows full primary family and all subcategories.
- Utility/debug/pass-through nodes render more quietly, while validation,
  breakpoint, execution, and Merge Beacon health states retain priority.

Remaining:

- Live-TUI verification and bug fixing. The implementation pass looked done in
  tests, but running the app surfaced rendering bugs (fixed so far: identity
  rows wrapped their closing frame and lost the identity line in panels
  narrower than the old fixed 48-char text width).

Current todo:

- Manually verify editor rows in the running app at several terminal widths
  before closing the phase: two-line rows, aligned frames, visible identity
  line, selection highlight, and branch selector rows.
- Begin Phase 18 only after the live editor view is verified clean.
- Keep future runtime-resource expansion separate from Phase 17 visual work.

Planning reference:

- `PHASE_17_NODE_VISUAL_IDENTITY.md`

Likely files:

- `backend/node_base.py`
- `backend/node_factory.py`
- `frontend/screens/node_selector.py`
- `frontend/widgets/node_card.py`
- `frontend/widgets/node_list.py`
- `frontend/styles.tcss`
- `tests/test_debug_nodes.py`

Focused checks:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"
```

## Later Roadmap

- **Phase 18 — Acceleration + help rewrite.** Hold-to-accelerate navigation,
  context-aware help polish, and a sweep for non-interactive nav stops.
- **Phase 19 — Built-in subworkflow node.** Run a saved workflow as a child
  supervisor from one node.
- **Phase 20 — User-created subworkflow nodes.** Publish workflows as reusable
  nodes with dependency/export policy.
- **Typed vault entries and AI session handles.** Add `type` field to
  `MemoryBank` vault entries (`string`, `number`, `boolean`, `file`,
  `ai_session`). `get_resource(key)` on `RunSession` is already implemented. Add config-driven
  "keep active AI session" output to LLM nodes (no separate Chat Session Node).
  Extend input source dropdowns to type-filter by declared input type. Extend
  the validator with the error/warning split for typed vault reference ordering.
  Architecture finalized 2026-06-11; see `PROJECT_BACKLOG.md` and
  `NODE_STANDARDS.md` for the full design.
- **Deferred AI integration.** Implement real AI node execution once UI and
  node authoring conventions stabilize. Typed vault entry support is a
  prerequisite for AI session continuation.

## Standing Implementation Rules

- Start at `README.md`, then use `TASK_INDEX.md` for the task route.
- Keep backend/frontend boundaries strict.
- Prefer node metadata and helper specs over custom config UI.
- Use focused `pytest -k` slices for small fixes, then full suite before broad
  runtime/shared UI commits.
- Update `SESSION_LOG.md` after each completed change.
- Update `DOCS_MIGRATION_NOTES.md` when docs are moved, collapsed, archived, or
  deleted.
