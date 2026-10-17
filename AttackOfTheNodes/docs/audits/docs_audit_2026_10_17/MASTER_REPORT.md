> Historical audit, retained 2026-10-17. Only this report survived the external
> audit run; supporting CSVs, scripts, topic matrix, vision sources and evidence
> were not retained. Links to missing supporting files are rendered as literal
> references below. Baseline facts are historical; see [CURRENT_STATE](../../CURRENT_STATE.md).

# Documentation audit — 2026-10-17

## 1. Verdict

The documentation contains substantial design value, but it is an unreliable crash course.
The biggest problem is competing accounts of what is current, including instructions to redo completed work (F01–F04).
There are **46 findings: 16 S1, 26 S2 and 4 S3**; S1 means following the text can break an action or direct work incorrectly.
The opening route is the first repair; document size is secondary (F01, F40).
The node-authoring path also has broken API and regeneration guarantees that need correction before consolidation (F05–F09, F41).
Keep the vision and decision rationale: finite distributed runs, isolated subworkflows, the Stash, typed contracts and a plain keyboard-first UI (V01–V08, V15–V22).
Existing files and owner workflows were left unchanged; only this audit directory was written (evidence/unchanged_worktree.txt).

**Baseline and scope.** `main` at `95f83990d198333688fdf76068ff348f1e8ba689`; default branch independently checked through GitHub and git refs. #64/#65 are merged to main. #66 is merged to the C6 branch, not main. Its Deep Branch port narrowing is absent from the baseline (evidence/github.json, remote_refs.txt, open_pr_changes.json; backend/nodes/debug/deep_branch_node.py:17).

Inventory: 45 top-level app docs, root AGENTS, helper specs, root docs, examples and recursive archive/audit assets: 175 files total. All 46 primary documents have an opening pass and at least 15 recorded claim checks; later sections were sampled. The 2,456 ledger entries include literal path/symbol checks, not that many independent behavior proofs. Scope and unverified results are explicit in claims_verified.csv and evidence/coverage.csv.

Local Markdown links and the two referenced anchors resolve. The 28 code-style reference candidates are triaged separately; most are historical commands, globs or sample filesystem paths, not broken hyperlinks. External web links were not comprehensively crawled (evidence/links.csv, link_triage.csv).

**Verification limits.** The supplied WSL checkout, Windows PowerShell and candidate newcomer-guide files were unavailable. Native Linux git and public read-only GitHub requests were used. The completed baseline suite passed **1,464 tests in 240.59s**, Python 3.12.14; the owner WSL environment, clean dependency installation, native desktop behavior, historical test runs and owner approval provenance remain unverified. One earlier, unfinished suite was stopped when the baseline was refreshed; one full suite completed on the final baseline (evidence/environment.md, full_suite.json).

Paths below are relative to `AttackOfTheNodes/`, except bare document names, which mean its `docs/`; AGENTS and `aotn_node_helper/` are at the repository root. Findings use pinned baseline line numbers. Full receipts are in evidence/code_receipts.md.

## 2. Ranked priority list

These are proposed documentation actions. No reorganization was performed. Effort: S = small edit, M = focused rewrite/extraction, L = consolidation requiring careful preservation.

