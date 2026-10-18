# Node Contract Plan (from the PR #51 node audit)

Status: **C1–C7 approved** (owner, 2026-10-14); **C8–C12 still proposed**,
to be approved one at a time once required/optional settles. Recorded on
2026-10-13 from an external audit of all 38 registered node types at PR #51's
head (`4e7af7d`). The owner chose to fix only the shared Vault model inside
PR #51 and to plan the rest. Timing (owner): after UX6 and before
`DISTRIBUTED_BUILD_PLAN.md` Step 4, C1–C7 in order, one PR each. Ask the
owner where a phase needs a decision (C5's number policy, C6's field
removal, C7's Deep Branch contract) and before Step 4. Each item needs a
reproduction first; the audit gives one for each.

For the checked implementation baseline, open PRs and owner gates, see
[Current State](CURRENT_STATE.md). Phase rows below retain completion details.
Historical integration note (2026-10-17): C7's #66 merged to the C6 branch;
#67 re-landed it on main. Workflow naming followed in #68 (see Session Log).
Stash S1 (core, paste parser, `accepted_types`) with the S3b `aotn stash` CLI
followed in #70 (owner approved S1 with the CLI, 2026-10-17). Stash S2, the
Stash screen, followed (`dist/stash-s2`; owner approved the sample screens).
Stash S3, inserting an entry into a node config field with `P`, followed
(merged #75, `714f190`, 2026-10-18). The owner then adopted three keymap
PRs: foundation, shared policies/high-traffic screens, generated Help/hints;
see [Frontend Command UI Toolkit](PROJECT_BACKLOG.md#near-term-project--frontend-command-ui-toolkit).
Phase 1 merged as #77; phase 2 is awaiting review. Step 4 stage 4a-1
(backend/CLI) proceeds separately; the 4a-2 screens follow keymap phase 2.

**Agreed order (owner, 2026-10-15; extended 2026-10-17):** C3 → C5 →
workflow authoring tool v1 → C4, C6, C7 → workflow
naming PR (rename in the library, name prompt on New; the backend already
has `rename_current_workflow`) → Stash S1–S3 (`STASH_PROPOSAL.md`,
proposal) → `DISTRIBUTED_BUILD_PLAN.md` Step 4 (sub-workflows) with Stash
S5 designed in.

Goal: one node contract (ports, config, effects, capabilities) that drives
the config UI, connection matching, preflight, runtime routing and author
tests, so that a green check means the runtime honours the generated UI.
Keep `NodeContext` and graph-ignorant execution.

## Done in PR #51

- One Vault read/write model, `backend/vault_declarations.py`
  (`active_vault_reads`, `typed_vault_writes`, `active_vault_writes`), used by
  the Connections tab, the Vault pickers (`memory_registry`,
  `NodeConfigScreen._declared_vault_writer_keys`) and the validator's
  existence/type/race checks. Node-specific writers (Set Variable, Variable
  Setter, Counter) have an unknown type (`None`, treated as `any`).
- The `await context.signal_done(...)` examples in `NODE_STANDARDS.md` and
  `AGENT_START_GUIDE.md` are fixed (it is a plain call).

## Proposed phases

| # | Item | Audit finding | Notes |
|---|---|---|---|
| C1 | Preflight checks for node-specific **reads** (Get Variable, Variable Reader, Conditional, Branch `vault:` seeds) | follow-up to 1 | **Done.** `vault_read_entries` flags every read required/optional; `config_vault_read_entries` marks all node-specific reads optional (each has a fallback). An optional read with no writer is a preflight **warning** ("Unwritten Vault key"); a required one is an error. Counter writes its own key, so it never warns. The parallel-branch race warning now covers node-specific reads too. Later: a declared workflow input (Step 4) also satisfies a read. |
| C2 | Edge compatibility diagnostics | 2 | One shared compatibility function for connector choice, Source dropdowns and preflight. Start with warnings for known-incompatible active edges (Random Number → File Reader on Upstream); keep `any` paths working. Runtime errors name the receiving node/port and the expected/actual shape. **Done:** `data_types.types_compatible` (exact match, `any` matches all) used by connector choice, Source dropdowns and the validator; `port_types.trace_producer` follows pass-through nodes; an active Upstream mismatch is a "Type mismatch" warning; File Reader, File Write and File View errors use `input_mismatch_message`. Mode-dependent output types are C3. |
| C3 | Mode-resolved output types | 3 | HTTP Request file mode → `default:file`, text mode → `default:string` through the per-node output-metadata hook; used by previews, insertion (auto-wiring picked File Write's `content` instead of `file_path`), validation and Vault typing. **Done:** HTTP Request's `describe_output_ports` resolves `default` to `string` or `file` (spec declares the port, type `any` statically); `port_types.resolved_metadata` gives config-resolved metadata to Vault typing (validator, Vault pickers, previews). Audit of every node with a concrete output type: HTTP Request is the only one whose type changes with a setting. |
| C4 | Fixed-forwarding capability and provenance | 4 | Declare forwarding for No Op, Logger, Probe, Memory Snapshot, Merge Beacon, Repeat Counter (Counter and Sleep have hints). Output type follows the input; show a read-only forwarding summary, not an optional checkbox. Branch/Conditional/Merge need config-selected forwarding. **Done (fixed forwarding):** No-Op, Logger, Probe, Memory Snapshot, Merge Beacon and Repeat Counter declare `ui_hints` `pass_through` (a one-line summary the editor shows read-only) and `forwarded_input_port`; a test checks each declaration against execution; the `error` port never forwards (it carries the failure record). Types now flow through them (validator, dropdowns, selector filter, inspect). **Still open:** config-selected forwarding (Conditional forwards its input or a Vault variable; Merge forwards a selected branch). |
| C5 | Save-time validation of numeric fields | 5 | `form_generator.py` turns unparseable numbers into `0.0`. One policy for malformed, out-of-range and non-finite values: inline error, keep the typed text, block save; same constraints in backend config validation. An existing test encodes the coercion and must be updated deliberately. **Done (policy approved by the owner 2026-10-15):** `field_types.check_number` (finite, `min` / `max` / `min_exclusive`, integers whole, blank = the default) used by the node editor's save (inline error under the field, typed text kept, save blocked, focus to the first bad field) and the validator (`invalid_number`, blocks the run). The form no longer coerces to 0. Limits added: Chat max tokens ≥ 1, temperature 0–1; HTTP timeout > 0; Repeat Counter max visits ≥ 1. |
| C6 | Random Number's ignored `value` field | 6 | Remove the control; keep any stored key through a migration. **Done:** the cause was the generator's `producer` template adding a Payload field to every producer; specs can now set `payload_field: false` and Random Number's does. The field is removed from the class by hand (its spec has drifted; see C8). A saved `value` key is kept and ignored without a migration (nothing transforms it; editor and loader keep unknown keys; tested). Owner addition: Chat Completion's Vault output defaults to off, so a fresh node validates. |
| C7 | Deep Branch continuation | 7 | `default` never runs after spawning; fix the contract or narrow the ports/description, and test that End actually executes. Parallel Branch semantics stay as they are. **Done (owner, 2026-10-17: narrow it; it is a debug node):** `default` removed; Deep Branch offers only `branch` and its description says its path ends. Instead of an End check, the test loops `branch` back into the node and asserts branches at depths 0–5 and a finished run, which tests what the node is for. Saved workflows that wired `default` get `undeclared_port`. Review fix: the child now receives the payload (Deep Branch stores its `branch` output, as Parallel Branch stores its paths); tested. |
| C8 | Helper specs and generator | community gaps | Only 12 of 38 types have specs; six differ from their classes (Chat Completion, File Manager, File Reader, File Write, Start, Text Output). Reconcile before treating specs as safe regeneration sources. Generated starters read `inputs['input']` regardless of the declared source; generated tests check registration only. **Found in C6:** Random Number's spec has drifted too (family Utility vs Complex, colour, group); the generator's `_port_metadata` keeps only name/description, so a spec's output `data_type` is dropped (regenerating Random Number lost `data_type: number`). Specs safe to regenerate today: HTTP Request (C3, C5). |
| C9 | Author conformance gate | community gaps | Extend `check_ui` (production CSS, widths, keyboard, save/reopen) and add contract tests (source matrix, emitted shape per mode, routing/Vault effects, invalid config rejected). |
| C10 | Declarative Vault effects | recommended contract | Let nodes declare their reads/writes instead of the `node_type` switch now in `vault_declarations.py`. |
| C11 | Doc conflicts | standards | Basic LLM forwarding default contradiction; File Instance example uses a boolean success result instead of coded errors; `data_types.py` describes references as strings although they are tagged JSON objects. |
| C12 | External node packages | later | Discovery through Python entry points with contract versions and a collision policy; separate reviewed change. |

## Owner direction (2026-10-14)

- **Required and optional inputs/outputs.** All nodes will be re-touched soon
  and each port and Vault read/write classified as required or optional; the
  rules get sharper as new nodes are made and old ones adjusted. Design the
  contract (C1, C2, C4, C10) so required/optional is a declared property, not
  a per-node guess. Expected end state: a required read with no writer and
  no declared workflow input (Step 4 subworkflow contracts) is an error; an
  optional read with a fallback is a warning that unattended runs report.
- **More data types** for Vault entries and dead-drop payloads, so community
  nodes can say precisely what they produce and accept. Today's set covers
  what the memory model does now; extend `backend/data_types.py` with the
  contract work (C2, C3, C11) rather than ad hoc per node, keeping `any` for
  genuinely heterogeneous values.
- **Help:** a per-panel `H` popup listing every key binding, with the bottom
  ribbon reduced to the basic movement keys and `h help`.
- **Labels:** stable display identity matters once labels appear in run
  history, logs or a second frontend; the numbered suffix was dropped for now.

### Workflow authoring tool (agreed 2026-10-15; after C5, before C4)

Goal: build preconfigured workflows from a small JSON spec, through the same
backend services the app uses, so agents and people can make example and
test workflows without hand-written scripts. Core in a backend module
(`backend/authoring.py`), the `aotn` CLI as one adapter; a future server or
AI tool interface wraps the same functions.

- **PR 1, core:** `list` and `describe` node types from the registry,
  config-aware (a six-path Branch shows six outputs; HTTP Request in file
  mode shows a file output). `build` from a versioned spec: named nodes
  with real config keys merged over defaults, explicit connection ports,
  spec-local node names mapped to generated IDs (translated only in fields
  declared as node references, e.g. Wait Until targets), shared checks,
  the app's save preparation, reload into a fresh map and re-check,
  atomic write, never overwrite an existing save. JSON and readable output.
- **PR 2, inspect + examples:** a readable report of execution paths,
  effective config, Vault writers/readers and ordering ("reads `doc`; its
  writer is on a parallel branch; ordering not guaranteed"), and "unchecked"
  wherever the contract cannot tell. A checked-in folder of example specs
  for real use cases, built and validated by the test suite; they double
  as owner test benches and as the Step 4 test corpus.
- **First, reproduce and fix in shared helpers** (so the TUI benefits):
  `connect()` accepting undeclared ports, unknown config keys passing
  silently, `update_node_config()` replacing instead of merging, empty
  schemas (Merge). Bad numbers are C5's shared policy, reused here.
- **Deferred:** templates, automatic graph planning, live editing of an
  open workflow, a server/MCP transport. Running stays `aotn run`.

Legacy UI migration by family (shared Source control and typed Vault picker,
shared Payloads component, hiding empty sections such as No Op's Parameters
and End's Payloads) follows C1–C9. The owner's live-test findings in
`PROJECT_BACKLOG.md` (window nodes, missing pass-through, outdated Vault UI,
reveal autoscroll, error UI keys during runs) overlap C4 and the migration.

### Migration inventory (2026-10-14, from code)

Read from each type's config schema and defaults at `main` + PR #56. "Current"
means the shared Source selector with a Vault option (`<port>_source`) and/or
standard Vault output routing (`vault_write`). The "Likely needs" column is a
proposal to confirm per node when its family is migrated; never add Vault or
forwarding controls a node does not implement (F01).

**On the current model (7):** Chat Completion (prompt, document, context 1–8;
Vault output), File Write (content, file path; Vault output), File Reader
(file; Vault output), File Manager / `file_view_node` (file; Vault output),
Window Control (file; no Vault output), Text Output (input; legacy key list
for output), Start (Vault output only).

| Family | Node | Today | Likely needs |
|---|---|---|---|
| Data | Concat | no source selector | Source control per input; Vault output |
| Data | Text Transform | Parameters only | Source control; Vault output |
| Data | JSON Path | Parameters only | Source control; Vault output |
| Data | Random Number | Parameters only (ignored `value` removed in C6) | Vault output; hide Source |
| Data | Get Variable / Variable Reader | own `variable_name` read | own field stays (no Vault picker); typed key picker later (C10) |
| Data | Set Variable / Variable Setter | own write, pass-through option | own field stays; hide empty sections |
| Data | Counter | own key, pass-through | own field stays; hide empty sections |
| Data | Memory Snapshot | none | forwarding summary (C4); hide empty sections |
| IO | HTTP Request | own body source, no Vault option | Source control with Vault; mode-typed output (C3) |
| IO | User Text Input | legacy output keys | Vault output routing |
| AI | Embedding, Image Generation | none (simulated) | Source control; Vault output; no inert secrets (F10) |
| Flow | Conditional | own left-value source | own source stays; hide empty sections |
| Flow | Parallel Branch | per-path seeds | keep focused layout (do not redesign) |
| Flow | Random Branch, Deep Branch | none | hide empty sections; Deep Branch contract settled in C7 |
| Flow | Merge, Merge Beacon, Wait Until | topology-driven | keep focused layout; Merge Beacon forwarding (C4) |
| Flow | End | none | hide empty Payloads |
| Flow | Error Mux | routes | keep focused layout |
| Debug | Logger, Probe, No-Op, Repeat Counter | none | forwarding summary (C4); hide empty sections |
| Debug | Sleep | pass-through hint | hide empty sections |
| Debug | Echo, Error Trigger | none | truthful descriptions (F11); hide empty sections |

Pass-through/forwarding exists on Counter, Set Variable, Sleep, Variable
Setter, Chat Completion, File Write, File Manager and Window Control, and
since C4 on No-Op, Logger, Probe, Memory Snapshot, Merge Beacon and Repeat
Counter (answers the backlog's "which nodes lack pass-through"). Deleted
Node (`tombstone_node`) is a backend record, not a migration target.

**Do not:** redesign Branch/Merge/Wait coordination, or put forwarding/Vault
checkboxes on nodes that do not implement those capabilities.

The audit's per-node table and probe files live outside the repository with
the audit report; copy the table here if a phase needs it.

## Documentation reorganisation (2026-10-17)

| Phase | Scope | Delivery |
|---|---|---|
| A | Entry route, newcomer guide and audit F01–F15/F41 | Prepared on `docs/a-entry-route`; publication/verification in [Current State](CURRENT_STATE.md) |
| B | Rebuild vision sources, preserve reasoning, consolidate and archive | Prepared on `docs/b-consolidation-vision`; see Current State for verification/review |
| C | Bound session history and address remaining S2/S3 | After B merges |
