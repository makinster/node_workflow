# Draft workflow trials — Step 1

This is an external test harness, not a new workflow node or a general English
requirements prover. The frozen oracle in `cases.py` implements the approved
10-case TEST_SET (version 3). `fixtures/calibration.json` contains 30 paired,
hand-authored good/bad drafts. Mock mode exercises the actual SDK adapter,
designer graph, Check nodes, authoring build/check and target engine. It supplies
canned replies and a synthetic credential in memory; Secrets lazy loading and
socket connections raise. It does not measure real drafting or judging quality.

Run from `AttackOfTheNodes/` with the repository's WSL interpreter:

```bash
python -m tools.draft_trials --trial-root /absolute/fresh/trial-root
python -m tools.draft_trials --trial-root /absolute/another-root --cases 1,10
python -m tools.draft_trials --trial-root /absolute/calibration-root --calibrate-only
```

A new root is prepared automatically in mock mode, or explicitly with
`--prepare`. Its only top-level entries are `prepared.json`, `library/` and
`runs/`. Prepared roots can be reused in mock or approved real mode. Each run
exclusively creates the next unused directory, `runs/000001/`, `runs/000002/`,
and so on. Existing files/directories are never overwritten to allocate a run.
All artifacts, generated workflows, fixture files and backend run records stay
inside that run's directory, including its own `library/`. Every CLI build/check
subprocess receives that run library through `--data-dir`; RunService inherits
it before backend imports. Both designer versions are built there with distinct
names, then only v2 executes. The shared root `library/` stays in place and is
not written by trials. In real mode only, normal node credential access uses a
read-only Secrets manager pointing to the shared library; no key or settings
are copied. Mock mode uses a synthetic credential and blocks Secrets loading.

Before any write, environment change or backend-service import, every existing
root undergoes the same complete metadata-only tree check, including **all prior
runs and the shared library**: symlinks (internal, external or dangling), hard
links, FIFOs, sockets and other non-regular entries are rejected. Every resolved
path must stay in the resolved root; symlinked ancestry is rejected too. The
regular `prepared.json` must match its exact version, library path and note,
with no duplicate or unknown fields. The root must contain exactly that marker
and the `library/` and `runs/` directories. Library files and Secrets are never
opened by this check. Old roots without this layout are rejected; prepare a new
root rather than silently migrating an old trial's evidence.
`--prepare` requires a fresh root, exclusively creates its marker and cannot be
combined with `--real-calls`. This preflight is not an OS sandbox against
concurrent directory replacement. For programmatic use, select `AOTN_DATA_DIR`
**before backend imports**, as the CLI does; changing it after imports cannot
relocate cached data paths. Use the CLI for preparation/reuse/containment checks.

Each case freezes its rendered request, clarification, expectations and fixture
variants before generation. Only the designer's draft destination is changed
to `runs/<run>/cases/<id>/drafts/draft.json`; that trial variant is saved in
`trial-designer.json`. Target paths are never repaired or redirected. The old
spec remains unchanged and is built for inspection, not run as a local-model
comparison. A future baseline comparison needs its separate approved call scope.

User Text Input uses RunService's `input_provider` with an ordered queue. Extra,
missing or out-of-order prompts fail. This is **not** PTY or interactive CLI
proof; that flow is a later manual check. Unicode, multiline input and an empty
answer are supported by this API hook. `--scenario judge_fail`, `error` or
`unhelpful` provides negative mock scenarios (use `--cases 10` for unhelpful).
`--replies <json>` supplies mock-only case-id → ordered SDK replies; each reply
is a JSON object or exact JSON string. `{ "_error": "transport" }` simulates a
transport failure. Unused replies and unexpected calls fail.

## Acceptance and containment

The four reports stay separate: valid spec, frozen case rules, meaning review,
and actual target behavior. A handled workflow error with exit 0 is not success.
No saved file, no completed success gate or missing gate evidence fails the case.
Unknown status/verdict values cannot reach the designer save path. Deeper report
checks enforce requirement ids, fields, lengths, numbered question bounds and
coverage ids; model verdicts cannot override deterministic rule failures.
The existing Check reply node checks only the top-level schema. A malformed
nested judge report may reach the graph's save step if its top-level verdict is
pass, but the harness rejects it before building or executing any target.
The ordinary designer labels output for manual review, never behavior-tested.