| Rank | Action and survivor | Why | Evidence | Effort | Newcomer payoff | Vision payoff |
|---|---|---|---|---|---|---|
| 1 | **Fix the entry route; create CURRENT_STATE**. README + AGENTS; link every handoff to it. | The first current-state link sends readers to a merged-PR task and obsolete CLI facts. One checked baseline removes competing session authorities. | F01,F02,F03,F04,F30,F44 | M | Very high: first thing every newcomer hits | High: separates current delivery from the durable direction |
| 2 | **Create one crash course; evaluate the candidate when available**. NEWCOMER_GUIDE, linked first from README. | Setup, run, full tests, data isolation, routing traps and a small working example currently require a scavenger hunt. Candidate content was unavailable, so adoption is conditional. | F01,F07,F18,F21,F24,F40 | M | Very high: one route to first successful run | High: explain why the app exists before implementation details |
| 3 | **Fix the authoritative node reference**. NODE_STANDARDS survives the standardization handoff. | Broken Vault API, obsolete file/error example and conflicting Chat defaults mislead implementation. Keep one current contract and tested examples. | F05,F08,F09,F15,F17,F24,F25,F26,F36 | M | High: prevents broken first nodes | Very high: preserves typed, graph-ignorant community contracts |
| 4 | **Rewrite the helper safety and limitation section**. NODE_HELPER survives helper instructions in AGENT_START_GUIDE. | Put overwrite behavior, spec drift, starter execution and correct cwd commands before generation. Preserve custom methods/tests manually in an isolated review. | F06,F07,F33,F34,F35,F41 | M | High: avoids losing custom code or type metadata | High: makes the ordinary authoring path dependable |
| 5 | **Merge reusable process rules; retire old executable prompts**. Create CONTRIBUTING; keep immediate order in NODE_CONTRACT_PLAN. | The active paste-in restarts C1; older inherited procedure says to merge while current procedure reserves merges to the owner. | F03,F04,F14,F30,F31 | M | High: gives agents a safe, current starting task | High: keeps owner decisions and project taste visible |
| 6 | **Merge runtime references and correct their invariants**. ARCHITECTURE survives PROJECT_KNOWLEDGE and SIGNAL_FLOW; absorb EXECUTION_STATUS_CONTRACT. | Correct completion/output order, RunContext/WaitRegistry, storage overrides and transport exceptions. Keep a short mental model plus deeper contracts. | F12,F13,F16,F21,F22,F23,F25,F26,F27,F42,F43,F46 | L | High: fewer competing explanations | Very high: accurate foundation for child runs and multiple clients |
| 7 | **Consolidate keys and current screen facts**. UI_QUICK_REFERENCE survives keyboard lists in TUI_DESIGN. | Correct five tabs and 64 paths; include execution keys and stop-on-return behavior. Move renderer lessons to CONTRIBUTING/ARCHITECTURE and archive prototype layouts. | F18,F19,F20,F33 | M | High: keyboard-first users get one usable reference | High: protects the plain UI and truthful inspection goals |
| 8 | **Separate live registry facts from the idea catalog**. Keep NODE_CATALOG for intent; use aotn nodes/describe for live facts. | Correct termination and Echo; show 38 registered versus 37 CLI-placeable versus 35 TUI-addable types. Replace duplicate node tables and the hand-maintained file tree. | F10,F11,F16,F28,F43 | M | Medium: accurate discovery and behavior | High: keeps future node ideas without implying they exist |
| 9 | **Split mixed plans; archive resolved session material after extraction**. Keep open items in NODE_CONTRACT_PLAN/PROJECT_BACKLOG; keep originals under archive. | Move completed integration, audit, Wait Until and execution-fix instructions off the entry path. Preserve decisions, unresolved FO7 checks and branch-view design first. | F01,F27,F29,F32,F39,F45; V09–V25 | L | Medium: less obsolete work to read | Very high: preserve reasons and useful future designs |
| 10 | **Split the session log and label status consistently**. SESSION_LOG becomes bounded recent history; older entries remain archived. | The 5,383-line recent-only log is an accidental authority store. Extract owner decisions and keep dates/SHA/implemented/proposed distinctions explicit. | F31,F36,F37,F38; V27,V28 | M | Medium: current context becomes cheap to find | High: owner intent survives without searching thousands of lines |

## 3. All S1 mismatches

These 16 findings are action risks. Other wrong facts and harmless stale labels are in `mismatches.csv` (not retained). Repeated occurrences are grouped under one finding and cited in its evidence field.

### F01 — README.md:3

