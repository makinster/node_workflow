# AttackOfTheNodes Comprehensive Build Plan

**Last updated:** 2026-05-31
**Project root:** `attackofthenodes_v05/`
**Runtime:** Python 3.14, Textual 8.2.7, asyncio, JSON persistence
**Current branch context:** Textual TUI spinoff; tkinter frontend is obsolete.

This is the active build plan and handoff source for the project. It merges the
current phase plan, the Textual TUI design notes, the agent working rules, and
the older architecture docs into one current-state reference.

Older docs in this folder remain useful as history, but several still describe
the Chrome-extension or tkinter eras. When documents conflict, prefer this file,
then `docs/AGENT_HANDOFF.md`, then `docs/SESSION_LOG.md`, then
`docs/TUI_DESIGN.md`.

---

## 1. Current Mental Model

Think of AttackOfTheNodes as a factory floor with a control room:

- The backend is the factory floor. Nodes are machines arranged in directed
  workflows, and supervisors walk execution paths through those nodes.
- The frontend is the control room. It displays workflow structure, execution
  state, memory, outputs, errors, settings, and editing surfaces.
- A workflow is a recipe: nodes plus connections. Execution starts at a start
  node, follows output connections, and can fork into multiple supervisors.
- All supervisors in a run share one `MemoryBank` and report back through
  `WorkflowMasterState` and the event bus.

The active frontend is Textual. The old tkinter modules and any older
browser/IndexedDB/HandleUI references are historical only.

---

## 2. Active Architecture

### Backend

- `backend/persistence.py`: local JSON persistence for workflows, settings,
  run history, run outputs, and run errors.
- `backend/configuration_manager.py`: settings cache and schema gatekeeper.
- `backend/workflow_map.py`: live workflow cache, node CRUD, connection
  operations, dirty tracking, traversal helpers, and save serialization.
- `backend/node_factory.py`: executable node registry and config templates.
- `backend/node_base.py`: `Node`, `NodeContext`, metadata validation, config
  schema contract, and node category support.
- `backend/memory_bank.py`: per-run persistent variables and transient port
  data.
- `backend/output_manager.py`: durable output collection and finalization.
- `backend/supervisor.py`: one execution path through the graph.
- `backend/master_state.py`: run coordinator, branch spawning, global pause,
  user input routing, run completion, and run history recording.
- `backend/save_manager.py`: assembles complete workflow save/export data.
- `backend/validator.py`: preflight validation and derived input-source checks.
- `backend/error_handler.py`: structured error logging and run cleanup.
- `backend/field_types.py` and `backend/node_category.py`: shared schema and
  node-classification constants.

Backend code must stay UI-agnostic. Do not import from `frontend/`.

### Frontend

The live UI is a Textual app:

```text
frontend/
  app.py
  styles.tcss
  ui_state.py
  screens/
    editor.py
    execution.py
    branch_selector.py
    node_selector.py
    node_config.py
    confirm.py
    workflow_library.py
    user_input.py
    memory_viewer.py
    output_viewer.py
    error_details.py
    settings.py
    help.py
  widgets/
    form_generator.py
    node_list.py
    node_card.py
    status_bar.py
```

Frontend code adapts to backend services through screen-level adapters and
widgets. UI convenience belongs in the frontend unless there is a genuine engine
capability missing.

### Execution Flow

1. Load or create a workflow in `WorkflowMap`.
2. Validate structure with `validator.py`.
3. Start a run through `WorkflowMasterState`.
4. Root `WorkflowSupervisor` starts at the start node.
5. Supervisors prepare node inputs from transient memory and branch data.
6. Nodes execute and signal completion, error, wait, or branches.
7. Branching nodes request branch supervisors through master state.
8. Nodes write transient data and optional memory-bank outputs.
9. Output nodes and end nodes feed run output records.
10. Master state finalizes output, errors, and run history when supervisors end.

---

## 3. Standing Instructions

Before coding:

1. Read `docs/AGENT_HANDOFF.md`.
2. Read `docs/SESSION_LOG.md` for the latest completed phase.
3. Read the phase-specific docs:
   - Frontend work: `docs/TUI_DESIGN.md`.
   - Engine work: this file plus the relevant backend modules.
   - Docs modernization: `docs/PROJECT_BACKLOG.md`.