Before any target executes, the harness checks the exact saved bytes and SHA,
runs real `main.py build --check --json`, rejects all warnings, verifies the
12-type palette and all configured/effective file paths, and interprets a bounded
pure subset over every fixture. It inspects every node, including error routes.
Dynamic file paths, escaping symlinks, ordinary output fan-out, cycles,
unsupported source/routing overrides and unproven parallel Vault races fail.
Oracle version 3 checks expression lineage for every output and write. Each
required operation must act on the complete requested source and feed the
result; merely carrying a source-derived character or an unrelated operation
name is insufficient. Literal answer suffixes and partial-file reconstruction
are rejected. Conditional status messages must depend on the real tested input;
saved-path displays must come from the same writer's file reference. Each frozen case also declares `required_structure`: semantic roles, ordering
and producer relationships, and work assigned to each active fork port. The
common matcher has no case-id branches. It matches roles to actual node/config
and output evidence, requires the producer that really feeds each output, and
uses graph dominance, exclusive route reachability and recorded execution-route
membership. Work before a fork, after a shared join, on its sibling route or in
an unused decorative operation cannot satisfy a route. Every active route must
do nonterminal work; an End-only branch fails. All control nodes must be
accounted for by the declaration. Case 8 permits upper/lower port swaps; cases
7/9 fix the true/false work. Linear cases use the same role/producer checks.
The `required_structure` rule emits role mappings and route evidence separately
from expression provenance and output comparisons. Ambiguous candidate searches
are bounded and fail for review instead of being silently accepted.
Explicit
fixed messages (Ready, Continuing/Stopping, Empty note) and the original fixed
heading remain valid literals in their appropriate roles.
Configured reader/writer paths are mandatory for these frozen cases. Proven
sequential Vault data alternatives, Concat and JSON Path adapters are supported.
Legacy Text Output prompts, Start contracts, arbitrary formatting expressions and
other unsupported equivalents require a versioned oracle extension and review.

A separate library is **not** a filesystem sandbox. Only passing targets run,
using the saved workflow returned by `build_workflow`. All required variants
reuse one generated draft; they restore synthetic files, preserve original
sentinels byte-for-byte and check unexpected files, raw saved bytes, returned
paths, prompt count, output bodies and branch traces. Target runs use the same
whole-value display-framing matcher as case rules; exactly/only display clauses
remain strict. Each run artifact stores `output_records` with text and emitting
spec handle. The harness classifies output by that handle and removes exactly
that Text Output node's nonblank label prefix; bare bracketed user data survives.
Only actual End-node logs count as completion noise, recorded separately.
Saved file bytes and preserved sentinels remain strict. The missing-file case is a distinct required
failure fixture, not a warning waiver for generated workflows.

## Artifacts

The CLI prints the exact report path. All paths below are relative to the new
`runs/<run>/` directory, never the shared root or an earlier run.

- `report.json`: overall result, per-case results, counts, timings (p50/range),
  failure categories, `budget_usd`, `time_limit_seconds`, cost estimate and caveat; no-result is explicit failure.
- `calibration-report.json`: selected `judge_model`/`judge_effort`, attempted and
  succeeded `model_calls`, estimated cost, every good/bad rule verdict and judge verdict,
  false passes and false failures. Each row includes `judge_reply`: parsed JSON
  when it fits, otherwise redacted text capped at 4,000 characters. Reply
  evidence uses the same credential masking as run records. Canned judge
  verdicts are protocol tests. Exact question text is saved beside each
  calibration draft as `<variant>-judge-question.txt`; contracts remain in
  `artifacts/contracts.json`. Each question includes the actual Check workflow
  spec result, using the v2 check's helper and character limit. Negative fixtures
  that fail structurally include its error code and bounded problem details.
  Budget stops retain completed calibration rows.