**Claim:** The first destination is the current project/session rundown.
**Reality:** It leads to an October 6 snapshot that instructs review/merge of already-merged #29 and says the dedicated CLI is future work. NEXT_CHAT_HANDOFF and SESSION_INTEGRATION_BUILD_PLAN repeat the open-PR instruction.
**Evidence:** SESSION_SUMMARY.md:7; SESSION_SUMMARY.md:39; SESSION_SUMMARY.md:68; NEXT_CHAT_HANDOFF.md:9; SESSION_INTEGRATION_BUILD_PLAN.md:41; evidence/github.json PR 29 merged; main.py:20; aotn_cli.py:1.
**Action:** Replace the first route with one current-state record; archive SESSION_SUMMARY and NEXT_CHAT_HANDOFF after preserving unique content.

### F02 — AGENTS.md:102

**Claim:** MASTER_BUILD_PLAN is the active build plan.
**Reality:** Its Current Active Work points to Phase 17 and subcategory filters. The current implemented contract phases and next sequence are in NODE_CONTRACT_PLAN; the selector has five tabs without those filters.
**Evidence:** MASTER_BUILD_PLAN.md:85; NODE_CONTRACT_PLAN.md:13; NODE_CONTRACT_PLAN.md:20; frontend/screens/node_selector.py:52; evidence/github.json PRs 55–65.
**Action:** Route active work to NODE_CONTRACT_PLAN and its execution rules; keep MASTER_BUILD_PLAN for the vision and roadmap.

### F03 — NODE_CONTRACT_EXECUTION_PROMPT.md:10

**Claim:** Confirm approval before starting C1; the paste-in message tells the next session to begin C1.
**Reality:** C1–C3 and C5 are already merged; C4 and C6 are on the audit baseline too. The same prompt acknowledges C1 completion, but its final paste-in still restarts it.
**Evidence:** NODE_CONTRACT_EXECUTION_PROMPT.md:82; NODE_CONTRACT_EXECUTION_PROMPT.md:130; NODE_CONTRACT_PLAN.md:13; backend/vault_declarations.py:135; evidence/github.json PRs 55,56,59,60,64,65.
**Action:** Rewrite the paste-in message around the remaining baseline work and link one current-state record.

### F04 — TASK_INDEX.md:338

**Claim:** Step 1 waits on the owner reading the distributed plan.
**Reality:** The plan records Steps 1, 1b, 2, 3 and the port work done; their runtime, service, CLI and regression tests exist. This route sends a newcomer back to completed work.
**Evidence:** DISTRIBUTED_BUILD_PLAN.md:107; MASTER_BUILD_PLAN.md:357; backend/run_context.py:1; backend/run_service.py:1; tests/test_run_service.py:1; evidence/github.json PRs 31–43.
**Action:** Replace roadmap task instructions with current baseline and remaining gates.

### F05 — NODE_STANDARDS.md:334

**Claim:** Use context.memory_bank.set to write a typed Vault reference.
**Reality:** MemoryBank has no set method. The example raises AttributeError. store_persistent(key, value, type_tag=...) is the available API.
**Evidence:** backend/memory_bank.py:32; evidence/behavior_probes.json vault_example and correct_vault_signature; probe_claims.py.
**Action:** Replace the example with the actual API and the real reference representation.

### F06 — NODE_HELPER.md:609

**Claim:** Custom resolve_output_ports/describe_output_ports methods are preserved by regeneration.
**Reality:** generate_from_spec writes the entire rendered class. It never reads the existing file; --force overwrites custom methods and tests. The later temporary-generation advice is safer but contradicts this guarantee.
**Evidence:** aotn_node_helper/generator.py:119; aotn_node_helper/generator.py:151; aotn_node_helper/generator.py:817; aotn_node_helper/generator.py:1217; RECOVERY_UX_EXECUTION_PROMPT.md:48; evidence/behavior_probes.json rendered_custom_hooks.
**Action:** Put an overwrite warning and explicit temporary-generation/manual-preservation procedure before the first generation command.

### F07 — NODE_HELPER.md:28

**Claim:** The same helper script paths work from the workspace root.
**Reality:** The displayed ../aotn_node_helper paths are relative to AttackOfTheNodes. From the repository root they point outside the repository and fail. AGENT_START_GUIDE repeats this instruction.
**Evidence:** AGENT_START_GUIDE.md:29; aotn_node_helper/create_node.py:1; evidence/behavior_probes.json root_helper_command.
**Action:** Give two explicitly labelled command blocks with the correct working directory and interpreter path.

