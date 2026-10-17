# Contributing

Work in your own checkout or worktree; never edit another worker's. Preserve
unrelated edits, untracked recovery material and owner workflows. Start with
[README](README.md), [Current State](CURRENT_STATE.md) and the owning plan.
Code is factual authority; dated logs preserve decisions, not fresh verification.

## Changes and review

- One PR per plan phase, based on fresh `origin/main`. Record root, branch,
  commit and dirty state before changes. Fetch and reconcile main; do not stash
  another person's work or silently continue from a stale base.
- The owner merges, or explicitly asks a reviewer to merge. Opening a PR is not
  permission to merge it. No AI model names in commits or PR text.
- Reproduce a behavior bug with a failing test before fixing it. Explain the
  failure and any deliberate change to old test expectations. Do not weaken or
  delete tests to manufacture a green result. Documentation-only changes need
  link/whitespace checks; task-specific requirements may add the full suite.
- Keep work focused. Reuse shared rules rather than duplicating them in the
  validator, authoring CLI and UI. Raise new design decisions; do not reopen
  settled rejected alternatives without evidence and owner direction.
- Every PR updates [Current State](CURRENT_STATE.md), adds a
  [Session Log](SESSION_LOG.md) entry and updates its owning plan row. Record
  actual checks and limitations; historical counts are not a current baseline.
- Check PR bases before publication and merge. This repository retains merged
  branches, so a stacked PR may still target a merged feature branch. Retarget
  it to `main`; do not assume GitHub did so automatically.
- When parallel work lands first, integrate main and retain both workers' log,
  plan and status entries. Review the combined result before publishing.

Node work starts with [Node Standards](NODE_STANDARDS.md), then
[Node Helper](NODE_HELPER.md). Regeneration can overwrite custom methods/tests
and lose legacy output metadata. Review temporary output and preserve custom
code manually. Ordinary node fields render from schema; custom frontend sections
are for topology-driven behavior. A structural-UI TODO is a design task, not
permission to patch screens ad hoc.

## Verification that demonstrates the claim

Use the checkout's app code and the intended interpreter. Run from
`AttackOfTheNodes/` (a local venv at the repository root is shown):

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -q -k '<behavior>'
../.venv/bin/python -m pytest tests/test_execution_status.py -q
../.venv/bin/python -m pytest -q
git diff --check
```

Choose the focused command for the change, then run required broader checks.
Full `pytest -q` is the full suite; `test_debug_nodes.py` alone is not. Use real
backend services when practical, isolate persistence to temporary directories,
and set `AOTN_DATA_DIR` before backend imports in standalone probes. Never write
test workflows to the owner's `workflows/` directory. New node tests should
cover non-string payload identity when forwarding, source/routing variants,
error behavior, actual output types, and save/reopen/Cancel preservation.

Mounted UI checks must load production `frontend/styles.tcss`, settle layout
and verify actual geometry/navigation at relevant widths (the prior audit used
60/100/140 columns). Bare-App mounts missed real clipping. Include keyboard
input, not just direct backend submissions: a prior W/S typing defect looked
like a missing Vault value. Test current selection/scroll, list-boundary escape,
hidden-value preservation, numeric errors and modal resume where affected.
Headless screenshots/tests do not replace owner live or native-platform checks.

The owner prefers plain, compact UI. Show sample screens before styling/layout
work and obtain the requested review. State which states/widths were inspected.
Keep generated test data and secrets out of commits.

## Shared frontend patterns

Use `CommandScreenMixin`, `CommandInput`/`CommandTextArea`, list navigation,
dynamic sections, form generation, payload display helpers and
`frontend/notifications.py`. [UI Quick Reference](UI_QUICK_REFERENCE.md) owns
keyboard behavior; avoid maintaining another binding list here.

Lessons retained from the TUI design and investigations:

- Non-editing CommandInput/CommandTextArea widgets can consume letter keys
  before a screen shortcut sees them. Verify the focused-widget path; the Stash
  S2 screen returns focus to a list after search/paste for this reason.
- Select's overlay owns focus while expanded. Reuse the guarded overlay patch
  and selection helpers in `command_navigation.py`; screen-level bindings alone
  cannot reliably implement its W/S/E behavior. Private Textual internals make
  this a regression-test target when dependencies change.
- Keep tab headers outside scrolling form content; preserve selected tab and
  focus when rebuilding fields. Scroll only enough to reveal the current field.
- Run/display events can arrive while a screen mounts, switches or sits under a
  modal. Honor mounted/current-screen guards and refresh on resume. Reuse App's
  refresh coalescer rather than scheduling a full redraw for every event.
- Execution uses `RichLog(markup=False)` and plain text rendering. Node output
  such as `[END]` is user data, not Rich markup.
- The form generator accepts options on non-boolean fields even when the type
  says `string`; check the renderer before adding a bespoke Select.
- Inserting into a connected path is an editor adapter operation: disconnect
  the old edge and reconnect through the inserted node using WorkflowMap.
  Keep business rules and dirty tracking in the backend APIs.
- OS pickers return paths; reveal/open-folder helpers do not select paths.
  Reuse `frontend/file_io.py`, retain typed-path fallback and Browse retry,
  and keep backend import/export methods independent of the picker UI.

## Owner's WSL setup

These are local working conventions, not product platform requirements.
The authoritative owner checkout is `/home/makin/src/node_workflow`; the
OneDrive copy is recovery-only. Parallel work uses separate WSL worktrees.
The shared interpreter is `/home/makin/src/node_workflow/.venv/bin/python`.
Run it with `main.py` from your worktree's app directory: installed `aotn` may
resolve to the owner's editable-install checkout. Versions/results are dated
in Current State rather than repeated here.

Use WSL git; Windows git has caused line-ending churn in this repository.
Preserve LF and inspect unexpectedly full-file diffs. For pushes, the Windows
credential manager needs `/mnt/c/Program Files/Git/bin` on `PATH`.
The CLI is `/mnt/c/Program Files/GitHub CLI/gh.exe`; pass
`--repo makinster/node_workflow`. Use a body file for multiline PR descriptions.
PowerShell inline `wsl bash -c` can mangle shell quoting: put complex commands in
a `.sh` file and run that inside WSL instead.

WSL is Linux with explicit Windows interoperability. Native Windows, macOS and
Linux desktop support require their own tests. The native FO7 protocol is in
[Project Backlog](PROJECT_BACKLOG.md#native-filewindow-verification-fo7).
