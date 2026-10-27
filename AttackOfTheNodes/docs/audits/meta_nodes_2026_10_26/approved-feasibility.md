# Approved planning snapshot — 2026-10-26

The owner approved decisions 1–12 and samples in the build request. The copied
planning text below is historical; its pending/no-build wording is superseded.
Build overrides: Debug group/section excluded by default, Include debug nodes
opt-in; Compact cap measured with 25% headroom; entry_kind/port shape reserves
later Bundle compatibility; repeated_shapes added to the delivery case. The
[built contract](../../integrations/META_NODES.md) owns the final behavior.

---

# Feasibility (step 1)

Conditional: the shared engines exist; the two workflow nodes do not.
Checked 2026-10-26 against `3f36552`. [Machine form](feasibility-check.json).

| Question | Evidence / implication |
|---|---|
| API? | Project-owned `backend/authoring.py`; CLI `aotn_author.py` calls it directly. Use backend functions, not a subprocess. |
| Sign-in? | None. Do not resolve Secrets values or call the nodes described. |
| Cost? | Local CPU/memory only. No generation/network/spending. |
| Reliability? | 56 registry types; 55 authorable, excluding tombstone. Defaults/config-resolved hooks already exist. New wrapper bounds and cancellation are unverified. |
| Terms? | No new outside service. Catalogue entries do not grant permission to run their integrations. |
| Verdict | Conditional on owner decisions/samples and later implementation checks. |

[Read-only probes](research-checks.json): `nodes`, seven `describe` calls,
and four `build --check` calls in an empty temporary data root. **No file or
directory appeared there**. No node executed; no workflow was saved.

- [Valid](check-valid.json): passes; generated ids are temporary check internals.
- [Invalid](check-invalid.json): unknown config key and unknown input port,
  plus unreachable warnings; no success payload.
- [Warning only](check-warning.json): passes with a missing-file warning.
- [Name boundary](check-name-boundary.json): `--check` accepts a name ending
  `[sub]` for a standard workflow; saving checks names later. A passing check
  does not guarantee that a later save or run succeeds.

## Reuse and gaps

`list_node_types` excludes authoring `HIDDEN_TYPES`; `describe_node_type`
resolves default/config-dependent ports, fields, errors and Vault effects.
Group/tags come from registry metadata. Detailed tables also need `item_schema`
and custom-key contracts from metadata: current `describe.fields` omits nested
row schemas. Dynamic ports/types must be labelled “with defaults”; details
must expose their controlling fields, not pretend to know a future workflow.

`describe` infers standard Source controls by `<port>_source`; custom controls
(Context Pack rows, Start contracts) need their declared metadata as well.
“No Source dropdown” is not evidence for invented Vault/Configured support.
Use the runtime/source-menu audit contract rules and preserve unknown `any`.

`build_workflow(write=False)` assembles an **ephemeral, isolated graph** to run
the validator. It does not save, execute or change the active editor. Keep that
same validation path (extract a shared check-only helper if useful); do not use
`write=True`, SaveManager, reload/save/name-availability checks, or a shell.
Validation may read configured path existence, referenced saved subworkflows
and Stash inputs, as the CLI does; it is not an offline execution/readiness test.

Current diagnostics have `level/code/node/message`, **no structured field**.
Proposal: add an optional `field` in the shared authoring diagnostics, populate
known config/connection/reference locations there, and preserve it in CLI/node
reports. Use null for graph-wide/unknown locations. Never parse English messages
or guess a field. This is future build scope, not implemented here.

## Budget is a real constraint

The 55 names/descriptions alone are **4,664 characters**, before ports/config/errors.
Context Pack permits at most 4,000 characters per item (default 2,000), default
6,000 total (max 8,000). Ask local model Context caps at 8,000; answers at 16,000.
Proposal: catalogue defaults to 4,000 characters, error on overflow; narrow a
query rather than silently omit contracts. Set a Context Pack catalogue item's
limit to 4,000 and reserve its remaining total budget for request/instructions.
Larger catalogue caps do not make downstream context limits larger.

Not verified: new-node runtime performance/cancellation, final full-catalogue
sizes, human approval, actual model-generated specs, live execution, device proof.
