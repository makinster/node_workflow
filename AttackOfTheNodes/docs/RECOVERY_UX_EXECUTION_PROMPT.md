# Prompt for the next agent session (Recovery/Editor UX detour)

Paste everything below the line into a new session.

---

Continue AttackOfTheNodes work in the authoritative checkout
`/home/makin/src/node_workflow`. The OneDrive copy is recovery-only: never
develop, test or delete there.

**Read first, in this order:**
1. `AGENTS.md` (repo root).
2. `AttackOfTheNodes/docs/RECOVERY_UX_BUILD_PLAN.md`: the approved plan and
   owner decisions U1–U10. It is binding.
3. `AttackOfTheNodes/docs/SESSION_LOG.md`, the entries from "P0" onward.
4. `AttackOfTheNodes/docs/DISTRIBUTED_EXECUTION_PROMPT.md`: the process and
   hard rules, which still apply.
5. `BACKEND_FRONTEND_BOUNDARY.md` before any backend change made for UI
   behaviour.

Older handoffs, `SESSION_SUMMARY.md` and `EXECUTION_STATUS_CONTRACT.md` lag
the code. When sources disagree, trust the code first, then the recent
session log, then older plans.

**Task:** execute UX1 → UX6 from the plan, in order, one PR per phase (UX2
finishes and merges the open PR #43). Then stop and report. Ask the owner
before starting Step 4 of `DISTRIBUTED_BUILD_PLAN.md`, unless they already
gave the go-ahead in this session.

**Per phase:**
- branch from the latest `main` (UX2 works on `dist/p4-inline-error-mux`
  with `main` merged in);
- reproduce the problem first (probe scripts are listed in the plan);
- write tests that fail on the old code;
- run the full suite, `compileall` and `git diff --check`;
- run `check_node.py` and `check_ui.py` for each touched helper node;
- do an adversarial self-review, and log what it caught;
- update the docs, including the status column of the plan's phase table;
- open the PR, then merge it with a merge commit;
- if the code contradicts the plan, or a decision is ambiguous, stop and ask.

**Hard rules:**
- Backend code never imports from `frontend/`.
- EventBus payloads are JSON-serializable and carry `run_id`.
- Never skip, weaken or delete a test to get green. When a test encodes
  behaviour the owner explicitly changed, update it to assert the new
  behaviour precisely, and say so in `SESSION_LOG.md`.
- Change helper-generated nodes through their spec in `aotn_node_helper/specs/`
  and regenerate with `create_node.py <spec> --force`. Then restore the
  custom body (everything from the class's custom hooks / `async def
  execute` onward) and the custom cases in the node's generated test.
- Never modify the owner's saved workflows under
  `AttackOfTheNodes/workflows/` (gitignored). Read-only checks are fine.
  The owner may be running the app at the same time.
- **Do not put model identifiers in commits, PRs or code.** This is the
  owner's rule and it overrides any default attribution line. Earlier P0–P4
  commits included one by mistake; do not repeat it.
- Do not commit `.claude/launch.json` or the stray untracked files
  (`AttackOfTheNodes/"C:\...\test.txt"`, `AttackOfTheNodes/Workflow started`).
- Commit the two new plan docs (`RECOVERY_UX_BUILD_PLAN.md`,
  `RECOVERY_UX_EXECUTION_PROMPT.md`) with the UX1 PR.

**Environment notes:**
- **Run git inside WSL**, not Windows git:
  `MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu --cd /home/makin/src/node_workflow --exec bash -c '...'`.
- **Push:** prepend `export PATH="/mnt/c/Program Files/Git/bin:$PATH";` so
  the credential helper works.
- **Python:** `/home/makin/src/node_workflow/.venv/bin/python` (use the
  absolute path; `../.venv/bin/python` prints harmless prefix warnings). Run
  pytest from `AttackOfTheNodes/` with `-p no:cacheprovider`. The full suite
  (1212 tests on 2026-10-13) takes about 3 minutes; run it in the background.
- **Quoting:** inline Python inside `bash -c '...'` breaks on apostrophes.
  Write patch scripts to the scratchpad, copy them to `/tmp/<dir>/` in WSL
  (`mkdir` there through `wsl.exe` first), and run them there. New files must
  have LF line endings.
- **Editing files:** the Edit/Write tools on the `\\wsl.localhost` share
  fail intermittently (`EUNKNOWN ... ftruncate`, the file is left intact).
  What worked all session: a small `apply.py <target> <patch.py>` script
  that applies exact one-match `(old, new)` replacements inside WSL
  (recreate it: for each pair assert the old text occurs exactly once,
  replace, write back with `newline=""`). Windows
  git shows many files as modified (CRLF noise); trust WSL `git status`.
- **PRs:** the Windows GitHub CLI works since 2026-10-13 (logged in as
  makinster; not installed inside WSL). From Git Bash:
  `gh pr create --repo makinster/node_workflow --base main --head <branch> --title "..." --body-file <file>`
  then `gh pr merge <N> --repo makinster/node_workflow --merge`. The browser
  pane is only a fallback; its GitHub sign-in can be lost, and you must never
  sign in for the owner.
- **Flaky tests:** `test_refresh_coalescer`, `test_file_picker_export_and_import_paths`
  and `test_error_details_navigation` are timing-sensitive under full-suite
  load. If one fails, rerun it alone and against `main` before concluding
  anything.
- **Mounted UI checks:** push the screen in `on_mount` (`self.push_screen`)
  and query with `app.screen.query_one`, using `CSS_PATH =
  frontend/styles.tcss`. `App.save_screenshot` gives an SVG for visual
  review.

Start by checking branch, HEAD and dirty state, then continue from the
last entry of **Current position** below.

## Current position

Update this section at the end of every session.

- **2026-10-13 (start):** the plan was written and no UX phase had started.
  `main` was at `09a1402`; PR #43 open on `dist/p4-inline-error-mux` at
  `3038634`.
- **2026-10-13 (UX1 done):** UX1 merged in PR #44 (branch
  `dist/ux1-merge-branch-identity`), which also committed these two plan
  docs. Suite: 1071 passed on `main`. PR #43 is still open and unchanged.
  **Next:** UX2. Check out `dist/p4-inline-error-mux`, merge `main` into it
  (expect conflicts in `SESSION_LOG.md` and possibly `node_config.py`), then
  run `aotn_review43_probe.py` to reproduce the three #43 bugs.
- **2026-10-13 (UX2 done):** `main` merged into `dist/p4-inline-error-mux`,
  the three #43 bugs fixed plus the no-edit-save invariant, and PR #43
  merged. Suite: 1124 passed. **Next:** UX3 (measured performance), branch
  from `main`; start by recording the "before" numbers with
  `aotn_review43_perf.py` and the Branch timings in `aotn_review43_probe.py`.
  UX3 part 3 needs Q3 (default: the largest saved workflow, read-only).
- **2026-10-13 (UX3 done):** merged in PR #45. Q3 answered: a synthetic
  wide graph (the saved workflows are 5–10 nodes). The owner accepted the
  64-branch open at ~0.6 s and moved lighter Branch rows into UX6. **Next:**
  UX4 (recovery flow from the originating node), branch from `main`. It
  needs Q5 (show both widget placements as samples) and Q6/Q7 when reached.
- **2026-10-13 (bug fix):** PR #46 fixed Branch-tombstone deletion losing
  or stranding nodes after Output-family nodes (owner report).
- **2026-10-13 (UX4 done):** merged in PR #47. Q5 (button under the Errors
  header, simplified, "Add Error Resolver Node"), Q6 (default rule) and Q7
  (insert between; downstream on No error) answered; the Error Mux's default
  alias is now "Error Resolver". **Next:** UX5 (Connections tab with jumps,
  Ctrl+Space, Save/Discard/Stay), branch from `main`. It needs Q2 (fallback
  key, after testing how Ctrl+Space arrives) and Q4 (the "missing
  connections" details) when reached.
- **2026-10-13 (UX4 follow-ups):** PR #48 removed "Any other error" from the
  picker and made picker lines `[code] description`; PR #49 keeps a/d off
  error recovery (`e` on the resolver's branch-select row opens it). Q4 is
  resolved by PR #46 (owner can no longer reproduce). Q2: bind `ctrl+space`
  and `ctrl+@`; F2 proposed as fallback, waiting for the owner's key check.
- **2026-10-13 (handoff, end of session):** `main` at the merge of this
  docs PR, after `d820939` (PR #49). All UX work is merged; no branch is in
  progress. Suite: 1212 passed. **Next: UX5**, branch from `main`
  (`dist/ux5-connections-and-saving`), one PR:
  1. Connections tab (node config tab 4): incoming and outgoing rows with
     node names, port display names and what flows (a payload, or "No
     payload"); Vault reads in their own list; each row focusable, Enter
     jumps to that node's editor; refresh after edits that change ports. It
     replaces today's `#connection-summary` text (which UX2 made refresh on
     mux picks). The Errors section with the **Add/Open Error Resolver
     Node** button stays on that tab.
  2. Save and stay (U3): bind both `ctrl+space` and `ctrl+@` (Textual turns
     the NUL byte most terminals send for Ctrl+Space into `ctrl+@`; the kitty
     protocol sends `ctrl+space`), plus **F2** as the fallback (Q2 proposal).
     In a `CommandTextArea` it also commits the text and leaves editing;
     Enter stays a newline. Ctrl+S keeps saving and closing. Document both in
     `UI_QUICK_REFERENCE.md`. The owner has not yet run the key check:
     `wsl -d Ubuntu /home/makin/src/node_workflow/.venv/bin/textual keys`,
     pressing Ctrl+Space and F2, in Windows Terminal and the browser
     session; ask for the result before finalising the fallback. (The owner
     never asked for Ctrl+@ itself; it is only how Ctrl+Space arrives.)
  3. Save / Discard / Stay (U9) when jumping away with unsaved changes;
     "unsaved" compares `_collected_config()` with the screen's
     `_opened_config` snapshot (UX2).
  4. Mounted tests: jump, the dirty prompt, save-and-stay, committing a text
     area with the new key; record the owner's manual terminal check.
  Then **UX6** (friendly labels U5 with Q8, and the presentation pass incl.
  lighter Branch rows; sample screens first), then stop and check in (Q1)
  before Step 4.
- **2026-10-13 (UX5 done):** merged in PR #51 (branch
  `dist/ux5-connections-and-saving`). Q2 replaced by an owner decision:
  Ctrl+S (and Ctrl+Enter) saves and stays, Esc closes with Save / Discard /
  Stay; no Ctrl+Space or F2. Four P2 review findings fixed on the branch
  (row focus by identity, shared Vault read/write model in
  `backend/vault_declarations.py`, error-port payload), then the node audit's
  Vault finding (pickers and validator on the same writer list). Suite: 1240
  passed. Manual checks passed in the app panel and Windows Terminal. The
  rest of the node audit is `NODE_CONTRACT_PLAN.md` (proposed; ask the owner
  when to schedule it — after UX6 or before Step 4). The owner's live-test
  findings are in `PROJECT_BACKLOG.md` ("Owner live-test findings —
  2026-10-13"); not part of UX6 unless the owner says so. **Next: UX6**,
  branch from `main` (`dist/ux6-labels-and-presentation`): friendly labels
  (U5) — ask Q8 (suffix format) first; then the presentation pass (lighter
  Branch rows, compact tab labels, no duplicate shortcut line, shorter
  Errors text, smaller Save/Cancel buttons, consistent focus styling, maybe
  renaming Cancel to Close now that Ctrl+S stays). Show 2–3 sample SVGs
  before styling changes. Then stop and check in (Q1) before Step 4.
- **2026-10-13 (UX6 done):** merged in PR #52 (branch
  `dist/ux6-labels-and-presentation`). Q8 answered (suffix ` ·1000`, ` ·1001`
  for repeated names; revisit later). Suite: 1244 passed. **The UX detour is
  complete.** Q1 (check in before Step 4) still applies. The owner chose, by
  best judgement, to run `NODE_CONTRACT_PLAN.md` after UX6 and before Step 4,
  starting with C1–C7; that plan is still marked proposed, so the next session
  confirms with the owner before starting C1. Open follow-ups: lazy loading
  for busy editors (`PROJECT_BACKLOG.md`, owner findings item 7).
