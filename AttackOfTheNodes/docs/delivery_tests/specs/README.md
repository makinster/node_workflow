# Draft a workflow

[Authoring spec](draft-a-workflow.json), [delivery case](../draft-a-workflow.json),
[approved sample fixtures](../fixtures/draft-a-workflow.json).
Owner approved the eleven recommended decisions and three samples on 2026-10-27.
The original PR checked the authored designer without running it. The later
owner-authorized decision 11 trial ran once on merged `398c482`: 70.64 s CPU,
two calls, Check failed on display-annotated port ids. No success file or
target build/run. The separately owner-approved re-trial on `8945c3d` passed
in 75.14 s with two local calls and zero Check warnings. The saved raw draft
passed build --check, was built only in a fresh trial library and ran once:
`[Ready Output] Ready`. It also emits an End completion line, unlike the quiet
sample. Full measurements, both trials and raw drafts are in the delivery case.

The medium trial on `80e4315` took 99.23 s with two calls, default cap 8,000,
zero Check warnings and no token-fit warning. Reference's one unreachable-node
warning was absent because the draft omitted the unused preview. Saved-file
check passed, but target was not built/run: its `/tmp` write violates the
trial-folder-only condition. It also uses `{{input}}` in Text Output, yielding
literal `{input}` instead of a path. No prompt/spec fix or retry was attempted;
this is not medium end-to-end proof.

The designer uses existing nodes only. Its **drafting palette** is nine types:
Start, End, Merge Beacon, Parallel Branch, User Text Input, Text Output,
Text Transform, File Reader and File Write. The designer's own meta/helper nodes
are additional existing types, not additions to that drafting palette.

Request → Brief → JSON shortlist → shape/status check → eight fixed Compact
queries → JSON draft → Check workflow spec → File Write → draft/report/path → End.
The shortlist advises drafting; it does not change the static catalogue filters.
A non-`ok` status explains scope/uncertainty and stops. All preparation/service/
validation/write errors go to a readable problem message and End. There is no
retry, automatic build, approval node, shell execution or generated-workflow run.

Current registry with the hosted-question node: Brief **7,634** characters;
fixed palette **7,421**, both below Context 8,000. Brief catalogue max is now
8,000 (previously 7,500); runtime Context setting and approved prompts are
unchanged. No designer/model call accompanies this maintenance.

Historical measurement: with the Context-limit description update, Brief is 7,447 characters; all
complete Compact fragments joined are 7,421, including headers. They reach Context intact, without Context Pack truncation.
The Brief count is measured on the Context-limit change from `e7d07e8`. That older 7,500 catalogue cap is superseded above. Further registry growth
can reach the current 8,000 Context/catalogue budget and stop rather than clip.
Options can raise Context independently of a workflow’s catalogue cap.
The shortlist uses a 300 s timeout / 256 output tokens; drafting uses 600 s /
1,024 tokens. Both use JSON replies, thinking off, temperature 0.2 and a context
window of 8,192. Model override is empty: use the owner's Options default.
The 500-character request limit is guidance, not a new input gate.

Text ports now show ids separately from quoted display names, with an id-only
connection legend. Brief uses `default "Greeting"`; Compact/Detailed use
`default ("Greeting") [string]`. The draft Question includes a literal
`{"from":"start.default","to":"show.input"}` example (doubled braces in the
stored Concat template, single braces when rendered). The port-id fix changed
no query, JSON format, call setting or workflow path.
Ask local model now supports an Options Context cap and per-node override;
this spec keeps the default and its separate catalogue budget unchanged. This revised
spec passed the separately authorized re-trial unchanged. The prior failed
trial used old Text/prompt; its original library was not modified. The new
library is `/home/makin/.local/share/aotn-draft-workflow-retrial-2026-10-27`.
No further inference or ordinary use was tested.

The raw Answer goes into `draft_text`. That exact text is checked with an
8,000-character limit. Only Check's success wire reaches File Write; its Content
source is Vault `draft_text`, not the parsed success payload. No sibling writer
can change it. File Write uses Create unique under
`/home/makin/src/agent_channel/draft-workflow-output/`, with newline interpretation
and automatic opening off. Run one designer at a time: Create unique is not an
atomic multi-process reservation. A failed write may leave a partial file;
its error path offers no success command.

