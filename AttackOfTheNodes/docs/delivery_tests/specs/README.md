# Draft a workflow

**Status (2026-10-29): v1 is deprecated; v2 is the maintained recipe.** Node
metadata record v1 / catalogue schema 2 (`backend/node_metadata.py`) made
Brief purpose-first and renamed the Branch purpose. The original spec below is
kept unchanged with its historical evidence, but it needs its pinned old app
and catalogue: on current main its `Duplicates input` Branch query matches
nothing, Brief is larger than its 8,000 cap and its contracts no longer fit its
8,500 Context. Do not grow its local prompts; any new v1 use needs a new local
fit/quality trial. Its historical numbers below refer to that old catalogue.

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

Current registry: Brief **7,634** characters, fixed palette **8,256**
(previously **8,168**). The original designer's drafting node explicitly sets
Context to **8,500** (previously the 8,000 default); Brief's cap stays 8,000.
No designer/provider call accompanies this maintenance.

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
The judge allows 4,096 output tokens and asks for short reasons (under about
150 words). Initial/resolved requirements allow 2,048 each; drafting retains
4,096. Character/schema checks and success gates are unchanged.

The extra Compact queries cover Conditional, Concat and JSON Path. All returned
entries are retained: the current exact inventory is 12 types and assembled
Context is **18,091 characters** with node metadata record v1 (previously
**17,736**), below the unchanged 50,000-character planning budget with more than
the required 20% headroom. Brief has an explicit 50,000 cap (15,037 characters
now); each Compact query uses 16,000. The Branch query is `Branch` group plus
the words `parallel simultaneous` from Parallel Branch's use_when (the old
`Duplicates input` wording is gone); its frozen inventory is `branch_node` only. Compact includes config defaults
and marks only fields without defaults as required. The meaning judge delegates
config completeness/validity to Check workflow spec; omitted defaults are allowed.
All twelve types now describe output payloads; generated Configured-source lines
explain trigger-only incoming values. File Write describes its actual `path`
key and unique-name collision rule; Conditional describes exact equals matching.
The judge reserves `problems` for request-blocking defects; remarks go in
`summary`, and a pass still requires empty `problems`.
Text Output's label is display framing, even for exact-text display requests;
both its log and downstream value contain the prefix, so saving that downstream
value also saves the label.
Check workflow spec retains its 8,000-character raw-draft cap. Check reply and
the trial runner share the decoded top-level shape gate, with the runner reading
the actual analysis/resolved/judge field configurations from this spec.
Numbered-question and nested requirement/coverage checks remain frozen protocol
checks in the runner. Requirement order accepts an integer or nonempty text
(including numeric strings and existing descriptive orders). A pass still needs
complete coverage and empty problems. The ordinary success output says manual review
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

The requirements prompt now applies Create unique and no automatic opening as
assumptions, rather than asking to confirm these defaults. Creating a new file
while preserving existing files means create a unique copy; stopping without
writing does not complete that request. Explicit restrictions/conflicts still
require clarification. The run 000006 case 5 evidence asked exactly this
unnecessary collision question; the case/request remains unchanged.

The analysis and resolve prompts must not invent “exactly”, “nothing else” or
“only” display acceptance unless requested for that value. End completion logs
are normal run framing. Blank or whitespace-only Text Output labels now produce
bare text; set labels retain their literal prefix. This runtime change applies
to logs, downstream payloads, legacy Vault writes and the configuration preview.

After the first Check workflow spec failure, v2 sends one structural repair
request containing the original drafting brief, rejected raw draft and exact
structured check error. The corrected raw draft replaces `draft_text` and goes
through a separate Check node before the meaning judge. A second rejection
ends through the failure path; there is no loop. Transport/adapter failures and
meaning-review failures do not trigger this structural retry. The trial budget
and usage accounting include the extra drafter call; evidence keeps both raw
drafts, first check error and retry status. See `tests/test_draft_structural_retry.py`.

Requirements describe user-visible outcomes and data/files, rather than node
wiring. The judge evaluates ordinary requested inputs, without inventing edge
cases such as line-ending formats. Start passes its greeting to the next node
as input and shows nothing itself. End logs only `[END] <message>`, never its
input. Compact contracts include shared `transient_output` behavior for every
type that declares that config option, including its actual default.

V2's Check nodes both enable `fail_on_unreachable`. A disconnected/decorative
node triggers the one structural redraft; a second rejection stops before the
judge/save. The judge likewise treats unreachable or unconnected nodes as
request-blocking problems. The retry question now has actual newline characters.
All other checker clients retain warning behavior by default.

The trial harness has `--case-set 2` for ten separate harder requests; set 1 is
still the default. Its clarification, outside-scope and missing-node outcomes
are explicitly scored without pretending they are runnable workflows. See the
[trial guide](../../../tools/draft_trials/README.md#choosing-the-request-set).
Shared calibration now has 23 pairs. The User Text Input contract documents its
existing answer-to-Vault copy option so a two-answer Concat is discoverable.
Current complete contracts: **18,271** characters; Brief: **15,037**. Caps hold.
