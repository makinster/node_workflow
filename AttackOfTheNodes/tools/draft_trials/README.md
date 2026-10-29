# Draft workflow trials — Step 1

This is an external test harness, not a new workflow node or a general English
requirements prover. The frozen oracle in `cases.py` implements the approved
10-case TEST_SET (version 3). `fixtures/calibration.json` contains 22 paired,
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
paths, prompt count, output bodies and branch traces. OutputManager's known
`[label] ` wrapper is removed exactly once; bracketed user data survives. End
noise is recorded separately. The missing-file case is a distinct required
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
  inventory from every static Compact query. Current palette text: 10,275 chars
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

Recommend **$0.50 for a full run**. There are 44 calibration judge calls before
the ten cases; calibration alone is about $0.12–0.15 at current planning
estimates, not a measured Step 1 result. `--budget USD` has **no default** and is
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
prefixes. All 22 existing negative calibration drafts still fail.

The saved case 5 analysis in run 000006 asked unique filename versus no write.
The requirements prompt's former “Offer” default wording allowed that needless
question; it now applies the default and records it in assumptions. No request
or fixture was changed, and model behavior has not been retested with live calls.
