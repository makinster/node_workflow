# Approved planning snapshot — 2026-10-26

The owner approved decisions 1–12 and samples in the build request. The copied
planning text below is historical; its pending/no-build wording is superseded.
Build overrides: Debug group/section excluded by default, Include debug nodes
opt-in; Compact cap measured with 25% headroom; entry_kind/port shape reserves
later Bundle compatibility; repeated_shapes added to the delivery case. The
[built contract](../../integrations/META_NODES.md) owns the final behavior.

---

# Owner decisions (step 3)

**Proposed answers; none approved.** Approve choices and the sample version
before step 5. This packet contains no product implementation.

1. **Scope and placement.** Two single-purpose nodes: `node_catalogue_node`
   and `check_workflow_spec_node`, Utility → Transform, direct-add, tags
   `meta` / `workflow`. “Meta” is the loop kind, not a new selector family.
   No Build workflow, approval transport, retries or auto-repair in this slice.

2. **Catalogue membership.** Use live authoring registry entries; exclude
   `HIDDEN_TYPES` and `editor_only` (currently tombstone). Keep Start/End:
   the visual add menu hides them, but authored specs need them. No planned
   or merely documented nodes. All current registered authorable debug types
   remain available; the catalogue is not the idea list in NODE_CATALOG.md.

3. **Catalogue fields.** Stable `schema_version: 1`; `type` is machine name,
   `display_name`, one-line description, family/group/tags, inputs/outputs with
   canonical types, accepted sources/routing, key config and declared errors.
   Compact keeps required/authoring-critical fields and marks other config
   as “ask for Detailed”; Detailed includes full field/item schemas, defaults,
   limits, conditionals, custom/unchecked keys and node-reference fields.
   Resolve ports with defaults; label that fact and expose mode controllers.

4. **Filters.** Default All nodes. Filtered exposes optional exact Group,
   exact Tag and plain Search. Filters combine AND; case-insensitive tag/search;
   all search words must match type/display name/description/tags. No regex.
   Empty group/tag means any. Unknown/zero-match query gives `catalogue_empty`.
   Static per-node config in v1; AI-chosen runtime filter objects are later work.

5. **Format and cap.** Text by default; JSON emits a record `[var]`, not
   serialized JSON text. Compact/Detailed is independent. Default cap 4,000
   characters, range 512–64,000, hard 256 KiB UTF-8 guard. Count the final
   text or compact JSON serialization including its envelope. **Overflow errors;
   no partial records, clipped JSON, silent omission or retry.** All-node queries
   can exceed the default: narrow filters or explicitly raise the budget.
   This deliberate tradeoff needs owner approval; alternative is explicit
   whole-record truncation with omission counts, which is less safe for drafting.

6. **Catalogue input/output.** An optional `Continue [any]` input, Upstream
   only, lets it sit in a chain; it is a sequencing input, not filter text.
   Output `Catalogue`: `[string]` for Text, `[var]` for JSON via the normal
   mode-resolved metadata hook. Standard downstream/Vault copy. No forwarding
   checkbox: the output is always the requested catalogue. Store the request
   in the Vault before this step if it must survive. No files/settings/Secrets
   values in catalogue output; registry defaults are static contract data.

7. **Spec input.** One required `Spec [string]`, exactly Upstream / Vault /
   Configured. Configured uses the shared long-text preview/editor. JSON text
   must contain one `aotn-workflow/1` object; no Markdown-fence extraction or
   automatic repairs. Start with max 32,000 characters (1–64,000), hard 256 KiB,
   128 nodes, 256 connections, nesting 64. Oversize refuses before graph checking.

8. **Valid and warning semantics.** Same error/warning verdict as `build
   --check`: any error blocks; existing warning-only reports pass. No new
   “warnings are errors” mode. Output the exact **parsed input spec** `[var]`,
   with original handles/config, not normalized graph/id maps. Optional Vault
   copy of that record. No forwarding checkbox that could return raw text.
   Optional secondary **Check report [var]**, Vault-only on a passing check,
   for warnings/counts;
   never include the whole spec in a report/error. A pass is not runtime proof.

9. **Invalid output.** Existing error path only, no default output or success
   Vault write. Codes: `invalid_json`, `spec_invalid`, `spec_too_large`, plus
   `invalid_config` and normal `node_error`; catalogue uses `catalogue_empty`,
   `catalogue_too_large`, `invalid_config`. Readable bounded problems carry
   node/field/message plus code/severity in `NodeError.details.problems`.
   Shared diagnostic field addition as described in Feasibility. Preserve null
   where no exact field applies. Cap at 100 problem rows / 8,000 characters,
   with omitted count. Redact diagnostics before run-error persistence; don't
   quote arbitrary spec/secret values or dump prompts.

10. **No library effects.** Reuse the check-only backend path; a temporary
    validation graph is allowed. No saving, build publication, node execution,
    active-map edits, id allocation in the library, or name reservations. Do not
    return ephemeral generated ids as a built workflow. Future build tests must
    make save/execute/network calls fail and compare the library before/after.

11. **First meta-workflow gap.** Manual first: inspect checked draft + warnings,
    owner approves the exact file, then manually `aotn build` that file (without
    `--check`). In-app automation later needs an approval-bound Build workflow
    path. Plain User Text Input + Conditional is only a prototype interaction,
    not a verified approval bound to a draft. No automated build in this slice.

12. **Later approval contract.** Proposal only: show name, node/config summary,
    warnings and full spec; Approve / Revise / Cancel, default Cancel. Bind
    approval to immutable spec hash, catalogue/schema version, run and target
    data root. Any change/stale approval requires fresh review. Build rechecks
    that exact spec and creates a new save, never overwrite/run/activate. Refusal
    or mismatch produces no write. Phone approval and in-app requests are later.
