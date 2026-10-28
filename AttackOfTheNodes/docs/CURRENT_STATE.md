# Current State

Snapshot checked **2026-10-28**, against fetched `origin/main` `19640f9`
after #134 merged. Revised workflow designer Step 1 is built for review on
`codex/draft-workflow-step1`; earlier entries retain their dated scope.
No real model/API calls in this change. Code and fresh checks take precedence.
This is the live status snapshot; plans and logs preserve dated decisions.
Live deployment facts below come from the owner's shared notes and confirmed
delivery; this documentation refresh did not change or rerun live jobs.

PR #134 review fixes (2026-10-28) correct doubled cache-read estimates for
Sonnet/Opus and document the 512-token minimum prefix. Per-model price tests
and real-engine run summaries cover all three supported models. See the latest
Session Log entry for verification: full `pytest -n auto` passes **3,234 tests
in 35.63 s** after the review fixes.

## PR #135 route review — 2026-10-28

On `codex/draft-workflow-step1` from `48959db`: oracle v3 now freezes
role/producer/route obligations for every case and checks them with one common
matcher. Parallel paths may swap their assigned operations, but every path must
do its own declared work. Conditional cases 7/9 require their work on the
corresponding route. Data lineage identifies the actual producing node, while
dominance and exclusive reachability prevent hoisted, shared or borrowed work.
Calibration: 22 good/bad pairs. Focused checks: **96 passed in 6.83 s**;
full `pytest -n auto`: **3,330 passed in 44.60 s**. Final standalone mock
batch passes all ten cases, 21 target fixtures and 22 calibration pairs.
No real calls or Secrets access.

## PR #135 review fixes — 2026-10-28

On `codex/draft-workflow-step1` from review head `4b42912`: prepared roots are
validated recursively before writes/backend imports, including exact marker
contents and rejection of links/special entries. Oracle v2 tracks complete
input/operation and conditional-control provenance; new regressions cover the
hardcoded heading and three partial-file reconstructions. Calibration is now
19 paired fixtures; trial tooling and tests use multiline control flow.
Focused tests: **78 passed in 6.09 s**. Full `pytest -n auto`: **3,312 passed
in 41.56 s**. Standalone mock batch: ten cases, 21 target fixtures and all
19 calibration pairs pass their expectations. Docs/whitespace checks pass.
No real model/API calls or Secrets access.

## Revised workflow designer — 2026-10-28, Step 1 built for review

