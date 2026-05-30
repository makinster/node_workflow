# Master Build Plan — Claude Code

**Scope:** Everything from the memory-leak-audit state through the breakpoint,
wait-node, and merge features designed in the planning session.  
**Audience:** Claude Code agents executing one phase per session.  
**Project root:** `node_workflow/attackofthenodes_v05/`

This plan is dependency-ordered. Do phases in sequence — later phases assume the
contracts established by earlier ones. Each phase is sized for roughly one
focused session.

---

## Standing Instructions (every session)

Before writing code:
1. Read `docs/AGENT_HANDOFF.md` for current state, then the docs relevant to
   your phase (`TUI_DESIGN.md` for frontend, `PROJECT_KNOWLEDGE.md` +
   `SIGNAL_FLOW.md` for backend/engine).
2. If your phase creates or edits files of a known type, read the matching
   skill first.

While writing code:
- All new async code uses `try_catch`: `data, error = await try_catch(coro())`.
- The backend never imports from `frontend/`. UI convenience belongs in a
  frontend adapter, not a new backend method.
- Any `Screen`-level letter-key action that must fire while a list widget has
  focus uses `Binding(..., priority=True)`. Navigation keys stay plain tuples.
- Keep modules concise. This project's design value is simple-and-powerful with
  light guardrails — validation is the safety net, not complex runtime logic.

After writing code (run from `attackofthenodes_v05/`, `.venv` active):
```bash
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```
Add the phase's own tests to `tests/test_debug_nodes.py` and confirm they pass.
Update `docs/SESSION_LOG.md` with a short entry when the phase is done.

Environment: Ubuntu, Python 3.14, Textual 8.2.7. Use `.venv` — global pip is
blocked. `source .venv/bin/activate` (or the project-root venv).

---

## Phase 0 — Memory Leak Fixes

**Goal:** Evict per-run caches after runs; stop output duplication; cap history.  
**Depends on:** nothing — do this first.

Follow `MEMORY_LEAK_FIXES.md` exactly. Five steps:
1. Add 4 leak-regression tests to `tests/test_debug_nodes.py` (confirm they fail).
2. `output_manager.py` — `finalize_run()` pops `_outputs_by_run[run_id]`.
3. `error_handler.py` — new `finalize_run(run_id)` pops `_errors_by_run[run_id]`.
4. `master_state.py` — remove `"outputs"` key from the `record_run` dict; call
   `error_handler.finalize_run(run_id)` after errors are read; clear
   `self.run_outputs` if it lives on MasterState.
5. `run_history.py` — add `_MAX_IN_MEMORY = 500`; trim on init and after each
   `record_run` (check list ordering for slice direction).

**Done when:** the 4 leak tests pass and the full suite stays green.

---

## Phase 1 — Forward-Reachability Helper

**Goal:** One graph utility reused by three later phases (membank input filter,
wait-node target filter, merge accessibility).  
**Depends on:** Phase 0.

**Files:** `backend/workflow_map.py` (add a method), or a small
`backend/graph_utils.py` if you prefer it standalone.

**Steps:**
1. Add `nodes_reachable_from(node_id) -> set[str]`: BFS/DFS forward over
   connections, return all node ids reachable downstream of `node_id`
   (excluding `node_id` itself).
2. Keep it pure — takes the current workflow structure, returns a set. No state.

**Contract:**
```python
def nodes_reachable_from(self, node_id: str) -> set[str]:
    """All node ids reachable by following output connections forward."""
```

**Validate:** unit test with a small branching workflow — assert a node sees its
descendants but not its ancestors or siblings on parallel paths.

**Done when:** the helper is covered by a focused test and reused-ready.

---

## Phase 2 — Dependency List + Validation

**Goal:** Derive a per-node input-source list at validate/save and bake it into
the save file; validation flags missing inputs.  
**Depends on:** Phase 1.

**Files:** `backend/save_manager.py` (or wherever save assembly lives),
`backend/validator.py`.

**Steps:**
1. At save/validate, derive per node: one `input_sources` entry per incoming
   connection, one per declared membank input (Phase 3 adds the config field;
   for now read whatever membank-input config exists, default empty).
2. Write `input_sources` into the saved node record. Do not maintain it
   separately during editing — connections + membank config remain the only
   source of truth; this list is a derived cache.
3. In `validator.py`, add a light input check: for each `node` source, confirm
   the source node still exists; for each `membank` source, confirm some node
   declares it as a membank output. Missing → flag the node with an input error.

**Contract:**
```python
"input_sources": [
    {"type": "node",    "source_id": "node_A", "port": "default"},
    {"type": "membank", "source_id": "session_id"}
]
```

**Validate:** build a workflow with a dangling membank input, run validation,
assert the consuming node is flagged; remove the dangle, assert clean.