While coding:

- Keep backend and frontend boundaries strict.
- Use `backend.utils.try_catch.try_catch` for new async UI/event paths.
- Textual screen-level letter actions that must fire while a list has focus use
  `Binding(..., priority=True)`.
- Text-heavy modals should avoid single-letter close/save bindings. Prefer
  `Esc`, `Ctrl+S`, `Ctrl+Enter`, and visible buttons.
- Do not dual-maintain derived graph metadata. Derive it from connections and
  node config at save/validate time.
- Keep modules concise. Validation is the safety net; avoid heavy runtime
  coupling unless a phase explicitly calls for it.

After coding, from `attackofthenodes_v05/` with the venv active:

```bash
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```

If normal pytest capture fails in this WSL/OneDrive workspace, keep
`pytest.ini` configured with `addopts = -s`.

Append a short entry to `docs/SESSION_LOG.md` for every phase or notable patch.

---

## 4. Current Status

| Phase | Title | Status |
|---|---|---|
| 0 | Memory leak fixes | Done |
| 1 | Forward-reachability helper | Done (`dfafea1`) |
| 2 | Dependency list + validation | Done (`38969a7`) |
| 3 | Membank I/O + registry + descriptions | Done (`9fa1b2a`) |
| 4 | Delete + insert nodes | Done (`51f9a74`) |
| 4.5 | Config modal and selector usability | Done (`0d53c04`) |
| 5 | Config tabs | Done |
| 6 | Breakpoints | Done |
| 7 | Per-node execution timing | Next, can float earlier |
| 8 | Completion registry + wait-until node | Open |
| 9 | Merge dynamic list + lineage barrier | Open |
| 10 | Documentation modernization | Open, docs-only project |
| 11 | Real AI node execution | Deferred |
| 12 | Packaging and release hardening | Deferred |

Sequencing:

- Phase 7 depends only on the memory-leak cleanup and can be pulled forward
  before heavier engine phases.
- Phase 8 depends on Phases 1 and 2.
- Phase 9 depends on Phase 1 and should start by verifying master-state lineage
  support.
- Phase 10 can happen any time, but it should not block engine/UI work unless
  stale docs are actively confusing the implementation.

---

## 5. Completed Work Reference

### Phase 0 — Memory Leak Fixes

- `output_manager.finalize_run()` clears per-run in-memory outputs.
- `error_handler.finalize_run(run_id)` clears per-run error state.
- `master_state._record_run()` no longer duplicates large output payloads in
  run history and finalizes error state.
- `run_history` caps in-memory runs at `_MAX_IN_MEMORY = 500`.
- Four leak-regression tests were added.

### Phase 1 — Forward Reachability

- Added `WorkflowMap.nodes_reachable_from(node_id) -> set[str]`.
- Traverses output connections forward.
- Excludes the starting node.
- Ignores missing targets; validation reports broken references separately.
- Handles cycles and self-loops safely.
- Covered by focused branching/cycle regression tests.

### Phase 2 — Dependency List + Validation

- Save/export/duplicate derive `input_sources` from incoming node connections
  and defensive reads of `config["membank_inputs"]`.
- `validator.py` flags missing derived node sources and undeclared membank
  inputs.
- Connections and config remain the source of truth.

Example saved shape:

```python
"input_sources": [
    {"type": "node", "source_id": "node_A", "port": "default"},
    {"type": "membank", "source_id": "session_id"}
]
```

### Phase 3 — Membank I/O + Registry

- `NodeConfigScreen` manages memory-bank outputs and inputs separately from core
  schema config.
- `membank_outputs` stores id plus description records.
- `membank_inputs` stores selected ids.
- Registry scans declared outputs across the workflow.
- Input dropdown filters downstream-only writers with
  `nodes_reachable_from(current_node)`.
- Port-edge mutation moved out of config modal.

Example config:

```python
"membank_outputs": [{"id": "user_name", "description": "Name entered by user"}],
"membank_inputs": ["session_id"]
```

### Phase 4 — Delete + Insert Nodes

- `A` adds at the visible tail or selected branch path.
- `I` inserts immediately after the highlighted node or active branch row.
- Insert rewires `source -> old_target` into `source -> new -> old_target`.
- Delete no longer cascades branch subtrees.
- Tombstones remain as the visual "rewire me" cue.

