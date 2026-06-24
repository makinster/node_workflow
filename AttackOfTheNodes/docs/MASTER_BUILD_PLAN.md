# AttackOfTheNodes Master Build Plan

**Last updated:** 2026-06-15
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
- Editor rows render two-line family/subcategory identity inside ASCII boxes,
  with truncation, the depth gutter outside the box, default node backgrounds,
  and preserved Merge Beacon state indicators.
- The editor details panel shows full primary family and subcategory metadata.
- Focused tests cover metadata exposure, selector filtering, row rendering,
  details-panel identity, truncation, and keyboard/selection stability.

Taxonomy revision (2026-06-12): five backend families (`Inputs`, `Outputs`,
`Flow Control`, `Utility`, `Complex`) mapped onto four selector tabs — `I/O`
(Input/Output switch), `Flow Control`, `Utility`, `Complex`. AI became a
subcategory, not a family. Filters reduced to I/O (`File I/O`/`Internet`/`AI`)
and Complex (`AI`). In-list section headers organize tabs; keyboard nav skips
them. Start/End removed from the user-facing taxonomy (terminate-branch
config on outputs + End Branch node). Full inventory in `NODE_CATALOG.md`.

Implemented for the revision (2026-06-12): `group` / `selector_section`
metadata exposure, five-family remap with `Utility` editor styling, the
four-tab selector with I/O switch, section headers, reduced filters, the
generic Group Picker modal with auto-promotion and ESC-returns-to-selector,
selector hiding of `start_node`/`end_node`, and node helper validation for
the new families and fields.

Remaining Phase 17 work:

- Manually verify the selector (tabs, switch, headers, picker) and the
  editor view in the running app at several terminal widths: two-line rows,
  aligned frames, identity line visible, selection highlight, and branch
  selector rows. (First rendering bug already fixed: identity rows now
  re-fit to the rendered panel width on resize.)
- Keep future runtime-resource expansion and node-library redesign work
  separate from the Phase 17 visual identity foundation.
- Keep backend-feature UI surfacing separate from Phase 17. Current gaps are
  tracked in `PROJECT_BACKLOG.md` under "Backend Features Not Yet Surfaced In
  UI" (run history browser, secrets UI, tombstone restore alerts, branch-health
  indicators, schema file pickers, memory snapshot save/load choices, workflow
  rename/bookmarks, and error clearing controls).

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
| 10.6 | Tombstone design decision + Phase B migration | Done (restore-alert UI + Phase C metadata deferred) |
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

- Backend/edit-time performance: fixed two O(n^2) hot spots — the
  `MEMORY_UPDATE` full-store snapshot (`memory_bank.py`) and the per-mutation
  workflow-cache deepcopy (`workflow_map.py`). Per-node execution overhead is
  ~15 us/node and linear; a C rewrite is not warranted. Remaining lower-leverage
  optimizations are deferred under `PROJECT_BACKLOG.md` → "Backend Execution &
  Edit-Time Performance" (2026-06-13).
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
- SecretsManager module (2026-06-13): plain-text JSON store at
  `secrets/secrets.json`; wired through `MasterState → Supervisor → NodeContext`;
  nodes call `context.get_secret(key_name)`. Validator checks secret-ref fields
  (`"secret": True` schema hint). Schema supports at-rest encryption as a
  one-module upgrade.
- Backend build plan Phases 1–6 (2026-06-13): tombstone `editor_only` flag and
  validator port context; legacy save migration; typed vault MemoryBank API;
  LLM chat session foundation in `RunSession`; parallel-branch vault race
  warnings; four utility nodes (TextTransform, JsonPath, RandomNumber, HttpRequest)
  via `aotn_node_helper`.
