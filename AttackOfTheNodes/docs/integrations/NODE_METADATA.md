# Node metadata record v1

Owner-approved design: `agent_channel/node-metadata-plan/` (PLAN, DECISIONS,
MIGRATION; all 15 recommendations accepted 2026-10-28, with debug nodes and
the tombstone getting a lighter record). Batch 1 shipped 2026-10-29: the
registry, catalogue schema 2 and reviewed records for the twelve Draft a
workflow v2 palette types. The other 47 registered types are pending review.

## What a record says

One record per node type, in [`backend/node_metadata.py`](../../backend/node_metadata.py)
(`NODE_METADATA`, keyed by the exact `node_type`). It is the only editable
copy. NodeFactory exports a deep copy as `node_metadata` on every metadata
row; `description` and `execution_contract` there are derived aliases of the
record's `purpose` and `execution_contract`. `node_execution_contracts.py`
is now a read-only compatibility projection. Node class descriptions and
`aotn_node_helper` spec descriptions must equal the purpose (tested).

| Field | Rule | Meaning |
|---|---|---|
| `schema_version` | exactly integer 1 | record version |
| `purpose` | 1–120 chars | one action and its result |
| `use_when` | 1–200 | the situation this node fits |
| `not_for` | 1–200 | the closest tempting wrong use |
| `side_effects` | `possible` list, `delegated` bool, optional `note` | possible effects over all modes |
| `needs` | `required` / `optional` lists, `unresolved` bool, optional `note` | prerequisites |
| `cost_class` | `no_usage_fee` / `metered` / `variable` / `unknown` (+`cost_note` for the last two) | usage fee category, not a price |
| `time_class` | `quick` / `seconds` / `slow` / `waits` / `variable` / `unknown` (+`time_note` for the last three) | typical execution class, not a deadline |
| `learnable_from` | optional, `example` / `recording` | omitted until reviewed support exists |
| `execution_contract` | `output_payload` (≤512), optional `notes` (≤512) | verified emitted values and rules |

Effect flags: `writes_files`, `sends_messages`, `spends_money`,
`runs_external_commands`, `changes_external_state`, `controls_windows`,
`sends_data`. Need codes: `network`, `browser`, `login`, `credentials`,
`model`, `local_files`, `user_input`, `external_program`,
`background_service`. Lists are unique and in that canonical order; notes are
required for delegated effects, optional needs and unresolved needs. Text is
single-line NFC with no surrounding space; a whole record is at most 4,096
UTF-8 bytes. Nothing is clipped: an invalid record fails the tests.

**Read-only is derived**, only from a reviewed empty `possible` list with
`delegated: false`. Missing data is never read-only. Common engine bookkeeping
(run history, the output log, timing, within-run Vault values) is excluded from
`writes_files`; explicit files, cross-run state and queues are included.

**Lighter records** (debug nodes and the tombstone, `LIGHT_RECORD_TYPES`):
`schema_version`, `purpose`, `side_effects`, `needs` only.

A record only describes code. It cannot add ports or change execution,
validation, defaults or errors, and it grants no approval: an empty effect
list or a matching purpose is never permission to run anything.

## Migration ledger and review manifest

`PENDING_REVIEW` lists registered types without a record. They expose
`node_metadata: null`, and catalogue Text marks them *Metadata pending
review: effects and needs not stated (not Read-only)*. Remove a type from the
ledger in the same change that adds its record. The ledger may only shrink: a
**new node type needs a reviewed record in the same change** (the
completeness test fails otherwise).

[`backend/node_metadata_review.json`](../../backend/node_metadata_review.json)
is the review manifest, never model Context. Per type: reviewed source/helper
paths with LF-normalized SHA-256, the mocked tests that support the claims,
the record's content digest, author, a different verifier, date and base
revision. `tests/test_node_metadata.py` fails when a listed file or the record
text changes. Then re-read the code, re-check the record and tests with a
second reviewer, and only then record new digests: updating a digest alone is
not a review. A helper change invalidates every record that lists it.

## Catalogue schema 2

Node catalogue output is now `schema_version: 2` with
`node_metadata_version: 1` and `metadata_projection`:

- **Brief** (`selection`): old fields kept (`description` is the purpose
  alias; names-only `inputs`/`outputs`), plus `node_metadata` = purpose,
  use_when, not_for, effect flags/delegated, required/optional needs/unresolved,
  cost and time classes. Notes, learnable_from and the wiring contract are
  omitted. Text keeps the `type|name|purpose|in -> out` line, then indented
  `Use when`, `Not for`, `Effects … Needs …` and `Cost … Time …` lines.
- **Compact / Detailed** (`full`): the full record under `node_metadata`, which
  carries `execution_contract` once (the separate top-level key is gone). Text
  adds the intent lines and `Effects note` / `Needs note` / `Cost note` /
  `Time note` before the existing ports, config, payload and Configured lines.

Search matches type, name, purpose, `use_when` and tags, never `not_for`.
`max_chars` may now be 512–200,000 (default still 64,000); the 256 KiB UTF-8
ceiling stays. `catalogue_too_large` reports characters, bytes, both limits and
which one `failed`. Strict JSON clients must accept schema 2; data readers can
keep using the retained fields.

## Writing a record

Write an action someone can point to in code and name the result. `use_when`
names the input/situation and wanted result; `not_for` names the closest wrong
choice and its limit. No marketing words, guarantees or instructions to the
model. Field names belong in `execution_contract`. List every effect any
supported mode can have, with a note naming the mode. Check every sentence
against `execute` and its helpers, add or cite mocked tests, and get an
independent verifier before the record lands.

## Shared standard config documentation (2026-10-29)

NodeFactory and authoring descriptions expose `standard_key_docs`, derived from
the node class defaults. Compact/Detailed catalogue records and Text include it.
For every type declaring `transient_output`, true passes output to the next
node and false sends no output on; the text states the type's actual default
(most are true; Notify and Record event default false). This generic description
lives outside the authored per-node record and does not mark pending types as
reviewed. Suppressing the payload does not stop traversal to the next node.

Start's record now consistently distinguishes passing the greeting as the next
node's input from showing text. End's re-reviewed record documents only the
configured completion message, with no echoed input. The manifest retains the
original metadata author and identifies this source recheck as the verifier;
no external human review is claimed for this change.

User Text Input's full record now documents the existing `membank_outputs`
answer-copy option and Concat's use of that saved value plus current input.
Its execute source was re-read and its content digest rechecked locally; set-2
engine tests cover the two-answer flow. No runtime behavior was added to that
node. The metadata manifest cites the supporting engine test.