- `artifacts/contracts.json`: complete text, length, hash and exact returned
  inventory from every static Compact query. Current palette text: 18,091 chars
  (before display-framing clarification: 9,928),
  comfortably below the 50,000-char planning cap. No entry is clipped.
- `cases/<id>/frozen-case.json`, `trial-designer.json`, `designer-run.json`,
  `evidence.json`, `calls.json`, `build-check.json`, `report.json`, exact saved
  draft, and `target-runs/`: original request/answer, first/resolved requirements,
  raw draft, structural/meaning reports, usage/cache tokens, serving models,
  node timings, input trace, save gate evidence and behavior receipts.

Unexpected or out-of-order prompts are not answered. Their trace row records
the actual prompt, node, `answer: null`, failure, and expected prompt when
applicable; earlier answered rows remain intact. Run evidence includes
`input_failure`. The designer's vault snapshot (`evidence.json`), call receipts,
run artifact and case report are saved before the case is marked failed.
Other cases still run when cost/time limits permit. Cost is unknown only for
unpriced usage or an adapter attempt without a receipt; a node/input failure
with all calls priced does not by itself make cost unknown. Priced partial
responses retain their costs. A calibration judge execution error still ends
calibration with a failed report and its completed evidence, independently of
the cost guard; the diagnostic cases flag retains its usual behavior.

The harness uses Check reply's shared decoded-record shape gate and the v2
spec's actual field declarations. Frozen protocol checks still require stable
ids, numbered clarification questions, complete judge coverage and empty
problems on pass. Requirement `order` accepts integers or nonempty strings,
including `1` and `"1"`; it no longer rejects a valid reply just for numeric order.

Adding equivalent graphs means openly versioning rules and calibration before
rerunning. Never change expected results to accept a generated mistake.

See [Step 1 verification](VERIFICATION.md) for the per-fixture results.

## Step 2 — separate owner approval

Step 1 makes no real calls. A real trial needs separate owner approval and the
owner adding `ANTHROPIC_API_KEY` to the **trial library** using the app. The
harness does not copy, inspect or print credentials. The app's normal Ask node
obtains its own key at execution, as in ordinary use.

### Owner commands (after separate approval)

From WSL, run from a checkout of main (e.g. `~/src/nw-main/AttackOfTheNodes`).
Use this block. Run the first two setup commands once. The root must
be fresh for `--prepare`; keep it for repeat trials. The app command really
selects that library before importing backend services (covered by a launch
regression test).

```bash
cd ~/src/nw-main/AttackOfTheNodes
TRIAL_PY=/home/makin/src/node_workflow/.venv/bin/python
TRIAL_ROOT=/home/makin/draft-trial-01

# a. Prepare once.
"$TRIAL_PY" -m tools.draft_trials --trial-root "$TRIAL_ROOT" --prepare

# b. Add ANTHROPIC_API_KEY in Options → Secrets, then close the app.
"$TRIAL_PY" main.py --data-dir "$TRIAL_ROOT/library"

# c. Run after owner approval; repeat this command with the same root.
"$TRIAL_PY" -m tools.draft_trials --trial-root "$TRIAL_ROOT" --real-calls --budget 0.50

# d. Read the first result. Repeats print their new report path.
cat "$TRIAL_ROOT/runs/000001/report.json"
```

There are 60 calibration judge calls before the selected cases (each ready
case may use one extra structural redraft). Earlier cost estimates predate this
family and require a new owner-run measurement. `--budget USD` has **no default** and is
required with `--real-calls`, even for calibration-only runs. Limits must be
positive finite numbers. `--time-limit SECONDS` defaults to 600. Both limits
are recorded in `report.json`, including failures.

