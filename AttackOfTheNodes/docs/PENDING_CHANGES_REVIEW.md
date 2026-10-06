# Pending changes review — 2026-10-06

Follow-up: [File Output integration review](FILE_OUTPUT_INTEGRATION_REVIEW.md)
examines the unmerged feature against the pending fixes, with 304-test source-overlay
evidence, nine production-CSS mounts and integration findings. The current checkout
audit remains distinct from that prospective 37-type inventory.

This review reconciles the pending work before a configuration-UI build plan.
It does not implement that plan or merge unrelated feature branches.

## Repository state

Authoritative checkout: `/home/makin/src/node_workflow`.
Branch: `codex/wait-until-vault-fix`, HEAD `7161ef2`.
`git fetch origin && git merge origin/main` succeeded: already up to date.
HEAD and origin/main have zero commits of divergence. The branch's implementation,
tests, design notes and audit remain uncommitted; synchronization with main does
not mean that pending work has been published. OneDrive recovery files untouched.

Reviewed the tracked diff, both new test files, pending investigation/design
notes, the configuration audit and its evidence tooling. The runtime/UI files
were preserved without further changes in this review.

## Local pending work

| Files | Purpose and review disposition |
|---|---|
| `backend/nodes/user_text_input_node.py` | Writes each declared legacy Vault answer key before signaling success, with string type and empty-answer preservation. Specific to this node; does not invent generic Vault behavior. Covered by direct and cross-branch tests. |
| `backend/supervisor.py` | Cancels an interrupted input future instead of treating Stop as an empty answer. Publishes transient output before recording target completion. Completion uses the saved completed-node ID even after routing advances current_node_id. Existing retry/skip/stop/lifecycle tests included in full verification. |
| `backend/nodes/wait_until_node.py` | Passes timeout 0 explicitly, meaning unlimited wait rather than the global timeout. Positive timeouts retain their limit. Waits for all selected IDs and forwards its incoming dead-drop unchanged; no Vault reads/writes. |
| `frontend/screens/user_input.py` | Explicitly starts ordinary editing so W/S type into the answer instead of moving focus. Existing Escape/submit and command-widget behavior retained. Four typing regressions plus full suite cover it. |
| `frontend/screens/node_config.py` | Wait/Connections layout removes unsupported controls; preserves invalid target IDs for explicit correction; rejects invalid/non-finite/negative timeouts; preserves unrelated config while clearing retired Wait-only declarations on Save. Shared help now describes numbered tabs and A/D within rows. **Not visually signed off:** production-CSS overflow remains (below). |
| `aotn_node_helper/ui_checks.py` | Accepts Wait's generated timeout in the focused Wait tab. Correct placement adaptation, but checker remains insufficient for production geometry. |
| `tests/test_wait_until_vault.py` | Nineteen parameterized cases: fresh/continued Chat, list/string targets, zero/positive waits, legacy output-key aliases, empty answers, stopped prompts and W/S typing. Fake provider; no live API required. Global timeout override uses monkeypatch rather than persisting a setting. |
| `tests/test_wait_until_ui.py` | Twelve mounted cases: three widths, target-list navigation/tab return, invalid targets/timeouts, empty selection, Save cleanup/preservation and Cancel. **Coverage limitation:** bare App does not load production styles.tcss, so these tests cannot establish visible timeout/caret placement. |
| `docs/WAIT_UNTIL_INVESTIGATION.md`, `docs/EXECUTION_STATUS_CONTRACT.md` | Explain the missing answer write, completion ordering, stopped-input contract, later typing fix and zero-timeout rule. Historical investigation sections must not be read as current unfixed behavior. |
| `docs/WAIT_UNTIL_UI_PLAN.md` | Records the focused layout that sparked the library-wide audit. The control/behavior simplification is implemented locally; the production-CSS defect found afterward remains. |
| `docs/NODE_STANDARDS.md`, `UI_QUICK_REFERENCE.md`, `AGENT_START_GUIDE.md`, `NODE_HELPER.md`, `TUI_DESIGN.md` | Consistent new policy: shared section meanings, only applicable controls, compact/focused forms permitted, consecutive visible-tab numbering. Generic composition has not yet been migrated to that policy. |
| `docs/EXECUTION_BRANCH_UI_DESIGN.md` | Separate proposal for execution-branch navigation and previews. No execution-screen redesign is implemented by these pending changes; not part of the upcoming configuration-UI plan. |
| `docs/NODE_CONFIG_UI_AUDIT.md`, `docs/audits/node_config_2026_10_06/` | Completed current-checkout audit, 35-type matrix, raw synthetic captures and reproducible checks. Findings and limitations remain valid for this baseline. No owner data in audit fixtures. |
| `docs/README.md`, `TASK_INDEX.md`, `MASTER_BUILD_PLAN.md`, `PROJECT_BACKLOG.md`, `NEXT_CHAT_HANDOFF.md`, `SESSION_LOG.md` | Routing, status and history. Reconciled current handoff/roadmap to this review; obsolete pre-PR-28 instructions are historical. AGENT_HANDOFF also updated to direct new sessions to current state. |