**Done when:** save files contain `input_sources` and validation flags missing
inputs without any heavier graph analysis.

---

## Phase 3 — Membank I/O in Config + Registry + Descriptions

**Goal:** Move port-connection editing out of the config modal; manage membank
writes/reads in the modal with descriptions; auto-populate a membank registry.  
**Depends on:** Phases 1 and 2.

**Files:** `frontend/screens/node_config.py`, `frontend/widgets/form_generator.py`,
a small registry helper (frontend-side, reads workflow structure).

**Steps:**
1. Remove output-port connection editing from the config modal. Port
   connections are drawn as edges in the editor; the modal no longer shows them.
2. Add a membank-outputs section: checkbox "Writes to memory bank" → integer
   "number of outputs" → per output a name + description field. Store as
   `membank_outputs` in config.
3. Add a membank-inputs section: checkbox "Read from memory bank" → dropdown
   auto-populated from the registry. Store selected ids as `membank_inputs`.
4. Build the registry: scan all nodes' `membank_outputs` → `{id: description}`.
   The dropdown shows id + description.
5. Filter the dropdown with `nodes_reachable_from(current_node)` (Phase 1):
   exclude ids whose only writers are downstream. Invisible during
   left-to-right creation; only fires on retrofit.

**Contracts:**
```python
"membank_outputs": [{"id": "user_name", "description": "Name entered by user"}],
"membank_inputs":  ["session_id"]
```

**Decision applied:** a downstream-writer membank selection is a **warning**, not
a hard error (design smell, not guaranteed failure).

**Validate:** declare a membank output on an upstream node, confirm it appears
in a downstream node's dropdown with its description; confirm a downstream
writer is excluded from an upstream node's dropdown.

**Done when:** the modal manages only membank I/O + core config, and the
registry/filter work from structure with no stored duplication.

---

## Phase 4 — Delete + Insert Nodes

**Goal:** Both as pure edge operations, no cascade.  
**Depends on:** Phase 2 (insert adopts input_sources).

**Files:** `frontend/screens/editor.py`, plus the WorkflowMap connect/disconnect
calls.

**Steps:**
1. **Delete** = remove node + its in/out connections. No auto-rewire. Orphaned
   inputs surface at next validation (Phase 2). Keep the existing tombstone
   placeholder as the visual "rewire me" cue.
2. **Insert between A→B** = disconnect A→B, connect A→new, connect new→B. The
   new node adopts B's `input_sources` so routing stays transparent; membank
   inputs (by id) are untouched by position.
3. Bind insert to a key (e.g. `i`) with `priority=True`.

**Validate:** delete a mid-path node, assert downstream node flags a missing
input; insert a node between two connected nodes, assert the three edges are
correct and the run still traverses in order.

**Done when:** delete and insert are trivial edge ops and validation catches the
fallout of a delete.

---

## Phase 5 — Config Tabs

**Goal:** Render grouped config fields as tabs.  
**Depends on:** Phase 3 (configs now have enough groups to warrant tabs).

**Files:** `frontend/widgets/form_generator.py`.

**Steps:**
1. Group fields by their existing `group` key (from `FieldDescriptor`).
2. Render each group as a `TabPane` inside Textual `TabbedContent` instead of a
   flat list. Core settings, membank inputs, membank outputs, and debug each
   become a tab.
3. No new schema concept — only the renderer changes.

**Validate:** open a node whose schema spans multiple groups; confirm one tab per
group and that values save correctly across tabs.

**Done when:** multi-group configs are tabbed and single-group configs still
render cleanly (no empty tab bar).

---

## Phase 6 — Breakpoints

**Goal:** Pause the run when a supervisor reaches a flagged node.  
**Depends on:** Phase 0 (independent of the membank line, can run earlier if
preferred).

**Files:** `backend/node_base.py` or node record (the flag),
`backend/supervisor.py`, `backend/master_state.py`, `frontend/screens/editor.py`.

**Decision applied:** **global freeze** for v1 — reuse the existing global pause.

**Steps:**
1. Add `breakpoint: bool` to the node (editor-toggled, saved in the file).
2. In the supervisor run loop, before executing a node: if its breakpoint is
   set, request the existing global pause and publish which node/branch tripped
   it. Resume uses the current resume path.
3. Editor: toggle breakpoint with `b` (`priority=True`); add a "clear all
   breakpoints" action.

**Validate:** a workflow with a breakpoint pauses at that node; the triggering
node/branch is reported; resume completes the run.

**Done when:** breakpoints pause and resume through existing machinery with no
new pause-state concept.

---

## Phase 7 — Per-Node Execution Timing

**Goal:** Record, display live, and average per-node execution time.  
**Depends on:** Phase 0.

**Files:** `backend/supervisor.py`, `backend/master_state.py` (run record),
`frontend/screens/execution.py`, `frontend/screens/editor.py`.

