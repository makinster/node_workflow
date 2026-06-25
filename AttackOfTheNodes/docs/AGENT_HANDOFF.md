# AttackOfTheNodes Agent Handoff

## Current State

The active app is `AttackOfTheNodes/`, a Python/Textual workflow editor and
execution TUI backed by an asyncio workflow engine. Backend services stay
UI-agnostic; frontend behavior lives under `frontend/`.

The current active work is Phase 17: node visual identity and selector
taxonomy. The phase should align editor row identity, selector tabs,
subcategory filters, and node metadata before the planned node-library
overhaul.

A design decision on 2026-06-11 reversed the Phase B tombstone decommission
plan: `tombstone_node` stays as an intentional backend type — the
save-persistent deleted-node record. Phase B is now a frontend migration task
(update save path from `branch_end_node` marker to `tombstone_node` with full
original data, extend validator errors). See `BACKEND_FRONTEND_BOUNDARY.md`.

## Start Here

1. `docs/README.md` — task router.
2. `docs/TASK_INDEX.md` — minimum docs, likely files, focused checks.
3. `docs/SESSION_LOG.md` — recent changes.
4. `docs/MASTER_BUILD_PLAN.md` — concise roadmap/status.
5. `docs/BACKEND_FRONTEND_BOUNDARY.md` — required before backend changes
   motivated by UI behavior.

## Current Documentation Shape

- Active docs are concise and current-state oriented.
- Full completed build-plan detail is archived in
  `docs/archive/BUILD_PLAN_HISTORY.md`.
- Full older session history is archived in
  `docs/archive/SESSION_LOG_HISTORY.md`.
- Historical tkinter/proof-of-concept planning is archived in
  `docs/archive/V05_BUILD_PLAN.md`.
- Completed/lower-priority planning docs are under `docs/archive/plans/`.
- `docs/DOCS_MIGRATION_NOTES.md` records why docs were moved or collapsed.
- `docs/PHASE_17_NODE_VISUAL_IDENTITY.md` records the active taxonomy and UI
  direction for selector/editor identity work.

## Project Status

Completed major phases:

- Runtime phases 0 through 9.
- Frontend audit/helper phases FA-0 through FA-5.
- Documentation modernization and backend/frontend boundary cleanup.
- Cursor model foundation, key binding remap, editor rework, and File/config
  polish through Phase 16.
- Node helper generator and focused generated-node test workflow.

Active product phase:

- Phase 17: Node visual identity and selector taxonomy.

Phase 17 direction (taxonomy revised 2026-06-12):

- Five backend families: Inputs, Outputs, Flow Control, Utility, Complex.
- Four selector tabs: I/O (Input/Output switch maps the Inputs and Outputs
  families onto one tab), Flow Control, Utility, Complex.
- AI is a subcategory tag, not a family. Filters exist only on the I/O tab
  (File I/O / Internet / AI) and Complex (AI).
- Selector lists use in-list section headers that keyboard navigation skips,
  group entries with member counts that open a generic Group Picker modal,
  and a string filter that dissolves groups/headers while active.
- New frontend-only metadata fields: `group` and `selector_section`.
- Editor rows may become two-line rows showing alias first, then family and
  high-signal subcategories.
- Full node inventory with statuses lives in `NODE_CATALOG.md`; read
  `PHASE_17_NODE_VISUAL_IDENTITY.md` before selector/taxonomy work.

Deferred:

- Backend features that need frontend surfacing: run history browser, secrets
  settings UI, tombstone restore warning alert, branch-health indicators,
  schema-driven file pickers in node config, memory snapshot save/load choices,
  workflow rename/bookmark controls, and error clearing controls. See
  `PROJECT_BACKLOG.md` before starting any of these.
- Real AI node execution.
- Packaging/release hardening.
- Nested workflow phases 19 and 20.

## Long-Range Direction

Three planned expansions that should shape current build decisions. Full design
notes and "what to avoid now" guidance live in `PROJECT_BACKLOG.md` under the
corresponding "Future Direction" sections.

- **Headless CLI execution (`aotn`).** "Save for headless" exports a duplicate
  file where TUI I/O nodes are swapped for headless twins with identical port
  shapes — graph topology preserved, only the I/O boundary nodes change. Twins
  default to stdin-prompted interaction (format inherited from node type: free
  text, single-index, or comma-separated multi-index). Optional `headless_input_mode`
  config enables CLI arg or static-default modes for automation. Nodes with no
  declared twin block the export with a clear error. Start node redesign
  introduces `HeadlessStartNode` (CLI preamble — banner, global session prompts,
  pre-flight setup) and `NestedStartNode`/`TriggerStartNode` for other contexts;
  all variants share the same downstream port shape. Nested workflows are treated
  as black boxes — validator checks `headless_valid` flag and port compatibility
  only, does not re-traverse internals. See `PROJECT_BACKLOG.md`.
- **Metadata conditional nodes.** A new node group (Flow Control → Context
  Branching) that branches on run-time execution context: `ExecutionModeConditionalNode`
  (`tui`/`headless`/`nested`/`triggered`) and `RunMetadataConditionalNode`
  (arbitrary context keys). Enables single workflows to handle multiple execution
  modes without a separate export. Validator softening rule: TUI-only nodes
  behind a correct context gate are warnings, not errors; TUI-only nodes with
  no gate in a headless-flagged workflow are still errors. Complementary to
  compile-and-swap, not a replacement. See `PROJECT_BACKLOG.md`.
- **Always-running trigger watcher.** A non-terminating headless workflow that
  monitors for external events and dispatches sub-workflows. Requires trigger
  nodes (exempt from `node_timeout_seconds`), loop/cycle workflow support,
  non-terminal resource lifecycle, and sub-workflow execution isolation. Depends
  on headless CLI and nested workflows (Phases 19/20).
- **Multi-frontend expansion.** TUI, Chrome extension, and desktop GUI as thin
  clients to a shared backend HTTP + WebSocket server. The backend/frontend
  separation already holds; the eventual shift is extracting the backend into
  its own process.

**Invariants that must hold across all future directions — verify on every
change:**

1. No frontend imports in backend code (`from frontend...` in any node or
   backend service is a permanent regression).
2. EventBus payloads stay JSON-serializable — no Python objects, Textual
   widgets, or reactive references in event data.
3. No non-serializable Textual state stored on `MasterState`.
4. All new event payloads carry `run_id` — required for future multi-run and
   multi-frontend event isolation.

## Working Rules

- Do not revert unrelated dirty/untracked files.
- Use `TASK_INDEX.md` to choose the smallest useful reading set.
- Ordinary nodes should be metadata-driven and generated through
  `../aotn_node_helper/` when practical.
- Backend code must not import from `frontend`.
- Before UI-motivated backend changes, read `BACKEND_FRONTEND_BOUNDARY.md`.
- Before Phase 17 selector/editor work, read
  `PHASE_17_NODE_VISUAL_IDENTITY.md`.
- Use focused `pytest -k` checks for small fixes; run the full relevant suite
  before broad runtime/shared UI commits.
- Update `SESSION_LOG.md` and, for doc moves/collapses,
  `DOCS_MIGRATION_NOTES.md`.

## Verification Pattern

From `AttackOfTheNodes/`:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "<focused_behavior>"
```

For docs-only work from the workspace root:

```bash
git diff --check
rg -n "<stale-folder-or-phase-pattern>" AttackOfTheNodes/docs AGENTS.md
find AttackOfTheNodes/docs -type f -name '*.md' | sort
```
