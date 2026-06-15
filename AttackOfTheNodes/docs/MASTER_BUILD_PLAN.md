# AttackOfTheNodes Master Build Plan

**Last updated:** 2026-06-14
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

Phase 17 is still in progress. It is establishing node visual identity and
selector taxonomy before the next node-library overhaul: primary node families,
subcategory filters, metadata exposure, and editor rows that make node roles
scannable without changing runtime behavior.

Completed in Phase 17 so far:

- `NodeFactory.get_node_types_metadata()` exposes portable identity metadata:
  family/category, legacy category, subcategory tags, icon name, and color hint.
- Registered nodes have transitional Phase 17 metadata.
- The current saved `branch_node` is user-facing as **Parallel Branch** and
  carries the `Parallel` subcategory, reserving `Conditional` for a later
  dedicated node.
- `NodeSelectorScreen` has family tabs, tab-specific subcategory checkbox
  filters with `AND` semantics, and command-mode search activation.
- Editor rows render two-line family/subcategory identity inside individual
  bordered text boxes, with truncation, quiet utility styling, and preserved
  Merge Beacon health colors.
- The editor details panel shows full primary family and subcategory metadata.
- Focused tests cover metadata exposure, selector filtering, row rendering,
  details-panel identity, truncation, and keyboard/selection stability.

Remaining Phase 17 work:

- Keep the active docs aligned with the true Phase 17 status and current
  frontend/backend support gaps.
- Decide whether the currently discovered frontend support gaps belong in the
  Phase 17 closeout, Phase 18 acceleration/help work, or separate backlog
  slices.
- Keep future runtime-resource expansion and node-library redesign work
  separate from the Phase 17 visual identity foundation unless a small UI
  affordance is needed for an already-exposed backend metadata hint.

Current frontend/backend support gaps discovered during the Phase 17 audit:

- No run-history browser: the backend persists run summaries, outputs, errors,
  and timings, but the UI only exposes the current run.
- No generic file picker for node config fields with schema
  `path_hint: "file"`; `FileReaderNode.file_path` is still a typed text field.
- No UI for `SaveManager` memory-state save/load options
  (`include_memory`, `restore_execution`); decide whether to expose or keep
  dormant.
- No UI for `WorkflowMap` rename, cached open-workflow switching, or bookmark
  navigation.
- No UI action for clearing persisted run errors.

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
| 10.5 | Backend/frontend boundary cleanup | Done |
| 11 | Real AI node execution | Deferred |
| 12 | Packaging and release hardening | Deferred |
| 13 | Cursor model foundation | Done |
| 14 | Key binding remap | Done |
| 15 | Editor rework | Done |
| 16 | File modal + node config tabs | Done |
| Docs | Task-first documentation overhaul | Done |
| 17 | Node visual identity + selector taxonomy | In Progress |
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

## Active Phase: Phase 17 — Node Visual Identity + Selector Taxonomy

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
- Editor rows use two-line alias plus family/subcategory identity inside
  individual bordered text boxes, with truncation for long identity text.
- The details panel shows full primary family and all subcategories.
- Utility/debug/pass-through nodes render more quietly, while validation,
  breakpoint, execution, and Merge Beacon health states retain priority.

Remaining:

- Triage and schedule the current frontend/backend support gaps listed above.
- Keep the Phase 17 completion criteria honest: metadata exposure, selector
  filtering, row identity, and details identity are implemented, but the phase
  remains open while the current gap audit is being folded into the roadmap.

Current todo:

- Update any stale active docs that still call Phase 17 complete.
- Choose the first UI gap to implement or explicitly defer.
- Keep future runtime-resource expansion separate from Phase 17 visual work
  unless it is limited to frontend affordances for existing schema metadata.

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
- **Deferred AI integration.** Implement real AI node execution once UI and
  node authoring conventions stabilize.

## Standing Implementation Rules

- Start at `README.md`, then use `TASK_INDEX.md` for the task route.
- Keep backend/frontend boundaries strict.
- Prefer node metadata and helper specs over custom config UI.
- Use focused `pytest -k` slices for small fixes, then full suite before broad
  runtime/shared UI commits.
- Update `SESSION_LOG.md` after each completed change.
- Update `DOCS_MIGRATION_NOTES.md` when docs are moved, collapsed, archived, or
  deleted.
