> Superseded by [CONTRIBUTING](../CONTRIBUTING.md), [DISTRIBUTED_BUILD_PLAN](../DISTRIBUTED_BUILD_PLAN.md) on 2026-10-17.
> Historical document retained whole; old status, permissions and designs below
> are not current instructions. See [Current State](../CURRENT_STATE.md).

> **Historical — superseded on 2026-10-17 by [Current State](../CURRENT_STATE.md)
> and the [newcomer process rules](../NEWCOMER_GUIDE.md#process-and-environment).**
> Do not paste or execute the instructions below. Completed phases and old
> merge permissions are historical; the owner merges. Retained whole for PR B extraction.

# Distributed Build Plan — Execution Prompt

Paste everything between the markers into a new session, together with
[DISTRIBUTED_BUILD_PLAN.md](../DISTRIBUTED_BUILD_PLAN.md). Authorized by the owner
on 2026-10-12 for steps 1, 1b, the refresh coalescer, 2, 3 and the ESP32 proof
slice. Step 4 onward needs a new go-ahead.

---8<--- PROMPT START ---8<---

You are implementing the approved AttackOfTheNodes (AOTN) distributed build
plan in the repo `makinster/node_workflow`. The plan is
`AttackOfTheNodes/docs/DISTRIBUTED_BUILD_PLAN.md`. It is attached, and it is
also on `main`.

## Goal and scope

Execute the plan in this order:

1. **Step 1** — bug fixes, as sub-fixes 1a (error-port routing), 1b-fix (Stop
   and the leak into the next run) and 1c (unattended policy). One commit each.
2. **Step 1b** — `RunContext`, WaitRegistry and delivery tracking (D5).
3. **Refresh coalescer** — frontend only.
4. **Step 2** — run service, `RecoveryPolicy`/`InputProvider`, configurable
   data directory, `aotn run` CLI.
5. **Step 3** — `[error]` routing: error codes, Errors section, error mux and
   skipped status (D7–D9).
6. **ESP32 proof slice** — binary-safe HTTP, run-owned temp files (R4),
   error routed to a notification.

**Stop after the ESP32 slice. Do not start step 4.**

The plan's decision record (D1–D9, R1–R4) is binding. Never reopen an option
it rejects. If the code contradicts the plan, or a decision is ambiguous or
missing, stop that step and report it; do not resolve it inline.

## Setup

1. Work from `AttackOfTheNodes/`. First read:
   - `../AGENTS.md`
   - `docs/README.md`
   - `docs/BACKEND_FRONTEND_BOUNDARY.md`
   - `docs/ARCHITECTURE.md`
   - `docs/SIGNAL_FLOW.md`
   - the whole of `docs/DISTRIBUTED_BUILD_PLAN.md`
2. Environment: if `../.venv` does not exist, create it. Then run
   `pip install -r requirements.lock` and `pip install -e .`.
3. Run the full suite on unchanged `main` and record the baseline count in
   `docs/SESSION_LOG.md` before changing anything.

## Per-step loop

Run steps strictly one after another. Do not start a step until the previous
one is merged.

1. `git fetch origin main`, then branch from the latest `main`. Name the
   branch after the step, for example `dist/step-1-bug-fixes`.
2. Implement only that step's scope as written in the plan, including its
   listed files and constraints.
3. Turn every test the plan lists for the step into a real test. Add
   regression tests for any bug you fix along the way.
4. Verify: run the full suite, `python -m compileall -q .`, and
   `git diff --check`. Then re-read your diff adversarially and fix anything
   CI or a reviewer would reject.
5. Update `docs/SESSION_LOG.md` and the docs the plan names for that step
   (for example `SIGNAL_FLOW.md`, `ARCHITECTURE.md`,
   `EXECUTION_STATUS_CONTRACT.md`, `NODE_STANDARDS.md`, `NODE_HELPER.md`).
   Mark the step done in `DISTRIBUTED_BUILD_PLAN.md` and the
   `MASTER_BUILD_PLAN.md` step table. Log every behavior change explicitly;
   the plan names the ones it already expects.
6. Open a PR to `main` that describes the step, its tests and its behavior
   changes. Once the full suite is green, merge it with a merge commit.
7. Start the next step from the updated `main`.

## Parallelism

- Use sub-agents freely for read-only exploration, for test writing, and for
  an independent review of each diff before merging.
- The coalescer is frontend only. It may run in its own worktree alongside
  step 1b or step 2, but it lands as its own PR.
- Never have two agents editing `backend/supervisor.py` or
  `backend/master_state.py` at the same time.

## Hard rules

- Backend code never imports from `frontend/`.
- EventBus payloads stay JSON-serializable and always carry `run_id`, plus
  `parent_run_id` where it applies.
- Never skip, disable, weaken or delete a test to get green.
- Change helper-generated nodes through their spec in `aotn_node_helper/` and
  regenerate per `docs/NODE_HELPER.md`, preserving custom runtime bodies.
  Run `check_node.py` and `check_ui.py` for each one.
- Never modify the owner's saved workflows under `workflows/`.
- Do not put model identifiers in commits, PRs or code.

## Done checks (in addition to each step's "Done when")

- **Step 1:** the 2026-10-09 probes, recorded in the plan's "Current-state
  facts", are regression tests and pass:
  - no silent routing of failures down `default`;
  - Stop releases a waiting Wait Until;
  - no wake-up leaks into the next run;
  - an unattended run never hangs on an error, an input request or a
    breakpoint.
- **Step 1b:**
  - the D5 structural unreachable rule, with no timeouts;
  - Wait Until fails instead of hanging when its target can no longer arrive;
  - scripts in `benchmarks/` exist and are not collected by a plain `pytest`
    run.
- **Coalescer:** the final frame after a run is correct, and refresh calls
  are bounded by the timer.
- **Step 2:** `aotn run <workflow>` works end to end and imports no Textual
  module on its path. The TUI behaves as before.
- **Step 3:**
  - D7 codes, with the default generic code;
  - D8 Errors section, with Connections kept;
  - D9 skipped status, spread and `not_taken`, and Wait Until failing with
    `engine.upstream_unreachable`;
  - both step 3 behavior changes logged.
- **ESP32 slice:**
  - proven against a local HTTP server serving a JPEG (the bytes are intact
    on disk) and against a failing endpoint (the error is routed to the
    notification node);
  - run-owned temp files are deleted on success and kept when the run fails.

## Final report

For each step, report:

- the PR link and merge commit;
- test counts before and after;
- behavior changes;
- any deviation from the plan and why;
- anything blocked or left open.

Finish with a short list of open items and risks for step 4.

---8<--- PROMPT END ---8<---
