# Draft a workflow

[Authoring spec](draft-a-workflow.json), [delivery case](../draft-a-workflow.json),
[approved sample fixtures](../fixtures/draft-a-workflow.json).
Owner approved the eleven recommended decisions and three samples on 2026-10-27.
This is the authored designer, checked without installing or running it.

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

Brief is 6,207 characters; all complete Compact fragments joined are 6,865,
including headers. They reach Context intact, without Context Pack truncation.
The exact counts are tied to base `cfd3458`; registry growth may hit the 7,500
catalogue/planning budget or hard 8,000 Context cap and stop rather than clip.
The shortlist uses a 300 s timeout / 256 output tokens; drafting uses 600 s /
1,024 tokens. Both use JSON replies, thinking off, temperature 0.2 and a context
window of 8,192. Model override is empty: use the owner's Options default.
The 500-character request limit is guidance, not a new input gate.

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
designer or create its output folder. No workflow or model call was run for this
PR. The separately approved measured trial is **after review**, not this step.
Future setup: confirm Options URL/default and permission for the fixed destination,
then explicitly authorize installation/trial in the intended data root. Keep local
requests/specs free of credentials; generated target-file paths still need review.

## Re-check the recipe

`tests/test_draft_workflow_spec.py` checks the spec without node execution,
saving/building or network access. It verifies the success gate, failure-stop
paths, acyclic graph, exact limits, current complete palette and sample verdicts.
The three fixtures are hand-authored: clean pass, warning-only pass, bad fan-out
refusal. They measure checker behavior, not inference quality or runtime.
CPU time, generated-spec quality and real-device proof remain unmeasured.
