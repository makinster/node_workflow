# Approved planning snapshot — 2026-10-26

The owner approved decisions 1–12 and samples in the build request. The copied
planning text below is historical; its pending/no-build wording is superseded.
Build overrides: Debug group/section excluded by default, Include debug nodes
opt-in; Compact cap measured with 25% headroom; entry_kind/port shape reserves
later Bundle compatibility; repeated_shapes added to the delivery case. The
[built contract](../../integrations/META_NODES.md) owns the final behavior.

---

# Node map and coverage (step 2)

The requested slice has **2 useful operations, 0 existing nodes, 2 gaps (0%)**.
Both engines already exist as authoring APIs; that is implementation reuse,
not an existing workflow node. Request kind `new-integration`, node kind `meta`;
owner label **meta nodes**. No outside service is being integrated.

| Operation | Existing building block | Gap / proposed node |
|---|---|---|
| Supply bounded authorable contracts | `list_node_types`, `describe_node_type`, NodeFactory; no callable workflow node | Node catalogue; filters/cap/rendering; merge static metadata for sources/tables; mode-resolved output type |
| Check a drafted spec, pass parsed object or errors | `build_workflow(write=False)`, validator, NodeError; Check reply only checks reply fields | Check workflow spec; JSON input/caps; shared structured field diagnostics; no save path |

Reuse normal Source menus and compatible upstream/Vault key discovery. Spec
accepts only string keys (including secondary upstream string outputs). JSON
Catalogue / Checked spec / Check report use `[var]`; Context Pack serializes
records as JSON. A JSON catalogue may exceed the same character budget after
serialization: don't assume `[var]` bypasses caps.

## First composition-only meta-workflow (direction only)

Request → classify kind → Node catalogue → Context Pack → draft JSON spec →
Check workflow spec → owner approval → build.

Update (review round 1, Brief added): the catalogue step is two passes.
Node catalogue (Brief, All nodes, Text; ~6,200 characters) → Ask local model
shortlists node types → Node catalogue (Detailed, Filtered to those types) →
Context Pack → draft. Brief fits the 8,000-character model Context; the full
Compact/Detailed catalogue does not.

| Operation | Current mapping |
|---|---|
| Request | User Text Input in an attended run; save request to Vault |
| Kind | Pick one (has service setup) or Ask local model; non-composition/unsure stops for owner |
| Catalogue | **Gap 1**, this proposal; choose reviewed filters/budget |
| Context | Context Pack: catalogue Upstream, request/kind Vault, configured format instructions |
| Draft | Ask local model, JSON on; Question configured, Context upstream; no generation in this run |
| Check | **Gap 2**, this proposal; errors go to readable problems, then revise/stop |
| Owner approval | **Gap 3** for a durable, exact-spec-bound approval; prototype text prompt isn't that guarantee |
| Build | **Gap 4** for an in-app save operation that verifies that approval |

Current related coverage: **4/8 = 50%**. If these two nodes land: **6/8 = 75%**.
Approval/build remain gaps. Start/End and Vault transport are excluded from
this denominator. Composition-only describes the workflows being designed;
creating these meta nodes is still new-integration work.

Use sequential order where data depends on the preceding result. Independent
catalogue queries/context collection may later run in parallel, then explicitly
join before drafting; shared Vault presence alone is not a completion barrier.
Classify before spending on drafting. A kind result does not yet set catalogue
filters dynamically: configure a reviewed small query or use explicit kind
branches; AI-driven filter requests/iterative retrieval are later work.

## Manual bridge, then possible Build workflow

These two nodes can stop at a checked spec now. Owner reviews the exact spec
and warnings; an agent may manually run `aotn build approved.json` after
explicit approval. A check passes only against the current catalogue/library;
child references, files and save names can change before build. Recheck then.

A future in-app **Build workflow** node is needed for an all-in-AOTN save path,
unless a separately approved authoring tool provides it. It should consume
parsed spec + an approval receipt bound to that spec, never infer permission
from successful validation. Its output would be a saved-workflow receipt,
not execution. No shell-runner workaround, automatic retry, overwrite or launch.

See decisions 11–12. Phone approvals, shared server, research branches,
candidate designs and free-form in-app requests are direction, not approved work.
