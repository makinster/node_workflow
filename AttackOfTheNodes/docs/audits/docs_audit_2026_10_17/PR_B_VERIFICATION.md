# PR B verification — 2026-10-17

This is newly produced verification for consolidation, not recovered evidence
from the external audit. The source map was committed as `23f96ee` before
extraction, using main `9d5455b`. Original audit evidence/CSVs remain unavailable.

## Preservation and entry route

`check_consolidation.py` checks every relative Markdown link/anchor under app
docs plus root AGENTS, the 17-document active set, and all 33 retained whole
bodies (32 moved documents plus the old architecture). Body comparison against
`9d5455b` permits changed relative link targets and the migration ledger's appended
entry; all other source text is retained after the new supersession banner.

The active destinations for each source range are recorded in
[vision_sources.md](vision_sources.md). The migration ledger records every move.
PR C still owns session-history bounding and remaining lower-priority findings.

## Claims checked against code

| Consolidated topic | Code checked |
|---|---|
| Graph ownership, first edge, config replacement | `backend/workflow_map.py`, `node_factory.py` |
| Signals versus calls; registration object; memory delta | `backend/event_bus.py`, `supervisor.py`, `memory_bank.py` |
| Output-before-completion; branch spawners; stop/input | `backend/supervisor.py`, `master_state.py`, `tests/test_wait_until_vault.py` |
| Shared transient keys and separate type tags | `backend/memory_bank.py` |
| File refs, generic resources and chat histories | `backend/file_refs.py`, `run_session.py`, `nodes/chat_completion_node.py` |
| Per-run waits, merge groups and cleanup | `backend/run_context.py`, `wait_registry.py`, `master_state.py` |
| Service validation and stopped result | `backend/run_service.py`, `aotn_cli.py`, `main.py` |
| All-node validation, reachability and warning limits | `backend/validator.py`, `validation_codes.py`, `port_types.py` |
| Output-log capture and finalization | `backend/output_manager.py`, `master_state.py`, `run_history.py` |
| Display reducer/status priority and retirement | `frontend/execution_state.py`, `frontend/app.py` |
| Keyboard and form behavior | `frontend/screens/`, `frontend/widgets/command_input.py`, `command_navigation.py` |
| 64-path width versus default merge slots | `backend/branch_paths.py`, `nodes/branch_node.py`, `nodes/merge_node.py` |
| Stash core and pending S2 controls | main `backend/stash_manager.py`; S2 PR #71 head `bdaeaec` via local Git objects |

The runtime consolidation addresses F12/F13/F16/F21–F23/F25–F27/F42/F43/F46;
keyboard and helper-reference corrections cover F18–F20/F33. The retained report
is an index of the original audit; code is the authority for these rewritten facts.

## Checks and limits

- Full app suite: **1509 passed in 173.22s**, with the shared Python 3.14.4 venv,
  run from `AttackOfTheNodes/` on main `9d5455b` plus the docs changes.
- No runtime, frontend, helper spec, workflow or test files changed in PR B.
- Link/archive/count verification and `git diff --check` pass; exact current
  counts are printed by `check_consolidation.py` and recorded in Current State.
- Clean installation, native FO7, external links and live UI geometry were not
  reverified. Pending S2 controls were source-checked, not tested by this branch's
  main-baseline suite. Owner decisions/proposals remain labelled.
