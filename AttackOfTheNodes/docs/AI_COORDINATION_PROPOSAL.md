# AI Coordination Proposal — Hermes Integration, Deterministic Tool Nodes, Bounded Agents

> **Status: owner decisions C1–C7 recorded (2026-10-20); see section 10.**
> Proposal text below is otherwise unchanged; Hermes facts still need
> re-verifying before any job is enabled. Originally: owner discussion only; no
> code. Nothing here changes an approved decision in
> [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md). Section 9 records the
> owner's approved delivery order, including the 2026-10-22 reset.

> **Owner reset, 2026-10-22:** section 9 now records the approved remaining
> delivery order and maps new ideas onto it. Earlier proposal text and dated
> decisions remain context; [Current State](CURRENT_STATE.md) owns live status.
>
> **Updated 2026-10-20** against main `2ecd297`: the AOTN facts (section 4),
> the tool-gap table, the MCP note and the build order now reflect that most
> of Step 4 is merged (contracts, child runs, the Subworkflow node) and that
> the Stash is built. The Hermes facts (section 3) are unchanged.

## 1. Summary

AttackOfTheNodes (AOTN) becomes a PC-wide coordinator: a deterministic
workflow spine that calls AI systems only at decision points, asks a human
at approval gates, and leaves a receipt for every AI step and every message
it sends.

- **Deterministic spine.** Workflows do ordinary operations (files, HTTP,
  commands, state) without spending tokens.
- **AI at decision points.** AI steps are *bounded nodes*: a tool allowlist,
  turn/time limits, and a recorded trace of the tools actually used. Token
  cost is visible in the graph, because only AI-family nodes spend tokens.
- **Humans at gates.** Approval in the TUI or by Telegram before anything
  that writes, deletes or sends.
- **Hermes as transport.** The Hermes agent already owns a Telegram bot, a
  cron scheduler and webhooks. AOTN uses them instead of duplicating them.

This fits the factory/control-room model in `AGENTS.md`: AI systems are
machines on the floor, not the operator.

### 1.1 Hermes is a near-term shortcut, not a dependency (owner, 2026-10-20)

Hermes already has a scheduler, a Telegram bot and webhooks, so using them
gets useful results soon. AOTN keeps the option to do each of these itself:

| Hermes gives now | AOTN's own version later | When |
|---|---|---|
| Cron jobs that run `aotn run` | Start triggers and event sources | Step 5 |
| Telegram delivery (stdout, outbox drain) | A notify node with its own destinations | After C1, if wanted |
| Telegram replies and buttons | `wait_for_reply_node` with an AOTN event source | Step 5 / C6 |
| `hermes chat -q` as an AI step | `chat_completion_node`, `claude_code_node` | C3 |

Rules that keep it a shortcut:

- **Nothing in the engine needs Hermes.** Hermes appears only in wrapper
  scripts, the shared folder and optional nodes. AOTN runs and tests the
  same without Hermes installed.
- **Hermes nodes are optional.** They sit in their own group, report
  clearly when Hermes is missing, and never block validation of workflows
  that do not use them.
- **One seam per job.** Notifications go through the outbox schema, AI steps
  through the bounded-agent contract, and schedules through `aotn run`. Each
  seam can switch from Hermes to an AOTN-native piece without changing
  workflows that use it.
- **Shared formats are AOTN's.** AOTN owns the outbox, events and proposal
  schemas (C2), so they outlive the Hermes integration.

### 1.2 A first community (owner idea, 2026-10-20)

Hermes users are a natural first audience: they already run an agent with
cron and Telegram, and the H1/H2 patterns give them a zero-token heartbeat
or watchdog in a few minutes. Before posting (for example in the Hermes
subreddit; check its rules on self-promotion first), have:

- an install path that works from a clean machine (`pip install` from the
  repository, the shared requirements lock);
- a short Hermes guide: the wrapper script, one cron job, H1 and H2 as
  ready-made workflow specs (`aotn build`);
- a few screenshots or a short recording of the TUI and a Telegram message;
- a plain list of what is not done yet (Step 5 triggers, no server, Linux
  and Windows status), so early users know what to expect.