**Steps:**
1. In the supervisor, bracket `node.execute()` with `perf_counter()`; store the
   delta.
2. Publish per-node timing live for the execution view.
3. Write `node_timings: {node_id: seconds}` into the run record. (Tiny data —
   safe to keep in history post-leak-audit.)
4. Editor view: average each node's timing across the workflow's stored runs and
   display it on the node.

**Validate:** run a workflow with a `sleep` node set to a known duration; assert
its recorded timing is ≥ that duration; assert the editor average reflects
multiple runs.

**Done when:** live timing shows during execution and rolling averages show in
the editor.

---

## Phase 8 — Completion Registry + Wait-Until Node

**Goal:** A node that gates its branch until specified nodes complete.  
**Depends on:** Phases 1 and 2.

**Files:** `backend/master_state.py` (registry), `backend/nodes/wait_until_node.py`
(new), `backend/nodes/__init__.py`, `frontend/screens/node_config.py`.

**Steps:**
1. Registry on MasterState: `completed_nodes: set[str]` + an `asyncio.Condition`.
   At the point the supervisor advances past a node, add its id and notify.
2. New `WaitUntilNode`: config holds target node ids; `execute()` awaits until
   all targets are in `completed_nodes`, then passes its input through.
   Semantics: "completed at least once" releases the gate.
3. On insert, adopt the downstream node's `input_sources` (transparent routing).
4. Config dropdown for targets filtered by `nodes_reachable_from(self)` — can't
   wait on a downstream node (deadlock), so it's never selectable.
5. Timeout fallback: reuse `node_timeout_seconds` so a never-satisfied wait
   errors instead of hanging.

**Validate:** two branches; a wait node in the slow branch targets a node in the
fast branch; assert the wait releases only after the target completes; assert a
wait on a never-run / downstream target times out with a clear error rather than
hanging.

**Done when:** cross-branch gating works deterministically with deadlock and
timeout guards.

---

## Phase 9 — Merge Dynamic Branch List + Lineage Barrier

**Goal:** Merge config lists accessible branches (updates live); runtime barrier
handles uneven speeds and dynamic sub-branching.  
**Depends on:** Phase 1.

**Files:** `frontend/screens/node_config.py` (or a branch_selector path),
`backend/master_state.py`, the merge node.

**First step — verify the assumption:**
0. Confirm MasterState's lineage tracking can answer "are all descendants of
   branch point P accounted for?" (parent/child supervisor links + depth). If
   yes, use the lineage barrier. If the tracking is insufficient, use the
   **counter fallback**: branch points increment an expected-arrivals counter;
   arrivals/terminations drain it; merge proceeds at zero.

**Steps:**
1. Edit-time: derive the merge's accessible-branch list from workflow structure
   on config-open — every branch of lower depth that can reach it. Recompute on
   each open (like the membank registry). Adding a branch later and reopening
   shows it. Nothing stored statically.
2. Run-time (lineage path): the merge waits until every supervisor descended
   from the relevant branch point has reached the merge or terminated. Lineage
   tracked as supervisors spawn, so sub-branches are counted automatically;
   speed is irrelevant.
3. Run-time (counter fallback, if chosen): implement the increment/drain counter
   per merge.

**Validate:** a branch that sub-branches before the merge's branch sets up still
converges correctly; a fast branch finishing early does not let the merge
proceed before a slow sibling arrives.

**Done when:** the merge list updates from structure at edit-time and the barrier
is correct under uneven, dynamically-spawning branches.

---

## Dependency Graph (quick reference)

```
Phase 0  Memory leak fixes        (standalone, first)
Phase 1  Reachability helper      ← used by 3, 8, 9
Phase 2  Dependency list + valid. ← used by 4, 8        (needs 1)
Phase 3  Membank I/O + registry                          (needs 1, 2)
Phase 4  Delete + insert                                 (needs 2)
Phase 5  Config tabs                                     (needs 3)
Phase 6  Breakpoints              (independent; after 0)
Phase 7  Per-node timing          (independent; after 0)
Phase 8  Wait-until node          (needs 1, 2)
Phase 9  Merge dynamic + barrier  (needs 1)
```

Phases 6 and 7 are independent of the membank line and can be pulled earlier if
a session opens up. Everything else follows the arrows.

---

## Confirmed Decisions

- **Downstream-writer membank input:** warning, not hard error (Phase 3).
- **Breakpoint scope:** global freeze for v1, reusing existing pause (Phase 6).
- **Merge runtime:** lineage barrier preferred; counter fallback if MasterState
  lineage tracking can't answer the descendants question (Phase 9, step 0).
- **Dependency list:** derived at validate/save, not dual-maintained (Phase 2).
- **Tombstones:** retained as the delete visual cue; delete logic stays a pure
  edge operation regardless (Phase 4).
