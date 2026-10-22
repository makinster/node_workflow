# Current State

Snapshot checked **2026-10-22**, against fetched `origin/main` `cce4fc7` and
PR #110 on GitHub. Code and fresh GitHub checks take precedence.
This is the live status snapshot; plans and logs preserve dated decisions.
Live deployment facts below come from the owner's shared notes and confirmed
delivery; this documentation refresh did not change or rerun live jobs.

## Baseline and open work — 2026-10-22

- **H0 live (#103/#106):** the adapter and installed wrappers run from
  `/home/makin/src/aotn-live` with the isolated cron library at
  `~/.local/share/aotn-cron`. Heartbeat job `63968ee90ae0` runs
  `aotn-h1-heartbeat.sh`, no-agent, daily at 09:00 America/Los_Angeles,
  delivering to Telegram's `home` alias. Installed copies were checked;
  `cron.wrap_response` remains on. The [adapter guide](../integrations/hermes/README.md)
  and [H0 contract](integrations/HERMES_H0_DRAFT.md) describe escaping, limits,
  exit codes, locking and descendant cleanup. Earlier test/probe receipts are
  retained in [Session Log](SESSION_LOG.md).
- **H2 parked:** the watchdog remains an **unscheduled template** until the
  owner chooses a real service and updates its URL. Throwaway adapter checks
  exercised success/failure responses; they did not enable a watchdog job.
- **C1 merged and live (#109):** Notify me and Record event write the
  [Hermes shared folder](integrations/HERMES_SHARED_FOLDER.md),
  `$HERMES_HOME/aotn` (default `~/.hermes/aotn`). The live checkout was updated
  and the drain installed. No-agent drain job `cd14afa83db9` runs every five
  minutes (`*/5 * * * *`) to Telegram `home`; the owner confirmed receipt of
  the end-to-end test message. The outbox was emptied and its `handed_off`
  receipt recorded; no reconciler supplies a `delivered` stage yet. The retained
  `c1-notify-test` workflow is available in the cron data directory for future
  checks. Send to names are configured in Options. Urgent sorts first with ⚠;
  per-job notification sound still needs a Hermes change (proposal Q7).
- **C4 merged (#107/#108):** [local stdio MCP](integrations/MCP.md) exposes
  four typed execution/history tools using the standard library. Contracts and
  Stash inputs, unattended termination/C25 checks and isolated timed workers
  are implemented. The stdin-from-file follow-up exits 64 with a one-line
  diagnostic. Current tools do not create/edit workflows, provide live progress
  or bridge interactive replies; adding authoring tools is a future designer
  step, not already implemented behavior.
- **C2 open as [PR #110](https://github.com/makinster/node_workflow/pull/110):**
  Saved values, branch `dist/persistent-store`, head `a685821`. Remember,
  Recall and If changed, the Stash Saved values tab, CLI and store-locking/
  validation changes remain outside main. Re-check found the original eight
  findings fixed and a new **P1**: numeric overflow can make the whole store
  unreadable. Its fix is pending; owner merge is still required. The author
  reports 2,244 tests passed at that head; this documentation task did not rerun
  that suite.
- **C3a built, awaiting owner review (2026-10-22):** branch `dist/pick-one`
  from main `cce4fc7`. Jev: Pick one, `backend/integrations/jev.py`, helper
  spec/generated checks, exact answer rows, fixed `unsure` below 0.3, optional
  Vault-only details. No provider/model selectors or Stop option. Shared
  routing now preserves each Vault output and omits Vault-only branch names.
  The standard Forward incoming payload unchanged control replaces only the
  downstream answer, preserving enabled Vault outputs.
  [Built screens](audits/pick_one_2026_10_22/README.md),
  [node contract](NODE_STANDARDS.md#bounded-choice-node-c3a-owner-2026-10-22).
  Full suite after the forwarding correction: **2,228 passed**; helper and docs checks passed. No paid call,
  owner/live data, installed wrapper, cron job or repository workflow change.
- **Owner plan reset (2026-10-22):** C2 → C3a Jev: Pick one → thin Telegram
  launcher → C3b bounded agents → 4e–4f → P1 → Phase 17 verification → C5 →
  Step 5 → C6 → Step 6. See the
  [approved order and idea mapping](AI_COORDINATION_PROPOSAL.md#9-effect-on-the-build-plan-owner-order-2026-10-22).
  Hermes confirmed `quick_commands` with `type: exec` (source `556bf7c5c`):
  fixed scripts run after normal sender authorization, with no agent turn,
  plugin or arguments. Config is the workflow allowlist; use one
  `aotn-run-<slug>.sh` entry per allowed workflow, deriving the slug from its
  filename. The 30 s reply timeout does not kill the script, so the entry must
  enforce its own deadline under 30 s and kill/reap on timeout. Natural-language
  menus later still need a plugin or an agent turn.
  The designer is a new track after C3; local-model comparison follows
  C3a. The [archived discussion](archive/plans/INTENT_ROUTING_AND_DESIGN_ASSISTANT.md)
  preserves context rather than setting a competing work order.
- Merged baseline includes C1–C7 decisions (#102), workflow naming (#68), docs A/B
  (#69/#72), Stash S1–S3 (#70/#71/#75), window buttons (#73), duplicate
  prevention (#74), keymap phases 1/2 (#77/#78), contracts (#80), the
  file-picker test fix (#81), editor hotfixes (#82), the deletion proposal
  (#84), docs C (#83), deletion answers (#86), subworkflow screens (#85),
  child runs (#87), deletion phase 2 (#88), picker polish (#90) and the
  Execution screen (#89), including its review fixes, are merged.
  S3 uses plain P, off while typing; Ctrl+P and the palette are unchanged.
- **Editor hotfixes (#82):** insert before a node with two parents keeps it;
  HTTP Request and JSON Path get no error path by default; failure paths keep
  the normal path's colour; deleting a node with an error handler asks, then
  removes the handler; undo and stub removal never give an output a second
  target. [Session log](SESSION_LOG.md).
- **Deletion review phase 2:** merged in #88. First delete groups owned paths;
  Z restores the group, with a preview before partial restore. Branch count
  reductions save removed paths under the live Branch; increases offer
  Recover / Leave empty / Cancel and optional path picks. Keep saved paths
  until the owner sets expiry. Every affected Beacon resets on Merge deletion;
  Beacon deletion ends its branch. Warning levels stay unchanged. The editor
  shows ` [sub]` for callable workflows. No `node_config.py` or Execution
  screen changes. The review follow-up (#90, merged) fits picker lists to their rows,
  shortens the new messages and reformats the two deletion test files.
  [Compact picker samples](audits/deletion_picker_polish_2026_10_19/README.md),
  [approved proposal](DELETION_REVIEW_PROPOSAL.md),
  [rendered screens and verification](audits/deletion_phase2_2026_10_19/README.md).
- **Step 4:** design rev. 4 approved (#76/#79); 4a-1 backend/CLI contracts
  built (#80). 4a-2 screens merged in #85: File window Workflows/Subworkflows
  tabs, copy to Subworkflows, Start Inputs and Results tabs, the End Results
  tab, "Send back to calling workflow". 4b child runs (backend and CLI) merged
  in #87: the Subworkflow node, call tree,
  limits (depth 4, 64 live), file hand-over, prompts, pause and stop, run
  records, validation and benchmark. EX (the Execution screen overhaul)
  merged in #89, with its review fixes. 4c-1 (the Subworkflow node in Node
  Config: Inputs and Payloads tabs, the picker, the map's `Greet (Greeter [sub])`
  and `➥ (n)`, the details pane; the node is in the selector) merged in #91, with
  its review fixes. 4c-2 (opening a running call
  from the Execution screen with E/Enter, breadcrumbs, prompts that say who
  asks) merged in #94, with its review fixes. The prompt queue (C19: a
  second prompt waits for the first instead of being dropped) merged in #96.
  4d (Stash entries as Subworkflow node inputs and `--input key=@stash:name`;
  per-machine bindings dropped, owner 2026-10-20) merged in #101.
  Left in Step 4: 4e/4f shared memory.
  [Proposal](SUBWORKFLOWS_PROPOSAL.md).
- **Keymap phase 3 — Editor/Execution:** merged in #92.
  Both screens already compiled bindings from profiles; Help and status hints
  now use those same definitions and native key overrides. Current keys and
  default compact hint wording are unchanged. Execution Help now lists X Stop,
  W/S movement, A/D paths, F Follow and V error panel. W/S scrolls Help while
  Close stays visible. [Before/after text and verification](audits/keymap_phase3_2026_10_20/README.md).
  Other Help contexts remain unchanged. Node Config, Node Selector and Workflow
  Library presentation remain separate work. Settings rebinding UI and generated
  Quick Reference tables remain deferred.
  [Scope](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
- **Modals fill the terminal** (owner, 2026-10-20), merged in #93: Node
  Config, the node selector, large viewers, Help, Options and the File
  window use the whole terminal; taller dialogs scroll to their buttons.
- Work order: [Node Contract Plan](NODE_CONTRACT_PLAN.md). Long-term direction:
  [Distributed Plan](DISTRIBUTED_BUILD_PLAN.md), [Stash](STASH_PROPOSAL.md).
  The owner merges, or explicitly asks a reviewer to.

## Verification and environment — 2026-10-22

- This refresh passed the documentation consolidation checker and
  `git diff --check`. Full-suite figures below are historical receipts, not a
  current-main test result. No live job or application behavior was changed.

- Prompt queue slice: **1,918 passed in 301.82s**, three new tests in
  `tests/test_prompt_queue.py`.
- This keymap phase-3 slice: **1,884 passed in 277.58s**. Twelve new tests cover
  generated Help, unchanged keys/hints, punctuation/control-key spelling,
  effective rebindings, modal isolation and keyboard scrolling at
  60/100/140 columns. Profile definitions for APP, EDITOR and EXECUTION are
  unchanged (AST comparison). No Node Config or workflow edits.

- Main `b5426ab` includes #88: **1848 passed in 265.69s (0:04:25)**.
  Picker follow-up (#90): **1856 passed in 265.73s (0:04:25)**. EX (#89)
  with its review fixes, merged with #90: **1872 passed in 281.21s (0:04:41)**. The 55 phase-2 tests
  cover topology, durable recovery,
  stale plans, conflicts and mounted form/picker flows. Production CSS and
  actual keys checked at 60/100/140 columns; SVG and text captures retained.
  The follow-up adds eight failing-first checks for compact geometry, wrapped
  rows on resize and the requested wording. Both reformatted test files retain
  their original assertions and setup (AST comparison). Tests set
  `AOTN_DATA_DIR` before importing the backend.
- Link/anchor, whole-archive and session-transfer checks: see
  [PR C verification](audits/docs_audit_2026_10_17/PR_C_VERIFICATION.md).
  The active set is 17 core docs plus SUBWORKFLOWS_PROPOSAL,
  DELETION_REVIEW_PROPOSAL and AI_COORDINATION_PROPOSAL, each archived when its
  work completes or is declined. The coordination owner decisions are recorded
  in section 10, with the October 22 work-order reset in section 9. The longer
  intent/designer conversation is already an archived reference.
- Prior receipts: keymap phase 2, 1666 passed with actual-keypress tests;
  phase 1, 1605 passed (57 focused); Stash S3, 1548 passed. Docs B retained
  33 archive bodies. These are historical counts, not the current suite.
- Python **3.14.4**, Textual **8.2.7**, pytest **9.1.0**; shared interpreter
  `/home/makin/src/node_workflow/.venv/bin/python`. Other workers' checkouts and
  owner workflows are not edited; the OneDrive checkout is recovery-only.
- Clean installation, native terminal/live geometry, native Windows FO7 and
  external web links were not reverified. Owner FO7 results are still needed.

## Open owner decisions and evidence limits — 2026-10-22

- Stash: file fields accept file entries; text fields accept text only.
  Global-only versus per-workflow pinning remains open (proposal question 3).
- Deletion Q1–Q5 answered October 19: keep/reset every affected Beacon, end a
  deleted Beacon's branch, preview partial restore, save removed Branch paths
  and offer optional recovery, preserve warning levels. Owner approved #86;
  phase 2 merged in #88; its small review follow-up merged in #90. Saved-path
  expiry remains undecided, so retain
  entries for now.
- Only the retained audit report survived; original CSVs/evidence are absent.
  The rebuilt source map and whole archives preserve the migration trail.
  [Recent log](SESSION_LOG.md); [older history](archive/SESSION_LOG_HISTORY.md).
