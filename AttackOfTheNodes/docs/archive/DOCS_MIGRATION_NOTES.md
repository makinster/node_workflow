> Superseded by [README](../README.md) on 2026-10-17.
> Historical document retained whole; old status, permissions and designs below
> are not current instructions. See [Current State](../CURRENT_STATE.md).

# Documentation Migration Notes

This file explains documentation moves, collapses, archives, and deletions so
future agents understand why the docs tree changed.

## 2026-06-09 — Task-First Docs Overhaul

| Old location | New location | Action | Reason |
|---|---|---|---|
| `README.md` | `README.md` | Rewritten | Make the docs entry point a task router instead of a flat file list. |
| n/a | `TASK_INDEX.md` | Added | Provide task type -> minimum docs -> likely files -> focused checks. |
| n/a | `UI_QUICK_REFERENCE.md` | Added | Summarize current UI keys and command-mode rules so agents do not need the full 500-line TUI design doc for routine UI fixes. |
| `MASTER_BUILD_PLAN.md` | `archive/BUILD_PLAN_HISTORY.md` | Full copy archived | Keep completed phase detail available without forcing agents to read 1000+ lines by default. |
| `MASTER_BUILD_PLAN.md` | `MASTER_BUILD_PLAN.md` | Collapsed | Active file now contains current status, next roadmap, and links to history. |
| `SESSION_LOG.md` | `archive/SESSION_LOG_HISTORY.md` | Full copy archived | Preserve detailed historical session notes while keeping active log small. |
| `SESSION_LOG.md` | `SESSION_LOG.md` | Collapsed | Active file now keeps recent/current entries and points to full history. |
| `V05_BUILD_PLAN.md` | `archive/V05_BUILD_PLAN.md` | Archived | Historical Python/tkinter proof-of-concept plan; useful context but not part of the normal current-task path. |
| `FRONTEND_AUDIT_BUILD_PLAN.md` | `archive/plans/FRONTEND_AUDIT_BUILD_PLAN.md` | Archived | Completed frontend standardization plan; active rules now live in `AGENT_START_GUIDE.md`, `TUI_DESIGN.md`, and `TASK_INDEX.md`. |
| `USER_FRIENDLY_POLISH_BUILD_PLAN.md` | `archive/plans/USER_FRIENDLY_POLISH_BUILD_PLAN.md` | Archived | Planning context retained, but current roadmap summary lives in `MASTER_BUILD_PLAN.md`. |
| `AGENT_HANDOFF.md` | `AGENT_HANDOFF.md` | Rewritten | Reflect current documentation overhaul and the new docs entry flow. |
| `FILE_TREE.md` | `FILE_TREE.md` | Refreshed | Align file tree with archived docs and current tracked project shape. |

## 2026-06-13 — Headless Build Plan archived

| Old location | New location | Action | Reason |
|---|---|---|---|
| `HEADLESS_BUILD_PLAN.md` | `archive/plans/HEADLESS_BUILD_PLAN.md` | Archived | Plan H1–H5 implemented and verified (full suite 284 passed); kept as history. Active status folded into `MASTER_BUILD_PLAN.md` and `PROJECT_BACKLOG.md`; deferred UI follow-ups tracked in `PROJECT_BACKLOG.md`. README directory row moved from Planning/Backlog to Archive. |

## 2026-06-19 — Node Standardization Handoff added

| Old location | New location | Action | Reason |
|---|---|---|---|
| n/a | `NODE_STANDARDIZATION_HANDOFF.md` | Added | Consolidates the node-standardization design discussion into an adopted implementation plan (per-node I/O contract via `NodeFactory`, Category > Family > Type rename onto the canonical `category` key, canonical data-type vocab, unified helper spec, master-detail selector). §2 open decisions signed off 2026-06-19: rename approved reusing `category` (retire `primary_family`/`legacy_category` aliases, `group → family`); drill-in family nav; one-line-per-port `to:` display; no behavior badge. README Document Directory row added under Node Authoring. Its changes fold into `NODE_STANDARDS.md`, `PHASE_17_NODE_VISUAL_IDENTITY.md`, and `NODE_HELPER.md` when each track is implemented. |

## 2026-06-22 — I/O Contract UI Design spec added

| Old location | New location | Action | Reason |
|---|---|---|---|
| n/a | `IO_CONTRACT_UI_DESIGN.md` | Added | Finalized design spec for Track B frontend changes surfacing the per-port I/O contract: master-detail selector layout, tab-sticking fix, vault conditional dropdown, upstream description hint, ⚠ badge, drill-in navigation. Resolves all open design decisions from the Track B planning session. README Document Directory row added under Frontend Reference. |

## Deletions

No tracked documentation files were deleted in this pass. Historical and
completed planning files were archived instead.

Untracked root `docs/hello.txt` was intentionally not touched because it is
outside the tracked active docs tree and prior workflow asked to ignore
untracked unrelated files.

## 2026-10-11 — Distributed Direction Build Plan added

