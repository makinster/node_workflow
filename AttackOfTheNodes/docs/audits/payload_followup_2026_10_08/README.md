# Saved workflow payload follow-up — 2026-10-08

Root `/home/makin/src/node_workflow`; `main`, base `1211e68`. Changes are
uncommitted. Screenshot recovered through its `/mnt/c/Users/...` path. Owner
workflows were inspected read-only; no owner workflow or referenced file was
executed or rewritten.

## Reproduced causes and corrections

1. The saved Writer receives its unchanged incoming payload on File Path while
   Content is configured separately. Runtime and preview previously assumed a
   Content connection. Both now prefer connected Content, falling back to
   connected File Path. Configured/Vault choices remain separate from the
   incoming payload being forwarded. A missing input no longer masquerades as
   Writer's own file-reference result.
2. Text Output intentionally accepts any payload and formats it as text. File
   references are displayed as references; File Reader reads contents. The
   Payloads tab now explains this and shows selected source, format, captured
   value preview and routing. Changing Source/Parameters updates the preview.
   No source value is fabricated before execution or when prompting for input.
3. Start edits greeting only in Parameters. Payloads reflects that value in a
   read-only preview and retains routing controls. Display-name overrides no
   longer obscure the configured greeting and are cleared when saving the
   simplified form. Unknown configuration fields remain preserved.
4. The saved graph has Text Output b2 directly before Wait Until. The prior
   unconditional Text Output termination made Wait Until unreachable. Restored
   continuation when connected; unconnected Text Output ends naturally. End
   is the explicit stop node. Branch-health traversal follows connected Text
   Output nodes. No change to the completion barrier or target selection was
   needed. This supersedes the previous build's unconditional output stop.

## Verification

`tests/test_reported_payload_routing.py` covers actual Writer forwarding and
provenance, Start and Text Output mounted at 60/100/140 columns, dynamic previews,
nontext formatting, and saved/reloaded parallel file-Vault workflows with Text
Output before Wait Until. Both Writer and post-Writer Text Output targets work,
including two consecutive executions with a fresh completion registry.
Existing Wait Until runtime/UI tests also pass.

**796 full-suite tests passed in 127.58s**. Compile and `git diff --check`
also pass; full details are in SESSION_LOG. Helper specs regenerate in
a temporary project without overwriting custom execution. Helper UI contracts
pass for all three changed ordinary nodes. Earlier full-run failures exposed
an obsolete Content-only label assertion; End's completion log was also added
to the integrated test when its terminal route became explicit.

This is automated/headless verification plus read-only inspection of the saved
graph. Owner live verification remains useful; earlier native Windows FO7 and
host-prefix investigation are unchanged.
