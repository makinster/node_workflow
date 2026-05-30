# Build Handoff — AttackOfTheNodes

**State as of:** commit `dfafea1` (Phase 1 complete).
**This document supersedes the earlier `MASTER_BUILD_PLAN.md`** — same phases,
updated to mark completed work and fold in the pre-flight and sequencing notes.

**Project root:** `node_workflow/attackofthenodes_v05/`
**Runtime:** Ubuntu · Python 3.14 · Textual 8.2.7 · asyncio · JSON persistence

---

## Pre-Flight — Do This First

The test suite uses `@pytest.mark.asyncio`, but the venv currently has no
pytest. Async assertions only run under `pytest-asyncio`, so install both inside
the venv (no `--break-system-packages` needed in a venv):

```bash
pip install pytest pytest-asyncio
```

Add an asyncio mode line so the markers resolve — in `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
```

After this, `python -m pytest tests/test_debug_nodes.py -v` is the real test
signal for every phase below.

---

## Standing Instructions (every session)

Before code:
1. Read `docs/AGENT_HANDOFF.md`, then the docs relevant to your phase
   (`TUI_DESIGN.md` for frontend; `PROJECT_KNOWLEDGE.md` + `SIGNAL_FLOW.md` for
   the engine).
2. If the phase creates or edits a known file type, read the matching skill first.

While coding:
- All new async code uses `try_catch`: `data, error = await try_catch(coro())`.
- The backend never imports from `frontend/`. UI convenience goes in a frontend
  adapter, never a new backend method.
- Any `Screen`-level letter-key action that must fire while a list widget has
  focus uses `Binding(..., priority=True)`. Navigation keys stay plain tuples.
- Keep modules concise. The design value is simple-and-powerful with light
  guardrails — validation is the safety net, not heavy runtime logic.

After coding (from `attackofthenodes_v05/`, venv active):
```bash
python -m compileall -q .
python -m pytest tests/test_debug_nodes.py -v
```
Add the phase's own tests, confirm green, and append a short entry to
`docs/SESSION_LOG.md`.

---

## Status

| Phase | Title | Status |
|---|---|---|
| 0 | Memory leak fixes | ✅ Done |
| 1 | Forward-reachability helper | ✅ Done (`dfafea1`) |
| 2 | Dependency list + validation | ✅ Done |
| 3 | Membank I/O + registry + descriptions | ✅ Done |
| 4 | Delete + insert nodes | ⏳ Next |
| 5 | Config tabs | ⏳ |
| 6 | Breakpoints | ⏳ (floats — see notes) |
| 7 | Per-node execution timing | ⏳ (floats — see notes) |
| 8 | Completion registry + wait-until node | ⏳ |
| 9 | Merge dynamic list + lineage barrier | ⏳ |

**Sequencing notes:**
- **2 and 3 are coupled.** The membank half of Phase 2's derivation and
  validation is inert until Phase 3 adds `membank_inputs`. The split is fine, but
  if you'd rather not leave that half untested, do 2 and 3 in one session.
- **6 and 7 float.** Both depend only on Phase 0, so pull them earlier for a
  quick win between the heavier membank/merge work if convenient.

---

## Completed Phases (reference)

**Phase 0 — Memory leak fixes.** `output_manager.finalize_run()` now pops
`_outputs_by_run`; `error_handler` gained `finalize_run(run_id)`;
`master_state._record_run()` dropped the duplicated `"outputs"` key and calls
`error_handler.finalize_run()`; `run_history` caps `_runs` at `_MAX_IN_MEMORY =
500`. Four leak-regression tests added.

**Phase 1 — Forward-reachability helper.** `WorkflowMap.nodes_reachable_from(
node_id) -> set[str]` (branching/cycle-safe), covered by a regression test.
Reused by Phases 3, 8, 9. Suite at 13 tests green.

**Phase 2 — Dependency list + validation.** Save/export/duplicate paths now
derive `input_sources` from incoming connections plus defensive
`membank_inputs` config reads. Validation flags missing derived node sources and
missing membank declarations. Suite at 16 tests green.