| Old location | New location | Action | Reason |
|---|---|---|---|
| n/a | `DISTRIBUTED_BUILD_PLAN.md` | Added | Records the approved long-term direction: decisions D1–D4/R1–R4 and steps 1–6 |
| `PROJECT_BACKLOG.md` headless CLI, Start-node redesign, nested headless validation, headless-export interaction, always-running watcher, performance item 4 | same file | Superseded banners added; text kept | The owner asked that superseded sections be marked rather than deleted |
| `MASTER_BUILD_PLAN.md` Phase N / N+1 / N+2 roadmap bullets | same file, "Superseded roadmap entries" | Kept under a superseded heading; the step table was added above them | Same reason |
| `AGENT_HANDOFF.md` Long-Range Direction | same file | Superseded pointer added | Same reason |
| `NODE_CATALOG.md` Wait Until row | same file | Corrected | The row said Wait Until waits on a Vault key; the code waits on node completion |

## 2026-10-17 — Entry route and S1 corrections (PR A)

| Source | Destination | Action |
|---|---|---|
| Root `AGENTS.md` and README directory | `README.md`, `NEWCOMER_GUIDE.md`, `CURRENT_STATE.md` | Replace competing entry/status routes with a short router |
| `TASK_INDEX.md` task routing and focused checks | `README.md` | Fold route into README; retain detailed source until PR B extraction |
| Owner's untracked newcomer candidate | `NEWCOMER_GUIDE.md` | Copy, correct against code, shorten; original untouched |
| Three execution prompts | Same files | Historical banners; no moves yet; owner merges overrides old procedure |
| Session summary, integration plan, handoffs, master plan | Same files | Historical status banners; preserve reasoning for PR B |
| External audit report | `audits/docs_audit_2026_10_17/MASTER_REPORT.md` | Copy report only; mark missing evidence references as unavailable |

No files moved or archived in A. VISION and CONTRIBUTING arrive in B after
rebuilding the missing vision-source map. F01–F04/F14/F15 repair routes;
F05/F08/F09 repair node examples; F06/F07/F41 repair helper safety and commands;
F10/F11 correct termination and Echo; F12 fixes output-before-completion order;
F13 preserves reuse with the approved child-run mechanism.

## 2026-10-17 — Consolidation and vision (PR B)

Source ranges/intent were recorded before edits in
[a rebuilt source map](../audits/docs_audit_2026_10_17/vision_sources.md), pinned to
`9d5455b`. Whole source documents are retained below with supersession notes;
relative hyperlinks are adjusted for their new locations. No runtime/tests/specs
are changed. Session-history bounding remains PR C.