The estimate guard includes calibration and checks **immediately before each
Ask adapter call**, including calls within one designer run. It stops before
further requests at the requested dollar limit, elapsed time limit, or unknown
cost. An exhausted calibration guard writes a failed report with the available
cost estimate. Capped replies (`max_tokens`) and refusals retain incomplete
usage receipts, so their known cost is included even though the error still
stops the trial. This is not a provider billing hard cap: a completed call can
cross the bound, SDK retries belong to that call, and charged failures may lack
usage. The time guard stops new calls; it does not interrupt one already in
flight, which retains its node timeout. Cache stays off initially. Calibration
precedes case generation; a real judge false pass stops the batch for an
owner-approved comparison, never automatic escalation. No real trial or
comparison was run in this Step 1 preparation change. Repeat runs reuse the
shared key through the app's ordinary provider without re-adding or copying it.


Judge diagnostics can run alone on a prepared root:

```bash
python -m tools.draft_trials --trial-root /absolute/prepared-root \
  --real-calls --budget 0.50 --calibrate-only \
  --judge-model claude-haiku-5-5 --judge-effort low
```

`--judge-model` accepts `claude-haiku-5-5` (default), `claude-sonnet-5-5`, or
`claude-opus-5-5`; `--judge-effort` accepts `low` (default), `medium`, or `high`.
These options affect only the judge in calibration and cases. Both reports
record the selections; `report.json` includes total attempted/succeeded calls
and estimated cost even when calibration fails or exhausts its budget.
Calibration-only skips all cases, whether calibration passes or fails. A failed
calibration still exits with failure. Mock mode remains the default; mock token
costs do not measure inference costs.

For diagnostic evidence after a failed calibration, add
`--cases-even-if-calibration-fails`. Without it, failed calibration skips all
cases as before. With it, the selected cases (all ten by default) run, but
`report.json` and stdout retain `calibration: "fail"` and overall
`result: "fail"`; the command exits 1 even if every case passes. Both record
`cases_even_if_calibration_fails`. `--calibrate-only` still skips cases even
when both flags are supplied. Cost/time/unknown-cost guards still apply before
each case and every real call; the flag cannot bypass an exhausted guard.
The v2 judge's `problems` contains only request-blocking defects, with harmless
remarks in `summary`. A pass still needs an empty problems list.

### Display scoring (oracle v4)

Requests to show a value accept a whole value surrounded by plain framing words,
for example `Saved path: {input[path]}`. The display clause's `exactly`/`only`
keeps strict body matching (a condition such as `type exactly yes` does not).
Only display evidence is unwrapped: downstream labels, saved content, full-source
provenance, actual writer path identity and route obligations remain strict.
The bounded oracle supports a single whole-value interpolation with plain ASCII
word/punctuation framing, not multiple fields, indexed fragments or path
prefixes. All 24 negative calibration drafts still fail.

The saved case 5 analysis in run 000006 asked unique filename versus no write.
The requirements prompt's former “Offer” default wording allowed that needless
question; it now applies the default and records it in assumptions. No request
or fixture was changed, and model behavior has not been retested with live calls.

### Empty-label runtime change (2026-10-29)

Empty or whitespace-only Text Output labels now emit/log bare formatted text.
Nonblank labels retain all their characters and add `[label] `. The symbolic
case evaluator and target-run extraction share the runtime prefix helper.
No frozen calibration fixture changed; the nonblank label in
`label_in_saved_content` still corrupts raw saved content and fails.

### One structural redraft

The first Check workflow spec error in v2 routes to one extra drafting step,
with the original brief, rejected raw draft and exact structured error. A
separate second Check must pass before the meaning judge runs. It never loops
back; a second structural failure stops without judge or save. An adapter or
meaning-review failure does not trigger redrafting.

`evidence.json` retains `first_draft_text`, `first_check_error`, final
`draft_text`, first/retry details and final `spec_check`. Each case report has
`draft_retry` with requested, attempted, succeeded and check_passed. SDK receipts
and the existing adapter boundary budget/time/unknown-cost guards cover the
extra call. `model_calls` records node attempts; the budget counts adapter calls
actually allowed past its guard. A recovered first check error remains in run
history even when the corrected draft passes.

## Choosing the request set

