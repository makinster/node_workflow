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
- **Python:** `/home/makin/src/node_workflow/.venv/bin/python`. Run pytest
  from `AttackOfTheNodes/` with `-p no:cacheprovider`. The full suite
  (about 1050 tests) takes about 2.5 minutes.
- **Quoting:** inline Python inside `bash -c '...'` breaks on apostrophes.
  Write patch scripts to the scratchpad, copy them to `/tmp/<dir>/` in WSL
  (`mkdir` there through `wsl.exe` first), and run them there. New files must
  have LF line endings.
- **PRs:** there is no `gh`. Open and merge in the built-in browser:
  `https://github.com/makinster/node_workflow/compare/main...<branch>?quick_pull=1&title=...`,
  fill the "Comment" textbox, click the visible "Create pull request"
  button, then "Merge pull request" and "Confirm merge".
- **Flaky tests:** `test_refresh_coalescer`, `test_file_picker_export_and_import_paths`
  and `test_error_details_navigation` are timing-sensitive under full-suite
  load. If one fails, rerun it alone and against `main` before concluding
  anything.
- **Mounted UI checks:** push the screen in `on_mount` (`self.push_screen`)
  and query with `app.screen.query_one`, using `CSS_PATH =
  frontend/styles.tcss`. `App.save_screenshot` gives an SVG for visual
  review.

Start by checking branch, HEAD, dirty state and PR #43's status, then
reproduce the UX1 bug with the probe described in the plan.

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
- Owner answers (2026-10-13): Q1, Q9, Q10, Q11 take the defaults (check in
  after UX6; keep 64; leave the `dist/*` branches; leave history). The owner
  also said the saved workflows under `workflows/` are unimportant and need
  not be preserved. Q2–Q8 are asked when their phase reaches them.

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