- Headless build plan H1–H5 (2026-06-13), backlog work verifiable with pytest
  alone (no live-TUI): saves write `tombstone_node` directly with full
  original data (H1); `restore_tombstone()` with connection validation and
  partial restore returning a `TombstoneRestoreReport` (H2); `"secret": True`
  fields on the four API-key nodes plus `SecretsManager` wired into editor
  validation (H3); label/value select options and full schema-key test
  coverage in `form_generator.py` (H4); `backend/branch_health.py` deriving
  per-branch `valid`/`ended_unmerged`/`floating` state (H5). Plan and outcome
  in `archive/plans/HEADLESS_BUILD_PLAN.md`. Deferred UI pieces (tombstone
  restore alert, Secrets settings tab, branch-health colours) remain in
  `PROJECT_BACKLOG.md`.

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
- Core Simplification Rule documented: when to group vs separate types vs
  mode-select vs direct-add. See `PHASE_17_NODE_VISUAL_IDENTITY.md` and
  `NODE_STANDARDS.md`.
- Taxonomy revised (2026-06-12): five families / four tabs with I/O switch,
  AI as subcategory, section headers, reduced filters, Start/End removal,
  AI Input node design, curated AI supported-model approach. Full node
  inventory (Live/Planned/Deferred/Concept) created in `NODE_CATALOG.md`.
- Two-level group picker design documented: main selector with group counts,
  generic Group Picker second modal, auto-promotion rule, `ESC` behavior,
  search-dissolves-groups behavior, keyboard flows.

Remaining:

- Live-TUI verification of the restructured selector (tabs, I/O switch,
  headers, group picker) and editor rows at several terminal widths before
  closing the phase (first rendering bug already fixed: rows re-fit to
  panel width).
- Begin Phase 18 only after the live editor view is verified clean.

Planning reference:

- `PHASE_17_NODE_VISUAL_IDENTITY.md`
- `NODE_CATALOG.md`

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
- **Typed vault entries and AI session handles.** Backend foundation done
  (2026-06-13): `MemoryBank.store_persistent` accepts `type_tag`; `read_persistent_by_type`
  added; validator warns on ai_session type mismatch and parallel-branch races;
  `RunSession` has multi-turn chat session API. Remaining: config-driven "keep
  active AI session" checkbox on LLM nodes; Vault write path for `ai_session`
  entries on execute; input source dropdowns filter by type. See
  `PROJECT_BACKLOG.md` and `NODE_STANDARDS.md` for full design.
- **Deferred AI integration.** Implement real AI node execution once UI and
  node authoring conventions stabilize. Typed vault entry support is a
  prerequisite for AI session continuation.
- **Phase N — Headless CLI execution.** `aotn <workflow name>` entrypoint,
  headless-safe node contract (validator blocks non-headless nodes), configurable
  data directory, Input nodes accept CLI args, Output nodes write to stdout/file.
  See `PROJECT_BACKLOG.md` → "Future Direction — Headless CLI Execution".
- **Phase N+1 — Always-running trigger watcher.** Trigger node primitives (async
  listeners, exempt from `node_timeout_seconds`), loop/cycle workflow support,
  non-terminal resource lifecycle, nested workflow fire-and-forget dispatch.
  Depends on Phase N and nested workflows (19/20). See `PROJECT_BACKLOG.md` →
  "Future Direction — Always-Running Trigger Watcher".
- **Phase N+2 — Multi-frontend backend API layer.** Backend as a standalone
  HTTP + WebSocket server; TUI, Chrome extension, and desktop GUI as thin
  clients. See `PROJECT_BACKLOG.md` → "Future Direction — Multi-Frontend
  Expansion".

## Standing Implementation Rules

- Start at `README.md`, then use `TASK_INDEX.md` for the task route.
- Keep backend/frontend boundaries strict.
- Prefer node metadata and helper specs over custom config UI.
- Use focused `pytest -k` slices for small fixes, then full suite before broad
  runtime/shared UI commits.
- Update `SESSION_LOG.md` after each completed change.
- Update `DOCS_MIGRATION_NOTES.md` when docs are moved, collapsed, archived, or
  deleted.
- Keep EventBus payloads JSON-serializable — no Textual widgets, Python handles,
  or reactive references in event data.
- All new event payloads must carry `run_id` for future multi-run isolation.
