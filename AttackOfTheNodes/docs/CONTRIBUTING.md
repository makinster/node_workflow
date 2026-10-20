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

## Keeping the session log bounded

Keep about two weeks of dated entries in `SESSION_LOG.md`; the checked window
is written at its top. Before moving an older entry, put any unique owner
decision, rationale or unresolved proposal in the reference that owns its topic.
Keep proposed, superseded and implemented behavior distinct. Record source
headings and destinations in the audit's extraction map, then transfer the
whole entries to `archive/SESSION_LOG_HISTORY.md`, rebasing relative links.
Retain the existing archive body and other workers' recent entries. Check moved
text against Git and run the docs link/archive checker; do not reduce history
to milestone summaries. Current status belongs in `CURRENT_STATE.md`.

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

### Adding a registered command

The typed definitions in `frontend/keymap.py` now own App, the command-mode
screens and their text/Select adapters. `keymap_runtime.py` supplies pure
availability. Memory/Output/File viewers retain their legacy maps until next
touched. Keep existing semantic IDs, including Confirm's phase-1 IDs.

1. Add a `Command` to its `Profile`: stable ID, native key aliases, action and
   description. `policies` is a **frozenset of allowed states**, default `{NAV}`.
   Use `{NAV, TEXT}` for a command deliberately available while typing. Node
   Config's save-and-stay also includes `SELECT` because its action explicitly
   commits/closes the dropdown before saving. Ordinary navigation excludes both
   TEXT and SELECT. NAV printable keys compile as priority bindings so a focused
   nonediting text field cannot swallow them; special control keys declare
   priority explicitly.
2. **A key-specific rule needs a separate action.** `check_action` sees actions
   and parameters, not the triggering key. For example, plain S allowed only in
   NAV and Ctrl+S allowed in NAV/TEXT must call different wrapper actions, which
   may share a save implementation. A profile rejects conflicting policy sets
   for one action signature. Disjoint NAV/TEXT meanings for one widget key use
   separate actions too (Enter begins editing in NAV, finishes it in TEXT).
3. Implement the action and declare `KEYMAP` and
   `BINDINGS = bindings_for(KEYMAP)` in the class body, before Textual merges
   bindings. `CommandScreenMixin` already inherits `KeymapScreenMixin`; do not
   add that base twice. Non-command screens/App use `KeymapScreenMixin` directly.
   Reuse existing focus/activation helpers. Movement/activation roles in command
   metadata let widget fallbacks and focus rescue follow effective keys rather
   than keeping old W/S/E routes alive after an override. Single-field A/D
   positioning has its own `text.caret_left/right` commands; their row fallback
   yields to an available screen movement command.
4. Availability queries must not change focus, close Selects, commit text or
   dispatch. Registered application commands yield to modals; inactive screen
   owners are unavailable. Screen-specific pure conditions may further restrict
   commands. Native text editing (caret, deletion, clipboard) remains Textual's.
   Edit transitions are registered widget actions; ordinary typing reaches them
   through native dispatch, never a second raw-key shortcut map.
5. `revert_or_cancel` first reverts a retained active editor, then uses the
   profile's `cancel_action` on a later press. Preserve screen-specific exit
   behavior (unsaved Save/Discard/Stay, User Input cancellation stopping a run).
   The focused text widget owns its own Ctrl+Q revert, preventing root Quit
   leakage in simple hosts. Keep Escape's edit-exit and modal-exit sequence.
6. Select compatibility belongs in `widgets/select_keymap.py`, the only place
   that patches Textual's private overlay/native class binding caches. Expanded
   Select and overlay use one profile; only the focused owner is enabled. Test
   both focus paths, including screen embedding. Do not add raw Select handlers
   to Node Config or new custom sections.
7. Editor/Execution Help uses `help_for(profile)`; their compact hints use
   `screen_hint_for(profile)`. Hint groups name stable command IDs; they do not
   copy key strings. Both renderers use native key overrides. Keep Help labels
   in command descriptions and provide before/after text for visible changes.
   Confirm still uses `hint_for(profile)`. Other contexts, generated Quick
   Reference tables and Settings rebinding UI remain deferred.
8. Add actual-keypress tests with production CSS: compiled IDs/aliases, focused
   controls, NAV/TEXT/Select ownership, modal scope and button activation. Test
   rebinding through `App.set_keymap` (without adding a preferences UI): the new
   key works, the old key does not survive in widget/overlay/rescue fallbacks,
   and typing stays literal. Run the `test_keymap*` modules, affected screen
   tests and full suite. Reproduce defects failing before fixing them.

For new Node Config custom sections, keep the existing compose/build, generated
field and `_nav_widgets()` integration. Ordinary fields inherit these policies
through CommandInput/CommandTextArea. New keyboard commands belong in the
NODE_CONFIG profile; a mode exception belongs in their declared policies and a
pure guard, not a new screen `on_key` branch. Observe the active editor and
preserve selection/focus when rebuilding rows.

Lessons retained from the TUI design and investigations:

- Non-editing CommandInput/CommandTextArea widgets can consume letter keys
  before a screen shortcut sees them. Verify the focused-widget path; the Stash
  S2 screen returns focus to a list after search/paste for this reason.
- Expanded Select navigation uses the shared native profile and the isolated
  compatibility adapter in `widgets/select_keymap.py`; selection/focus helpers
  remain in `command_navigation.py`. Private Textual internals make this a
  regression-test target when dependencies change.
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
