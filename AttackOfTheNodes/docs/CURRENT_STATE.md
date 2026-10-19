# Current State

Snapshot checked **2026-10-18**. Code and fresh GitHub checks take precedence.
This is the live status snapshot; plans and logs preserve dated decisions.

## Baseline and open work — 2026-10-18

- Fresh `origin/main`: **90182f0**. C1–C7, workflow naming (#68), docs A/B
  (#69/#72), Stash S1–S3 (#70/#71/#75), window buttons (#73), duplicate
  prevention (#74), keymap phases 1/2 (#77/#78) and contracts (#80) are merged.
  S3 uses plain P, off while typing; Ctrl+P and the palette are unchanged.
- Open against main: **#81**, file-picker test teardown synchronization
  (`codex/file-picker-teardown`, reviewed OK per owner), and **#82**, editor
  fan-in/error-path fixes (`fix/insert-fan-in-error-path`). Both require their
  log/status entries retained by whoever integrates second. The owner or an
  explicitly requested reviewer merges.
- Docs PR C: `codex/docs-c`, based on 90182f0, in `/home/makin/src/nw-docs`.
  Bounds the active log after decision extraction; updates the reading route,
  audit check, Stash and contract documentation. #82's error-port bullet,
  HTTP/JSON Path catalog rows and owner-findings backlog section are preserved.
- Step 4 design rev. 4 is approved (#76/#79); 4a-1 backend/CLI contracts are
  built (#80), including typed --input and --inputs-file. 4a-2 screens are in
  progress separately in Node Config, Workflow Library, Editor, Help and App.
  Child-workflow calls remain later work. [Proposal](SUBWORKFLOWS_PROPOSAL.md).
- Keymap phase 3 is next for Stash, Settings, Execution, list pickers, Confirm
  hints, Unsaved Changes, User Input and Recovery. Editor, Node Config,
  Node Selector, Workflow Library and Help topics follow after 4a-2 merges.
  Read-only viewers, generated reference tables/source checks and Settings
  rebinding UI remain deferred. [Scope](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
- Work order: [Node Contract Plan](NODE_CONTRACT_PLAN.md). Long-term direction:
  [Distributed Plan](DISTRIBUTED_BUILD_PLAN.md), [Stash](STASH_PROPOSAL.md).

## Verification and environment — 2026-10-18

- Docs C full suite: **1708 passed in 223.15s** on 90182f0 plus docs changes.
  The known HeaderTitle flake did not occur in this run; its fix is still #81.
  Two authoring-doc specs build in isolated storage; the contract example
  returns `greeted = Kim` with typed CLI inputs. No application/tests changed.
- Link/anchor, whole-archive and session-transfer checks: see
  [PR C verification](audits/docs_audit_2026_10_17/PR_C_VERIFICATION.md).
  The active set is 17 core docs plus SUBWORKFLOWS_PROPOSAL, archived after Step 4.
- Prior receipts: keymap phase 2, 1666 passed with actual-keypress tests;
  phase 1, 1605 passed (57 focused); Stash S3, 1548 passed. Docs B retained
  33 archive bodies. These are historical counts, not the current suite.
- Python **3.14.4**, Textual **8.2.7**, pytest **9.1.0**; shared interpreter
  `/home/makin/src/node_workflow/.venv/bin/python`. Other workers' checkouts and
  owner workflows are not edited; the OneDrive checkout is recovery-only.
- Clean installation, native terminal/live geometry, native Windows FO7 and
  external web links were not reverified. Owner FO7 results are still needed.

## Open owner decisions and evidence limits — 2026-10-18

- Stash: file fields accept file entries; text fields accept text only.
  Global-only versus per-workflow pinning remains open (proposal question 3).
- End is CLI-authorable but hidden in the current selector. Exposure is part
  of the separate 4a-2 UI work; this docs PR does not change it.
- Only the retained audit report survived; original CSVs/evidence are absent.
  The rebuilt source map and whole archives preserve the migration trail.
  [Recent log](SESSION_LOG.md); [older history](archive/SESSION_LOG_HISTORY.md).
