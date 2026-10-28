# Draft workflow trials — Step 1

This is an external test harness, not a new workflow node or a general English
requirements prover. The frozen oracle in `cases.py` implements the approved
10-case TEST_SET (version 1). `fixtures/calibration.json` contains 15 paired,
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

The root must not exist. The runner creates its own `library/`, `cases/`,
`calibration/` and `artifacts/`. It builds both designer versions into that library
with distinct names, then executes only v2. Every CLI build/check subprocess
receives `--data-dir <root>/library`; every RunService worker inherits that root
before backend imports. No default library or owner settings are copied.
For programmatic use, set `AOTN_DATA_DIR` **before backend imports**, as the CLI
does; changing the environment after imports cannot relocate cached data paths.

Each case freezes its rendered request, clarification, expectations and fixture
variants before generation. Only the designer's draft destination is changed
to `cases/<id>/drafts/draft.json`; that trial variant is saved in
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

- `report.json`: overall result, per-case results, counts, timings (p50/range),
  failure categories and cost caveat; no-result is explicit failure.
- `calibration-report.json`: every good/bad rule verdict and judge verdict,
  false passes and false failures. Canned judge verdicts are protocol tests.
- `artifacts/contracts.json`: complete text, length, hash and exact returned
  inventory from every static Compact query. Current palette text: 9,364 chars,
  comfortably below the 50,000-char planning cap. No entry is clipped.
- `cases/<id>/frozen-case.json`, `trial-designer.json`, `designer-run.json`,
  `evidence.json`, `calls.json`, `build-check.json`, `report.json`, exact saved
  draft, and `target-runs/`: original request/answer, first/resolved requirements,
  raw draft, structural/meaning reports, usage/cache tokens, serving models,
  node timings, input trace, save gate evidence and behavior receipts.

Adding equivalent graphs means openly versioning rules and calibration before
rerunning. Never change expected results to accept a generated mistake.

See [Step 1 verification](VERIFICATION.md) for the per-fixture results.

## Step 2 — separate owner approval

Step 1 makes no real calls. A real trial needs separate owner approval and the
owner adding `ANTHROPIC_API_KEY` to the **trial library** using the app. The
harness does not copy, inspect or print credentials. The app's normal Ask node
obtains its own key at execution, as in ordinary use.

After approval, prepare a fresh root and stop:

```bash
python -m tools.draft_trials --trial-root /absolute/approved-root --prepare
# Owner opens the app with --data-dir /absolute/approved-root/library,
# adds the key through Options → Secrets, then closes the app.
python -m tools.draft_trials --trial-root /absolute/approved-root --real-calls
```

`--real-calls` is off by default; it accepts only a fresh or untouched prepared
root. Cache stays off initially. The estimate guard includes calibration and
stops before further calls at $0.10, 600 seconds or unknown cost. It is not a
provider billing hard cap: a completed call can cross the bound and charged
failures may lack usage. Reports record that limitation. Calibration precedes
case generation; a real judge false pass stops the batch for an owner-approved
comparison, never automatic escalation. No such trial or comparison was run
in Step 1. Repetitions require fresh roots and the approved later budget.