This is packaging and docs work; it fits after H0 and C1, when there is
something to show.

## 2. Principles

1. **Tokens only where judgment is needed.** "AI as router, not worker": one
   small model call chooses a branch or fills a parameter; the workflow does
   the mechanical steps.
2. **Know what tools ran, without asking the AI.** Enforce with an allowlist,
   record with a trace. Never rely on a model's description of its own
   actions.
3. **Teach once, replay forever.** An AI that solves a task once can write
   it as a workflow spec (`aotn nodes | describe | build | inspect` already
   exist for this). Later runs cost no tokens.
4. **Never write another system's internals.** AOTN and Hermes meet only at
   a shared folder with versioned schemas (section 5), and at documented
   entry points (`aotn run`, `hermes chat -q`, cron jobs).
5. **Standing infrastructure is configured once.** Workflows emit events;
   they do not create or delete cron jobs, bots or services as a side effect
   of a run.
6. **Receipts, not memory.** Events go to an append-only log. Durable AI
   memory is changed only through a reviewed proposal queue.

## 3. Hermes facts this proposal relies on

Reported by Hermes on 2026-10-20 after inspecting its installed code (cited
paths are in the Hermes repo). Re-verify when Hermes is upgraded.

| Fact | Consequence for AOTN | Source (Hermes) |
|---|---|---|
| Cron jobs support `no_agent: true`: a script runs, its stdout becomes the message, no LLM | Zero-token notifications | `cron/scheduler.py` |
| Empty stdout sends nothing | A workflow can stay silent by skipping its output | same |
| `script` is a single file path inside `$HERMES_HOME/scripts` (`/home/makin/.hermes/scripts`); no arguments, no shell parsing; `.sh`/`.bash` run via Bash, else Hermes's Python | One wrapper file per scheduled workflow | `cron/scheduler.py:878–950` |
| Subprocess cwd is the script's directory (not the job's `workdir`) | Wrapper must `cd` to the AOTN project | `:925–950` |
| Environment is a copy of the gateway's, with Hermes's venv first on `PATH` | Wrapper must call AOTN's interpreter by absolute path | `:1246–1259` |
| Non-zero exit → "⚠️ Cron job failed" alert with exit code, stderr and stdout | AOTN exit codes 1/2/3 all alert; 0 sends stdout | `:951–975`, `:1269–1286`, `:1931–1967` |
| Script timeout defaults to 120 s, global only (`HERMES_CRON_SCRIPT_TIMEOUT` / `cron.script_timeout_seconds`); a timeout loses all output | Long workflows cannot deliver via stdout | — |
| Output is delivered after the script exits, so the script never sees the Telegram message ID or delivery outcome | Receipts need stages (section 6) | — |
| Telegram splits at 4,096 UTF-16 units with `(1/3)` markers; no total cap | AOTN must cap output itself | `gateway/platforms/base.py:4112–4241` |
| Stdout is trimmed, wrapped by `cron.wrap_response`, Telegram-formatted | Message framing is a Hermes setting | `cron/scheduler.py:640–665` |
| `[SILENT]` anywhere suppresses delivery; `MEDIA:` lines become attachments; a final JSON line with `"wakeAgent": false` suppresses delivery | Feature *and* injection risk (section 5.3) | `:978–1001`, `tools/send_message_tool.py:592–639` |
| Memory notes are short durable facts injected into prompts; scripts should not edit their backing files | Use a proposal queue instead | — |
| Webhook subscriptions exist; agent-oriented webhooks are not assumed token-free | Only deterministic webhook paths are in scope | — |

## 4. AOTN facts this proposal relies on

- `aotn run <workflow>` (`aotn_cli.py`) runs without Textual. Stdout carries
  only run outputs (one line per output); status and errors go to stderr.
  `--policy terminate_workflow` makes it unattended; `--data-dir` selects a
  data directory.
- Exit codes (`backend/run_service.py`): 0 ok, 1 finished with *unhandled*
  errors, 2 run failed, 3 invalid/could not start, 4 not found, 5 invalid
  contract inputs (missing, invalid or unknown), 64 usage error, 130
  interrupted. Errors routed to an error path do not fail the run (D10), so
  **error routing is alert routing**: handled errors send your message,
  unhandled ones become a Hermes alert.
