# Wait Until / Shared Memory Investigation

2026-10-06. Canonical checkout, merged PR #28 base `7161ef2`;
branch `codex/execution-branch-ui-design`. Investigation only. Existing dirty
branch-UI design documents preserved; no workflow files or runtime code edited.

## Implemented follow-up

Owner confirmed this workflow and the intended cross-branch LLM input. Fix on
`codex/wait-until-vault-fix`, based on `7161ef2`: User Text Input copies its answer
to declared Vault keys (string typed) before success; Supervisor publishes
transient data before recording completion. Stopping an unanswered prompt cancels
the input future, preventing output writes and completion-registry insertion.

The saved LLM already selects Document/Context from Vault key `user_text`, with
Continue AI session as its prompt source. No saved workflow changes are needed.
Verification: full suite **425 passed in 49.81s**; focused new/execution tests
**32 passed**, compileall, diff checks, local links and node UI check passed.
Live owner workflow verification remains.

Focused regressions cover both fresh and continued LLM calls with a fake provider,
list/string target configs, legacy key aliases, empty answers and stop. Historical
investigation below describes the pre-fix behavior.

## Follow-up: empty continued-session input

Owner reported the continued-session error at node_8ec97b0a after the Vault fix.
Read-only inspection confirmed the running app was canonical and started after
that fix. The saved workflow still targets User Text Input and reads `user_text`.
A controlled run of the exact saved graph (fake LLM, non-empty answer) held the
second LLM until user input and finished successfully with two provider calls.
No saved workflow contents, credentials or prompt text were modified.

Mounted dialog testing exposed an independent defect: auto_edit_on_focus enabled
W/S navigation even during text entry. Typing `w` or `s` alone yielded an empty
answer; `what is your answer` became `hat ier`, and typing moved focus. This can
cause the reported empty-document error, but the owner's exact submission and
prompt/error ordering have not yet been confirmed.

UserInputScreen now explicitly begins normal text editing on mount without the
auto-edit navigation override. W/S type text during editing; after leaving edit
mode normal command navigation resumes. Ctrl+Enter still submits. Four mounted
regressions failed before the change and pass afterward. The running process
needs restarting to load this additional UI change. Backend-only input submission
tests did not cover this keyboard path, explaining the earlier coverage gap.

## Reproduced result

A controlled real MasterState/Supervisor run used two parallel paths:

- Path A: Wait Until (target IDs stored as a list) -> Get Variable -> End.
- Path B: User Text Input with `membank_outputs` declaring `user_text`.

While the input future remained unanswered, Wait Until was running, not done;
Get Variable had not started, and the target was not in completed_nodes.
After submitting `ANSWER`, the run finished, Wait Until completed after the
input target, and the target's default transient output contained `ANSWER`.
The Vault key `user_text` was absent and Get Variable returned `MISSING`.

This proves branch gating works in that scenario and reproduces the missing
shared value. No external API calls were made, and the diagnostic graph was
not saved. Existing `test_wait_until_node_gates_cross_branch_completion` passed
(1 passed, 153 deselected). The prior 414-test result is historical; the full
suite was not rerun for this investigation.

## Code evidence

- `backend/nodes/wait_until_node.py`: accepts list or comma/newline target IDs,
  awaits context.wait_for_nodes, then forwards context.inputs["input"].
- `backend/master_state.py`: asyncio.Condition suspends until all configured
  target IDs are in completed_nodes. The registry is reset for each run and
  means completed at least once, not completed on every loop iteration.
- `backend/nodes/user_text_input_node.py`: awaits user input and emits default
  transient data. It never writes the configured membank_outputs to the Vault.
- `backend/supervisor.py`: prepares upstream transient inputs only; it does not
  apply generic membank_inputs/membank_outputs declarations. Thus declaring a
  writer in the UI/validator does not guarantee a runtime write.
- Wait Until's selected membank_inputs also do not replace its pass-through
  input with Vault data. A downstream Chat Completion must explicitly select
  Vault for the relevant prompt/context/document source to read a shared key.
  Extending a chat session is separate from adding its next-turn context.

## Local saved workflow evidence

Read-only inspection found `workflows/wf_0d75f6241f3d.json` with this pattern:
Wait Until targets User Text Input (`node_d33abdff`), whose declaration writes
`user_text`; Wait Until declares a read of `user_text`. Its downstream Chat
Completion uses Continue AI session. This is a candidate for the reported
workflow, not owner-confirmed identification. It was not executed or changed;
provider credentials and configured prompt contents were not printed.

## Other observations and fix scope

Completion notification precedes _handle_payload's transient writes. In the
normal current event loop path, condition acquisition and routing do not yield
between those operations, so this alone did not reproduce an early-release
race. Nevertheless output publication should precede completion notification
if “completed” promises readable output; test that boundary explicitly before
changing it. Avoid claiming this ordering observation caused the reported case.

Empty target sets currently pass immediately. User input and barriers have
separate semantics: Wait Until remains lifecycle running while awaiting its
condition, so its play glyph does not prove downstream execution continued.
Timeouts signal an error and enter recovery; they do not signal success.

Recommended next fix: ensure the configured User Text Input Vault output is
actually written before its completion can release waiters; define that mapping
against the legacy declaration format and preserve typed keys. Do not silently
introduce a universal writer/reader policy for all node types or replace the
Wait Until incoming payload with a Vault value. The owner should identify the
reported workflow/target and clarify which downstream input should consume the
Vault value before modifying its configuration or broadening runtime behavior.

Acceptance: hold input open and assert the reader cannot start; answer it and
assert the configured Vault key exists when target completion is recorded and
when the dependent reader starts. Cover target-ID list/string configs, all-target
waits, timeout/error/skip/stop, and existing output routing. Any runtime fix needs
focused tests, full suite and compileall; investigation verification used the
existing focused test, real runtime diagnostic, git diff --check and local links.