**Phase 3 — Membank I/O + registry + descriptions.** The node config modal now
manages memory-bank outputs/inputs separately from core schema config, derives
the selectable input registry from declared `membank_outputs`, filters
downstream-only writers via `nodes_reachable_from`, and leaves port-edge editing
to editor path tools. Suite at 17 tests green.

---

## Remaining Phases

### Phase 2 — Dependency List + Validation
**Files:** `backend/save_manager.py`, `backend/validator.py`. **Depends on:** 1.

1. At save/validate, derive per node: one `input_sources` entry per incoming
   connection, one per declared membank input. Bake into the saved node record.
   Do not dual-maintain — connections + config remain the only truth.
2. `validator.py`: light check — each `node` source must exist; each `membank`
   source must be declared as a membank output somewhere. Missing → flag the
   node with an input error.

```python
"input_sources": [
    {"type": "node",    "source_id": "node_A", "port": "default"},
    {"type": "membank", "source_id": "session_id"}
]
```

Write the membank half defensively (read the field, default empty) — it stays
inert until Phase 3. The node-connection half is what Phase 2's tests exercise.
**Done when:** save files carry `input_sources` and validation flags missing node
sources without heavier analysis. ✅ Done.

### Phase 3 — Membank I/O + Registry + Descriptions
**Files:** `frontend/screens/node_config.py`, `frontend/widgets/form_generator.py`,
a frontend registry helper. **Depends on:** 1, 2.

1. Remove output-port connection editing from the config modal — ports are drawn
   as edges in the editor.
2. Membank-outputs section: checkbox "Writes to memory bank" → integer count →
   per output a name + description. Store as `membank_outputs`.
3. Membank-inputs section: checkbox "Read from memory bank" → dropdown from the
   registry. Store ids as `membank_inputs`.
4. Registry = scan all `membank_outputs` → `{id: description}`; dropdown shows id
   + description.
5. Filter the dropdown with `nodes_reachable_from(current_node)` — exclude ids
   whose only writers are downstream. Invisible during left-to-right creation.

```python
"membank_outputs": [{"id": "user_name", "description": "Name entered by user"}],
"membank_inputs":  ["session_id"]
```

**Decision:** a downstream-writer membank selection is a **warning**, not a hard
error. **Done when:** the modal manages only membank I/O + core config and the
registry/filter work from structure with no stored duplication. ✅ Done.

### Phase 4 — Delete + Insert Nodes
**Files:** `frontend/screens/editor.py` + WorkflowMap connect/disconnect.
**Depends on:** 2.

1. **Delete** = remove node + its in/out connections. No auto-rewire; orphaned
   inputs surface at next validation. Keep the tombstone placeholder as the
   visual "rewire me" cue.
2. **Insert between A→B** = disconnect A→B, connect A→new, connect new→B. The new
   node adopts B's `input_sources`; membank inputs (by id) are untouched.
3. Bind insert to a key (e.g. `i`) with `priority=True`.

**Done when:** both are pure edge ops and validation catches a delete's fallout.

### Phase 5 — Config Tabs
**Files:** `frontend/widgets/form_generator.py`. **Depends on:** 3.

Render fields grouped by their existing `group` key as `TabPane`s inside Textual
`TabbedContent`. No new schema concept — only the renderer changes. **Done when:**
multi-group configs are tabbed and single-group configs render without an empty
tab bar.

### Phase 6 — Breakpoints *(floats; after 0)*
**Files:** node record, `backend/supervisor.py`, `backend/master_state.py`,
`frontend/screens/editor.py`.

**Decision:** **global freeze** for v1, reusing the existing global pause.

1. Add `breakpoint: bool` to the node (editor-toggled, saved).
2. Supervisor run loop: before executing a node, if its breakpoint is set,
   request the existing global pause and publish which node/branch tripped it;
   resume via the current path.
3. Editor: toggle with `b` (`priority=True`); add "clear all breakpoints".

**Done when:** breakpoints pause and resume through existing machinery with no
new pause-state concept.

