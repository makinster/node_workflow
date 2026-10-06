# Next Chat Handoff — Execution Status and Branch UI

Updated 2026-10-06. Use `/home/makin/src/node_workflow` and its `.venv/bin/python`.
The OneDrive checkout is recovery-only. Select the WSL project in Codex for the
new chat. Do not create another independent checkout or copy whole trees.

## Completed in this session

- Chat Completion Edit Node lag fixed, owner confirmed live, and merged via
  PR #27 into main `8ada5b2`. Rule processing profile 7.664s -> 0.093s.
- Investigated the run-screen symbols: missing per-node state transitions,
  false success after error/termination, and stale screen after modal dismissal.
- Recorded the fix build plan and the owner's future branch-view direction.
- Implemented explicit scoped node lifecycle events, per-branch visit/attempt
  display history, independent shared-node statuses, retry/skip/stop outcomes,
  resumed-screen refresh, and stable execution cards/highlight/scroll.
- Corrected the skip path's premature completion of the next node. Existing
  routing, Vault/dead-drop, safe-point pause, barrier and recovery actions remain.
- Added 21 execution-specific regressions, including real runtime and mounted
  Textual tests at 60/100/140 columns. Full suite verification recorded in
  SESSION_LOG.md. These do not replace the owner's live check of the new fix.

## Repository state

Branch: `codex/execution-symbol-investigation`, based on main `8ada5b2`.
Investigation `20d58c7`, build-plan docs `fa91bd0`. Implementation commit and
publication state are recorded below after final verification. This branch
contains the investigation/plan as well as the fix; they have not been merged
into main. Preserve unrelated Git safeguards and File Output feature branches.
Fetch, inspect status/history and compare the intended branch tip before changes.

## Read before continuing

1. `EXECUTION_STATUS_CONTRACT.md` — current code's event/cache/render contract.
2. `EXECUTION_STATUS_BUILD_PLAN.md` — ES0–ES3 implemented; ES4 live/review pending.
3. `SESSION_LOG.md` — actual verification and publication status.
4. `EXECUTION_STATUS_INVESTIGATION.md` — historical before-fix evidence.
5. `PROJECT_BACKLOG.md` -> Execution Screen Branch View — future design scope.

Implementation files: `backend/events.py`, `backend/supervisor.py`,
`frontend/execution_state.py`, `frontend/app.py`,
`frontend/screens/execution.py`, `frontend/widgets/node_list.py`,
`frontend/widgets/node_card.py`; tests: `tests/test_execution_status.py`.

## Immediate next steps

Restart the WSL app and manually confirm the owner's workflow: every successful
node becomes a checkmark, errors remain errors after ending their branch, and
Memory/Output modal closure reveals current statuses. Check slow linear and
parallel workflows; skip/stop must not show success checks. Record owner results.
Review the fix PR and merge after verification; then update local main.

## Following task — Execution screen branch view

Owner intends A/D cycling through runtime branches, scrollable per-branch node
lists and output-summary UI. These controls and layout are not implemented.
Keep this visual work in a separate branch/PR after the correctness fix.

Use `app.execution_state.branches` (registration order and retained ended
branches) and `node_statuses(branch_id)`. Visits contain independent attempts
and timings; branch metadata has parent/depth/start-node provenance. Keep branch
selection, node/visit selection and per-branch scroll in frontend screen state.
Do not rebuild lifecycle reporting or collapse shared-node visits globally.

Design decisions still needed: branch names/order/wrap; actual visits versus
upcoming graph rows; repeat-visit presentation; pause/barrier/skip/stop symbols;
output-summary placement and whether it describes a branch, node or both.

OutputManager is not a universal node-output history. Shared transient payloads
can be overwritten. Define branch/visit attribution, bounded preview retention,
and resource handling before implementing summaries. Do not put arbitrary
payloads/resources in lifecycle events. Persistent run-history browsing and
transport-safe supervisor registration are separate future tasks.

## Verification commands

From `AttackOfTheNodes/`, using the canonical venv:

```bash
../.venv/bin/python -m pytest tests/test_execution_status.py -q
../.venv/bin/python -m pytest tests/ -q
../.venv/bin/python -m compileall -q .
git diff --check
```
