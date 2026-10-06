# Next Chat Handoff — Execution Status and Branch UI

Updated 2026-10-06. Use `/home/makin/src/node_workflow` and its `.venv/bin/python`.
The OneDrive checkout is recovery-only. Select the WSL project in Codex for the
new chat. Do not create another independent checkout or copy whole trees.

## Current next step — review integrated session PR

This branch now combines the pending fixes, File Output and configuration audit.
See [CONFIG_UI_BUILD_PLAN.md](CONFIG_UI_BUILD_PLAN.md) for implemented stage 0 and
ordered remaining stages; [SESSION_INTEGRATION_BUILD_PLAN.md](SESSION_INTEGRATION_BUILD_PLAN.md)
records merge/publication strategy. The shared config-preservation and critical
input overflow defects are fixed. Current merged inventory is 37 types. Windows
FO7 and owner live accessibility/appearance review remain open. Earlier counts,
commit IDs and PR #28 instructions below are historical, not current baselines.

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
  Textual tests at 60/100/140 columns. Full suite: 414 passed in 49.74s; compileall, diff and
  local documentation-link checks passed; results recorded in SESSION_LOG.md. Owner confirmed the symbols work in the live app on 2026-10-06.

## Wait Until layout and shared tab standard

Wait Until now uses `1 - Wait` (alias, targets, timeout, forwarding explanation)
and `2 - Connections`. Unsupported Vault/routing controls are absent. Save
clears obsolete Wait Until Vault declarations; Cancel preserves them unchanged.
Unavailable targets remain visible until explicitly removed; invalid timeout
input blocks Save. Focus/scroll are remembered across tab switches.

Shared documentation now treats Source/Parameters/Payloads/Connections as
section meanings, with only applicable sections shown and consecutive numbered
tabs. Four tabs are not mandatory; compact/topology-driven nodes may use focused
layouts. Other nodes' current layouts are unchanged. See WAIT_UNTIL_UI_PLAN.md
and SESSION_LOG for verification. Restart the app to load the new config UI.

## User input keyboard follow-up

Continued-session empty-document report prompted exact saved graph diagnostics:
with a non-empty submitted answer, Wait Until gates correctly and the LLM reads
`user_text`. Mounted dialog tests found W/S navigating while typing and dropping
answer characters. UserInputScreen now starts normal editing explicitly; four
new keyboard regressions pass. Full suite: **429 passed in 52.25s**. Restart the
app for this additional UI change. Exact original answer/timing remains unconfirmed.

## Wait Until follow-up

Owner confirmed the cross-branch User Text Input -> Vault -> LLM scenario.
Working fix on `codex/wait-until-vault-fix`: declared input Vault writes precede
success, transient publication precedes completion gates, and stopped input
does not satisfy gates. See `WAIT_UNTIL_INVESTIGATION.md` and SESSION_LOG for
verification. Saved workflow was not changed; its LLM already reads `user_text`
through Document/Context. Prior uncommitted branch-UI design docs are preserved.

## Current continuation — merged base and design

PR #28 is merged in main `7161ef2`; canonical main matched fetched origin/main
on 2026-10-06. Branch UI design is recorded in
[EXECUTION_BRANCH_UI_DESIGN.md](EXECUTION_BRANCH_UI_DESIGN.md) on
`codex/execution-branch-ui-design`. Design only; implementation remains pending.
Read it before implementing navigation or previews. The repository-state and
immediate-next-step sections below are historical pre-merge handoff text.

## Repository state (historical)

Branch: `codex/execution-symbol-investigation`, based on main `8ada5b2`.
Investigation `20d58c7`, build-plan docs `fa91bd0`. Implementation: `a31900d`, verified by **414 passing tests**, including the
21 execution regressions and 154 existing debug tests. Branch is pushed;
[PR #28](https://github.com/makinster/node_workflow/pull/28): owner confirmed
live symbols and authorized publication/merge on 2026-10-06. Check GitHub
merge status, fetch and use updated main before the next UI task. This branch
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

## Historical immediate next steps

Owner confirmed successful nodes now receive the correct symbols. Automated
checks cover recovery, modal resume and edge cases; these were not separately
reported as manually verified. PR #28 has been reviewed for the requested merge.
Verify it is merged, fetch, and fast-forward local main before starting branch
UI work. Do not reimplement the symbol fix.

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

## Historical opening request (superseded by current next step)

“Continue from execution-status PR #28. Read
NEXT_CHAT_HANDOFF.md and EXECUTION_STATUS_CONTRACT.md, verify branch/status and
the PR merge status (owner confirmed the symbols). Start from updated main and
plan the A/D branch execution UI using the retained branch/visit state; settle
output-summary attribution and layout before implementing it.”
