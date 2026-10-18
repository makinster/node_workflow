# Current State

Snapshot checked **2026-10-18**. Code and fresh GitHub checks take precedence.
This is the only live status snapshot; older logs/plans retain dated history.

## Baseline and open work — 2026-10-18

- Phase-2 implementation base: fresh `origin/main` at `4cb246e` (keymap
  foundation #77, merged after approved Step 4 design #76). C1–C7 and workflow naming
  (#68) are merged; C7 has only `branch` and publishes its child payload.
- Merged: Stash S1 + `aotn stash` CLI (#70); Stash S2, the Stash screen
  (#71, `p` in the editor); docs PR B (#72: consolidation, VISION,
  CONTRIBUTING), confirm/close buttons in every window (#73), and Stash
  duplicates (#74: the same file or text is never stashed twice), and S3 field
  insert (#75: plain `P`, off while typing; Ctrl+P/palette unchanged).
- Keymap phase 1 is merged (#77). Awaiting review: phase 2 on
  `codex/keymap-policies`: multi-state command policies, native text/Select
  adapters and migrated App/high-traffic screens. The three listed defects have
  failing-first regressions and fixes: Node Config availability mutation,
  Execution's duplicate Stop route, Settings' duplicate digit route.
  Phase 3 generates Help/hints/tab labels; current visible text/layout is
  unchanged. Memory/Output/File viewers, generated reference tables/source
  checks and rebinding UI remain deferred.
  [Scope](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
  Step 4 design revision 3 is approved and merged in #76; backend/CLI stage
  4a-1 proceeds separately, with 4a-2 config screens after keymap phase 2.
  Docs PR C follows B.
  The owner merges, or explicitly asks a reviewer to.
- Work order: [Node Contract Plan](NODE_CONTRACT_PLAN.md). Long-term decisions:
  [Distributed Build Plan](DISTRIBUTED_BUILD_PLAN.md), [Stash](STASH_PROPOSAL.md).

## Verification and environment — 2026-10-18

- Keymap phase 2: **1666 passed** in 212.52s on the final code, including
  actual-keypress coverage for the three regressions, NAV/TEXT saves, multiline
  Ctrl+S/Ctrl+Enter, modal scope, dropdown and navigation/caret remapping.
  Compilation and `git diff --check` pass. An earlier full run hit the known
  file-picker `HeaderTitle` teardown flake; its isolated rerun and final full
  run pass. That separate fix remains deferred. Native terminal checks were
  not performed; visible wording/layout is unchanged.
- Docs audit: all **342 relative links/anchors** and **33 archive bodies** pass;
  its historical 17-active-doc assertion reports **18**, already the main
  baseline after #76 added the proposal. This phase does not change that count.
- Previous full suite: **1548 passed** on `dist/stash-s3` (2026-10-18).
- Keymap phase 1: **1605 passed** in 196.94s; focused registry/routing tests
  **57 passed**. Compilation and `git diff --check` pass. Documentation check:
  336 relative links/anchors resolve; 33 archive bodies and 17 active docs.
  Actual-keypress tests use headless Textual with production CSS; native
  terminal verification was not performed. Confirm's visible text/layout is unchanged.
- PR B checks: **334** relative Markdown links/anchors resolve, 33 whole archive
  bodies retained, 17 active docs, and `git diff --check` passes.
  Fresh receipts: [PR B verification](audits/docs_audit_2026_10_17/PR_B_VERIFICATION.md).
- Owner WSL setup: Python **3.14.4**, Textual **8.2.7**, pytest **9.1.0**;
  interpreter `/home/makin/src/node_workflow/.venv/bin/python`.
- Docs worktree: `/home/makin/src/nw-docs`; owner checkout and other workers'
  worktrees are not edited. The OneDrive checkout is recovery-only.
- Clean dependency installation and native Windows FO7 checks were not run.

## Open owner decisions and limits — 2026-10-17

- **Step 4:** design approved (2026-10-18; [Subworkflows proposal](SUBWORKFLOWS_PROPOSAL.md)
  rev. 4). 4a-1 (contracts, backend and CLI) is in its PR (`dist/step4a1-contracts`);
  4a-2 (the Start and Return End screens; sample screens shown) follows keymap phase 2 (#78).

- **Stash:** S1 approved with the CLI (2026-10-17). Answered 2026-10-18:
  the field-insert key is `P`; a text field takes text entries only, not
  a file path (`STASH_PROPOSAL.md` §7 questions 1 and 2). Still the
  owner's: question 3, global-only Stash or per-workflow pinning.
- **End in the selector:** End is registered and CLI-authorable, but hidden
  from the TUI selector. Whether to expose it remains an owner decision.
- **FO7:** native Windows/terminal-host verification remains unverified in
  this session; owner results are needed before claiming native coverage.
- **Step 4 implementation:** the approved contracts remain unbuilt; `--input`
  is recorded but not yet consumed. Stage 4a-1 is backend/CLI only; config
  screens follow keymap phase 2.
- Only the [audit report](audits/docs_audit_2026_10_17/MASTER_REPORT.md) survived.
  Original evidence/CSVs are unavailable. PR B rebuilt the source map before
  extraction; whole originals and migration notes are retained in `archive/`.
