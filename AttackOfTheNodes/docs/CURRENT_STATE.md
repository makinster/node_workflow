# Current State

Snapshot checked **2026-10-19**. Code and fresh GitHub checks take precedence.
This is the live status snapshot; plans and logs preserve dated decisions.

## Baseline and open work — 2026-10-19

- Fetched `origin/main` at `1addbf9`: C1–C7, workflow naming (#68), docs A/B
  (#69/#72), Stash S1–S3 (#70/#71/#75), window buttons (#73), duplicate
  prevention (#74), keymap phases 1/2 (#77/#78), contracts (#80), the
  file-picker test fix (#81), editor hotfixes (#82), the deletion proposal
  (#84) and docs C (#83) are merged.
  S3 uses plain P, off while typing; Ctrl+P and the palette are unchanged.
- **Editor hotfixes (#82):** insert before a node with two parents keeps it;
  HTTP Request and JSON Path get no error path by default; failure paths keep
  the normal path's colour; deleting a node with an error handler asks, then
  removes the handler; undo and stub removal never give an output a second
  target. [Session log](SESSION_LOG.md).
- **Deletion review:** original [proposal](DELETION_REVIEW_PROPOSAL.md) merged
  (#84). The October 19 owner answers and revised recovery windows await review
  in this docs update. Phase 2 waits for that approval and #85 merging, then
  starts from fresh main: grouped delete, partial restore after a conflict
  preview, exact-count keep picker, saved paths under a live Branch and optional
  recovery when its count rises. Keep saved paths until the owner sets expiry.
  Unconnected Beacon and unreachable warnings do not block runs. Ownership:
  Editor (including ` [sub]` header), editor adapter, error-mux helpers and keep
  picker; no `node_config.py` edits.
- **Step 4:** design rev. 4 approved (#76/#79); 4a-1 backend/CLI contracts
  built (#80). 4a-2 screens merged in #85: File window Workflows/Subworkflows
  tabs, copy to Subworkflows, Start Inputs and Results tabs, the End Results
  tab, "Send back to calling workflow". 4b child runs (backend and CLI) merged
  in #87: the Subworkflow node (hidden in the selector until 4c), call tree,
  limits (depth 4, 64 live), file hand-over, prompts, pause and stop, run
  records, validation and benchmark. Next: EX design, then 4c (TUI).
  [Proposal](SUBWORKFLOWS_PROPOSAL.md).
- Keymap phase 3 is next for Stash, Settings, Execution, list pickers, Confirm
  hints, Unsaved Changes, User Input and Recovery. Editor, Node Config,
  Node Selector, Workflow Library and Help topics follow after 4a-2 merges.
  Read-only viewers, generated reference tables/source checks and Settings
  rebinding UI remain deferred. [Scope](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
- Work order: [Node Contract Plan](NODE_CONTRACT_PLAN.md). Long-term direction:
  [Distributed Plan](DISTRIBUTED_BUILD_PLAN.md), [Stash](STASH_PROPOSAL.md).
  The owner merges, or explicitly asks a reviewer to.

## Verification and environment — 2026-10-19

- This docs update on main `1addbf9`: full suite **1729 passed in 228.35s**;
  docs link/archive checks pass. #85 at `afe98cd`: **1759 passed in 230.79s**,
  with the additional file-default probe failure recorded above and in the log.
- Link/anchor, whole-archive and session-transfer checks: see
  [PR C verification](audits/docs_audit_2026_10_17/PR_C_VERIFICATION.md).
  The active set is 17 core docs plus SUBWORKFLOWS_PROPOSAL and
  DELETION_REVIEW_PROPOSAL, each archived when its work completes.
- Prior receipts: keymap phase 2, 1666 passed with actual-keypress tests;
  phase 1, 1605 passed (57 focused); Stash S3, 1548 passed. Docs B retained
  33 archive bodies. These are historical counts, not the current suite.
- Python **3.14.4**, Textual **8.2.7**, pytest **9.1.0**; shared interpreter
  `/home/makin/src/node_workflow/.venv/bin/python`. Other workers' checkouts and
  owner workflows are not edited; the OneDrive checkout is recovery-only.
- Clean installation, native terminal/live geometry, native Windows FO7 and
  external web links were not reverified. Owner FO7 results are still needed.

## Open owner decisions and evidence limits — 2026-10-19

- Stash: file fields accept file entries; text fields accept text only.
  Global-only versus per-workflow pinning remains open (proposal question 3).
- End is CLI-authorable but hidden in the current selector. Exposure is part
  of the 4a-2 UI work.
- Deletion Q1–Q5 answered October 19: keep/reset every affected Beacon, end a
  deleted Beacon's branch, preview partial restore, save removed Branch paths
  and offer optional recovery, preserve warning levels. Revised screens await
  approval; saved-path expiry remains undecided, so retain entries for now.
- Only the retained audit report survived; original CSVs/evidence are absent.
  The rebuilt source map and whole archives preserve the migration trail.
  [Recent log](SESSION_LOG.md); [older history](archive/SESSION_LOG_HISTORY.md).