### F08 — NODE_STANDARDS.md:751

**Claim:** Dead-drop forwarding is the default for the Basic LLM reference; nearby text also says the result goes to Vault by default.
**Reality:** The running Chat Completion defaults emit the result downstream, with forwarding false and Vault output false. The document contradicts itself at line 730 and was not updated for C6.
**Evidence:** NODE_STANDARDS.md:730; NODE_STANDARDS.md:756; backend/nodes/chat_completion_node.py:151; evidence/behavior_probes.json chat_routing_defaults; evidence/github.json PR 65.
**Action:** Keep one tested routing example with explicit defaults and distinguish optional writes from mandatory ones.

### F09 — NODE_STANDARDS.md:619

**Claim:** The File Instance reference outputs a bool and handles errors on the false path.
**Reality:** That demo type is retired. File Write/File Manager emit file references and failures follow the engine error contract. Copying the reference designs a node outside the documented current contract. NODE_HELPER repeats the bool/error example.
**Evidence:** NODE_STANDARDS.md:654; NODE_HELPER.md:273; NODE_CATALOG.md:94; backend/nodes/io/file_output_node.py:63; backend/node_errors.py:1; evidence/runtime_facts.json nodes; NODE_CONTRACT_PLAN.md:57.
**Action:** Replace the obsolete reference with a registered file node and an explicit coded-error example.

### F10 — NODE_CATALOG.md:77

**Claim:** All output nodes have a Terminate branch after completion option; there is no standalone End node.
**Reality:** None of Text Output, File Write or File Manager exposes that option. End is registered and explicitly terminates; the TUI selector hides it, while workflow authoring can place it. Newcomers need that distinction, rather than the retired policy.
**Evidence:** NODE_CATALOG.md:181; NODE_STANDARDS.md:158; backend/nodes/end_node.py:51; frontend/screens/node_selector.py:67; backend/authoring.py:63; evidence/behavior_probes.json has_retired_output_completion_control.
**Action:** Correct the catalog and explain natural route endings, explicit End, and its current TUI availability.

### F11 — NODE_CATALOG.md:242

**Claim:** Echo forwards the incoming value unchanged.
**Reality:** Echo converts it to str and optionally prefixes a label. Integer 7 becomes string "7". Its class docstring and description repeat the false guarantee.
**Evidence:** backend/nodes/debug/echo_node.py:1; backend/nodes/debug/echo_node.py:14; backend/nodes/debug/echo_node.py:24; evidence/behavior_probes.json echo.
**Action:** Document Echo as text conversion; use No-Op or the fixed-forwarding debug nodes for identity preservation.

### F12 — ARCHITECTURE.md:238

**Claim:** The supervisor marks completion before writing transient output.
**Reality:** The runtime publishes/routes output first and marks the saved completed-node ID afterward. The documented order would reintroduce the cross-branch Wait Until race that the project fixed.
**Evidence:** ARCHITECTURE.md:239; backend/supervisor.py:300; backend/supervisor.py:358; EXECUTION_STATUS_CONTRACT.md:45; tests/test_wait_until_vault.py:1.
**Action:** Correct the ordered run-loop example and make this ordering an engine invariant.

### F13 — MASTER_BUILD_PLAN.md:332

**Claim:** The built-in subworkflow runs as a child supervisor.
**Reality:** The approved direction specifies a child RunContext linked by parent_run_id, with separate run identity and lifetime. Implementing supervisor nesting instead would send Step 4 in the rejected direction.
**Evidence:** DISTRIBUTED_BUILD_PLAN.md:49; DISTRIBUTED_BUILD_PLAN.md:390; backend/run_context.py:1; evidence/symbols.csv RunContext.
**Action:** Replace the earlier Phase 19 mechanism with the approved child-run design; preserve its reuse goal.

### F14 — RECOVERY_UX_EXECUTION_PROMPT.md:39

