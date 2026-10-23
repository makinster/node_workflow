# Ask Hermes (C3b part 1)

Ask Hermes asks one question and returns text. **The installed Hermes release
is refused before inference:** `This Hermes version can't run with these limits.`
This PR delivers the registered node, isolation gate, process ownership,
records and usage presentation. It does not enable a compatible agent adapter.
Success/error/cleanup tests use fake workers; no real account or model call
was made. No Hermes files, configuration or live installation were changed.

## Configure

Add **Complex → AI Processing → Ask Hermes**. Question uses the standard
Upstream payload, Vault or Configured source; upstream/Vault values must be
non-empty strings. The configured field uses today's shared multiline editor;
the later preview/full-screen editor remains a proposal.

Choose an existing **Folder** permitted by Options `system_node_folders`.
Links are resolved and checked again at invocation; an empty allowed list
allows nothing. Folder is the worker's CWD, not an operating-system sandbox.
The agent has no project-file tools. Installation selection is a machine
option, **Hermes installation folder**, never a workflow flag or executable.

**Stop after (seconds)** defaults to 60, range 10–300, including worker startup
and cleanup. Question is limited to 20,000 characters; answer to 256 KiB UTF-8.
Exactly one model turn, no tools, retries or fallback models. No dollar cap is
verified: **Allow Ask Hermes without a dollar cap** defaults off in Options.
This first version requires that opt-in for all runs, including unattended ones.
It changes neither time limits nor permissions. Provider billing or remote
computation may continue after a local process is stopped.

**Answer** is text, downstream by default, optionally copied to the Vault.
The standard **Forward incoming payload unchanged** checkbox substitutes the
original incoming payload downstream, including when Question comes from
Configured or Vault. Enabled Vault outputs still receive the answer/details.
**Run details** is optional, off by default, and Vault only. Its key must differ
from Answer's key. Validation happens before starting a worker.

## Compatibility and isolation

The worker runs through an isolated native Linux Python interpreter (`-I -S`),
with a fixed protocol and explicitly empty tool list. It must guarantee
read-only identity/memory, no writeback, plugins, hooks, MCP, project context
files, fallback, automatic retries, summarization, extraction or extra paid
calls. No user-supplied shell command is constructed; question travels on stdin.
Unrelated credentials and Python/plugin overrides are removed from child env.

Installed-source audit: Hermes 0.14, source revision `556bf7c5c`. Its imports
perform plugin discovery and its agent loop has additional retry/maintenance
paths. CLI empty-tool selection also falls back to configured tools. These
cannot establish the approved restrictions. The stdlib-only gate reads the
version literal without importing Hermes, loading auth or memory, or making
inference. **All releases remain refused until a separately source-audited,
containment-tested adapter is added.** A version string alone never enables
execution; there is no workflow/environment bypass. Missing installations
report `not_installed`. Native Windows runtimes are unsupported.

## Stop, records and usage

An async subprocess broker reuses H0's Linux subreaper collector. Every
invocation has a session/process group; descendants that detach with `setsid`
are discovered, killed and reaped too. The final five seconds are reserved:
INT at T−5, KILL at T−1, final second for reaping. Stop starts the same cleanup,
clamped to the original deadline. Repeated Stop cannot interrupt cleanup.
Cancellation stays cancelled and publishes no answer.

Before dispatch, write an intent and a C1 Record event receipt. Every invocation
gets a private file at `run_outputs/<run_id>/agents/<invocation_id>.jsonl`;
directories are 700, files 600. Records include timestamps, IDs, resolved
folder, limits, effective empty-tool policy, bounded answer, size/digest,
status, time and usage. There are no tool events in this version. Cap is 4 MiB
plus 64 KiB reserved for a terminal receipt. Recording failure prevents further
execution and suppresses successful outputs. Failed/cancelled records remain.

Terminal C1 receipts contain status and cost only; they never send a message.
Execution details, JSON run results and saved run summaries retain usage even
with forwarding or both Vault outputs off. They show turns, tokens, cost and
record location. Reported costs are estimates; absent usage is null/“not
reported”, never a fabricated zero. Per-run totals sum known estimates and
mark missing/partial amounts. Account source is `agent-owned`; no billing
account switch, pricing lookup or second login. Records are private, not an
invoice or a complete private-memory dump.

No auth values are stored in node config, argv or receipts. Raw stderr and
unknown worker fields are discarded. Registered AOTN secret values are redacted
from recorded answers/identity fields; a future compatible adapter must redact
its own selected credentials before emitting events. Arbitrary project text
may contain secrets unknown to AOTN. Credential files are never copied here.

Ownership markers live in `run_outputs/.ask-hermes-workers`. An active marker
is locked; an unlocked retained marker indicates a crash/unconfirmed cleanup
and blocks further invocations. Confirm those processes are gone before an
owner removes that marker; no automatic recovery or paid retry occurs.

## Errors

All are nonretryable: `not_installed`, `unsupported_runtime`, `auth_failed`,
`folder_missing`, `not_allowed`, `text_too_long`, `timed_out`, `turn_limit`,
`permission_denied`, `agent_failed`, `invalid_response`, `record_failed`,
`cleanup_failed`. Standard `node_error` covers invalid input/configuration or
the disabled cost opt-in. Stop is a cancellation receipt. Limits and malformed
output never become a partial successful answer; errors contain plain fixed
messages and safe run details, not a CLI traceback.

[Built screens and reproduction](../audits/ask_hermes_2026_10_22/README.md).