- **Owner UI taste (learned in UX4):** plain and simple. Compact one-row
  buttons (Textual `Button(..., compact=True)`), no extra status lines,
  error lines code first (`• [code] description`), and the Error Mux is
  called **Error Resolver** in the UI (type name stays Error Mux; default
  alias "Error Resolver"). Show sample SVGs (`App.save_screenshot`, sent with
  SendUserFile) before styling changes; the owner reviews them closely.
- **Watch item (not reproduced):** the owner once saw a newly added Error
  Resolver missing from the editor after tab 4 → Add Error Resolver Node →
  pick an error → save. A mounted probe of that exact path (No Op and HTTP
  Request) showed the resolver in the rows; the owner called it a fluke and
  will note the steps if it happens again. Do not claim a fix without a
  reproduction.
- Owner answers (2026-10-13): Q1, Q9, Q10, Q11 take the defaults (check in
  after UX6; keep 64; leave the `dist/*` branches; leave history). The owner
  also said the saved workflows under `workflows/` are unimportant and need
  not be preserved. Answered since: Q3 (synthetic graph), Q4 (resolved by
  PR #46), Q5, Q6, Q7 (see UX4 entries). Q2 was replaced in UX5 by
  the Ctrl+S decision; Q8 answered in UX6. None open.

## Continuing across sessions

When a session ends, or its context is about to run out:

1. Finish or park the current phase cleanly. Never leave the branch with
   failing tests. If a phase is unfinished, commit the work in progress on
   its branch, push it, and do not merge it.
2. Update the phase table in `RECOVERY_UX_BUILD_PLAN.md` (Not started / In
   progress on `<branch>` / Done in PR #N).
3. Add a `SESSION_LOG.md` entry: what changed, test counts before and
   after, behaviour changes, open items.
4. Update **Current position** above with the branch, HEAD, PR numbers and
   the next concrete step.
5. Tell the owner what is merged, what is pending, and any question from
   the list below that blocks the next phase.

The next session starts from the same message that started this one, with
no other context.

## Open questions and items needing owner input

Ask about these when the phase reaches them; do not guess.

| # | Question | Needed by | Default if the owner says "your call" |
|---|---|---|---|
| Q1 | After UX6, go straight into Step 4 or stop and check in? | End of UX6 | Stop and check in |
| Q2 | Fallback key for "save and stay" if Ctrl+Space does not reach the app in Windows Terminal or the browser session | UX5 | Pick a key that works in both, and document it |
| Q3 | A representative large workflow to profile the main editor | UX3, part 3 | Use the largest saved workflow, read-only |
| Q4 | Details of the "missing connections" report: which workflow and node, and which link was expected | UX5 | Investigate the stale summary first; do not claim a fix without a reproduction |
| Q5 | Where the "Catch errors…" widget goes: under the Errors header, or at the bottom of the error list | UX4 | Show both as sample screens, then use the one the owner picks |
| Q6 | "Delete branch" scope: delete only the nodes reachable through that route, stopping at any node also reachable another way (such as a Merge) | UX4 | That rule; the modal lists the nodes first |
| Q7 | The node's normal output already feeds other nodes besides a mux: insert a new mux (the plan) or offer the existing one? | UX4 | Insert a new mux (U7) |
| Q8 | Format of the suffix for duplicate labels (`Fetch ·2` or the last 4 ID characters) | UX6 | `·2`, numbered by order in the workflow |
| Q9 | Is 64 (the safety limit on Branch paths and Merge slots, set in P3b) acceptable? | Any time | Keep 64 |
| Q10 | Delete the merged `dist/*` branches, locally and on GitHub? | Any time | Leave them |
| Q11 | P0–P4 commit messages name a model, against the owner's rule. Leave history alone? | Any time | Leave history; follow the rule from now on |

## Known facts the owner already has (no action unless asked)

- The owner's workflow `wf_597a2a4f596f` feeds an Error Mux from Error Node's
  `default` output into the old `error` input, which is invalid. The owner
  will rewire it. Do not edit it.
- `wf_13cab8f84dd3.json` disappeared during the owner's own app session on
  2026-10-12. The owner was told about it.