**Claim:** The old per-phase procedure tells an agent to merge; the active prompt imports its hard rules and environment notes.
**Reality:** The current process explicitly says the owner merges, yet older instructions also give a gh pr merge command. Copying the old process can publish a merge outside the current ownership rule.
**Evidence:** RECOVERY_UX_EXECUTION_PROMPT.md:86; DISTRIBUTED_EXECUTION_PROMPT.md:70; NODE_CONTRACT_EXECUTION_PROMPT.md:105; NODE_CONTRACT_EXECUTION_PROMPT.md:14.
**Action:** Keep the owner-merges rule in one process document; label completed execution prompts as historical and remove them from live procedure routes.

### F15 — README.md:66

**Claim:** The adopted standardization handoff uses canonical category, retires aliases and renames group.
**Reality:** The handoff explicitly cancels that rename in its June 19 revision, and the factory still exposes category, primary_family, legacy_category and group. The router promotes a rejected implementation direction.
**Evidence:** NODE_STANDARDIZATION_HANDOFF.md:16; backend/node_factory.py:166; backend/node_factory.py:174; evidence/runtime_facts.json.
**Action:** Correct the directory synopsis; fold the surviving contract into NODE_STANDARDS and archive the superseded handoff.

### F41 — NODE_HELPER.md:250

**Claim:** The legacy input/output metadata sections still work alongside the unified contract format.
**Reality:** Legacy output_port_metadata is reduced to name and description by _port_metadata. A real number output in the Random Number spec loses data_type during normalization, which turns generated metadata into any. The C8 warning names this risk but the helper-first entry path does not.
**Evidence:** NODE_HELPER.md:296; aotn_node_helper/generator.py:1137; aotn_node_helper/specs/random_number_node.yaml:1; NODE_CONTRACT_PLAN.md:54; evidence/behavior_probes.json random_number_spec_metadata.
**Action:** Make the limitation explicit at the first helper command; use reviewed unified blocks and do not promise safe regeneration of the existing spec inventory.

## 4. Proposed source of truth by topic

The complete 46-document matrix and consolidation choices are in `topic_matrix.md` (not retained). Code remains factual authority; a proposal is not an implemented capability.

| Topic | Single documentation authority | Main conflicts |
|---|---|---|
| Mental model | ARCHITECTURE.md | F16,F21,F22,F25,F27,F42 |
| Setup | NEWCOMER_GUIDE.md (create or validate the unavailable candidate) | F01,F07,F40 |
| Run and test commands | NEWCOMER_GUIDE.md; WORKFLOW_AUTHORING.md owns the authoring subcommands | F07,F40,F44 |
| Engine rules | ARCHITECTURE.md | F12,F21,F22,F32 |
| Node contract | NODE_STANDARDS.md | F05,F08,F09,F15,F17,F41 |
| Type system | NODE_STANDARDS.md, linking backend/data_types.py and backend/file_refs.py | F24,F25,F26,F41 |
| Validator | NODE_STANDARDS.md, linking the issue-code registry | F24,F27,F42 |
| UI keys | UI_QUICK_REFERENCE.md | F18,F19,F20,F33 |
| Process | CONTRIBUTING.md (merge surviving instructions) | F03,F04,F14,F15 |
| Environment | CONTRIBUTING.md, with owner WSL notes labelled as one environment | F07,F21 |
| Current state | CURRENT_STATE.md (create; all other docs link) | F01,F02,F03,F04,F29,F30,F31,F37,F38,F44,F45 |
| Roadmap | DISTRIBUTED_BUILD_PLAN.md; NODE_CONTRACT_PLAN.md owns the immediate delivery order | F02,F03,F04,F13,F31 |

The live node catalog is the factory/CLI metadata, not a hand-maintained prose table. The catalog mentions all 38 registered identifiers; AGENTS names only 30. There are 37 backend-authorable types but 35 TUI-addable types because the selector additionally hides Start and End. The family/port comparison is complete in evidence/node_ports.csv; legacy category and primary family are different metadata concepts (F16, F17; backend/authoring.py:63; frontend/screens/node_selector.py:67).

## 5. Vision and what must survive