`--case-set 1` is the default and retains the original ten requests, variants and
rule expectations. `--case-set 2` selects a separate frozen version-1 set;
`--cases` still selects ids 1–10 **within that set**. Case numbers overlap across
sets, so stdout, run/case reports and frozen case artifacts record `case_set`.
Each run has its own directory and temporary fixture files as before.

Mock example (no API calls):

```bash
python -m tools.draft_trials --trial-root /tmp/draft-set-2 --case-set 2
```

| Set 2 id | Request / required outcome |
|---|---|
| 1 | Ask for a word; exact `Go` shows uppercase, other answers show lowercase, on exclusive routes. |
| 2 | Ask first name then last name; combine both answers with a single space. |
| 3 | Read JSON and show `person.nickname`, not the surrounding document. |
| 4 | Read, trim and uppercase text; Create unique, preserve older files and show actual path. |
| 5 | Missing source file path: ask a numbered file/path clarification, then reverse and show the specified file. |
| 6 | Email request: `outside_scope`, with a reason and no saved target draft. |
| 7 | Count words in new user text on each run: `needs_new_node`, with a reason and no saved target draft. |
| 8 | Two parallel paths from one answer: show uppercase on one; lowercase/write/show path on the other. Only one file write. |
| 9 | Method wording: copy the first/only line of an explicitly single-line file into a new file; a whole-file copy is equivalent. |
| 10 | Show a fixed message despite harmless conversational chatter. |

Definitions and reference drafts live in `case_set_two.py`, with a checked-in
snapshot at `fixtures/case_set_2.json`. The eight runnable cases have **23
behavior variants**, covering both conditional outcomes, two distinct answers,
changed JSON fields, Unicode, empty phrases, collisions and missing files.
Rules independently check whole-source lineage, both answer identities/order,
JSON projection, requested transforms, actual writer path, and required route
work. The real local target engine then checks output/file bytes and preserved
sentinels. Trim/uppercase order may commute because that changes no result.
The oracle accepts a bounded set of equivalent forms, not arbitrary English
or arbitrary workflow programs; unsupported forms fail with a rule id.

“Fully right” means `result: pass` / `fully_right: true`:

- Runnable cases pass clarification, structure, case rules, judge and all target
  variants. Case 5 specifically starts `clarify`, consumes the supplied path on
  the one clarify turn, then becomes `ready` and passes the same gates.
- Cases 6/7 return the expected status with a nonempty reason, no clarification
  question, one analysis call, no saved target draft and no target execution.
  `expected_outcome: status_only`, `status_check` and `no_saved_workflow` expose
  that proof. Structure/judge/behavior are `not_applicable`, not failures.
- Batch stdout/report show `case_set` and the `fully_right` count. A calibration
  failure still makes the overall run fail even if all case outcomes pass.

Concat has one wire input, not two independently named wire ports. Case 2 uses
two logical inputs: User Text Input's documented `membank_outputs` copies the
first answer to Vault, and Concat combines it with the second current input.
The method request explicitly guarantees a one-line source: arbitrary first-line
extraction is outside this palette and is not being hidden by the fixtures.

## Unreachable-node calibration and cost

Calibration is shared across sets and now contains **23 pairs / 46 judge
calls**, adding `unconnected_end` (clean two-path workflow versus that workflow
plus an unreachable End). Every earlier pair retains its expected rule verdicts.
V2's first check and retry check opt into `fail_on_unreachable`; other Check
workflow spec uses keep their default warning behavior. The exact structured
warning reaches the one redraft, and the reviewer treats disconnected nodes as
problems even if they appear decorative. The retry template uses real newlines.

A full set-2 run without redrafts has **75 hosted calls**: 48 calibration, 10
initial analyses, one clarification analysis, eight drafts and eight meaning
reviews. Using run 000010's recorded per-stage estimated costs gives **$0.09354**;
eight redrafts would project **$0.10966**. Allow roughly **$0.15** for planning.
These are projections under the same selections/prices, not a measured set-2
run or a billing cap. Harder outputs, different selections and caching can change
them. Details: `docs/audits/draft_trials_set_2_cost.json`. No new API calls were
made to estimate cost; existing budget/time/unknown-cost guards remain active.

