# Session integration build plan — 2026-10-06

Goal: one reviewable PR combining the pending Wait Until/runtime work, the
configuration audit, and the implemented File Output branch on current main.
Authoritative checkout: `/home/makin/src/node_workflow`; recovery copy untouched.

## Ordered stages

1. Preserve current changes in a checkpoint commit on
   `codex/wait-until-vault-fix`; fetched main starts at `7161ef2`.
2. Merge `origin/claude/file-output-pywin32-32tnv9` (`0a19718`), retaining
   both session histories, updated standards and local runtime fixes.
3. Fix small demonstrated defects: reject ambiguous window identification;
   keep blocking launch work off the event loop; remove unsupported Window
   Control forwarding metadata; preserve unrelated config on save; let shared
   CSS size CommandInput; distinguish write destinations in path validation;
   retain zero-valued numeric settings where demonstrated.
4. Handle multiple viewer requests through a FIFO queue, with user-input modals
   taking priority. This uses a conventional queue without changing node execution
   semantics. Keep bigger viewer-history/product changes in the backlog.
5. Refresh incoming-node audit evidence on the actual integrated tree. Run
   focused regression tests, helper checks, compileall, the full suite and
   production-CSS checks at 60/100/140 columns. Record actual counts and limits.
6. Reconcile current handoff/plan docs, document unresolved audit findings and
   Windows FO7 requirements, commit, push and create one PR to main. Attach it
   to this chat. Do not merge the PR automatically.

## Scope limits and follow-up

The audit's broad layout redesign is planned, not implemented in this integration.
No uniform four-tab mandate, no bespoke node screens, no new File Reader input
semantics, no tombstone cleanup, no Vault behavior added to Wait Until. Runtime
changes remain defect fixes. Unsupported platform controls require explanatory
UI work and consistent capability warnings in a later focused stage; Windows
launch/placement/close needs owner live review before claiming completion.

## Completion record

Updated as stages finish; see SESSION_LOG.md for checks and final PR details.
