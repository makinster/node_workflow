# Current State

Snapshot checked **2026-10-19**. Code and fresh GitHub checks take precedence.
This is the live status snapshot; plans and logs preserve dated decisions.

## Baseline and open work — 2026-10-19

- Fetched `origin/main` at `a31d721`: C1–C7, workflow naming (#68), docs A/B
  (#69/#72), Stash S1–S3 (#70/#71/#75), window buttons (#73), duplicate
  prevention (#74), keymap phases 1/2 (#77/#78), contracts (#80), the
  file-picker test fix (#81), editor hotfixes (#82), the deletion proposal
  (#84), docs C (#83), deletion answers (#86), subworkflow screens (#85)
  and child runs (#87) are merged.
  S3 uses plain P, off while typing; Ctrl+P and the palette are unchanged.
- **Editor hotfixes (#82):** insert before a node with two parents keeps it;
  HTTP Request and JSON Path get no error path by default; failure paths keep
  the normal path's colour; deleting a node with an error handler asks, then
  removes the handler; undo and stub removal never give an output a second
  target. [Session log](SESSION_LOG.md).
- **Deletion review phase 2:** implemented on `codex/deletion-phase2`, from
  fresh main `a31d721`, awaiting owner review. First delete groups owned paths;
  Z restores the group, with a preview before partial restore. Branch count
  reductions save removed paths under the live Branch; increases offer
  Recover / Leave empty / Cancel and optional path picks. Keep saved paths
  until the owner sets expiry. Every affected Beacon resets on Merge deletion;
  Beacon deletion ends its branch. Warning levels stay unchanged. The editor
  shows ` [sub]` for callable workflows. No `node_config.py` or Execution
  screen changes. [Approved proposal](DELETION_REVIEW_PROPOSAL.md),
  [rendered screens and verification](audits/deletion_phase2_2026_10_19/README.md).
- **Step 4:** design rev. 4 approved (#76/#79); 4a-1 backend/CLI contracts
  built (#80). 4a-2 screens merged in #85: File window Workflows/Subworkflows
  tabs, copy to Subworkflows, Start Inputs and Results tabs, the End Results
  tab, "Send back to calling workflow". 4b child runs (backend and CLI) merged
  in #87: the Subworkflow node (hidden in the selector until 4c), call tree,
  limits (depth 4, 64 live), file hand-over, prompts, pause and stop, run
  records, validation and benchmark. Next: EX design, then 4c (TUI).
  [Proposal](SUBWORKFLOWS_PROPOSAL.md).
- Keymap phase 3 follows the deletion PR: Node Config, Node Selector,
  Workflow Library and Help, now that 4a-2 is merged. Keep visible wording
  unchanged unless correcting a confirmed mismatch, with before/after text.
  Execution design and samples are separate work; neither task edits
  `frontend/screens/execution.py`. Other migration topics and Settings
  rebinding remain deferred. [Scope](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
- Work order: [Node Contract Plan](NODE_CONTRACT_PLAN.md). Long-term direction:
  [Distributed Plan](DISTRIBUTED_BUILD_PLAN.md), [Stash](STASH_PROPOSAL.md).
  The owner merges, or explicitly asks a reviewer to.

## Verification and environment — 2026-10-19

- Main `a31d721`: owner-reported full suite **1793 passed**. Deletion phase 2:
  **1848 passed in 265.69s (0:04:25)**; the 55 new tests cover topology, durable recovery,
  stale plans, conflicts and mounted form/picker flows. Production CSS and
  actual keys checked at 60/100/140 columns; SVG and text captures retained.
  Tests set `AOTN_DATA_DIR` before importing the backend.
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
- Deletion Q1–Q5 answered October 19: keep/reset every affected Beacon, end a
  deleted Beacon's branch, preview partial restore, save removed Branch paths
  and offer optional recovery, preserve warning levels. Owner approved #86;
  phase 2 awaits PR review. Saved-path expiry remains undecided, so retain
  entries for now.
- Only the retained audit report survived; original CSVs/evidence are absent.
  The rebuilt source map and whole archives preserve the migration trail.
  [Recent log](SESSION_LOG.md); [older history](archive/SESSION_LOG_HISTORY.md).