V2 also enables `fail_on_disabled_output` on both structural checks and the
calibration check. A connected default output that publishes no payload now
triggers the same one redraft as an unreachable node, with exact diagnostic
text. A second failure stops before judge/save. Budget and usage accounting
still count the extra draft call. `disabled_transient` bad is now mechanically
rejected; all 23 pairs retain their expected rule verdicts. No fixture changes.
The optional second-analysis text is explicitly initialized so a status-only
first analysis does not rely on Concat silently filling a missing key.

## Structured reply schemas (2026-10-29)

Analysis, resolve and judge use generated closed JSON schemas, repeated on their
Check reply nodes for local validation. Candidate IDs and role IDs are generated
from `backend.palette_selection.ADMITTED` and `ROLE_TYPES`; status/verdict are
enums. Refresh the checked-in spec with:

```bash
python -m tools.draft_trials.reply_schemas --write
```

Tests require those schemas to equal the live generator, so palette/role changes
cannot silently leave stale enums. Selection stays separate from outcome
requirements. An unsupported capability without an allowed role returns
needs_new_node rather than an invented role. Draft and structural repair retain
reply_json plus Check workflow spec: arbitrary handle/config maps need an open
schema, which structured outputs disallow. No extra inference call was added.

The 24th pair, `end_framing_does_not_hide_missing_value`, uses identical connected
graphs and enabled End completion logs: GOOD shows Ready; BAD shows unchanged
Waiting input. The real local engine and case rules distinguish them even when
End noise is ignored. All previous 23 pairs are unchanged. There are now 48
calibration calls; totals without structural retries are 79 for set 1 and 75
for set 2. Mock SDK tests bind the actual SDK stream signature and inspect the
format/schema payload on all three supported routes, without provider calls.

Full verification: **4,548 passed, 187 skipped, zero xfails** (`pytest -n auto`,
38.22s); 24 calibration rule pairs retain their expected verdicts. No real API
calls. The original 23 frozen pairs are byte-for-byte equivalent when decoded.


## Helper family: set 3 (2026-10-30)

`--case-set 3` selects four requests / twelve fixture runs: inclusive excerpt,
interactive literal search with a handled `no_matches` route, JSON reply shape
validation and summary extraction, and a two-source labelled Context Pack.
Each file reader uses a literal configured path. Each target run explicitly
sets `system_node_folders` to that case's fixture directory only; its execution
artifact records that setting. These settings are a read-scope check, not an OS
sandbox. No new target writes files or contacts a service.

Sets 1 and 2 retain exactly their original twelve types and seventeen role IDs,
including the word-count `needs_new_node` and email `outside_scope` cases.
`fixtures/admission_baseline.json` pins those IDs, all original requests,
structures, reference drafts, variants and the first 25 calibration pairs by
canonical digest. Scope is applied to the actual Brief lookup, discovery,
selection/expansion and analysis/check schemas; it is not only prompt wording.
Default delivery uses all sixteen admitted types / twenty-one roles.

Five new pairs cover whole-file versus excerpt, configured search overriding
an answer, a wrong no-match message, rejecting permitted extra JSON fields and
a pack that ignores its answer. The pack pair is explicitly held out from prompt
tuning. The base already contained 25 pairs (including the held-out reversed
empty check); all remain unchanged, giving 30 pairs / 60 judge calls now.
Per-pair `contracts.json` preserves the exact context the judge received;
original pairs retain the twelve-type baseline, helper pairs get all sixteen.
The judge prompt is unchanged.

The set-3 oracle invokes real local execute methods with tiny temporary fixtures,
fixed snapshots and empty fake Secrets, comparing independent expected values.
It observes active input/Vault reads for lineage, so a configured-source wire
cannot masquerade as a consumed value. Shared authoring checks own graph/type
validity; the existing structure matcher owns frozen case intent. Target fixtures
then run through the real engine as a separate delivery check. Positive alternate
Vault routing, direct JSON projection and renamed handles are tested.
Mock reports are plumbing and behavior evidence, not live drafting quality.