On success, the owner sees the original draft, all bounded report problems,
warning/omission counts, actual returned path and literal `aotn build '<path>'`.
Warnings pass but remain visible. Passing checks does not prove request fidelity,
palette compliance or runtime behavior. Prompt restrictions are not a security
boundary. Review the exact file and warnings before manually building it.
Build saves a workflow; it does not run it.

## Review without running

From `AttackOfTheNodes/`, use the intended checkout interpreter:

```bash
python main.py build docs/delivery_tests/specs/draft-a-workflow.json --check --json --data-dir /tmp/aotn-designer-check
```

This check needs no inference endpoint or credentials. It does not install the
designer or create its output folder. No workflow or model call was run for the original
PR #126. The separate trial after review is now recorded above.
Future setup: confirm Options URL/default and permission for the fixed destination,
then obtain separate authorization before any further trial in that data root. Keep local
requests/specs free of credentials; generated target-file paths still need review.

## Re-check the recipe

`tests/test_draft_workflow_spec.py` checks the spec without node execution,
saving/building or network access. It verifies the success gate, failure-stop
paths, acyclic graph, exact limits, current complete palette and sample verdicts.
The three fixtures are hand-authored: clean pass, warning-only pass, bad fan-out
refusal. They measure checker behavior, not inference quality or runtime.
CPU time, generated-spec quality and real-device proof remain unmeasured.

## Draft a workflow v2 — Step 1

`draft-a-workflow-v2.json` is the revised recipe; the original spec is unchanged.
It analyzes requirements, permits one clarification turn of at most three
questions, drafts with the fixed 12-type palette, checks the structure, and asks
for an independent meaning review. Only the exact verdict `pass` reaches File
Write (Create unique). Other verdicts, unresolved requests and errors explain
what needs review and stop. There are no repair loops or automatic target runs.
All four Ask steps use the explicit approved hosted option, low effort and JSON
replies; the clarify path adds the fourth call only when needed. Stable complete
contracts are Context; changing request/requirements/draft are in Question.

The extra Compact queries cover Conditional, Concat and JSON Path. All returned
entries are retained: the current exact inventory is 12 types and assembled
Context is **9,364 characters**, below the 50,000-character planning budget.
Check workflow spec retains its 8,000-character raw-draft cap. Check reply checks
top-level fields; numbered-question and nested requirement/coverage checks live
in the external trial runner. The ordinary success output says manual review
required and not behavior-tested, with both reports and the actual saved path.

From the app directory, run a fresh **mock-only** trial:

```bash
python -m tools.draft_trials --trial-root /absolute/fresh/trial-root
```

The [runner guide](../../../tools/draft_trials/README.md) explains case rendering,
ordered `InputProvider` answers (no PTY), calibration, safety checks, fixture
runs, per-case evidence and negative scenarios. It creates an isolated library per run under `runs/<run>/`;
never pass the owner's library or copy settings/Secrets. `--real-calls` defaults
to off. **Step 2 requires separate owner approval and the owner adding the key
to the trial library through Options → Secrets.** Use the documented `--prepare`
flow first. Prepared roots are reusable with a stable shared key library; each
run gets a fresh artifact directory. Real mode requires an explicit `--budget`
(recommend `0.50` for the full batch); `--time-limit` defaults to 600 seconds.
See the runner guide for the exact owner commands and report paths. Step 1's canned replies are engine/harness proof, not real-model
quality, latency, cost or interactive CLI proof.


PR #135 review follow-up: the runner now validates the entire prepared-root tree
and exact preparation record before writes or backend imports. Symlinks, hard
links, special entries and resolved escapes are rejected. The frozen oracle is
version 2: per-value source/operation lineage rejects hardcoded heading answers
and partial-file reconstructions. Calibration now has **19 good/bad pairs**
(original 15 plus four provenance regressions). The v2 designer spec is unchanged.


PR #135 route follow-up: oracle version 3 freezes structural obligations for
all ten cases. A shared matcher checks required operations and displays on their
own declared routes, requires real work on every branch, and binds outputs to
the actual producer node. This rejects correct-looking values produced serially
on one parallel path. Cases 7/9 also require true/false work after their own
Conditional route. The original 19 pairs remain; three new pairs cover serial
parallel work, pre-Conditional displays and pre-Conditional uppercase work.
Calibration is now **22 pairs**. The designer spec remains unchanged.