### Phase 7 — Per-Node Execution Timing *(floats; after 0)*
**Files:** `backend/supervisor.py`, `backend/master_state.py`,
`frontend/screens/execution.py`, `frontend/screens/editor.py`.

1. Bracket `node.execute()` with `perf_counter()`; store the delta.
2. Publish per-node timing live for the execution view.
3. Write `node_timings: {node_id: seconds}` into the run record (tiny data — safe
   post-leak-audit).
4. Editor: average each node across the workflow's stored runs; display on node.

**Done when:** live timing shows during runs and rolling averages show in the
editor.

### Phase 8 — Completion Registry + Wait-Until Node
**Files:** `backend/master_state.py`, `backend/nodes/wait_until_node.py` (new),
`backend/nodes/__init__.py`, `frontend/screens/node_config.py`. **Depends on:** 1, 2.

1. Registry on MasterState: `completed_nodes: set[str]` + an `asyncio.Condition`.
   At the point the supervisor advances past a node, add its id and notify.
2. `WaitUntilNode`: config holds target ids; `execute()` awaits until all targets
   are in the set, then passes input through. Semantics: "completed at least
   once" releases the gate.
3. On insert, adopt the downstream node's `input_sources`.
4. Target dropdown filtered by `nodes_reachable_from(self)` — a downstream
   (deadlocking) target is never selectable.
5. Timeout fallback via `node_timeout_seconds` so a never-satisfied wait errors
   instead of hanging.

**Done when:** cross-branch gating works deterministically with deadlock and
timeout guards.

### Phase 9 — Merge Dynamic Branch List + Lineage Barrier
**Files:** `frontend/screens/node_config.py` (or branch_selector path),
`backend/master_state.py`, the merge node. **Depends on:** 1.

**Step 0 — verify the assumption:** confirm MasterState's lineage tracking can
answer "are all descendants of branch point P accounted for?" (parent/child
links + depth). If yes → lineage barrier. If not → **counter fallback**: branch
points increment an expected-arrivals counter; arrivals/terminations drain it;
merge proceeds at zero.

1. Edit-time: derive the accessible-branch list from workflow structure on
   config-open — every branch of lower depth that can reach it. Recompute each
   open (like the membank registry). Nothing stored statically.
2. Run-time (lineage): merge waits until every supervisor descended from the
   branch point has reached the merge or terminated. Sub-branches are counted
   automatically; speed is irrelevant.
3. Run-time (counter fallback, if chosen): implement the increment/drain counter.

**Done when:** the list updates from structure at edit-time and the barrier is
correct under uneven, dynamically-spawning branches.

---

## Dependency Graph

```text
Phase 0  Memory leak fixes        ✅
Phase 1  Reachability helper      ✅   → used by 3, 8, 9
Phase 2  Dependency list + valid. ✅   (needs 1)        → used by 4, 8
Phase 3  Membank I/O + registry   ✅   (needs 1, 2)
Phase 4  Delete + insert               (needs 2)
Phase 5  Config tabs                   (needs 3)
Phase 6  Breakpoints                   (after 0; floats)
Phase 7  Per-node timing               (after 0; floats)
Phase 8  Wait-until node               (needs 1, 2)
Phase 9  Merge dynamic + barrier       (needs 1)
```

---

## Confirmed Decisions

- **Dependency list** — derived at validate/save, not dual-maintained (P2).
- **Downstream-writer membank input** — warning, not hard error (P3).
- **Tombstones** — retained as the delete visual cue; delete stays a pure edge
  operation regardless (P4).
- **Breakpoint scope** — global freeze for v1, reusing existing pause (P6).
- **Merge runtime** — lineage barrier preferred; counter fallback only if
  MasterState lineage tracking can't answer the descendants question (P9, step 0).

---

## Repo Docs

In `docs/`: `MASTER_BUILD_PLAN.md` (this supersedes it), `SESSION_LOG.md`,
`PROJECT_BACKLOG.md`, `AGENT_HANDOFF.md`. Keep `SESSION_LOG.md` current per phase
so the next agent picks up from the repo without a manual paste.