Requirements may include `kind: "action" | "constraint"` before `acceptance`;
when omitted it means `action`. Prohibitions and limits are constraints, not
steps, so only action requirements need shortlist role coverage. All requirements
remain frozen for draft/judge, with judge coverage and case safety rules unchanged.
This general schema field changes neither admission nor frozen sets 1/2.

Schemas are regenerated with `python -m tools.draft_trials.reply_schemas --write`.
The exact enum lists and contract sizes are recorded in
[the admission receipt](../../docs/audits/claims_baseline_2026_10_29/helper_family_admission.json).
The full catalogue is Brief 15,794 / Compact 57,781 characters after the PR #158
follow-up restored per-node standard-flag and Configured descriptions. The
sixteen-type view is 8,484 / 26,444. Caps remain unchanged: full catalogue 64,000,
selected contracts 50,000 and model context 100,000. Representative selection
snapshots use 8,500–11,929 characters including their receipts. The full registry
fits its hard cap; selected contracts retain the 20% planning headroom check.

### Follow-up: admitted types versus oracle limits

The local family probe follows actual `output_port` packets, including
Conditional's true/false value forwarding, and directly evaluates all audited
sequential local types. Extra Conditional guards are allowed when observed
outcomes and requested producer lineage hold; frozen sets 1/2 keep their exact
branch-layout obligations. The copied run 000035 case-3 draft is an engine-backed
regression fixture. Its only normalization is the configured fixture file root.

A safe admitted composition the local oracle cannot certify (for example
parallel scheduling or dynamically sourced File Reader references) returns
`needs_review`, not a draft failure. Such a case is
not fully right and does not execute target fixtures. Its batch and stdout also
report `needs_review` unless a separate known failure takes precedence; the CLI
exits nonzero. `reviews_needed` lists these cases separately from `failures`.
Known invalid structures, unsafe paths and wrong observed results still fail.

Selection repair occurs after duplicate folding: drop Start/End candidates with
undeclared roles because support already includes them; reassign any other
undeclared candidate role only when its type occurs in exactly one declared
role's reviewed alternatives. Otherwise retain the error. No extra inference
call or rewrite of the recorded requirements is involved.

## Cheaper iteration: saved replies, shared calibration and affected sets

```bash
# One fresh self-test for all selected suites, not one per suite:
python -m tools.draft_trials --trial-root /absolute/trial --case-set all
python -m tools.draft_trials --trial-root /absolute/trial --case-set 1,3 --cases 1,2

# No provider calls; infer the suite and recorded case IDs from the source:
python -m tools.draft_trials --trial-root /absolute/replay-trial \
  --replay ~/draft-trial-01/runs/000041

# Committed, staged, unstaged and untracked paths relative to the base:
python -m tools.draft_trials --trial-root /absolute/trial --affected origin/main
```

`--case-set` defaults to 1 and accepts distinct comma-separated IDs or `all`
(1,2,3). Calibration always runs once, with every current good/bad pair, before
any selected case. A multi-set run writes one root `calibration-report.json`
and `set-<n>/report.json` for each set; the root report embeds those sections.
`fully_right` remains per set. Per-set call/cost totals exclude shared calibration;
the invocation totals include it once. Budget, elapsed-time and unknown-cost
guards cover the entire invocation without resetting between sets. Failed
calibration blocks cases unless explicitly running the diagnostic override;
even with that override, the overall result remains fail. Sets 1/2 retain the
exact original twelve-type admission/contracts; set 3 retains its sixteen types.
For multi-set `--replies`, use `{ "1": { "1": [replies...] }, "3": ... }`;
single-set overrides retain the original case-ID object format.

Replay is mock-only and cannot combine with `--real-calls`, `--replies`,
`--prepare` or nondefault `--scenario`. The source tree is validated before
creating output; outputs cannot be inside the saved source run. Replay reads
published replies and AI execution order from each case's evidence/run files,
plus the saved per-pair judge replies. It relocates only that case's original
fixture root into a fresh fixture directory and preserves recorded user answers.
First drafts and structural retries stay separate. It never falls back to the
canned good draft or judge answer. Missing/unpublished/truncated reply evidence,
a new AI call or a mismatched stage stops that case/variant as `replay_diverged`;
remaining cases and calibration pairs are still checked. A new deterministic
rejection is a newly failing case, not a reason to consume leftover replies.