| Original top-level document | Active destination(s) | Whole archive copy |
|---|---|---|
| `AGENT_HANDOFF.md` | CONTRIBUTING; CURRENT_STATE; PROJECT_BACKLOG | `archive/AGENT_HANDOFF.md` |
| `AGENT_START_GUIDE.md` | NODE_STANDARDS; NODE_HELPER; CONTRIBUTING; UI_QUICK_REFERENCE | `archive/AGENT_START_GUIDE.md` |
| `CONFIG_UI_BUILD_PLAN.md` | NODE_STANDARDS; UI_QUICK_REFERENCE; PROJECT_BACKLOG | `archive/CONFIG_UI_BUILD_PLAN.md` |
| `DISTRIBUTED_EXECUTION_PROMPT.md` | CONTRIBUTING; DISTRIBUTED_BUILD_PLAN | `archive/DISTRIBUTED_EXECUTION_PROMPT.md` |
| `DOCS_MIGRATION_NOTES.md` | README; archive/DOCS_MIGRATION_NOTES | `archive/DOCS_MIGRATION_NOTES.md` |
| `EXECUTION_BRANCH_UI_DESIGN.md` | PROJECT_BACKLOG | `archive/EXECUTION_BRANCH_UI_DESIGN.md` |
| `EXECUTION_STATUS_BUILD_PLAN.md` | ARCHITECTURE; PROJECT_BACKLOG | `archive/EXECUTION_STATUS_BUILD_PLAN.md` |
| `EXECUTION_STATUS_CONTRACT.md` | ARCHITECTURE | `archive/EXECUTION_STATUS_CONTRACT.md` |
| `EXECUTION_STATUS_INVESTIGATION.md` | ARCHITECTURE; CONTRIBUTING | `archive/EXECUTION_STATUS_INVESTIGATION.md` |
| `FILE_OUTPUT_BUILD_PLAN.md` | NODE_STANDARDS; PROJECT_BACKLOG | `archive/FILE_OUTPUT_BUILD_PLAN.md` |
| `FILE_OUTPUT_INTEGRATION_REVIEW.md` | NODE_STANDARDS; PROJECT_BACKLOG; CONTRIBUTING | `archive/FILE_OUTPUT_INTEGRATION_REVIEW.md` |
| `FILE_TREE.md` | NEWCOMER_GUIDE | `archive/FILE_TREE.md` |
| `IO_CONTRACT_UI_DESIGN.md` | NODE_STANDARDS; UI_QUICK_REFERENCE | `archive/IO_CONTRACT_UI_DESIGN.md` |
| `MASTER_BUILD_PLAN.md` | VISION; NODE_CONTRACT_PLAN; DISTRIBUTED_BUILD_PLAN; PROJECT_BACKLOG | `archive/MASTER_BUILD_PLAN.md` |
| `NEXT_CHAT_HANDOFF.md` | CURRENT_STATE; ARCHITECTURE; UI_QUICK_REFERENCE; PROJECT_BACKLOG | `archive/NEXT_CHAT_HANDOFF.md` |
| `NODE_CONFIG_UI_AUDIT.md` | NODE_CONTRACT_PLAN; NODE_STANDARDS; PROJECT_BACKLOG | `archive/NODE_CONFIG_UI_AUDIT.md` |
| `NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md` | UI_QUICK_REFERENCE; CONTRIBUTING | `archive/NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md` |
| `NODE_CONTRACT_EXECUTION_PROMPT.md` | CONTRIBUTING; NODE_CONTRACT_PLAN; PROJECT_BACKLOG | `archive/NODE_CONTRACT_EXECUTION_PROMPT.md` |
| `NODE_STANDARDIZATION_HANDOFF.md` | NODE_STANDARDS; NODE_HELPER; UI_QUICK_REFERENCE | `archive/NODE_STANDARDIZATION_HANDOFF.md` |
| `PAYLOAD_FILE_IO_BUILD_PLAN.md` | NODE_STANDARDS; ARCHITECTURE; PROJECT_BACKLOG | `archive/PAYLOAD_FILE_IO_BUILD_PLAN.md` |
| `PENDING_CHANGES_REVIEW.md` | CONTRIBUTING; NODE_STANDARDS; PROJECT_BACKLOG | `archive/PENDING_CHANGES_REVIEW.md` |
| `PHASE_17_NODE_VISUAL_IDENTITY.md` | VISION; NODE_STANDARDS; NODE_CATALOG; UI_QUICK_REFERENCE; PROJECT_BACKLOG | `archive/PHASE_17_NODE_VISUAL_IDENTITY.md` |
| `PROJECT_KNOWLEDGE.md` | ARCHITECTURE; NODE_STANDARDS; CONTRIBUTING | `archive/PROJECT_KNOWLEDGE.md` |
| `RECOVERY_UX_BUILD_PLAN.md` | UI_QUICK_REFERENCE; NODE_STANDARDS; CONTRIBUTING | `archive/RECOVERY_UX_BUILD_PLAN.md` |
| `RECOVERY_UX_EXECUTION_PROMPT.md` | CONTRIBUTING; PROJECT_BACKLOG | `archive/RECOVERY_UX_EXECUTION_PROMPT.md` |
| `SESSION_INTEGRATION_BUILD_PLAN.md` | CONTRIBUTING; CURRENT_STATE | `archive/SESSION_INTEGRATION_BUILD_PLAN.md` |
| `SESSION_SUMMARY.md` | CURRENT_STATE; CONTRIBUTING; PROJECT_BACKLOG | `archive/SESSION_SUMMARY.md` |
| `SIGNAL_FLOW.md` | ARCHITECTURE | `archive/SIGNAL_FLOW.md` |
| `TASK_INDEX.md` | README; NODE_HELPER; CONTRIBUTING | `archive/TASK_INDEX.md` |
| `TUI_DESIGN.md` | UI_QUICK_REFERENCE; CONTRIBUTING; ARCHITECTURE | `archive/TUI_DESIGN.md` |
| `WAIT_UNTIL_INVESTIGATION.md` | ARCHITECTURE; CONTRIBUTING | `archive/WAIT_UNTIL_INVESTIGATION.md` |
| `WAIT_UNTIL_UI_PLAN.md` | UI_QUICK_REFERENCE; NODE_STANDARDS | `archive/WAIT_UNTIL_UI_PLAN.md` |
| `ARCHITECTURE.md` before consolidation | ARCHITECTURE | `archive/ARCHITECTURE_PRE_CONSOLIDATION.md` |

New active files: VISION and CONTRIBUTING. Exactly 17 active top-level docs
remain. README routes by task; CURRENT_STATE owns the dated snapshot.

## 2026-10-18 — PR C session-history window

| Source | Destination | Preservation |
|---|---|---|
| `SESSION_LOG.md` at `90182f0`, 96 entries before October 4 | [SESSION_LOG_HISTORY.md](SESSION_LOG_HISTORY.md) | Whole entries appended; only relative link targets rebased. Existing archive body retained. |
| Owner decisions in those entries | [Extraction map](../audits/docs_audit_2026_10_17/vision_sources.md#session-decisions-extracted-before-pr-c) → owning references | Existing references checked before transfer; missing badge/fallback intent retained in UI reference/backlog. |
| October entries | [Active Session Log](../SESSION_LOG.md) | All 86 existing entries retained whole, including every October 18 entry. |

The active window is October 4–18; the first existing entry is October 6.
[PR C verification](../audits/docs_audit_2026_10_17/PR_C_VERIFICATION.md) records
checks and evidence limits. This ledger remains append-only.