The project is aiming for a workflow tool people can trust with complicated jobs that take time. Its value is not the number of node types: it is being able to build a recipe, see what is happening, supply input, recover from a failure and understand what actually ran. The factory-and-control-room model is useful because it keeps execution separate from the operator’s view. That separation is already visible in the engine and UI; the distributed plan makes it a foundation for further clients. [V01, V19, V22]

Predictability comes from explicit contracts. A node should declare its ports, types, requirements and effects once. The selector, form, connection chooser, validator, runtime and tests should tell the same story. A green check should mean that the behavior the user configured is the behavior the engine will honor. This also gives community authors a manageable way to add capabilities. The helper is intended to make the routine parts boring; its current overwrite and spec-drift limits need to be stated honestly. [V03–V05, V26]

The workflow should remain useful beyond its original terminal session. The CLI is already another adapter; a website, desktop client or hardware endpoint can eventually use the same engine. Start inputs and End outputs form one contract for every caller. A reusable subworkflow becomes a separate child run with its own identity and lifetime, linked to its parent, rather than an ambiguous scope inside a long-lived run. Triggers create finite runs, with explicit queue/drop behavior, instead of one watcher run that retains resources forever. Authentication, concurrency isolation and transport-safe events are still future work. [V01, V02, V10, V13]

The Stash connects that direction to a daily annoyance: repeatedly typing paths and reusable text. It should keep machine-local values outside the workflow, first by copying into configured fields and later through contract-input bindings. The same portable workflow can then run on another machine after rebinding its inputs. It is not another per-run Vault. Its proposed limits, missing-path warnings, input precedence and separation from secrets are part of the design’s usefulness, not incidental implementation detail. [V06–V08]

Recovery and inspection matter as much as starting a run. A handled failure should be visible without making a successfully recovered workflow look broken. A stopped or skipped visit must not become a checkmark. Future per-branch inspection should preserve the user’s place and distinguish visits and retries, while keeping previews bounded and honestly attributed. Resource ownership should be clear: files and session handles belong to a run, and failure evidence is retained when needed. The documents do not establish general crash-resume/checkpoint recovery; that should not be promised. [V01, V17–V20, V23, V24]

The interface should stay plain, compact and usable from the keyboard. Clear names, useful source/type previews, only applicable controls and predictable Save/Discard/Stay behavior help people reason about a complex graph without ornamental clutter. A better node taxonomy and future live output panels serve that goal. Cross-platform support remains an ambition, with honest capability detection rather than treating WSL verification as proof of desktop support everywhere. These qualities should survive consolidation even if most session handoffs and finished plans move out of the main reading path. [V09, V11, V12, V15, V16, V20, V21, V25, V30]

Before archiving anything, extract the unique content listed in `vision_sources.md` (not retained). It identifies 30 source ranges and a destination for their intent. In particular:

- Preserve distributed decision records and rejected alternatives, the one-contract-per-caller rule, child-run isolation and explicit trigger concurrency (V01, V02).
- Preserve the Stash’s machine-local portability, binding precedence, missing-input refusal, paste rules and separation from secrets (V06–V08).
- Preserve node-library reuse, the five-family reasoning, live output-display ambitions and cross-platform capability honesty (V09–V16).
- Preserve truthful lifecycle outcomes, visit/attempt identity, bounded previews, resource lifetimes and recovery/edit invariants (V17–V20, V23–V25).
- Preserve the owner’s plain compact UI preferences and the decisions scattered through execution prompts and SESSION_LOG (V21, V27, V28).

Archiving should retain the full original with a dated resolution/supersession note. A table of milestones alone would lose the reasons these features belong together.

## 6. Newcomer tests

These are documentation desk walkthroughs followed by code/command verification, not a blinded usability study. Counts are unique consulted document lines per task, excluding code and generated help. Exact ranges are in evidence/newcomer_routes.csv; they measure these routes, not a mathematical minimum.

