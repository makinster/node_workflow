# AttackOfTheNodes Session Log

This log keeps roughly the last two weeks: entries dated October 4–24, 2026
(the earliest existing entry is October 6). Every October 18 entry is retained.
Older entries remain whole in [Session Log History](archive/SESSION_LOG_HISTORY.md).
Before rolling the window forward, extract owner decisions into their owning
references; see [Contributing](CONTRIBUTING.md#keeping-the-session-log-bounded).

## 2026-10-24 — #119 re-check: multiline credentials and URL userinfo

Own worktree `/home/makin/src/nw-mcp-activity-review`, branch
`codex/mcp-activity-review`, clean start from `6cbee5f`. Fetched and merged
`origin/main` (already current); push target remains #119's `codex/mcp-activity`.
Only the shared C3c helper changes: mask multiline credential blocks rather
than their YAML marker; mask URI authority userinfo for any scheme case/name,
including username-only credentials. Inbox request persistence and activity
findings/event summaries benefit from the same implementation. Block handling
covers literal/folded markers, indentation/chomp indicators, header comments,
list indentation, CRLF/tabs, plain credential/key continuations and PEM values.
Empty headers preserve following fields; public URLs remain unchanged.
URL authority is masked before label matching can consume its @ delimiter;
a password containing `token=` cannot expose the URL username.

All final re-check cases run against a temporary archive of actual `6cbee5f`:
**36 fail and eight existing controls pass**, including both persisted inbox
requests and real activity-worker/MCP output. The same 44 cases pass with the
fix. Broader focused MCP/inbox checks: **190 passed**. Compilation, documentation
links and whitespace checks pass. Full suite: **2,697 passed in 440.89
seconds**; no known WaitUntil timing-flake retry needed.
No live installs, owner-data reads, configuration changes or model calls.


## 2026-10-24 — #119 review: shared credential redaction and EOF damage

Own worktree `/home/makin/src/nw-mcp-activity-review`, branch
`codex/mcp-activity-review`, clean start from #119 head `ff2ea3f`. Fetched and
merged `origin/main` (already current). Push target remains #119's
`codex/mcp-activity`; the original worker's worktree is unchanged.

Extended C3c's shared redactor with case-insensitive authorization/bearer,
spaced API key and AWS credential labels, quoted JSON escaping and mixed-case
private-key blocks. Activity passes read-only loaded Secrets values to that
same helper, before caps and worker replies, instead of maintaining its own
replacement loop. Label redaction precedes known-value replacement so a
Secrets value equal to a label cannot obscure the credential. Event scanning
counts an unfinished EOF line once even when it consumes the whole byte
window; complete leading fragments still count only as truncation.

Eleven regression cases fail against `ff2ea3f`, including worker stdout and
both MCP output forms, an oversized unfinished tail, escaped quoted values
and label-shadowing by a known value. Seven controls cover already-supported
labels and complete window fragments. All **146 focused MCP/inbox tests pass**;
compilation, documentation links and whitespace checks pass. Full suite:
**2,653 passed in 439.49 seconds**; no known WaitUntil timing-flake retry needed.
No live installs, model calls, configuration changes or owner-data reads.


## 2026-10-24 — MCP activity across sources

Own worktree `/home/makin/src/nw-mcp-activity`, branch `codex/mcp-activity`,
clean starting/fetched main `d86faf2`. Added read-only `get_activity(since,
limit)` across persisted run summaries, investigation terminal findings and
C1 event/receipt summaries. This gives the MCP client visibility of findings
that finish after their requesting run. The original `get_recent_events`
implementation and response shape remain unchanged.

Activity uses normalized UTC timestamps, inclusive since filtering and one
merged limit. Fixed-path descriptor reads refuse symlinks/special files and
never create, chmod or repair the shared folder. Per-record/line, byte-window
and directory/line-count caps bound the scan; damage counts and explicit source
truncation flags describe omissions. Safe projections exclude evidence,
event values, outbox messages, error details and run outputs. Known AOTN Secrets
values and common credential forms are redacted before text caps; unsafe
Secrets loading fails closed without content diagnostics. Tool discovery and
the [MCP guide](integrations/MCP.md#activity-across-runs-and-hermes) include the
new tool and the existing-client allowlist instruction.

Focused MCP verification: **73 passed**, including real stdio calls with a
temporary Hermes home, mixed sources, damaged JSON/UTF-8, unknown versions,
oversized files/lines, unfinished tails, UTC/offset/fractional ordering and
inclusive since filtering, newest-tail caps, Unicode, redaction, read-only
mode/content preservation, unsafe destinations and legacy compatibility.
Full suite: **2,635 passed in 437.16 seconds**; no known WaitUntil timing-flake
rerun needed. Compilation and whitespace checks pass. The docs
consolidation checker reports the pre-existing unexpected active doc
`SMALL_WINS.md`, reproduced against the #118 base; no other checker error.
No paid calls, live installs, external configuration changes or merges.

## 2026-10-24 — #118 review: byte consistency, decoded Unicode and ranges

Own worktree `/home/makin/src/nw-small-wins-build`, branch
`codex/small-wins-build`, clean starting head `4c780fc`; fetched and merged
`origin/main` (already current). Read lines now verifies the original raw byte
range across counting/extraction with bounded per-chunk SHA-256 fingerprints.
This catches same-inode rewrites even when the file grows, including changes
outside the excerpt, before any success/Vault publication. Append-only growth
remains valid; short reads are filled within bounded chunks and Stop yields.
Range ordering is checked on resolved positions before clamping. Check reply
recursively verifies decoded text and object keys encode as UTF-8, including
allowed extra fields; lone surrogates become `reply_mismatch` before outputs.
No UI changes or external configuration changes.

Verification: eleven regression cases fail against original `4c780fc` helpers
(three growing rewrites, a later-chunk change outside the excerpt, six decoded
Unicode cases, reversed negative range). Four controls pass before/after:
append-only growth, valid Unicode/persistence, ordered clamping and short reads.
All 15 review cases and 62 focused tests pass. Full suite: **2,609 passed
in 439.81 seconds**; no known WaitUntil timing-flake retry needed. Compilation,
documentation links and whitespace checks pass. [Updated contract](SMALL_WINS.md).


## 2026-10-23 — Small wins: bounded file excerpts and reply checks

Own worktree `/home/makin/src/nw-small-wins-build`, branch
`codex/small-wins-build`, clean start from fetched `origin/main` `472001c`.
Rendered Check reply v2 normal/80×24 before product changes in the shared
small-wins samples folder. Built three helper-specified nodes: Read lines,
Find lines and Check reply. Find keeps recent matches and offers the true
Match count in the Vault; Check uses Start-style compact table navigation and
row editors. Standard forwarding keeps computed Vault outputs independent.
Bounded allowed-folder snapshots close on Stop; JSON shape checks are strict.
Configured Reply uses an opt-in shared preview/editor with Stash mode rules.
[Contract](SMALL_WINS.md), [built screens](audits/small_wins_2026_10_23/README.md).
No real model call, install, Hermes configuration change or owner-data read.
Verification: **2,594 passed in 438.14 seconds** (full `pytest -q`); no known WaitUntil timing-flake retry needed. Helper node/UI checks, compilation, documentation links, whitespace and 41 focused behavioral/UI tests pass. Rejected-cap and generic-row in-memory mutations
fail the corresponding regressions (one cap case, both table viewport cases).
The first complete run had 2,593 passes and one selector inventory assertion
still expecting only System; updated its exact group expectation to include
Text files (and assert both members), plus Check reply in Utility. This is an
intentional inventory change, not a relaxed assertion. The updated selector
and all 41 small-wins tests pass together.


## 2026-10-23 — Investigation Unicode and stdout-cap review fixes (#117)

Branch `codex/c3c-inbox`, own worktree `/home/makin/src/nw-c3c-inbox`, starting
head `1329965`. Fetched and merged `origin/main` `5e7c4e3` first (already
integrated). Fixed both findings in the review comment.

- Write bounded UTF-8 JSON without ASCII expansion, so a valid 12,000-character
  finding containing emoji fits the 128 KiB record budget. Normalize lone
  surrogates with C1's UTF-8 replacement rule before counting/writing/reporting.
  The shared CLI answer parser preserves U+2028/U+0085 rather than rewriting
  them as LF; embedded session receipts are still rejected.
- A serialized finding rejected by the record-size limit now publishes an
  immediate `invalid_response` terminal failure and moves to failed, instead
  of leaving working/not-ready after successful cleanup.
- At the installed entry's final output boundary, reserve print's LF in the
  shared 3,500 UTF-16-unit budget, including all headers/escaping/truncation.
- Seven review regression cases fail against an isolated archive of `1329965`
  and pass with the fixes. Fake CLI subprocesses only; no real model calls,
  Hermes config/cron changes or live installation. Existing screens unchanged.

Verification: **2,541 passed in 432.48 seconds** (full `pytest -q`), no known WaitUntil timing-flake rerun needed; all seven regressions pass and all seven fail on `1329965`. Compilation, Bash syntax and whitespace checks pass.

## 2026-10-23 — C3c simple investigation inbox

Branch `codex/c3c-inbox`, worktree `/home/makin/src/nw-c3c-inbox`, clean start
from fetched `origin/main` `5e7c4e3` (#116 merged). Owner approved design samples
and chose workflow-gathered evidence plus a tool-free investigator; read-only
MCP evidence service is deferred, not built.

- Added helper specs, registered request/result nodes and generated contract/UI
  tests. Independent source choices for incident/excerpts; standard forwarding
  and optional Vault outputs, including plain State for Conditional. Existing
  multiline widgets retained because the preview editor has not landed.
- Atomic private versioned request/result files, C1 lock, repeat id reuse and
  durable admission/start counts. Options defaults: 5 investigations per UTC
  day, `aotn` profile. No workflow control of command/profile/cap. Requests
  publish owner policy in the shared root for the deterministic bridge.
- Named script-only cron entry and safe named install/check; one oldest claim,
  strict #116 disabled-tool preflight and argv-bound query, one turn, ignore
  rules, 90-second deadline with nested subreaper/descendant cleanup and Stop.
  Stale work is failed without paid retry; uncertain cleanup blocks starts.
  A pre-claim write regression ensures no result is fabricated for pending work.
- Secrets redacted before persistence; no evidence-file reads. Full bounded
  finding remains in the result; escaped/capped stdout is only a Telegram
  handoff. Usage stays honestly unknown; account billing remains authoritative.
- Updated the selector inventory test for the new entries. Full-suite review
  caught a test-only subreaper leak: real bridge tests now use disposable
  subprocesses, preserving later Git-process cleanup tests. The 48 inbox cases
  plus both affected checks passed together (50 total).
- Added setup/record documentation and real production-CSS captures at 110
  columns and 80×24. No Hermes changes, cron/config changes, installs or real
  model calls. No merge performed.

Verification: **2,534 passed in 423.50 seconds** (full `pytest -q`); no known WaitUntil timing-flake rerun needed. All 48 inbox tests and both affected integration checks passed together (50). Helper node/UI checks, compilation, Bash syntax, 17 real-screen captures, keyboard save/reopen/discard, doc links and whitespace pass.

## 2026-10-23 — Ask Hermes profile CLI rework (#116)

Branch `codex/ask-hermes`, worktree `/home/makin/src/nw-ask-hermes`, starting
head `c7f1b10`. Fetched and merged `origin/main` `f9f5f07` first (already
integrated). The owner's new profile route supersedes the original internal
worker compatibility bar; the old 2026-10-22 entry describes that earlier head.

- Removed the always-refuse worker. Use the public executable in machine
  Options (`hermes_command`, default `~/.local/bin/hermes`) with only its own
  `HERMES_HOME` (`hermes_profile_home`, default `~/.hermes/profiles/aotn`).
  Question is one bounded argv argument, no shell: `chat -q <question> -Q
  --source tool --max-turns 1 --ignore-rules`. Checked Folder remains the CWD.
  No Hermes internal imports, app env changes or fallback to the default profile.
- Strict `tools list --platform cli` before every question: all 24 known CLI
  toolsets must be present and disabled, no enabled/duplicate/missing/unknown
  lines or unclassified stderr. No cache; config identity/mtime/size checked
  across preflight. Listing failure prevents chat. Both phases share the H0
  process-tree deadline/Stop cleanup, including detached descendants.
- Missing profile/command and expired auth get the requested plain messages.
  Answer parsing drops session metadata and rejects empty/invalid/oversized
  output. The cap applies after CLI newline/metadata removal. `-Q` supplies no
  measured turns/tokens/cost; those stay null, with CLI limits separate.
- [New-user setup](../integrations/hermes/README.md#ask-hermes-setup) includes
  the owner's exact profile prompt, verification commands and profile-vs-OS
  isolation limits. Updated contract/standards/catalog/current plan and refreshed
  real screens, including both new Options at full size and 80×24.

One owner-authorized real question through the node, against the existing profile:
`Reply with exactly: AOTN profile smoke OK` → **AOTN profile smoke OK**, completed
in **5.518 seconds**. Temporary AOTN data/C1 receipts; no repository workflow
saved, no Hermes config/default-profile/gateway/cron/live install changed. The
CLI manages its own profile session/auth state. No other real questions ran.
[Smoke evidence](audits/ask_hermes_2026_10_22/profile-smoke.json).

Verification: **58 fake-CLI tests passed**, covering sources, literal argv/CWD/env,
per-run tool preflight, auth, malformed/oversized output, missing setup, timeout
and repeated Stop in either phase, detached descendants, records/usage/secret
redaction, exact caps (including emoji) and malformed Unicode without a stranded
broker. Request transport uses bounded escaped JSON; the question remains one
CLI argument. Helper node/UI checks and shared H0 regressions pass.
Final full `pytest -q`: **2,465 passed in 408.10 seconds**, no timing-flake
rerun. Compilation, docs consolidation/link checker and whitespace pass.

## 2026-10-22 — C3b part 1: guarded Ask Hermes

Branch `codex/ask-hermes`, own worktree `/home/makin/src/nw-ask-hermes`,
from fetched main `f9f5f07`. Implemented the approved Ask Hermes slice only;
the later task node and shared long-text editor remain separate work.

- Helper spec/generated registration and smoke/UI tests; standard Question
  sources, checked Folder, 10–300-second total limit, Answer forwarding and
  optional independent Vault-only Run details. Machine Options owns installation
  and explicit acceptance of no dollar cap (off by default).
- Stdlib-only isolated compatibility gate refuses the installed Hermes before
  imports/auth/memory/inference: **no compatible adapter is enabled**. The source
  audit found plugin discovery and additional retry/maintenance paths that
  cannot guarantee the approved one-turn/no-tools/read-only policy. Unknown
  versions also refuse; no workflow bypass. Exact refusal and future audit
  requirements are in the [contract](integrations/ASK_HERMES.md).
- Async broker reuses H0's subreaper/process-tree cleanup and adds bounded stdin
  transport to its collector. Deadline/Stop kills and reaps detached descendants;
  repeated Stop is shielded. Retained ownership markers block calls after an
  unconfirmed cleanup. Nonretryable errors publish no partial answer.
- Private per-invocation JSONL records plus C1 intent/terminal receipts; timestamps,
  limits, bounded answer/digest, usage and safe errors. Known secrets redacted,
  unrelated credential env removed, raw stderr discarded. Usage survives disabled
  Vault/forwarding in Execution, run JSON and saved summaries; per-run totals
  mark missing/partial estimates. No auth/account switch or pricing call.
- [Built screens](audits/ask_hermes_2026_10_22/README.md): real production styles,
  Parameters/Source/Payloads, forwarding, selector, small workflow, 80×24 states,
  and actual Execution with a fake worker. Save/Close geometry checked; PNGs
  visually inspected. Current multiline editing is preserved.

Verification: helper node/UI checks, compilation, focused fake-worker/process
regressions and real Execution/run-history checks passed. The initial full run
was 2,444 passed / one failure: selector inventory still expected four AI nodes.
Updated both count assertions to five and added the exact membership check;
the focused selector test passes. Final full `pytest -q`: **2,445 passed in 400.74 seconds**; the known Wait Until
timing flake did not occur. Docs consolidation/link checker and whitespace
passed. No real inference, Hermes changes, secrets in saves/logs or live install.

## 2026-10-22 — Shared long-text UI backlog proposal

Branch `codex/docs-long-text-proposal`, from fetched main `a58a686`.
After the C3b samples were complete, recorded the owner's preview-only multiline
proposal beside selector sorting in the UI consistency pass, after C3b, samples
first and not approved for implementation. Includes full-screen Save/Cancel,
dirty-Esc, focus return and Stash S3 paste rules; single-line editing stays inline.
C3b shared samples illustrate previews only; no product behavior was changed.
Verification: documentation consolidation/link checker and `git diff --check`.

## 2026-10-22 — Telegram launcher review fixes (#114)

Branch `codex/telegram-launcher`, review base `89c9d2a`, worktree
`/home/makin/src/nw-telegram-launcher`. Fetched main remains `bfcdc36`; already
integrated. All three findings in the PR review are fixed.

1. The launcher's timestamp uses CLI `--input-if-declared checked_at=...`,
   filtered against the loaded Start contract before typed input resolution.
   Callable workflows without that row run with valid saved defaults; heartbeat
   timestamp behavior is unchanged. Explicit `--input` keeps precedence.
2. Install and check refuse directories, FIFOs, symlinks and dangling links.
   Installation checks again before rename, uses `mv -T` to prevent moving
   inside a directory, and cleans its temporary file on failure.
3. Drift detection includes exact modes: 755 for entry scripts, 644 for shared
   files. Check reports drift without writes; install repairs it atomically.

Failing-first proof on `89c9d2a`: **11 failures, 4 passes** in the new review
cases. Callable launch exited 5 while ordinary CLI succeeded; directory/FIFO
installs were accepted; wrong modes were reported up to date. The four
symlink cases already passed. After the fixes, all **15 review cases passed**.
Full `pytest -q`: **2,403 passed in 395.57 seconds**, no Wait Until rerun needed.
Compilation, Bash syntax, documentation consolidation and whitespace checks
passed. Updated the adapter guide, CLI input reference, Current State and
coordination status. No live install, Hermes config, cron or owner workflow
changes. Pushed for owner re-review; #114 remains unmerged.

## 2026-10-22 — Telegram launcher v0

Branch `codex/telegram-launcher`, from fetched main `bfcdc36`, in the clean
worktree `/home/makin/src/nw-telegram-launcher`. Read the October 22 PLAN RESET
and Hermes quick-command answer in the shared notes, adapter guide and approved
coordination order first. #113 is now merged; this is the next requested slice.

- Added repository template `aotn-run-template.sh`, installed as
  `aotn-run-<slug>.sh`: filename selects the saved workflow,
  arguments are refused, and production checkout/interpreter/cron-data paths
  are fixed. No workflow is built or replaced.
- Added `--telegram-launcher` to the existing JSON adapter: a 25-second budget
  including cleanup, H0 escaping and 3,500 UTF-16-unit cap, outputs on success
  and one plain failure line otherwise. INT at 20 s, KILL at 24 s, final second
  for reaping; late signals/overflow cannot extend this budget. Existing calls
  retain H0's 100-second mode and lock/cleanup rules.
- V0 supplies only the heartbeat's `checked_at` UTC timestamp. Other required
  inputs need saved defaults or get a clear refusal. Empty/missing workflow
  data gets one line; child tracebacks/diagnostics are not Telegram replies.
- `install.sh --run-command <slug>` installs only the adapter and named copy;
  `--check` compares without writing. The README includes a top-level
  `quick_commands` example and deployment/timeout/input limits, not applied.
- Verification: **2,388 passed in 395.97 seconds** (full `pytest -q`), with no
  timing-flake rerun. Launcher/H0 focused run: **89 passed**; the expanded
  launcher-only run: **21 passed**. Subprocess coverage includes a real
  25-second timeout, detached-descendant kill/reap, late signal budget,
  slug/argument checks, input refusal, missing workflow, escaping/cap, empty
  output, stale lock and named install/check in disposable folders.
  After the portable template filename was finalized, launcher subprocess checks
  passed again: **21 passed in 29.19 seconds**. Compilation, Bash syntax,
  documentation consolidation and whitespace checks passed. No live
  installation, Hermes config, cron or owner workflow changes.

Ready for owner review; not merged. Stop here after opening the PR.

## 2026-10-22 — Integrate main into System forwarding (#113)

Branch `codex/system-node-forwarding`, previously `a4ecc80`, merged fetched
`origin/main` `670b3b3` after #110 and #112 landed. Retained both sides' log,
current-state and coordination entries, ordering dated log entries newest first.
Updated current status and the coordination order to reflect those merges;
NODE_STANDARDS explicitly covers Remember/Recall's standard forwarding checkbox
and independent own-value Vault outputs alongside the System report behavior.

Verification from this worktree's app with the shared WSL interpreter:
full `pytest -q`: **2,367 passed in 370.24 seconds**; no Wait Until rerun needed.
Compilation, documentation link/archive checks and whitespace checks passed.
An initial pytest invocation from the repository root failed collection; the
reported full result is the subsequent run from `AttackOfTheNodes/`.
Every existing Session Log entry from both parents was checked intact.
No live jobs or owner workflows changed. #113 remains for the owner to merge;
Telegram launcher work awaits the owner's next prompt.

## 2026-10-22 — C2 re-check fixes and forwarding (#110)

- An Add whose result is not a finite number (an overflowing float, or an
  integer too large for a float) is refused as `not_a_number`; every value
  passes one rule on write and read (plain JSON, finite numbers at any depth,
  64 KB), so nothing written can make the store unreadable.
- Remember and Recall use the standard Forward incoming payload unchanged
  control (owner): the next node gets the incoming payload; the Vault output
  still gets the node's own value.
- Main (#111, #112) merged in; both sides' log and status entries kept.

## 2026-10-22 — System nodes: standard forwarding control

Branch `codex/system-node-forwarding`, from fetched main `9470729`. The owner
requested the same Forward incoming payload unchanged control used by the
recent output nodes for Disk space, Git status and File age.

All three declare the pass-through capability and use the existing standard
Payloads composer. Their shared output helper stores the computed report in
the Vault first, then chooses the original incoming payload when forwarding
or the computed report when unchecked. No custom screen or color rules.
Helper specs retain the flags; existing execution, path restrictions and
Git process handling remain intact.

New regressions failed before the fix and now cover non-text payload identity,
forwarding on/off, report-specific Vault types (number, bool, string, var),
producer tracing, and production-style keyboard toggle/save/reopen at 80×24
and 120×40. Focused System/no-edit checks: 38 passed. All three helper specs
match their classes; helper registration/UI checks passed.
Full suite: **2,176 passed in 341.54 seconds** (full `pytest -q`). Docs link/archive and whitespace checks
passed. No repository workflows edited; awaiting owner review, not merged.

## 2026-10-22 — Choice-node review fixes (#112)

Review head: `6c7467b`. Working branch `codex/choice-review-fixes` in
`/home/makin/src/nw-choice-review`; changes publish to `dist/pick-one`.
Merged current `origin/main` `9470729` first (`d5d2f02`), retaining both sides'
Session Log entries, current coordination order/live status and C3a build facts.

- Reserved literal `unsure` for the low-confidence result. Answer rows reject
  that value and leading/trailing Unicode whitespace through shared opt-in
  schema checks used by form-save, preflight and runtime. Case and internal
  spaces remain exact; nothing is silently trimmed.
- Added a 20,000-character text cap for Upstream, Vault and Configured sources
  before HTTP or Vault writes, with nonretryable `text_too_long` and the clear
  message "Text is too long for Jev". The shared client also enforces the cap.
  Helper spec, metadata/error assertions and authoring rules describe the same
  behavior.
- Failing-first proof on the merged code: 16 new cases failed and the exact
  20,000-character boundary passed. Cases cover real form-save refusal,
  validator/runtime rejection, all text sources, loopback request prevention
  and the shared client. The older edge-space acceptance case now checks valid
  internal spaces, Unicode and case preservation to match the reviewed policy.
- Verification: **89 focused tests passed**; full `pytest -q`: **2,245 passed
  in 345.91 seconds** on the combined branch. Targeted compilation,
  documentation consolidation and whitespace checks passed. All provider tests
  use loopback; no paid calls, owner workflow edits or live integration changes.

## 2026-10-22 — C3a owner correction: standard forwarding (#112)

Same branch. Pick one now advertises the standard pass-through capability and
shows **Forward incoming payload unchanged**, replacing Publish downstream
payload. Checking it hides and disables the own-output name/description fields
and sends
the original upstream payload downstream; unchecking restores the answer.
The configured text source affects what is judged, not what is forwarded.
Enabled Vault outputs still store the answer and Pick details.

Regression cases failed on the prior head, then passed after the fix: three
text sources, non-text payload identity, keyboard toggle/save/reopen, and a
real RunService route with forwarding on and off. Updated built screenshots
include the checked state. Verification: **2,228 passed in 346.02 seconds** (full `pytest -q`); helper registration/UI,
docs link/archive and whitespace checks passed.

## 2026-10-22 — C3a: Pick one, built for owner review

Branch `dist/pick-one`, from main `cce4fc7`. Owner-approved samples and
revisions are implemented: one fixed service, no provider/model selectors,
exact answer rows with duplicate-save refusal, and literal `unsure` below the
cutoff. New helper spec, registered node and reusable async HTTP client;
API credentials are resolved through the secrets store, never workflow config.
The total deadline defaults to 20 seconds; transport/service errors and
malformed replies use safe fixed errors, redirects are refused, and task
cancellation closes the connection. Only timeout/service errors offer Retry.

Answer is plain text for a following Conditional and can also be copied to
the Vault. Pick details starts off, has an independent Vault destination, and
never becomes a downstream path or Parameters branch-name control. Shared
form, declaration and preflight support now preserves multiple Vault outputs.
Payload headers use the documented `PAYLOAD` and `TYPE` color roles.

[Built screens](audits/pick_one_2026_10_22/README.md) include full Parameters,
Source, Payloads, selector and routing map, with compact 80×24 captures.
The capture harness clears this shell's monochrome override and uses real
registered screens with production styles. Tests exercise keyboard edit/save,
no-edit save, duplicate refusal, reopening/Cancel and independent routing.
Default answer rows have stable IDs so no-edit saves do not mutate config.
The selector test's AI Processing member count intentionally rises from 3 to 4.

Verification: 2,222 passed in 347.10 seconds (full `pytest -q`). Helper `check_node` and `check_ui`, docs
link/archive consolidation, and whitespace checks pass. HTTP tests use a
loopback fake server (including timeout, cancellation, malformed responses,
exact matching and secret-safe failures); an actual RunService test routes
its plain answer through Conditional and Text Output. No paid call, owner
workflow edit, local installation or cron job. PR awaits owner review.

## 2026-10-22 — Coordination documentation review fixes (#111)

Same branch, after review of `6bf9576`. Documentation only.

- Updated C3a to the approved Jev-only Jev: Pick one: no provider/model
  selectors, shared client module, samples approved October 22, and always
  pass `unsure` below the cutoff (default 0.3), with no Stop option.
- Recorded the Hermes `quick_commands` answer (source `556bf7c5c`): `type: exec`
  scripts run after normal sender auth, without an agent turn, plugin or args.
  Config is the allowlist. Each `aotn-run-<slug>.sh` needs its own deadline
  under the 30 s reply timeout, which does not kill the script; enforce kill/reap.
- Added the simple-purpose-node principle to the new-ideas mapping and selector
  sorting to Project Backlog after C3a. The cancelled Category rename remains
  cancelled. Updated the archive notice so its old command investigation is
  clearly superseded.
- Recorded #110's re-check: original eight findings fixed at `a685821`, with a
  new P1 numeric-overflow/store-readability issue whose fix is pending.
- Verification: documentation consolidation checker and `git diff --check`.
  No application, live gateway or scheduled workflow changes.

## 2026-10-22 — Coordination status refresh and owner plan reset

Branch: `codex/docs-plan-reset`, based on fetched `origin/main` `cce4fc7`,
in `/home/makin/src/nw-plan-reset`. Documentation only, at the owner's request.

- Refreshed Current State: H0 live heartbeat `63968ee90ae0`; C1 merged in #109
  and live drain `cd14afa83db9`, with owner-confirmed Telegram delivery; C4
  merged in #107/#108; C2 open as #110 at `a685821`; H2 parked as an unscheduled
  template. GitHub confirms the open PR; deployment evidence comes from shared
  notes and the owner's confirmation, not a new live run in this task.
- Recorded the October 22 owner order in AI Coordination Proposal section 9:
  C2, C3a, thin Telegram launcher, C3b, 4e–4f, P1, Phase 17 verification,
  C5, Step 5, C6 and Step 6. Added the short mapping of new ideas to that plan.
- Moved the uncommitted intent/designer conversation from `nw-review109` into
  `archive/plans/INTENT_ROUTING_AND_DESIGN_ASSISTANT.md`, rebased its local
  links and marked its old recommendations/prompts as reference history.
  Section 9 links it without adding another active plan document.
- Verification: documentation consolidation checker and `git diff --check` passed.
  No application tests, implementation, cron changes or gateway activation.

## 2026-10-22 — C2 review fixes (#110, eight findings)

Each finding has a regression test that fails on `a308fa8`.

1. Changes lock with `msvcrt` on Windows too; with no lock available they
   are refused, never done unlocked.
2. Every record is checked whole (id, name, place, times, and that the value
   matches its type); a damaged file is `store_unreadable` and left as it is.
3. Renaming a workflow leaves its values alone while another workflow (a
   standard workflow and a subworkflow may share a name) still has the old name.
4. Change and Forget show names as text (escaped markup).
5. Change keeps the value exactly (the name prompt no longer trims it).
6. `var` must be a JSON list or record, and numbers finite, in the CLI,
   Change and Recall's starting value.
7. Invalid UTF-8 is `store_unreadable`; the Stash still opens.
8. The CLI and Stash tab group and filter by the place itself; a workflow
   named "All workflows" shows as "All workflows (workflow)".

## 2026-10-21 — C2: Saved values (persistent store on the Stash's store)

Branch `dist/persistent-store` from main `cce4fc7`. Samples approved with
eleven answers, then one change: If changed's paths are **Changed** and
**No change**, and its first-run setting reads "First run (nothing saved
yet): No change · save quietly / Changed · send it on". Decisions are
recorded in [Saved values](STASH_PROPOSAL.md#saved-values-c2).

- `backend/saved_values.py`: `saved.json` (`aotn-saved/1`) beside the Stash's
  entries; places are a workflow's name or All workflows; each change is
  lock → re-read → change one value → atomic write. A multi-process test
  proves counters lose nothing.
- Nodes from helper specs: `remember_node` (Replace or Add), `recall_node`
  (strict Type, which is also the output's type; starting value or stop),
  `if_changed_node` (compare and save in one step; paths Changed / No change,
  with plain "path name" fields).
- Stash tab 3 Saved values (E change, X forget); `aotn stash saved`;
  `aotn --data-dir`; workflow renames move values; runs record where they
  came from (`app`, `command line`, `MCP`).

## 2026-10-21 — C1 review fixes (#109, eight findings)

Same branch, after main was merged in (`4ad68c2`). Each finding has a
regression test that fails on `4ad68c2` for the reported reason.

1. An unfinished last line (a writer killed mid-line) is moved to
   `<file>.bad.jsonl` and cut off before the next append, in the nodes and
   the drain.
2. A repeat is remembered only after its record is written.
3. A message with Hermes commands allowed goes out alone; other messages wait
   for the next tick, so its `[SILENT]` never hides them.
4. The drain splits the outbox on LF only (U+2028 / U+0085 stay inside a line).
5. The finished digest, header and notes included, fits 3,500 UTF-16 units;
   cutting counts the same units.
6. One folder for both sides: `$HERMES_HOME/aotn` (`HERMES_HOME` defaults to
   `~/.hermes`). The `hermes_folder` Option is gone.
7. Repeat times in the future count as expired.
8. Folder 700 and files 600 are enforced on existing contents too, by the
   nodes and the drain; symbolic links are refused.

## 2026-10-21 — C1: Notify me, Record event and the outbox drain

Branch `dist/hermes-notify`, from main `6f5c216`. The owner approved the
sample screens (after asking for lighter config screens: hints inside the
fields, `Name · what it does` dropdown items) and answered the open questions.

- `backend/hermes_folder.py`: the shared folder (`~/.hermes/aotn`, later
  `$HERMES_HOME/aotn`; folder 700, files 600, one `flock` for every change),
  escaping identical to the H0 adapter's, Telegram-length cutting, repeats.
  Formats: [Hermes shared folder](integrations/HERMES_SHARED_FOLDER.md).
- `hermes_notify_node` (Notify me) and `record_event_node` (Record event),
  generated from helper specs, group Hermes in Outputs. Both forward their
  input by default. Send to lists Options `hermes_send_to_names` through a new
  select key `options_from_setting` (Node Config).
- `NodeContext.workflow_name`, set by the supervisor, so records say which
  workflow sent them.
- `integrations/hermes/_aotn_drain.py` + `aotn-drain-home.sh`: one digest per
  tick, urgent first with ⚠, 3,500 characters, overflow waits, bad lines set
  aside, `handed_off` receipts after printing. `install.sh` copies them too.
- Owner answers: the Hermes folder is not limited by `system_node_folders`;
  Urgent goes first with ⚠ and does not ring; "Quiet" dropped (Hermes has no
  per-job silent option; follow-up Q7); drain every 5 minutes, one job per
  name; Send to names in Options.
- Tests: `tests/test_hermes_notify.py`, `tests/test_hermes_drain.py`, the
  generated node tests (pointed at a temporary folder), install list updated.

## 2026-10-21 — C4 local stdio MCP server

Branch `codex/mcp-stdio`, based on fetched main `6f5c216`; isolated worktree
`/home/makin/src/nw-mcp`. No changes to the owner or cron live checkout.

- Added `aotn_mcp/` and `aotn mcp`: standard-library newline-delimited JSON-RPC,
  initialization/version negotiation, typed tool schemas, JSON text and
  structured results, ping, cancellation and EOF/signal shutdown. The official
  Python MCP SDK is absent from `requirements.lock`; no dependency was added.
- Four tools list saved contracts, run unattended workflows with typed/native
  JSON and named Stash inputs, read a persisted run summary and list recent run
  summaries. Contract C25 rejects potential prompts, including nested calls,
  before starting. The existing unattended provider also rejects runtime input.
- Select data before backend import. Saved-library lookup excludes arbitrary
  workflow paths; run IDs/arguments are validated. Only a configured repository
  workflow library is refused; other chosen libraries remain usable. Logging
  and incidental worker stdout go to stderr, leaving stdout to the protocol.
- Each tool has an isolated subprocess and deadline, including queue time.
  Timeout/cancellation/EOF/TERM kill and reap the worker; Linux subreaper and
  `/proc` ancestry cover escaped descendants. Cleanup is bounded and blocks
  further starts if unconfirmed. No engine or TUI changes.
- Documented setup for local clients in `integrations/MCP.md`; packaged the new
  module in the wheel. Wheel build/package-content check and an isolated
  built-wheel initialize/list-workflows/EOF smoke test passed.
- Verification with the shared Linux Python 3.14.4 interpreter: **46 MCP
  subprocess tests passed in 7.00 seconds**; full suite with disposable
  `AOTN_DATA_DIR`: **2,104 passed in 330.71 seconds**. Compileall, documentation
  link/archive checks and `git diff --check` passed.
- No client configuration, Hermes installation, cron activation or workflow
  library edits. One PR; owner review/merge is the next gate.

## 2026-10-21 — H0 install: live checkout and copies (Hermes v0.14 check)

Branch `dist/hermes-live-install`, from main `531b8d2`. Hermes inspected its
installed scheduler before installing: it rejects any script whose real path
is outside `$HERMES_HOME/scripts` (so no symlinks), and the planned live
checkout did not exist yet. The owner's main checkout is on an old branch, so
cron must not run from it.

- The wrapper's project root is now `/home/makin/src/aotn-live`: a worktree on
  branch `live` tracking main, updated on purpose with `git pull`.
- `integrations/hermes/install.sh` copies the four files into
  `$HERMES_HOME/scripts` (entry scripts executable, atomic replace, refuses a
  symlink at the target); `--check` reports drift without changing anything.
- Tests: three install tests in `tests/test_hermes_adapter.py`.

## 2026-10-21 — H0 review fixes: descendant containment and entry scripts

Branch `codex/hermes-h0-adapter`, original head `057ca45`; synchronized with
main `055dfba` (#104) in merge commit `e8ffbd0`, preserving both session entries.

- P2: enable Linux child-subreaper adoption via guarded `ctypes`/`prctl`, walk
  `/proc` ancestry, kill escaped descendants and reap them before releasing the
  slug lock. Cleanup also runs on natural exits and adapter errors. Reserve the
  final second of the deadline/stop budget for bounded kill/reap; an unconfirmed
  cleanup returns 70 and leaves a persistent stale marker, so later ticks return
  75 without starting a child. A crash also leaves the marker. Other POSIX
  platforms retain bounded process-group cleanup; Linux setup failures prevent
  spawning. The contract and integration guide document these behavior changes.
- P3: both actual entry scripts honor `HERMES_HOME` and run from an isolated
  deployment with spaces. Only fixed installation path assignments in the copied
  shared file are substituted; Bash exec, the adapter and controlled children
  are real subprocesses. Normal calls reach the right slug; extra arguments
  return 70 without starting a run.
- Fail-first evidence against `057ca45`: the initial deadline/TERM and entry
  deployment cases produced **6 failures** before implementation. Additional
  cleanup-denied/timeout and natural-exit cases ran against the original adapter
  extracted with `git show`, producing **3 failures**. Both logs were retained
  under `/tmp/review103-red*.log` for this session. After fixes, **67 adapter
  tests passed**, including retained same-group cases, escaped sessions, actual
  reaping, denied/ineffective-kill fault injection and stale-lock rejection.
- An unaccelerated escaped-descendant probe exited **124 at 99.06 seconds**,
  emitted zero stdout bytes and confirmed the descendant was reaped. Removing
  `"$@"` from each temporary deployed entry was detected by the new argument
  test (both mutations failed as intended).
- Combined full suite (main `055dfba` plus fixes), shared Linux interpreter,
  disposable `AOTN_DATA_DIR`: **2,052 passed in 322.44 seconds**. Separate adapter
  run: **67 passed in 22.66 seconds**. Compileall, Bash syntax, documentation
  link/archive checks and `git diff --check` passed. No repository workflow edits,
  Hermes installation, cron activation or live delivery. Owner review follows
  the pushed fixes; no merge is authorized.

## 2026-10-20 — H0 repository adapter implementation

Branch `codex/hermes-h0-adapter`, based on main `b7e6484`; read PR #102's
owner decisions C1–C7 without merging that docs PR. The owner authorized
implementation under `integrations/hermes/`: shared Bash function, two entry
scripts, standard-library Python JSON/exit adapter and the H1/H2 build specs.
No engine or repository workflow files changed. No Hermes installation,
configuration, cron job or live delivery was performed.

The function derives a validated slug from the entry filename and uses the
absolute project/interpreter and separate cron library. The adapter supplies
UTC `checked_at`, drains both pipes with bounded retention, renders the JSON
report like the text CLI, leaves successful empty stdout at zero bytes, and
escapes directives before the 3,500 UTF-16-unit cap. Ordinary lines keep their
text; only JSON-looking lines get `| `, including after non-LF separators.
Run IDs survive truncation and graceful stops. Per-slug locks remain held
through process-group cleanup. Natural exits are preserved; failures/overlap/
deadline/external INT/TERM use 70/75/124/130/143 as specified.

Verification: all **57 adapter subprocess tests passed**, covering every draft
case-table row. Real CLI builds/runs use disposable data and loopback HTTP:
heartbeat, healthy/whitespace silence, degraded body, handled 503/refusal/timeout,
unhandled error, missing input and missing saved name. Controlled children
exercise malformed/oversized reports, simultaneous pipe floods, directive
variants, emoji caps, lock lifetime, signals and lingering descendants. Timing
tests shorten module constants only in a test subprocess launcher; production
has no timing override. A separate unaccelerated production-deadline probe
forced cleanup at **100.05 seconds**, exit **124**, zero stdout bytes.

Full suite from `AttackOfTheNodes/`, with the shared interpreter and
`AOTN_DATA_DIR=/tmp/hermes-h0-final-suite`: **2,016 passed in 320.17 seconds**.
Bash syntax, adapter compilation, `git diff --check` and the documentation
link/archive checker passed. Owner review is the next step; activation and
all later coordination capabilities remain separate.

## 2026-10-20 — System nodes: Disk space, Git status, File age (C7)

Branch `dist/system-nodes`, from main. Owner decision C7: specific command
nodes first; the owner left the details to Claude, with reasons:

- **Allowed folders:** a new Options value `system_node_folders` (`;`-
  separated, default `~`). Paths outside it fail `not_allowed`, so a received
  workflow cannot inspect the whole machine. Nodes read it through a new
  `NodeContext.get_setting`, wired from the run's ConfigurationManager.
- **Family/section:** Inputs family, selector section "System".
- **One typed value per node:** the samples drew several payloads per node,
  but the output model has one downstream output (optionally copied to the
  Vault), so each node has a **Report** choice instead. A Conditional can
  compare the value directly.
- **Nodes:** Disk space and File age use the standard library (no command);
  Git status runs only `git status --porcelain=v2 --branch`, argv, no shell,
  15 s timeout, its output type follows Report.
- Generated with `aotn_node_helper` (specs added); execution hand-written and
  the generated smoke tests adjusted to expect coded refusals.
- Tests: `tests/test_system_nodes.py` plus the generated tests.
- Review (#104, Codex): a repository's `core.fsmonitor` (and other run-a-program settings) are off for
  status; the repository Git finds must itself be allowed; git runs in its own process group, killed and
  reaped on stop or timeout; status is read NUL-separated (spaces, renames, accents kept); an empty
  `system_node_folders` allows nothing. Six tests, each failing before its fix.

## 2026-10-20 — H0 quiet End update and review corrections

Branch `codex/hermes-h0-spec`, PR #97; merged main `f86fbe8` in `e9f0df5`,
keeping both the H0 and main session entries. H1/H2 now finish with End
nodes using `record_line: false` from #99, rather than terminal No-Op nodes.
The wrapper draft also incorporates the two confirmed self-review findings:
escape every silent-marker case variant recognized by Hermes, and translate
external SIGTERM into the child's handled SIGINT path for graceful cleanup.
The adapter remains unimplemented; this change is documentation only.

Both extracted specs passed CLI build/check and build/save/reload against
this updated checkout. All 13 isolated CLI cases passed again, including
one-line heartbeat output, zero-byte healthy watchdog stdout, HTTP failure
routes and nonzero unhandled-error exits. Required-input warnings remain
expected. Docs links/archive/session preservation and whitespace checks pass;
no full suite rerun for this docs-only update, no live Hermes/Telegram test,
and no repository workflow edits. Existing historical receipts below remain
unchanged.

## 2026-10-20 — H0 wrapper and workflow specification draft

Branch `codex/hermes-h0-spec`, from fresh main `7227b1b` (#94–#96 merged).
Owner requested the H0 docs draft while other sessions own Step 4d and the
Editor Validation Panel. No changes to those files or to engine code.

- Added [the draft](integrations/HERMES_H0_DRAFT.md): filename-derived wrapper
  names, separate cron data directory, absolute interpreter/checkout entry,
  an external JSON-output adapter preserving natural exit codes, escaped
  and bounded stdout/stderr, timeout/signal/overlap semantics, and a later
  activation checklist. Adapter behavior is a specification, not installed
  or tested implementation; Hermes assumptions still require rechecking.
- Two complete `aotn-workflow/1` JSON specs: timestamped heartbeat and HTTP
  body watchdog with conditional silence and handled network/timeout/status
  alerts. Real runs revealed End always adds `[END] ...`; terminal No-Op
  nodes preserve one heartbeat message and zero-byte healthy stdout.
- Verification: both extracted JSON specs passed CLI `build --check` and
  build/save/reload in temporary data directories. Thirteen CLI run cases
  passed: heartbeat text/JSON, healthy and whitespace-healthy bodies,
  unhealthy/directive-bearing bodies, HTTP 503, timeout, healthy text with
  empty stdout, refused connection, missing timestamp, unknown name and an
  unhandled-error variant. HTTP used an ephemeral loopback fixture; the
  scratch spec alone changed its URL. Required-input warnings are expected.
- Relative links/anchors, archive/session preservation and `git diff --check`
  passed. Full suite was not rerun for this docs-only change. No live Hermes
  job, Telegram message, wrapper implementation or repository workflow edit.
- No own open prompt-queue PR or Codex prompt-queue branch was present to
  close; duplicate queue work is dropped in favor of merged #96. Other
  workers' worktrees and the owner's dirty checkout remain untouched.

## 2026-10-20 — AI coordination decisions C1–C7

Owner accepted the suggested answers for C1–C6 (build order accepted,
`~/.hermes/aotn/` owned by AOTN, digest drain, `cron.wrap_response` off —
revised to on for now on 2026-10-21, since Hermes applies it to every job —
persistent store on the Stash's store, scheduling decided at Step 5). C7:
specific command nodes first (fixed command, typed settings, argv, typed
outputs); a generic `run_command_node` later behind a Settings allowlist with
approval on. Recorded in the proposal's section 10.

## 2026-10-20 — H0 draft review fixes (#97)

Owner asked for review, fixes and merge. Ran both H1/H2 specs against main
`6e37909`: heartbeat one line; healthy watchdog silent; unexpected body,
HTTP 503 and refused connection one fixed message each, exit 0; missing
input exit 5 with the new "Can't start" list; unknown workflow exit 4.

- The adapter prefixes `| ` only to a line that starts with `{` (the
  `wakeAgent` risk); ordinary lines, such as the heartbeat, are unchanged.
- Stale "Stash bindings" wording replaced: 4d is built as Stash entries
  saved by name (#101), here and in the coordination proposal.

## 2026-10-20 — A quiet End node

Branch `dist/quiet-end`, from main `7227b1b`. Found by the H0 Hermes draft
(#97): every End adds `[END] Branch completed` to the run's output, so a
healthy watchdog could never stay silent. Owner samples approved, on by
default.

- End's Parameters tab: "Add a line to the output" (`record_line`, on by
  default) and "Line" (shown only when on). Off, the End adds nothing to the
  output; saved Ends without the setting keep their line.
- Field descriptions in Node Config are drawn as plain text (a description
  containing `[END]` lost it to markup).
- Tests: `tests/test_quiet_end.py`.

## 2026-10-20 — One colour per meaning

Branch `dist/ui-colors`, from main `7227b1b`. Owner: text colours were all
over the place. `frontend/colors.py` names one colour per meaning (MUTED,
TYPE, SOURCE, SUCCESS, RUNNING, WARNING, ERROR, HIGHLIGHT, MAP_BACKGROUND,
BRANCH_PATHS); UI_QUICK_REFERENCE "Colours" is the reference. Existing code
moved onto it: `[dim]` became MUTED, sources and destinations (`Vault key
"count"`, `next node`, Vault log Source) now use SOURCE. `tests/test_colors.py`
fails on any colour literal outside `colors.py`. Then: fixed hex values for
every role (named ANSI colours vary by terminal), `colors.PALETTES` +
`colors.use(name)` for later theme swaps, and a 4.5:1 contrast test on the
map, panel and highlight backgrounds (MUTED and ERROR were brightened to
pass). Owner approved four more roles: NAME (node names), PAYLOAD (input and
payload names), KEY (Vault key names), VALUE (literal values), applied to
the Subworkflow tables, the editor details, the Vault log and the Execution
details.

## 2026-10-20 — AI coordination proposal (docs only)

Branch `docs/ai-coordination-proposal`, from main `2ecd297`. Adds
`AI_COORDINATION_PROPOSAL.md`, written in an owner planning chat (not
approved): Hermes cron/Telegram integration through `aotn run` wrappers and
an outbox, staged receipts, stdout escaping, deterministic tool nodes,
bounded agent nodes and a proposed build order.

- Updated the AOTN facts against main: contracts and typed `--input` are
  built (exit 5 for bad inputs, 64 for usage), subworkflows and the Stash
  exist, headless callers fail fast on a prompting subworkflow. The tool-gap
  table, the `notify_me` and MCP notes and the build order (finish 4c first,
  then H0–C4 ahead of 4d–4f and Step 5) follow. Hermes facts unchanged.
- Listed as a temporary doc in README, CURRENT_STATE and the docs check.
- Owner framing added (section 1.1): Hermes is a near-term shortcut, not a
  dependency; each Hermes piece has an AOTN-native replacement, and nothing
  in the engine needs Hermes. Section 1.2 and build step P1: a first
  community of Hermes users, with the packaging it needs.

## 2026-10-20 — Prompts queue (C19)

Branch `dist/4c3-prompt-queue`, stacked on `dist/4c2-watch-calls` (#94, not
yet merged). A second `USER_INPUT_NEEDED` arriving while a prompt was open
was dropped, so its branch waited forever (two parallel User Input branches,
or a subworkflow and its caller both asking).

- **TUI:** the app keeps a queue of prompts and shows the next one when the
  open prompt closes, in arrival order, with the 4c-2 asker and path. It
  skips a prompt whose run is no longer current or whose branch no longer
  waits, and a run reset clears the queue.
- **Engine:** `MasterState.waiting_for_input(branch_id)` (root branches, or a
  subworkflow's through the call tree) and `Supervisor.waiting_for_input`.
- Tests: `tests/test_prompt_queue.py` (two parallel prompts answered in
  order; a stopped run's queued prompt is not shown; a new run drops the
  queue). Full suite 1,918 passed.

## 2026-10-20 — 4c-2: watching a running subworkflow, labelled prompts

Branch `dist/4c2-watch-calls`, from main `2ecd297` (#91–#93). Owner samples
2026-10-20, with the owner's answers: E and Enter act the same, opening is
manual, finished calls are not opened, and a long breadcrumb is shortened.

- **Engine:** a call forwards its run's events (workflow state, supervisor
  register/state/terminating, node execution, node timing) to the root run's
  bus inside `SUBWORKFLOW_RUN_UPDATE`, tagged with the invocation id, the
  calling run and node and the call path, so the root run's own state is
  untouched; `SUBWORKFLOW_RUN_ENDED` follows. `MasterState.memory_bank` is
  readable.
- **TUI:** `frontend/child_runs.py` keeps one record per live call, built as
  the app builds the root run's, and drops it when the call ends. The
  Execution screen shows either the root run or one call. On a running
  Subworkflow card, E/Enter opens it (elsewhere E still shows errors); inside,
  the title is the breadcrumb and Esc goes back one level. Pause and X act on
  the whole run. A calling card, the details pane and the title read "waiting
  for you" when a call below waits.
- **Prompt:** "Greeter asks", "From Fetch report › Greet › Greeter › Ask
  name", Send / Cancel (it read "User Input Needed" with node and branch ids).
- Tests: `tests/test_subworkflow_watch.py`; the pinned Execution keys test now
  includes E/Enter.

## 2026-10-20 — 4c-1: the Subworkflow node in Node Config

Branch `dist/4c-subworkflow-node`, from main `106c437` (#89, #90). Built from
the owner-approved samples (revision 2, 2026-10-19). 4c is split in two:
4c-1 here, 4c-2 (watching a call from the Execution screen, prompts labelled
by call path) next.

- **Tabs:** 1 Inputs, 2 Payloads, 3 Connections, the words other node
  screens use. Inputs: Alias, "Subworkflow: Greeter [sub]" with Change, a
  warning naming the nodes that may ask ("at its node Ask name", nested calls
  included), and a table Input / Type / Required? (yes/no) / Value comes
  from. Payloads: Payload / Type / Goes to, and "The next node receives: …".
- **Row editors:** an input's value comes from a Typed value, The incoming
  payload, a Vault key or Its default (not offered for a required input
  without one); a typed value is checked against the input's type. A
  payload goes to the Next node, the Vault or Both.
- **Picker:** search, a scrolling list, "12 subworkflows" / "1 of 12", and a
  preview (inputs, payloads, may ask). Changing the subworkflow keeps only
  the mappings the new one still has.
- **Map:** the card reads "Greet (Greeter [sub])", the gap marker uses the
  existing `➥ (n)` for payloads sent to the Vault, and the details pane
  lists Runs, Inputs and Payloads. The node is now in the selector.
- **Owner decision (2026-10-20):** a result's blank Vault key is its own
  name, not `<alias>.<result>` (backend, docs and authoring guide updated).
- `backend.contracts.call_contract` / `asking_nodes` describe a child as a
  caller sees it; `frontend/subworkflow_info.py` caches that per saved file.
- Review (#91, Codex): an unchanged typed object or list keeps its stored
  value (it was saved back as text); the picker fills the screen with its
  list taking the space left, so Choose/Cancel show at 80×24; a prompt
  added or removed in a nested subworkflow updates "may ask" (the cache
  checks every file it read).
- Tests: `tests/test_subworkflow_screens.py`. Full suite: 1889 passed.

## 2026-10-20 — Keymap phase 3: Editor and Execution

Branch `codex/keymap-editor-execution`, fresh `origin/main` `106c437` after
#89 and #90 merged. Re-read NOTES; Node Config is reserved for 4c.

- Both screens already used registry bindings. Complete their presentation
  migration: Help reads command descriptions/aliases from the profiles, and
  compact hints use command IDs to obtain their keys. Native Textual handles
  overrides and dispatch; no key, alias, ID, action route or policy changed.
- Preserve the default hint wording. The error-panel prefix reads its V key
  from the Execution profile and follows an override. Help lists inherited
  application commands without duplicate screen-owned keys. Fix the stale
  “S Stop” help entry; the profile says X Stop and S Down. Native punctuation
  and control-key names display as ?, Esc and Backspace.
- W/S or arrows scroll Help; E/Enter still closes it, with Close visible at
  60/100/140 columns. Other Help topic text stays unchanged. No edits to
  `frontend/screens/node_config.py`, Vault log, backend or owner workflows.
- Failing-first: eight initial failures and one passing key characterization;
  punctuation normalization and the default Escape hint each failed in added
  checks before correction. Twelve new tests plus the updated existing Help
  regression pass; full suite **1,884 passed in 277.58s**. Compile, docs and
  whitespace checks pass. Tests set `AOTN_DATA_DIR` before backend imports.
  [Before/after Help and hint text, mounted samples](audits/keymap_phase3_2026_10_20/README.md).
  Native terminal manual checks were not performed.
- Open one PR and stop for owner review. Remaining profile presentation and
  4c proceed separately; this PR does not authorize merging.

## 2026-10-20 — Modals fill the terminal

Branch `dist/modal-full-size`, from main `106c437`. Owner: modals left an
unused strip on the right and at the bottom. They sit at the top left and
were sized 80–90%.

- Node Config, the node selector, the large viewers (`fill-modal`) and Help
  now fill the terminal (100%). Small dialogs stay sized to their content but
  may grow to the whole terminal; so may the keep/recover pickers and the
  deletion confirm.
- The modal CSS comment said "centered"; it now says top left.
- Review (#93, Codex, findings that were already on main): Options and a full
  File window now fill the terminal with their tabs above Save/Cancel and
  Open/Close; any other dialog taller than the terminal scrolls (W/S reach
  its buttons); the keep/recover list fit counts the button row's margin.
- Tests: `tests/test_modal_size.py` (each failed before its change). Full
  suite: 1881 passed.

## 2026-10-19 — EX: Execution Screen Overhaul

Branch `dist/ex-execution-screen`, from main `b5426ab` (#88). Owner-approved
samples, three revisions. Before: 1848 passed.

- **Map:** the run is drawn with the editor's own row code (an editor screen
  that is never shown builds the rows), so it matches the editor exactly.
  Cards in run mode show the status on their second line (`✓ done 0.42s`,
  `▶ running`, `⏸ waiting for you`, `✗ Unexpected failure`, `skipped:
  upstream failed`, `· 2 tries`, `· 3 runs`). Rows update in place, so the
  highlight and scroll survive every run event. Only the path from Start is
  shown, as in the editor.
- **Details:** the highlighted node's name, step and branch, status and tries,
  what it received from the previous node, sent to the next node and saved
  to the Vault; for a Subworkflow node, the call and where it is.
- **Follow:** the highlight follows the node that needs you, then a waiting
  one, then the running one, switching paths to show an error or prompt.
  W/S stops following, F follows again. A/D switch the path at the nearest
  branch above the highlight. Stop moves from S to X.
- **Error panel:** on this screen a recovery choice opens in the right pane
  (Retry, Skip, Stop branch, Go to node, Stop run, Details) instead of the
  pop-up; V hides and shows it, and the title then reads "⚠ 1 error waiting
  · v to choose". Other screens keep the pop-up.
- **Vault log (M):** `MemoryBank.writes()` records every Vault write with the
  writing node, branch and visit (the supervisor sets a context variable each
  step; no node changes). Columns Time, Key, Type (coloured), Value
  (shortened), Source (`S2B1 Keep`: step from Start, branch number, node; the
  main path has no branch number). E opens the whole entry; A/D move between
  writes of the same key; / filters.
- Narrow terminals (under 80 columns) stack the details under the map.
- Backlog: the Editor Validation Panel (V opens it; Run validation button;
  Go to node), as the owner asked.
- After: 1858 passed (10 new tests in `test_execution_screen.py`; two older
  tests now build a connected chain, since unconnected nodes are not on the
  map). The old memory viewer stays in the code for its tests and is no
  longer opened from this screen.
- Review fixes (six findings on #89): Vault cells are literal text; the narrow
  layout keeps the error panel's buttons on screen (the details pane scrolls);
  Go to node takes one route from Start, so loops can't overwrite it; F shows
  the followed node's path; the live path selector and its Saved paths row
  keep separate highlights; Stop run clears every waiting choice. Six new
  tests, each failing before its fix: 1864 passed.

## 2026-10-19 — Deletion picker review follow-up

Branch `codex/deletion-picker-polish`, from fresh `origin/main` `b5426ab`
after #88 merged. Re-read the EX ownership and #89 entries in NOTES.

- Keep/recover lists fit their rows. Hints and buttons follow immediately;
  long lists still scroll within the screen. Wrapped labels refit on resize.
- Use “Deletes 6 nodes. Shared nodes stay. Z brings them back.” and shorten
  nearby deletion/recovery messages. Editor edits are strings only: no map,
  profile, Execution, Vault log, backend or recovery-screen changes.
- Reformat `test_editor_delete_groups.py` and `test_editor_delete_group_ui.py`
  with normal spacing, multiline definitions and separate statements. Original
  ASTs match after excluding the added tests; no original cases/assertions
  were dropped. No semicolon-joined statements or one-line definitions remain.
- Eight new checks failed before the fixes. Focused deletion suites:
  **63 passed**. Full suite: **1856 passed in 265.73s (0:04:25)**. Compile, docs and
  whitespace checks pass. Tests set `AOTN_DATA_DIR` before backend imports.
  [Rendered samples and wording changes](audits/deletion_picker_polish_2026_10_19/README.md)
  cover 60/100/140 columns with production CSS, short lists, wrapped rows,
  resize and the existing 64-path keyboard/scroll checks. Native terminal
  manual checks were not performed.
- Open this PR and stop. #89 review is next, findings only. Keymap phase 3
  may cover Node Config, Node Selector, Workflow Library and Help; Editor
  and Execution profiles wait until #89 merges. Owner merges.

## 2026-10-19 — Deletion review phase 2

Branch `codex/deletion-phase2`, from freshly fetched `origin/main` `a31d721`
in `/home/makin/src/nw-docs`. Owner approved #86; #85/#87 are merged.
This PR awaits owner review; no merge or keymap phase 3 work in this change.

- First deletion of Branch/Conditional asks for exactly one kept path and
  archives the owner plus exclusive dropped paths in one blocking group stub.
  Resolver deletion keeps No error; shared live handlers/tails survive.
  Ownership planning reuses `stub_removal_plan` and `nodes_only_reached_from`;
  disconnected outside parents, cycles, terminals and orphan Merges are covered.
- Merge deletion keeps and resets every connected Beacon, including Beacons
  with other Merge targets. Beacon deletion ends its branch before and after
  Save; final removal does not bypass into Merge. Warning levels are unchanged.
- Group Z restores nodes, connections and related settings after save/reload.
  Conflicts are shown before partial restore; unresolved changes remain saved
  and retries recognize previously restored nodes. Final removal and different-
  type replacement confirm permanent loss and use only the stored continuation.
- Count reductions require exactly N old paths, remap their names/seeds/edges/
  Merge keys and save removed paths under the live Branch. Count increases
  offer Recover / Leave empty / Cancel, with an optional zero-to-slots picker
  when needed. Unchosen paths remain saved; a partially recovered head is not
  offered twice. No expiry is implemented. Saved paths and unresolved repairs
  have distinct rows, separate from live path selection and insertion targets.
- An editor-owned Branch config subclass defers count saves; cancellation
  preserves the draft and successful save-and-stay reopens a clean baseline
  with the same tab/focus. `node_config.py` is unchanged. The editor header
  adds literal ` [sub]` only for callable workflows; markup previously hid
  `[IDLE]`, which now displays. No Execution screen or backend edits.
- Failing tests first, then **1848 passed in 265.69s (0:04:25)**; **55 new tests** cover
  graph/recovery and mounted form/picker behavior. Legacy regression cases
  remain. Compile and docs link/archive checks and `git diff --check` pass.
  Tests set `AOTN_DATA_DIR` before backend imports, keeping owner settings safe.
  [Production CSS captures and wording comparison](audits/deletion_phase2_2026_10_19/README.md)
  include 60/100/140-column SVG/text and header before/after text. Native
  terminal manual checks were not performed.

## 2026-10-19 — Step 4b: Child Runs (Backend and CLI)

Branch `dist/step4b-child-runs`, from main `1addbf9`. Design C11–C20, C22.
Before: 1729 passed.

- **`subworkflow_node`** (`backend/nodes/flow/`): calls a saved subworkflow by
  id and waits. Inputs from a configured value (parsed by the child's row
  type), the incoming payload or a Vault key; results routed downstream, to
  the Vault (`<alias>.<result>` by default) or both; one `default` output.
  Hidden in the selector until 4c gives it a picker.
- **`backend/subworkflow_calls.py`**: each call builds its own bus, map,
  memory and master state and shares the factory, settings, secrets and the
  run-history writer (C18). A `CallTree` per root run enforces
  `max_subworkflow_depth` (4) and `max_live_subworkflow_runs` (64), failing
  at once (`depth_limit`, `capacity_limit`); routes prompts and answers
  between the root's client and any child, tagged with an invocation id and a
  call path (C19); and spreads pause, including a child's breakpoint (C20).
- **Cancellation:** stopping the root or terminating a branch cancels the
  calling task; the call stops its child and waits until it has stopped.
- **Files (C13):** inside the child's finalization, returned run-owned files
  are released by the child and adopted by the caller, so they outlive the
  child and are deleted with the caller. A file passed in stays the caller's.
- **Records (C22):** child history records carry `root_run_id`,
  `parent_run_id`, `invocation_id`, the call-site node, its alias, the
  parent branch and the call number.
- **Validator:** `subworkflow_not_found`, `subworkflow_not_callable`,
  `subworkflow_recursion`, `subworkflow_input_unknown`,
  `subworkflow_input_missing` (errors), `subworkflow_input_unmapped`
  (warning). A shared helper called by two children is fine.
- **Benchmark** `benchmarks/bench_subworkflow_calls.py`: 200 waiting children
  at once in 0.73 s and 9 MB; busy 60-node children about 10 ms and 0.4 MB
  each, linear; every stack and subscription released; nesting about 0.5 ms
  per level; 0.55 ms per short call with 2,000 saved history records. The
  live-run default is set to 64 from these numbers.
- Tests found that `configuration_manager` and `run_history` bind their
  folders at import, so a test that changes Settings must patch them there;
  the new tests do. Not done here: the TUI (4c), the EX screen, prompt
  queueing in the TUI, fire-and-forget.
- After: 1752 passed (22 new tests in `test_subworkflow_calls.py`).
- **Review of 974af31** (seven findings, each reproduced failing first):
  the call waits on one shielded completion task, so cancellation stops the
  child before its tasks are cancelled and a second Stop can't cut its
  cleanup short; pause holds a child waiting for input and a root
  breakpoint pauses the children; the validator walks the whole reachable
  call graph for loops (Root → A → B → A), matches names exactly as a run
  does, parses configured values by type (`subworkflow_input_invalid`) and
  checks result routes (`subworkflow_result_unknown`); child records add
  `parent_visit` and `parent_attempt`. After: 1762 passed.

## 2026-10-19 — Deletion owner answers and recovery-window samples

Branch `codex/deletion-owner-answers`, fresh from `origin/main` at `1addbf9`,
in `/home/makin/src/nw-docs` (clean at start). The owner checkout remains at
`105623d` on `docs/newcomer-guide` with its unrelated edits preserved.

- Recorded the five owner answers from the shared NOTES: all Beacons previously
  connected to a deleted Merge stay and reset to unconnected; deleting a Beacon
  ends its branch; conflicted undo previews what cannot return, then restores
  what fits; reduced paths stay saved under the live Branch; warning levels stay.
- Checked `validator.py`: `merge_beacon_unconnected` is a warning and does not
  block running. Keep that level; unreachable warnings and blocking tombstone
  errors also keep their levels.
- Added compact samples for the recover prompt and optional which-paths picker.
  Recover relinks to new ports; zero choices leave them empty. Unchosen paths
  remain saved. No expiry until the owner decides the retention window.
- Phase 2 waits for owner approval of this update and #85 merging, then uses
  fresh main and the agreed Editor/adapter/error-mux/keep-picker files. Include
  the editor's ` [sub]` header; no `node_config.py` edits. Open each PR and stop.
- Findings-only #85 re-review at `afe98cd` in `/home/makin/src/nw-review85`:
  the five original cases pass; **53 focused tests passed in 13.24s** and the
  full suite **1759 passed in 230.79s**. One additional mounted-screen probe
  fails: confirming a typed file-reference default unchanged saves JSON text,
  which file input resolution mistakes for a path. No source/test edits or
  review comments posted. Temporary probe uses an isolated temporary file.
- This PR changes documentation only; behavior regressions must fail first in
  phase 2. Verification: **1729 passed in 228.35s**; docs link/archive checks and
  `git diff --check` pass. Prior log entries and archive bodies are retained.
  Samples are plain text; no live-terminal or new rendered-UI claim.

## 2026-10-18 — Step 4a-2: Subworkflow Screens

Branch `dist/step4a2-screens`, from main `1addbf9`. Owner-approved samples
(three wording passes, then File window tabs). Before: 1729 passed.

- **File window:** Workflows and Subworkflows tabs (1/2). The key line keeps
  the common keys and `?` opens the grouped key list; Open replaces Load.
  **C** on tab 1 copies a workflow to Subworkflows with the same name; a
  repeat copy is numbered "(2)" with a warning toast; the original is not
  touched; a single End becomes the Return End. **N** on tab 2 makes a
  subworkflow. Names are unique per tab (`workflow_names`, `list_workflows`
  now reports `callable`); `aotn run "<name> [sub]"` picks the copy.
- **Start:** an Inputs tab of one-line rows (the old greeting shows as one
  row; saving it untouched changes nothing), an input editor (name, type,
  default with P for the Stash, required, send to, Vault key, description;
  names must be unique and defaults must parse by type), and "Next node
  gets: ...". In a subworkflow, a read-only Results tab mirrors the Return End.
- **End (subworkflows only):** a Results tab with "Send results back" and
  its result rows. Standard workflows never show these controls.
- **Payloads (subworkflows only):** "Send back to calling workflow" under a
  Vault payload adds or removes that key on the Return End when saved.
- Node Config titles show `[sub]` in a subworkflow. A new keymap profile,
  `contract_row_editor`, covers the input/result editor.
- Not in this PR: `[sub]` in the editor header (Codex owns `editor.py`),
  "Send back" for multi-output Vault nodes (`membank_outputs`), and the
  plain-language pass over the rest of the UI.
- After: 1754 passed (25 new tests in `test_subworkflow_library.py` and
  `test_contract_screens.py`; the old Start Payloads test now checks the
  Inputs row instead).
- **Review of f5ca052** (five findings, each reproduced failing first):
  renaming a sent-back Vault key moves its result instead of leaving a stale
  one; "Send back" refuses a result name the Return End already uses;
  removing every Start input saves `no_inputs: true` (plain `rows: []` still
  means the old greeting, as saved files expect); an object or list default
  shows as JSON, so confirming it unchanged keeps its type; `aotn build`
  applies the full name rule (`name_invalid` for a name ending in `[sub]`).
  After: 1759 passed.
- **Review of afe98cd:** a file default shows as its path, and an input row
  confirmed without changes keeps its stored value, so a typed file
  reference no longer saves back as JSON text. After: 1760 passed.

## 2026-10-18 — Docs C integrated with #81, #82 and #84

Main merged into `codex/docs-c` (owner asked for the merge). `CURRENT_STATE.md`
was rewritten from docs C's bounded version to today's state; the backlog
keymap row keeps docs C's wording; the audit allows
`DELETION_REVIEW_PROPOSAL.md` as a second temporary doc. Every 2026-10-18
log entry is kept.

## 2026-10-18 — Docs C: Bounded History and Remaining Audit Cleanup

Branch `codex/docs-c`, fresh from `origin/main` at `90182f0`. Docs only;
#81 and #82 remain separate PRs. The owner/reviewer merges.

- Checked owner-decision destinations before transferring 96 older entries
  (July 11–June 9) whole to `archive/SESSION_LOG_HISTORY.md`. Retained all
  86 October entries, including every October 18 entry. Current window:
  October 4–18; earliest existing entry October 6. Existing archive bodies
  remain intact; no history was deduplicated or reduced to milestones.
- Added the extraction map and migration receipt. UI reference makes manual
  validation-badge semantics explicit; backlog retains the older amber-type
  fallback choice without claiming it is implemented. Contributing explains
  how to roll the window forward after extracting unique owner intent.
- Remaining-finding review is recorded in the audit verification matrix:
  corrected Stash's Ctrl+P/palette and implementation claims, the newcomer
  guide's recorded-only inputs, the stale Step 4 gate and regeneration promise,
  and the catalog's old inline-subworkflow direction. Current State is bounded
  to a dated snapshot; historical status remains in this log and the archive.
- README links directly to contracts; Workflow Authoring distinguishes built
  CLI contracts from future child calls and clarifies missing versus explicit
  empty values. Both documented JSON specs build in isolated storage; typed
  `who=Kim`, `times=3` returns `greeted = Kim`.
- UI Quick Reference adds the primary Enter-action button/Close-or-Cancel
  convention and Stash deduplication. No visible application text/layout changed.
- The docs checker now requires the exact 17 core document names and allows
  only the temporary Step 4 proposal as an extra. The former count check
  failed first on 18; whole-history transfer is now checked against Git too.
- Verification: full suite **1708 passed in 223.15s**; **392 relative
  links/anchors**, 33 whole archive bodies and 96 transferred-entry checks
  pass; `git diff --check` passes.
  #81's picker flake did not occur. #82's standards error-port bullet,
  HTTP/JSON Path catalog rows and owner-findings backlog text are untouched.
- Original S2/S3 CSVs remain unavailable. No native FO7/live terminal, clean
  install or external-link claim was added. Restricted keymap phase 3 follows
  as its own PR; Editor/Node Config/selector/library/Help follow after 4a-2.

## 2026-10-18 — Editor Hotfix Re-review and Proposal Evidence

Branch `codex/deletion-proposal`; docs-only follow-up to #84. Re-reviewed
#82 at `531e4c1` after its three review fixes, without application changes.

- The original shared-Resolver, shared recovery-tail and missing source-port
  reproductions pass. Nearby cases pass for soft-deleted/materialized peer
  guards, a guard restored before deletion, tails shared between a Resolver
  route and the guarded node's wired error path, and protection when No error
  also reaches the tail. Stale original and newly gained input edges lose both
  halves without relying on Editor's prior pruning. No remaining finding in
  these cases; this is not a claim about untested deletion cases.
- Verification on #82: **92 focused tests passed in 5.47s** and the full suite
  **1728 passed in 212.11s**. Updated the proposal's current-behavior evidence
  and regression requirements; phase 2 still requires owner approval and #82's
  merge. No source/test changes or review comments posted.
- Docs: **352 relative links/anchors**, **33 archive bodies**, existing October
  18 entries retained, and `git diff --check` pass. The historical active-doc
  count still needs the temporary proposal allowance when #83 integrates.

## 2026-10-18 — Editor Deletion Review: Phase 1 Proposal

Branch `codex/deletion-proposal`, fresh from main `90182f0`. Docs only;
#81/#82/#83 remain open. The owner/reviewer merges.

- Read the evening ownership split, #82's approved backlog direction and
  all three initial follow-up comments, then the later review-fixes comment.
  Rechecked current behavior at #82 head `531e4c1`; hotfix behavior is not
  claimed to be merged on main.
- Added `DELETION_REVIEW_PROPOSAL.md`: every requested structural deletion,
  two parents, stub removal/replacement and undo before/after save and reload.
  Defines grouped recovery, one exact-cardinality picker, protection for shared
  nodes, Merge cleanup, versioned stub data and later in-memory session history.
- Included plain-text samples for pickers, destructive confirmations and
  conflicts. Owner choices: Merge/Beacon effects, group restore on drift,
  persistent undo for count reduction, and actual validator warning severity.
- Code/probe checks found Beacon removal differs before/after materialization:
  unsaved removes Merge selections and does not bypass; saved can bypass and
  leave selections. Proposal requires one approved policy. #82 advanced during
  drafting: `531e4c1` fixes the shared-handler/tail/restore review gaps; those
  are retained as regression requirements, not described as current defects.
  Twenty current hotfix tests plus three independent reproductions pass
  (**23 passed in 3.51s**).
- Count-reduction picker belongs in Editor's config-save path, with no Node
  Config edits. Save-and-stay takes its own snapshot after a synchronous
  callback; cancellation needs a real completion contract, not a false save.
- Verification: full main suite **1708 passed in 217.06s**; **352 relative
  links/anchors** and **33 whole archive bodies** pass. The new review is temporary; #83's active-doc allowlist
  needs its name during integration (the old 17-count assertion was already
  failing on the subworkflows proposal). No runtime/test/helper/workflow edits;
  no live/native terminal verification. Phase 2 waits for owner review and
  #82's merge. Existing log entries are retained whole.

## 2026-10-18 — Editor fixes: insert with two parents, error paths, colours

Branch `fix/insert-fan-in-error-path`, from `main` at `90182f0`. Owner bug
report on the "Test Bench - C1/C2 checks" workflow. Before: 1708 passed.
Tests are in `test_insert_fan_in_error_path.py`.

- **Insert lost the nodes below it** when the next node had a second parent
  (Pause is fed by Dice and Save note): its input looked occupied, so the
  new node was never connected to it. The inserted node now takes over the
  port it was cut from.
- **No error path by default.** HTTP Request and JSON Path no longer list
  `error` as an output; their failures are coded `NodeError`s that go to
  the default handler until the node's Errors tab catches them. The
  `error` payload is now the engine's error record (code, message,
  details), the same as every other node.
- **Colours:** failure paths (a node's error path, an Error Mux's
  recovery branches) no longer re-colour the node's one normal path,
  No error included; the failure paths keep their own colours.
- **Deleting a node with an error handler** (owner follow-up): it asks
  first, then removes the inline Error Mux and every node only its error
  branches reach (its wired `error` path, the mux's recovery branches).
  The node continues on the mux's No error path. Cancel changes nothing;
  undo restores only the node. Nodes without a handler delete as before.
- **Error Resolver missing from the editor** (owner, C1/C2): undoing a
  saved delete re-added the node's old input even when that output now led to
  a new Resolver, so HTTP's output had two targets and the editor (and the
  run) followed only the first. Restore now keeps the wiring the tombstone
  gained, never gives an output a second target, and lets two parents share
  an ordinary input again. The validator warns (`ignored_fan_out`) when a
  Resolver's No error path can never run because its node also leads
  elsewhere; that is the state the owner's saved C1/C2 file is in.
- **Removing a deleted node's stub** (owner, "user test"): removing an
  Error Resolver's stub joined its parent to every path after it, so a
  successful run went down the old error branch. The gap is now bridged to
  one target only. An Error Resolver keeps its No error path and, after a
  confirm, deletes the nodes only its error branches reach. Other paths of
  a multi-path node (Conditional's second path) are left loose for the
  deletion review. Branch nodes keep their keep-one picker.
- **Review of 47e7580** (three more cases, each reproduced failing first):
  deleting one of two nodes that share a Resolver keeps the Resolver and
  its branches for the other; error routes that share a tail are walked
  together, so the tail goes too; undo drops an input from a path that no
  longer exists (a Branch reduced from three paths to two) instead of
  keeping half an edge.
- Logged for later in the backlog: reducing a Branch node's path count,
  and a deletion review with the owner. After: 1728 passed (20 new tests).

## 2026-10-18 — Deterministic File-Picker Test Teardown

Branch `codex/file-picker-teardown`, fresh from `origin/main` at `90182f0`
(#78 and #80 merged). Test-only fix; no frontend/backend files changed.

- Reproduced `NoMatches: HeaderTitle` before fixing the test by delaying
  Header mounting 250 ms. The new regression failed with the same traceback:
  the old 100 ms pause ends while the imported workflow's editor is mounting.
- Cause: `load_workflow` records success before `show_editor_screen` finishes
  its asynchronous switch. `pilot.pause(delay)` drains the current screen
  before sleeping, so it can miss the replacement screen created during sleep.
- The test now observes picker completion through a test-only App subclass,
  awaits Textual's public screen-switch completion, then drains the new screen.
  It retains production picker entry points, threaded OS-picker stubs, the
  stylesheet and every original assertion. It additionally checks that import
  reaches a new mounted editor. No increased sleep in the fix; the regression's
  delay models slow mounting only.
- Verification: unmodified full suite **1708 passed** in 216.99s; regression
  failed first; focused picker tests **3 passed**, with **ten consecutive runs**
  also passing (30 tests). Final full suite **1709 passed** in 216.57s.
  Changed-test compilation and `git diff --check` pass.
- Step 4a-2 frontend files are untouched. Docs PR C and the restricted keymap
  phase 3 remain separate follow-up PRs; the owner/reviewer merges.

## 2026-10-18 — Step 4a-1: Contracts (Backend and CLI)

Branch `dist/step4a1-contracts`, from `main` at `15742b0` (#79). Before:
1605 passed (#77). After: 1647 passed (42 new tests in `test_contracts.py`);
the known file-picker flake failed once in one full run and passes alone.

- `backend/contracts.py` (pure): Start rows (the inputs) and Return End
  rows (the results), typing (`string`, `number`, `bool`, `var`, `file`),
  the fill order, missing-versus-empty, one downstream row as itself or
  several as an object, and a revision hash of the definition.
- **Start** routes its rows downstream and/or to the Vault; with no rows
  it keeps its greeting exactly as before (no migration needed). Its
  output type follows the routed rows.
- **End** gains `return_end` and `results`; a Return End collects its
  results and publishes them once (`result_missing`, `result_invalid`,
  `result_conflict`). A callable workflow whose Return End never ran logs
  `result_missing` at finish.
- **Engine:** inputs resolve before the run resets anything, so a run
  with missing or invalid inputs never starts (`ContractInputError`);
  `RunResult` gains `values` and `revision`; run history records the
  revision. `WorkflowMap` carries `callable` (saved only when true).
- **Validator:** `contract_row_invalid`, `input_required_no_value`,
  `return_end_not_callable`, `multiple_return_ends`, `return_end_unmerged`.
- **CLI:** `--input` typed by row, `--inputs-file`, exit code 5 for bad
  inputs, results printed as `name = value`. `aotn build` accepts
  `"callable": true`. The TUI shows why a run can't start.
- Found by the CLI smoke test: a required text row stored blank started
  with `""`; a stored blank now means "no default" for every type (C6).
- **Review fixes (owner's review of #80):** Start's Vault rows are declared
  writers in `vault_declarations.standard_vault_writes`, so readers pass
  preflight; text parsing (`parse_text`, for `--input` and editor
  defaults) is separate from typed checks (`check`, for inputs files,
  callers and results), so a `var` string like "false" or "null" is never
  re-parsed; Return End results are enforced only in callable workflows
  (the engine offers `publish_result` only there). One test each.
- Frontend touched only for the five issue labels and the TUI's
  can't-start message (`error_details.py`, `app.py`); merged with #78
  (keymap phase 2) without conflicts in either file.

## 2026-10-18 — Keymap Phase 2: Shared Policies and Native Adapters

Branch `codex/keymap-policies`, fresh from `origin/main` at `4cb246e`.
Merged reviewed #77 on the owner's explicit instruction, integrating #76's
approved Step 4 docs and keeping both sets of log/status entries first.

- `Command.policies` is a nonempty frozenset of allowed NAV/TEXT/SELECT states.
  Key-specific exceptions use separate actions; conflicting policy sets for
  one action signature are rejected. NAV printable commands compile as priority
  bindings. Confirm's existing IDs and visible hint remain unchanged.
- App and the high-traffic screens now compile their native bindings from the
  registry: Editor, Execution, Node Config (plain P insert), selector, Stash,
  Settings, Workflow Library/prompts and list pickers. Shared command-mode
  Help/recovery/confirmation/input modals receive mechanical profile integration;
  their wording/layout stays unchanged. Memory/Output/File viewers are deferred.
- Retired duplicate typing action-name lists and the raw Select dispatcher.
  Input/TextArea edit transitions and NAV caret aliases are native widget
  commands; focus rescue and standalone fallbacks use effective registered
  roles/keys. Ctrl+Q reverts before leaving; root registered commands yield
  to modals. Normal editing/caret/clipboard behavior remains Textual-owned.
- `widgets/select_keymap.py` isolates the private Textual 8.2 compatibility:
  focused Select and overlay share one native profile, with pure availability.
  Both pushed-screen and embedded-screen focus paths are tested. No second
  dispatcher or screen-level raw Select key list remains.
- Failing-first receipts: three regressions failed before fixes in
  `tests/test_keymap_regressions.py`: reading Node Config availability closed
  a Select; Execution's old S route survived removing its bindings; Settings'
  bubbled digit handler bypassed rebinding. All now pass through native routes.
- New actual-keypress tests cover Input and multiline save-and-stay, retained
  editor ownership, literal typing/digits/P, modal scope, Select remapping,
  screen-navigation and caret remapping, and native compiled IDs/actions.
  Two old direct `_on_key` tests now press Escape through the pilot; behavior
  assertions are retained. Ctrl+Q's static test checks its registered wrapper
  and Back fallback. No backend/CLI files or workflow data changed.
- Contributing documents command addition and custom-section integration for
  4a-2. Phase 3 owns generated Help/hints/tab labels; reference-table/source
  checks, Settings rebinding and read-only viewer migration remain deferred.
- Final verification: **1666 passed** in 212.52s, compilation and whitespace
  checks pass. Actual-keypress cases include Input and TextArea commits,
  dropdown/screen/caret rebinding, modes, focus and cancellation. An intermediate
  full run hit the known `HeaderTitle` file-picker teardown flake; its isolated
  rerun passed. That separate fix is not folded into this PR. The old docs
  audit finds all 342 links/anchors and 33 archive bodies intact, but reports
  18 active docs versus its historical 17 expectation (already true on main
  after #76 added the proposal). No native terminal verification was performed.

## 2026-10-18 — Step 4 Proposal Revision 4: Follow-Up Decisions

Branch `docs/step4-r4`, docs only. Owner decisions in chat, 2026-10-18:

- Results are defined on the **Return End** (opt-in), mirrored read-only on
  Start; no auto-results from output nodes (C1, C3).
- Result routing per result (downstream / Vault / both) in the
  Subworkflow node's Payloads tab, with indented result lines in the
  editor, instead of an auto-added handler node (C11).
- **Return to caller** toggle on Vault outputs (C26); **callable**
  workflows with Make callable as the primary path (C27); a `folder`
  type (C28); exclusive leases for shared read-write entries that fail
  fast (C24).
- Nesting yes, recursion not intended (C17); a concurrency benchmark in
  4b sets the live-run default (C16). Correction: boundary types use
  `var`, not `object`/`list` (C7).
- Later: run the validator on Make callable with suggestions (for
  example, fold User Input nodes into Start's inputs).

## 2026-10-18 — Keymap Phase 1: Registry and Confirm Profile

Branch `codex/keymap-foundation`, fresh from `origin/main` at `714f190`,
after Stash S3 #75 merged. Owner adopted three keymap PRs, one at a time;
this implements only the foundation. The Step 4 proposal proceeds separately.

- `frontend/keymap.py`: immutable typed commands/profiles, stable semantic IDs,
  class-time native Binding compilation and compact hint generation.
  `keymap_runtime.py`: pure NAV/TEXT/Select, active-screen and application/modal
  availability; no second dispatcher. Availability reads never change focus,
  close overlays or commit text.
- Confirm is the first complete profile: registry supplies all its commands,
  navigation aliases and unchanged `Y confirm  N / Esc cancel` hint. Existing
  action methods, buttons and focus mechanics remain. No visible text/layout
  changes. All other screens/root guards and shared adapters await phase 2.
- Characterized Confirm's nine actual key routes before migration. Added
  registry/native-map contracts and mounted tests for nonediting text focus,
  Input/TextArea typing and retained edit ownership, expanded Select navigation,
  side-effect-free availability reads, and modal/root scope. Test hosts suppress
  Textual's default root Quit when isolating modal Ctrl+Q; this does not claim
  production root bindings have migrated.
- Post-S3 inventory corrects the research: insertion uses plain **P**, priority
  and off while typing. **Ctrl+P and the command palette are untouched**;
  there is no palette migration hazard. Inventory, three-phase scope and
  deferrals are in Project Backlog; Contributing explains adding a command.
- Verification: focused **57 passed**; full suite **1605 passed** in 196.94s;
  compilation and `git diff --check` pass. Docs check: 336 relative links/anchors,
  33 whole archive bodies, 17 active docs. No native terminal verification.

## 2026-10-18 — Step 4 Design Proposal: Subworkflows and Contracts

Branch `docs/step4-subworkflows`, from `main` at `714f190` (#75). Docs
only. The owner agreed to a design-first Step 4 with Stash S5 designed in,
and to the keymap work running in parallel (Codex, frontend).

- New [SUBWORKFLOWS_PROPOSAL.md](SUBWORKFLOWS_PROPOSAL.md): decisions
  C1–C13 (contracts on Start/End, inputs via the Vault, a fresh backend
  stack per child run, workflow-id references, call-and-wait first, one
  input fill order, recursion limits, stop cascade, returned-file
  hand-over, inherited prompts, per-machine Stash bindings), four PRs
  (4a–4d) and five owner questions.
- Checked against the code: `MasterState` holds one run, so a child needs
  its own stack; `RunContext.inputs` and `parent_run_id` exist but are
  unused; `RunResult.outputs` is the output log, not named values.
- **Revision 2 (review of #76):** one contract on Start with a single
  Return End after merges; results only after the child finishes; one
  `default` continuation with results in parent Vault keys; simultaneous
  calls with fail-fast depth and live-run limits (no waiting queue);
  file hand-over inside child finalization (`_record_run` deletes run
  files before `wait()` returns); a run-aware prompt bridge with
  invocation ids (the TUI has no input provider to inherit); tree
  cancellation with acknowledgement; blocking contract-compatibility
  errors and revision recording; missing-versus-empty and boundary types;
  shared read-only services per child stack (`RunHistory` reads all
  history on construction). Seven owner questions.
- **Revision 3 (owner answers, 2026-10-18):** approved. Start overhaul:
  rows become typed, routed outputs and are the contract's inputs (C1, C2);
  prompt-free children are the norm and prompting is visible (C25); a new
  Execution screen overhaul stage (EX) comes before the subworkflow UI;
  limits are Settings; one Return End now, a Return Merge family later;
  shared memory as C24. Step 4 in DISTRIBUTED_BUILD_PLAN now summarises the
  design and order; the backlog records the Return Merge family and
  merge-early guidance.

## 2026-10-18 — Stash S3: Insert an Entry Into a Node Config Field

Branch `dist/stash-s3`, from `main` at `e4fd25d` (#74). Before: 1539
passed. After: 1548 passed (9 new tests in `test_stash_insert.py`).

- **Owner decisions (2026-10-18):** the insert key is `P` (Ctrl+P clashes
  with the command palette and VS Code's terminal); a text field takes only
  `[text]` entries, not a file path (proposal question 1: no, for now).
- `P`, or the new **Insert from Stash** button, on a highlighted field
  opens the Stash on Entries in insert mode: titled "insert into <field>",
  only entries the field accepts, **E/Enter** or **Insert** fills the field.
  A field that takes nothing gets a toast. `P` is off while typing.
- On a port's Source row, the insert fills the path field that row hides
  and switches the source to Configured (proposal §9 note 1); the toast
  says so. `field_types.stash_insert_target()` is the shared rule, read
  from the schema's `visible_when`.
- The button is last in node config's button column, so W/S from the
  fields still reaches Save first. The hint line and Help list `p stash`.
- Found: Help says A/D switches node-config tabs, but A/D moves within a
  row there; left for the proposed keymap-table PR, which keeps Help and
  bindings in sync.

## 2026-10-17 — Stash: Duplicates Are Not Stashed Twice

Branch `dist/stash-duplicates` (PR #74), from `main` at `9032151`, then merged
with `main` after #73. After: 1539 passed (7 new tests).

- **Owner decision (2026-10-17):** the same file is the same reference, so
  adding it again creates no entry; a toast says "Duplicate found" (the
  bottom-right notification). Same for identical text (ignoring
  surrounding whitespace) and for imports (`theirs: duplicate of 'mine'`).
- `StashDuplicate` (a `StashError`) carries the existing entry;
  `add_paste` collects them in `PasteResult.duplicates`, and
  `duplicates_message()` writes the notice for the screen and the CLI
  (`aotn stash add` exits 0 on a duplicate).
- A *different* file with a name already used is named after its folder,
  `march (archive)`, instead of `march 2`. A name you choose must still be
  free.

## 2026-10-17 — Confirm and Close Buttons in Every Window

Branch `dist/modal-buttons`, from `main` at `9032151` (docs PR B, #72).
Before: 1518 passed. After: 1532 passed (14 new tests in
`test_modal_buttons.py`).

- **Owner request (2026-10-17):** every window offers its main action and
  a way out as buttons, for mouse use. Added: Choose/Cancel (branch
  selector), Go to/Cancel (merge beacon), Keep/Cancel (keep-branch),
  Add/Back (group picker, which had no buttons), Add/Cancel (node
  selector; Add does what Enter does on the highlighted entry, since a
  click moves focus), Load/Close (workflow library), Confirm/Cancel (the
  name prompt, which had none). Help's button says Close.
- **Found by the new test:** Help's Close was off-screen in a 30-row
  terminal (long help text, no scroll). The text now scrolls inside a
  bounded card.
- Two tests encoded the old buttons and were updated deliberately:
  `test_help_screen_is_contextual_and_focuses_cancel` (label Close) and
  `test_workflow_library_uses_shared_list_navigation` (Load + Close).
- Code comments citing docs that #72 archived now point at
  `docs/archive/` (review note on #72).
- **Review fixes (owner's review of #73):** the node selector's Add acts on
  the list that last had focus, so leaving a group's quick list for the
  main list no longer adds the stale quick-list node; E/Enter on a focused
  Back/Cancel button presses it in the group picker and the three branch
  pickers instead of choosing. One test each.

## 2026-10-17 — Stash S2: The Stash Screen

Branch `dist/stash-s2`, from `main` at `9d5455b` (PR #70). Before: 1509
passed. After: 1518 passed (9 new tests in `test_stash_screen.py`).

- **Owner decisions (2026-10-17, on sample screens):** tab 1 is Paste /
  drop and tab 2 is Entries; the node-config field hotkey (S3) opens the
  Stash on tab 2 (`App.action_stash(initial_tab="entries")`). Types show
  bracketed at a glance (`[file]`, `[text]`, the teal `type_label`). Every
  action has a button for mouse use, including Close. Later, not now: a
  hotkey to copy an entry and convert it to text.
- `frontend/screens/stash.py`: `p` in the editor opens it. Pastes and drops
  are collected only on this screen (a paste is added at once; typed text
  on Enter or Add). After a paste, focus moves to "Just added" so T (keep
  a refused paste as text) and R act on it; E types again. Entries: live
  search (`/`), T cycles all/files/text, R or E renames through the
  workflow name prompt, X deletes after a confirm. Letters typed in a box
  are text, never shortcuts.
- `stash_manager.preview()` / `type_word()` / `name_problem()` are shared
  by the screen and the CLI (`aotn stash list` now shows `[file]`/`[text]`).
- Found while building: a CommandInput or CommandTextArea that isn't
  editing swallows letter keys, so screen shortcuts can't fire while it has
  focus. The screen moves focus to a list instead. Mouse-button audit of the
  other modals (name prompt and group picker have no buttons; selectors
  have only Cancel; Help says Cancel for Close) is the next small PR.
- **Review fixes (owner's review of #71):** 1/2 switch tabs even when a
  text box has focus but isn't typing (priority bindings, off while
  typing); E on the Paste tab always types, R renames; search matches the
  whole value, and only the display is truncated. One test each.

## 2026-10-17 — Docs B: Consolidation and Vision

Branch `docs/b-consolidation-vision`, from `origin/main` at `9d5455b` (#70).
Source map committed first as `23f96ee`; consolidation commit `2cc4f2f`.
Full app suite: **1509 passed in 173.22s**. Runtime/tests/specs/workflows unchanged.

- Rebuilt the missing vision-source map before extraction; added VISION and
  CONTRIBUTING, with newcomer/router links. Restored the short AGENTS rules
  list and clarified separate checkout/worktree ownership (review of #69).
- Folded runtime references into ARCHITECTURE, correcting output/completion
  order, shared transient addressing, resource/chat representations, validation
  scope, direct service/callback boundaries and transport exceptions.
- Consolidated keyboard and interaction rules in UI_QUICK_REFERENCE, including
  64-path width, current execution keys and pending Stash S2 (#71) controls.
- Folded authoring/standardization guidance into NODE_STANDARDS/NODE_HELPER;
  preserved file/window D1–D12 reasons, FO7 protocol, recovery editing decisions,
  and the complete pending branch-inspection/preview proposal in active owners.
- Archived 32 whole documents plus the original architecture, with dated
  supersession notes; repaired relative links and recorded every destination.
  Exactly 17 active top-level docs remain. Session-history bounding is PR C.
- Retained S1's approval/status/plan/log entries. Stash S2 (#71) merged first;
  `main` was merged into this branch at review and both entries kept.
- Fresh verification in [PR B receipts](audits/docs_audit_2026_10_17/PR_B_VERIFICATION.md).
  The reproducible checker passes all relative links/anchors and compares all
  33 archive bodies with the pinned baseline, allowing link-target changes and
  the ledger append. Whitespace is clean. An initial pytest invocation from
  the repository root failed collection imports; the required app-directory
  invocation completed with the 1509 passing result above.
- No clean-install, native FO7, external-link or live geometry claims were added.
  Owner decisions stay explicit; the owner or an explicitly asked reviewer merges.

## 2026-10-17 — Stash S1: Core, Paste Parser, `aotn stash`

Branch `dist/stash-s1` (PR #70), from `main` at `7e3f151` (PR #68), then
merged with `main` at `579be24` (docs PR A, #69). The owner
approved S1 with the S3b CLI and authorised merging #68 first. Before:
1480 passed. After: 1509 passed (29 new tests in `test_stash.py`). The
docs reorganisation runs in parallel (another agent owns `docs/`; this
PR only adds this entry and the plan's progress line).

- **`backend/stash_manager.py`:** entries in `<data dir>/stash/entries.json`
  (`persistence.STASH_DIR`), types `file` (a file reference) and `string`.
  Generated ids that survive renames; names trimmed, not blank, unique
  ignoring case (a default name counts up, a chosen one must be free).
  Versioned export/import (`aotn-stash/1`): import skips entries already
  present, numbers clashing names, and skips files missing on this
  machine. Key-like text is warned about on add and export, never
  stored silently as a secret. An unreadable Stash file is never
  overwritten.
- **`backend/paste_parser.py`:** the §9.7 rule. Splits drops from Windows
  Terminal (quoted Windows paths, kept backslashes, UNC), Linux terminals
  (single quotes, backslash escapes), `file://` URIs and newline lists;
  every candidate goes through `normalize_local_path`. All pieces
  path-like → existing files become entries, missing paths and folders
  are reported, not stored; otherwise the whole paste is one text entry.
  Narrowed from the proposal: a quoted *relative* piece is not treated
  as path-like (nothing to resolve it against).
- **`field_types.accepted_types`:** declared `data_type` wins, else
  `path_hint: file` → `file`, text fields → `string`, everything else
  nothing. A text field doesn't take a file yet (open question 1).
- **`aotn stash list|add|rename|rm|export|import`** (`aotn_stash.py`),
  readable output or `--json`; exit 1 when refused. Users see "text";
  JSON keeps `string`.
- `persistence.write_json_atomic` now serves both workflow saves and the
  Stash (same temp-file-and-rename write as before).
- Verified on WSL with a real Windows path (`C:\Windows\win.ini` →
  `/mnt/c/Windows/win.ini`) and a test that converts a temp file with
  `wslpath -w` and parses the quoted result.

## 2026-10-17 — Docs A: Entry Route and S1 Corrections

Branch `docs/a-entry-route`; implementation commit `77784ff`, rebased onto
`7e3f151` (workflow naming #68). Naming's entry and integration history retained.
Initial baseline `0d03eb2`: 1466 passed in 177.98s. Final: 1480 passed in
178.18s on the rebased docs branch. See [Current State](CURRENT_STATE.md).

- F01–F04/F14/F15: README absorbs task routing; AGENTS becomes a short pointer;
  the copied newcomer candidate becomes a checked 180-line guide. Historical
  banners stop old handoffs/prompts directing completed work or agent merges.
- F05/F08/F09: use `store_persistent(..., type_tag=...)` and tagged references;
  document Chat's actual routing defaults and File Write's error contract.
- F06/F07/F41: explain full-file/test overwrite and legacy output type loss
  before helper commands; give separate app/root command paths and temporary
  generation/manual preservation instructions.
- F10/F11: distinguish natural endings, explicit End and its hidden selector
  status; Echo converts to text. Only its docstrings/description changed.
- F12/F13: publish outputs before marking the saved node ID completed; preserve
  subworkflow reuse through a separate child RunContext, as D3 specifies.
- Copied only the surviving audit report, with unavailable evidence marked.
  No docs moved/archived yet; PR B rebuilds vision sources before extraction.
  The owner's untracked guide, audit prompt and workflows remain untouched.
- Verification: all 176 relative Markdown links/anchors resolve; whitespace
  clean; isolated guide example builds, inspects and runs to FINISHED with
  `[Output] Hello`. Vault/resource, Chat defaults, Echo conversion, legacy type
  loss, unified type retention and generator overwrite probes pass. AST
  comparison confirms Echo behavior is unchanged. No tests were modified.
- The brief's timeout shorthand was checked against Supervisor: the setting
  supplies default waits, not a universal execute timeout. The guide states
  that limit explicitly. Clean install/native FO7 and original audit evidence
  remain unverified; PR B/C wait for the owner's merge sequence.

## 2026-10-17 — Workflow Naming: Rename In The Library, Name On New

Branch `dist/workflow-naming`, from `main` at `95f8399` (PR #65) with
`dist/c7-deep-branch` merged in (its re-land PR #67 was still open).
Before: 1466 passed. After: 1480 passed (14 new tests in
`test_workflow_naming.py`).

- **#66 landed on the wrong branch:** it merged while its base was
  still `dist/c6-random-chat` (merged branches aren't deleted, so GitHub
  didn't retarget it). PR #67 carries the same branch into `main`.
- **One name rule** (`backend/workflow_names.py`): trimmed, not blank,
  and no other saved workflow with the same name ignoring case. Used by
  the library's rename, New, Duplicate (`X (Copy)`, then `X (Copy) 2`)
  and `aotn build` (which had its own copy of the check).
- **Rename (`R` in the library):** `SaveManager.rename_workflow` writes
  only the name into the saved file, and `WorkflowMap.set_workflow_name`
  updates an open copy without marking it dirty, so unsaved edits stay
  unsaved. The library reopens afterwards.
- **New (`N`, Ctrl+N):** asks for a name first, prefilled with the first
  unused `Untitled Workflow`, `Untitled Workflow 2`, ...; Esc creates
  nothing.
- **Name prompt:** `NamePromptScreen`, a rejected name keeps it open
  with the reason under the field. Enter or Ctrl+S (owner: save, as
  elsewhere) confirms whether or not the field is in edit mode: other prompts need Ctrl+Enter, which many
  terminals and tmux don't send distinctly. Sample screens were sent to
  the owner before the PR.
- Library help line and the Help screen list the library keys.
- **Owner request:** `E` loads the highlighted workflow, as `E` chooses in
  every other list (on the Cancel button it cancels). Export moved from
  `E` to `O`, pairing with `I` import (in/out).

## 2026-10-17 — C7: Deep Branch Offers Only `branch`

Branch `dist/c7-deep-branch`, stacked on `dist/c6-random-chat` (PR #65).
Before: 1456 passed. After: 1457 passed.

- **Owner decision (2026-10-17):** Deep Branch is a debug node for the
  branch depth limit; narrow it rather than add engine behaviour, and keep
  debug nodes consistent without going further.
- A node that spawns branches ends its own supervisor, so Deep Branch's
  `default` port was filled but never ran. It is removed; the node offers
  only `branch`. Saved workflows that wired `default` get `undeclared_port`.
- `test_deep_branch_respects_depth_limit` used to wire only `default` to
  End and accept FINISHED or ERROR. It now loops `branch` into the node and
  asserts supervisors at depths 0–5 and a FINISHED run. New
  `test_deep_branch_offers_only_the_branch_port` fails on the old node.
- **Review fix (payload):** the child branch's first node reads the
  `branch` port's stored output, which Deep Branch never stored, so
  Start → Deep Branch → Probe saw `None` (also before C7). Parallel
  Branch stores each path itself; Deep Branch now returns
  `data: {"branch": value}`. `test_deep_branch_child_receives_the_payload`
  fails on the old node. With the C4 review fix merged up the stack the
  suite is 1466 passed.

## 2026-10-17 — C6: Random Number's Payload Field; Chat Vault Output Off

Branch `dist/c6-random-chat`, stacked on `dist/c4-forwarding` (PR #64).
Before: 1449 passed. After: 1456 passed (7 new tests in
`test_c6_payload_and_chat_defaults.py`).

- **C6 root cause:** the helper generator's `producer` template adds a
  "Payload" (`value`) field to every producer; Random Number computes its
  output and never read it. New spec option `payload_field: false`
  (generator, NODE_HELPER.md); Random Number's spec sets it.
- **Regeneration refused:** regenerating Random Number from its spec also
  changed its family (Complex → Utility), colour and group, and dropped
  the output's `data_type: number` (the generator's `_port_metadata` keeps
  only name/description). Reverted; the field was removed from the class
  by hand. Both recorded under C8.
- **Saved `value` keys** stay in the config and are ignored; no migration
  is needed (nothing transforms them; the editor and loader keep unknown
  keys). Tested through load, the node editor's save, and a run. A spec
  for `aotn build` that sets `value` now gets `unknown_config_key`.
- **Owner decision (2026-10-17):** Chat Completion's Vault output defaults
  to off; a fresh Chat node now fails Validate only for its secret.
  `examples/summarise_file.json` turns Vault output on explicitly. Two tests
  encoded the old default and were updated deliberately: the generated
  `test_chat_completion_node_session_and_routing_fields` now asserts
  `vault_write is False`; `test_wait_until_releases_llm_after_answer_is_published`
  sets `vault_write: True` with its key.

## 2026-10-17 — C4: Fixed Forwarding Declared

Branch `dist/c4-forwarding`, from `main` at `105623d` (PR #63). The owner
asked for a brief self-review of #62/#63, merge, and continue: the review
found HTTP Request's error path listed twice in `inspect` (fixed with a
test before merging #62 and #63). Before: 1424 passed. After: 1449 passed
(new `test_forwarding.py`).

- No-Op, Logger, Probe, Memory Snapshot, Merge Beacon and Repeat Counter
  return their input unchanged (read in their `execute`); they now declare
  `ui_hints` `pass_through` (one-line summary, shown read-only in the node
  editor as "Dead drop payload: ...") and `forwarded_input_port: input`,
  like Sleep and Counter. `test_forwarding.py` runs each node and checks
  the payload comes out as the same object.
- Effect: types flow through them. Random Number → Logger → File Reader now
  warns "Type mismatch"; the Source dropdowns, the selector filter and
  `aotn inspect` see the producer's type.
- Tests changed deliberately: four preview tests in `test_debug_nodes.py`
  used a standalone Logger as a named producer; with forwarding a Logger
  with nothing connected passes nothing on, so they now use Get Variable
  (same "Output" port, produces its own value). `test_any_paths_keep_working`
  (C2) and `test_data_flow_statuses` (inspect) used No-Op as an untyped
  node; they now use Echo, which computes its output.
- Not done (plan says config-selected): Conditional forwards its input or
  a Vault variable depending on its source; Merge forwards a selected
  branch.
- **Review fix:** forwarding was applied to every port, including
  `error`, so Random Number → Logger's error output was typed `number`
  although it carries the failure record (false "Type mismatch";
  wrong preview). Sleep and Counter already had this; C4 spread it.
  `port_types.is_pass_through_node` now never forwards on `error`;
  `test_error_output_is_not_forwarded` covers all eight forwarding nodes.

## 2026-10-17 — Workflow Authoring Tool, PR 2 (Inspect + Examples)

Branch `dist/authoring-inspect`, stacked on `docs/stash-proposal` (PR #62).
Before: 1400 passed. After: 1424 passed (24 new tests in
`test_authoring_examples.py`).

- **`authoring.inspect_workflow`** and **`aotn inspect <id|name|path>`**:
  execution outline from Start (first-connection rule, ignored extra
  connections, parallel splits, one-of choices, on-error paths, loops,
  joins, nodes not reached), Vault writers/readers with ordering (before /
  not guaranteed / no writer), data-flow statuses (ok, ok (accepts any),
  mismatch, unchecked), unchecked config, changed-from-default config,
  validation. Duplicate names get an id suffix (`No-Op #3f2a`).
- **Shared lookup:** `run_service.resolve_workflow_data` (id, name
  case-insensitive, or .json path), used by `aotn run` and `aotn inspect`.
- **`custom_config_keys`** on node classes, published by the factory:
  config a custom editor section manages. Error Mux declares `routes` and
  `unmatched_route` (before this a spec could not configure a mux).
- **`examples/`**: six specs (parallel wait, ask and branch, Vault handoff,
  fetch and save, catch HTTP errors, summarise a file) with a README; the
  suite builds and inspects each.
- **Finding for the owner (not changed):** a freshly added Chat Completion
  fails Validate: its defaults turn Vault output on with an empty key
  (`vault_output_key_missing`), besides the expected "secret required".
  Only File Reader/Write (path) and Chat fail with their own defaults.
- **PR 63 review (five findings, all reproduced, fixed on the branch):**
  1. Vault "before" was claimed for any ancestor writer, even one on a
     Conditional branch the run can bypass. Now "before" only when every
     path from Start to the reader passes a writer; otherwise "not
     guaranteed" (a path skips every writer / writers on a parallel path);
     plus "its own key" (Counter) and "not reached".
  2. The outline walked hidden outputs (a two-path Branch with a kept
     `path_c` connection split three ways); only active ports are walked,
     hidden connections are listed as never running.
  3. Wait Until targets saved as a list (the editor) showed as `?`; both
     list and comma-string forms are read, as the engine does.
  4. Error Mux `unmatched_label` / `unmatched_forward` were rejected;
     declared as custom keys.
  5. `aotn inspect` on a file that is not a workflow (`[]`) raised a
     traceback; it now applies `aotn run`'s shape checks and exits 2.
  9 new tests fail on the first PR head. Stash proposal: paste outcomes
  reconciled (section 9.7) on #62's branch and merged in.

## 2026-10-17 — Stash Proposal Brought Into The Plan

Docs only. The owner's `STASH_PROPOSAL.md` (written in another session on
`claude/drag-drop-file-paths-j7o5r1`, cut from an older main) was
cherry-picked onto `main` as `docs/stash-proposal`, its commit message
reworded to drop a model-name attribution line (owner rule). Added
section 9 (review notes the owner agreed with, and the order) and put
Stash S1–S3 into `NODE_CONTRACT_PLAN.md`'s agreed order, before Step 4.
Still a proposal, not approved. The `ctrl+p` terminal test waits until S3.

## 2026-10-16 — Workflow Authoring Tool, PR 1 (Core)

Branch `dist/authoring-core`, from `main` at `4f045bd` (PR #60). The owner
merged #59 and #60 and asked to continue. Before: 1376 passed. After:
1400 passed (24 new tests in `test_authoring.py`).

- **Reproduced first** (the proposal's findings, on main): `connect()`
  accepts a port that does not exist; `update_node_config` replaces the
  config; a misspelled key (`duraton`) passes validation silently; Merge
  has five config keys and an empty schema.
- **`backend/authoring.py`**: `list_node_types`, `describe_node_type`
  (config-aware: resolved ports and types, field limits and visibility,
  Vault reads/writes, declared errors, node-reference fields, keys without
  schema reported as unchecked) and `build_workflow` (spec
  `aotn-workflow/1`: handles, real config keys merged over defaults,
  explicit ports, Wait Until targets as handles; every problem reported in
  one pass; the validator's errors fail the build; SaveManager save;
  duplicate names refused; reload into a fresh map and re-check; nothing
  written on failure).
- **CLI**: `aotn nodes`, `aotn describe <type> [--set k=v]`, `aotn build
  <spec|-> [--check]`, all with `--json` and `--data-dir`
  (`aotn_author.py`, dispatched from `main.py`; added to `py-modules`).
- **Shared change**: `persistence.save_workflow` writes atomically (temp
  file, then rename), for the app too.
- **Kept as is on purpose**: `WorkflowMap.connect()` and
  `update_node_config()` (the editor relies on both); the builder checks
  ports and merges overrides itself.
- Tried end to end on a temporary data folder: a bad spec listed all
  seven problems; a good spec saved, its Wait Until target was the
  generated id, and `aotn run` finished it.
- New `docs/WORKFLOW_AUTHORING.md`; README, TASK_INDEX and AGENTS.md
  point to it.
- **PR 61 review (four P2 findings, all reproduced, fixed on the branch):**
  1. Concurrent saves shared one temporary filename (six of eight writers
     failed in the probe); `save_workflow` now uses `tempfile.mkstemp`.
  2. One output wired to two nodes built cleanly but only the first runs
     (`find_next_node_id`). New validator warning `ignored_fan_out`
     (label "Ignored connection"; the `error` port and inline Error Mux
     catches are exempt); the builder treats it as an error.
  3. Duplicate names were compared case-sensitively while `aotn run`
     matches case-insensitively; now `casefold`.
  4. `--json` output could start with a plain-text warning: persistence
     now logs warnings instead of printing, and the CLI sends any stray
     stdout to stderr. Checked in a real shell pipe.
  Five new tests fail on the first PR head; the sixth (inline Error Mux
  exemption) guards the new rule.
  `test_prune_merge_node_survives_when_another_branch_still_feeds_it`
  asserted no warnings, but its fixture wires `start.default` to two nodes;
  it now expects exactly that `ignored_fan_out` (updated deliberately).
  Read-only check of the owner's saves: one "Untitled Workflow" has a
  Parallel Branch `path_a` wired to two different Merge nodes; only the
  first runs, and the editor's Validate now says so.

## 2026-10-15 — C5: Number Field Policy

Branch `dist/c5-number-validation`, stacked on `dist/c3-mode-output-types`
(PR #59; merge that first). Before: 1328 passed. After: 1376 passed
(new `test_number_policy.py`; `test_form_generator.py`'s coercion test
rewritten).

Owner approved the policy: block save with an inline error, limits declared
per field, blank means default, the same check in the validator.

- **Reproduced first:** on main the validator passed Sleep durations
  `'definitely not a number'`, `-1` and `'inf'`; the form turned unparseable
  or blank numbers into 0.
- **Shared check:** `field_types.check_number(field, raw, default)` returns
  `(value, problem)`; `number_fields`, and `field_visible` (moved from the
  validator so the editor and validator share it).
- **Editor:** `NodeConfigScreen._checked_numbers` runs on every save;
  problems show in red under the field (under the whole row for inline
  fields), the typed text stays, focus goes to the first bad field, and
  a toast says how many to fix. Blank saves the default. Number inputs
  show the placeholder `blank = default`.
- **Validator:** `invalid_number` (label "Invalid number") for a visible
  saved value that fails; it blocks the run. The owner's saved workflows
  have none (read-only check).
- **Limits:** Chat Completion max tokens ≥ 1 and temperature 0–1 (the
  provider's range); HTTP timeout > 0 (`min_exclusive`); Repeat Counter
  max visits ≥ 1. Existing: Sleep 0–60, Branch count 2–64, wrap width ≥ 0,
  Wait Until timeout ≥ 0. A test checks every default passes its field.
- **Helper specs:** HTTP Request changed through its spec and regenerated
  (custom body and test cases restored). Chat Completion's spec has
  drifted from its class (512 differing lines, plan item C8), so a
  regenerate would destroy the node: its class and spec fields were edited
  by hand to match.
- **Test changed deliberately:** `test_numeric_coercion_on_invalid_input_
  defaults_to_zero` encoded the old coercion; now
  `test_numeric_fields_keep_unparseable_text`.
- Sample screen (Sleep with -2) sent before the PR.
- **PR 60 review (four findings, all reproduced, fixed on the branch):**
  1. Integers went through float (9007199254740993 became …992) and a
     saved 10**400 crashed with OverflowError. Integer fields now parse
     exactly (`_whole_number`); float overflow reports "Number is too
     large".
  2. Preflight accepted values execution could not use (Sleep `""`,
     Repeat Counter `"3.0"` raised at run time). `Node.__init__` now
     stores number fields through `field_types.normalize_numbers`, so
     every node receives exactly what preflight checked.
  3. Custom controls bypassed the policy: Branch count 65 saved as 64 and
     `abc` as 2; Wait Until still rejected a blank timeout. The editor now
     checks the type's whole schema, including custom controls
     (`CUSTOM_NUMBER_CONTROLS`: Branch count), and Wait Until's timeout
     uses `check_number` (blank = 0, wait forever). Its own "nonnegative
     number" message is gone; `test_wait_timeout_validation_and_cancel`
     was updated deliberately to assert the shared inline error.
  4. An untouched save of a partial config (Sleep `{}`) added keys; the
     no-edit comparison now runs before checked numbers are written.
  12 new tests fail on the first PR head.
- **PR 58 review (maintainability):** `test_validation_codes.py` counted
  source snippets; it now parses `validator.py` with `ast` and requires every
  issue dict (a dict literal with a "message" key) to carry a registered
  literal code, independent of formatting. A mutation check (one code
  removed) fails with the line number.

## 2026-10-15 — C3: Mode-Resolved Output Types

Branch `dist/c3-mode-output-types`, from `main` at `9809a90` (PR #58).
Before: 1314 passed. After: 1328 passed (14 new tests in
`test_mode_output_types.py`).

- **HTTP Request** (helper-generated): the spec now declares the `default`
  port ("Response", static type `any`); regenerated with
  `create_node.py --force`, custom body restored, and the custom hook
  `describe_output_ports` resolves the type to `string` or `file` by
  "Response as". The generated test file's custom cases were restored
  unchanged (the generated part did not differ).
- **Consumers:** the validator's type check, the Source dropdowns, the
  selector filter, previews (`trace_transient_producer`) and auto-wiring
  already read per-config metadata through the factory hook, so they pick
  the type up with no change. Vault typing did not: new
  `port_types.resolved_metadata(factory, type, config)` now feeds
  `typed_vault_writes` in the validator, the Vault pickers
  (`_declared_vault_writer_keys`), `memory_registry` and the Branch-seed
  tracer.
- **Audit:** of the nodes with a concrete output type (string, number,
  file), HTTP Request is the only one whose type changes with a setting;
  Random Number's integer/float mode is `number` either way, and
  pass-through options were already handled by `is_pass_through_node`.
  Nodes typed `any` whose real type could be known (Get Variable from its
  key's writer, JSON Path) are later contract work.
- **Reproduced first:** with the HTTP change reverted, 10 of the 14 new
  tests fail, including the audit's case (file mode into File Write wired
  `content`; now `file_path`).
- Plan updated with the agreed order (C3 → C5 → authoring tool → C4, C6,
  C7 → Step 4), the authoring tool's scope, and the queued naming PR.
- **PR 59 review (P3, fixed):** the editor's details panel still showed
  `Response [any]` in both modes; `_detail_output_lines` now reads
  `resolved_metadata` (2 new tests; suite 1330).

## 2026-10-15 — Validator Issue Codes

Branch `dist/validation-issue-codes`, stacked on
`dist/selector-upstream-filter` (PR #57; merge that first). Before: 1308
passed. After: 1314 passed (6 new tests in `test_validation_codes.py`).

- Owner chose this small PR before C3 so labels stop depending on message
  text (C1 and C2 had each added another text match).
- `backend/validation_codes.py`: `ISSUE_CODES`, 34 codes with one-line
  meanings. All 38 message sites in `validator.py` now add `code`;
  `type_mismatch` also carries `port` and `source_node_id`,
  `unwritten_vault_key` carries `port`. `message` is unchanged, so the CLI
  and logs read the same.
- Validation Details: `VALIDATION_LABELS` (code to label) replaces the
  text matching in `_validation_type`; unknown codes fall back to
  "Validation issue". Every issue now gets a specific label; new names:
  "Missing node" (was "Missing connection target"), "No Start node" /
  "Several Start nodes" (was "Start node"), plus labels for checks that
  had none (secrets, files, Vault keys, Error Mux, unused ports).
- Tests: codes used equal codes registered, every append carries a code,
  every code has a label, a messy workflow yields only registered codes
  with port/source details, labels ignore message wording. One C1 test
  that compared a whole issue dict now includes the code (intended).
- Wording noticed for the owner's batch: an unknown type reads "Unknown
  node type: Unknown node type: ..." (label and message repeat).
- Sample screen sent before the PR.

## 2026-10-14 — Node Selector: Fitting-Only Toggle (owner request)

Branch `dist/selector-upstream-filter`, stacked on
`dist/c2-edge-compatibility` (PR #56; merge that first). Before: 1292
passed. After: 1308 passed (16 new tests in
`test_selector_upstream_filter.py`).

- Owner asked for a key in the node selector that shows either all nodes
  or only those that can take what is upstream. `T` toggles it; default
  is all nodes (unchanged behaviour) and the choice is remembered for the
  app session (`NodeSelectorScreen.show_fitting_only`).
- Backend `port_types.accepts_producers(factory, node_type, types)`: a
  node fits when any input port takes any of the upstream types
  (`types_compatible`); nodes without inputs never fit.
- The editor traces the upstream of the add/insert point with
  `trace_producers` (so Sleep after Dice counts as number) and passes
  `{name, types}`; the title reads `Add Node · after Dice (number)`.
- Upstream only: an insert between two nodes does not yet check that the
  new node's output suits the downstream node. Most ports are `any`
  today, so the filter hides few nodes (file and text ports); it gets
  sharper as C3 and the migration declare types.
- Sample screens (all vs fitting, inserting after Dice) sent before the PR.

## 2026-10-14 — C2: Edge Compatibility Diagnostics

Branch `dist/c2-edge-compatibility`, from `main` at `4d7eca2` (PR #55).
Before: 1260 passed. After: 1292 passed (32 new tests in
`test_edge_compatibility.py`).

- **One rule:** `data_types.types_compatible(actual, wanted)`: `any` or no
  type on either side matches, otherwise canonical types must be equal (no
  implicit conversion; File Write rejects a number on its text input). The
  editor's connector choice (`_matching_typed_input_ports`), the Source
  dropdowns (Upstream option filter, Vault key filter; untagged legacy keys
  still count as text) and the validator use it. Dropdown behaviour is
  unchanged.
- **Backend tracing:** new `backend/port_types.py` (`metadata_for_type`,
  `is_pass_through_node`, `port_metadata`, `input_port_type`,
  `trace_producer`). `frontend/node_io_display.py` now imports the first
  three instead of keeping its own copies.
- **Preflight:** an active Upstream edge (`<port>_source` is Upstream
  payload, or the port has no selector) whose traced producer type the
  port does not accept is a warning, labelled "Type mismatch" in
  Validation Details: `Input 'File' expects file but Dice sends number`.
  No-op and other `any` outputs never warn. The owner's saved workflows
  produce no new warnings (read-only check).
- **Runtime:** `data_types.describe_value` and `input_mismatch_message`;
  File Reader, File Write (File Path and Content) and File View now say
  `Input 'File' (Upstream payload) expects a file reference but got a
  number (42).` instead of "must contain a typed file reference".
- Reproduction: Random Number → File Reader on Upstream validated clean
  before and failed at run time with a message naming neither port nor
  value; the new tests fail on the old code.
- Sample screen sent to the owner before the PR.
- **PR 56 review (fixed):** the tracer followed only the first connection
  into a pass-through node, so File Write and Random Number both feeding a
  Sleep before File Reader warned or not depending on connection order.
  `port_types.trace_producers` now returns every producer a pass-through
  chain can forward (each connection into its forwarded port, without
  repeats, ending on cycles) and the validator checks each. Reproduced
  first (the File-Write-first order failed).
- **Owner follow-up (2026-10-14): Source dropdown checks every producer.**
  The Upstream option used the display tracer, which follows only the
  first connection, so a Sleep fed by Random Number then File Write hid
  it from File Reader. It now uses `trace_producers` and is offered when
  any producer fits (the validator warns about the rest). To keep the
  dropdown's Branch behaviour, `trace_producers` now follows Branch paths
  like the display tracer does: a path forwards the Branch's input, or a
  Vault-seeded path carries its key's writer types. So Random Number →
  Branch → File Reader now warns too. The display tracer
  (`trace_transient_producer`) still names only the first producer in
  previews; that is display, not a check.

## 2026-10-14 — C1: Preflight Warnings for Node-Specific Vault Reads

Branch `dist/c1-vault-read-warnings`, from `main` at `959eb58` (PR #54).
Before: 1247 passed. After: 1260 passed (13 new tests in
`test_validator_node_vault_reads.py`).

Owner approved `NODE_CONTRACT_PLAN.md` C1–C7 (C8–C12 stay proposed).

- **Shared model:** `vault_declarations.vault_read_entries` returns every
  Vault read as `{source_id, target_port, required}`. `membank_inputs` and
  standard-model reads are required; `config_vault_read_entries` (Get
  Variable, Variable Reader, Conditional on a variable, Counter, Branch
  `vault:` seeds) are all optional because each has a runtime fallback.
  `config_vault_reads` and `active_vault_reads` are derived from them, so the
  Connections tab is unchanged.
- **Validator:** an optional node-specific read whose key no node writes is
  a warning ("Reads Vault key 'value' but no node writes it; the node uses its
  fallback value", or "Path 'Branch 1' seeds from Vault key ..." for Branch
  seeds); a required one is the existing "Membank input source not declared"
  error. Counter writes its own key, so it never warns. The parallel-branch
  race warning now also covers node-specific reads.
- **Validation Details** labels the warning "Unwritten Vault key". Sample
  screen sent to the owner before the PR.
- Reproduction: Start → Get Variable (default key `value`) validated clean
  before; the new tests fail on the old code (missing model functions, no
  warning).

## 2026-10-14 — Session Handoff: UX Detour Complete

Docs only. New `NODE_CONTRACT_EXECUTION_PROMPT.md` starts the next phase: what
to read, where things stand after PRs #43–#53, the owner's direction
(required/optional, data types, help popup, lazy loading, stable labels),
the next step (confirm, then `NODE_CONTRACT_PLAN.md` C1 as warnings plus a
required/optional flag), the working practice and the paste-in message.
`RECOVERY_UX_EXECUTION_PROMPT.md` points to it. Suite unchanged: 1247 passed.

## 2026-10-14 — UX6 Follow-up: One Help Ribbon, A/D on Branch Selects, IDs on Their Own Line

Branch `dist/ux6b-ids-errors-keys`, from `main` at `6f70f85` (PR #52).
Before: 1244 passed. After: 1245 passed (1 new A/D test; `test_node_labels.py`
rewritten for the rolled-back suffix and the new headings: 4 tests).

Owner requests (2026-10-14):

1. **One key-hint ribbon, at the bottom.** Settings, User Input and the
   workflow path prompt still showed a top copy above their status bar; the
   top copies are gone (node editors lost theirs in UX6). Screens without a
   status bar keep their single hint line. A per-panel `H` key-list popup is
   planned (`NODE_CONTRACT_PLAN.md`, owner direction).
2. **A/D on a branch-select row** steps through that node's branches, error
   recovery included (`EditorScreen._cycle_selected_branch_select`); `E` still
   opens the selector. Elsewhere A/D are unchanged (PR #49 rule).
3. **Node IDs:** the UX6 numbered suffix is rolled back; names are the alias
   or type name everywhere. The ID moved off labels onto its own line: under
   the node editor title (`#node-config-id`) and under `Name:` in the details
   panel; execution cards no longer show it; "Merge Node" / "Merges To
   Branch" lines and the "Jumped to" toast use names.
4. **Error headings:** the runtime error screen and validation results open
   with `<name> (<type>) · depth <n> · <branch>` (`frontend/node_location.py`),
   then `Node ID: …`; the runtime screen keeps the run branch, category,
   message and traceback below.
5. Recorded in `NODE_CONTRACT_PLAN.md` (owner direction): required vs
   optional inputs/outputs will be defined when nodes are re-touched; more
   Vault/dead-drop data types are needed for community nodes; C1 proposed as
   a warning with a required/optional flag.

**Tests updated (behaviour the owner changed):** six assertions in
`test_debug_nodes.py` expected IDs inside names (`Merge Node: Merge (id)`,
`Merges To Branch: Approve (id:path_a)`, `Name: Logger (id)`, the editor title
`Edit Node: Logger (id)`, the details line order) or the suffix (`Merge ·1001`);
they now assert the names and the separate `Node ID:` line.

**Review of PR #53 (two crashes, both reproduced and fixed).** After: 1247
passed (2 new in `test_node_labels.py`; both fail before the fix).

1. A node name such as `Fetch [/draft]` was parsed as markup and crashed Error
   Details and validation results. Both now render as literal text
   (`markup=False`), which also covers brackets in messages and tracebacks.
2. The heading reused `_branch_contexts_by_node`, which recursed once per
   node and crashed past ~1,000 connected nodes. It now walks with an explicit
   stack, pushing children in reverse so the visit order (and each node's
   first branch path) is unchanged; the UX3 equivalence tests against the old
   scan still pass.

## 2026-10-13 — UX6: Friendly Labels and Presentation Pass

Branch `dist/ux6-labels-and-presentation`, from `main` at `1a92b43` (PR #51).
Before: 1240 passed. After: 1244 passed (4 new in `tests/test_node_labels.py`).
Sample screens were reviewed by the owner before and after the Branch-row
revision; the owner checked the result live and approved it.

**Owner answers:** Q8 — a counter suffix from 1000 ("something simple for
now, we can re-address this"); details below. Timing of the node contract plan
— the owner asked for best judgement: after UX6 and before Step 4 (Step 4's
contracts build on it), bug items C1–C7 first. Cancel is renamed Close.

1. **Friendly labels** (U5, `frontend/node_labels.py`): a node's usual name,
   plus ` ·1000`, ` ·1001`, … for every node whose name is shared, in
   workflow order. Display only. Used in editor cards (the editor computes
   the labels once per refresh), Connections rows (which no longer repeat the
   node ID), Wait Until targets, the Error Resolver unpick list, the unsaved
   prompt and Merge selectors. The details panel and editor title keep the ID.
2. **Presentation:** tab headers `1 Source` instead of `1 - Source` on every
   tabbed screen (node config, node selector, settings); the duplicate key
   hint line at the top of the node editor is gone (the status bar keeps it,
   reworded to fit 100 columns); Save / Close are compact one-row buttons.
3. **Branch path rows:** one row per path, Branch ID beside its Start Payload
   dropdown, with column headings. The first version used compact borderless
   dropdowns; the owner found them indistinguishable from the names and the
   open list indistinguishable from the rows, so the dropdowns keep their
   border, and every open dropdown list now has a rounded accent border, a
   darker background and a bold highlighted option (global style).
4. **Row navigation in node editors:** W/S and up/down moved one widget at a
   time, so in a path row they went name → its own dropdown → next name (the
   owner saw this as an invisible stop). `NodeConfigScreen._move_keyboard_focus`
   now moves by rows (`group_widgets_into_rows` / `row_move_target`), as
   `UI_QUICK_REFERENCE.md` already specified, and `row_move_target` keeps the
   column index when both rows have the same number of widgets.
5. **64-path Branch open:** 695 → 567 widgets; 0.50–0.67 s → about 0.5–0.6 s
   (target under 0.5 s not met: the rest is Textual building 64 dropdowns).
   Lazy loading is logged in `PROJECT_BACKLOG.md` with the owner's rule (load
   what is shown first, queue Save / Close until all is loaded). Errors text
   was already shortened in UX4.

**Tests updated (behaviour the owner changed):** three Connections tests and
the Merge Beacon selector test expected labels with IDs or without a suffix
(two Merges named "Merge" now read `Merge ·1001`);
`test_branch_config_uses_parallel_payload_ui` read the removed top help line
(it now reads the status bar) and expected S to visit every dropdown (it now
checks S keeps the Branch ID column, D reaches the row's dropdown and W keeps
the dropdown column).

**Behavior changes:** suffixed labels for repeated names; `N Label` tab
headers; Close instead of Cancel; row-wise W/S wherever widgets sit side by
side in a node editor; open dropdown lists look different everywhere.

## 2026-10-13 — UX5: Connections Tab With Jumps, Ctrl+S Save and Stay

Branch `dist/ux5-connections-and-saving`, from `main` at `4bb89cd` (PR #50).
Before: 1212 passed. After: 1230 passed (18 new in
`tests/test_connections_and_saving.py`; all fail on the old code).

**Owner decisions in this phase (replace Q2 and revise U3):** the key check
in the app's terminal panel showed Ctrl+Space arriving as `ctrl+@`, and F2
never arrived (it is a volume key on the owner's keyboard). The owner then
chose: **Ctrl+S saves and stays** (also commits a text field being edited),
**Ctrl+Enter does the same**, **Esc closes** and asks Save / Discard / Stay
when there are unsaved changes. No Ctrl+Space or F2 binding.

1. **Connections tab** (`frontend/connection_rows.py`, node config tab 4,
   Wait Until tab 2): Incoming and Outgoing rows name the node at the other
   end, both port display names and what flows (the producer's payload name,
   or "No payload" when the source publishes nothing). Vault reads (declared
   `membank_inputs` and `<port>_source: Vault` keys) are listed separately
   with their writer, or "no node writes it". A row whose node exists is a
   compact button; Enter opens that node's editor. Rows refresh after a save
   and after Error Resolver picks (the "removed on save" note moved here). It
   replaces the `#connection-summary` text; the Errors section stays below.
2. **Save and stay**: `NodeConfigScreen(on_save=…)`; the editor applies the
   save at once (`EditorScreen._save_and_stay`) and the screen takes a new
   no-edit snapshot. Without `on_save` the last saved result is returned on
   close. The Save button still saves and closes. Ctrl+S / Ctrl+Enter are
   priority bindings so they work while a field is being edited.
3. **Save / Discard / Stay** (U9, `screens/unsaved_changes.py`) on Esc,
   Cancel, Ctrl+Q and Connections jumps. "Unsaved" compares the widgets with
   the snapshot (UX2) and the alias. A fresh Error Resolver saved with Ctrl+S
   is kept when its editor closes (U8 revert only for a never-saved one).
4. The editor opens node editors through `_open_node_config(node_id)`: saves
   and jumps go to that node, not to whatever the editor has selected.

**Tests updated (behaviour the owner changed):** seven test cases pressed Ctrl+S
and expected the editor to close
(`test_file_writer_configured_content_has_visible_keyboard_editor`,
`test_node_config_saves_transient_output_overrides_and_vertical_buttons`,
both `test_viewer_payload_ui_saves_vault_option_with_or_without_forwarding`
cases, the three `test_wait_layout_navigation_and_clean_save` widths); they
now assert the editor stays open, then press Esc and check the same saved
config. The five `test_wait_timeout_validation_and_cancel` cases expected
Cancel to discard an edit silently; they now assert the prompt appears and
press Discard. `test_mux_connections_summary_follows_the_picks` reads the
new rows instead of the removed summary.

**Self-review / found while probing:** (a) the editor's refresh after a
stay-save moved focus to the node list behind the modal, so Esc did nothing;
the screen now restores its own focus. (b) a jump to a node the editor view
does not show (a second target on the same port) opened and would have saved
the *selected* node; fixed by item 4 and covered by a test. (c) the rows'
container had the default `1fr` height and the Errors section was drawn over
them; it is `height: auto` now. Sample SVGs were sent to the owner.

**Manual check (owner, 2026-10-13, app terminal panel):** Ctrl+S saves and
stays, the Save/Discard prompt on a Connections jump works, key bindings as
expected.

**Also recorded:** the owner's live-test findings (outdated older nodes,
window placement in file nodes, missing pass-through, outdated Vault UI,
reveal without autoscroll, error UI keys during runs) as a new section in
`PROJECT_BACKLOG.md`; to be investigated when relevant.

**Behavior changes:** Ctrl+S in a node editor no longer closes it; Esc and
Cancel ask before discarding edits; the Connections tab is rows with jumps.

**Review of PR #51 (four P2 findings, all reproduced and fixed on the
branch).** After: 1239 passed (9 new: 8 in
`test_connections_and_saving.py`, 1 runtime test in `test_error_routing.py`;
7 of the new tests fail on the first PR head, the other two confirm existing
engine behaviour and a fallback).

1. *Saving from a row moved the next jump.* The row refresh replaced the
   focused button and focus fell back to the first row. Rows now carry a
   connection identity (direction plus both node/port ends, or Vault key and
   writer); after a refresh the same connection gets focus, or the first row
   if it was removed, and the tab keeps its scroll position.
2. *Active Vault reads were missing* (Branch `vault:` seeds, Get Variable,
   Chat continuation key). New shared model in `backend/vault_declarations.py`
   (`active_vault_reads`, `standard_vault_reads`, `config_vault_reads`); the
   validator's standard-model rules (`continuation_selected`,
   `repeatable_slot_active`) moved there and the validator calls them, with
   identical results (validator suite unchanged).
3. *An existing writer was reported as absent* (Set Variable). Writers come
   from `active_vault_writes` (declared outputs, standard writes, Set
   Variable / Variable Setter / Counter fields), one entry per node. When no
   writer is declared the row says "no writer found" instead of claiming none
   exists.
4. *Error port described as "No payload"* when normal output is off. The
   Publish toggle now only affects `default`; an `error` port reads "Error
   details on failure". A runtime test routes a File Write failure with
   normal output off and checks the error payload.

**Not changed (follow-up):** `memory_registry` (Vault key pickers) and the
validator's write checks still use `standard_vault_writes` only, so Set
Variable keys are not yet offered in Vault pickers or used by validator
warnings. Moving them onto `active_vault_writes` changes what pickers offer
and what the validator warns about, so it waits for the owner. The review's
documentation drift (README → `SESSION_SUMMARY.md`, `AGENT_HANDOFF.md`
selector text, the README description of `NODE_STANDARDIZATION_HANDOFF.md`,
`AGENTS.md` data-directory/RunContext lines) is reported to the owner, not
fixed here. The plan's second-terminal manual check (Windows Terminal) was
not done at that point (see below).

**Node audit of PR #51 (owner chose: Vault fix in #51, rest planned).**
After: 1240 passed (1 new end-to-end test, which fails on `4e7af7d`).

- The Vault pickers (`memory_registry`, the node config's declared-writer
  scan) and the validator's existence/type/race checks now use
  `vault_declarations.typed_vault_writes`: standard writes with their tags
  plus node-specific writers (Set Variable, Variable Setter, Counter) with an
  unknown type. Before, a Set Variable key showed in Connections but was
  missing from Text Output's Vault picker and failed preflight with
  "Membank input source not declared". The new test checks the row, the
  picker, preflight and a real run agree. Validator reads are unchanged
  (node-specific reads: plan item C1).
- `NODE_STANDARDS.md` / `AGENT_START_GUIDE.md`: `signal_done` is a plain
  call; the examples awaited it.
- The audit's other findings (edge type checks, HTTP mode types, forwarding
  provenance, numeric save validation, Random Number's dead field, Deep
  Branch continuation, spec/generator gaps, author gate) are recorded in the
  new `NODE_CONTRACT_PLAN.md` as proposed phases C1–C12, not approved.

**Manual check, second terminal (owner, 2026-10-13):** Windows Terminal,
passed: Ctrl+S, the Esc prompt and Connections jumps behave as in the panel.

## 2026-10-13 — Session Handoff After UX4

Docs only (`RECOVERY_UX_EXECUTION_PROMPT.md`): environment notes now use the
Windows `gh` CLI for PRs and record the WSL-share edit workaround; "Current
position" has the handoff entry with the concrete UX5 steps, the owner's UI
taste, the pending Ctrl+Space/F2 key check (Q2) and one unreproduced watch
item (a new Error Resolver once missing from the editor after saving).
Suite unchanged: 1212 passed.

## 2026-10-13 — UX4 Follow-up: a/d Cycling Skips Error Recovery

Branch `dist/ux4c-resolver-branch-select`, from `main` at `7fc8e9d` (PR #48).
Before: 1210 passed. After: 1212 passed (2 new in `tests/test_recovery_flow.py`;
both fail on the old code).

Owner request: error recovery branches should not be picked up by a/d
cycling; they are reached by pressing `e` on the branch-select row under the
Error Resolver node.

- `EditorScreen._branch_view_candidates` (a/d and ctrl+a/d) leaves out
  recovery ports (`_is_recovery_port`: any node's `error` port, and an Error
  Resolver port other than No error) and nodes that Start reaches only
  through a recovery port (`_nodes_only_on_recovery_paths`), such as a Branch
  inside a recovery branch, because cycling to them would switch the
  resolver off No error.
- Unchanged: the resolver's branch-select row and `e` (BranchSelectorScreen)
  still list every branch, including recovery ones.

Also recorded: **Q4** (missing connections) — the owner reported it came
after adding a Branch midway and deleting its tombstone, and can no longer
reproduce it; it matches the Branch-tombstone prune bug fixed in PR #46.
**Q2** groundwork: Textual reports Ctrl+Space as `ctrl+@` when a terminal
sends NUL (the usual case) and as `ctrl+space` with the kitty keyboard
protocol, so UX5 binds both; F2 arrives unambiguously and is the proposed
fallback, pending the owner's check in Windows Terminal and the browser.

## 2026-10-13 — UX4 Follow-up: Error Resolver Picker Without "Any Other Error"

Branch `dist/ux4b-picker-cleanup`, from `main` at `1e6c8b4` (PR #47).
Before: 1208 passed. After: 1210 passed (2 new in `tests/test_recovery_flow.py`).

Owner question: why does the picker offer both "Unexpected failure" and "Any
other error", and can both branches be reached? Answer from the code: every
code a node can fail with is already listed (the supervisor rewrites any
undeclared code to `node_error`, and only Wait Until and User Text Input can
raise engine codes, which they declare), so "Any other error" only ever
repeated the unpicked choices; with both picked, the first listing wins and
its branch never runs. The owner chose to remove it.

- `recovery_choices` no longer offers "Any other error". A mux that already
  has `unmatched_route` still shows it, ticked and marked "Older setting …
  Unpick to remove", and keeps working until unpicked. Engine, validator and
  the `unmatched` port are unchanged.
- Picker lines use the Errors-list format, `[code] description`
  (`friendly_error_choice`, stale codes `[code] Not raised by the connected
  node`). The picker's prompts are passed as plain `Text`, because
  `SelectionList` read `[timeout]` as markup and dropped it.

**Tests updated (behaviour the owner changed):**
`test_errors_are_offered_in_plain_words` asserts the new line format and that
"Any other error" is offered only for an existing setting;
`test_config_tabs_source_picks_fill_parameters_and_payloads` no longer picks
it and asserts it is not offered.

## 2026-10-13 — UX4: Recovery Flow From the Originating Node

Branch `dist/ux4-recovery-flow`, from `main` at `1ae7d82`, then `4e1090e`
(PR #46) merged in. Before: 1195 passed. After: 1208 passed (13 new in
`tests/test_recovery_flow.py`).

Owner answers in this phase: **Q5** — the button sits under the Errors
header; after reviewing samples the owner asked for a simpler look: one
compact solid button, no status line, and each error as one plain line with
its code first (`• [timeout] The server did not answer…`). The button reads
**Add Error Resolver Node**, or **Open Error Resolver Node (N caught)** when a
mux catches the node. The node type keeps the name "Error Mux"; its default
alias is now **Error Resolver** (spec change, regenerated, custom body and the
generated test's custom cases restored; `check_node` / `check_ui` pass;
existing nodes keep their alias). **Q6** — Delete branch removes only nodes
reached through that route, stopping at a Merge or any node Start also
reaches another way. **Q7** — insert a new mux in between; the old
downstream continues on No error, which the editor keeps selected.

1. **Errors section** (`node_config._compose_errors_section`): the Show error
   path checkbox is gone (U4); `_error_path_config_values` returns nothing, so
   a stored `show_error_path` stays in the config and keeps its path (U10).
   No button on the Error Mux itself or on nodes without outputs.
2. **Spawn or open** (U2, U7, U8): the button saves the node and returns
   `then: "catch_errors"`; `EditorScreen._catch_errors_for` reuses the mux the
   node feeds directly (`error_mux_ui.inline_mux_for`, the engine's own rule)
   or inserts one with `_connect_new_node` (old downstream moves to No
   error), then opens the mux config. Cancelling the first edit of a fresh
   mux deletes it and reconnects the original edges; the editor stays on the
   originating node with the mux's No error path active. The editor's save
   path is `_apply_node_config_result`.
3. **Unpick confirmation** (U1): unpicking the last error of a branch whose
   port has a connection opens `RecoveryBranchUnpickScreen`, which lists the
   branch nodes (`error_mux_ui.branch_nodes_for_port`) with **Leave
   unlinked**, **Delete branch**, **Cancel**. Cancel picks the error again (the
   draft restores the branch); the other choices apply on save — leave drops
   the connection (the existing prune), delete turns the nodes into
   tombstones first, so undo still works.

**Tests updated (behaviour the owner changed in U4):**
`test_node_config_fixed_tabs_are_keyboard_navigable` now expects the resolver
button as the Connections tab's first field;
`test_errors_section_offers_the_toggle_only_where_error_is_not_listed` became
`test_errors_section_has_no_toggle_and_offers_the_resolver_button`;
UX2's `test_edits_are_still_saved_and_an_undone_edit_is_not` edits the URL
field instead of the removed checkbox.

**Acceptance:** mounted tests cover insertion keeping the downstream on No
error, cancel leaving the graph identical, reopening finding the same mux,
reuse only for a directly fed mux, the three unpick choices, delete stopping
at a Merge and at shared nodes, and the UX1 Merge identity with an inserted
mux.

**Self-review:** the catch button saves the node first, so pending edits are
not lost (UX5 adds Save/Discard/Stay for jumps); with UX2's invariant a
no-edit save changes nothing. Delete branch tombstones nodes before the save
prunes the connection, so each tombstone keeps its original wiring for undo.

**Behavior changes:** no Show error path toggle; new Error Muxes are named
"Error Resolver"; unpicking a branch with nodes asks first.

## 2026-10-13 — Fix: Deleting a Branch Tombstone Loses or Strands Nodes

Branch `fix/branch-prune-output-nodes`, from `main` at `1ae7d82` (PR #45).
Owner report, mid-UX4: deleting a Branch node's tombstone and keeping Branch 1
lost nodes, and the validator then reported unreachable nodes. The owner's
current save (`wf_dfe1f9277865`, read only) showed Start → File Manager → File
Write plus a detached File Reader → Text Output. UX4 work is parked in a stash
on `dist/ux4-recovery-flow`.
Before: 1191 passed. After: 1195 passed (4 new in
`tests/test_branch_prune.py`; 3 fail on the old code).

- **Cause.** `EditorWorkflowAdapter._is_branch_prune_terminal` treated Text
  Output and every Outputs-family node (File Manager, File Write) as the end
  of a path. Since `file_io_continuation_v1` those nodes continue along their
  connections, and `NODE_STANDARDS.md` says termination is declared only by
  `terminates_branch`. So keeping a path whose head is File Manager cut its
  link to File Write (`_disconnect_kept_branch_terminal_outputs`), stranding
  File Write; and dropping such a path pruned File Manager but stopped there,
  stranding everything after it.
- **Fix.** A path end is a Merge Beacon or a type with `terminates_branch`
  (End). Pruning now continues past output nodes, so one guard was added: a
  node still reachable from Start through a surviving route (the kept path or
  anything else) is never pruned (the same rule as UX4's planned Delete
  branch). Merge handling is unchanged.
- Reproduced with a probe on a temp data folder (both kept-path directions);
  after the fix neither leaves unreachable nodes.

**Behavior changes:** deleting a Branch tombstone removes the whole dropped
path, including what follows an output node, and never deletes a node that a
surviving route still reaches.

## 2026-10-13 — UX3: Measured Performance (Branch Rows, Topology Scan, Editor)

Branch `dist/ux3-measured-performance`, from `main` at `79776c3` (PR #43).
Before: 1124 passed. After: 1191 passed (67 new in
`tests/test_branch_topology_scan.py`; the timing, row-map, debounce and
metadata tests fail on the old code).

All numbers are from this machine, `frontend/styles.tcss`, 100×40, using the
review probes (`aotn_review43_probe.py`, `aotn_review43_perf.py`) and two
session scripts (a Branch-open profile and a wide-editor navigation profile).
The plan's "before" column was measured on another run (1.48 s / 0.42 s);
here the same code measured 2.006 s / 0.364 s.

| Measurement | Before | After | Target |
|---|---|---|---|
| 64-branch config open | 2.006 s | 0.58–0.65 s | under 0.5 s (owner accepted, see below) |
| 64-branch row sync | 0.364 s | 0.009–0.010 s | under 0.03 s |
| 12 fork/rejoin pairs scan | 0.0277 s | 0.0001 s | under 5 ms |
| Wide editor open (340 nodes) | 0.782 s | 0.18 s | (profile first) |
| Wide editor key press, median / p90 | 0.588 / 0.633 s | 0.139 / 0.156 s | (profile first) |

1. **Branch rows.** `NodeConfigScreen._branch_rows` maps each port to its
   row, label input and source select, filled as rows are built; the sync
   and `_branch_config_values` use it instead of three whole-screen queries
   per port. Options go through `_set_select_options_preserving_value`, which
   skips unchanged options. New rows mount in one batch. Typing in the count
   field syncs 150 ms after the last keystroke (`BRANCH_COUNT_DEBOUNCE_SECONDS`).
   UX2's open-time snapshot made `_transient_config_values` run two queries
   per output port (1.2 s of a profiled open); it now walks the screen once.
   **Open stays at ~0.6 s:** what remains is Textual applying CSS to ~700
   widgets (64 rows × ~10). The owner accepted ~0.6 s for now; lighter Branch
   rows (fewer labels per row) move into UX6's presentation pass.
2. **Topology scan.** `_branch_contexts_by_node` keeps one visited set keyed
   by (node, branch_id, branch_port) for the whole scan instead of copying it
   per edge. A node reached by several routes in the same context keeps the
   first route's `branch_path` display text (documented in the docstring).
   Identical results to the old scan (kept as a reference copy in the test)
   on fork/rejoin chains, 60 random graphs with Branches, Conditionals,
   beacons, rejoins and cycles, and every saved workflow (read-only).
3. **Main editor (Q3: the owner chose a synthetic wide graph).** 340 nodes:
   Branch(64) → HTTP Request → No Op per path, eight paths with a nested
   Branch(4) of 3-node paths, beacons and Merges; 58 navigation keys (`s`,
   `w`, `d`, `a`). The profile showed 87 of 102 profiled seconds in
   `metadata_for_type`, which rebuilt every type's metadata (including the
   64-port tables) on each of 152,188 calls. `NodeFactory.metadata_for_type`
   now builds the per-type table once (types are fixed after construction;
   the result is shared and must not be modified) and
   `node_io_display.metadata_for_type` uses it; `get_node_types_metadata`
   still returns fresh copies. Left as is: the remaining per-key cost is
   spread over port display names (`node_output_port_metadata`, ~1.9 s of a
   12 s profiled run) and Textual layout.

**Self-review:** the metadata cache must not leak edits between callers;
nothing in `frontend/` or `backend/` writes into looked-up metadata (checked by
search), and the list API is unchanged. The Branch-row map is filled where
rows are built, so a row mounted later is found too (debounce test). Timing
assertions are limited to the topology scan (best of five runs, 50× margin);
the row tests count queries and `set_options` calls instead of timing.

**Behavior changes:** Branch count edits apply after a 150 ms pause in typing.
No functional change otherwise.

## 2026-10-13 — UX2: PR #43 Made Safe (Pass-Along, Route Draft, No-Edit Save)

Branch `dist/p4-inline-error-mux` (PR #43), with `main` at `acc8e2f` (UX1, PR
#44) merged in first; the only conflict was this log. Before: 1071 passed
(P4 + UX1). After: 1124 passed (53 new in `tests/test_no_edit_save.py`; 50
fail on the pre-UX2 code). `check_node` / `check_ui` pass for
`error_mux_node`. The UX1 probe also passes with an inline Error Mux after
HTTP Request inside the Branch path (only possible on this branch).

`aotn_review43_probe.py` before → after:
- LEGACY_SAVED: `failed_input` became `forward: error` on the route and
  `unmatched_forward: error` → both keep `failed_input`.
- GROUPED_RESELECT: `timeout` came back on a new `route_…` branch with
  `error` → back on `both` with `failed_input`.
- REPEATED_RESELECT: label reverted to `Timeout` on a new branch → `Revised`
  on `both`.

1. **Legacy pass-along.** New migration `error_mux_forward_v1`
   (`config_migrations.py`): a node-wide `forward` is copied onto every route
   whose own `forward` is missing or invalid and onto `unmatched_forward`
   when that is missing or invalid, then removed and kept as evidence under
   `_config_migrations`. This reproduces the old fallback exactly. The
   fallback in `node_errors._forward` / `mux_routes` / `mux_forward_for` is
   gone: one rule remains (the branch's own choice, else `error`).
2. **Route draft record.** `frontend/error_mux_ui.MuxRouteDraft` replaces
   `routes_for_selection` and the screen's append-only `_mux_removed`:
   `routes_by_id` (id, label, forward, codes in original order) and
   `owner_by_code`. Unpicking keeps ownership; re-picking restores the same
   branch with its latest name and pass-along choice; grouped routes stay
   grouped; a newly picked code gets a branch that is remembered too.
3. **No-edit-save invariant.** The node config screen takes a snapshot of
   what its widgets describe after mount (`_collected_config`, now shared with
   `action_save`). When a save's collected config equals that snapshot (no
   edit), a key the stored config lacked stays absent and a stored empty
   value ("", None, [], {}) is kept; non-empty corrections (migrations,
   retired Wait Until declarations) are still written. A save with any edit
   is written as collected, exactly as before. This removes every noise key
   the probe found (all 38 types added some: `show_error_path: false`, empty
   `<port>_label`, default `transient_outputs`, `""`→`None` Vault keys, a
   Merge `home:path_a` carry, Branch payload sources, empty mux routes, …).
   The editor's save path is now `_apply_node_config_result(node_id,
   result)` so the test can apply it unmounted. The mounted test covers every
   registered type with its default config plus six representative configs,
   and compares config, alias and every node's connections.
4. `EXECUTION_STATUS_CONTRACT.md`: `recovered` added (statuses, priority
   order, card text); the Skip bullet that said Skip advances to the next node
   now matches D9 (Skip ends the branch).
5. Mux Connections summary refreshes after each pick and marks a connection
   whose branch is unpicked "(branch unpicked: removed on save)". UX5's
   Connections tab replaces it.

**Tests updated (behaviour the plan changed):**
`test_each_branch_chooses_what_it_passes_along` asserted the removed runtime
fallback; it now asserts raw legacy config gives `error` and the migrated
config gives `failed_input` (route and catch-all).
`test_picks_become_branches_that_keep_their_ids` uses `MuxRouteDraft` with the
same assertions. `test_wait_target_toggle_empty_selection_and_no_options`
expected a no-edit save to rewrite Wait Until's stored `target_node_ids: ""`
as `[]`; it now asserts `""` is kept and that the node reads it as no targets.

**Self-review:** the first version of item 3 applied the rule per key on
every save, so an edited save (for example enabling Vault write) would have
stored `""` instead of the prefilled default description; it now applies only
when nothing changed. A probe command in this session hung on a stray
`python -` waiting for stdin; it was stopped and nothing was written.

**Behavior changes:** a no-edit save no longer changes config; legacy muxes
migrate their node-wide pass-along on load; the P4 note that "node-wide
`forward` is the fallback" is superseded by the migration.

## 2026-10-13 — UX1: Merge Branch Identity and the Never-Drop Backstop

Branch `dist/ux1-merge-branch-identity`, from `main` at `09a1402` (PR #42).
First phase of `RECOVERY_UX_BUILD_PLAN.md`; this PR also commits that plan and
`RECOVERY_UX_EXECUTION_PROMPT.md`.
Before: 1053 passed. After: 1071 passed (18 new in
`tests/test_merge_branch_identity.py`; 16 fail on the old code).

- **Reproduced** with the review's `aotn_review41_probe.py` on `main`: turning
  on Show error path for a node inside Branch path_b changed the Merge option
  from `<branch>:path_b` to `<node>:default`; a no-edit Merge save wrote
  `branches_to_close: []`, `carry_forward_branch_id: home:path_a`, and the
  editor disconnected the Merge Beacon. After the fix the probe keeps all
  three.
- **Backend:** `Node.spawns_branches: ClassVar[bool] = False`; True on
  `BranchNode` and `DeepBranchNode`, the only nodes that signal `branches`
  (a test scans every registered class's source so a new one cannot be
  missed). Factory metadata `spawns_branches` and
  `NodeFactory.spawns_branches(type)`. No engine change.
- **Topology:** `node_config._branch_contexts_by_node` starts new branch
  contexts only at nodes whose type spawns branches. Every other node passes
  the current context to all connected targets, whatever its output count.
  Covered: Show error path on, HTTP Request (lists `error`), Error Mux
  routes, Conditional, Random Branch (picks one path, spawns none). The
  inline-mux variant from the plan only exists on PR #43's branch; UX4's
  acceptance re-runs this probe with an inserted mux.
- **Backstop:** `unmatched_merge_values(options, config, reserved_ports)` finds
  stored `branches_to_close` / carry-forward values (including the legacy
  `selected_branch_id`) that match no current option. The Merge config shows
  them as checked "Kept, no longer matches a branch" rows, with a warning, and
  a no-edit save writes them back unchanged (carry, `selected_branch_id` and
  `selected_input_port` exactly as stored). Unchecking or reselecting drops
  them explicitly. The editor's `_sync_merge_branch_end_connections` does not
  disconnect any beacon while an unmatched closure remains (it cannot know
  which beacon the value meant) and, on a Merge save, notifies the warning.
- `NODE_STANDARDS.md`: new "Branch spawning" section.
- Not changed: the editor's other `len(output_ports) > 1` checks (port
  cycling, Merge slot hints, branch selector paths) are navigation, not
  branch identity; `WorkflowMap.get_nodes("branches")` is unused by Merge.

**Checked read-only:** every workflow under `workflows/` (4 files, 1 Merge in
`wf_0d75f6241f3d`) has identical Merge options with the old and new rule and no
unmatched values; file hashes were unchanged after the check.

**Self-review:** first version computed the kept values after the "no open
branches" early return, so a Merge whose only branch identity changed and had
no home inputs would still have saved an empty closure; moved before it. The
editor first notified on every whole-workflow Merge sync (load, any node
save); now only on a Merge save. A `home:` carry-forward is judged only when
the caller passes the home inputs, so the editor never flags a valid one.

**Behavior changes:** a node with several outputs inside a Branch path no
longer creates its own Merge option (existing configs that relied on the old
identity would show as kept rows; none exist in the saved workflows). Merge
saves never drop unmatched values silently.

## 2026-10-12 — P4: Error Mux Redesign (Inline Catch, No Error Branch)

Branch `dist/p4-inline-error-mux`, from `main` at `09a1402` (P3b, PR #42).
Before: 1053 passed. After: 1053 passed (P2's route-list UI tests replaced
by tests of the new design; see below).

Owner feedback: the P2 mux was confusing. Intended use: override chosen
error codes so a failure takes a recovery path instead of stopping with an
error; a default No error branch for normal execution; pick errors in Source
(readable), get one entry per pick in Parameters (scrollable), and choose per
branch in Payloads whether to pass the error or the previous node's input.

- **Engine.** The mux sits inline: the guarded node's output feeds its
  `input`. `Supervisor._inline_error_route` routes a failure to a mux fed by
  the failed node when the mux (`catches_upstream_errors`) accepts the code;
  an explicit `error`-port connection still wins. Routed to the mux, the
  supervisor passes `inputs["error"]` (the payload) and
  `inputs["failed_input"]`; reached normally, `error` is removed so a stale
  payload never leaks. A routed failure publishes node status `recovered`
  (reason = code) instead of `errored`; unrouted failures stay `errored`.
- **Error Mux** (spec change, regenerated, custom body restored; `check_node`
  / `check_ui` pass): inputs `input`, `error` (older layout); outputs
  `default` (No error) + one per branch + `unmatched` (Any other error). No
  generic config fields; per-branch `forward` in `routes`, plus
  `unmatched_label` / `unmatched_forward`. Node-wide `forward` from P2 is the
  fallback.
- **Config UI** (custom tabs, frontend-only): Source explains the mux, names
  the guarded node and lists its errors in plain words (`HTTP status: The
  server answered with an HTTP error status... `, "Retrying may help." when
  retryable, "Unexpected failure" for `node_error`, "Any other error"); each
  pick adds a row on Parameters (branch name, prefilled) and Payloads (pass
  along: error details or the failed node's input). Unpicking and re-picking
  restores the branch's id, name and choice. P2's auto-fill on wiring, route
  list and "Refill from upstream" are removed (`ObjectListField`'s generic
  additions stay).
- **Execution display:** node cards show `↪ [recovered: HTTP status]`;
  `recovered` ranks below `errored` and `stopped`.
- Validator: a mux fed inline is valid; "Error Mux has no incoming
  connection" replaces the error-input-only warning.

**Behavior changes:** routed failures (to a mux or any `error` handler) show
`recovered`, not `errored` (`test_routing_to_the_error_port_skips_the_default_path`
updated); a new mux has a No error output; inserting a mux after a node wires
it inline. **Tests replaced, not weakened:** P2's tests of auto-fill, refill
and the route-list editor were rewritten for the new picker flow (the
features were removed at the owner's request); `test_error_mux_routes.py`
and the generated mux tests now cover inline catching, No error, per-branch
pass-along, readable choices and the Source → Parameters → Payloads flow.
`test_file_picker_export_and_import_paths` and
`test_error_buttons_have_keyboard_focus_and_scroll[True-60]` failed once
under full-suite load and pass alone (timing-sensitive UI tests).

## 2026-10-12 — P3b: Branch Beyond Five Paths, Merge Slots to Match

Branch `dist/p3b-branch-merge-slots`, from `main` at `745fed3` (P3a, PR #41).
Before: 1029 passed. After: 1053 passed.

The owner chose "Branch + Merge" over raising only Branch's cap or deferring.

- `backend/branch_paths.py`: one naming scheme for Branch paths and Merge
  slots (`path_a` … `path_z`, `path_aa` …), `MIN_BRANCH_COUNT` 2,
  `MAX_BRANCH_COUNT` 64 (a safety limit on run width), `DEFAULT_MERGE_SLOTS`
  5, `branch_count_from_config`, `merge_slot_count`, `slots_covering`.
- Branch: the type lists all 64 paths; `resolve_output_ports` returns the
  first `branch_count`; `execute` spawns exactly those.
- Merge: the type lists all 64 slots; new `input_slots` config (default 5)
  and `resolve_input_ports`. Inputs now have the mirror of the P1 output
  model: `Node.resolve_input_ports`, `get_input_ports()` uses it,
  `NodeFactory.input_ports_for` / `node_input_ports` / `declared_input_ports`,
  `WorkflowMap.input_ports`.
- Validator: inputs per node; a connection into a slot above `input_slots`
  is a warning ("never read"); a port the type never had stays an error.
- Editor: slot allocation draws from every slot name;
  `_ensure_merge_input_slots` raises `input_slots` to cover connected slots
  after each Merge sync; input-port reads (connect, insert, typed-input
  reassignment, repair) use the backend resolver. Tombstone restore checks
  inputs per node (the type-level `_ports_by_type` table is gone).
- Node config: Branch rows are composed for `max(count, 5)` paths and
  mounted on demand when the count grows (labels of hidden paths are kept on
  save); "Choose 2 to 64 spawn points"; Merge capacity text uses every slot.
- Node card colours use the path index, so `path_f`+ cycle the palette.

**Behavior changes:** Branch accepts up to 64 paths; a Merge can close more
than five branches. Old saves: Branch and Merge behave exactly as before (five
slots, same names). Tests that encoded the five-path cap
(`test_branch_node_default_labels_are_configurable`, the P1 port-model
tests) now assert the new contract; the `FakeFactory` gained
`node_input_ports`.

**Checked read-only:** every workflow under `workflows/` validates the same on
this branch and on `main` (`wf_597a2a4f596f`'s two errors pre-date this work:
an Error Mux fed from Error Node's `default` port, and an input on a port
Error Node lacks).

## 2026-10-12 — P3a: Error Paths on Every Node in the Editor

Branch `dist/p3-error-path-and-branch`, from `main` at `57a0709` (P2, PR #40).
Before: 1022 passed. After: 1029 passed.

- `frontend/error_paths.py`: `editor_output_ports(factory, node)` is the
  backend's ports plus `error` when the node shows it — always for nodes that
  list `error` (HTTP Request, JSON Path), otherwise when config
  `show_error_path` is on or an `error` connection exists. The editor's
  `_output_ports_for_node` and node config's `_node_output_ports` use it, so a
  shown error path cycles, is selectable for add/insert (which auto-fills an
  empty Error Mux), and appears in branch selector rows.
- Node config Errors section: **Show error path in the editor** checkbox
  (hidden on nodes that list `error`), saved as `show_error_path` for every
  node type including Wait Until.
- Tombstone restore treats `error` as a port every node has (matching the
  validator), so a restored handler reconnects to its failing node.

**Behavior changes:** the Connections tab now has a focusable field, so
switching to it focuses the checkbox before Save
(`test_node_config_fixed_tabs_are_keyboard_navigable` updated to assert
that, then `s` reaches Save). Nothing changes for nodes that do not opt in.

## 2026-10-12 — P2: Error Mux Routes, Code Pickers and Auto-Fill

Branch `dist/p2-error-mux-routes`, from `main` at `49c5587` (P1, PR #39).
Before: 1000 passed. After: 1022 passed.

- **Routes (backend, `node_errors.py`).** `routes: [{id, label, codes}]` plus
  `unmatched_route`. `mux_routes`, `mux_output_ports`, `mux_route_for_code`
  (first listing wins, then `unmatched`), `mux_route_problems` (missing,
  reserved or repeated ids; a code on two routes), `error_codes`.
- **Error Mux** (spec change, regenerated, custom body restored; `check_node` /
  `check_ui` pass): class `output_ports` is `["unmatched"]`; ports come from
  `resolve_output_ports` (route ids) and names from the new
  `Node.describe_output_ports` (route labels).
  `NodeFactory.node_output_port_metadata(node)` and
  `declared_output_ports(type)` serve them; `output_display_name` uses them.
- **Migration** (`config_migrations`, `error_mux_routes_v1`): `path_a_codes`
  ... `path_c_codes` become routes `path_a`–`path_c` labelled Path A–C, so old
  connections and tests keep working; the old keys are kept as evidence.
- **Validator:** route problems and duplicate codes are warnings; unknown codes
  name the route label; an unconnected route with codes or an unconnected
  unmatched route is a warning; a connection on a deleted route is an
  undeclared-port error.
- **UI only** (`frontend/error_mux_ui.py`): codes from the node wired into
  `error` (its declared errors, then engine codes, then any code a route
  already lists) fill each route's code picker; an empty mux is prefilled with
  one route per code when its config opens, and when the editor wires an
  `error` port into it; **Refill from upstream** rebuilds the routes, keeping
  the id and name of any single-code route. `ObjectListField` gained
  `add_label` / `remove_label` / `id_prefix` / `refill_label` and
  `replace_rows`; file lists keep "Add file" / "Remove file".
- **Prune on save:** `WorkflowMap.prune_removed_output_connections(node,
  previous_ports)` drops connections on ports the save removed (deleted
  routes). Hidden Branch paths and already-invalid connections are untouched.

**Behavior changes:** Error Mux config is a route list (old configs migrate);
new muxes start with no outputs until routes exist; generated `<port>_label`
fields are limited to the type's declared ports.

**Self-review fixes:** the prune first ran on every config save and would
have silently removed already-invalid connections; it is now limited to ports
the save removed. Route ports no longer get generated `_label` fields.

**Open items:** the editor still offers `error` only on nodes that list it (P3);
auto-fill on wiring covers the editor's add/insert flow.

## 2026-10-12 — P1: Port Model, Ports Resolved by the Backend

Branch `dist/p1-port-model`, from `main` at `60b6f37` (P0, PR #38).
Before: 977 passed. After: 1000 passed.

- `Node.resolve_output_ports(config)` (classmethod; default: the class list)
  and `get_output_ports()` now use it. `BranchNode` overrides it with
  `branch_count_from_config` (moved from the UI, with `MIN_BRANCH_COUNT` /
  `MAX_BRANCH_COUNT`, into `backend/nodes/branch_node.py`).
- `NodeFactory.output_ports_for(type, config)`, `node_output_ports(node_data)`
  and `WorkflowMap.output_ports(node_id)`. Metadata `output_ports` is unchanged
  (the type's full list).
- Consumers switched to the backend: the editor's `_output_ports_for_node`
  (about 20 call sites) and Branch tombstone keep-selector; node config's
  `_node_output_ports`, generated port-label fields, downstream/vault port
  lists and transient (dead drop) rows; the editor's insert-between wiring;
  the tombstone restore source-port check and `_declares_output_port`.
- Validator: per-node ports. A connection on a port the type has but the
  config hides (a Branch path above its count) is a **warning** ("never
  runs"); ports the type never had stay errors. No saved workflow under
  `workflows/` has such a connection (checked read-only).

**Behavior changes:** the hidden-path warning; node config's dead drop rows for
a Branch list only its counted paths (overrides for hidden paths are kept on
save so raising the count brings them back); tombstone restore no longer
reconnects a connection from a Branch path the source now hides.

**Tests:** `tests/test_port_model.py` (23). The `FakeFactory` in
`test_debug_nodes.py` gained `node_output_ports` to match the factory API.

**Open items:** Merge has five fixed input ports (`path_a`–`path_e`) and the
Branch config rows use the same five; lifting Branch's cap (P3) must decide
Merge's capacity too. `test_refresh_coalescer` timing test failed once under
full-suite load (passes alone, with and without this change).

## 2026-10-12 — P0: Handled Errors Do Not Fail a Run (D10)

Branch `dist/p0-handled-errors`, from `main` at `0667520` (ESP32 slice, PR #37).
The owner approved the port-model spin-off P0–P3 ahead of step 4.

- **D10.** `ErrorHandler.log_error(..., handled=False)` adds a top-level
  `handled` flag to every error record. `Supervisor` now decides the error
  route *before* logging, so a failure routed along `error` is logged with
  `handled: true`; one that falls through to recovery or the policy is
  `handled: false`. `error_handler.unhandled_errors()` filters records
  (records without the flag count as unhandled).
- `RunResult.exit_code` returns 1 only for unhandled errors;
  `RunResult.unhandled_errors` and `to_dict()["unhandled_error_count"]`.
- `MasterState._record_run` deletes run files when there are no *unhandled*
  errors, and run history records `unhandled_error_count` beside
  `error_count`.
- `aotn run` summary: `1 error(s), 1 handled`.
- Plans: ESP32 row marked done; P0–P3 added to the DISTRIBUTED_BUILD_PLAN
  step table with a spin-off section; D10 in the decision record.

**Behavior change:** a run whose only errors were routed (for example the
failing ESP32 capture that notifies) now exits 0 instead of 1 and deletes its
run files. Errors are still logged and shown in the Errors view.

## 2026-10-12 — ESP32 Proof Slice: Binary-Safe HTTP, Run-Owned Files, Error Notification

Branch `dist/esp32-proof-slice`, from `main` at `f2c1677` (step 3, PR #36).
Before: 952 passed. After: 967 passed.

- **Run-owned temporary files (R4).** `RunSession.new_run_file`,
  `run_file_reference`, `keep_file`, `file_lifetime`; files live under
  `<data dir>/run_files/<run_id>/` (`persistence.RUN_FILES_DIR`, gitignored,
  created only when a run writes one). `file_refs.file_reference(path,
  lifetime=None)` and `reference_lifetime()`; absent lifetime means `kept`.
  `close_all(delete_run_files=...)`: `MasterState._record_run` deletes `run`
  files (and the empty run directory) only when the run succeeded — FINISHED,
  no errors logged, not stopped by the user — and keeps them otherwise.
- **HTTP Request** (spec change, regenerated, custom body restored,
  `check_node` / `check_ui` pass):
  - **Response as** (`response_mode`: `text` default | `file`): `file`
    streams the raw bytes into a run-owned file named after the node with an
    extension from the Content-Type, and outputs the `file` ref. Without a run
    session it fails with `node_error`.
  - **Keep the response file** (`keep_response_file`): marks the file `kept`.
  - **Body from** (`body_source`: `config` default | `input`): POSTs the
    node's input; text as `text/plain`, bytes as `application/octet-stream`,
    anything else as JSON (`application/json`, made JSON-safe).
- **Error to notification:** capture `error` → Error Mux (`http_status,
  network, timeout`) → HTTP POST with Body from `input`, which sends the
  versioned error payload.

**Done checks (`tests/test_esp32_slice.py`, local `http.server`):**

- A JPEG-shaped body (invalid UTF-8) is saved byte-for-byte as a run-owned
  `.jpg` under `run_files/<run_id>/`, and the ref is JSON.
- A 503 endpoint routes `http_status` (status, body) through the mux to the
  notification endpoint, which receives the JSON payload with `run_id` and
  `node_id`.
- Run files are deleted on success (directory removed), kept on ERROR, on
  FINISHED-with-errors and on Stop, and kept on success when marked `kept`.
- `aotn run capture.json --data-dir <tmp>` exits 0 and leaves no run files;
  the failing variant notifies and exits 1.

**Behavior changes:** none for existing workflows (new options default to the
old behavior; refs without `lifetime` are unchanged). `RunSession.close_all()`
without arguments keeps run files.

**Open items / risks:**

- A routed (handled) error still makes `aotn run` exit 1 (step 3 open item),
  so the failing capture run exits 1 even though it notified.
- `urlopen` runs on the event loop thread, so a slow camera blocks other
  branches of the same run (pre-existing for HTTP Request).
- A run-owned file deleted on success may still be named in run outputs; use
  Keep the response file when the file is the result.
- Interrupted processes leave run files behind (no sweeper yet).

## 2026-10-12 — Distributed Step 3: Error Codes, Error Mux, Errors Section, Skipped Status

Branch `dist/step-3-error-routing`, from `main` at `5e65265` (step 2, PR #35).
Before: 905 passed. After: 952 passed.

- **D7 codes** (`backend/node_errors.py`): `NodeError`, declared
  `error_definitions` (helper specs: `errors:`), the default generic
  `node_error` on every node, `engine.*` codes, and the versioned error
  payload (`version`, `code`, `message`, `node_id`, `run_id`, `stage`,
  `details`, `retryable`, `error_id` = the `ErrorHandler` record id). The
  payload lives on the transient store only. `ErrorHandler` records and
  `RECOVERY_OPTIONS_AVAILABLE` carry the code.
- **One engine-level `error` port.** Every failure (exception or a signal on
  `error`) is coded and logged once, then routes along a connected `error`
  port or falls through to recovery / the run's policy. The validator accepts
  `error` connections from any node.
- **Error Mux** (`error_mux_node`, helper spec): routes by code to path A/B/C;
  no matching code falls through. The validator checks its codes against the
  upstream node's declarations (plus engine codes) and flags a mux fed from a
  non-`error` port.
- **Helper**: `errors:` parsing/validation, emitted `error_definitions`, a
  generated codes assertion and a `ui_checks` Errors-section check. HTTP
  Request (`missing_url`, `timeout`, `network`, `http_status` with status and
  body in details) and JSON Path (`invalid_json`) declare codes; both were
  regenerated with custom bodies and tests restored. Wait Until and User Text
  Input list the engine codes they raise.
- **D8 Errors section** beside Connections (all config layouts, including Wait
  Until and branch/merge).
- **D9 skipped status** with reasons, spreading, run history
  `skipped_nodes`, logs, and `[skipped: <reason>]` on execution cards. Wait
  Until on an unreachable target fails with `engine.upstream_unreachable`.

**Interpretation notes (owner agreed 2026-10-12):**

- "One engine-level `error` port for every node" is implemented in the engine
  and validator; nodes do not list `error` in `output_ports` (the editor treats
  any node with several output ports as a branch). Wiring `error` from nodes
  that do not list it in the editor is an **open item**.
- A non-mux node connected to `error` receives every code (catch-all); only an
  Error Mux filters by code.
- A node whose error was routed is `failed` (not completed); its `default`
  target is skipped `not_taken`.

**Behavior changes:**

- The recovery **Skip** button no longer runs the next node with an empty
  input. Its downstream path is skipped until it rejoins something live.
- Untaken paths now show as skipped (`not_taken`, or `upstream_failed` /
  `upstream_skipped`) rather than having no status.
- A failure routed along a connected `error` port now carries the versioned
  error payload (a dict) instead of the node's message string, and the node
  is failed rather than completed.

**Tests:** new `tests/test_error_routing.py` (34) covering every test the plan
lists (linear spread, Merge with a live sibling, not-taken Conditional port,
error routing skips `default`, recovery Skip spreads, Wait Until on a skipped
target fails with `engine.upstream_unreachable`, mux fall-through to the
policy, skipped never completed) plus codes, payload, generator, Errors
section and validator checks; `tests/generated/test_error_mux_node.py`.
Updated for the logged behavior changes: two tests in
`test_execution_status.py` (Skip no longer runs the next node; the untaken
`end` is skipped) and one in `test_run_lifecycle.py` (the error port carries
the payload dict).

**Fixed after the adversarial review** (each with a regression test in
`tests/test_error_routing.py`):

- A mux or catch-all fed by several `error` connections read the first
  connection's slot, not the node that failed (empty or stale payload). The
  supervisor now remembers which node and port routed it to its current node,
  and an input port with several connections reads that one
  (`WorkflowMap.find_input_sources`). This also applies to ordinary ports fed
  by several connections.
- Non-JSON error `details` (e.g. bytes) or inputs broke the persisted
  `run_errors` file and stopped the run. Logged details and inputs now go
  through `node_errors.json_safe`.
- Skip spreading scanned the whole graph after every node (quadratic on long
  runs). A completed node that delivered to all its successors now skips the
  scan.
- A user Stop during a recovery prompt marked downstream nodes skipped
  `upstream_failed`. A user Stop (`RunContext.stop_requested`) no longer
  spreads skips. A failure that terminates the workflow (`_halt`) still does.

**Owner request during review: Error Mux "Pass along".** A path after an
Error Mux only received the error record, so the data the failed node was
working on was lost to the handling path. The mux spec gained a `forward`
select (`error` default, `failed_input`); the node was regenerated and its
custom body restored, and `check_node` / `check_ui` pass. Engine hook:
`receives_failed_input` on the node class (`node_errors.FAILED_INPUT`). The
error payload stays on the failed node's `error` slot either way. Tests:
`test_mux_can_pass_the_failed_nodes_input_down_its_path`,
`test_a_catch_all_node_does_not_get_the_failed_input`, and a generated-test
case.

**Open items from the review (not fixed, need a decision):**

- A routed (handled) error is still logged, so `aotn run` exits 1 for a run
  that handled its errors through a mux. Error records do not say whether an
  error was routed.
- Nodes on an untaken loop (or fed by an orphan node that never runs) are
  never marked skipped, because skipping waits for every source to be final.
  D5 waits still treat them correctly; only the displayed status is missing.
- Spread skip events use `visit_index` 0 on the branch that triggered them.
  Nothing displays per-visit data yet.

## 2026-10-12 — Distributed Step 2: Run Service, Policies, Data Directory, CLI

Branch `dist/step-2-run-service`, from `main` at `5749b9e`. Before: 866
passed. After: 905 passed.

- **Run service** (`backend/run_service.py`): load (saved id, saved name, or
  `.json` file; never touches `last_active_workflow_id`), validate, start with
  inputs and policies (**validates on start**), subscribe/unsubscribe, submit
  input or recovery, pause/resume/stop, wait, `RunResult` with shared exit
  codes. No frontend import.
- **`RecoveryPolicy` / `InputProvider`** (`backend/run_policies.py`, D1). The
  engine asks them when a run was started with them; otherwise the attended
  event-and-wait path is unchanged. Step 1's `unattended=` is now shorthand
  for `TerminatePolicy` + `NoInputProvider`. A policy that does not pause at
  breakpoints skips them. `UNATTENDED_ACTIONS`/`UnattendedInputError` moved
  here and are still importable from `backend.supervisor`.
- **Configurable data directory**: `AOTN_DATA_DIR` (or `--data-dir`) moves
  workflows, settings, secrets, logs and run records; unset, nothing moves.
  Persistence now creates missing parent folders.
- **Logging** moved to `backend/logging_setup.py`; the log file follows the
  data directory.
- **CLI** `aotn run <workflow>` (`aotn_cli.py`, routed from `main.main`): errors on
  stderr from `ERROR_LOGGED`, outputs on stdout (or `--json`), exit codes 0 /
  1 / 2 / 3 / 4 / 130, stdin policies when interactive, `--policy` (default
  `terminate_workflow`) when not, `--input KEY=VALUE` recorded on the run.
  Verified in a subprocess that no Textual module is imported.

**Deviations / notes:**

- The TUI still calls `MasterState`'s public methods rather than the run
  service, so its behavior (including no validation on start) is unchanged,
  as step 2's done-check requires. Moving it onto `RunService` is a later
  change.
- Run inputs are recorded on the `RunContext` only; the Start contract that
  consumes them is step 4.
- The engine still has no `STOPPED` workflow state (step 1 follow-up). The
  run service reports a stopped run as `STOPPED` (exit 130) in `RunResult`;
  run history still records it as `FINISHED`.

**Review fixes (independent diff review before merge):**

- Ctrl+C at an interactive CLI prompt hung the process: the stdin reader ran
  in the default executor, which `asyncio.run` waits for. Prompts now read in
  a daemon thread and are serialized, so parallel branches cannot interleave.
- A run ending in `ERROR` stored and printed no outputs; `MasterState` now
  captures the output log on the `ERROR` paths too.
- A provider raising `CancelledError` (its own future, not a stop) cancelled
  the supervisor and the run looked successful; it now fails the node. A
  recovery policy that raises is logged through `ErrorHandler` and ends the
  branch.
- Unloadable workflow files and unstartable workflows (`--no-validate`) exit
  cleanly (4 and 3) instead of with a traceback.
- `RunService` keeps only the current run's error list; the new tests write
  run records to a temporary folder; the CLI module is `aotn_cli` (not the
  generic `cli`).
- Provider-answered input now reports the node `waiting` while it waits.

**Behavior changes:**

- `aotn` accepts a `run` subcommand; plain `aotn` still launches the TUI.
- Data folders are created with their parents when missing.
- A run that ends in `ERROR` now records the outputs it produced in
  `run_outputs/` (previously only finished runs did).

**Tests:** `tests/test_run_service.py` (24) and `tests/test_cli.py` (15, CLI
runs in a subprocess against a temporary data directory, including Ctrl+C at
an interactive prompt on a pseudo-terminal).

## 2026-10-12 — Distributed Plan: Refresh Coalescer (Frontend Only)

Branch `dist/refresh-coalescer`, built in its own worktree alongside step 1b
and merged with step 1b's `main` (`41f2063`). Before: 860 passed. After: 866
passed. Only `frontend/app.py` and frontend tests changed.

- `NODE_EXECUTION_UPDATE`, `SUPERVISOR_STATE_UPDATE`, `NODE_TIMING_UPDATE`,
  `MEMORY_UPDATE`, `SUPERVISOR_REGISTER`, `SUPERVISOR_TERMINATING` update App
  state and mark the screen dirty; a 75 ms timer (`REFRESH_COALESCE_SECONDS`)
  refreshes once.
- `USER_INPUT_NEEDED`, `RECOVERY_OPTIONS_AVAILABLE`, `WORKFLOW_STATE_UPDATE`,
  `ERROR_LOGGED`, `ERROR_OCCURRED` act at once and flush. `WORKFLOW_DIRTY`
  (editor edits) also flushes, which keeps its immediate refresh.
- `App.flush_refresh()` is exposed for tests. With no running app the refresh
  stays immediate.
- Measured on a 32-node run with a mounted `ExecutionScreen`: 168 screen
  refreshes before, at most 10 after (proposal v2 Task 1 Case B).

**Behavior change:** during a run the execution screen updates at most every
75 ms instead of on every event; the final frame after a run is unchanged.

**Tests:** new `tests/test_refresh_coalescer.py` (6). Two mounted-screen tests
in `test_execution_status.py` now call `app.flush_refresh()` before asserting
a card changed, rather than relying on a refresh per event; their assertions
are unchanged. One unrelated run of the full suite saw
`test_error_details_navigation.py::test_error_buttons_have_keyboard_focus_and_scroll[True-140]`
fail once; it passed on six reruns, on both this branch and `main`.

## 2026-10-12 — Distributed Step 1b: RunContext, WaitRegistry, Delivery Tracking

Branch `dist/step-1b-run-context`, from `main` at `e39f5f7` (step 1, PR #32).
Before: 818 passed. After: 860 passed.

- **`RunContext`** (`backend/run_context.py`): one per run, holding the memory
  bank reference, `RunSession`, `WaitRegistry`, node timings, branch/merge
  groups, delivery tracking, live supervisors, `run_id`/`parent_run_id`, the
  unattended policy and the start time. Supervisors get callables bound to
  their own run. The Supervisor constructor only gained an optional
  `report_node_outcome` keyword. `MasterState.completed_nodes`,
  `node_timings` and `_run_session` remain as views of the current run.
- **`WaitRegistry`** (`backend/wait_registry.py`): tuple keys
  (`("node", id)`), sticky completion, wait-for-all on one Future, any
  unreachable key fails the wait at once, `stop()` gives waiters a `stopped`
  result. Merge is unchanged apart from its state moving into `RunContext`.
- **Delivery tracking + D5**: supervisors report each visit's final state and
  routed targets; pending wait keys are re-evaluated when a node finishes, a
  supervisor terminates or a wait registers. Never timeout-based.
- **Wait Until** fails with `TargetUnreachableError` naming the target instead
  of waiting forever. The code `engine.upstream_unreachable` comes in step 3.
- **Benchmarks (D6)**: `benchmarks/bench_linear_run.py` (5.04 events per node
  on a 200-node linear run, matching the Oct 9 figure) and
  `benchmarks/bench_wait_registry.py`. A test checks pytest collects nothing
  from `benchmarks/`. Proposal v2 Task 1 Case B (refresh rate with a mounted
  `ExecutionScreen`) is a frontend measurement and belongs to the coalescer.

**Interpretation notes (no decision reopened):**

- Proposal v2 was not available in the repo, so its WaitRegistry unit tests
  could not be copied; `tests/test_wait_registry.py` covers the behavior the
  plan specifies instead.
- The plan says 1b fixes the Oct 9 hang "where the target was terminated". A
  target that itself failed was reached, so the literal D5 incoming-connection
  test does not cover it. The rule therefore also treats a target whose own
  latest visit failed or was skipped, and that no live supervisor can reach
  again, as unable to complete.
- A source that never ran and that no live supervisor can reach is treated as
  settled (it can only ever become `skipped`, which D9 does explicitly in step
  3). Without this, a target two or more hops past a failure or an untaken
  port still hung; the independent review reproduced that.
- The memory bank stays the one shared instance the TUI displays (cleared per
  run); separate memory per run is part of step 6's parallel runs.

**Review fixes (independent diff review before merge):**

- Multi-hop hang (above).
- Outcomes are now reported after a node is marked completed, so evaluation
  never sees a finished node that is not yet completed.
- A branch refused by `max_branch_depth` counted as delivered; deliveries
  for branches are now recorded by `MasterState` only when the child exists
  (`SUPERVISOR_REQUEST_BRANCH` gains `source_node_id`).
- Recorded, not fixed (deadlock detection is beyond D5): a target reachable
  only through the parked waiter, and a Merge whose group includes the
  waiter's branch (that one also hangs on earlier code). Because Stop cancels
  tasks, a waiter in a real run sees cancellation; the registry's `stopped`
  result matters for waits that are not task-cancelled.

**Behavior changes:**

- A Wait Until whose target can no longer complete (failed and not
  re-reachable, no incoming connections, or every source finished without
  routing to it) now fails and goes to recovery (or the unattended policy)
  instead of waiting forever.
- When Stop is requested while a node is running, the supervisor discards the
  node's result and reports it `stopped` (it no longer routes the result or
  marks the node completed).

**Tests:** `tests/test_wait_registry.py` (17), `tests/test_wait_until_reachability.py`
(24: terminated target, source failure, two hops past a failure, untaken
Conditional port one and two hops, no incoming connections, depth-refused
branch, Merge before the target, a real loop, long wait behind a pending
input never failed, stale supervisor isolation, unattended Wait Until), and
`tests/test_benchmarks_not_collected.py` (3). The step 1 lifecycle tests'
Wait Until fixture now targets a node downstream of the waiter: its old
target had no incoming connections, which D5 now rightly fails at once.

## 2026-10-12 — Distributed Step 1: Bug Fixes

Branch `dist/step-1-bug-fixes`, one commit per fix. **Baseline on unchanged
`main` (`51c1f0c`): 796 passed.** After this step: 818 passed.

- **1a, error-port routing.** HTTP Request and JSON Path signal failures with
  `{"data": {"error": msg}, "output_port": "error"}`; HTTP Request also
  catches `TimeoutError`. The Supervisor turns a payload routed to an
  unconnected `error` port into a node error, so recovery runs. Both nodes
  were regenerated from their specs with the custom bodies and tests
  restored; the generated header gains `group`/`selector_section` from the
  spec (runtime identity is unchanged — `node_identity` already applied it).
- **1b-fix, Stop and leak.** `MasterState.stop()` cancels supervisor tasks
  after requesting stop, and `start_workflow` cancels and awaits leftover
  tasks before resetting state.
- **1c, unattended policy.** `start_workflow(unattended=None |
  "terminate_branch" | "terminate_workflow")`, passed to every Supervisor.
  Errors are logged and persisted, then the policy applies without waiting;
  input requests fail with `UnattendedInputError`; breakpoints are skipped.
  The TUI passes nothing.

**Behavior changes:**

- Saved workflows that previously continued silently after an HTTP Request or
  JSON Path failure now stop for recovery, unless their `error` port is
  connected.
- Stop interrupts a node that is executing or waiting (reported `stopped`)
  instead of only stopping at the next safe point, and releases Wait Until.
  A stopped run is still recorded as `FINISHED` (known follow-up: no
  `STOPPED` state).

**Review fixes (independent diff review before merge):**

- A supervisor task cancelled before its first step never published
  `SUPERVISOR_TERMINATING`, so the run stayed `RUNNING` and
  `wait_for_completion` spun without yielding (Stop right after Start; or
  `terminate_workflow` with parallel failing branches). Tasks are now pruned
  by a done-callback that re-checks completion.
- Two overlapping `start_workflow` calls could lose track of a live
  supervisor; starts are now serialized by a lock.
- Not fixed, recorded: cancelling does not stop work running in a thread
  (`asyncio.to_thread` in Chat Completion and File Output), and a Wait Until
  whose target can never complete still hangs an unattended run until step
  1b's unreachable rule lands.

**Tests:** new `tests/test_run_lifecycle.py` from the Oct 9 probes: error port
connected/unconnected/retry, HTTP timeout and URL errors, Stop releases Wait
Until, no wake-up leak into the next run (with and without Stop), and an
unattended run hitting an error, an input request and a breakpoint under both
policies. The Stop/leak tests fail on the previous code.

## 2026-10-12 — Authorize Distributed Plan Execution; Merge Plan To Main

Docs only. The owner authorized execution of steps 1, 1b, the refresh
coalescer, 2, 3 and the ESP32 proof slice. Each step lands as its own PR,
which the agent merges to `main` once the suite is green. The agents stop
before step 4.

Added `DISTRIBUTED_EXECUTION_PROMPT.md`, a copy-ready prompt for the next
session, and updated the plan, master plan and backlog status notes plus
README. The plan branch `ccr-1b2501bf-dgol6g` was merged to `main` by PR.

## 2026-10-12 — Record Step 1b And Step 3 Decisions (D5–D9)

Docs only; no code changes. Branch `ccr-1b2501bf-dgol6g`. The owner resolved
the open decisions in `DISTRIBUTED_BUILD_PLAN.md`:

- **D5, unreachable.** Structural and based on incoming connections, never on
  a timeout. A node is unreachable when every source of an incoming
  connection is final and none of them routed to it, and no live supervisor
  can still reach those sources. A required input that is never delivered
  stays a data error.
- **D6, benchmarks.** `AttackOfTheNodes/benchmarks/`, backend only, outside
  `tests/`.
- **D7, error matching.** Stable codes, with a default generic code on every
  node. Messages stay free text. A mux with no matching code falls through to
  pause (app) or the failure policy (headless).
- **D8, node config.** Keep the Connections tab and add an Errors section
  (confirms the 2026-10-09 recommendation).
- **D9, skipped status.** Skipped is its own status, with a reason. It counts
  as finished but never as completed, and spreads downstream until the path
  rejoins something live. Untaken paths are marked `not_taken`. A Wait Until
  whose target is unreachable fails with `engine.upstream_unreachable`.

**Design.** One delivery-tracking mechanism in `RunContext` serves D5 in
step 1b and D9 in step 3. Step 1b also fixes the Oct 9 Wait Until hang: Wait
Until now fails with a clear message instead of waiting forever.

**Behavior changes queued for step 3:**

- The recovery Skip button spreads the skip downstream instead of running the
  next node with an empty input.
- Untaken paths show as skipped.

Also updated: the `MASTER_BUILD_PLAN.md` step table. Step 1 still waits on the
owner's read of the plan.

## 2026-10-11 — Record Approved Distributed Direction Build Plan

Docs only; no code changes. Branch `ccr-1b2501bf-dgol6g`, based on `main` at
`32e9132`. The plan builds on the Oct 9 investigation and a review of the
WaitRegistry/Refresh Coalescer v2 proposal.

**Approved.** The owner signed off decisions D1–D4:

- providers instead of headless twins;
- triggers launch runs;
- subworkflows as child runs;
- `RunContext` extraction as step 1b.

They also accepted refinements R1–R4:

- step 1 is bug fixes only;
- the unattended policy is passed in at run start;
- per-trigger `single`/`queued` modes first, `restart` once Stop is clean,
  `parallel` at step 6;
- `file` reuse with run-owned temp files, kept when a run fails.

**Added** `DISTRIBUTED_BUILD_PLAN.md`. The wait-for-event node is recorded as
an open question with its tradeoffs, not as a decision.

**Superseded, not deleted:**

- `PROJECT_BACKLOG.md`: superseded banners on the headless twin, Start-node
  variant, nested headless validation, headless-export, watcher and
  completion-notify sections. The text is kept.
- `MASTER_BUILD_PLAN.md`: a step table, with the old Phase N/N+1/N+2 bullets
  kept under a superseded heading.

**Pointers and fixes:**

- Pointers in `AGENT_HANDOFF.md`, `README.md` and `TASK_INDEX.md`.
- Corrected the `NODE_CATALOG.md` Wait Until row (node completion, not a
  Vault key).
- Logged in `DOCS_MIGRATION_NOTES.md`.

**Corrections recorded in the plan:**

- Merge does not stall when a sibling branch fails (corrects the Oct 9 entry).
- `node_timeout_seconds` effectively bounds nothing.
- The backlog's cycle-rejection claim is wrong.

**Probes run during the review:**

- Wait Until hangs when its target was terminated or skipped.
- Stop does not release Wait Until, and a stopped run's waiter wakes inside
  the next run and writes into its memory.
- About 5 events per node, each causing a synchronous full screen refresh.

**Step 1 has not started.** It waits on the owner's read of the plan.
Verification: `git diff --check`, and relative links checked.

## 2026-10-09 — Investigate AOTN Distributed Direction Brief

Investigation only; no code or other doc changes. Started from `main` at
`32e9132` (PR #30). Checked the owner's distributed-direction brief (triggers,
workflow contracts, headless server, supervisor/router, AI inputs, `[error]`
type, error details tab, error mux) against code and docs. Full findings went
to the owner in the session reply; key code facts:

- Triggers, nested workflows, headless CLI and the multi-frontend API are
  already recorded as Phase 19/20 and Phase N/N+1/N+2 in MASTER_BUILD_PLAN and
  PROJECT_BACKLOG. The backlog makes the trigger watcher depend on headless and
  nested workflows. No separate rejection-record file exists in the repo.
- The backend runs without Textual installed (`demo_execution.py` finished).
  Headless runs block forever on any node error (recovery future), user input,
  or a saved breakpoint. `MasterState.start_workflow` does not validate.
- `http_request_node`/`json_path_node` failures write the `error` port but
  route via `default`. The node reports `done`, the run finishes, and a node
  wired to `error` never runs (scratch probe).
- "Dead-drop" and "transient" are synonyms in the docs and code; the second
  output kind is Vault. Config tab 4 is the read-only Connections tab, which
  WAIT_UNTIL_UI_PLAN marks "retain" and tests depend on.
- The backlog's "cycles are rejected by the validator" does not match the code:
  there is no cycle check. `node_timeout_seconds` only bounds Wait Until and
  Merge waits, not `execute()`.

No tests run (no code changed).

## 2026-10-09 — Publish Payload/File Routing PR

Owner confirmed the saved-workflow fixes live and requested a PR. Authoritative
root `/home/makin/src/node_workflow`, starting `main` at `1211e68`; fetched
origin/main and confirmed synchronization. Created `codex/payload-file-routing`
for the accumulated payload/file implementation and saved-workflow follow-up.
Preserved the unrelated Windows-path test file, `Workflow started` output,
and recovery-only checkout. Updated handoff publication status.

Fresh verification: **796 tests passed in 126.79s**; app/helper compilation
and `git diff --check` passed. Publish for review; merging is a separate step.

## 2026-10-08 — Fix Saved File Forwarding And Connected Text Output

Resumed the interrupted follow-up in `/home/makin/src/node_workflow`, `main`,
base `1211e68`. Fetched origin and confirmed already up to date before edits.
Changes remain uncommitted; preserved existing work and the recovery checkout.
Recovered the attached screenshot through `/mnt/c/Users/...` and inspected the
saved file-test graph read-only, without executing or modifying owner files.

Reproduced Writer's configured Content + incoming File Path connection: both
runtime and tracing assumed Content. Both now prefer connected Content and
fall back to connected File Path, preserving the actual incoming payload and
its provenance. A forwarding node without a connected source does not claim
its own result. UI labels follow the selected connected forwarding input.

Start now has one value editor in Parameters, with a read-only live value
preview in Payloads plus its routing controls. Old custom output-name overrides
no longer mislabel its greeting and are cleared on Save. Text Output now shows
selected source, template/label, captured-value preview and routing in Payloads.
Its existing any-input contract is intentional: values are formatted as text;
file references are displayed, not read. This is explained in the UI and tested.

The saved Wait Until was downstream of Text Output b2. Unconditional termination
introduced in the previous build prevented reaching Wait Until at all. Restored
Text Output continuation when connected, naturally ending when unconnected;
End remains an explicit stop. Branch-health traversal follows connected Text
Output nodes. This supersedes the prior unconditional Text Output termination
contract. No change to Wait Until's target/completion barrier was necessary.
The optional routing preference was unanswered; continuation was chosen to
restore the owner's demonstrated existing workflow, as stated during the work.

Verification: **796 full-suite tests passed in 127.58s**. Focused combined regression slice: 46 passed.
Existing Wait Until UI/runtime slice plus new UI/file tests: 38 passed before
continuation changes. New integration covers configured file writes on one
parallel branch and Text Output → Wait Until → File Reader on the other,
waiting for either Writer or its following Text Output, across save/reload and
two runs. Start/Text Output production-CSS mounts cover 60/100/140 columns.
Helper UI checks pass for Start, Text Output and Writer; all three specs were
regenerated in temporary projects, preserving custom runtime implementations.
Compile and whitespace checks pass. Earlier full-run failures were obsolete
Content-only label and terminal-output assertions, corrected to exercise the
new contracts; the integrated End completion log is now asserted explicitly.

Evidence: `docs/audits/payload_followup_2026_10_08/README.md` and
`tests/test_reported_payload_routing.py`. Owner workflows remain unchanged;
reopen/restart the app to load the updated implementation. Native Windows FO7,
line-number insertion and the unreproduced host-prefix issue are unchanged.

## 2026-10-07 — Complete Payload/File Build And Integration Audit

Continued the interrupted build in `/home/makin/src/node_workflow`, `main`,
base HEAD `1211e68` (origin synchronized during this build). All changes remain
uncommitted. Preserved existing edits, unrelated untracked files and the
recovery-only OneDrive checkout. Three agents implemented the file, runtime
and frontend tracks; the integrator finished their audits after usage limits.

Implemented the PAYLOAD_FILE_IO_BUILD_PLAN contract: File Manager rename and
multiple files with selected downstream reference/remaining typed Vault keys;
File Reader configured/upstream/Vault reference reads with independent text
publication; Writer string Content, prepend/append and opt-in newline escapes;
Start typed Vault output; Text Output source dropdown; accurate forwarding
previews/types; compatible source filtering and deleted-reference lifecycle;
explicit terminal nodes; Merge home/selected-sibling carry-forward and capacity
checks. Earlier Content/error-modal keyboard fixes remain included.

Shared audit fixes: actual legacy Vault capabilities gate controls, output
metadata identifies text/number producers, User Text Input declarations carry
string type, nested defaults are copied, and Vault-only outputs are excluded
from upstream choices. Saved file forwarding uses `transient_output=False`
to suppress the own result, not the forwarded input; both runtime and source
eligibility now preserve that distinction with regression coverage.

Versioned migrations preserve old values under `_config_migrations` and unknown
config keys. Retired file termination flags become continuation; End/Text Output
express terminal paths. Text Output legacy multi-key source selection requires
choosing one. Existing Reader configs remain Configured. See the build plan for
all migration details. Preserved the original Reader path tests in a dedicated
file after helper generation replaced the generated test file.

Verification: **784 full-suite tests passed in 121.97s**, including the full debug suite. Compile checks passed for app/helper and
`git diff --check` passed. Helper UI contracts passed for Reader, Writer,
Manager, Start and Text Output. Mounted production-CSS audit: 37 types in the
registry, 36 editable types, 108 mounts at 60/100/140 columns; 36/36 Cancel,
72/72 unrelated-config preservation, 72/72 repeated-save equality, 163
conditional states, no state exceptions. Both integrated home/sibling Merge
workflows pass, including save/reload, file/text Vaults, Reader/Writer,
terminal output, and deletion/undo. Earlier failed runs exposed obsolete UI
fixtures/error wording; updated tests retain their behavioral assertions.
Evidence: `docs/audits/payload_file_io_2026_10_07/`.

Remaining: numbered-line insertion is deferred. Native Windows/window placement
and owner's live terminal FO7 remain manual checks. The quoted Windows example
normalizes to its existing WSL path; the reported `makin@kelly:` prefix was not
reproduced and its origin is unconfirmed. No claim of live Windows verification.

## 2026-10-07 — Add Windows Copy-As-Path Investigation To Build Plan

Owner reported a quoted Windows path displayed as
`makin@kelly:/mnt/c/Users/makin/Documents/App_Tests/test.md` on execution.
Authoritative root `/home/makin/src/node_workflow`, `main`, HEAD `1211e68`;
origin/main synchronized. Preserved existing edits and unrelated files.

Read-only check of the exact quoted Windows input through normalize_local_path
returned `/mnt/c/Users/makin/Documents/App_Tests/test.md`; is_file was True.
No contents read or file changes made. Current converter does not construct a
user/host prefix, and FileViewerScreen displays the supplied path directly.
The expected WSL translation is verified; the reported prefix/UI symptom is
not reproduced and remains open.

Added P0a to PAYLOAD_FILE_IO_BUILD_PLAN and linked the concern in PROJECT_BACKLOG:
trace config/reference/event/display separately, preserve entered paths,
classify drive/UNC/POSIX forms with runtime OS rather than slash direction alone,
retain wslpath for actual mount mappings, and define extended/WSL-share/network
support and errors. Path tests must cover Save/reopen and complete execution,
not only the converter. File track owns this before new file-access features.

Existing Reader/path regression slice **61 passed in 0.11s**; this does not
establish coverage of every newly planned path form. Local plan Markdown links
and `git diff --check` passed. No runtime changes; documentation uncommitted.

## 2026-10-07 — Rename File Manager And Plan Reader Text Routing

Owner renamed File Viewer to File Manager and requested File Reader contents
as text transient/Vault payloads. Authoritative root
`/home/makin/src/node_workflow`, branch `main`, HEAD `1211e68`; origin/main
fetch/fast-forward merge up to date. Earlier dirty/untracked work preserved.

Changed the node's display name and new-node default alias to File Manager,
aligned its helper spec and existing generated metadata expectation, and updated
NODE_CATALOG. Internal `file_view_node`, viewer screen/event identifiers and
existing saved aliases remain intact. The node still displays one file until
the planned multi-file stage lands.

Existing FileReaderNode already reads a configured UTF-8 file into downstream
text. Extended PAYLOAD_FILE_IO_BUILD_PLAN with P2a to add typed file-reference
Upstream/Vault sources and independent typed string downstream/Vault outputs;
preserve old file_path/port identities, read-only behavior, empty-file handling
and current Windows/WSL normalization. Reader remains separate from Manager's
file-reference output. Updated track ownership, integration scenarios and
CONFIG_UI_BUILD_PLAN/MASTER_BUILD_PLAN/PROJECT_BACKLOG links. Reader extensions
are planned, not implemented; no duplicate Reader node added.

Verification: `check_node.py file_view_node` compiled the application and passed
**9 existing node tests**; `check_ui.py file_view_node` passed. Local Markdown
links and `git diff --check` passed. No new tests needed for the label-only
runtime change; no full-suite rerun. Changes uncommitted.

## 2026-10-07 — Plan Payload, Vault And File I/O Follow-up

Owner requested a coordinated build plan for forwarding preview/source-type
defects, Start/Text Output Vault controls, multi-file Viewer, Writer newline and
top/bottom insertion, completion-checkbox removal and Merge branch choices.
Worked in `/home/makin/src/node_workflow`, `main`, HEAD `1211e68`;
fetch/fast-forward merge origin/main up to date. Preserved earlier uncommitted
fixes and unrelated untracked files; recovery checkout untouched.

Investigated current code. Found legacy-only pass-through detection, first-input
tracing, Start's absent Vault write, Text Output's absent standard source/Vault
read, Writer Content declared any, empty-Vault-only source pruning, single-file
Viewer execution, file completion controls and selected-beacon-only Merge carry
choices. Noted Sleep forwards incoming data and `next_node_id: None` does not
stop connected traversal. These are code findings; exact owner graphs were not
live-reproduced. No application changes or agents launched in this planning task.

Created PAYLOAD_FILE_IO_BUILD_PLAN with P0–P6, shared type/provenance contracts,
separate frontend/runtime/file/integrator ownership, serialized shared-file
editing, multi-file declaration/execution rules, migration decisions, explicit
line-number TODO and behavioral/live verification gates. Linked it from README,
TASK_INDEX, CONFIG_UI_BUILD_PLAN, MASTER_BUILD_PLAN and PROJECT_BACKLOG. The new
owner terminal-node direction is identified as superseding the old optional
checkbox policy, with old-save migration to settle before implementation.

Documentation-only verification: local Markdown links and `git diff --check`.
No new application tests run; prior **686 passed** remains the last completed
implementation baseline. Plan and related documentation are uncommitted.

## 2026-10-07 — Hide Deleted File Producers From Vault Source Pickers

Owner reported deleted file-reference producers still offered as Vault sources
for new File I/O nodes. Authoritative root `/home/makin/src/node_workflow`,
branch `main`, starting HEAD `1211e68`; fetch/merge origin/main up to date.
Preserved all earlier uncommitted fixes, unrelated untracked file, and the
recovery checkout.

Found two causes: soft-delete is a frontend overlay, so scanning backend
configs counted deleted nodes as live writers; after tombstone materialization
or permanent removal, leftover Vault values were treated as external entries.
Editor now passes its workflow adapter to NodeConfigScreen. Writer declarations
use the adapter to recognize soft deletion and tombstones, retain original
keys with no active writer ids, and filter those keys from compatible source
options. A surviving eligible writer keeps a shared key available. Persisted
file entries without a current graph declaration are hidden even after full
removal or replacement. Vault data and tombstone restoration remain intact;
undo restores choices. External nonfile entries retain existing compatibility.
Saved invalid selections remain visible as not declared for repair; fresh
consumers do not offer those choices or an empty Vault source option.

Added 15 regressions covering Viewer/Writer producers before/after execution,
soft delete/undo, JSON save/reload and restore, permanent removal, replacement,
shared parallel keys, self/downstream exclusions after parallel deletion,
external nonfile values, and mounted editor-to-config Writer/Viewer/Window
Control source pickers with fresh and previously saved selections. Updated
NODE_STANDARDS eligibility documentation. Initial mounted tests accidentally
selected the editor's highlighted deleted row; fixed the fixture to select the
consumer's actual displayed row. Final new regression slice **15 passed**;
existing config/tombstone/Vault slice **35 passed**. Frontend compilation and
`git diff --check` passed. Full application suite **686 passed in 118.51s**;
final `git diff --check` passed. UI verification used headless Textual with
production CSS; live-terminal verification remains with the owner.
Changes uncommitted.

## 2026-10-07 — Reuse Same-File References And Clarify Output Labels

Owner confirmed the rewired workflow works, then asked to automatically reuse
a file reference used as input instead of suggesting incremental references to
the same file. Authoritative root `/home/makin/src/node_workflow`, branch `main`,
starting HEAD `1211e68`; fetch/merge origin/main up to date. Preserved all earlier
fixes, unrelated untracked file, and recovery checkout.

References already use resolved paths as identity, not incrementing counters.
File Writer now retains the actual source reference and resource key when it
writes the same file. This matches Viewer/Window Control reuse and preserves
noncanonical incoming keys. Create unique still returns a new reference when
it writes another file. Vault outputs keep the file reference even when
downstream forwarding emits Content; output remains usable by later nodes.

Shared file-output Payloads forms explain reuse and label the editable name
Display name. Additional Vault keys are explained as names for the same file,
not copies or versions. File Writer advertises its forwarded input in ui_hints
and its helper spec; the shared checkbox now explicitly names Content, avoiding
the misleading suggestion that selecting it is required to reuse File Path.
No automatic checkbox changes or disabling of downstream/Vault output.

Added 20 regressions: upstream/Vault references, repeated Overwrite/Append,
forwarding on/off, with/without RunSession, preserved keys/registered handles,
distinct Create unique file identity, reconstruction of a reference missing its
identity key, and mounted 60-column Writer/Viewer copy.
Updated Windows-path expectations to preserve incoming typed references while
still converting paths for actual file access.

Focused affected-file slice **95 passed**; Writer/Viewer UI helpers, compilation,
and `git diff --check` passed. First full run: **669 passed / 1 failed** in the
previously intermittent Settings navigation test. It directly moves focus and
toggles a checkbox without awaiting queued messages before switching tabs;
added a Pilot pause at that boundary. No Settings production code changed.
Final reference + Settings slice **21 passed**. Final full application suite
**671 passed in 116.26s**. Writer forwarding hint matches its normalized helper
spec; final `git diff --check` passed. Headless UI used production CSS; owner
live-terminal verification remains.
Changes uncommitted.

## 2026-10-07 — File Viewer Vault Reference And Downstream File Wiring

Owner confirmed Windows file access and reported File Writer failing to receive
File Viewer's reference. Requested default reference downstream unless forwarding
is selected, and an independent optional typed Vault reference accessible to
parallel branches. Authoritative root `/home/makin/src/node_workflow`, branch
`main`, starting HEAD `1211e68`; fetch/merge origin/main up to date. Preserved
all preceding fixes, the unrelated untracked file, and recovery checkout.

- Viewer already emitted a file reference by default. Added optional Vault
  output metadata/defaults and execution that writes the viewed reference with
  type `file`, independently of downstream forwarding. Updated its helper spec;
  reused standard Payloads controls without custom node-screen UI.
- Identified editor insertion always wiring the first input: File Writer
  Content, leaving File Path empty. Prefer a unique exact metadata type match;
  new typed non-first-input connections select Upstream in that input's source.
  Insert-between reconnection uses the same selector. Unknown/forwarded or
  ambiguous output types retain the existing first-input behavior.
- On configuration Save, move an inactive connection (its input now Configured
  or Vault) to a unique matching unconnected Upstream input. This repairs the
  existing Viewer→Writer Content misconnection when Content is Configured/Vault
  and File Path is Upstream. Preserve active Content wiring and configured paths;
  no automatic load/refresh migration or changes to owner's saved workflows.
- Added eleven tests: Viewer default/pass-through × Vault on/off, real
  Viewer→Writer execution after insertion and existing-config Save, preservation
  of intentional/occupied wiring, mounted production-CSS Vault controls/save/type
  declarations with forwarding on/off, and actual parallel Vault consumers.

Focused routing tests **11 passed**; existing Viewer/path tests **44 passed**.
Viewer node/UI helpers, normalized helper-spec optional Vault defaults,
compilation, and `git diff --check` passed. Final full suite **651 passed in
116.19s**. First full run had **649 passed / 1 failed** in the existing Settings
modal navigation test (late tab change); it passed in isolation and unchanged
in the final full run. Added occupied-port insertion preservation before that
final run. No Settings production changes were made.
Changes uncommitted; owner must restart and save the existing Writer config to
apply the connection repair.

## 2026-10-07 — Windows Copied Paths And Error Dialog Keyboard Recovery

Owner supplied two Error Details screenshots: File Viewer could not find an
existing Windows path under WSL, and File Writer reported an empty path. Both
dialogs lacked command navigation. Authoritative root
`/home/makin/src/node_workflow`, branch `main`, starting HEAD `1211e68`;
fetch/merge origin/main was up to date. Preserved the preceding Content editor
fix, unrelated untracked Windows-path-named file, and recovery checkout.

- File Writer and File Viewer now use the existing `normalize_local_path`
  service at execution, offloading WSL conversion to a thread. Quoted Windows
  Copy as path values work with Configured, upstream, and Vault sources;
  configured-path preflight uses the same normalization. Helper specs retain
  the matching schema hint without regenerating hand-written execution.
- Confirmed the exact screenshot's `test.md` exists at its `/mnt/c/...`
  equivalent. Executed the viewer node against quoted and unquoted copies:
  both completed and emitted the correct Linux path. Did not write that file.
- An empty selected path source remains an error. Writer now names the source
  and explains where to supply the path; no implicit source fallback was added.
- Error Details adopts CommandScreenMixin and vertically arranged buttons,
  human-readable recovery labels, and a scroll container. Deferred first focus
  reveals buttons after long-traceback layout; validation jump/Close controls
  share the behavior. App Back yields to Error Details so Ctrl+Q runs dismissal
  and clears the pending-error flag via the callback.
- Added 35 path tests covering sources, quoted paths, session/no-session,
  reference identity, preflight, conversion failures, and missing-source help.
  Added 15 production-CSS keyboard tests using the real app, three widths,
  long tracebacks, all recovery actions, dismissal callbacks, and validation
  jumps. Early tests exposed default App Ctrl+Q interception and initial scroll
  timing; final tests use the real app and deferred focus.

Verification: path/Reader/Writer/Viewer slice **91 passed**; error UI slice
**15 passed**; final full application suite **640 passed in 112.66s**.
Writer/Viewer node and UI helpers, compilation, and `git diff --check` passed.
Real WSL path/node verification passed; keyboard checks used headless mounted
production CSS, with owner live-terminal verification remaining. Changes
uncommitted.

## 2026-10-07 — Restore Visible File Writer Content Editing

Owner reported that File Writer Content appeared unable to enter editing after
selecting Configured in Source and switching to Parameters. Authoritative root
`/home/makin/src/node_workflow`, branch `main`, starting HEAD `1211e68`;
fetch/merge origin/main was up to date. Preserved the unrelated untracked
Windows-path-named file and left the recovery checkout untouched.

Production-CSS reproduction showed a two-row TextArea with zero content rows.
E correctly entered editing and accepted text, but the border-only layout hid
both text and cursor. Generated multiline/code fields now default to six rows
when their schema omits height; explicit schema heights retain their behavior.
No node execution or keyboard bindings changed. Documented the sizing rule.

Added a mounted File Writer regression at 60/100/140 columns and 24 rows:
enable Configured from Source, switch with 2, verify visible content geometry,
activate with E, type multiline text including navigation letters and a digit,
leave with Escape, navigate, and Save with the text preserved. Synthetic
workflow remains untouched until the caller applies the returned config.

Verification: focused regression passed; full application suite **590 passed
in 99.61s**. Compilation and `git diff --check` passed. Headless mounted tests
used production CSS; live owner-terminal verification remains. Changes
uncommitted.

## 2026-10-07 — Publish Confirmed Fixes And Synchronize

Owner confirmed the node UI fixes live and requested a PR and an up-to-date
project. Reuse existing PR #29 on `codex/wait-until-vault-fix`, which remained
open after fetching origin; main baseline `7161ef2`, starting HEAD `6b34303`.
Include the tested File Reader/path documentation and visibility/scroll audit
work in the integrated PR. Owner authorized merging and checkout synchronization;
GitHub and Git history record the resulting merge commit. Preserve the unrelated
Windows-path-named test file and the recovery checkout. Refreshed current agent
handoff with verified coverage and the remaining capability/layout work.

Verification before publication: 589 tests passed, final 108-mount audit clean,
compilation/helpers passed as recorded below; `git diff --check` passed.

## 2026-10-06 — Audit Every Editable Node For Visibility And Scrolling

Owner confirmed the preceding UI fix and requested a whole-node audit of
toggle-dependent controls, convenience reasons for retained information, and
scrolling. Authoritative root `/home/makin/src/node_workflow`; branch
`codex/wait-until-vault-fix`; starting HEAD `6b34303`, with preceding session
changes dirty. Fetch/merge origin/main was already up to date. Preserved those
changes and the owner's untracked Windows-path-named test file. No recovery
checkout changes, commit, push, PR merge, or new platform integration.

- Reviewed registered schemas/execution use and mounted all 36 editable types,
  including compatibility Start/End and excluding the internal tombstone.
  Reused owner-safe synthetic audit helpers with explicit production CSS.
- Added schema visibility for Text Output's user-input prompt, Set Variable's
  literal value, Conditional's variable name, and HTTP's POST body. Updated
  HTTP helper spec alongside the executable schema without regenerating its
  custom execution. No backend execution logic changed for these controls.
- Hide unavailable legacy Write to Vault checkboxes on both setter types while
  forwarding; no useful visible disabled choices remain in the audited states.
- Removed competing automatic/deferred scroll reveals. Shared focus helper
  supports caller-owned scrolling; Node Config opts out and reveals only its
  current focused target after layout. Other screens retain existing behavior.
  Guard against stale reveal requests and avoid scrolling outside the tab.
- Added NODE_CONFIG_VISIBILITY_SCROLL_AUDIT, before/intermediate/final evidence,
  reproducible audit runner with optional failure gate, and convenience reasons
  for read-only previews, wiring, empty states and still-active parameter fields.
  Updated README/TASK_INDEX, shared style standards and the UI build plan.

Final actual verification: **589 full-suite tests passed in 92.82s**.
**108 mounts**, **1,202 toggle/source states**, **4,008 navigation samples**,
Cancel unchanged **108/108**, **zero** final scroll findings, generated-rule
visibility mismatches, or visible disabled selectors/checkboxes. Explicitly
validated the saved final summary. Focused visibility/scroll tests: **17 passed**;
earlier affected-UI subset: 48 passed (overlaps). HTTP node helper/five tests and
UI helpers for HTTP Request, Text Output, Set Variable, Conditional passed.
Compileall app/helper and `git diff --check` passed.

Retained rapid-before scan's transient candidates rather than claiming 226 real
defects. Settled-before confirmed one Image Generation scroll failure and two
visible disabled checkboxes; intermediate three-width scan exposed two further
short-viewport failures in Conditional/Embedding. All are clear in the final
scan after consolidating the scroll path. Evidence uses synthetic populated
Vaults, 24-row headless WSL screens, and one-factor selector variants; it is not
exhaustive combinations or native/live accessibility verification. Unsupported
runtime Vault controls, empty tabs, simulated-AI options and platform capabilities
remain separately scoped in CONFIG_UI_BUILD_PLAN.

## 2026-10-06 — Hide Toggle-Dependent Config And Fix Initial LLM Scrolling

Owner requested hidden dependent configuration instead of disabled clutter,
and first-field focus without the initial LLM tab jumping to the bottom.
Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, starting HEAD `6b34303`. Fetch/merge origin/main
was already up to date. Preserved pending File Reader/docs edits and the owner's
untracked test file. This work remains local and uncommitted.

- Shared legacy Vault lists and empty-state messages hide until reads are
  enabled. Write count, label, and rows hide until writes are enabled. Keep
  hidden edited rows mounted so toggling back restores unsaved values.
- Hide standard downstream name/description rows when forwarding incoming
  data, and Vault key/description rows when output is disabled. Merge's carry
  selector, label, and details hide until a branch is selected. Hidden fields
  remain excluded from keyboard navigation and preserve appropriate values.
- Only changes on the focused widget may request scrolling, including the
  deferred callback. Initial/programmatic events no longer scroll toward
  unhighlighted fields. Config navigation reveals its current target without
  pre-scrolling to the next neighbour. First-field/tab focus remains intact.
- Added the general visibility and scrolling rules to UI_QUICK_REFERENCE;
  updated NODE_STANDARDS routing examples and CONFIG_UI_BUILD_PLAN. This is a
  focused stage-2 slice; stage-1 capability auditing and empty-tab cleanup remain.

Final verification: **580 full-suite tests passed in 86.24s**, including eight
new production-CSS UI tests covering Text Output and LLM at 60/100/140 columns,
toggle preservation, hidden navigation exclusion, Cancel preservation, initial
scroll position, non-focused changes, and routing visibility. Existing Merge
test now checks hiding/reappearance as branches are selected. Compilation and
Chat Completion/Text Output helper UI checks passed. Merge helper reports
structural UI is unsupported; the actual mounted Merge test passed instead.
`git diff --check` passed. An intermediate callback rename missed the selection
list handler; that failure was corrected before the final complete suite.

## 2026-10-06 — Owner-Confirmed WSL Fix And Future OS Support Direction

Owner confirmed the File Reader path fix works in the running app. Documented
WSL/Linux as the current development/debugging environment and Windows, macOS,
and Linux app versions as the intended future product direction in
PROJECT_KNOWLEDGE and PROJECT_BACKLOG. Nodes should adapt to actual runtime
paths and capabilities through platform adapters, with clear unsupported-operation
feedback and native verification before support claims. No packaging or additional
OS integration was implemented by this documentation change.

Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, HEAD `6b34303`. Fetched origin and merged origin/main:
already up to date. Preserved the pending File Reader changes and the owner's
untracked test file. Verification: `git diff --check` passed; no tests rerun for
this docs-only change. Prior actual full-suite result remains 572 passed.

## 2026-10-06 — File Reader Copied Windows Paths And Read Errors

Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, starting commit `6b34303`, initially clean.
Fetched origin and merged origin/main: already up to date. Changes remain local
and uncommitted; no PR merge or recovery-checkout changes.

- File Reader removes paired copied quotes and surrounding clipboard whitespace,
  expands home paths, and converts Windows paths using `wslpath` under WSL.
  Conversion during execution runs in a worker thread. Native Windows paths
  retain their normal behavior; incompatible Windows paths on other systems
  produce guidance rather than a misleading missing-file error.
- Schema opt-in `normalize_local_path` keeps pre-run validation consistent with
  execution without changing other file nodes. Missing files remain warnings
  because earlier nodes can create them. Empty, null-containing, incompatible,
  or unconvertible paths produce errors. Stored workflow config is preserved.
- Runtime errors explain missing files, folders, denied access, and non-UTF-8
  content. Both direct reads and RunSession handle reuse are covered.
- Verification: **572 full-suite tests passed in 72.29s**, including 26 focused
  File Reader tests. Helper `check_node.py file_reader_node` (including compileall)
  and `check_ui.py file_reader_node` passed. Real temporary Windows-drive file
  read under WSL passed quoted/unquoted with and without RunSession (four checks).
  Native Windows handling was simulated, not live verified. `git diff --check`
  passed. Legacy File Reader has no helper spec; its implementation was edited
  directly and its focused helper test added without regenerating the node.

## 2026-10-06 — Next-Session Project Rundown

Rechecked Git and GitHub: PR #29 open, unmerged and mergeable; main remains
`7161ef2`. Added SESSION_SUMMARY.md, corrected stale selector/AI/status roadmap
paragraphs, and linked the rundown from the docs entry point and handoff. This
is a docs-only follow-up on the same PR. No new runtime/UI changes or tests;
546-test integration result above/below remains the last actual full run.
`git diff --check` passed. Real Windows FO7 and remaining UI stages stay open.

## 2026-10-06 — Integrate File Output, Repair Audit Blockers, Prepare One Session PR

Authoritative root `/home/makin/src/node_workflow`; branch
`codex/wait-until-vault-fix`. Fetched origin/main `7161ef2`, already current.
Preserved prior dirty runtime/UI/tests/docs in checkpoint `1c4a57e`, then merged
File Output `0a19718` in `95f9049`. Resolved SESSION_LOG conflict by preserving
both histories. No recovery-copy changes, stash/reset, or automatic main merge.

- Added `SESSION_INTEGRATION_BUILD_PLAN.md` and `CONFIG_UI_BUILD_PLAN.md`,
  reconciled current handoffs/roadmap, retained original audit evidence and
  documented unresolved findings with priorities and follow-up verification.
- Integrated File Write, File Viewer, Window Control, Markdown formatting,
  typed file refs, optional Windows adapter and launcher work. Registry 37;
  actual selector 34; editable/user-facing 36; tombstone intentionally internal.
- Fixed arbitrary ambiguous window selection and nonunique title matches;
  offloaded blocking launch/discovery, kept resource registration on the loop;
  missing OS opener logs a warning after successful writing.
- File view events are scoped to the active displayed run and queued FIFO;
  input/recovery modal priority and retired-run queue reset are explicit.
  Updated mounted test that formerly specified dropping a second request.
- Removed Window Control's unsupported forwarding capability/control in spec
  and executable metadata. Kept its existing fixed selected-reference output.
- Shared save overlays existing config. Descriptions wrap beneath fields;
  stylesheet controls CommandInput width and labels leave input room.
  Wait Until remains Wait/Connections and never accesses the Vault.
- Added write-path schema intent, avoiding missing-input warnings for new
  destinations while retaining empty-required-path errors. Chat temperature
  zero reaches the provider unchanged. Helper specs match these metadata fixes.
- Added meaningful regression tests for ambiguous discovery, slow launch loop
  responsiveness, queued displays, config preservation, geometry and a real
  parallel File Write → Wait Until → explicit Vault File Viewer workflow.

Actual verification of the integrated tree:

- Final full suite: **546 passed in 71.26s**. Earlier full attempt: 544 passed,
  one expected-old-viewer-policy test failed; that test was updated to the new
  FIFO contract, passed narrowly, then the final whole suite passed.
- Focused initial checks: 94 passed; integration/Wait/Chat checks: 44 passed;
  final session regressions including parallel file/Vault: 15 passed; mounted
  viewer tests: 2 passed. These overlap; do not sum them as a baseline.
- Compileall app/helper and helper UI checks for File Write, File Viewer,
  Window Control and Wait Until passed. `git diff --check` passed.
- Current production-CSS audit: **108 mounts**, 306 alternate states, no state
  errors; Cancel unchanged 36/36; unrelated config retained and stable second
  saves 72/72; variant roundtrips **115/115**, zero mismatches. Nine focused
  fields fit at 60/100/140. Synthetic data only; no owner workflows/settings.
- Evidence under `docs/audits/integrated_2026_10_06/`; before-fix artifacts retained.

Outstanding: capability-gating legacy Vault controls, broader tab/layout cleanup,
other schema/numeric/routing descriptions and port issues recorded in
CONFIG_UI_BUILD_PLAN; unsupported-window explanations/validation and Windows FO7
live owner checks. File Reader still uses configured paths. Large file work,
window heuristics and complete live accessibility remain unverified. No broad
UI redesign or new node behavior was silently introduced.

Published one session PR: [#29](https://github.com/makinster/node_workflow/pull/29),
“Integrate file workflows and fix Wait Until/configuration UI blockers,” targeting
main. Verified feature/main ancestry, pushed `5f944de`, and attached the PR to
this chat. This publication record is a final docs-only commit on the same PR.
Main remains unchanged pending PR review.

## 2026-10-06 — File Output Integration Review

Reviewed fetched `origin/claude/file-output-pywin32-32tnv9` at `0a19718`
against authoritative `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, HEAD/origin-main `7161ef2`, including dirty
runtime/Wait Until code. Preserved existing work; no application edits,
feature merge, checkout switch, stash, commit or push.

- Added `FILE_OUTPUT_INTEGRATION_REVIEW.md`: architecture fit, current UI
  inventory, six prioritized findings, integration order and explicit limits.
- Git merge-tree found only SESSION_LOG conflict between committed branches.
  Temporary three-way Python source overlay found no conflicts against actual
  dirty files; it preserved pending runtime fixes and current chat resources.
- Corrected source-overlay verification: **304 passed in 59.16s**, including
  feature-changed tests and both pending Wait Until suites. This is not an
  installed merged-tree/full-suite baseline. Initial harness configuration/CSS
  path errors were corrected; they were not application regressions.
- Mounted three incoming config screens at 60/100/140 × 24 with production CSS;
  nine mounts, all four tabs captured, combined registry 37. This extends review
  evidence but does not replace exhaustive conditional/keyboard/save audits.
- Deterministic ambiguous-window probe selected HWND 202 despite no title match:
  document as P1 along with blocking synchronous launch polling. No real window
  opened/controlled. Other findings: dropped viewer requests, ineffective Window
  Control forwarding toggle, platform explanations and writer-path warnings.
- File Reader still only accepts a configured path; typed-reference consumption
  is an explicit future scope decision. Wait Until still has no Vault behavior.
- Evidence/harness: `docs/audits/file_output_2026_10_06/`. `git diff --check`
  passed. Windows FO7 protocol, actual integrated full suite and exhaustive new
  node interaction audit remain outstanding. Owner display-policy choice remains.

## 2026-10-06 — Pending Work Review Before Configuration Build Plan

Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, HEAD `7161ef2`. Fetched origin and merged
origin/main: already current, zero divergence. Existing uncommitted changes,
audit artifacts and recovery checkout preserved; no application code changed,
no commits/pushes/feature merges made in this review.

- Reviewed pending answer-Vault publication, transient-before-completion ordering,
  stopped-input cancellation, W/S typing, zero-timeout semantics, Wait/Connections
  composition, target/timeout validation, Save/Cancel and helper adaptation.
  Reviewed both new test files and pending design/standards/audit documents.
- Added PENDING_CHANGES_REVIEW.md with file-group dispositions and remaining
  readiness limits. No additional runtime defect confirmed. Wait Until's
  production-CSS timeout clipping (audit F03) prevents visual sign-off despite
  green functional tests; keep the focused design and fix shared sizing later.
- Inspected fetched File Output feature `0a19718` read-only: nine feature-only
  commits and nine main-only commits, 48 changed files. Adds File Write, File
  Viewer, Window Control and Markdown mode; removes File Instance demo. FO7
  Windows checks remain pending on that branch. This was an integration-impact
  check, not full validation of that feature; no separate checkout or merge.
  GitHub PR status unverified because gh is unavailable.
- Updated current handoff, roadmap, backlog and documentation routes to the
  configuration build-plan checkpoint; retained historical entries/proposals.
  Flagged File Output baseline selection before finalizing a build plan and
  linked the existing audit/Wait Until plan to the reviewed state.
- Fresh verification: full `pytest tests/ -q` **445 passed in 64.00s**;
  compileall for app/helper passed; `check_ui.py wait_until_node` passed;
  local documentation links and git diff --check passed. No owner live UI or
  Windows verification claimed. Pending work remains local and uncommitted.

## 2026-10-06 — Configuration UI Audit and Staged Plan

Branch: `codex/wait-until-vault-fix`, starting/current HEAD `7161ef2`, authoritative
`/home/makin/src/node_workflow`. Fetched origin and merged origin/main: already
up to date. Preserved all 18 initially modified and five untracked files; no
runtime/UI implementation edits, commits or OneDrive recovery changes.

- Added NODE_CONFIG_UI_AUDIT.md: all 35 registered types, 32 selector-visible
  types, group/mode coverage, current/recommended controls, 12 prioritized
  findings, deliberate exclusions/history, reusable fixes and six small stages.
- Mounted 34 configurations (including automatic Start and legacy End; intentional
  Tombstone exclusion) at 60/100/140x24 using production styles.tcss. Captured 102
  width records, 278 alternate states, 68 default save/reopen mounts and 87
  additional changed-mode/routing save/reopen cases. The 87 selected values all
  persisted; all 34 Cancel cases left stored data unchanged. Default second-save
  results were stable, but unrelated config survived only on Wait Until (33/34
  other screens lose it). Assertions document defects, not expected future behavior.
- Confirmed unsupported generic Vault controls, registered File Instance demo
  stub exposure, shared save-key loss and off-screen inputs under production CSS.
  Wait timeout starts at x=80 at 60 columns; CommandInput's inline 100% width and
  inline descriptions defeat row sizing. Existing bare-App tests miss this.
- Additional findings cover irrelevant conditional fields, empty/duplicate tabs,
  ignored Random Number Payload, numeric coercion, Chat forwarding/blank keys,
  unused simulation credentials, inaccurate Echo/Repeat descriptions and helper
  contract gaps. Fake-provider probe confirms Chat temperature 0 is sent as 1.
- Retained scripts, complete control inventory, compressed raw evidence and
  terminal text/SVG receipts under docs/audits/node_config_2026_10_06. Updated
  README and TASK_INDEX routes without replacing preceding session edits.
- Verification: Python 3.14.4/Textual 8.2.7; focused pytest command covering
  test_wait_until_ui.py, test_chat_completion_node.py, test_node_helper.py,
  tests/generated and test_debug_nodes.py: **232 passed in 55.27s**. Audit scripts
  compiled; packaging coverage assertions, local Markdown links, matrix coverage,
  and git diff --check passed. No new full-suite result claimed.
- Limitations recorded: one-factor alternate states rather than exhaustive
  combinations, no full per-field live keyboard/accessibility sign-off, no real
  providers, and no per-node disk export/reload audit. Owner live review and demo/
  termination/Chat contract decisions remain; broad implementation has not begun.

## 2026-10-06 — Wait Until Focused UI and Shared Section Standard

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; fetched origin/main,
merge already current. Preserved preceding runtime fixes/design documentation.

- Implemented Wait + Connections tabs: alias, graph-derived targets, timeout,
  unchanged dead-drop explanation and read-only route; removed Vault reads/writes,
  payload reveals and editable output metadata from Wait Until.
- Bounded target list, explicit unavailable-target rows, selected-count/empty
  hints, list-boundary keyboard movement and per-tab focus/scroll restoration.
  Save rejects invalid/non-finite/negative timeouts and invalid selected targets.
- Save preserves unrelated config and clears retired Wait Until membank/transient
  declarations; opening/Cancel does not mutate workflow config. SaveManager's
  existing derived input_sources calculation removes stale Vault read claims.
- Updated NODE_STANDARDS, UI_QUICK_REFERENCE, TUI_DESIGN, AGENT_START_GUIDE and
  NODE_HELPER: shared section meanings, only applicable controls/tabs, consecutive
  number navigation, flat/focused forms allowed. Other node layouts unchanged.
- Updated Wait Until UI plan, task routes, roadmap/handoff and helper UI check
  for timeout's placement in Wait. Initial full run caught an omitted Ctrl+Q revert
  hint; restored it before final rerun.
- Added 12 mounted regressions covering 60/100/140-column layouts, long-list
  navigation, tab focus/scroll, typed letters/digits, unavailable targets,
  timeout validation, toggle/no-target cases and save/cancel configuration.
- Focused execution/UI suites **52 passed**; check_ui.py wait_until_node,
  compileall, git diff --check and local documentation-link checks passed.
  Final full suite: **445 passed in 63.03s**. No owner live UI
  confirmation yet; restart app for the configuration change. Uncommitted.

## 2026-10-06 — Wait Until Configuration UI Plan

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; fetched origin/main,
merge already current. Preserved all prior dirty runtime/design work.

- Mounted current Wait Until screen to inventory controls across all four tabs.
  Legacy generic composition exposes unsupported Vault reads/writes, previews
  and output metadata; help copy incorrectly advertises A/D tab navigation.
- Proposed two tabs (Wait, Connections), targets and timeout together, fixed
  pass-through explanation, keyboard/list navigation and responsive scrolling.
- Specified explicit stale-target handling, no-target immediate pass-through,
  save-only removal of obsolete Vault declarations and derived source refresh.
- Added WAIT_UNTIL_UI_PLAN.md and documentation routes. Design only; config UI
  remains unchanged. Verification: mounted inventory, git diff --check and local
  Markdown links passed. No runtime suite rerun for this docs-only task.

## 2026-10-06 — Wait Until Zero Timeout Means Forever

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; origin/main already current.

- Owner confirmed the cross-branch flow works live after the input fixes and
  requested 0.0 mean wait forever and remain default. Previously zero became
  None and Supervisor substituted the global timeout. Pass zero explicitly;
  positive values still enforce a limit. Updated Parameters description.
- Extended four cross-branch LLM cases with zero/positive timeout variants and
  a shorter in-memory global timeout to prove zero does not inherit it.
- Focused new/execution suites **40 passed in 7.21s**; compileall and diff checks
  passed. Prior full suite **429 passed** before this timeout edit; not rerun.
- Initial test setup mistakenly persisted a 0.005 global timeout. Test now uses
  monkeypatch on the in-memory cache; local global timeout restored to 30 seconds.
  The prior custom value was not captured. Other settings retained.

## 2026-10-06 — User Input Dialog Drops W/S While Typing

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; fetched origin/main,
merge already current. Existing dirty design/runtime work preserved.

- Owner reported continued-session missing context at node_8ec97b0a. Exact saved
  workflow diagnostic using fake provider held the second LLM until input, wrote
  `user_text`, and completed both calls successfully. Running app was canonical
  and started after the earlier Vault fix; stale code was not assumed.
- Mounted dialog reproduction found auto-edit input treats W/S as navigation
  while editing: a single w/s yielded empty input and sentences lost characters.
  This can cause the reported error; owner's exact typed answer/timing remains
  unconfirmed. Backend-only tests missed this keyboard path.
- UserInputScreen explicitly starts ordinary text editing on mount. W/S now type
  during editing; command navigation resumes after edit. Shared auto-edit behavior
  for other screens remains intact. No saved workflow or live process modified.
- Added four mounted typing/submission regressions: all failed before the change,
  all pass afterward. Focused suites **36 passed**; full tests/ **429 passed in
  52.25s**; compileall and git diff --check passed. Updated investigation/handoff.
  App restart required to load the new UI code; no live owner verification yet.

## 2026-10-06 — Cross-Branch User Input Vault Fix

Branch: `codex/wait-until-vault-fix`, based on merged main `7161ef2`;
fetched origin/main and merge was already current. Preserved uncommitted branch
UI design/investigation docs from the preceding work. No saved workflow edits.

- Owner confirmed the User Text Input -> Wait Until -> cross-branch LLM case.
  Saved LLM already reads Document/Context from Vault `user_text` while continuing
  an AI session; configured input declarations previously never wrote that key.
- UserTextInputNode copies the answer to declared legacy Vault keys before success,
  supporting output/id aliases and tagging the values as strings. Dead-drop answer
  remains available. Supervisor publishes transient output before completion gates.
- Stop cancels the pending input future rather than injecting an empty answer;
  interrupted prompts cannot publish output or satisfy the completion registry.
- Added 11 regressions: list/string wait targets, fresh and continued LLM calls
  using a fake provider, legacy declarations, genuine empty answers and stop.
  Before fix: 11 failed, including completion observed before data publication
  and stopped input incorrectly appearing in completed_nodes. After fix: all pass.
- Verification: focused new/execution tests **32 passed**; full tests/ **425 passed
  in 49.81s**; compileall, git diff --check, local documentation links and
  check_ui.py user_text_input_node passed. check_node.py compiled but could not run
  its expected generated test because this legacy node has no helper spec/generated
  test file; focused real runtime tests and full suite cover the change instead.
- Updated execution contract, investigation and handoff. No real LLM calls or
  owner live verification yet. Changes remain local and uncommitted.

## 2026-10-06 — Wait Until / Vault Investigation

Branch: `codex/execution-branch-ui-design`, base `7161ef2`, synchronized with
origin/main. Preserved existing uncommitted branch-UI design documentation.

- Reproduced two parallel branches with an unanswered User Text Input target.
  Wait Until held its branch until the answer; downstream reader did not start.
- After answering, target transient output existed but configured `user_text`
  Vault declaration was never written; downstream Get Variable returned missing.
  Generic membank declarations have no runtime application in Supervisor.
- Read-only local workflow inspection found a matching candidate. No live LLM
  calls, saved workflow edits, runtime changes or symbol changes.
- Recorded evidence and proposed focused fix in WAIT_UNTIL_INVESTIGATION.md.
  Existing cross-branch test: 1 passed, 153 deselected. Real runtime diagnostic,
  git diff --check and local Markdown links passed. Full suite not rerun.

## 2026-10-06 — Execution Branch UI Design

Branch: `codex/execution-branch-ui-design`, starting from clean main `7161ef2`
(merged PR #28). Fetched origin; main matched origin/main; merge already current.

- Reviewed retained branch/visit/attempt state, execution screen navigation,
  Supervisor payload handling and OutputManager finalization.
- Proposed A/D wrap, stable runtime labels, actual-visit rows, queued-node row,
  independent scroll/selection/follow and attempt details; proposed S navigation
  with X stop to resolve the current binding conflict.
- Defined selected-visit summaries and branch counts, opt-in bounded safe
  descriptors with explicit attribution, and shared run-wide durable output.
  Recorded current IDLE reset limitation and barriers' observability limits.
- Added EXECUTION_BRANCH_UI_DESIGN.md and routed handoff/index/backlog to it.
  Application unchanged. Verification: git diff --check and local Markdown links
  passed. Prior 414-test result remains historical; no runtime tests rerun.

## 2026-10-06 — Owner Confirmed Execution Symbols; PR #28 Review

Branch: `codex/execution-symbol-investigation`, fix `a31900d`, handoff `1f7ac2c`.

- Owner confirmed the execution-symbol fix works live and requested PR work
  before starting the next chat. Recorded confirmation and merge authorization.
- Reviewed the fix diff; automated validation remains 414 passing tests.
  No implementation changes in this follow-up; git diff --check passed.
- Updated build plan and next-chat handoff: use fetched main once PR #28 is
  merged, then design branch navigation/output summaries. Recovery/modal edge
  cases have automated coverage; owner confirmation specifically covers symbols.

## 2026-10-06 — Execution Status Fix Implementation (ES0–ES3)

Branch: `codex/execution-symbol-investigation`, continuing `fa91bd0` and
investigation `20d58c7`, based on fetched main `8ada5b2`. Canonical WSL checkout.

- Added NODE_EXECUTION_UPDATE with run/branch/node/visit/attempt/status facts;
  expanded supervisor position/provenance and timing identity. Report each
  execution, retry, input wait/resume, successful/failed/skipped/stopped outcome.
- Replaced frontend success guesses with ExecutionDisplayState. Retain ended
  branches and visit/attempt timing/history; derive independent branch statuses
  and a deterministic global summary. Ignore stale/retired runs and clear the
  cache on workflow replacement.
- Preserved failed outcomes through termination/cancellation, and safe-point
  successes through stop. Corrected SKIP marking the next node completed before
  it executed; regression asserts completion registry behavior.
- Refresh run view after modals; update stable cards in place to retain scroll
  and selection. Skipped/stopped use text labels without success checkmarks.
- ES0 regression cases failed on original code (5 failed); now 21 execution
  checks pass covering linear live/final rendering, parallel shared nodes,
  retries/repeat visits, recovery, user input, cancellation, barriers, pause,
  stale events, workflow replacement and three terminal widths.
- Final verification: `pytest tests/ -q` **414 passed in 49.74s** (includes all
  154 existing debug tests); focused execution suite **21 passed**; compileall;
  git diff --check; local Markdown link checks. No live owner confirmation yet.
- Current implementation recorded in EXECUTION_STATUS_CONTRACT.md. Updated
  plan/roadmap/backlog/UI routes and NEXT_CHAT_HANDOFF.md. Future A/D branch
  view, scrolling and output summaries remain a separate design/layout task.
- ES4 automated work complete; owner live check and review/merge remain.
  Implementation commit `a31900d` pushed; draft PR #28 opened at
  https://github.com/makinster/node_workflow/pull/28 (not merged).
  NEXT_CHAT_HANDOFF.md records exact state and next-chat instructions.

## 2026-10-06 — Execution Fix Build Plan and Future Branch UI

Branch: `codex/execution-symbol-investigation`, continuing investigation commit
`20d58c7` from fetched main `8ada5b2`. Documentation only.

- Added `EXECUTION_STATUS_BUILD_PLAN.md`: ES0 regression cases, ES1 explicit
  lifecycle facts, ES2 branch-specific display state, ES3 rendering/resume,
  ES4 verification and handoff. All stages pending; no application fix made.
- Recorded owner direction: A/D cycles execution branches, scrollable node
  lists per branch, and output-summary UI in a separate future task/PR.
- Defined preparation for branch/visit identity and completed-branch retention;
  documented output-summary attribution/retention and layout decisions still
  requiring design. Preserve runtime semantics and current glyph meanings.
- Linked investigation, README, task index, master plan, handoff, backlog and
  TUI design so subsequent work finds both immediate and future scope.
- Verification: documentation link/heading review and `git diff --check`.

## 2026-10-06 — Execution Symbol Investigation and Proposed Plan

Branch: `codex/execution-symbol-investigation`, based on fetched main `8ada5b2`
in `/home/makin/src/node_workflow`. Investigation and docs only.

- Reproduced missing per-node supervisor events: Start -> Sleep -> Sleep -> End
  executes fully but leaves the latter three nodes idle in App's status cache.
- Reproduced error status overwritten as done on branch termination, and a
  mounted ExecutionScreen remaining stale after a modal closes.
- Documented event -> cache -> rendering behavior, current symbol meanings,
  safe-point pauses, barrier waits, timing, run-scoping and concurrent-visit gaps.
- Added `EXECUTION_STATUS_INVESTIGATION.md` with a staged correctness fix plan
  and guidance for the upcoming execution UI redesign; linked docs/task routes.
- Verification: real-run event/cache probes, mounted Textual modal probe;
  existing focused debug tests 5 passed, 149 deselected; git diff --check.
- Owner clarified that completed nodes retain circles instead of checkmarks,
  matching the reproduced missing-transition defect. No application fix
  implemented; proposed implementation/design decisions recorded for follow-up.

## 2026-10-06 — Chat Completion Config Opening Delay

Branch: `codex/chat-config-opening-lag`, based on fetched `origin/main`
`af04c5f`, in `/home/makin/src/node_workflow`.

- Profiled the mounted Chat Completion config interaction: repeated dynamic
  rule passes traversed the entire widget tree for each field/label/row.
- Changed shared form-rule application to build one widget-id lookup per pass,
  preserving conditional visibility, enabled state, required labels, section
  titles, and forced select values. Rebuild each pass to reflect DOM changes.
- Added a traversal-count regression assertion to the mounted Continue AI
  session test; existing tests cover repeatable context and source choices.
- Same cProfile test before/after: rule processing 7.664s -> 0.093s;
  pytest duration 11.08s -> 2.25s. These include profiling overhead and are
  automated interaction timings, not live-terminal opening measurements.
- Verification: compileall; focused config/form tests (32 passed, 122
  deselected); full debug suite (154 passed); node-helper tests (14 passed);
  git diff --check. Owner confirmed the fix in the live app on 2026-10-06
  after local implementation commit `de04338`.
- Local fix only; no push or merge into main.

## Older Entries

See [Session Log History](archive/SESSION_LOG_HISTORY.md).
