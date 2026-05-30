# AttackOfTheNodes Session Log

## 2026-05-30 — Phase 1 Reachability Helper

- Treated `docs/MASTER_BUILD_PLAN.md` Phase 0 memory-leak fixes as complete.
- Added `WorkflowMap.nodes_reachable_from(node_id) -> set[str]` for downstream
  graph reachability. The helper excludes the starting node, ignores missing
  targets, and is cycle-safe.
- Added a focused branching-graph regression test to
  `tests/test_debug_nodes.py`.
- Added repo-local handoff/backlog docs so future sessions can start from the
  current Textual build state instead of pasted chat context.
- Verification:
  - `python -m compileall -q .`
  - `python tests/test_debug_nodes.py`

## 2026-05-30 — Phase 2 Dependency List + Validation

- Replaced `docs/MASTER_BUILD_PLAN.md` with the updated build handoff that marks
  Phase 0 and Phase 1 complete and makes Phase 2/3 sequencing explicit.
- Installed `pytest` and `pytest-asyncio` in the project venv and added
  `pytest.ini` with `asyncio_mode = auto`.
- Added derived `input_sources` to workflow save/export/duplicate data. The
  cache is derived from node input connections plus defensive reads of
  `config["membank_inputs"]`.
- Added validation for missing derived node input sources and missing membank
  declarations.
- Added focused tests for save-file `input_sources`, missing node input sources,
  and missing membank input sources.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

## 2026-05-30 — Phase 3 Membank I/O + Registry

- Removed port-edge mutation controls from `NodeConfigScreen`; connections are
  shown read-only there and remain an editor-path responsibility.
- Added memory-bank output controls that store `membank_outputs` as id +
  description records.
- Added memory-bank input controls that store selected ids in `membank_inputs`.
- Added a frontend registry helper that scans declared `membank_outputs` and
  filters downstream-only writers with `WorkflowMap.nodes_reachable_from()`.
- Added a focused registry/filter regression test.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`