| Task | Documents | Lines | Result |
|---|---|---|---|
| (a) Setup, launch, tests | 7 | 286 | Runnable after reconciling routes; existing dependencies reused; clean installation unverified. |
| (b) Plan a forwarding debug node | 9 | 960 | Plan possible, but authoring instructions require safety corrections; no node written. |
| (c) Explain Parallel Branch → Merge | 8 | 289 | Basic model available; current limits and group/barrier traps require deeper reading. |

### (a) Setup, launch and run tests

The route starts at AGENTS → README → SESSION_SUMMARY, then needs TUI_DESIGN installation instructions, PROJECT_KNOWLEDGE launch guidance, AGENT_START_GUIDE checks and the execution prompt’s process notes. Installation and the launch entry exist, but the router has no setup task; “Main tests” points to only test_debug_nodes.py. The exact full-suite command in this audit came from the audit brief, not a clean first-run path (F01, F40; PROJECT_KNOWLEDGE.md:29; AGENT_START_GUIDE.md:278).

Actual checks: the production-styled EditorScreen mounted at 100×30 through main.run_tui. The exact JSON example in WORKFLOW_AUTHORING built in check-only and save modes, then inspect and run returned exit 0. nodes, describe with --set, and run --help also succeeded. The baseline full suite passed once. All generated workflow/data files were inside this report directory (evidence/newcomer_commands.json, documented_workflow_spec.json, full_suite.json).

The crash course needs these traps up front: set AOTN_DATA_DIR before imports; Vault data is run-scoped; --input is currently recorded but not bound into workflow contracts; type mismatches can be warnings; pause is cooperative; node_timeout_seconds is not an execution-wide timeout; returning from execution stops a live run. These are current limitations, not a request to change them (backend/persistence.py:25; STASH_PROPOSAL.md:54; ARCHITECTURE.md:46; EXECUTION_STATUS_CONTRACT.md:52; frontend/app.py show_editor_screen; evidence/behavior_probes.json).

### (b) Plan a forwarding debug node, end to end

The task route reaches nine docs because it crosses standards, practical checklist, helper syntax, taxonomy, migration history and current contracts. The helper-first structure and no-frontend-edit rule help. The broken Vault API, incomplete family list, contradictory defaults and unsafe preservation guarantee are the traps (F05–F09, F17, F41).

The resulting plan is: check NODE_CATALOG for overlap with Probe/Logger/No-Op; declare category debug and primary_family Utility; one any input named input and one default output; a small optional label parameter; fixed-forwarding ui_hints with forwarded_input_port=input; no fake Source/Vault controls or optional forwarding checkbox. The custom execute body would log through the normal output-log structure and signal the same input value on default with a plain signal_done call. It would not inspect graph/UI state (AGENT_START_GUIDE.md:70; NODE_HELPER.md:386; backend/nodes/debug/probe_node.py:19; backend/nodes/debug/probe_node.py:31; NODE_STANDARDS.md:175).

Generate only into an isolated review location; inspect the whole generated diff and preserve custom hooks/tests deliberately. Verification would cover registration, non-string payload identity, log attribution, error-port non-forwarding, schema rendering and Save/Cancel behavior, then the helper checks. Existing generated smoke tests alone do not prove those behaviors. No spec, node implementation or node test was written for this task (F06, F35, F41; tests/test_forwarding.py; aotn_node_helper/generator.py:858).

### (c) What Parallel Branch does at Merge

Parallel Branch computes a seed per configured path and requests a child supervisor for each connected path. The spawning supervisor ends that path; it does not continue on a default output. Width is 2–64, default 2; max_branch_depth defaults to 5 and is a separate nesting limit. Siblings share the run’s Vault. Merge Beacons and editor closure choices create real graph edges into Merge slots (backend/nodes/branch_node.py:129; backend/supervisor.py:806; backend/supervisor.py:828; backend/configuration_manager.py:15; SIGNAL_FLOW.md:476; evidence/runtime_facts.json).

At runtime, Merge records each arrival in its branch group, removes that branch from pending, and waits until pending is empty. Sibling termination also releases its pending membership. One winning arriving supervisor continues; the others terminate. The selected input supplies one forwarded value; Merge does not aggregate all inputs. Without a branch group it continues immediately. Five slots is the default, not the maximum (backend/master_state.py:553; backend/master_state.py:610; backend/master_state.py:624; backend/nodes/merge_node.py:29; evidence/behavior_probes.json).

