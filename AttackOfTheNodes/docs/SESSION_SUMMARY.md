# Project rundown for the next session — 2026-10-06

## Publication and workspace

Authoritative checkout: `/home/makin/src/node_workflow`; use its Linux `.venv`.
OneDrive copy is recovery-only. Session branch: `codex/wait-until-vault-fix`.
[PR #29](https://github.com/makinster/node_workflow/pull/29) is open against main
and was verified mergeable. Main is still `7161ef2` (PR #28). Integration changes
are committed and pushed; review/merge #29 before treating them as main behavior.

## What the project does

AttackOfTheNodes is a local Python/asyncio workflow engine with a keyboard-first
Textual terminal editor and execution monitor. Users assemble node graphs,
configure connections, save/load/import/export workflows, run parallel branches,
use conditions/merge barriers/Wait Until, collect output and debug with pause,
breakpoints, timings, recovery and per-node execution status.

Dead-drop payloads travel through connections; the Vault provides named shared
run data. RunSession owns file handles and AI session resources and closes them
at run end. SecretsManager resolves configured secrets and has a settings UI.
Real Chat Completion uses the implemented Anthropic provider; image generation
and embeddings remain simulations. Utilities include transformations, HTTP,
text input/output, local file reading and debugging nodes.

The session branch adds File Write, File Viewer, Window Control and Markdown
formatting, with typed file references and optional OS opening/placement/control.
There are 37 registered types, 34 selector-addable and 36 editable/user-facing;
tombstone remains intentional internal save/recovery data.

## What remains unfinished

- General node configuration still has misleading legacy Vault controls, empty
  tabs, conditional-field/validation gaps and some routing/label defects.
- Windows placement/control is implemented but requires FO7 live verification;
  WSL uses the Linux fallback and does not gain pywin32 capabilities automatically.
- File Reader accepts a configured path, not typed file-reference input.
- The proposed per-branch execution navigation/output-summary screen is not built.
- Nested/subworkflows, dedicated headless CLI execution, persistent trigger watcher
  and additional frontend/server architectures remain future work.
- Several backend features lack complete UI surfaces, including browsing run
  history, restore warnings and memory-snapshot choices. Packaging/release
  hardening and full live accessibility/appearance review are not complete.

## What this chat accomplished

Preserved the pending Wait Until/runtime/UI/tests/docs work in a checkpoint,
merged the File Output branch while retaining both histories, audited actual
screens and behavior, produced persistent coverage/evidence and implementation
plans, and published one PR.

Fixed answer/transient publication ordering, stopped-input cancellation, typing,
Wait Until zero-timeout/layout behavior, unrelated-config loss on save, critical
field sizing, Chat temperature zero, writer-path warnings, unsupported Window
Control forwarding UI, ambiguous window selection, blocking launch polling and
lost viewer requests. Viewer requests now queue FIFO by displayed run, with
input/recovery modal priority. Wait Until still waits for all selected targets
and forwards its incoming dead-drop unchanged; it never accesses the Vault.

## Actual verification and next order

546 full-suite tests passed; compileall and four node UI helper checks passed.
Production CSS: 108 mounts at 60/100/140 columns, 306 alternate states, unchanged
Cancel 36/36, stable default save/reopen with unrelated config retained 72/72,
and variant save/reopen 115/115. These are this session's checks, not a permanent
baseline; real Windows and owner live TUI verification remain open.

1. Fetch origin and check PR #29; review/merge it, then synchronize the authoritative checkout.
2. Follow `CONFIG_UI_BUILD_PLAN.md`, starting with truthful shared capability controls.
3. Complete Windows FO7 on a real Windows environment; retain portable fallback behavior.
4. Keep execution-branch redesign and new node capabilities in separate focused work.

Read `README.md`, `TASK_INDEX.md`, recent `SESSION_LOG.md`, then
`CONFIG_UI_BUILD_PLAN.md`. Original audits are historical snapshots; current
integrated evidence is under `docs/audits/integrated_2026_10_06/`.
