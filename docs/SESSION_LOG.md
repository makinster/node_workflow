# AttackOfTheNodes Session Log

## 2026-05-31 — Config Modal Usability Patch

- Reordered node config modals so memory-bank reads are above core node
  settings and memory-bank writes are at the bottom.
- Removed `Q` and other single-letter navigation/save bindings from the
  text-heavy node config modal so typing in fields works normally.
- Added branch label config fields (`path_a_label`, `path_b_label`) and editor
  display support so branch rows can show names instead of raw `path_a/path_b`.
- Improved node selector keyboard behavior: tab focuses the node list and the
  top filtered item is highlighted immediately; arrow keys move the highlighted
  item.
- Added pass-through defaults to variable writer nodes so utility writes can
  preserve input as output.
- Verification:
  - `python -m compileall -q .`
  - `python -m pytest tests/test_debug_nodes.py -v`

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

## 2026-05-30 — Phase 4 Delete + Insert Nodes

- Split editor add/insert intent: `A` keeps add-at-tail behavior, while `I`
  inserts after the highlighted node or active branch row.
- Insert rewiring disconnects the highlighted node's old downstream edge,
  connects highlighted -> new node, then connects new node -> old downstream.
- Removed cascade subtree deletion from editor delete; tombstones remain as the
  visible "choose a replacement" cue and downstream branch nodes are retained.
- Added focused tests for insert-between rewiring and no-cascade tombstone
  deletion.
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
