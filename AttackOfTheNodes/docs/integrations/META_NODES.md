# Meta nodes: catalogue and spec check

Built from `origin/main` `3f36552`, owner-approved decisions 1–12 plus the
2026-10-26 overrides. Both direct-add nodes are **Utility → Transform**,
tagged `meta`, `workflow`. They use production metadata/forms. No new Options,
account, network request, generation, build or approval node is involved.
[Built screens and evidence](../audits/meta_nodes_2026_10_26/README.md).

## Node catalogue

`node_catalogue_node` reads the same current registry as `aotn nodes` and
`aotn describe`; it does not instantiate/execute the listed nodes. Hidden,
internal, editor-only and tombstone types stay out. Start and End stay in.
**Include debug nodes** defaults off: `group` or selector section `Debug`
is excluded. Legacy backend category alone does not exclude a visible node
in another group (for example Loop Helpers).

Optional **Continue [any]** is an upstream-only sequencing input. Its value
is ignored. There is no source dropdown, configured filter input or input
forwarding. Filters are node settings:

- **All nodes** ignores filter values.
- **Filtered** ANDs exact group, case-insensitive exact tag, and every
  case-insensitive search word in type/name/description/tags. Blank means any.
  No regex. No matches gives `catalogue_empty`.
- **Brief / Compact / Detailed** is separate from **Text / JSON**. Brief has
  type, display name, one-line description (the node's purpose) and
  input/output display names (plus port ids in Text), then the
  [node metadata](NODE_METADATA.md) selection facts: use when, not for,
  effects, needs, cost and time. No data types, sources, config or errors. Compact includes
  field names/types/ranges/options, config defaults and error codes. Fields with
  defaults may be omitted from specs; Compact retains `required` only for fields
  without defaults. Detailed adds full schemas,
  defaults, declared error descriptions, custom/unchecked keys, reference
  fields, Vault declarations and UI hints. Dynamic ports are resolved with
  defaults, explicitly labelled `ports_basis: "defaults"`; config can change
  those ports. Compact is discovery context, not a complete validator schema.

Compact and Detailed expose the full [node metadata record](NODE_METADATA.md)
(catalogue schema 2) under `node_metadata`; for the twelve designer target
types it includes `execution_contract`: `output_payload` describes the emitted
value and `notes` records extra execution rules. The one authored registry is
[`node_metadata.py`](../../backend/node_metadata.py), verified against the node
execute methods; `node_execution_contracts.py` is a derived projection. Both the drafter and meaning judge
receive these same entries. Configurable inputs get a generated
`configured_inputs` line: when their source is Configured, the configured field
provides the data and the incoming wire is a trigger only; its value is ignored
and is not checked against that input's data type. This does not waive checks
on the configured value itself.

File Write emits a file-reference object with `type`, `ref_key` and `path`;
`path` is the actual absolute saved path, usable as `{input[path]}`. Create
unique first uses the requested path if absent, then adds ` (1)`, ` (2)`, etc.
before the last extension on collisions. It preserves existing files but is
not an atomic reservation. Conditional `equals` compares stringified operands
with case and whitespace intact. These describe existing execution; no runtime
or fixture behavior changed.

Text Output logs and emits bare formatted text when its label is empty or
whitespace-only. A nonblank label adds `[label] ` verbatim, including any
surrounding spaces in that label. Log, default payload and legacy Vault writes
all receive the same string. Set labels are display framing; writing their
payload saves the label too. For exact bare text use an empty label.
End's `record_line` completion log is normal run framing, not an unrequested
effect or additional requested output.

Compact Text config now uses `field:type=JSON-default`, with any remaining
constraints in JSON after the value; no `=` means no default. For example,
`message:string="Branch completed"`. Every field/default/constraint remains;
JSON `config_fields` retains its structured form. This shorter notation pays
for the payload/Configured lines within existing context caps.

**Catalogue** is a string in Text mode or a JSON record `[var]` in JSON mode,
published downstream and/or to the standard optional Vault output. JSON has
`schema_version: 2` (since node metadata record v1, 2026-10-29),
`node_metadata_version: 1`, `metadata_projection` (`selection` for Brief,
`full` otherwise), `complete`, `detail`, `include_debug`, `matched_count`,
`ports_basis` and `entries`. Each entry has `entry_kind: "node"`, `type`,
`display_name`, one-line `description`, `family`, `group`, `tags`, `inputs`,
`outputs`, `config_fields`, `errors`, `node_metadata` (null while a type is
pending review: effects unknown, not Read-only), plus detailed fields where
requested. Search also matches a record's `use_when`, never its `not_for`.

Inputs/outputs are arrays of `{id, name, data_type, required, ...}`; inputs
carry `sources` (and source/configured-field identifiers where declared),
outputs carry `to`. The common shape and `entry_kind` reserve a future
`"bundle"` record whose ports could come from Start rows / Return results.
**No Bundle discovery, serialization or execution is implemented.** Saved
workflows are not scanned or presented as catalogue entries.

Text ports separate machine ids from quoted labels: `default ("Greeting")
[string] ...`. Brief uses the shorter `default "Greeting"`; its tight table
separators keep ids and names inside the existing designer budget. Every Text
level says **Connections use port ids only; quoted names are labels.** Labels
are JSON-quoted, including embedded slashes, quotes and newlines. A connection
uses `start.default`, never `start.default/Greeting`. JSON fields are unchanged:
Brief retains names-only arrays; Compact/Detailed retain separate `id` / `name`.

Remeasured after the Text-port fix, base `232d112`: **50 non-debug entries;
Compact Text 35,386 characters / 35,437 UTF-8 bytes; compact JSON 49,874
characters/bytes**. At that measurement the default was **62,400**, about 25% above the larger
form. Original build measurement is retained in the
[historical measurement](../audits/meta_nodes_2026_10_26/catalogue-size.json).
Current fixed-palette and Brief counts are in the
[designer case](../delivery_tests/draft-a-workflow.json).
The cap counts Text as returned or compact JSON, not pretty-printed JSON.
Both forms also have a hard 256 KiB UTF-8 cap. Overflow gives
`catalogue_too_large`, with measured count/limit, and publishes nothing.
Nothing is partially returned or silently dropped. Detailed/all-debug output
can overflow; narrow filters. Context Pack and Ask local model have their own
limits: the full catalogue fitting this node does not make it fit downstream.
Use a filtered catalogue for a small request.

Current registry with node metadata batch 1 (12 reviewed records, 2026-10-29):
**51 non-debug entries**, Compact Text **52,321** characters (previously
**49,204**), within the unchanged **64,000** default; compact JSON **75,164**
(previously **71,830**) now needs an explicit larger cap. The configurable
maximum is **200,000**; the 256 KiB byte ceiling is unchanged. Brief Text
**15,037** / compact JSON **18,214** (previously **15,051** / **18,217**). V2's
contracts are **18,091** (previously **17,736**) within its 50,000 budget. The
original designer is deprecated: its 8,500 Context no longer fits its palette
(**12,194** now, without its unmatched Branch query) and its Branch query no longer matches.

Text Output with an empty or whitespace-only label logs and emits bare text.
Start without nonempty rows emits the greeting string verbatim; configured rows
replace it. Conditional emits the original left value on its selected true/false
port, not a comparison boolean. The contracts describe the routing exceptions.

**Two-pass planning.** Brief **all non-debug** Text is **15,037 characters**
with node metadata batch 1 (previously 7,634): purpose-first selection facts no
longer fit the default 8,000-character Ask local model Context; raise that cap
or filter. Pass Text to a model.
1. Shortlist: Brief, All nodes, Text → Context of the planning question.
2. Detail: Detailed (or Compact), Filtered by the shortlisted types/search →
   Context of the drafting question. Only the chosen nodes' config reaches it.

## Check workflow spec

`check_workflow_spec_node` takes required **Spec [string]**, exactly from
**Upstream / Vault / Configured**. The configured value uses the shared
long-text preview/editor. Compatible upstream writes (including secondary
Vault outputs) use the existing typed key picker. A parsed record is not text;
serialize it explicitly before this input.

One `aotn-workflow/1` JSON object is parsed, then sent to the shared
`backend.authoring.check_workflow_spec`. `aotn build --check` and saving builds
use the same `_checked_graph` path. No JSON fence extraction, repairs, node
execution or extra semantic validator. Warning-only checks pass, with warnings
in the optional report. Save-only naming/collision checks remain save-only,
just as with CLI `build --check`. The node permits an ephemeral validation map;
it does not edit the active editor map, reserve a name or publish a workflow.
Existing preflight may read referenced files/contracts/Stash like the CLI.

**Checked spec [var]** equals the original parsed input, preserving handles,
config values and references. It is not a normalized saved graph or generated
IDs. Publish downstream and/or to a standard optional Vault key. No forwarding.
**Check report [var]** is a separate optional Vault-only output, on success:
schema version, verdict, node/connection/warning counts, bounded `problems`
and `omitted_count`. It contains no spec body. Enabled Vault keys must be
nonblank and distinct. Failure leaves both outputs untouched.

Invalid JSON, including any repeated object key at any depth, →
`invalid_json`; a repeated key is listed with its path (for example
`nodes.end` or `nodes.say.config.template`) and code `duplicate_key`, since
a parser would otherwise keep only the last value; failed shared check → `spec_invalid` on the
normal error port; overflow → `spec_too_large`; bad settings → `invalid_config`.
The problem list has `node`, `field`, `code`, `severity`, `message`; unknown
locations remain null. Authoring diagnostics now carry structured locations.
Safe guidance replaces value-quoting CLI messages before error persistence;
locations use the existing secret redactor before capping. No raw spec is
copied into errors. Separately, for every node, the engine redacts a failed
node's persisted inputs (`context.inputs` in `run_errors/<run>.json`) with the
same redactor (known Secrets values plus labelled credentials) and trims each
input to 2,000 characters with a `[trimmed: …]` note. Structured inputs use
that same shared credential-key rule recursively: inspect the original key,
replace its entire sensitive value (including containers), then mask keys and
ordinary text. Harmless structure survives; live input objects are unchanged. At most 100 rows / 8,000 serialized message+details
characters, with explicit omissions. Graph-level issues can lack a field.

Default spec cap 32,000 characters, configurable 1–64,000; hard 256 KiB,
128 nodes, 256 connections and nesting 64. Invalid Unicode and non-finite
JSON numbers are rejected. These bounded transport/parser limits precede the
shared semantic check. Cancellation points precede publication; no await
separates validated in-memory outputs from completion. There are no retries.

## Tests and later composition

[Behavior/isolation tests](../../tests/test_meta_nodes.py) forbid save/build,
node construction/execution, subprocess and network calls, and compare a
seeded temporary library's bytes/mtimes before/after. They check valid,
warning-only and invalid reports, source routes, cancellation, caps and CLI
parity. The registry-wide [source audit test](../../tests/test_source_menu_audit.py)
now covers all 58 types, the new input controls and every compatible writer,
including Check report. The dated #124 baseline is retained; a separate
[extension](../audits/meta_nodes_2026_10_26/source_contracts.json) records the
new execute contracts and hashes.

Related first-designer coverage is **6/8** on this candidate: capture request,
classify kind, catalogue, pack context, draft JSON, check spec. Exact-spec-bound
owner approval and approval-bound saving remain two gaps. The illustrated map
stops after a passing check for manual review/build. A later Build workflow
node would need a displayed exact draft/hash, run/version binding, a default
refusal/cancel path and an approval receipt invalidated by any edit. This is
proposal only; a successful check grants no execution or save permission.

A [checkable two-node example](../audits/meta_nodes_2026_10_26/nodes-example.json)
and its [CLI check report](../audits/meta_nodes_2026_10_26/check-built-nodes.json)
show both nodes with a configured draft. It performs no generation and is not
saved to the workflow library.

The helper specs remain authoring inputs; runtime bodies are intentional custom
implementations. Continue uses legacy explicit port metadata because the helper
currently requires two choices for a generated source selector. Regeneration
must preserve its explicit upstream-only type/required/source metadata.

Shared `standard_key_docs` now explains transient_output in Compact/Detailed
entries for each declaring type, including the actual default. false suppresses
the payload; it does not stop traversal. Start passes its greeting as input to
the next node and itself shows nothing. End record_line logs only `[END] <message>`
and no longer echoes input. Return End's workflow results still read the input.

### Opt-in rejection of unreachable nodes

Check workflow spec now accepts `fail_on_unreachable` (boolean, default false).
With it enabled, any `unreachable` diagnostic fails the check as `spec_invalid`;
its original warning severity, code, location and sanitized text remain in the
error details. There is no success/report publication. Other warnings and the
default checker behavior are unchanged. V2 enables the option on both checks,
so a disconnected node gets the same single redraft as a structural error.
The retry prompt includes the exact structured check warning.

Latest sizes after the option and User Text Input's existing Vault-copy behavior
were documented: Brief Text **15,037** / JSON **18,214** (unchanged), Compact Text
**52,535** (previously **52,321**) / JSON **75,407** (previously **75,164**).
The complete v2 contract bundle is **18,271 / 50,000**. Query and context caps
are unchanged. Full Compact JSON still needs an explicit larger cap as before.

### Shared arrivals and saved-path display

Full catalogue Text and JSON now include a generic `input_routing` note. Several
incoming wires to one ordinary input are allowed: each arriving path runs it
separately with that path's payload. A shared normal End finishes each arrival;
it is complete, not an unreachable node or a join barrier. Return End still has
its separate single-publication rule. Engine tests verify both shared ordinary
inputs and direct parallel arrivals at a shared End.

After File Write, Text Output `{input}` displays the whole file record
`{type, ref_key, path}`. That does not satisfy a saved-path display request;
use `{input[path]}`. Both node records and the judge checklist say this directly.

Latest counts: Brief Text/JSON unchanged **15,037 / 18,214**; Compact Text
**53,280** (previously **52,535**), JSON **76,170** (previously **75,407**).
Complete v2 contracts **21,146** (previously **18,271**), within 50,000.
Caps/headroom are unchanged; full Compact JSON still needs a larger explicit cap.

## Concat and disabled-output follow-up — 2026-10-29

Concat now performs standard Vault result writes, optional transient output and
unchanged-input forwarding. Missing format names error. Shared preflight warns
for unsupported standard Vault writes, unknown earlier Concat template writers,
and connected default outputs with disabled payload publication. These are
warnings for ordinary uses. `fail_on_disabled_output=false` is the new default
Check option; v2 sets it true on both checks so the first failure triggers its
one structural redraft. The trial's calibration check uses the same setting.
A second defect stops before judge/save. No calibration fixture changes.

Latest Text counts: Brief **14,569**, Compact **53,217**; JSON **18,214 / 76,638**.
V2 bundle **21,513 / 50,000**. Repeated pending-metadata wording is shorter but
retains unknown effects/needs and not-Read-only facts; caps/headroom unchanged.
See the [audit](../audits/concat_vault_2026_10_29/README.md) for capability and
static-analysis limits. No live reviewer calibration was run.

## Exact identities and v2 selection (2026-10-29)

Use Node catalogue `scope=Exact IDs` with `type_ids_source` set to Configured,
Upstream payload or Vault. Configured takes a `type_ids` list; Vault takes
`type_ids_vault_key`. Lists contain 1–64 exact, unique, visible admitted IDs;
unknown, duplicate, hidden or unadmitted IDs are errors. Output includes every
selected contract in stable ID order, or a size error; no truncation or
substring matching. All nodes/Filtered retain their existing trigger behavior.
Brief Text now groups entries under family headings; Brief JSON is unchanged.

The optional `Selected analysis` mode is the existing v2 adapter: separate
candidate/role evidence from requirements analysis, reviewed support closure,
one local discovery expansion and a frozen Compact snapshot. Both v2 structural
checks enforce the snapshot's type set. No extra ordinary inference call or
new target-node admission. [Audit, source attestations, recall and budgets](../audits/palette_selection_2026_10_29/README.md)
record the mock-only evidence and deliberate omission test.
