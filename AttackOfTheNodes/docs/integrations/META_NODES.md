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
  type, display name, one-line description and input/output display names
  (plus port ids in Text): no data types, sources, config or errors. Compact includes
  field names/types/ranges/options, config defaults and error codes. Fields with
  defaults may be omitted from specs; Compact retains `required` only for fields
  without defaults. Detailed adds full schemas,
  defaults, declared error descriptions, custom/unchecked keys, reference
  fields, Vault declarations and UI hints. Dynamic ports are resolved with
  defaults, explicitly labelled `ports_basis: "defaults"`; config can change
  those ports. Compact is discovery context, not a complete validator schema.

**Catalogue** is a string in Text mode or a JSON record `[var]` in JSON mode,
published downstream and/or to the standard optional Vault output. JSON has
`schema_version: 1`, `complete`, `detail`, `include_debug`, `matched_count`,
`ports_basis` and `entries`. Each entry has `entry_kind: "node"`, `type`,
`display_name`, one-line `description`, `family`, `group`, `tags`, `inputs`,
`outputs`, `config_fields`, `errors`, plus detailed fields where requested.

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

Current registry with config defaults: **51 non-debug entries**, Compact Text
**41,400** characters (before: **36,848**) and compact JSON **56,360** (before:
**51,792**). The default stays **64,000**, the existing upper bound. Brief Text
stays **7,634** / compact JSON **10,603**. The designer
Brief catalogue cap rises from 7,500 to **8,000** so registry growth does not
stop its first pass; Context remains 8,000 (366 characters headroom). The
fixed nine-type palette is **7,943** (before: **7,421**), below Context 8,000.
Repeated headers are shorter so all config defaults fit without raising caps.

**Two-pass planning.** Measured Brief **all non-debug** Text: **50 entries,
7,447 characters** after the Context-limit description update: 553 below the
default 8,000-character Ask local model Context cap (now configurable). Compact
JSON is 10,371, so pass Text to a model.
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