### Phase 4.5 — Config and Selector Usability

- Node config modals put memory-bank reads at the top and writes at the bottom.
- Core node settings render between reads and connections.
- Text-heavy config windows no longer use `Q`, `E`, `W/S`, or `A/D` bindings.
- Branch nodes have `path_a_label` and `path_b_label`; editor display uses those
  labels instead of raw port ids.
- Node selector highlights the top filtered result when tabbing into the list.
- Arrow keys move the active highlight cleanly.
- Variable write nodes can pass input through to output by default.

### Phase 5 — Config Tabs

- `frontend/widgets/form_generator.py` groups schema fields by their existing
  optional `group` key.
- Multi-group schemas render as Textual `TabbedContent` / `TabPane` sections.
- Single-group schemas stay flat so simple nodes do not get an empty or noisy
  tab bar.
- Numeric zero values now render as `"0"` instead of a blank field.
- Blank `Select` fields now use Textual's `Select.NULL` sentinel instead of the
  older falsey blank value.
- Tests cover pure grouping behavior plus mounted Textual grouped and
  single-group forms.

### Phase 6 — Breakpoints

- Node data now has a persisted `breakpoint` boolean.
- `WorkflowMap` can set one breakpoint or clear all breakpoints.
- The editor toggles the selected node with `B` and clears all with `Ctrl+B`.
- Node cards show a breakpoint marker on nodes with breakpoints.
- Supervisors publish `BREAKPOINT_HIT` and pause before executing the marked
  node.
- `MasterState` handles breakpoint hits as a global freeze by reusing the
  existing pause/resume machinery.
- Tests cover breakpoint persistence, pause-before-execute behavior, and resume
  through completion.

---

## 6. Remaining Implementation Plan

### Phase 7 — Per-Node Execution Timing

**Files:** `backend/supervisor.py`, `backend/master_state.py`,
`frontend/screens/execution.py`, `frontend/screens/editor.py`.
**Depends on:** Phase 0 only.

Requirements:

- Bracket `node.execute()` with `time.perf_counter()`.
- Publish live node timing to the execution view.
- Store `node_timings: {node_id: seconds}` in the run record.
- Editor displays rolling average timing per node from stored runs.

Done when:

- Execution screen shows live timing.
- Run history records per-node timings.
- Editor shows averages without slowing normal navigation.

### Phase 8 — Completion Registry + Wait-Until Node

**Files:** `backend/master_state.py`, new wait node,
`backend/nodes/__init__.py`, `frontend/screens/node_config.py`.
**Depends on:** Phases 1 and 2.

Requirements:

- Master state owns `completed_nodes: set[str]` plus an `asyncio.Condition`.
- When a supervisor advances past a node, add that node id and notify waiters.
- Add `WaitUntilNode` with config target ids.
- Node waits until all targets have completed at least once, then passes input
  through.
- Target selector filters out downstream nodes using
  `nodes_reachable_from(self)` to avoid obvious deadlocks.
- Use existing node timeout settings so unsatisfied waits error instead of
  hanging.

Done when:

- Cross-branch gating works deterministically.
- Downstream targets are not selectable.
- Timeout failure is reported as a normal node error.

### Phase 9 — Merge Dynamic List + Lineage Barrier

**Files:** `frontend/screens/node_config.py` or branch selector path,
`backend/master_state.py`, merge node implementation.
**Depends on:** Phase 1.

Step 0: verify whether current master-state lineage can answer:

```text
Are all supervisors descended from branch point P accounted for?
```

If yes, implement a lineage barrier. If not, use the counter fallback:
branch points increment expected-arrivals; arrivals and terminations drain the
counter; merge proceeds when it reaches zero.

Requirements:

- Edit-time branch list derives from workflow structure whenever config opens.
- Do not store static branch lists.
- Merge waits for every relevant descendant branch to reach merge or terminate.
- Uneven branch speeds and nested dynamic branches must not race the merge.

Done when:

- Merge config updates from current structure.
- Runtime merge is correct under parallel branches, slow branches, and nested
  branch spawning.

### Phase 10 — Documentation Modernization

