# Ask Hermes (C3b part 1)

Owner route revision: 2026-10-23.

Ask Hermes sends one question to the public CLI using an independent `aotn`
profile and returns text. It imports no Hermes internals. The owner set up and
verified the dedicated profile; AOTN checks its disabled CLI toolsets before
every question. This replaces the original always-refuse compatibility gate.
[New-user profile setup](../../integrations/hermes/README.md#ask-hermes-setup)
includes the owner's prompt and verification commands.

## Configure

Add **Complex → AI Processing → Ask Hermes**. Question uses Upstream payload,
Vault or Configured; upstream/Vault values must be non-empty strings. Configured
uses today's shared multiline editor; the later preview/editor remains separate.

Choose an existing **Folder** allowed by Options `system_node_folders`.
Expand `~`, resolve links and check at invocation. Empty allowed folders permit
nothing. The selected directory is the CLI's CWD. `--ignore-rules` prevents
AGENTS.md, SOUL and other context files in the Folder from loading.

Machine Options owns **Hermes profile home** (`hermes_profile_home`, default
`~/.hermes/profiles/aotn`) and **Hermes command** (`hermes_command`, default
`~/.local/bin/hermes`), never credentials or workflow-supplied CLI flags. Command
is an explicit executable path, so cron need not include `~/.local/bin` in PATH.
A wrapper may use bash; AOTN executes it directly as argv without constructing
a shell command string.
Only the disposable broker/CLI children receive the selected `HERMES_HOME`;
the app's environment and default Hermes profile remain unchanged.

**Stop after (seconds)** defaults to 60, range 10–300, including preflight,
startup and cleanup. Question is capped at 20,000 characters, answer at 256 KiB
UTF-8. The command is `chat -q <question> -Q --source tool --max-turns 1
--ignore-rules`; Question is one literal argument, not shell text.
There is no enforceable dollar cap: **Allow Ask Hermes without a dollar cap**
defaults off and must be enabled deliberately, for interactive and unattended
runs alike. Remote usage/billing may continue after local processes stop.

**Answer** is downstream text by default, optionally copied to the Vault.
The standard **Forward incoming payload unchanged** checkbox substitutes the
original upstream payload downstream, even with a Configured/Vault question.
Enabled Vault outputs still receive the answer/details. **Run details** is
optional, off by default and Vault only; its key must differ from Answer's.

## Preflight and output

Each run checks profile/config existence and command executability, then runs
`tools list --platform cli` using the selected profile and checked CWD. Strict
UTF-8 parsing requires the known header and all 24 unique built-in toolsets,
each marked disabled. Enabled, missing, duplicated, new or unclassified lines,
including diagnostics, refuse with `permission_denied`. SGR colour is accepted;
other terminal controls are refused. There is no cache. Config identity, mtime
and size must remain unchanged across preflight. Unknown CLI formats fail closed.

After successful preflight, run one `chat` command in the same total budget.
The owner-verified profile blocks MCP, disables all CLI tools and has memory
off and its own credentials. `--ignore-rules` also skips injected rules/memory.
This is **profile isolation, not an OS sandbox**; it trusts the owner's profile
and CLI, which run with the owner's OS access and maintain profile session data.
AOTN does not certify internal provider retries/fallbacks or exactly one paid
API call from `--max-turns 1`. No automatic AOTN retry or account switch occurs.
`--source tool` currently persists as `cli` in Hermes; no behavior depends on it.

`-Q` stdout is the answer; recognised bounded session-ID lines at its edges are
removed. Stderr is never an answer. Empty, undecodable, control-bearing, known
error-shaped or oversized output gives `invalid_response`; failed authentication
gives the plain `auth_failed` message. Unknown CLI errors become `agent_failed`,
without raw service text or traceback. `-Q` reports no measured turns, token use,
provider identity or cost: those values remain null/“not reported”. Configured
turn/time limits are separate from observations.

## Stop, records and usage

An async subprocess broker reuses H0's Linux subreaper collector. Every CLI
process has a session/group; descendants detaching with `setsid()` are discovered,
killed and reaped. Preflight and chat share one absolute deadline. Final five
seconds: INT at T−5, KILL at T−1, final second for reaping. Stop starts the same
bounded cleanup, clamped to the original deadline; repeated Stop is shielded.
Cancellation stays cancelled and publishes no answer. Native Windows is refused.

Before dispatch, write a private intent and C1 Record event receipt. Each visit
gets `run_outputs/<run_id>/agents/<invocation_id>.jsonl`, directories 700, files
600. Records include timestamps, IDs, checked folder, configured limits,
profile-isolation policy, bounded answer/size/digest, status and usage. No hidden
reasoning, credential files or raw CLI diagnostics are copied. Cap is 4 MiB plus
64 KiB reserved for the terminal receipt. Recording failure suppresses outputs;
failed/cancelled records remain. CLI session history stays in the selected profile.

C1 terminal receipts contain status/cost and send no message. Execution details,
JSON results and saved run summaries retain usage/record location regardless of
forwarding or disabled Vault outputs. Missing cost is null, never a fabricated
zero. Totals mark missing/partial estimates; they are not a bill.
Unrelated credential/agent environment overrides are removed. Known AOTN secret
values are redacted from recorded answers; unknown project text can contain
secrets AOTN does not know. The question is visible as a local process argument,
as required by the CLI; never put credentials into questions or workflow config.

Ownership markers in `run_outputs/.ask-hermes-workers` remain until cleanup is
confirmed. An unlocked retained marker blocks new calls after a crash or cleanup
failure. An owner must verify processes are gone before removing it. No paid
retry occurs automatically.

## Errors

All nonretryable: `not_installed` (“Hermes is not installed”), `profile_missing`
(“Set up the aotn Hermes profile first”), `unsupported_runtime`, `auth_failed`
(“Sign in to Hermes (aotn profile)”), `folder_missing`, `not_allowed`,
`text_too_long`, `timed_out`, `turn_limit`, `permission_denied` (“This Hermes
profile has tools turned on.”), `agent_failed`, `invalid_response`,
`record_failed`, `cleanup_failed`. `node_error` covers bad input/configuration
or disabled no-budget opt-in. Stop is a cancellation receipt, not an extra code.

[Built screens and verification](../audits/ask_hermes_2026_10_22/README.md).
