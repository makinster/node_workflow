# Node Contract Plan (from the PR #51 node audit)

Status: **proposed, not approved.** Recorded on 2026-10-13 from an external
audit of all 38 registered node types at PR #51's head (`4e7af7d`). The owner
chose to fix only the shared Vault model inside PR #51 and to plan the rest.
Timing (owner, 2026-10-13, by best judgement): after UX6 and before
`DISTRIBUTED_BUILD_PLAN.md` Step 4, bug items C1–C7 first. Confirm with the
owner before starting C1. Each item needs a reproduction first; the audit
gives one for each.

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
| C1 | Preflight checks for node-specific **reads** (Get Variable, Variable Reader, Conditional, Branch `vault:` seeds) | follow-up to 1 | Today only standard-model reads and `membank_inputs` are checked. Proposed: a **warning** for now (these nodes have fallbacks; Get Variable's default key `value` often has no writer), and record each read as required or optional in the shared model so it can tighten later (see "Required and optional"). |
| C2 | Edge compatibility diagnostics | 2 | One shared compatibility function for connector choice, Source dropdowns and preflight. Start with warnings for known-incompatible active edges (Random Number → File Reader on Upstream); keep `any` paths working. Runtime errors name the receiving node/port and the expected/actual shape. |
| C3 | Mode-resolved output types | 3 | HTTP Request file mode → `default:file`, text mode → `default:string` through the per-node output-metadata hook; used by previews, insertion (auto-wiring picked File Write's `content` instead of `file_path`), validation and Vault typing. |
| C4 | Fixed-forwarding capability and provenance | 4 | Declare forwarding for No Op, Logger, Probe, Memory Snapshot, Merge Beacon, Repeat Counter (Counter and Sleep have hints). Output type follows the input; show a read-only forwarding summary, not an optional checkbox. Branch/Conditional/Merge need config-selected forwarding. |
| C5 | Save-time validation of numeric fields | 5 | `form_generator.py` turns unparseable numbers into `0.0`. One policy for malformed, out-of-range and non-finite values: inline error, keep the typed text, block save; same constraints in backend config validation. An existing test encodes the coercion and must be updated deliberately. |
| C6 | Random Number's ignored `value` field | 6 | Remove the control; keep any stored key through a migration. |
| C7 | Deep Branch continuation | 7 | `default` never runs after spawning; fix the contract or narrow the ports/description, and test that End actually executes. Parallel Branch semantics stay as they are. |
| C8 | Helper specs and generator | community gaps | Only 12 of 38 types have specs; six differ from their classes (Chat Completion, File Manager, File Reader, File Write, Start, Text Output). Reconcile before treating specs as safe regeneration sources. Generated starters read `inputs['input']` regardless of the declared source; generated tests check registration only. |
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

Legacy UI migration by family (shared Source control and typed Vault picker,
shared Payloads component, hiding empty sections such as No Op's Parameters
and End's Payloads) follows C1–C9. The owner's live-test findings in
`PROJECT_BACKLOG.md` (window nodes, missing pass-through, outdated Vault UI,
reveal autoscroll, error UI keys during runs) overlap C4 and the migration.

**Do not:** redesign Branch/Merge/Wait coordination, or put forwarding/Vault
checkboxes on nodes that do not implement those capabilities.

The audit's per-node table and probe files live outside the repository with
the audit report; copy the table here if a phase needs it.