Own worktree `/home/makin/src/nw-draft-workflow-step1`, branch
`codex/draft-workflow-step1`, clean base `19640f9`. Approved external plan
`/home/makin/src/agent_channel/draft-workflow-plan-2/` decisions 1–14:
existing-node clarify/draft/check/meaning-review/save gate, 12-type static
palette, external frozen-case evaluator and ordered RunService InputProvider.
No app/backend changes or old-spec edits. All ten canned cases and 21 target
fixtures pass; 15 calibration pairs accept good and reject bad drafts.
The independent judge is mocked; real quality, billing and CLI interaction are
not proven. Step 2 needs separate owner approval and owner trial-key setup.
See [v2 recipe](delivery_tests/specs/README.md#draft-a-workflow-v2--step-1) and
[runner](../tools/draft_trials/README.md). Full `pytest -n auto`: **3,274 passed in 38.41 s**. V2 build --check has no
diagnostics; docs and whitespace checks pass.

## Hosted question caching — 2026-10-28, built for review

Own clean worktree `/home/makin/src/nw-ask-claude-caching`, branch
`codex/ask-claude-caching`, base `56cb997`. Options **Cache context** defaults
to off and offers 5 min / 1 h. Enabled requests cache the stable Context prefix;
o marker for empty Context, and off keeps the original request. SDK 2.3.0
cache/TTL types inspected locally. Run details include cache reads and writes,
with separate TTL pricing; successful calls now publish usage and estimates to
run history and CLI JSON through the existing event. Mocked engine tests verify
canary masking; no owner Secrets read and no live API calls.
Full `pytest -n auto`: **3,229 passed in 37.51 s**. Docs consolidation and
whitespace checks pass. See [contract](integrations/ASK_CLAUDE.md) and the latest
session entry for checks and the tested Run details example.

## Parallel test suite — 2026-10-27, built for review

Own worktree `/home/makin/src/nw-faster-tests`, branch `codex/faster-tests`,
base `4f1f5e7`. Per-test persistence/Hermes roots, isolated logging, spawned
concurrency tests and xdist work-stealing; no production code changes.
All declared Stash selectors remain checked, real subprocess kill/reap assertions
remain, twenty child-stack releases remain, and full geometry coverage remains.
Three consecutive full parallel runs: **3,127 passed**, **35.48 / 35.45 / 35.38 s**
external wall; serial **526.10 s**, quick **29.68 s** (3,083 passed; 44 slow cases).
The original serial probe took 694.25 s with overlapping diagnostics; owner's
independent baseline was 657 s. [Measurements and coverage accounting](audits/test_speed_2026_10_27/README.md)
record caveats and the controlled parallel baseline. Install `requirements-dev.txt`;
full `pytest -n auto`, quick `pytest -n auto -m "not slow"`. Reviewers run full.
After merging main `ba48bf5` (#132) into the candidate, one full parallel run
passes **3,205 tests in 37.16 s**; both runtime SDK and xdist dev dependencies
are present. Original benchmark numbers above remain tied to `4f1f5e7`.

## Hosted question node — 2026-10-27, built for review

Own worktree `/home/makin/src/nw-ask-hosted-question`, branch
`codex/ask-hosted-question`, base `4f1f5e7`. Owner choices 1–9 implemented:
single-turn streaming SDK, Secrets-only key, Options model/context limit, node
overrides/effort/JSON and standard inputs/routing. Refusal/cutoff stop before
content; typed errors omit provider bodies. Shared redactor protects Answer and
SDK diagnostics; real engine canary checks cover run_errors. No real API call.
[Contract](integrations/ASK_CLAUDE.md), [case](delivery_tests/ask-claude.json).
Brief grows to 7,634; designer Brief cap raised to 8,000; palette stays 7,421.
Catalogue default 64,000 (existing ceiling), compact JSON 51,792. **3,207 full-suite checks pass** (680.92 s); 205 focused checks, 27 example checks, helper node/UI, build --check, delivery schema, dependency, docs and whitespace checks pass. The three full runs and inventory corrections are recorded in the case.
[PR #132](https://github.com/makinster/node_workflow/pull/132), implementation `9d04dde`, targets main; not merged.

PR #132 P2 follow-up: Answer now masks only exact known Secrets, with JSON
parsed before masking decoded strings and re-serialized afterward. Ordinary
credential-like field names remain data for Check reply. Diagnostic/error
redaction is unchanged. Ask local model has no Answer-redaction pattern and is
unchanged. Verification is recorded in the latest session entry.

## Draft a workflow — 2026-10-27, medium trial checked only

Own clean worktree `/home/makin/src/nw-draft-workflow-medium-trial`, branch
`codex/draft-workflow-medium-trial`, main `80e4315`. Owner-approved unchanged
spec, fresh library `/home/makin/.local/share/aotn-draft-workflow-medium-2026-10-27`,
exact medium request, default Context 8,000, two local calls/no retry or edits.
**99.23 s overall** (shortlist 48.62 s, draft 50.55 s). Before: unloaded;
during/after: 100% CPU, context 8192, GPU VRAM 0. Neither token-fit warning fired
(estimates 2,323.5 / 3,246.75 below 8,192). Full Context 7,447 / 7,421.

Check passed with **zero warnings**; the reference has one intentional unreachable
preview, omitted by the generated graph, so warning-only display was not tested.
Exact raw Answer saved as
`/home/makin/src/agent_channel/draft-workflow-output/draft (1).json`;
saved-file build --check clean. **Target not built/run**: requested write path
`/tmp/draft-note.txt` is outside the allowed trial library. No path redirection.
Source comparison finds a functional error: display template `{{input}}` would
emit literal `{input}` rather than the saved path (pure string-format proof,
not target execution). Six-node graph/input/uppercase/Create unique structure
fits, but medium end-to-end behavior is not proven. Prior trivial success remains.
[Case](delivery_tests/draft-a-workflow.json) and local TRIAL.md Medium trial retain
metrics, Check/fit warnings, saved draft, scope decision and source-quality limits.
[Results PR #131](https://github.com/makinster/node_workflow/pull/131), record `ee1cb4c`.

Earlier implementation/trial entries below are historical; #130 is now merged.

## Ask local model Context limit — 2026-10-27, built for review

Own clean worktree `/home/makin/src/nw-local-context-limit`, branch
`codex/local-context-limit`, base `e7d07e8`. Owner's six choices implemented:
Options character limit 8,000 (1,000–200,000); blank per-node override inherits;
total Question limit is effective cap + 12,000. Oversize still errors without
trimming. Run details records chars/4 + max-output token estimate, window and
advisory warnings; never blocks solely on estimated fit. Context Pack's per-item
4,000 and catalogue-specific caps stay separate. No real model/workflow calls.
New node description measures Brief at 7,447; fixed palette remains 7,421.
[Contract](integrations/LOCAL_MODEL.md),
[delivery case](delivery_tests/local-model-context-limit.json). Focused checks
cover defaults/override/bounds/oversize, warning publication, mounted Options and
Node Config save/reopen/blank/range, source-menu parity and shared numeric policy.
**316 focused checks pass**; [PR #130](https://github.com/makinster/node_workflow/pull/130),
implementation `5746071`, targets main.

## Draft a workflow — 2026-10-27, re-trial passed

Own clean worktree `/home/makin/src/nw-draft-workflow-retrial`, branch
`codex/draft-workflow-retrial`, main `8945c3d`. Owner authorized an unchanged-spec
re-trial in fresh library
`/home/makin/.local/share/aotn-draft-workflow-retrial-2026-10-27`.
Same trivial request, public RunService/InputProvider, one designer run and
exactly two local calls, no prompt changes/retry. **75.14 s designer wall**:
shortlist 45.89 s (27.51 s cold load), draft 29.18 s. Before: unloaded;
during/after: 100% CPU, context 8,192, GPU VRAM 0.

Check passed with zero warnings and File Write saved the exact raw Answer to
`/home/makin/src/agent_channel/draft-workflow-output/draft.json`.
Saved-file build --check passed; under the same explicit approval, built only
into the fresh trial library and ran that target once: **[Ready Output] Ready**.
Target CLI wall 0.1225 s; no errors/model calls. Start-to-target completion
138.60 s includes inspection/handoff, saved-file check/build and CLI startup.
Three core types and machine port ids are correct. Extra End completion line
makes this noisier than the quiet sample; one trivial success is not general
quality/repeatability proof. Main library unchanged. [Case](delivery_tests/draft-a-workflow.json)
retains original failure, timings, saved draft, output and observed shapes.
[Results PR #129](https://github.com/makinster/node_workflow/pull/129), record `869ab1a`.
Local report: `/home/makin/src/agent_channel/draft-workflow-samples/TRIAL.md`.

Earlier implementation/failed-trial notes below are historical.

## Catalogue port ids — 2026-10-27, checked fix

Own clean worktree `/home/makin/src/nw-catalogue-port-ids`, branch
`codex/catalogue-port-ids`, base `232d112`. Text now distinguishes port ids from
quoted display labels in Brief/Compact/Detailed, with an id-only connection
legend; JSON fields stay unchanged. The designer draft prompt includes a
literal id-only connection example. Brief **7,438** / fixed Compact **7,421**
characters fit the existing 7,500 budget and hard 8,000 Context cap.
Four regressions failed on the base then passed; **104 focused tests pass**.
`build --check` is clean without temporary-root writes. No workflow/model calls,
live-library changes or re-trial; prior failure below remains the observed result.
[PR #128](https://github.com/makinster/node_workflow/pull/128), implementation
`555e493`; [contract](integrations/META_NODES.md),
[spec/guide](delivery_tests/specs/README.md).

## Draft a workflow — 2026-10-27, trial failed

[PR #126](https://github.com/makinster/node_workflow/pull/126) merged as `398c482`
after one clean review. That trial used the unchanged original
[spec](delivery_tests/specs/README.md).
Owner authorized decision 11: installed in the dedicated persistent library at
`/home/makin/.local/share/aotn-draft-workflow-trial`, answered the original input
through supported RunService/InputProvider, and ran the trivial request once.
Trial worktree `/home/makin/src/nw-draft-workflow-trial`, branch
`codex/draft-workflow-trial`; [case](delivery_tests/draft-a-workflow.json).

**70.64 seconds total, exactly two calls, no retry.** Before: model unloaded;
during/after: 100% CPU, 8,192 context, no GPU offload. Shortlist 41.26 s (28.02 s
load), draft 29.32 s. Neither timed out. The draft used display annotations in
port ids (`default/Greeting`, `input/Input`). Check rejected it: two unknown-port
errors, two unreachable warnings. The failure message appeared; File Write and
success output were skipped. No saved draft, target build/run or output folder.
Engine FINISHED/exit 0 means handled failure, **not** a successful draft.

Complete Brief/Compact context stayed 6,207 / 6,865 characters. Original general
lookup mapping remains 7/8; approved fixed-palette scope stays 8/8, not a quality
score. The generated draft is non-executable versus the approved clean sample.
No fixes, extra trial or broad activation were authorized;
[results PR #127](https://github.com/makinster/node_workflow/pull/127) changes
documentation only. Local timing/evidence:
`/home/makin/src/agent_channel/draft-workflow-samples/TRIAL.md`.

The following #125 candidate/review notes are historical; #125 is now merged in
`cfd3458`, as verified from Git/GitHub. Their pending/open labels are retained.

## #125 re-check: structured failure inputs — 2026-10-27

The re-check of `3a69e19` found that credentials in objects/lists could still
reach `run_errors` because labels and values were redacted independently.
The supervisor now checks each original dictionary key with the shared C3c/#119
credential-label matcher, masks its whole value, then redacts keys and recurses
through non-sensitive values. No second label list; harmless structure remains.
Known Secrets masking and the 2,000-character input cap remain. Real Start (var)
→ Error regressions cover flat/nested/list payloads and credential containers.
Two flat/nested regressions fail on the reviewed head; **47 focused checks pass**.
Full suite: **3,106 passed in 676.59 seconds**, no retry. Compilation, delivery-case
schema, docs consolidation and whitespace checks pass. Independent clean re-check
remains pending.
No generation or live settings/workflow changes.

## Meta nodes — 2026-10-27, PR #125 open

`codex/meta-nodes`, own worktree `/home/makin/src/nw-meta-nodes`, base `3f36552`.
Implementation `389692c`, [PR #125](https://github.com/makinster/node_workflow/pull/125).
Owner-approved [Node catalogue / Check workflow spec](integrations/META_NODES.md)
provide bounded live contracts and the CLI's shared check-only validation.
Debug nodes opt in; Start/End remain; internal types stay out. Measured compact
all-non-debug catalogue: 50 entries, Text 34,618 / JSON 49,866 characters;
default cap 62,400 (25.14% above the larger form). No partial output.
Check returns the original parsed draft; optional bounded warnings/report and
error problems do not save/build/execute. No approval/build or Bundle node.
[Built screens](audits/meta_nodes_2026_10_26/README.md) use real CSS/classes.
[Loop case](delivery_tests/meta-nodes.json) records step 5 and optional repeated
shapes; related designer coverage 6/8, approval and build still gaps. Review,
merge, activation and ordinary owner use remain pending. No generation calls.
Verification: **3,096 passed in 680.85 seconds**, no WaitUntil retry; helper,
CLI/example, artifact/schema, compilation, consolidation and whitespace checks pass.

The following #124 candidate notes retain historical review details. #124 is
now merged in the checked `3f36552` baseline; their pending status is historical.

## #124 second review P2 — 2026-10-26, fix for re-check

At `f360e8a`, the original wrong-field Stash assignment was fixed, but shared
printable-key rescue could still append P to a previously edited field after
focus moved to a closed Select. The new candidate removes that rescue and
resolves typing policy and Stash targets from current focus only. No remembered
Insert-button target remains; unsupported focus refuses without value/dirty
changes. Long-text callbacks capture their exact field. Subworkflow binding
buttons use explicit E/Enter activation; P refuses.
[Review evidence](audits/source_menus_2026_10_26/STASH_FOCUS_REVIEW.md) and
[loop case](delivery_tests/source-menu-audit.json) record both review rounds:
**3048 passed in 674.42 seconds**, no WaitUntil retry. Independent re-check and
merge remain pending.

## Source menus and model pickers — 2026-10-26, PR #124 open

`codex/source-menu-audit`, worktree `/home/makin/src/nw-source-menu-audit`,
base `f0aa39d`: [all-node audit](audits/source_menus_2026_10_26/README.md),
56 types / 131 input ports / 31 standard source ports, **five shared mismatches**.
Fixes preserve dynamic types, compatible multi-writer keys, child result Vault
writes and all fan-in parents; duplicate summary IDs no longer block Node Config.
Options and per-node model choices share bounded read-only installed-model
pickers, sole-model Options draft autofill and editable failure fallback.
Source additions remain proposals; no generation or live settings changes.
[Loop case](delivery_tests/source-menu-audit.json): `swiss-army fix`, no new
workflow operations/coverage denominator; review and owner use pending.
Full suite: **3,016 passed in 516.49 seconds**; focused **125 passed**,
no WaitUntil retry. Helper, schema/screenshots, docs and whitespace checks pass.

## Ask local model — 2026-10-26, PR #123 merged

Owner approved decisions 1–10 and the visible per-node tuning controls.
`codex/ask-local-model`, worktree `/home/makin/src/nw-local-model`, base
`27d16bc`: native bounded Ollama client, Options URL/default model, Question
and optional Context, Answer, optional Vault Run details and standard forwarding.
No retries, auto-pull/start, tools/history or cloud fallback. Source menus match
runtime/metadata; mounted checks include eligible upstream secondary Vault text.
The per-machine model field starts blank; no particular model is shipped.

[Contract](integrations/LOCAL_MODEL.md), [real built screens](audits/local_model_2026_10_26/README.md),
[delivery case](delivery_tests/ask-local-model.json). Original coverage 3/4;
the candidate fills its one gap. Exactly two authorized small generation
requests: cold **35.180 s** (load 27.336 s), warm **2.929 s** (load 0.008 s).
Both JSON replies passed Check reply. Temporary data/Options only; no live
workflow, notification, service or schedule changes. A clean first independent
review was reported in the coordinator notes; PR #123 merged at `f0aa39d`.
Owner setup, ordinary use and retro remain pending.

Final full suite: **2920 passed in 502.05 seconds**. Two inventory
follow-ups were needed: 26 multiline fields across 13 types (explicit new-field
assertions), and registration of the new example in the build/save/reload
matrix. Final complete suite passes; no WaitUntil flake retry needed. Helper, example
build check, compilation, JSON/schema, source-hash, docs and whitespace checks pass.

## Delivery-loop method — 2026-10-26, docs only

[Delivery Loop](DELIVERY_LOOP.md) records the request-to-use cycle, owner gates,
review/go-live checklists, versioned planning templates and three historical
[delivery tests](delivery_tests/README.md). Base `3239b44`; no application or
live changes. Measurement comes first; MCP authoring and the meta-workflow are
future direction, not implementation approval. Existing Step 4/5/6 order stays
in its owning plans.

## #121 line-ending/history correction — 2026-10-26

The shared editor uses logical LF positions while keeping separator provenance
separately for mixed text and native history. LF/CRLF/CR fields save in their
opened style, including pasted/Stash text. Mixed fields preserve their separate
endings; newly adjacent CR/LF breaks cannot silently coalesce. Save and close
compare logical drafts, so undo restores an unchanged state and a byte-identical
field. No workflow migration or runtime changes.

Regression keys reproduce on `4e75a62`: four CR/mixed failures and two CRLF
controls, at 80×24 and 120×40. Coverage also checks redo, clipboard paste,
commands-mode Stash insert, mixed-history ranges, genuine saves and reopen.
Focused checks: **116 passed**. Full suite: **2,840 passed in 498.49 seconds**;
no WaitUntil flake retry needed. Compilation and whitespace checks passed.

## Shared long-text editor — 2026-10-26, built for review

Owner-approved answers 1–15 and the 2026-10-25 Save/Esc/Ctrl+Q decisions are
implemented in `codex/shared-long-text`, own worktree `nw-shared-long-text`,
from `origin/main` `334cb67`. All 23 existing multiline paths plus Text Output
Template use one preview/editor through the form generator, including nested
items. Source visibility, payload/Vault routing and saved keys are unchanged.

Editor Ctrl+S applies only the field and restores preview focus; Node Config
Ctrl+S saves the node. Two Esc stages, Ctrl+Q cancel, safe confirmation defaults,
whole-field Stash replacement and cursor insertion use shared keyboard/modal
patterns. Full Unicode, mixed CRLF/CR/LF and trailing blank lines survive edits.
Selected previews/buttons use HIGHLIGHT; editor text colour stays unchanged for
the later UI pass. Read-only fields get a viewer. No workflow migration.

[Real built screens](audits/shared_long_text_2026_10_26/README.md) cover 80×24
and 120×40. Final focused verification: **105 passed**, including the 15 shared-editor
cases and real Stash integration; Text Output helper **2 passed** and UI contract OK.
Full suite: **2,825 passed in 477.41 seconds**; no WaitUntil flake retry needed.
No deployment, model calls or live configuration changes; owner merges.

## #120 P2 corrections — 2026-10-25

Known Secrets values are masked in decoded strings and keys before JSON
serialization, using the shared redactor. Its opt-in final check recognizes
mixed JSON escapes and the rendered line-prefix layout. Pack output and its
Vault copy share that checked result. Metadata reservation switches to compact
section-order shortening notes when needed, keeping every valid 16-item setup
within the minimum pack cap even with run info/errors enabled; bodies can be
marked omitted. Regression probes fail on `0d12725` (17 failures, two controls
passed); all 52 Context Pack checks now pass. Full suite: **2,809 passed in
461.92 seconds**, no WaitUntil flake retry needed. No installation or live
configuration changes.

## #120 compact-row highlight correction — 2026-10-25

Owner correction supersedes the earlier grey/nav-highlight request. Start
inputs, Check reply and Context Pack now use the live `frontend.colors.HIGHLIGHT`
role for one solid selection over every cell and the full row width. The shared
renderer follows palette/role overrides after mounting and preserves cell
colours when unselected. Three failing-before cases now pass; focused UI checks
**15 passed**. Full suite: **2,784 passed in 470.05 seconds**, with no
WaitUntil timing-flake retry needed. The [before/after and Context Pack screen
captures](screenshots/context-pack/README.md) were updated; before is the prior
#120 head `e0f0dbe`. No backend, installation or live configuration changes.

## Context Pack — 2026-10-25

Built for review on `codex/context-pack`, own worktree
`/home/makin/src/nw-context-pack`, from clean fetched `origin/main` `9b98f48`.
The approved 15 answers and the owner's wording/table/Context/snapshot decisions
are implemented: ordered source rows, bounded JSON preparation, shared C3c
redaction before trimming, complete shortening notes, standard forwarding and
an independent redacted Vault copy. The supervisor supplies immutable per-visit
start/latest-five-error facts from this run's memory; no history/error-file
reads or node subscriptions. Missing upstream publication remains distinct
from explicit null. Engine changes are separate commits `92b9d4b` and `8bdf8a8`.
Ask Hermes has optional Context (off by default), 8,000-character own cap within
the existing 20,000-character total, in the same attached `--query=` argument.
The shared compact tables use the live `HIGHLIGHT` role from `frontend/colors.py`
for a solid selection across every cell and the row padding. This supersedes
the earlier grey/nav-highlight treatment after the owner’s correction.

[Contract](NODE_STANDARDS.md#context-pack-owner-2026-10-25),
[real screenshots, including before/after Start and Check reply](screenshots/context-pack/README.md),
[validated example](../examples/context_pack.json). Tests use synthetic data,
fake executables and temporary libraries; no paid calls, installs, owner
workflow changes, Hermes configuration or live-job changes.

Verification: initial full suite **2,779 passed in 453.68 seconds**; final-tree
full suite **2,784 passed in 452.35 seconds**, with no WaitUntil flake retry
needed. Focused checks cover source/cap/trim/redaction/error cases,
per-run snapshots, real-engine direct Context wiring, literal argv injection
attempts, Unicode cap boundaries, keyboard editing at 80×24 and shared highlight
styles. Node-helper generation/checks, compilation and whitespace checks pass.
The docs consolidation checker still reports the base's unexpected active
`SMALL_WINS.md`; relative links/anchors pass.

## MCP activity summaries — 2026-10-24

**#119 padding/boundary re-check (2026-10-24):** the shared C3c/activity
redactor masks padded Base64 continuations through trailing padding-only
lines and matches credential labels as whole field names. Ordinary compound
names and prose remain intact. New inbox-persistence and real-worker cases
produce 18 failures/four preservation controls on `16fbe5f`; all 22 pass with
the fix. Focused MCP/inbox checks: **212 passed**. Full suite: **2,719 passed
in 443.87 seconds**; no known WaitUntil timing-flake retry needed. No live
configuration or install changes.

**#119 P2 re-check (2026-10-24):** the shared C3c/activity redactor now masks
whole multiline credential values and URL userinfo across scheme cases/names.
Inbox request persistence and real activity-worker/MCP output are covered;
public URLs and following non-secret fields remain intact. All final re-check cases against an archive of `6cbee5f` produce
36 failures across both paths and eight existing PEM/quoted/HTTP controls
passing. Final focused MCP/inbox checks: **190 passed**, including 44 re-check
cases and controls. Full suite: **2,697 passed in 440.89 seconds**; no
known WaitUntil timing-flake retry needed. Compilation, links and whitespace
checks pass. No live data/configuration or install changes.

**#119 review follow-up (2026-10-24):** activity projections now use the shared
C3c redactor for labelled credentials and loaded Secrets values, before caps
and worker output. Labels include spaced API keys, AWS access/secret keys,
authorization/bearer and mixed-case private-key blocks. An oversized unfinished
EOF event line counts once as damaged even when it spans the byte window;
complete leading window fragments remain truncation only. Eleven regression
cases fail on `ff2ea3f`; all 146 focused MCP/inbox tests pass. Compilation,
links and whitespace checks pass. Full suite: **2,653 passed in 439.49
seconds**; no known WaitUntil timing-flake retry needed.

`get_activity(since, limit)` merges run summaries, investigation findings/failure
codes and C1 Notify me receipts/Record event summaries into one newest-first
UTC list. This addresses the gap where an investigation finished after its
requesting run and was absent from a run-history-only answer. The legacy
`get_recent_events` tool is unchanged. Reads use the selected data root and
`$HERMES_HOME/aotn`, with bounded scans, damage counts, source truncation flags,
regular-file/no-symlink checks and redacted field projections; no raw evidence
or event values are exposed. [Contract and setup](integrations/MCP.md#activity-across-runs-and-hermes).

Own worktree `/home/makin/src/nw-mcp-activity`, branch `codex/mcp-activity`,
from clean fetched main `d86faf2`. Focused MCP tests: **73 passed**; full
suite: **2,635 passed in 437.16 seconds**, with no timing-flake rerun.
Compilation and whitespace checks pass; the docs checker retains the base
`SMALL_WINS.md` active-doc allowlist failure. No live install, Hermes allowlist/configuration,
cron job, gateway or owner workflow changes; the owner merges after review.

## Small wins — 2026-10-23

**#118 review follow-up (2026-10-24):** Read lines compares the original byte
range across both passes with bounded chunk fingerprints, rejecting growing
same-inode rewrites while permitting append-only growth. Reversed ranges are
checked before clamping. Check reply recursively rejects decoded strings and
keys that cannot encode as UTF-8, including extra fields, before publication.
Eleven regression cases fail against `4c780fc`; all 15 review cases and 62
focused tests pass with the fixes. Full suite: **2,609 passed in 439.81
seconds**; no known WaitUntil timing-flake retry needed. Compilation, links
and whitespace checks pass.

Read lines, Find lines and Check reply built on `codex/small-wins-build`, own
worktree `/home/makin/src/nw-small-wins-build`, fetched `origin/main` `472001c`.
The owner approved recent-match retention plus a true optional Vault Match
count, and Start-style compact expected-field rows. Allowed-folder snapshots,
bounded UTF-8 reads, strict JSON shape checking and standard forwarding are
implemented. Configured Reply uses a shared opt-in preview/full-screen editor;
the wider long-text UI rollout remains separate.
[Contract](SMALL_WINS.md), [real built screens](audits/small_wins_2026_10_23/README.md).
No model calls, live installs or external configuration changes.
Verification: **2,594 passed in 438.14 seconds** (full `pytest -q`); no known WaitUntil timing-flake retry needed. Helper node/UI checks, compilation, links, whitespace and 41 focused behavioral/UI tests pass. Both approval regressions fail when the
rejected behavior is restored in memory, and pass with the implementation.

## C3c investigation inbox — 2026-10-23

**#117 review follow-up:** Unicode findings publish as bounded UTF-8 JSON,
including emoji and Unicode separators; lone surrogates follow C1 replacement.
Record-size rejection becomes terminal failed, and the final 3,500 UTF-16-unit
stdout budget includes the entry newline. Seven regressions fail on `1329965`
and pass with the fixes. Verification: **2,541 passed in 432.48 seconds** (full `pytest -q`), no known WaitUntil timing-flake rerun needed; all seven regressions pass and all seven fail on `1329965`. Compilation, Bash syntax and whitespace checks pass.

Built on `codex/c3c-inbox`, own worktree `/home/makin/src/nw-c3c-inbox`, from
fetched main `5e7c4e3` (#116 merged). The owner's simple v1 decision supersedes
the read-only-tool proposal: AOTN gathers evidence, and the investigator has
**no tools**. Two standard nodes queue/read versioned requests; the no-agent
bridge uses #116's strict CLI preflight and one-turn `--query=` launch, with
90-second bounded process-tree cleanup, exclusive claims, durable daily caps,
no paid retries and conservative stale/cleanup blocking.

[Setup](../integrations/hermes/README.md#investigation-inbox-c3c-simple-v1),
[record contract](integrations/HERMES_SHARED_FOLDER.md#investigation-inbox-c3c),
[built screens](audits/investigation_inbox_2026_10_23/README.md).
Current multiline widgets are used; the shared preview editor remains later
work. No real model call, Hermes config/job change or live install.
Verification: **2,534 passed in 423.50 seconds** (full `pytest -q`); no known WaitUntil timing-flake rerun needed. All 48 inbox tests and both affected integration checks passed together (50). Helper node/UI checks, compilation, Bash syntax, 17 real-screen captures, keyboard save/reopen/discard, doc links and whitespace pass.

## Baseline and open work — 2026-10-22

- **C3b part 1 reworked for #116 (2026-10-23):** `codex/ask-hermes`, own
  worktree `/home/makin/src/nw-ask-hermes`, merged fetched main `f9f5f07`
  (already integrated). Ask Hermes now calls the public CLI in the independent
  `aotn` profile, checking every CLI toolset disabled before each question.
  Options owns profile home/command; Folder stays checked and the total deadline
  covers preflight/chat/process-tree cleanup. No Hermes imports or shell command
  string. Unknown usage stays null; forwarding/Vault/records remain standard.
  One authorized real smoke returned **AOTN profile smoke OK** in 5.518 seconds.
  [Setup](../integrations/hermes/README.md#ask-hermes-setup),
  [contract](integrations/ASK_HERMES.md), [screens](audits/ask_hermes_2026_10_22/README.md).
  Profile isolation is not an OS sandbox; no default-profile/config/live changes.
  Verification: **2,465 passed in 408.10 seconds** (full suite), no timing-flake
  rerun; helper node/UI, compilation, docs and whitespace pass.
  The later task node and long-text editor remain separate.

- **Later long-text UI proposal:** preview-only multiline fields and a shared
  full-screen editor, scheduled after C3b; **proposal, samples first**, not
  approved implementation. [UI consistency backlog](PROJECT_BACKLOG.md#later-project--ui-consistency-pass-and-theme-owner-2026-10-20).

- **Telegram launcher v0 built for owner review:** branch
  `codex/telegram-launcher`, from main `bfcdc36`, worktree
  `/home/makin/src/nw-telegram-launcher`. A named `aotn-run-<slug>.sh` entry
  selects a saved workflow by filename, refuses arguments and runs the existing
  JSON adapter against the live checkout and separate cron data directory.
  `--telegram-launcher` uses a 25-second run/cleanup budget, H0 escaping and
  cap, and single-line failures. It supplies `checked_at` only if Start declares
  it; other required inputs need saved defaults. Review fixes for #114 refuse
  non-regular install destinations and detect/repair mode drift (755 entries,
  644 shared files). Named install/check and the unapplied Hermes config
  example are in the [adapter guide](../integrations/hermes/README.md#telegram-launcher-v0-owner-requested-2026-10-22).
  Verification: **2,403 passed in 395.57 seconds** (full `pytest -q`), no
  timing-flake rerun; all 15 review regressions pass (11 failed on `89c9d2a`).
  Real 25-second descendant cleanup, heartbeat and H0 checks passed, along
  with compilation, Bash syntax, docs and whitespace.
  No live installation, Hermes configuration or cron changes.

- **System-node forwarding follow-up merged in #113:** branch
  `codex/system-node-forwarding`, from main `9470729`, now integrated with
  main `670b3b3` for #113. Disk space, Git status and File age use the standard Forward incoming payload unchanged checkbox.
  Checked sends the incoming payload; unchecked sends the computed report.
  Enabled Vault outputs always receive the computed report with its own type.
  Combined verification after the merge: **2,367 passed in 370.24 seconds**
  (full `pytest -q`); no timing-flake rerun needed. Compilation, docs and
  whitespace checks passed; original helper node/UI checks remain logged.

- **H0 live (#103/#106):** the adapter and installed wrappers run from
  `/home/makin/src/aotn-live` with the isolated cron library at
  `~/.local/share/aotn-cron`. Heartbeat job `63968ee90ae0` runs
  `aotn-h1-heartbeat.sh`, no-agent, daily at 09:00 America/Los_Angeles,
  delivering to Telegram's `home` alias. Installed copies were checked;
  `cron.wrap_response` remains on. The [adapter guide](../integrations/hermes/README.md)
  and [H0 contract](integrations/HERMES_H0_DRAFT.md) describe escaping, limits,
  exit codes, locking and descendant cleanup. Earlier test/probe receipts are
  retained in [Session Log](SESSION_LOG.md).
- **H2 parked:** the watchdog remains an **unscheduled template** until the
  owner chooses a real service and updates its URL. Throwaway adapter checks
  exercised success/failure responses; they did not enable a watchdog job.
- **C1 merged and live (#109):** Notify me and Record event write the
  [Hermes shared folder](integrations/HERMES_SHARED_FOLDER.md),
  `$HERMES_HOME/aotn` (default `~/.hermes/aotn`). The live checkout was updated
  and the drain installed. No-agent drain job `cd14afa83db9` runs every five
  minutes (`*/5 * * * *`) to Telegram `home`; the owner confirmed receipt of
  the end-to-end test message. The outbox was emptied and its `handed_off`
  receipt recorded; no reconciler supplies a `delivered` stage yet. The retained
  `c1-notify-test` workflow is available in the cron data directory for future
  checks. Send to names are configured in Options. Urgent sorts first with ⚠;
  per-job notification sound still needs a Hermes change (proposal Q7).
- **C4 merged (#107/#108):** [local stdio MCP](integrations/MCP.md) exposes
  four typed execution/history tools using the standard library. Contracts and
  Stash inputs, unattended termination/C25 checks and isolated timed workers
  are implemented. The stdin-from-file follow-up exits 64 with a one-line
  diagnostic. Current tools do not create/edit workflows, provide live progress
  or bridge interactive replies; adding authoring tools is a future designer
  step, not already implemented behavior.
- **C2 merged in [PR #110](https://github.com/makinster/node_workflow/pull/110):**
  Saved values, branch `dist/persistent-store`, with main merged in. Remember,
  Recall and If changed, the Stash Saved values tab, CLI and store
  locking/validation are in main `670b3b3`. Both reviews'
  findings (eight, then the overflow P1 and the large-integer P3) are fixed
  with regression tests; Remember and Recall use the standard Forward incoming
  payload unchanged control.
- **C3a merged in #112 (2026-10-22):** branch `dist/pick-one`
  from main `cce4fc7`, with `origin/main` `9470729` merged before the review
  fixes. Jev: Pick one, `backend/integrations/jev.py`, helper
  spec/generated checks, exact answer rows, fixed `unsure` below 0.3, optional
  Vault-only details. No provider/model selectors or Stop option. Shared
  routing now preserves each Vault output and omits Vault-only branch names.
  The standard Forward incoming payload unchanged control replaces only the
  downstream answer, preserving enabled Vault outputs.
  [Built screens](audits/pick_one_2026_10_22/README.md),
  [node contract](NODE_STANDARDS.md#bounded-choice-node-c3a-owner-2026-10-22).
  Review fixes reserve `unsure`, reject edge whitespace in answers through form,
  preflight and runtime checks, and cap Text at 20,000 characters before requests.
  **89 focused tests passed; 2,245 passed in 345.91 seconds** in the full suite
  on the combined branch; compilation, docs and whitespace checks passed. No paid call,
  owner/live data, installed wrapper, cron job or repository workflow change.
- **Owner plan reset (2026-10-22):** C2 → C3a Jev: Pick one → thin Telegram
  launcher → C3b bounded agents → 4e–4f → P1 → Phase 17 verification → C5 →
  Step 5 → C6 → Step 6. See the
  [approved order and idea mapping](AI_COORDINATION_PROPOSAL.md#9-effect-on-the-build-plan-owner-order-2026-10-22).
  Hermes confirmed `quick_commands` with `type: exec` (source `556bf7c5c`):
  fixed scripts run after normal sender authorization, with no agent turn,
  plugin or arguments. Config is the workflow allowlist; use one
  `aotn-run-<slug>.sh` entry per allowed workflow, deriving the slug from its
  filename. The 30 s reply timeout does not kill the script, so the entry must
  enforce its own deadline under 30 s and kill/reap on timeout. Natural-language
  menus later still need a plugin or an agent turn.
  The designer is a new track after C3; local-model comparison follows
  C3a. The [archived discussion](archive/plans/INTENT_ROUTING_AND_DESIGN_ASSISTANT.md)
  preserves context rather than setting a competing work order.
- Merged baseline includes C1–C7 decisions (#102), workflow naming (#68), docs A/B
  (#69/#72), Stash S1–S3 (#70/#71/#75), window buttons (#73), duplicate
  prevention (#74), keymap phases 1/2 (#77/#78), contracts (#80), the
  file-picker test fix (#81), editor hotfixes (#82), the deletion proposal
  (#84), docs C (#83), deletion answers (#86), subworkflow screens (#85),
  child runs (#87), deletion phase 2 (#88), picker polish (#90) and the
  Execution screen (#89), including its review fixes, are merged.
  S3 uses plain P, off while typing; Ctrl+P and the palette are unchanged.
- **Editor hotfixes (#82):** insert before a node with two parents keeps it;
  HTTP Request and JSON Path get no error path by default; failure paths keep
  the normal path's colour; deleting a node with an error handler asks, then
  removes the handler; undo and stub removal never give an output a second
  target. [Session log](SESSION_LOG.md).
- **Deletion review phase 2:** merged in #88. First delete groups owned paths;
  Z restores the group, with a preview before partial restore. Branch count
  reductions save removed paths under the live Branch; increases offer
  Recover / Leave empty / Cancel and optional path picks. Keep saved paths
  until the owner sets expiry. Every affected Beacon resets on Merge deletion;
  Beacon deletion ends its branch. Warning levels stay unchanged. The editor
  shows ` [sub]` for callable workflows. No `node_config.py` or Execution
  screen changes. The review follow-up (#90, merged) fits picker lists to their rows,
  shortens the new messages and reformats the two deletion test files.
  [Compact picker samples](audits/deletion_picker_polish_2026_10_19/README.md),
  [approved proposal](DELETION_REVIEW_PROPOSAL.md),
  [rendered screens and verification](audits/deletion_phase2_2026_10_19/README.md).
- **Step 4:** design rev. 4 approved (#76/#79); 4a-1 backend/CLI contracts
  built (#80). 4a-2 screens merged in #85: File window Workflows/Subworkflows
  tabs, copy to Subworkflows, Start Inputs and Results tabs, the End Results
  tab, "Send back to calling workflow". 4b child runs (backend and CLI) merged
  in #87: the Subworkflow node, call tree,
  limits (depth 4, 64 live), file hand-over, prompts, pause and stop, run
  records, validation and benchmark. EX (the Execution screen overhaul)
  merged in #89, with its review fixes. 4c-1 (the Subworkflow node in Node
  Config: Inputs and Payloads tabs, the picker, the map's `Greet (Greeter [sub])`
  and `➥ (n)`, the details pane; the node is in the selector) merged in #91, with
  its review fixes. 4c-2 (opening a running call
  from the Execution screen with E/Enter, breadcrumbs, prompts that say who
  asks) merged in #94, with its review fixes. The prompt queue (C19: a
  second prompt waits for the first instead of being dropped) merged in #96.
  4d (Stash entries as Subworkflow node inputs and `--input key=@stash:name`;
  per-machine bindings dropped, owner 2026-10-20) merged in #101.
  Left in Step 4: 4e/4f shared memory.
  [Proposal](SUBWORKFLOWS_PROPOSAL.md).
- **Keymap phase 3 — Editor/Execution:** merged in #92.
  Both screens already compiled bindings from profiles; Help and status hints
  now use those same definitions and native key overrides. Current keys and
  default compact hint wording are unchanged. Execution Help now lists X Stop,
  W/S movement, A/D paths, F Follow and V error panel. W/S scrolls Help while
  Close stays visible. [Before/after text and verification](audits/keymap_phase3_2026_10_20/README.md).
  Other Help contexts remain unchanged. Node Config, Node Selector and Workflow
  Library presentation remain separate work. Settings rebinding UI and generated
  Quick Reference tables remain deferred.
  [Scope](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
- **Modals fill the terminal** (owner, 2026-10-20), merged in #93: Node
  Config, the node selector, large viewers, Help, Options and the File
  window use the whole terminal; taller dialogs scroll to their buttons.
- Work order: [Node Contract Plan](NODE_CONTRACT_PLAN.md). Long-term direction:
  [Distributed Plan](DISTRIBUTED_BUILD_PLAN.md), [Stash](STASH_PROPOSAL.md).
  The owner merges, or explicitly asks a reviewer to.

## Verification and environment — 2026-10-22

- This refresh passed the documentation consolidation checker and
  `git diff --check`. Full-suite figures below are historical receipts, not a
  current-main test result. No live job or application behavior was changed.

- Prompt queue slice: **1,918 passed in 301.82s**, three new tests in
  `tests/test_prompt_queue.py`.
- This keymap phase-3 slice: **1,884 passed in 277.58s**. Twelve new tests cover
  generated Help, unchanged keys/hints, punctuation/control-key spelling,
  effective rebindings, modal isolation and keyboard scrolling at
  60/100/140 columns. Profile definitions for APP, EDITOR and EXECUTION are
  unchanged (AST comparison). No Node Config or workflow edits.

- Main `b5426ab` includes #88: **1848 passed in 265.69s (0:04:25)**.
  Picker follow-up (#90): **1856 passed in 265.73s (0:04:25)**. EX (#89)
  with its review fixes, merged with #90: **1872 passed in 281.21s (0:04:41)**. The 55 phase-2 tests
  cover topology, durable recovery,
  stale plans, conflicts and mounted form/picker flows. Production CSS and
  actual keys checked at 60/100/140 columns; SVG and text captures retained.
  The follow-up adds eight failing-first checks for compact geometry, wrapped
  rows on resize and the requested wording. Both reformatted test files retain
  their original assertions and setup (AST comparison). Tests set
  `AOTN_DATA_DIR` before importing the backend.
- Link/anchor, whole-archive and session-transfer checks: see
  [PR C verification](audits/docs_audit_2026_10_17/PR_C_VERIFICATION.md).
  The active set is 17 core docs plus SUBWORKFLOWS_PROPOSAL,
  DELETION_REVIEW_PROPOSAL and AI_COORDINATION_PROPOSAL, each archived when its
  work completes or is declined. The coordination owner decisions are recorded
  in section 10, with the October 22 work-order reset in section 9. The longer
  intent/designer conversation is already an archived reference.
- Prior receipts: keymap phase 2, 1666 passed with actual-keypress tests;
  phase 1, 1605 passed (57 focused); Stash S3, 1548 passed. Docs B retained
  33 archive bodies. These are historical counts, not the current suite.
- Python **3.14.4**, Textual **8.2.7**, pytest **9.1.0**; shared interpreter
  `/home/makin/src/node_workflow/.venv/bin/python`. Other workers' checkouts and
  owner workflows are not edited; the OneDrive checkout is recovery-only.
- Clean installation, native terminal/live geometry, native Windows FO7 and
  external web links were not reverified. Owner FO7 results are still needed.

## Open owner decisions and evidence limits — 2026-10-22

- Stash: file fields accept file entries; text fields accept text only.
  Global-only versus per-workflow pinning remains open (proposal question 3).
- Deletion Q1–Q5 answered October 19: keep/reset every affected Beacon, end a
  deleted Beacon's branch, preview partial restore, save removed Branch paths
  and offer optional recovery, preserve warning levels. Owner approved #86;
  phase 2 merged in #88; its small review follow-up merged in #90. Saved-path
  expiry remains undecided, so retain
  entries for now.
- Only the retained audit report survived; original CSVs/evidence are absent.
  The rebuilt source map and whole archives preserve the migration trail.
  [Recent log](SESSION_LOG.md); [older history](archive/SESSION_LOG_HISTORY.md).