The docs help with seeds, Beacon wiring, carry-forward and sibling termination. They mislead on the old 2–5/fixed-five limits (F18, F32). The critical deeper trap is that Merge’s group can include a branch parked on Wait Until that needs a node after that Merge; this can deadlock. A target reachable only through its parked waiter is another documented limit. These are not general deadlock detection or automatic recovery guarantees (ARCHITECTURE.md:303; backend/master_state.py:585; backend/wait_registry.py).

## 7. Suggested target layout — proposal only

**Target: 16 active top-level documents**, down from 45. Root AGENTS remains a short pointer; helper specs, examples, archives and audit evidence remain outside that count. This is an organization proposal, not authorization to move anything.

| Purpose | Files |
|---|---|
| Entry and current work | README, NEWCOMER_GUIDE, CURRENT_STATE |
| Contributor process | CONTRIBUTING, bounded SESSION_LOG |
| Runtime and boundaries | ARCHITECTURE, BACKEND_FRONTEND_BOUNDARY |
| Nodes and interaction | NODE_STANDARDS, NODE_HELPER, NODE_CATALOG, UI_QUICK_REFERENCE, WORKFLOW_AUTHORING |
| Direction and remaining work | NODE_CONTRACT_PLAN, DISTRIBUTED_BUILD_PLAN, STASH_PROPOSAL, PROJECT_BACKLOG |

Newcomer path: README → NEWCOMER_GUIDE → one task reference. The guide should target about 120–180 lines covering purpose, setup, first run, tests, mental model and the traps above. Runtime work then goes to ARCHITECTURE; node work to NODE_STANDARDS/NODE_HELPER; workflow construction to WORKFLOW_AUTHORING. Those length limits are proposed budgets, not measured outcomes.

CURRENT_STATE alone owns the checked main SHA, PR state/base, suite result/environment, current task, known blockers and owner gates. Other docs link to it. NODE_CONTRACT_PLAN owns immediate delivery order; DISTRIBUTED_BUILD_PLAN keeps the long-term decisions. Keep decision dates even when implementation status changes.

Rejected option: one comprehensive handbook containing setup, architecture, current state, plans and history. It would reduce filenames while recreating the same mixed-authority problem and making the vision hard to find. A small entry path with stable references and separately preserved decisions fits both goals better (F01–F04, F37; V01–V30).

## 8. Open questions for the owner

1. Where can the local newcomer-guide candidate and README edit be read? They were unavailable here, so their quality and any conflicts remain unverified.
2. Should the C7 merge on the C6 branch be brought to main before the next phase? GitHub says merged, but main still has Deep Branch default+branch ports (F30).
3. What is the current explicit authorization for naming, Stash S1–S3 and Step 4? The order is recorded, but proposal/approval wording and old paste-in gates disagree. This audit does not infer approval from code or elapsed time (F03, F31; STASH_PROPOSAL.md:3; STASH_PROPOSAL.md:247).
4. Should End remain hidden from the TUI selector while docs recommend it for explicit termination? Backend authoring can place it; the current UI policy needs a clear user-facing explanation (F10).
5. Is the proposed 16-document active set acceptable, with full historical originals preserved? In particular, retain the Stash and distributed decision records as substantial vision documents rather than reducing them to backlog rows (V01–V08).
6. Is a native-platform FO7 result available, and which OS/terminal hosts should be verified first for a supported release? This audit leaves FO7 unverified and follows the current request’s strict workflow protection; older dated session permissions are not treated as current authorization (FILE_OUTPUT_BUILD_PLAN.md:45; PROJECT_BACKLOG.md:82; RECOVERY_UX_EXECUTION_PROMPT.md:52).

Supporting files: `inventory.csv` (not retained), `mismatches.csv` (not retained), `claims_verified.csv` (not retained), `topic_matrix.md` (not retained), `vision_sources.md` (not retained), and `REPRODUCE.md` (not retained).
