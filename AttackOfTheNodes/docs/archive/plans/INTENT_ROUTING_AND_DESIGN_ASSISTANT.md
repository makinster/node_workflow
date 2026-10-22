# Intent routing and an interactive workflow designer

> **Archived reference — 2026-10-22 plan reset.** The owner moved this
> conversation write-up into the archive to preserve context. The approved
> remaining order and short idea mapping live in
> [AI Coordination Proposal, section 9](../../AI_COORDINATION_PROPOSAL.md#9-effect-on-the-build-plan-owner-order-2026-10-22);
> [Current State](../../CURRENT_STATE.md) owns current deployment/review status.
> The original recommendations, worktree paths and handoff prompt below are a
> dated record, not a competing plan or new implementation instructions. Later
> discussion also clarified that MCP is one interface option: local commands
> and services may be simpler for direct integrations. First investigate Hermes's
> built-in no-agent command support before choosing a message-interception plugin.
> C3a's first downstream result is the plain-text choice id; richer metadata can
> remain optional. The approved plan does not require a new server for these slices.

Conversation record and planning handoff, **2026-10-22**.

**Status:** the owner requested this write-up and cross-agent context sharing.
It records product direction, research, implementation observations and proposed
sequencing. It does not approve every design choice below or authorize installing
services, changing the live gateway, buying inference, or implementing the whole
roadmap. The owner specifically sees Telegram interception and an initial Jev
integration as work that could happen soon. Planning should keep those small
deliveries connected to the larger purpose.

This is a temporary planning reference, not an additional core specification.
Once decisions have been extracted into their owning plans, retain this whole
conversation record in the documentation archive and update its incoming links.

**Shared chat:** [immutable conversation snapshot](https://chatgpt.com/s/cx_6ad9b9b6fc088191bc8155152f505b4e).
The sharing tool returned a public link. It was created during this documentation
task and cannot contain later edits to this document or later chat messages.
This document is the durable written handoff; use the chat for the owner's exact
phrasing. The snapshot may require browser access; its availability is not a
dependency for understanding the proposal.

**Code baseline:** inspected fetched `origin/main`, `cce4fc7`, in the separate
worktree `/home/makin/src/nw-review109`. The owner checkout and live cron checkout
were not changed. Research summaries below originated in the October 21–22 chat;
prices, model availability and provider guarantees need checking at implementation.

## 1. The forest: what the owner is trying to achieve

AOTN should let people express what they want, turn that intent into understandable
workflows, and carry out repeatable work with explicit inputs, outputs and effects.
AI supplies judgment and design assistance where useful. The graph makes the
result inspectable, reusable and editable.

The owner does not want to spend a large-agent turn merely preparing to do a
routine task. They also do not want users to memorize workflow names or become
experts in the application's vocabulary. Cheap decisions, plain-language choices,
reusable patterns and progressive assistance can lower both costs.

One owner statement supplies an engineering acceptance criterion:

> A goal I have for this project is to make adding new nodes easy and for ui
> "to just work" based on the nodes added.

Another explains the longer product direction: a user describes a workflow's use
case, specialist AI paths research and expand the idea, a builder produces one
or more configured variations, and the chosen design appears progressively in
the editor with explanations and opportunities for feedback.

These ideas form two connected goals:

1. **Near term — inexpensive decisions and workflow invocation.** Telegram
   messages can start saved workflows; natural-language intent can produce a
   short numbered menu; Jev or local models can choose workflow paths.
2. **Near-to-mid term — interactive workflow design.** An app-managed system
   workflow helps a person design, compare and refine workflows in the editor.

The first goal produces useful features on its own. It also develops contracts,
interaction patterns and authoring capabilities the second goal can reuse.

## 2. How the conversation developed

### 2.1 Telegram as an incoming workflow interface

The owner's first idea was to intercept messages to their existing Hermes
Telegram bot when they begin with an AOTN keyword. Those messages could run saved
workflows, provide Hermes with extra context and tools, or delegate work to coding
agents. Messages outside that route would continue to Hermes normally.

The assistant checked the installed Hermes source and found the plugin hook
`pre_gateway_dispatch`, which supports consuming or rewriting incoming messages.
That provides a concrete integration seam: keep Hermes's existing Telegram
receiver and insert a small routing plugin rather than creating another poller
for the same bot.

Illustrative syntax discussed in the chat:

```text
aotn list
aotn run daily-summary
aotn status <run-id>
aotn context project-x Why did the build fail?
aotn claude review project-x
aotn codex fix issue-42
```

These are examples, not implemented commands or an agreed final grammar. The
first three are a sensible small starting point. Context enrichment and coding
delegation require additional capabilities and should not be advertised as live.

The assistant distinguished two useful paths:

- **Explicit invocation:** the user selects a workflow through the message
  prefix. An exact request needs no model call to decide which workflow to run.
- **Agent tool use:** during ordinary conversation, Hermes can discover and run
  saved workflows through the existing local MCP tools.

Important code observation: the installed interception hook runs **before**
Hermes's normal authorization/pairing checks. It also falls through to normal
dispatch when a plugin raises an exception. A plugin that executes work therefore
needs explicit sender admission and deliberate failure handling; merely finding
the hook does not make interception safe or complete.

### 2.2 Natural language instead of remembered names

The owner then suggested a fast decision step: infer likely intent, present a
few numbered choices, and let the user reply with a number. The user could also
clarify in natural language rather than follow a rigid command grammar.

Example interaction:

```text
User: Can you check what happened with the project?
Assistant:
  1. Recent changes and current status
  2. Failed tests or builds
  3. Open issues and next steps
User: 2
Assistant: Checking failed tests and builds…
```

The assistant proposed matching against the actual available/exposed workflow
catalog, asking for missing inputs after selection, and keeping pending choices
scoped to a user and conversation with an expiry. A natural-language clarification
such as “the build from yesterday” should be accepted as well as `2`.

Showing a candidate is distinct from granting permission for all its effects.
Selecting a workflow must respect its existing execution policy and any relevant
confirmation requirements. A recommendation score cannot supply authorization.

### 2.3 Jev and cheap branch decisions

The owner described Jev at a high level as fast and easy for software to consume
because of its fixed output style. The assistant initially had not identified
the name, then researched and identified TypeSafe AI's Jev decision API.

The owner emphasized the economics:

> Right, don't want to waste money just getting the big boy ai/tools ready to run.

And the central workflow application:

> I could see something like jev being really helpful for almost deterministic ai
> using workflows. Branch selection is big.

The assistant's response was to use small bounded judgments within an explicit
workflow: choose the likely intent, classify an error, select relevant context,
or decide whether a larger agent is needed. Exact tests such as exit codes,
numeric thresholds and known keywords remain ordinary deterministic conditions.

The useful distinction is **deterministic execution after a probabilistic
choice**. A fixed schema ensures an answer has the permitted shape; it does not
establish that the selected action is correct. The workflow should retain the
decision and support an uncertain/unmatched outcome.

### 2.4 Local alternatives and the owner's machine

The owner asked whether open-source/local alternatives were worthwhile and
provided this hardware baseline:

- Intel Core i9-14900K.
- 32 GB system RAM.
- Intel Arc B580; the card's published specification is 12 GB dedicated VRAM.
- Current AOTN development is in WSL; that does not establish GPU availability
  inside WSL.

Research covered hosted small models, GLiClass, SetFit, embedding-based semantic
routing, Qwen around 4B, and Liquid's LFM2.5-1.2B. The assistant concluded that
the machine is sufficient to explore useful local routing without an upgrade.
Small classifiers are CPU candidates; compressed 3–4B and 7–9B language models
are plausible GPU candidates with bounded context. Those are feasibility
estimates, not measurements on the owner's computer.

The assistant recommended comparing a hosted Jev baseline, a small classifier,
and one local language model using the same real messages. Local execution's
advantages include privacy, offline operation and control. At personal routing
volumes, hosted inference is already cheap enough that electricity, setup and
maintenance should enter the comparison.

### 2.5 Nodes should exercise the shared authoring/UI system

The owner asked for the scope of adding the discussed nodes and reiterated that
their UI should follow automatically from node definitions.

The assistant inspected the actual node helper, factory, schema-driven forms,
port hooks and backend/frontend boundary. Most ordinary controls already exist:
typed inputs, source selection, secrets, parameters, repeatable rows, conditional
visibility and downstream/Vault routing.

Two reusable gaps stood out:

1. The helper cannot yet declaratively generate “one output port per configured
   row.” Existing dynamic-port hooks can implement it, but require handwritten
   code and careful preservation during regeneration.
2. Optional local-model execution needs a lifecycle and dependency boundary so
   registration does not import heavyweight ML libraries or load weights at
   application startup.

The assistant proposed composing a decision/classification node with a generic
route-by-choice node. This lets several models share routing, inspection and
feedback behavior. The proposed organization should follow Node Standards:
different port shapes justify separate types; substantially different config
with the same ports can use a selector group; compatible model substitutions
can be ordinary settings. The final grouping has not been selected.

### 2.6 App-managed system workflows for live design

The owner expanded the idea to AI-assisted workflow authoring in real time.
They have been making tools for coding agents to produce preconfigured workflow
save files and want to make that process increasingly automated.

The owner's envisioned experience includes:

- A user types the intended use case.
- A system workflow sends research/expansion tasks to appropriate medium-sized
  models, potentially on parallel paths.
- A stronger builder uses the workflow-creation tools to produce one or several
  configured variations, with alternatives kept on standby.
- Nodes appear individually or as whole branches when applying common patterns.
- An editor follow mode tracks additions, analogous to F in the execution UI.
- Half-screen, slide-in or other unobtrusive output surfaces explain placements.
- Combined explanation/input surfaces offer a message, action button and input
  field; ordinary input nodes are another possible interaction.
- Cheap judgments can review proposals or suggest corrections before display.

The owner clarified the terminology:

> by system workflow, I mean a non user executed workflow that could have
> specialized nodes for interacting with the app in specific ways.

Here, **system workflow** means app-managed execution triggered by an interaction,
with explicitly supplied host capabilities. It is separate from the existing
**System node** group for fixed machine operations such as Git status or disk
space. It is also separate from the user workflow being designed. App-managed
does not mean the assistant has blanket authority or must be invisible.

The assistant's architectural response was to put a validated editing interface
between the designer and the live editor. Research branches contribute evidence
and proposals; one builder owns assembling each candidate. Generic interaction
nodes request content and input, while the frontend chooses presentation.

## 3. What is already real, and what remains proposed

At the inspected main revision:

| Capability | Observed status and practical consequence |
|---|---|
| Workflow discovery and authoring | `aotn nodes`, `describe`, `build --check`, `build`, and `inspect` exist. They are the starting tool surface for generation. |
| Workflow contracts and calls | Typed Start/End contracts and child subworkflow execution exist. Reuse them when composing designer steps. |
| Local MCP | Four tools: `list_workflows`, `run_workflow`, `get_run_status`, `get_recent_events`. This is execution/history access, not an authoring or live-editing API. |
| MCP status/events | Status reads persisted history; recent events are newest run summaries. Neither is a live event stream or an asynchronous job-management service. |
| Unattended runs | MCP rejects workflows that may ask for input through C25 and uses unattended policy. A Telegram or editor conversation needs a separate interaction bridge. |
| Hermes outgoing notifications | H0 wrappers and the C1 outbox/drain exist. Shared notes report the owner confirmed the C1 Telegram message arrived. This task did not repeat a live test. |
| Incoming Telegram workflow router | Not implemented by this conversation. A supported hook was identified in the installed Hermes source. |
| Jev and local decision nodes | Not implemented by this conversation. |
| Chat Completion | Real Anthropic transport exists. Other providers/local endpoints need adapters; dropdown entries alone do not add execution support. |
| Embedding node | Currently simulated output. Real embeddings are prerequisite to meaningful embedding-based intent routing. |
| Schema-driven config | Ordinary fields, object-list rows, secrets and dynamic visibility already render generically. |
| Config-driven ports | Backend/factory hooks exist. Declarative helper generation and generic route-edit lifecycle need work. |
| Editor follow | Execution has follow behavior; equivalent editor behavior is proposed, not already available. |
| Authoring assistant | No general live-draft edit transaction API or app-managed designer was added. Existing editor plan/apply operations provide a useful precedent. |

Earlier work in this chat reviewed #109's outgoing-message system. Eight
findings—torn lines, premature repeat suppression, mixed directive suppression,
Unicode JSONL framing, digest size, folder mismatch, clock rollback and existing
permissions—were rechecked as fixed at `371679d`, with 46 relevant tests and
additional concurrency/crash probes. The feature subsequently merged into the
inspected main. This is historical validation, not a new full-suite result.
The incoming router should reuse these lessons about durable admission, replay,
escaping and honest receipt stages.

Shared notes also report concurrent C2 Saved values work as PR #110, branch
`dist/persistent-store`, in `/home/makin/src/nw-store`. This document did not
review that branch. Check its current status before proposing new persistence
primitives or changing shared status/log files; do not duplicate its work or
make the first Telegram/decision delivery depend on an unmerged implementation.

## 4. A near-term Telegram delivery that stands on its own

### 4.1 Thin first slice

Start with explicit prefixed invocation of a small set of exposed saved
workflows. Add discovery and final results using existing contracts. A first
version could be limited to the owner's admitted private conversation and one
in-flight request, with a clear busy response. That avoids prematurely building
a general multi-user scheduler.

Proposed behavior:

1. Match the prefix at a defined boundary; `aotnish` must not accidentally match.
2. Admit the sender before execution, respecting the gateway's actual identity
   and pairing rules. The existing pre-dispatch hook precedes normal admission.
3. Resolve only explicitly exposed workflow names/IDs and check typed inputs.
4. Record acceptance and deduplicate by Telegram platform/conversation/message
   identity before scheduling effects.
5. Hand off to a bounded worker, keep the gateway responsive, and consume the
   intercepted message so it is not also processed as an ordinary agent request.
6. Return a useful acknowledgment and final result/failure, with a correlation
   to the request/run. Unprefixed conversation continues through normal Hermes.

The hook's fail-open behavior is a concrete design issue: expected errors in
the reserved prefix route need explicit handling. An exception must not silently
turn a failed deterministic request into a general agent prompt that could try
the operation again. Overlong jobs, duplicate updates, gateway restart and
partial acceptance need defined outcomes. Deduplication alone is not proof of
exactly-once execution; record the boundary at which a retry may be safe.

Workflow execution can use the existing CLI/run service or MCP surface. Choose
the smallest suitable adapter; a persistent MCP process is not a requirement for
every one-off invocation. Existing MCP call deadlines and persisted-only history
must not be misrepresented as a background queue or live status service.

Trusted inbound reply metadata belongs to the bridge. A workflow should not get
arbitrary Telegram chat IDs in its destination config. Existing outgoing Notify
me nodes use named destinations. Decide explicitly whether first-version results
use the existing notification path or a bridge-owned immediate reply; the cron
drain's five-minute cadence is not an interactive acknowledgment mechanism.

### 4.2 Natural-language route as a follow-on

After exact invocation works, add prefixed natural-language requests. Give the
decision model the exposed catalog's plain-language descriptions and relevant
input contracts. Present the best few matches using stable workflow IDs behind
the menu, rather than assuming a visible name is an unambiguous identifier.

Persist a pending menu with user/chat identity, expiry and catalog/revision
context. A numeric reply needs an unambiguous association with that menu, even
when it lacks the original prefix. Expired menus, ordinary numeric conversation,
multiple pending requests, cancellation and changed/deleted workflows all need
predictable handling. Ask for required inputs after selection and revalidate
before execution.

Context enrichment is another follow-on: a workflow gathers context, and Hermes
receives the result with the original question. Keep provenance and separate
retrieved content from instructions. Agent delegation comes after its bounded
execution contract is available.

### 4.3 Checks that demonstrate the first slice

Use real plugin/worker subprocess paths with isolated data: authorized versus
unauthorized sender; exact prefix boundaries; ordinary chat pass-through; typed
input failure; duplicate messages; busy/timeout behavior; restart recovery; and
honest success/failure responses. Do not test against the owner's live workflows
or enable a gateway plugin as a side effect of unit tests.

## 5. A near-term Jev delivery without a large framework prerequisite

The owner considers getting Jev working fairly easy. A thin client plus one
ordinary node is a reasonable bounded first delivery. Separate that from the
larger reusable routing/helper work and from proving the model's suitability.

**Initial node:** input state, one specific question, a configured list of
choice IDs/descriptions, model, API-secret reference and request timeout. Output
a validated decision object containing the selected choice, alternatives and
provider-reported probability/confidence information when available, with model
identity and usage metadata. Existing forms should render these fields.

Validation must reject undeclared choices and malformed values. Authentication,
transport, deadline and provider errors need explicit outcomes. Small automated
tests should use a local test endpoint; paid smoke calls are deliberate separate
verification. No secrets belong in workflow saves or request/error logs.

An early demonstration can extract the selected value and use the existing
Conditional node. It does not have to wait for a complete configurable router,
profile manager, local inference stack or design assistant. Such a demo proves
the integration, while a representative evaluation establishes usefulness.

**Next reusable piece:** Route by choice. A decision is data; the router chooses
one output and forwards the intended payload. Stable route identities preserve
connections across label edits and row reorder. Duplicate/unknown choices and an
uncertain outcome need explicit handling. This selects a path; it is not a
parallel branch-spawning operation.

**Later Jev primitives:** yes/no judgments and rubric scores can share the client
and transport. Their result semantics differ; a rubric score, binary probability,
choice distribution and summary confidence must not become one interchangeable
number called “confidence.”

### 5.1 Costs and interpretation recorded in the chat

The published Jev rate consulted was **USD 0.042 per million input tokens**, with
output free. At one 1,000-input-token request per suggestion, 1,000 suggestions
cost approximately **USD 0.042**. At 500 tokens each it is USD 0.021; at 5,000
tokens each it is USD 0.21. Inputs include instructions, catalog descriptions,
question definitions and relevant context, not only the user's message.

For the comparison researched in chat, Gemini 2.5 Flash-Lite was USD 0.10 input /
0.40 output per million tokens, and Gemini 3.1 Flash-Lite was USD 0.25 / 1.50.
At 1,000 input plus 50 output tokens per request, 1,000 requests would be about
USD 0.12 and USD 0.325 respectively, excluding extra reasoning, retries and
other services. These are dated examples; check the actual available model and
billing terms before choosing a provider. Running the selected workflow or a
coding agent is a separate cost.

TypeSafe's confidence statistic summarizes the returned distribution. A value
of 0.9 is not automatically a 90% measured correctness rate on our workload.
Structured output guarantees format, not truth or authorization.

## 6. Local competitors and node scope

| Candidate | Role worth evaluating | Addition scope |
|---|---|---|
| Jev | Fixed-choice decisions, rubric scoring, binary judgments | Thin hosted transport first; decision node; additional primitives reuse the client. |
| GLiClass-small | Rank a message against supplied intent labels without task-specific training | Optional inference worker/server, cached model, label-score validation and classification node. |
| SetFit | Recognize recurring intents learned from the owner's selections | Prepared-model inference first. Training/evaluation/model versioning are separate work. |
| Qwen around 4B | Routing plus extraction, context preparation and short summaries | Local inference endpoint with constrained output, bounded requests and strict parsing. |
| Liquid LFM2.5-1.2B | Lightweight CPU-oriented language-model alternative | Reuse a compatible local server where supported; verify capabilities and custom license. |
| Embedding-based semantic routing | Shortlist workflows from examples/descriptions | Real embedding client, prepared candidate representations and thresholds; current simulated embedding output cannot supply this. |
| Hosted small language model | Routing plus argument extraction or clarification text | Provider adapter; compatible adapters can share the decision contract, without pretending all APIs behave identically. |

GLiClass-small is approximately 100M parameters. SetFit uses a small encoder and
classifier trained from labeled examples. Qwen's inspected 4B models use
Apache-2.0 licensing; Liquid's inspected model has a custom license. “Available
weights,” permissive source code and unrestricted commercial use are different
claims; keep those distinctions when packaging optional integrations.

For the B580, llama.cpp's SYCL documentation explicitly lists the device as
verified, and Ollama documents Vulkan support on Windows/Linux. Initially a
Windows-hosted inference server accessed from WSL is a plausible arrangement.
Verify the selected device/backend rather than assuming GPU acceleration from
the fact that inference starts. No models were installed or benchmarked here.

Approximate four-bit weight-memory estimates from the discussion:

| Model size | Weight memory estimate | Practical interpretation |
|---|---|---|
| 1–2B | 0.8–1.5 GB | Lightweight starting point, including CPU experiments. |
| 3–4B | 2–3 GB | Sensible first general language-model comparison. |
| 7–9B | 4.5–6.5 GB | Plausible GPU workload with bounded context. |
| 12–14B | 7.5–10 GB | Tighter VRAM budget; context/runtime overhead matters. |
| Around 30B | 17–21 GB | Cannot fully reside in 12 GB VRAM at these estimates; CPU/offload compromises. |

These are estimates, not total memory requirements or speed promises. KV cache,
buffers, quantization format, operating system and other applications change
the result. Useful broader experiments include summaries, structured extraction,
document questions and small coding tasks. None establishes frontier-agent
reliability merely because the weights fit.

Compare candidates on a modest held-out set of actual messages: top-choice
accuracy, intended-workflow presence in the first three suggestions, uncertain
cases, confidently wrong routes, latency with models warm/cold, and total cost.
Include out-of-scope and multi-intent messages. A tuned threshold should be
evaluated on different examples from those used to tune it.

## 7. Make node addition easier as these features arrive

The [Node Helper](../../NODE_HELPER.md) already creates class scaffolding, registration
and focused/generated UI tests from a spec. Schema-driven forms support typed
sources, secrets, conditional rules and repeatable object rows. These additions
should prove that contract rather than accumulate one frontend exception per
model/provider.

Recommended shared improvements, introduced when a real consumer needs them:

1. **Ports from configured rows.** Add a declarative helper contract for stable
   route IDs, labels and descriptions. Use existing backend port-resolution
   hooks and generic frontend consumers. Define connected-row deletion and
   validation behavior as part of the feature.
2. **Decision results with explicit semantics.** Carry the selected key,
   alternatives, score kind, uncertainty, model/provider and usage. Existing
   `var`, `string`, `number` and `bool` types suffice initially. An invented
   per-model global type is not required.
3. **Optional inference lifecycle.** Keep app registration lightweight. Put
   heavyweight imports, model loading and training outside normal node imports;
   use an isolated worker or separately managed endpoint with bounded work and
   explicit failure/cancellation behavior.
4. **Behavioral UI checks.** Exercise keyboard navigation, live row/mode changes,
   Save/Cancel, reopen and connection preservation, not just widget existence.
5. **Honest generator ownership.** Regeneration currently overwrites custom
   execute/port hooks. Preserve reviewed custom code and tests; a future safe
   generation model needs a separate design rather than a claim of lossless
   regeneration.

Model profiles and installation UI may eventually simplify setup. They are not
prerequisites for a thin hosted client or an explicitly configured local endpoint.
Keep training, downloading, starting a model server and performing inference
separate operations unless the owner chooses otherwise.

## 8. The app-managed workflow designer

### 8.1 Proposed process and model roles

```text
User brief + current design context
                 |
           Clarify / plan
                 |
       Research and expand in parallel
        /              |              \
   Node/pattern     Approach        Constraints /
     discovery     comparison      missing inputs
        \              |              /
             Candidate builder
                 |
       Deterministic build/validation
                 |
       Semantic review / bounded repair
                 |
       Stage edits + explain in editor
                 |
      User feedback / select variation
                 |
              Revise or keep
```

The strong builder receives evidence and available contracts, not independent
research agents all writing into the same live document. Medium models can
perform bounded exploration; cheap decisions choose known patterns or identify
uncertainty. Model allocation is an experiment, not a fixed hierarchy requiring
every request to traverse several paid agents.

The first builder can use tool schemas, examples and validator feedback. The
owner imagined a model trained for the creator tools; specialized training may
eventually help, but it need not block an initial authoring assistant. Collect
accepted designs, corrections and failures if future training is desired.

### 8.2 Specialized system capabilities

| Capability | Request/result contract |
|---|---|
| Read design context | Snapshot of the target draft, selection, revision and validation findings. |
| Discover nodes and patterns | Real node contracts and available callable workflows/templates. |
| Build candidate | Proposed authoring spec → checked candidate plus diagnostics. |
| Propose edits | Revision-scoped configured nodes/connections/branch changes → accepted batch or conflict. |
| Explain placement | Short user-facing explanation associated with actual affected node IDs. |
| Ask designer | Question, choices and optional fields → correlated answer or cancellation. |
| Manage variations | Create, compare, select and discard separate candidate drafts. |
| Validate candidate | Machine-readable structural/configuration checks, plus clearly separate semantic review. |

These are proposed capabilities, not final node names. Whether each needs a node
or some are tools used by an agent node is an open design question. Nodes should
remain small and graph-ignorant; host capabilities supply prepared context and
explicit service requests. A node must not import editor screens or reach into
widgets.

### 8.3 Live editing and variations

The current authoring tool creates complete configured saves. Progressive edits
need an additional service that accepts validated operations against a target
draft with an expected revision. It should support a single configured node or
an atomic branch/pattern batch, preserving graph invariants and creating an
understandable undo unit.

The designer's run context, target draft and displayed candidate must have
separate identities. Current session singletons/shared live graph services are
not evidence that a second assistant run can safely reuse the editor's stack.
Choose isolated execution and a host bridge appropriate to the first version;
a full distributed server is not automatically required.

Concurrent user edits should make stale proposals detectable. Refresh or
reconcile the affected proposal; do not silently overwrite newer edits. Incomplete
streamed construction needs draft-aware checks: an unconnected node is expected
during assembly, while a completed candidate needs full validation.

Keep alternative designs as separate candidate drafts/snapshots with parent
revision and validation status. “Standby” should not mean adding disconnected
experimental branches to the active workflow. Draft storage, retention and
promotion into the saved library still need a design.

### 8.4 Interaction and follow mode

The owner suggested half-screen/slide-in/nonintrusive output and combined text,
button and input nodes. The common requirement is an assistant interaction
surface that can display a short explanation, point at nodes, and collect a
response without obscuring the graph or forcing a modal for every placement.

The frontend owns geometry, focus and rendering. The system workflow requests
semantic interactions; another frontend could render the same request differently.
Keep request IDs, run/draft identity, expiry/cancellation and answers JSON
serializable. Backend events must not contain widgets or mutable UI references.

Follow mode should adopt the execution UI's familiar behavior: follow recent
placements/highlights while enabled, allow manual inspection to stop following,
and let F resume. Follow is presentation state and must not determine which
edits are committed. The exact focus rules and layouts need owner-reviewed
sample screens at relevant terminal widths before UI implementation.

### 8.5 Validation and quick fixes

Use deterministic checks first for known node types, config fields, types,
ports, references and graph rules. Use model judgments for semantic questions:
does the candidate address the brief, is information missing, or which variant
best fits simplicity/cost requirements?

The owner suggested cheap review and quick fixes before display. A repair should
be a bounded proposal followed by revalidation. An AI score cannot replace
structural checks or justify an unlimited self-repair loop. A structurally valid
workflow is not proof that external operations will succeed; test execution
requires its own inputs and explicit effects policy.

## 9. Proposed sequence and acceptance gates

This is a recommendation for planning discussion, not an approved implementation
queue. The existing owning plan still controls project work order.

| Slice | Demonstrable result | What it should avoid waiting for |
|---|---|---|
| A. Telegram exact invocation | An admitted prefixed request starts an exposed saved workflow once per admitted request policy and reports the real outcome; ordinary chat still works. | Jev, local models, system workflows, general server/triggers. |
| B. Thin Jev integration | A real optional provider client and schema-generated choice node produce validated decisions with explicit failure handling. | A complete provider framework, dynamic router, fine-tuning. |
| C. Shared route-by-choice/helper | Configured stable rows create correct ports, select one path and preserve wiring through edits; uncertain case covered. | Additional model providers or assistant panels. |
| D. Intent suggestions | A real catalog yields a short menu; numbered/clarified replies remain scoped and validated before running. | Live workflow authoring. |
| E. Local comparison | One optional classifier and one local language model tested on the same messages as Jev; device, accuracy and latency measured. | Training UI, automatic model installation, supporting every backend. |
| F. Authoring assistant | Brief → candidate specs → deterministic checks → selected configured draft, using real node contracts. | Progressive editor mutation, a custom-trained model, all system nodes. |
| G. Live design editing | Revision-aware batches, undo, explanations and follow behavior work together in an isolated draft. | Every possible agent/research configuration. |
| H. System-workflow composition | Reusable app interaction capabilities support research branches, feedback and standby variations. | A claim of general autonomous application control. |

Slices A and B are the owner's clear near-term opportunities and can be scoped
independently. Agent CLI nodes form another substantial track: lifecycle,
cancellation, working directory, tool permissions, limits, answer extraction and
trace persistence. Their settings can mostly use generated forms, but they are
not merely a subprocess call plus a dropdown.

## 10. Decision rules that preserve the larger goal

For each proposed feature or abstraction, ask:

1. What concrete user task becomes easier in this delivery?
2. Which existing contract does it reuse, and what specific missing capability
   requires a change?
3. Can a simpler slice prove usefulness before introducing a framework?
4. Does a new model/node fit the shared metadata/UI path, or expose a reusable
   gap that should be fixed once?
5. Is the behavior exact logic, a model judgment, or a human decision? Are those
   roles visible in the graph and records?
6. How does the person inspect, correct, cancel or undo the result?
7. Can the feature work without Hermes or without this one model provider where
   that independence belongs in the existing architecture?
8. What evidence would show the feature is useful, and what would make us stop
   expanding it?

Avoid spending weeks generalizing before the first useful Telegram command or
provider call. Equally, avoid a fast prototype whose special-case UI and opaque
effects make subsequent nodes harder to add. A small delivery should leave a
reusable seam proportional to its demonstrated needs.

## 11. Open decisions for the next planning discussion

- Prefix spelling, parsing, escaping and the first exposed workflow set.
- Admission rules for private chats/groups, pending numeric replies and reserved
  route errors in a fail-open gateway hook.
- First execution adapter, concurrency/busy policy, acceptance durability and
  acknowledgment/final-result delivery path.
- Initial Jev primitive and result schema; treatment of uncertainty and selection
  confirmation; API-secret setup and paid smoke verification.
- How choices are declared once and shared between a decision node, a router and
  a user menu, including changes to saved catalogs and connected ports.
- Local model candidate/runtime and whether Windows-hosted serving is the first
  arrangement; optional dependency packaging.
- Scope of authoring tools exposed through MCP or another adapter, with new
  draft creation separate from effects on an open document.
- Minimum system-host capabilities, execution isolation, cancellation and stale
  proposal handling.
- Candidate persistence and comparison, batch undo, incomplete-draft validation,
  panel geometry, focus and follow behavior.
- Which research paths/patterns are useful enough to implement first, and which
  evidence would justify specialized training later.

## 12. Reading map and source references

### Project authority and implementation

- [Vision](../../VISION.md): inspectable workflows, dependable contracts and community
  extensions; this proposal should advance those goals.
- [Current State](../../CURRENT_STATE.md), [Node Contract Plan](../../NODE_CONTRACT_PLAN.md),
  [Project Backlog](../../PROJECT_BACKLOG.md): delivery status and owning work order.
- [AI coordination proposal](../../AI_COORDINATION_PROPOSAL.md): Hermes as an optional
  seam, bounded agents, receipts, event sources and owner decisions.
- [Workflow authoring](../../WORKFLOW_AUTHORING.md) and
  [authoring implementation](../../../backend/authoring.py): current create/check tools.
- [MCP contract](../../integrations/MCP.md) and [tool definitions](../../../aotn_mcp/tools.py):
  execution/history scope and current unattended restrictions.
- [Node Standards](../../NODE_STANDARDS.md), [Node Helper](../../NODE_HELPER.md),
  [generator](../../../../aotn_node_helper/generator.py),
  [form generator](../../../frontend/widgets/form_generator.py): metadata/UI contract.
- [Boundary](../../BACKEND_FRONTEND_BOUNDARY.md),
  [NodeContext](../../../backend/node_base.py), [factory](../../../backend/node_factory.py),
  [editor adapter](../../../frontend/editor_workflow_adapter.py),
  [execution screen](../../../frontend/screens/execution.py): placement of shared
  behavior, live edits and follow precedent.
- [Outgoing Hermes shared folder](../../integrations/HERMES_SHARED_FOLDER.md): named
  destinations, receipts, escaping and drain behavior already implemented.

Local cross-agent context is outside Git at
`/home/makin/src/agent_channel/NOTES.md` and
`/home/makin/src/agent_channel/ORCHESTRATOR_FIELD_GUIDE.md`. The installed Hermes
source checked during the chat is `/home/makin/.hermes/hermes-agent/`, especially
`gateway/run.py` and `website/docs/user-guide/features/hooks.md`. Recheck the
installed version before implementation. Shared notes can be newer than main's
status prose; neither is a substitute for code or a fresh live check.

### External research cited during the chat

- [Hermes hooks](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/hooks.md#pre_gateway_dispatch).
- [TypeSafe introduction](https://docs.typesafe.ai/introduction),
  [Choice](https://docs.typesafe.ai/primitives/choice),
  [confidence](https://docs.typesafe.ai/confidence), and
  [published pricing](https://typesafe.ai/).
- [Independent Jev evaluation preprint](https://arxiv.org/abs/2609.37647):
  evaluates 37 datasets, reports strong choice performance and task-dependent
  limitations. It is not evidence for our specific workflow catalog.
- [Decision reranking preprint](https://arxiv.org/abs/2609.40241): favorable
  latency/quality tradeoffs in some settings; specialization alone does not
  guarantee superior task quality or robustness.
- [GLiClass](https://github.com/Knowledgator/GLiClass),
  [small model](https://huggingface.co/knowledgator/gliclass-small-v1.0),
  [SetFit](https://github.com/huggingface/setfit), and
  [Semantic Router](https://github.com/aurelio-labs/semantic-router).
- [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B),
  [non-thinking Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
  [Liquid LFM2.5-1.2B](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct).
- [Intel B-series specifications](https://cdrdv2-public.intel.com/839907/Intel%20Arc%20B-Series%20Graphics%20Quick%20Reference%20Guide%20V1.1.pdf),
  [llama.cpp SYCL backend](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/SYCL.md),
  [constrained-output grammars](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md),
  [Ollama hardware support](https://docs.ollama.com/gpu),
  [Google model pricing](https://ai.google.dev/gemini-api/docs/pricing).

No external price or benchmark in this document is a fresh measurement of the
owner's system. Nothing was installed, scheduled or enabled by writing this file.

## 13. Handoff prompt for Claude

```text
Please read the owner's shared planning chat and the write-up before proposing
the next steps:

Chat: https://chatgpt.com/s/cx_6ad9b9b6fc088191bc8155152f505b4e
Write-up:
/home/makin/src/nw-review109/AttackOfTheNodes/docs/INTENT_ROUTING_AND_DESIGN_ASSISTANT.md
Branch: codex/intent-design-planning, based on origin/main cce4fc7.
This is a local documentation handoff; do not assume it has been committed,
pushed, merged, or copied into the owner checkout. Read it directly at that path.
If the shared chat is inaccessible, the document is self-contained.

The owner wants two connected goals preserved:
1. Near term: Telegram messages beginning with an AOTN prefix can run exposed
   saved workflows. Add a thin Jev integration soon, then natural-language intent
   suggestions, numbered clarification, and reusable choice-based routing.
2. Near-to-mid term: an app-managed system workflow helps users design workflows
   from a plain-language brief. It can research approaches, build configured
   variations, validate proposals, place nodes/branches progressively, explain
   placements, collect feedback, and use an editor follow mode.

The owner's central engineering goal is that adding nodes is easy and the UI
works from node definitions. Preserve the larger user experience while keeping
the first deliveries small. Do not require a comprehensive agent framework,
local model stack, fine-tuning, or live-editing service before a useful Telegram
launcher or Jev choice node can ship.

Read the authoritative checkout's AGENTS.md, shared NOTES.md and
ORCHESTRATOR_FIELD_GUIDE.md, then Vision, the existing AI coordination proposal,
Node Standards/Helper, Workflow Authoring and the backend/frontend boundary.
Verify current main and current worker ownership before implementation. Never
develop in the retired OneDrive copy or edit the owner's/live cron checkouts.
Use your own worktree; run git in WSL; gh requires --repo makinster/node_workflow.
Never edit AttackOfTheNodes/workflows/. No AI model names in commits or PR text.
Owner review controls merging and activation of live integrations.
Shared notes currently report C2 Saved values work as PR #110 in nw-store;
verify its status and avoid duplicating its storage work or shared-doc edits.

Important findings to retain:
- The installed Hermes pre_gateway_dispatch hook can intercept messages, but it
  runs BEFORE normal admission and falls through to normal dispatch on plugin
  exceptions. Prefix routing needs explicit admission, deduplication, bounded
  execution and deliberate handling of reserved-route failures.
- The existing MCP tools run saved workflows/read history. They do not author
  graphs, stream live status or supply an interactive input bridge. Authoring
  CLI/services already exist and should be reused.
- Jev's structured outputs do not guarantee correct decisions; its confidence
  statistic is not automatically our measured accuracy. Deterministic validation
  remains authoritative for graph/config rules.
- The owner has an i9-14900K, 32 GB RAM and an Arc B580 (12 GB VRAM). Local
  routing is plausible, but nothing was installed or benchmarked in this chat.
- Ordinary forms already support choices/object rows, secrets and conditional
  fields. The reusable gaps are declarative config-row-driven ports, safe route
  edit lifecycle and optional inference execution. Heavy imports must not burden
  app startup. The existing Embedding node is simulated.
- A system workflow is an app-managed assistant run, separate from the draft
  it edits and separate from the existing System nodes group. Future host
  capabilities should use explicit services and JSON events, not widget access.

For your first response, propose a concise sequence of independently useful
deliveries, with a concrete smallest Telegram slice and smallest Jev slice,
dependencies, acceptance checks and the few owner decisions that really matter.
Identify disagreements or simplifications rather than treating the assistant's
recommendations as settled decisions. Explain how the near-term seams support
the later design assistant without overbuilding them. This is a planning handoff;
it is not a blanket request to implement or deploy the entire roadmap.
```
