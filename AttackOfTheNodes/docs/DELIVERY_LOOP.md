# The AOTN delivery loop

Turn an intention into something the owner uses. Keep one small record per
request, with links to decisions, samples, PR, setup and real-device proof.
This is a working method; the automation at the end is direction, not approved work.

## The loop

Each step names its purpose, input → output, who does it, and its finish line.
A failed check returns to the relevant earlier step; record the reason.
Owner approval applies to the exact recorded scope/version, not later changes.

**0 · Intent.** Make the need concrete. Owner supplies a wish → agent writes a
workflow request (below). Owner + agent. Done: a real example, target device
and observable success are clear; unknowns are written down.

**1 · Feasibility research.** Find out whether the outside system permits it.
Request → dated feasibility verdict with official sources and setup needs.
Agent researches; owner supplies account/device facts. Done: API, sign-in,
cost, reliability and terms are checked, or explicitly unknown. A blocked
verdict stops building; conditional work waits for its named conditions.

**2 · Map to existing nodes / gaps.** Reuse before inventing.
Request + verdict + current node contracts → workflow outline and gap list.
Agent maps; AOTN `nodes` / `describe` supplies contracts. Done: every useful
workflow step has an existing node or a precise gap, with ports and sources.
Classify the request and count coverage here.

**3 · Owner decisions — APPROVAL.** Settle meaningful tradeoffs.
Outline + open questions → recorded choices and build scope. Agent presents
short options; owner decides. Done: required choices are answered, including
cost/permissions; unresolved choices block dependent work.

**4 · Samples — APPROVAL.** Check what the owner will actually see.
Chosen scope + real input → sample screens/messages, including long text,
errors and upstream replies. Agent prepares; owner approves the version.
Done: expected behaviour and the actual device/width are represented, and
approval is recorded. For invisible changes, approve input/output examples.

**5 · Build.** Make the agreed design concrete.
Approved scope/samples → workflow spec or focused node PR, checks and docs.
Agent builds; AOTN checks specs and executes isolated tests. Done: `build
--check` and relevant checks pass; gaps, setup and limits are documented.
A composition-only request may need a spec rather than application code.

**6 · Review / fix / re-check.** Find and close realistic serious issues.
Exact candidate head + evidence → findings, fixes and clean re-check.
An agent other than the author reviews; builder fixes; AOTN runs checks.
Done: blocking findings are reproduced, fixed and re-checked on the new
head. Put rare nonblocking cases in the backlog. Count every review round.

**7 · Merge.** Land the reviewed result.
Reviewed head + current main → merged commit, or accepted versioned spec
for a request with no code PR. Owner merges, or explicitly delegates;
agent reconciles main and checks the combined result. Done: record the
accepted revision and retain other workers' docs/log entries.

**8 · Go-live — APPROVAL.** Connect the accepted result to real life.
Accepted revision + one setup checklist → installed/configured workflow.
Agent prepares and checks; owner approves activation and supplies sign-in
or secrets; AOTN performs the approved run. Done: paths, permissions,
destinations, limits and rollback are checked and setup evidence recorded.
Merge alone does not authorize live sends, spending or schedules.

**9 · Prove on the real device.** Verify the whole path.
Live setup + test input → run receipt and owner-confirmed device result.
AOTN runs; agent checks receipts; owner confirms the phone/Echo/terminal.
Done: the expected message/action is visible there, including agreed failure
or silence cases. Queued/handed-off is not delivered; delivered is not read.

**10 · Use and observe.** Learn from ordinary use.
Device proof + daily use → dated usefulness, failures, noise and cost notes.
Owner uses; AOTN records runs; agent examines agreed observations.
Done: an agreed observation window ends, with evidence or explicit unknowns.

**11 · Retro.** Improve the next request.
Loop record + observations → lesson, measurements and a delivery test case.
Owner + agent reflect; AOTN may later aggregate. Done: record what to reuse,
what to change and any follow-up; assign it without implying approval to build.

## Lessons from real runs

These are dated project lessons, not a fresh survey of outside services.