**Files:** `docs/PROJECT_KNOWLEDGE.md`, `docs/ARCHITECTURE.md`,
`docs/SIGNAL_FLOW.md`, `docs/FILE_TREE.md`, `docs/V05_BUILD_PLAN.md`.
**Depends on:** none.

Goal:

Turn the docs folder into a reliable current-state reference by removing the
split-brain Chrome-extension/tkinter language from active docs.

Requirements:

- Rewrite `PROJECT_KNOWLEDGE.md` around the Python/Textual implementation.
- Rewrite `ARCHITECTURE.md` around local JSON persistence and current backend
  classes, not IndexedDB/Dexie/JS classes.
- Rewrite `SIGNAL_FLOW.md` around Textual screens, event bus, supervisor events,
  memory/output/error flows, and modal routing.
- Regenerate `FILE_TREE.md` from the current project while excluding caches,
  logs, run artifacts, and venvs.
- Mark `V05_BUILD_PLAN.md` as historical proof-of-concept history, or split its
  current Textual notes into this plan and archive the rest.

Done when:

- A new agent can read the docs folder without being told which documents are
  stale.
- `AGENT_HANDOFF.md` points to this plan as the main source of truth.

### Phase 11 — Real AI Node Execution

**Files:** `backend/nodes/chat_completion_node.py`,
`backend/nodes/image_generation_node.py`,
`backend/nodes/embedding_node.py`, configuration/API helpers.

Requirements:

- Keep existing placeholder behavior available for offline/dev mode.
- Add async HTTP execution with `httpx` or `aiohttp`.
- API keys come from configuration/settings, not hardcoded values.
- Surface provider errors through the normal node error path.
- Add tests using mocked HTTP responses.

Done when:

- AI nodes can run against configured providers.
- Offline placeholder mode remains usable.
- Failures appear in the normal error UI.

### Phase 12 — Packaging and Release Hardening

Requirements:

- Clean dependency files and environment setup.
- Add CI test command documentation.
- Decide how to handle generated run artifacts and logs.
- Add packaging/run instructions for Windows and WSL.
- Expand test coverage beyond `tests/test_debug_nodes.py`.

Done when:

- A fresh checkout can install, test, and launch from documented commands.
- Runtime artifacts are excluded from normal commits.

---

## 7. UI Rules Captured from Testing

- Config windows with multiple text fields should not use single-letter quit or
  save shortcuts.
- Memory-bank reads belong above core settings; memory-bank writes belong at the
  bottom.
- Branch labels are user-facing names and should replace raw `path_a`/`path_b`
  where the editor displays branch paths.
- When filtering in add/insert selectors, tabbing into the list should highlight
  the first visible item automatically.
- Arrow keys should move the visible highlight whenever a highlighted list is on
  screen.
- Utility/write nodes that primarily update memory should support pass-through
  so input can continue to downstream nodes.
- Ports are graph edges. Edit them in the editor, not in the general config
  form.

---

## 8. Parallel Branching Model

Branch nodes are intended to support parallel branch execution, not only manual
single-path selection.

- Runtime branching happens when a node signals multiple branches.
- `WorkflowMasterState` spawns one supervisor per branch.
- The editor's branch selector is only an editing/navigation view of one branch
  path at a time.
- Future merge/wait features must preserve true runtime parallelism and avoid
  UI-only assumptions about a single selected branch.

---

## 9. Test Plan

Use this baseline after every implementation phase:

```bash
cd attackofthenodes_v05
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```

Expected latest known signal:

- 21 tests passing after the config modal usability patch.

For docs-only changes:

```bash
git diff --check
```

Manual TUI smoke tests to keep revisiting:

- `python main.py` launches.
- Node selector groups and search work.
- Sleep node exposes editable duration.
- Branch labels render in editor branch rows.
- `A` adds and `I` inserts after the highlighted node.
- Config text fields accept normal typing.
- `Ctrl+R` starts a run; execution view updates live.
- `Esc` from execution stops/returns cleanly.

---

## 10. Git Workflow

- Work on the current branch unless the user requests otherwise.
- The worktree may contain unrelated dirty/untracked migration files. Do not
  revert them.
- Stage only files touched for the current phase or docs update.
- Commit with a focused message.
- Keep `docs/SESSION_LOG.md` current.