## Review findings and readiness

1. **Wait Until's semantic/UI direction is sound:** configure targets and timeout,
   explain unchanged forwarding, and let downstream nodes choose Vault sources.
   Keep this as the reference for capability-driven layouts. Do not restore
   generic Vault controls to Wait Until.
2. **The focused UI is not visually complete.** Audit F03 demonstrates that the
   timeout starts at x=80 at a 60-column terminal. Inline descriptions plus
   CommandInput's inline 100% width cause a shared layout failure; bare-App tests
   missed it. Carry this into the first build-plan stage with production-CSS
   visibility assertions. Do not claim this screen is ready for live sign-off
   merely because its functional tests pass.
3. **Runtime fixes are separately reviewable.** Current regression coverage
   supports the scoped answer-publication, cancellation, typing and timeout
   behavior. No additional runtime defect was confirmed during this review.
   Broader audit issues (generic Vault promises, other nodes' save loss, etc.)
   remain future work, not fixes already present in this diff.
4. **Publication remains pending.** Nothing was committed, pushed or merged during
   this review. Keep runtime fixes, focused UI/standards and audit/design evidence
   identifiable when preparing later commits. Preserve the existing feature work.

## Fetched File Output work changes the planning baseline

`origin/claude/file-output-pywin32-32tnv9` is at `0a19718`. Compared with
origin/main, it has **nine unique commits**, while main also has **nine unique
commits**: this is a diverged feature branch, not an unapplied main update.
Its diff from the merge base spans 48 files. Local tracking branch is one commit
behind that fetched feature tip; it was not checked out or modified.

Read-only inspection of its registry, node contracts, diff and phase checklist
shows:

- Removes `example_file_instance_node` and its helper/test files.
- Adds `file_output_node` (File Write), `file_view_node` (File Viewer), and
  `window_control_node` (Window Control).
- Adds Markdown formatting to Text Transform.
- Adds actual termination options to the two new output nodes, plus file-reference,
  viewer-event and window-platform services. This does **not** implement termination
  for the current Text Output node.
- Its phase checklist marks FO1–FO6 done and FO7 Windows live checks pending.
  The plan's top “no phase started” label is stale even on that branch; code and
  checked phases take precedence. No Windows verification was performed here.

This review is an **integration-impact check**, not full review/test approval of
those 48 files. Only the authoritative current checkout was executed. GitHub PR
state was not verified (`gh` unavailable); fetched Git refs establish the branch
contents and divergence, not approval or merge readiness.

Before finalizing a build plan, explicitly choose its baseline:

- If File Output is to land first, review/reconcile it with main and the local
  runtime fixes, test the combined tree, then extend the mounted audit to the
  three added nodes and Markdown mode. Revisit the demo-removal/save-compatibility
  decision and audit F04; do not build a new demo-management solution first.
- If it remains deferred, base the configuration plan on the current 35 types and
  record those four future additions/variants as an integration follow-up. Keep
  shared capability/rendering helpers usable by the new file nodes.

Do not automatically merge this feature into a dirty tree or treat its historical
Linux test results as current combined-tree verification. The current audit is
not an audit of that unmerged feature branch.

## Verification

Fresh `python -m pytest tests/ -q`: **445 passed in 64.00s**.
`compileall -q AttackOfTheNodes aotn_node_helper` and
`check_ui.py wait_until_node` passed. Local Markdown links and
`git diff --check` passed; results also recorded in SESSION_LOG. The audit's earlier 232-test
result remains evidence for that audit, not the baseline for this review.
No owner live confirmation, real provider call or Windows placement test is
claimed. The next task is a build plan based on the audit and the chosen feature
baseline; broad configuration implementation has not started.