The current selection/Check reply/spec checks, case rules, bounded real-engine
fixtures and all calibration rules still run through the existing gates.
Reports include `same_outcome`, `newly_passing`, `newly_failing`, `diverged`,
consumed/remaining replies, original/current outcomes and `real_api_calls: 0`.
Replay runs the saved cases diagnostically even after failed calibration; it
still cannot report an overall pass without passing calibration. Replay is
`execution_mode=stub`: recorded inference, fake Secrets and blocked network,
with real local nodes/engine. It measures deterministic handling of old answers,
not how changed prompts/contracts would affect a fresh model answer.
The committed `fixtures/replay_small/` is a minimal saved **mock** run, not paid
evidence. A replay source can itself contain a multi-set invocation.

Calibration reuses the unchanged complete contract text in the node's existing
Context input, enabling `claude_cache_context = "5 min"` for that isolated
RunService's setting lookup only. No settings file is changed, including the
prepared key library and the owner's normal settings. The existing adapter
serializes cached Context before the question; the question text and the order
of all judge-template sections are unchanged. There are two reusable prefixes:
the frozen twelve-type contracts and the admitted sixteen-type contracts.
`calibration-report.json.cache` reports ordinary/output/cache-read/cache-write
tokens, estimated cost, the same tokens priced without caching and savings
(which may be negative on a cache write). Unknown usage stays unknown. Mock or
replay counts are explicitly synthetic, never a measured inference charge.

`dependencies.py` owns reviewed dependency index v1. Suite/oracle paths map to
their owning set. It reuses case family/helper/used-type/candidate-alternative
tags, expected compositions and reviewed metadata source dependencies. Shared
prompts, serving, catalogue, metadata, selection and harness/routing changes
select all. Any unmatched path, or no changed paths, selects all; never zero.
Git renames inspect both old/new paths. The selection and skipped-set reasons
are printed to stderr and retained in stdout/report JSON. An explicit
`--case-set` adds requested coverage to affected coverage, never excludes it.
The complete universal calibration core still runs for an affected-only family.
Affected-only runs shorten iteration; they do not replace full release checks.

To reproduce the conservative paid `all` projection from saved SDK counts:

```bash
python -m tools.draft_trials.costing \
  ~/draft-trial-01/runs/000039 ~/draft-trial-01/runs/000040 \
  ~/draft-trial-01/runs/000041
```

Those runs yield **130 calls** (60 calibration + 31/27/12 case calls),
**1,074,097 input / 140,169 output tokens**, approximately **$0.1774942** before
any cache savings, using the adapter's checked-in prices. Calibration from the
last supplied run is charged once. This assumes historical reply lengths and
repair counts, with no guessed character/token ratio or cache-hit rate; the
next owner-approved paid run reports actual cache reads/writes and savings.

Verification on the step-A branch from `a1d5363` (2026-10-30): full
`python -m pytest -n auto` **4,756 passed, 187 skipped**, zero xfails (46.12 s).
All mock sets pass (10/10, 10/10, 4/4), as do all thirty mechanical calibration
pairs. A separate multi-set CLI round trip also replays its saved replies.
Owner run replays made zero real API calls:

| Source run | Same outcome | Newly passing | Newly failing | Diverged |
|---|---:|---:|---:|---:|
| 000039 (set 1) | 10 | 0 | 0 | 0 |
| 000040 (set 2) | 10 | 0 | 0 | 0 |
| 000041 (set 3) | 4 | 0 | 0 | 0 |

All sixty judgment-variant comparisons are unchanged in each replay. Run 000039
keeps its failed calibration and therefore remains an overall failure despite
its 10/10 case score. Runs 000040/000041 keep their 9/10 and 3/4 case scores.
No judge prompt, frozen expected result, backend service or workflows/ edit.