- **Contracts are built (4a-1, #80):** `--input KEY=VALUE` is typed by the
  workflow's Start rows (number, true/false, JSON for `var`, a path for
  `file`); `--inputs-file` supplies a JSON object; missing required inputs
  fail before the run starts (exit 5). The run's `values` come from the
  Return End. A cron wrapper can therefore pass typed inputs today.
- **Subworkflows are built (4b #87, 4c-1 #91, 4c-2 #94):** the
  `subworkflow_node` calls a saved subworkflow and waits (call-and-wait;
  fire-and-forget is later). Depth 4 and 64 live calls by default. A
  headless caller fails fast when a called subworkflow would prompt (C25),
  so cron runs never hang on a hidden prompt.
- **The Stash is built (S1–S3):** a durable per-machine store of files and
  text (`stash/`), insertable into config fields. **Step 4d (#101):** a
  Subworkflow node's input can come from a Stash entry, saved in the workflow
  by name (a missing entry is a validation error), and `aotn run` accepts
  `--input key=@stash:"name"`, so a cron wrapper can pass a per-machine file
  or text without a path in the workflow. There are no per-machine binding
  files (owner, 2026-10-20).
- Existing deterministic nodes relevant here: `file_reader_node`,
  `file_view_node`, `file_output_node`, `http_request_node`,
  `window_control_node`, `json_path_node`, `text_transform_node`,
  `conditional_node`, `user_text_input_node`, `wait_until_node`,
  `subworkflow_node`, `chat_completion_node`. There is no command-execution
  node.
- Planned work this overlaps: the rest of Step 4 (4e/4f shared memory
  between caller and subworkflow); Step 5 event sources, start
  triggers and a persistent store; the open wait-for-event node question;
  Step 6 server/auth.

**To verify in H1:** nothing in AOTN logs to stdout (stray lines would end
up in Telegram messages). A code check on 2026-10-20 found no `print()` in
`backend/` and logging on the default stderr handler; H1 still confirms it
end to end.

## 5. Hermes integration

### 5.1 Short workflows: `aotn run` *is* the cron script

H0's owner-requested [wrapper and H1/H2 specification draft](integrations/HERMES_H0_DRAFT.md)
is ready for review. It refines direct exec into exec of an external output
adapter, preserving the child's natural exit code while escaping/capping its
message. Its checked JSON specs use End nodes with `record_line: false` (#99):
the End stops the branch without adding a completion output line. The draft
does not install wrappers or approve this proposal's wider build order.

```
Hermes cron (no_agent) ──> ~/.hermes/scripts/aotn-<name>.sh
                              └─> cd project; exec <aotn venv>/aotn run <name>
                                   --policy terminate_workflow --data-dir <cron dir>
                                       │
                         stdout ──> Telegram     exit≠0 ──> ⚠️ alert
```

**Wrapper spec** (one file per scheduled workflow, all sourcing a shared
`_aotn_common.sh`):

- `cd` to the AOTN project root.
- Call AOTN's interpreter/entry point by absolute path.
- Pass `--policy terminate_workflow` and `--data-dir` for a separate
  cron-run data directory (owner decision 2026-10-20: separate is fine).
- Derive the workflow name from the wrapper's filename, so adding a job is
  "copy a file".
- `exec` the run so AOTN's exit code reaches Hermes unchanged.
- Cap stdout (about 3,500 characters) with a "…truncated, see run <id>"
  tail.

Fits checks that finish well inside 120 s: heartbeat, watchdog, change
detector, digest.

### 5.2 Long workflows: the outbox

A long run writes messages to an outbox file; one standing `no_agent` cron
job (every minute or so) drains it. The drain script prints the queued
messages (one digest per tick, see C3) and marks them handed off.

```
long AOTN run ──> hermes_notify_node ──> outbox.jsonl
                                              │
Hermes cron (every N min) ──> drain script ───┴─> stdout ──> Telegram
```

Progress updates from a long run are notify nodes at milestones. A parallel
"ticker" branch that notifies every N minutes waits for loop semantics to
mature (completion is sticky; no per-iteration cleanup).

Immediate (non-polled) sending needs a callable Hermes send entry point that
returns the message ID. Hermes mentioned a standalone fallback path in
`tools/send_message_tool.py`; whether a plain script can call it is an open
question (Q1).

### 5.3 Stdout escaping rule

Any Hermes-facing output that may contain outside text (file contents, HTTP
bodies, AI answers) is escaped by default so it cannot contain `[SILENT]`,
start a line with `MEDIA:`, or end with a `wakeAgent` JSON line. A node
option, **allow Hermes directives**, turns escaping off for trusted
template text, which enables:

- `MEDIA:/path/image.png`: `image_generation_node` → Telegram picture.
- `[SILENT]`: an explicit "nothing to say" signal.

### 5.4 Shared folder contract

Proposed root `~/.hermes/aotn/`, schemas owned by AOTN docs, each record
carrying `schema_version`:

| File | Writer | Reader | Purpose |
|---|---|---|---|
| `outbox.jsonl` | AOTN notify node | drain script | Messages waiting to send |
| `events.jsonl` | AOTN nodes, drain script, reconciler | Hermes context reader, digest workflows | Append-only receipts |
| `memory_proposals.jsonl` | AOTN propose node | Owner / Hermes review | Candidate durable facts |

One stable Hermes memory note points at this folder, so Hermes can find the
receipts without them filling its memory.

## 6. Receipts

A notification's receipt moves through stages, and different parties write
each one:

| Stage | Written by | Meaning |
|---|---|---|
| `queued` | AOTN node | In the outbox |
| `handed_off` | Drain script | Printed for this cron tick |
| `delivered` / `failed` | Reconciler reading Hermes cron delivery records, or an immediate sender | Telegram accepted it (or not) |

"Delivered" never means "read". A read/ack stage exists only once a real
acknowledgement (a Telegram button) is wired.

Common fields: `event_id`, `schema_version`, `source` (`AOTN`),
`workflow`, `run_id`, `node_id`, `branch`/supervisor id, `kind`, `summary`,
`created_at`, `stage`, `stage_at`, and `telegram_message_id` when known.

**Deduplication key** defaults to `run_id + node_id + branch id`, because a
node can run more than once per run (branches, loops). An optional
`dedupe_window` suppresses the same key within a time window.

## 7. Candidate nodes

Grouped by what they need. "AI" marks token-spending nodes.

### 7.1 Hermes bridge (IO)

| Node | Does | Notes |
|---|---|---|
| `hermes_notify_node` | Renders a template, appends to the outbox | Config: `message_template`, `destination` alias (never a raw chat id), `priority` (normal/silent/urgent), `event_key`, `dedupe_window`, `allow_directives`, `on_queue_failure`. Outputs: `receipt_id`, `status`, rendered `message`. Never holds the Telegram token |
| `record_event_node` | Appends an event without notifying | How Hermes learns what happened while it was away |
| `propose_memory_node` | Appends a candidate fact to the review queue | Never edits Hermes memory directly |

A `notify_me` *subworkflow* could wrap escaping + cap + outbox so fewer
nodes are needed; subworkflows exist now, so this is buildable once the
notify node exists.

### 7.2 Deterministic tool nodes (the "what Claude does" gap)

| Agent tool | AOTN today | Gap |
|---|---|---|
| Read / Grep / Glob | `file_reader_node`, `file_view_node` | Search and glob nodes |
| Write / Edit | `file_output_node` | Patch/replace node |
| Web fetch | `http_request_node` | — |
| Desktop control | `window_control_node` | More actions |
| Ask the user | `user_text_input_node` | Telegram-delivered variant (7.4) |
| Shell | System nodes: Disk space, Git status, File age (fixed operations, allowed folders; C7) | More System nodes; a generic `run_command_node` later |
| Subagents | `subworkflow_node` (call and wait) | Fire-and-forget (later) |
| Scheduling | — | Step 5 triggers (Hermes cron until then) |
| Memory | Stash (files and text, per machine) | Keyed run state: Step 5 persistent store |

`run_command_node` requirements: a command allowlist in settings (not only
node config), argv only (no shell string by default), working directory and
timeout in config, stdout/stderr/exit code as outputs, and an optional
approval gate. Never enabled by default.

### 7.3 Bounded agent nodes (AI)

| Node | Wraps |
|---|---|
| `hermes_ask_node` | `hermes chat -q "<prompt>"`: Hermes with its memory and tools |
| `claude_code_node` | Headless Claude Code (`claude -p`) |

Shared contract:

- **Allowlist:** tools the agent may use, in node config
  (`--allowedTools` for Claude Code).
- **Limits:** max turns, timeout, optional budget.
- **Trace output:** the exact tool calls made (Claude Code
  `--output-format stream-json`), stored with the run. This is the
  deterministic record of what the AI did.
- **Answer output:** final text, and optionally parsed JSON for routing.
- **Receipt:** a `record_event` entry for every invocation.

Verify CLI flags against the installed versions at build time.

### 7.4 Human-in-the-loop over Telegram

`wait_for_reply_node` suspends a branch until a Telegram button press or
reply. This is the plan's open **wait-for-event** question with Telegram as
one event source. It needs a deterministic handler inside Hermes's existing
Telegram receiver (no second poller on the same bot).

## 8. Workflow patterns (proof of concept ladder)

| # | Pattern | Shape | Needs |
|---|---|---|---|
| H1 | Heartbeat | start → text_output "AOTN alive · {date}" → end | Wrapper + cron job only |
| H2 | Watchdog | check (file age, disk, HTTP) → conditional → output or silence | Wrapper only |
| H3 | Change detector | read last value → compare → notify + store on change | Persistent store |
| H4 | Escalation ladder | check → normal: record event; known error: fixed fix + notify; unknown: `hermes_ask` → notify with diagnosis | record_event, hermes_ask |
| H5 | Daily digest | read today's events → concat → one message | events log |
| H6 | Teach once, replay | an agent does a task with tracing on, then writes the sequence as a spec via `aotn build` | Authoring CLI (exists) + agent guide |
| H7 | AI as router | C3a Jev: Pick one selects a choice id (or `unsure`) → Conditional routes to deterministic sub-flows | C3a; ports-per-choice router later when needed |
| H8 | Approval gate | workflow asks "Deploy? [Yes] [No]" on Telegram, waits | wait_for_reply + Hermes handler |

H1 test cases: normal message; a forced unhandled error (expect alert); a
conditional that skips the output (expect nothing).

**AOTN as a tool for AIs.** An MCP server (local stdio) exposing
`list_workflows`, `run_workflow`, `get_run_status`, `get_recent_events` lets
Hermes or Claude Code run a saved workflow instead of repeating its steps,
saving tokens on the agent's side. Its inputs use the Step 4 contracts,
which exist: `run_workflow` can take typed inputs and return `values`
today. Local stdio does not need Step 6 network auth.

## 9. Effect on the build plan (owner order, 2026-10-22)

H0 is live (heartbeat `63968ee90ae0`); C1 merged in #109 and is live (drain
`cd14afa83db9`, owner-confirmed Telegram delivery); C4 merged in #107/#108.
H2 remains an unscheduled watchdog template. Step 4 through 4d is merged;
4e/4f shared memory and Phase 17 verification remain open. C2 (#110) and C3a
(#112) are merged in main `670b3b3`. C2's review fixes include numeric-overflow
and store-readability checks; Remember and Recall use the standard forwarding
checkbox. The System-node forwarding follow-up merged in #113 (main
`bfcdc36`). Telegram launcher v0 is built on `codex/telegram-launcher` for owner
review in #114: fixed-script quick commands, a 25-second run/cleanup budget
and named installation. Review fixes make timestamp input conditional on the
Start contract and validate install destination types and modes. No live
install or Hermes config change. [Current State](CURRENT_STATE.md) records the
deployment and review details.

The owner approved the following remaining order on 2026-10-22:

| Order | Work | Why here | Depends on |
|---|---|---|---|
| C2 | Saved values: persistent store pulled forward from Step 5, on the Stash's store (#110). **Merged:** [Saved values](STASH_PROPOSAL.md#saved-values-c2): Remember, Recall and If changed (paths Changed / No change), `<data dir>/stash/saved.json` with locked changes, Stash tab 3, `aotn stash saved` | Merged; enables H3 without another workflow-state store | Existing Stash; owner decision C5 |
| C3a | **Jev: Pick one, merged (#112):** Jev only, no provider/model selector; shared Jev client for later nodes; output is the choice id as plain text | Enables H7 through Conditional; below the cutoff (default 0.3), always pass `unsure`, with no Stop option | Jev API key; samples approved 2026-10-22; [built screens and verification](audits/pick_one_2026_10_22/README.md) |
| Telegram launcher | **Built for owner review:** thin Hermes version of a Step 5 start trigger: one `quick_commands` entry of `type: exec` per allowed workflow, calling `aotn-run-<slug>.sh` | No agent turn or plugin; normal sender authorization first; Hermes config is the allowlist; full trigger remains Step 5 | Installed-source answer `556bf7c5c`: no arguments; 30 s reply timeout does not kill the script, so each entry needs its own deadline under 30 s with kill/reap |
| C3b | **Part 1 profile CLI rework for review (2026-10-23):** Ask Hermes (`hermes_ask_node`), isolated profile CLI, strict disabled-tool preflight, one-turn CLI limit, bounded process-tree cleanup, private records and visible unknown usage. Owner-authorized profile smoke succeeded. | [Contract](integrations/ASK_HERMES.md), [built screens](audits/ask_hermes_2026_10_22/README.md); owner-approved samples, answers 1, 2, 4–10 | C1 receipts; Claude task remains a separate later PR after a native Linux CLI is installed |
| C3c | **Simple v1 built for review (2026-10-23):** Ask Hermes to investigate + Investigation result; workflow-gathered redacted excerpts, tool-free `aotn` profile, one-turn script-only bridge, repeat/admission/start caps, atomic records and bounded cleanup. No installs or live jobs. | [Inbox contract](integrations/HERMES_SHARED_FOLDER.md#investigation-inbox-c3c), [setup](../integrations/hermes/README.md#investigation-inbox-c3c-simple-v1), [built screens](audits/investigation_inbox_2026_10_23/README.md) | #116 merged; owner chose no-tools analysis over the samples’ read-only evidence service; that service remains v2 |
| 4e–4f | Shared memory between a caller and its subworkflow | Complete the remaining Step 4 work | Step 4 through 4d (merged) |
| P1 | First-community package: install path, Hermes guide, H1/H2 specs, screenshots and known limits (section 1.2) | Package the proven integrations; describe H2 as a template until configured | H0/C1 live; preceding delivery slices |
| Phase 17 | Verification of the editor/configuration work | Finish the outstanding verification before later expansion | Existing implementation and owner/native evidence |
| C5 | `run_command_node` with allowlist + approval gate | High value, needs careful security design | Settings-level allowlist design |
| Step 5 | Event sources and start triggers; persistent store supplied by C2 | Full Telegram trigger and native scheduling can replace the thin Hermes seam | Step 4; C2 |
| C6 | `wait_for_reply_node` (Telegram) | Resolves the wait-for-event question for one source | Step 5 event sources, Hermes handler |
| Step 6 | Server | Add the planned multi-client service after event sources/triggers | Step 5 |

### New ideas and where they fit (owner, 2026-10-22)

- **Telegram launch:** thin Step 5 trigger via Hermes `quick_commands`,
  `type: exec`, after normal sender auth; no plugin, agent turn or arguments.
  Config is the allowlist: one `aotn-run-<slug>.sh` per allowed workflow. Its own
  deadline must be under the 30 s reply timeout, which does not kill the script.
  Natural-language menus later still need a plugin or an agent turn.
- **Jev:** C3a **Jev: Pick one** is Jev-only, without provider/model selectors,
  using a shared Jev client. Samples are approved; below cutoff (default 0.3),
  pass `unsure`, never Stop. Plain-text choice ids feed Conditional for H7.
- **Simple-purpose nodes:** offer a line of tailored nodes (Pick one, Yes or no,
  Score), so users pick the best fit; avoid one multi-mode node. Selector
  sorting is [backlogged after C3a](PROJECT_BACKLOG.md#node-selector-sorting--after-c3a-owner-2026-10-22).
- **Easy nodes:** follow the existing [helper rule](NODE_HELPER.md); add reusable
  ports-per-choice support when the router needs it, not before the first node.
- **Local models:** an experiment after C3a, comparing the same real choices.
- **Workflow designer:** a new track after C3. Its first step is authoring tools
  (`nodes`, `describe`, `build --check`) in `aotn mcp`; local services/commands
  remain valid integration options. This does not move Step 6 forward.

The [archived conversation reference](archive/plans/INTENT_ROUTING_AND_DESIGN_ASSISTANT.md)
preserves the wider ideas and rationale. The order above is the current plan;
the reference's older sequencing and handoff prompts are historical.

## 10. Owner decisions (answered 2026-10-20)

| # | Decision | Answer |
|---|---|---|
| C1 | Reprioritization in section 9 | **Accepted:** H0, then C1 (notify/record nodes), C4 (MCP server), C2 (persistent store), C3 (bounded agent nodes), ahead of 4e–4f and Step 5 |
| C2 | Shared folder location and schema owner | **`~/.hermes/aotn/`, schemas owned by AOTN docs** |
| C3 | Outbox drain | **One digest per tick** |
| C4 | `cron.wrap_response` | **On, for now** (revised 2026-10-21: Hermes v0.14 applies it to every cron job, not just AOTN's; it adds a job-name header and a management footer. Revisit if the framing gets in the way) |
| C5 | Persistent store | **Pulled forward, built on the Stash's store** |
| C6 | Who schedules once Step 5 lands | **Decide at Step 5** |
| C7 | Running commands | **Specific command nodes first; a generic `run_command_node` later** (see below) |

**C7 in detail (owner, 2026-10-20).** Build nodes that each run one specific
command, for example a Disk space node (`df`) or a Git status node: the
command is fixed in the node's code, the workflow fills only typed settings
(such as a folder), arguments are passed as argv with no shell, and outputs
are typed (free space as a number, changed files as a list) with the node's
own error codes, so a workflow can branch without an AI step. Owner follow-up
(2026-10-22): these three System nodes use the standard Forward incoming
payload unchanged checkbox; forwarding changes the downstream payload while
an enabled Vault output retains the computed report. The node
helper can generate them from a short spec. A generic `run_command_node`
waits until it is needed, behind a command allowlist in Settings with
approval on by default.

## 11. Open questions

- **Q1:** Does Hermes expose a callable "send to destination, return
  message ID" entry point a plain script can use without starting an agent?
  (Decides immediate sending and the `delivered` receipt stage.)
- **Q2:** Where does Hermes record per-run cron delivery outcome, and can a
  reconciler read it safely?
- **Q3:** How are Telegram destinations named/aliased in Hermes?
- **Q4:** Can a deterministic command/button handler be added to Hermes's
  Telegram receiver without a second poller?
- **Q5:** Does anything in AOTN write to stdout during `aotn run` besides
  outputs? (A code check found nothing; confirm end to end in H1.)
- **Q6:** Does `hermes chat -q` run non-interactively with a timeout and
  return only the answer on stdout?
- **Q7 (follow-up from C1, 2026-10-21):** per-job sound control. Hermes has
  no per-job or output option for silent delivery; gateway cron deliveries are
  already silent and its standalone fallback rings. A ringing Urgent (or a
  real Quiet) needs a Hermes enhancement, approved by the owner through
  Hermes. Nothing in C1 depends on it.

## 12. Risks

- **Command execution and AI tool permissions** widen what a workflow can
  do. Allowlists live in settings, approval gates default on for write,
  delete and send actions.
- **Stdout directive injection** (`[SILENT]`, `MEDIA:`) from outside text;
  mitigated by default escaping (5.3).
- **Message floods** from loops or large outputs; mitigated by caps and
  dedupe keys.
- **Hermes upgrades** may change the facts in section 3; the wrapper and
  drain script are the only places that depend on them.
- **Secrets:** AOTN never holds the Telegram token; agent nodes inherit the
  owner's CLI credentials, so they run only on this machine until Step 6
  auth exists.
