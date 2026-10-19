# PR C verification — 2026-10-18

New checks against **90182f0**; this does not reconstruct the external audit's
missing CSVs or assign unsupported detail to individual S2/S3 findings.
Read the [decision extraction map](vision_sources.md#session-decisions-extracted-before-pr-c)
first, then the active reading route and corrected contract/Stash references.

## History transfer and owner intent (F31/F36–F39, V27/V28)

The active window is October 4–18; its first existing entry is October 6.
All October 18 entries from main remain whole. Entries before the cutoff
(July 11 through June 9) are appended whole to `archive/SESSION_LOG_HISTORY.md`.
The old archive body remains intact, including repeated June 9 history.
Only relative link targets are rebased. This retains reasoning and verification,
rather than replacing detailed entries with milestone summaries.

The extraction map records owner choices and their owning references: output
routing and session continuation, helper overwrite limits, visibility and typed
choices, window D1–D12, taxonomy reversals, child contracts, trigger direction,
resource ownership and intentional tombstones. Most had already been extracted
in PR B. Manual badge semantics are explicit in the UI reference; the June 22
amber-type fallback choice is retained as a backlog design target, not an
unverified claim about current styling. Superseded defaults and headless-export
ideas remain historical. Contributing now explains rolling this window forward.

## Remaining S2/S3 review

The retained report groups these finding IDs by topic but contains full details
only for S1; the matrix records what can actually be checked today.

| Report group | Result and authority checked |
|---|---|
| F16/F21–F23/F25–F27/F32/F42/F43/F46: runtime ownership, waits, signals, storage/resources and display | PR B's owning runtime/boundary references remain. Checked the current MemoryBank, RunSession, Supervisor/MasterState and RunService paths; no duplicate runtime rewrite. Known preflight/runtime limits remain explicit. |
| F17/F24/F36: authoring/types/defaults | Node Helper uses all six supported categories and five families; standards describe typed references, warning limits and current Chat defaults. Generator starters remain non-conforming until execution is implemented. #82 owns the error-port wording; not rewritten here. |
| F18–F20/F33: keys and screen reference | UI reference already has numbered tabs, within-row A/D, execution keys and 64-path behavior. Added primary/close-button and Stash deduplication wording. Stash design now uses plain P, off while typing; command palette unchanged. Generated in-app Help remains keymap phase 3. |
| F28/F43: live registry versus idea inventory | Catalog continues to point to live CLI contracts. Replaced the old inline/Phase-19 subworkflow rows with the approved child-run/Step-4 design; parallel calls are C15, not an approved separate collector node. HTTP Request and JSON Path rows are untouched for #82. |
| F29–F31/F37–F39/F44/F45: status, prompts, archive and plans | Current State is the dated snapshot; old prompts remain archived. Removed the stale Step-4 approval gate, keymap-awaiting-review text and “run inputs are only recorded” claims. Stash historical review is labelled as superseded. Log bounded after extraction. |
| F34/F35/F41: helper safety and limitations | Existing generator precautions remain: complete-class/test overwrite, legacy metadata type loss, spec drift, starter execution and smoke-test limits. Removed the contract plan's blanket HTTP-spec regeneration guarantee; preserved custom hooks/tests remains mandatory. |
| F40: newcomer route | Setup/full-suite commands remain in the guide; README now links directly to workflow contracts. Both authoring examples build and the typed-input example runs. |

These are documentation corrections only. This PR does not fix application
behavior, expose new UI or claim that deferred helpers/platform work is built.
No backend/frontend, test, owner workflow or helper-spec files changed.

## Checks and limits

- Full suite: **1708 passed in 223.15s**. #81's known picker flake did not
  occur in this run; #81 and #82 remain separate, unmerged PRs.
- Before changing the checker: 18 active docs failed the hard-coded 17 check.
  The checker now requires the exact 17 core names and permits only the approved
  temporary `SUBWORKFLOWS_PROPOSAL.md`, to be archived after Step 4.
- The checker verifies relative Markdown links/anchors, the 33 complete PR B
  archive bodies and the complete session-history transfer from 90182f0.
  Final result: **392 relative links/anchors**, **33 archive bodies**,
  **96 transferred entries**, **18 active docs** across 70 Markdown files.
- The two JSON specs in Workflow Authoring build in temporary storage; running
  the callable example with `who=Kim`, `times=3` returns `{"greeted":"Kim"}`.
- `git diff --check` and explicit preservation checks pass; all original
  October 18 log entries and the #82-owned standards/catalog text remain.
- Native FO7/live terminal, clean installation and external links were not
  verified. Original S2/S3 CSV detail remains unavailable; no missing evidence
  is presented as recovered verification.