- C1 Notify me (#109), **6/9**: cross-review caught torn queue lines and failed-write repeats; owner Telegram confirmation proved more than an outbox receipt.
- C3c investigation inbox (#117), **3/9**: the owner chose AOTN-gathered evidence and tool-free analysis; the fake full-disk incident then reached Telegram end to end.
- Pick one (#112), **4/5**: approve the small choice task and plain choice id; low confidence routes to `unsure` instead of inventing a general agent.
- Context Pack (#120), **4/6**: show realistic upstream context, then check escaped Secrets, caps and omission notes in the final rendered pack.
- #119 redaction, **6/11**: four review rounds exposed multiline/boundary leaks; test both persisted inbox and worker output, preserving harmless text too.
- Alexa lists, **1**: the 2026-10-26 research found the official lists route closed; stop and reconsider before designing an integration around it.
- Hermes profile (#116), **1/3**: research replaced an always-refusing route with a supported isolated tool-free profile; profile isolation is not an OS sandbox.

Evidence: [Current State](CURRENT_STATE.md), [Session Log](SESSION_LOG.md),
[AI coordination](AI_COORDINATION_PROPOSAL.md). The external coordinator's
2026-10-26 notes and delivery-loop field guide supplied the loop and Alexa
lesson; they are local working notes, not a repository/runtime dependency.
Recheck official service facts at step 1 of a new request.

## Copyable templates

### Workflow request

- Request id and date:
- Intent: what should happen, for whom, and why?
- Example input → expected result:
- Target device and destination:
- Trigger and frequency:
- Available inputs/accounts; secret names only:
- Constraints: cost, time, privacy, permissions:
- Success: what the owner must see; failure/silence behaviour:
- Unknowns and owner decisions:

### Feasibility check

- Request id; checked date; researcher:
- Official API? Link and scope; supported, unsupported or unknown:
- Sign-in? Account, OAuth/setup, secret storage; owner action needed:
- Cost? Price evidence, expected frequency and ceiling; unknown if unreported:
- Reliability? Rate limits, timeouts, unofficial dependencies, failure plan:
- Terms of service? Official source and relevant restrictions; unknowns:
- Verdict: feasible / conditional / blocked. Why? Conditions and alternatives:

Machine forms: [request schema](templates/workflow_request.schema.json),
[filled request](templates/workflow_request.example.json),
[feasibility schema](templates/feasibility_check.schema.json),
[filled verdict](templates/feasibility_check.example.json).
These are small JSON Schemas, version 1; `required` lists mandatory fields,
`properties` gives types. Example documents carry integer `schema_version: 1`.
Keep unknowns explicit; do not infer approval from a filled form. These records
are planning data, not `aotn-workflow/1` specs. A future Check reply step can
check expected fields/types; full schema validation is a separate check.

### Review by node kind

Use every applicable list, plus the standard [node rules](NODE_STANDARDS.md)
and [contributing checks](CONTRIBUTING.md). Review the real data path.

- **File access:** authorized resolved folders; traversal/symlink refusal;
  regular files; byte/line caps; encoding and changed-during-read behaviour;
  safe writes and errors; tests use temporary paths.
- **Secrets/redaction:** no secret values in specs, logs or samples; redact
  before persistence/capping; test labelled, multiline, escaped and boundary
  values through inbox, worker, output and Vault copies; preserve harmless text.
- **Subprocess/agent:** fixed argv, no shell interpolation; account for
  target-configured programs; settings allowlist; tool/profile preflight;
  turn/time/cost limits; kill/reap descendants; receipt, failure and unknown usage.
- **Network API:** official endpoint and terms; auth scope and Secrets lookup;
  bounded requests/responses, timeouts and rate limits; retry/idempotency for
  side effects; no paid retry by surprise; fake-service checks before live use.
- **UI table/long text:** production CSS at 80×24 and wider; real upstream data;
  long/Unicode/multiline values; selected row/scroll; actual keyboard editing;
  Save/reopen/Cancel, source changes and hidden values; shared editor/patterns.

### Go-live checklist

- [ ] Owner approved the exact revision, destination, spending and activation.
- [ ] Update the separate live checkout; record commit and data root.
- [ ] Install/check named wrappers and dependencies; use absolute interpreter paths.
- [ ] Owner completes sign-in; secret names resolve without exposing values.
- [ ] Check allowed folders, profile/tool permissions, limits and destination alias.
- [ ] Dry-run safely; check empty/no-change behaviour and failure reporting.
- [ ] Enable only the agreed job/command; check frequency, caps and duplicate control.
- [ ] Send one agreed test; record run/receipt and owner real-device confirmation.
- [ ] Write disable/rollback instructions and the observation window in one place.

Batch these owner actions into one list for this request. Record skipped items
with a reason. Repeat step 9 after material live changes.

## Measure each loop

Keep `docs/delivery_tests/<request-id>.json` as the durable case; link larger
artifacts. During delivery it can be a draft. Record:

- **Request kind:** `composition-only` uses available nodes; `new-integration`
  needs a new node/capability. Record classification date/base; keep the original
  kind even if later node growth makes replay composition-only. For maintenance,
  retain the owner's change label (for example `swiss-army fix`) and node kind.
  A UI/contract fix with no new workflow has zero operations and coverage not
  applicable; keep related workflow replay coverage separately.
- **Node kind:** `swiss-army` = reusable primitive (HTTP Request, Read lines);
  `use-case` = one tailored job (Notify me); `meta` = helps plan/check workflows
  (Context Pack, Check reply). These are measurement labels, not registry taxonomy.
- **Review rounds:** one review pass on a named head, including a clean re-check,
  counts as one. Save head, findings, outcome; do not estimate history as fact.
- **Days per step:** for steps 0–11, save start/end timestamps and elapsed days
  (seconds / 86400), including waiting. Record wait reason separately; skipped
  steps have a reason, unknown history has null times/days. Reopened steps keep
  each visit; sum visits, avoid counting parallel wall time twice in total days.
- **Node coverage:** split the intended workflow into useful operations, excluding
  Start/End and transport/setup. Map each operation once to existing nodes or a
  new gap. Save denominator, existing count, new count, and mapping at step 2;
  coverage = existing / total. Zero operations → not applicable. Do not inflate
  coverage by adding trivial nodes; retain the original denominator on replay.

Track deploy/setup gaps separately: node coverage does not measure readiness.
Log actual cost when available; `not_reported` is not zero. The first measured
new loop is intended to be Google Calendar samples; this doc does not start it.

## Finished requests become tests

The [delivery test set](delivery_tests/README.md) seeds three real requests:
heartbeat, Notify me and the investigation test. Each stores the request,
dated feasibility verdict, final spec link or node plan, operation mapping,
coverage, evidence, expected checks and notes. Historical measurements are
explicitly unknown; these examples are not freshly executed live tests.

At step 11, freeze the approved outcome and acceptance checks, scrub private
facts, and append observations. Keep a stable case id; version changes rather
than silently rewriting an old verdict. Include blocked requests too when useful:
a correct refusal is a result. Never store credentials or raw private evidence.

For a proposed meta-workflow change, run the same frozen cases against the
same catalogue/base in a temporary data root, without live sends or paid calls.
Save candidate head, prompt/context versions and per-case results beside the
case (a dated results file). Check request/verdict fidelity, correct node/port
mapping, `build --check` for draft specs, preserved approval gates and acceptance
checks. Node plans are planning fixtures until a checkable spec is produced.
Score each dimension pass/fail per case; report passed / applicable checks,
coverage change, review rounds and elapsed time separately. A failed permission,
secret or owner-approval check blocks promotion regardless of aggregate score.
Require no regression in frozen acceptance checks; compare new coverage with
the frozen denominator. Owner approves changed expectations. Keep some later
requests held out so prompt tuning cannot merely memorize these three cases.

## Future direction — not approved work

This extends [H6 teach-once-replay and the designer track](AI_COORDINATION_PROPOSAL.md#new-ideas-and-where-they-fit-owner-2026-10-22).
Teach a task once, capture a spec, replay deterministic parts. Model calls
remain where the workflow still needs judgment; replay is not always free.

1. Measure by hand, keep the test set, and improve prompts/checklists first.
2. Add MCP authoring tools around existing `nodes`, `describe`, `build --check`.
   Current MCP tools execute/read runs; they do not author workflows yet.
3. Try one **composition-only** meta-workflow:
   Request → Pick one (kind) → Context Pack (node catalogue + request) →
   draft spec → `build --check` → owner approval → build.
   Route `unsure` to the owner; route gaps/new integrations to research, not
   fabricated nodes. Check reply can validate structured drafts before checking.
4. Choose model, context and prompt per step; record versions, limits and cost.
   Parallelize independent checks; keep research → decisions → approved design
   and dependent build steps sequential. Approval remains tied to the reviewed
   draft, with another decision if the checked result changes.
5. Later: research branches, candidate designs, phone approvals and in-app
   requests, retaining the three owner gates and real-device proof.

The designer track does not move the server plan forward or authorize new
integrations. Measure each slice against the test set before widening scope.
