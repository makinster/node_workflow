# Prompt for the next agent session (node contract work)

The Recovery/Editor UX detour (UX1–UX6 plus follow-ups, PRs #43–#53) is
complete. This file starts the next phase. The paste-in message is at the end.

## Read first, in this order

1. `AGENTS.md` (repo root). Parts lag the code (it omits RunContext,
   RunService and `AOTN_DATA_DIR`); trust the code.
2. `AttackOfTheNodes/docs/NODE_CONTRACT_PLAN.md`: the proposed phases C1–C12
   and the owner's direction of 2026-10-14. **Still marked proposed:** confirm
   with the owner before starting C1.
3. `AttackOfTheNodes/docs/SESSION_LOG.md`, entries from "UX5" onward.
4. `AttackOfTheNodes/docs/RECOVERY_UX_EXECUTION_PROMPT.md`: the hard rules,
   environment notes and owner UI taste still apply (sections "Hard rules",
   "Environment notes", "Owner UI taste").
5. `BACKEND_FRONTEND_BOUNDARY.md` before any backend change made for UI.
6. `NODE_STANDARDS.md` ("Connections Tab": the shared Vault model) and
   `UI_QUICK_REFERENCE.md` (keys, saving, names/IDs/error headings).

When sources disagree: code first, then the recent session log, then plans.

## Where things stand (2026-10-14)

- `main` at `105623d` (merge of PR #63). Merged: C1–C3, C5, the selector
  toggle, issue codes, the authoring tool (#61, #63) and the Stash proposal
  docs (#62), C4 (#64), C6 (#65). C7 re-lands as #67 (#66 merged into
  the C6 branch, not `main`). The naming PR (`dist/workflow-naming`) is
  in its PR. Suite: **1479 passed** (about 3.5 minutes).
  Order:
  Stash S1–S3 → Step 4 with Stash S5 (see `NODE_CONTRACT_PLAN.md`).
- Untracked files to leave alone: `.claude/launch.json`,
  `AttackOfTheNodes/"C:\...\test.txt"`, `AttackOfTheNodes/Workflow started`.

What the detour delivered, in short:

- **Node editor:** Ctrl+S / Ctrl+Enter save and stay (committing a text
  field); Esc / Close ask Save / Discard / Stay with unsaved edits; the Save
  button saves and closes. Connections tab (tab 4): Incoming / Outgoing rows
  with what flows, Vault reads with their writers; Enter jumps to that node's
  editor. W/S move by rows and keep the column where widgets sit side by
  side (Branch path rows: Branch ID | Start Payload).
- **Names and IDs:** nodes show alias or type name everywhere; the node ID is
  its own line (node editor under the title, editor details panel). Error
  and validation messages open with `Name (Type) · depth N · branch`, then
  `Node ID:` (`frontend/node_location.py`). The numbered `·1000` suffix was
  tried and rolled back.
- **Keys:** one key-hint ribbon per panel, at the bottom. A/D cycle branch
  views and skip error recovery, except on a branch-select row, where they
  step through that node's own branches (error branches included); E there
  opens the branch selector.
- **Shared Vault model** `backend/vault_declarations.py`:
  `active_vault_reads`, `typed_vault_writes`, `active_vault_writes`,
  `standard_vault_reads`. Used by the Connections tab, the Vault pickers
  (`memory_registry`, the node config writer scan) and the validator's
  existence/type/race checks. Node-specific readers/writers are a
  `node_type` switch there (Get/Set Variable, Variable Reader/Setter,
  Conditional, Counter, Branch `vault:` seeds).

## Owner direction to keep in mind

- **Required vs optional** inputs, outputs and Vault reads will be defined
  when all nodes are re-touched soon; it sharpens as nodes are made and
  adjusted. Make it a declared property in the contract, not a per-node guess.
- **More data types** for Vault entries and dead-drop payloads, for community
  nodes; extend `backend/data_types.py` through the contract work, keep `any`
  for genuinely mixed values.
- **Help:** later, a per-panel `H` popup listing every key; the bottom ribbon
  shrinks to the basic movement keys plus `h help`.
- **Lazy loading** for busy editors (64-path Branch opens in ~0.55 s): show
  and make navigable what loads first, queue Save / Close until all is loaded.
- **Stable labels** matter once names appear in run history, logs or a
  second frontend.
- Owner taste: plain, compact UI; show sample screens (SVG via
  `App.save_screenshot`, sent with SendUserFile) before styling changes; the
  owner reviews them closely and often tests live (tmux, below).
- **No model names in commits or PRs** (owner rule; overrides default
  attribution lines).

## Next step

1. Report branch, HEAD and dirty state.
2. Done 2026-10-14: the owner approved C1–C7 (C8–C12 stay proposed), and
   **C1** (warnings for node-specific Vault reads with no writer, plus the
   required/optional flag in `vault_read_entries`) merged as PR #55. **C2**
   (one edge compatibility rule, `data_types.types_compatible`, plus
   "Type mismatch" warnings and clearer file-node runtime errors) merged
   as PR #56. C3, C5 and the authoring tool merged; C4, C6 (with
   Chat's Vault output off by default) and C7 are in their PRs. Next:
   the naming PR (in its PR), then Stash S1–S3 (see the plan's agreed
   order). A stacked PR must be retargeted to `main` before merging: the
   repo keeps merged branches, so GitHub doesn't retarget it (#66).
3. Then C2–C7 in order, one PR each, asking the owner where a phase needs a
   decision (C5's number policy, C6's field removal, C7's Deep Branch
   contract). Ask before starting Step 4 of `DISTRIBUTED_BUILD_PLAN.md`.

Known gaps worth a look while there: other editor graph walks may still
recurse once per node (for example `_find_branch_choices_to_node`); the
user-input prompt during a run still shows a raw node ID.

## Working practice that worked this session

- **Per phase:** branch from `main`; reproduce first; tests that fail on the
  old code; full suite (background), `compileall`, `git diff --check`;
  adversarial self-review; docs (`SESSION_LOG.md`, the plan's status, the
  named docs, this file's "Where things stand"); open the PR with `gh`; the
  **owner merges** (the auto-mode classifier blocks agent merges).
- **Editing on the WSL share:** Edit/Write can fail with `EUNKNOWN ...
  ftruncate`. Write a patch script to the scratchpad, copy it into
  `/tmp/<dir>/` in WSL and run it there with exact one-match replacements
  (`newline=""`). Avoid heredocs for Python containing apostrophes or `\n`:
  write the script with the Write tool instead.
- **Shared terminal:** run the app in tmux so the agent can read it:
  `wsl -e tmux new-session -A -s aotn -c /home/makin/src/node_workflow/AttackOfTheNodes /home/makin/src/node_workflow/.venv/bin/python main.py`.
  The agent reads panel tabs with the terminal tools; it cannot see Windows
  Terminal. Restart the app after pulling new code.
- **Reviews:** the owner often pastes external review or audit reports.
  Reproduce each finding before fixing; record what was fixed, what was
  deferred and why.

## Paste this into the new session

```
Continue AttackOfTheNodes work. Work only in /home/makin/src/node_workflow
(WSL). Read and follow AttackOfTheNodes/docs/NODE_CONTRACT_EXECUTION_PROMPT.md
completely: it lists what to read, where things stand after the UX detour,
the owner's direction, the next step and the working practice (environment,
WSL editing workaround, shared tmux terminal). The hard rules and environment
notes in RECOVERY_UX_EXECUTION_PROMPT.md still apply.

First report: branch, HEAD, dirty state. Then confirm with me that the node
contract plan starts now, and begin C1 (preflight warnings for node-specific
Vault reads with no writer, plus a required/optional flag in the shared Vault
model). One PR per phase; I merge. Ask me before Step 4 of
DISTRIBUTED_BUILD_PLAN.md.

I prefer plain, compact UI; show sample screens before styling changes.
No model names in commits or PRs.
```
