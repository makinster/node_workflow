# Editor deletion review proposal

**2026-10-18 — phase 1, for owner review. No implementation in this PR.**
The grouped-delete direction is approved; the case-specific choices below are
proposals. Phase 2 starts only after this review is approved **and #82 merges**,
from fresh `origin/main`. [Current State](CURRENT_STATE.md) owns delivery status.

## Basis and ownership

This proposal branch starts at main **90182f0**. “Current” below means the
pending **#82 head 531e4c1**, not a claim that its hotfixes have merged.
Re-inventory after #82 merges, including any changes since that head.

Read first:

- [Approved backlog direction on #82](https://github.com/makinster/node_workflow/blob/531e4c1c14ec2682a30a67a3cdf75b05aa984fc8/AttackOfTheNodes/docs/PROJECT_BACKLOG.md#owner-live-test-findings--2026-10-18-editor-deletion-and-branch-count).
- [Handler deletion follow-up](https://github.com/makinster/node_workflow/pull/82#issuecomment-6257579035),
  [restore/fan-out follow-up](https://github.com/makinster/node_workflow/pull/82#issuecomment-6257821191),
  [stub-removal follow-up](https://github.com/makinster/node_workflow/pull/82#issuecomment-6258154533),
  and the later [three-review-fixes follow-up](https://github.com/makinster/node_workflow/pull/82#issuecomment-6259457638).
- Checked source at that head:
  [Editor](https://github.com/makinster/node_workflow/blob/531e4c1c14ec2682a30a67a3cdf75b05aa984fc8/AttackOfTheNodes/frontend/screens/editor.py),
  [adapter](https://github.com/makinster/node_workflow/blob/531e4c1c14ec2682a30a67a3cdf75b05aa984fc8/AttackOfTheNodes/frontend/editor_workflow_adapter.py),
  [reachability helpers](https://github.com/makinster/node_workflow/blob/531e4c1c14ec2682a30a67a3cdf75b05aa984fc8/AttackOfTheNodes/frontend/error_mux_ui.py),
  [keep picker](https://github.com/makinster/node_workflow/blob/531e4c1c14ec2682a30a67a3cdf75b05aa984fc8/AttackOfTheNodes/frontend/screens/branch_keep_selector_screen.py).

Implementation ownership: `frontend/screens/editor.py`,
`frontend/editor_workflow_adapter.py`, `frontend/error_mux_ui.py`, and the shared
keep picker or a new picker screen. Required registry entries and tests follow
[Contributing](CONTRIBUTING.md#adding-a-registered-command); no raw key dispatcher.
Do not edit Node Config, Workflow Library, Help or App during the parallel 4a-2
work. Coordinate any needed interface change rather than reaching into new
Start/End controls. This proposal changes no frontend or backend code. It is a temporary review
document: after delivery, extract durable rules to the boundary/UI references
and archive it. When integrating the open docs C PR (#83), register this name
alongside the temporary subworkflows proposal in its active-doc allowlist;
it is not an eighteenth permanent core reference.

Source checks for this review: the 20 current hotfix tests plus three
independent review reproductions pass on 531e4c1 (**23 passed in 3.51s**).
The saved/unsaved Beacon probe still produces the different outcomes below.
A subsequent re-review passed **92 focused tests in 5.47s**, including the
three independent reproductions, the new hotfix tests and nearby restore/error
routing tests. Additional cases cover another guard being soft-deleted or saved
as a tombstone, restoring that guard before deletion, a tail shared by a
Resolver route and the node's own wired error path, and that tail also being
reachable from No error. Both halves of a removed original or newly gained
input were also checked without relying on Editor's prior edge pruning. No
remaining finding in those cases. The full suite on that same #82 head passed
**1728 tests in 212.11s**.
This docs branch's main suite passed **1708 tests in 217.06s**; no application
change is shipped by the proposal.

## Decisions to review

| Question | Recommended default | Detail |
|---|---|---|
| Q1: Merge's other Beacons | Preserve them as visible repair work | [Merge](#merge) |
| Q2: Beacon removal | End its branch and remove its Merge selection | [Merge Beacon](#merge-beacon) |
| Q3: group undo after conflicting edits | Refuse the whole restore, list conflicts | [Undo](#undo-before-save-after-save-after-reload) |
| Q4: reduction recovery while Branch stays live | One saved, non-executable recovery row | [Count reduction](#branch-count-reduction-and-the-shared-picker) |
| Q5: strict validation | Preserve existing severities; do not hide leftovers | [Validation](#group-record-reachability-and-validation) |

The required exact-count picker, keeping No error and grouped undo are already
approved. These questions concern gaps in case semantics, not a new approval
request for that direction. Moving the Branch picker to first delete is a
recommended interaction change included in these samples.

## The agreed model

1. **Delete is reversible as a group.** Delete a branch-owning node together
   with nodes reached only by its dropped paths. Keep one visible stub;
   one undo restores the owner, its removed members, wiring and related config.
2. **One required keep picker.** Branch/Conditional deletion asks for one path
   to keep: their owner is going away, so there is one continuation to bridge.
   Reducing a Branch from M paths to N requires exactly N selections from the
   original M. Error Resolver always keeps **No error**, with no picker.
3. **Save keeps one recovery stub.** The stub stores the group's removed node
   records. They are not loose executable nodes or independent tombstones.
   Removing that stub commits removal of the whole group. Until later session
   history exists, this final removal has no undo.
4. **Later, global session undo.** Multi-step Ctrl+Z records complete editor
   actions in memory and is cleared when the app closes. Group actions should
   already have the before/after records that history will need.

An **owner** here is a graph node whose removal drops routes, not merely a node
adjacent to another. A shared Resolver belongs to the surviving graph too; it
must not be removed just because one guarded node is deleted.

## Current and proposed behavior, case by case

### Ordinary node, Start and End

**Current:** first X/Backspace records an in-memory deleted overlay; the node
and its connections remain. A second delete removes the stub. In #82 the gap
bridges to only the first used non-error output target. Start deletion is
blocked. End has no normal continuation. Output-family nodes can continue;
they are not automatic pruning boundaries. Save/Validate materialize overlays
as `tombstone_node` records and drop their outgoing live edges.

**Proposed:** retain the simple two-step interaction for an ordinary node with
no owned paths. Use the same group record with one member so undo is consistent.
Keep the one-continuation rule; Start remains protected. End/Return End removal
must preserve the existing contract diagnostics, not silently invent a new
result endpoint. No new confirmation for an ordinary unshared, single-path
node. Group members contain data, not copied file contents or run resources.

**Owner choice:** none needed for the ordinary case; structural cases below
supply the exceptions. Return End's UI belongs to 4a-2, not this proposal.

### Parallel Branch

**Current:** first delete only marks the Branch; it does not remove descendants.
Second delete opens the existing **single-choice** keep picker when original
output connections exist. `prune_branch_tombstone` permanently removes the
other paths and the owner, reconnects its parents to the selected head, protects
nodes reached by surviving routes, and handles Merge orphan cleanup. This
pruning cannot be undone as a group. An empty/unwired Branch has no such picker.

**Proposed:** show the shared picker on the **first** delete, before mutation.
Require exactly one normal path. After Apply, one group stub represents the
Branch and all exclusively dropped members; its kept continuation is explicit.
A second delete removes this already-planned stub, without asking which path
again. Even empty slots have readable rows; selecting an empty kept path ends
that continuation rather than choosing another path silently. Cancel does
nothing. Deleting all paths is not an extra option in this phase.

**Owner choice:** first-delete placement is recommended so the first action
already has a complete, reversible group. It replaces today's late picker.

### Conditional

**Current:** first delete marks the Conditional. Second delete has no picker;
`stub_removal_plan` bridges the first declared used normal path, usually True,
and leaves the other path's nodes loose. It does not create a group undo.

**Proposed:** the same required picker as Branch, selecting exactly one of
True/False, including an empty path. Remove the Conditional and exclusively
reached nodes on the unpicked path as one group. Do not silently choose True.
Shared descendants stay. Any owned recovery paths are included in the same
plan and preview; they are not additional keep choices.

**Owner choice:** no new choice beyond explicitly picking the kept path.

### Error Resolver itself

**Current:** deleting the Resolver first only marks it. On stub removal, #82
keeps its No error target and computes error-only nodes with
`nodes_only_reached_from`; it asks before permanently deleting those nodes.
Cancel keeps the stub and branches. Before that second action, undo only
restores the Resolver. A node the No error path also reaches is protected.

**Proposed:** no picker. Confirm the owner plus the complete recovery group
on first delete, preserve No error, and create one undoable group stub. Gather
**all** dropped recovery heads together: two removed routes sharing a tail
still own that tail. Preserve other live users of shared descendants. An empty
No error route stays empty; never bridge into a recovery route as fallback.
If the selected Resolver has several guarded parents, the confirmation names
that consequence and the plan reconnects each valid parent to the kept head.

**Owner choice:** none on keeping No error; that is approved.

### A node with an error handler

**Current:** #82 confirms, deletes its inline Resolver and error-only nodes
immediately, preserves No error as the node's continuation, then marks only the
selected node. Undo cannot recover the handler or recovery nodes. A direct
wired `error` path is included. In 531e4c1, all dropped error heads are walked
together and a Resolver with another live guarded parent is preserved. The
three earlier shared-handler/shared-tail/retained-edge review gaps are fixed
at this head; they remain regression requirements, not current defects.
Only another **live** guard preserves the shared Resolver. A soft-deleted or
saved deleted guard does not count as live, and restoring it before the next
delete makes it count again; those nearby cases were independently checked.

**Proposed:** collect the selected node, its **exclusive** handler(s), and the
union of exclusively dropped recovery descendants as one group. Include direct
error wiring and handlers on relevant outputs, not just the first mux found.
Use a single preview and undo. Preserve a Resolver still used by another live
guard; detach only the deleted node's edge. Preserve normal continuation and
unrelated parents. The selected root itself is deleted even when it is shared;
protection applies to collateral members, not a silent refusal to delete it.

**Owner choice:** none on protecting shared live handlers. The confirmation
must say when a handler is kept because another node uses it.

### Merge

**Current:** first delete marks Merge. Permanent removal selects the first
non-Beacon incoming connection as its home path and its default downstream
connection (falling back to the first downstream). It bridges only if the
ports still exist and both ends are free. Other Beacon inputs disconnect;
their nodes remain and validation warns that they no longer join a Merge.
There is no prompt or grouped undo for those effects.

**Proposed:** preview the home continuation and affected Beacon links before
first delete. If the home path is ambiguous, do not select one by list order;
stop for repair/explicit selection. Store every changed edge and Merge-related
config in the undo group. Never reconnect all Beacon parents to the home path.
No hidden deletion of another live branch is permitted.

**Q1 — genuine choice:** keep those other Beacons as explicit repair work
(recommended, least destructive and closest to current behavior), or remove
Beacons that point **only** to this Merge as group members and end their
branches at the preceding node? The latter changes more than the selected
Merge. Shared Beacons/branches must survive either choice. Validation must
continue to explain any remaining unjoined branches.

### Merge Beacon

**Current:** first delete marks it, retaining Merge selections and wiring.
Second delete **before save** prunes its Merge closure/carry-forward selections
and disconnects its Merge outputs. It does not bridge the preceding node into
Merge. After materialization, its type is `tombstone_node`, so that special
editor path is missed: generic stub removal can bridge the parent into Merge
and leave those selections intact. This save-dependent difference was
reproduced on #82 with the same graph in both cases.

**Proposed:** one policy before and after save. Capture the Beacon and every
affected closure/carry-forward/selected-input field and connection as a group.
Undo restores those changes together. Do not delete Merge or its other parents
simply because one Beacon disappears.

**Q2 — genuine choice:** end the deleted Beacon's branch at its preceding node
and remove its Merge selection (recommended, matches today's unsaved removal),
or bypass the Beacon and feed Merge directly? The second changes home-input
inference and needs explicit semantics; it must not happen merely because Save
was pressed. If no valid Merge data source remains, show existing diagnostics
rather than silently choosing another branch's payload.

### Two parents, convergence, nested branches and loops

**Current:** soft deletion retains both parents; generic permanent stub
removal reconnects each recorded incoming edge to its one kept target, without
a shared-parent confirmation. Insertion now preserves the cut target input
even with a second parent. Tombstone restore in #82 allows an ordinary input to be shared unless
it appears a new node took the deleted node's place; Merge slots remain single
source. Pruning protects surviving reachability. The 531e4c1 handler fix now protects
a shared live Resolver and removes a tail reached only through dropped recovery
routes. Those fixes do not yet provide grouped undo or the requested picker.

**Proposed:** show a confirmation when the selected root has multiple parents.
All its incoming edges are in the group. Reconnect eligible ordinary upstream
outputs to the single kept head; preserve fan-in and Merge-slot rules. A parent
output already reassigned elsewhere is a conflict, never a second target.
Protect any collateral node with a surviving outside route; walk dropped heads
as a union, including nested branches. Use visited sets for loops. Start is
always protected. Beacons and explicit terminal types stop traversal; output
nodes do not. At Merge boundaries retain the existing surviving-input/orphan
analysis from `prune_branch_tombstone`; the simpler helper alone is insufficient.

A shared node reached by both a kept path and a dropped path stays, with only
the dropped edges removed. A shared node reached by **two dropped** paths can
be removed. Cleanup of Merge config belongs to the same group, not a later
side effect outside undo.

**Owner choice:** none on protecting collateral live users. For a selected
shared Merge/Resolver, use the applicable structural confirmation as well.

### Removing or replacing a stub

**Current:** X on an existing stub is generally final. #82 uses
`stub_removal_plan` to bridge one path; Resolver error descendants can still be
live until this step. Branch has its separate irreversible keep-one picker.
Soft stubs and materialized stubs can differ, notably for Beacon. Opening a
stub also allows replacement; choosing the original type can restore it.

**Proposed:** a group stub already contains removed members; final Remove
only discards that recovery record and bridges its one planned kept route.
It does not traverse the current graph again and discover extra nodes to delete.
Confirm permanence, group size and kept route. Any graph drift must be checked
before bridging. Replace-with-original restores the **whole** group. A different
replacement is explicit finalization plus a normal insertion, with a warning
that stored members will not return; never silently discard them through the
old single-node replacement path. Legacy stubs keep compatibility adapters,
not an assumption that every saved tombstone already contains a group.

**Owner choice:** no change to the approved final-removal distinction. Future
session history can make final Remove reversible; it does not do so today.

### Undo before save, after save, after reload

**Current:** **Z**, not Ctrl+Z, restores only the selected stub; there is no
editor history stack. Before materialization, undo clears its overlay. After
save/reload, `restore_tombstone` restores identity/config and attempts validated
wiring, reporting partial repair. #82 keeps current incoming wiring to avoid
restoring a second target. At 531e4c1 it also drops both halves of retained
inputs whose source port disappeared, reporting `source_port_missing`. The
previous failure on a three-to-two Branch reduction is fixed. Permanent stub
removal has no undo.

**Proposed:** Z on a group stub restores the complete owner/member/config/edge
operation once, before or after Save and after reload. Revalidate **retained
and original** wiring: valid current rewiring may survive; invalid ports may
not. Never overwrite a replacement node or a surviving parent's newer edge.
Mark the workflow dirty; undo is not an automatic disk save or rollback of a run.
A compatible Resolver inserted before the stub is not by itself a conflict:
retain that valid current input instead of re-adding the old parent's second
target. Validation can materialize a stub before a disk save, so the rule
depends on its representation, not just on whether Save was pressed.

**Q3 — genuine choice:** for conflicts after subsequent graph edits, use
all-or-nothing group restore with a clear conflict list (recommended), or allow
an explicitly confirmed partial group restore? Current single-node partial
restore should remain available for legacy records; “Undo restored” must not
hide a partially missing new group.

## Branch-count reduction and the shared picker

Current `_apply_node_config_result` applies the new config and prunes removed
output edges. Descendants of the removed high-numbered ports can remain loose;
there is no required keep-N decision. Existing Error Mux route deletion marks
`delete_branch_nodes` as separate placeholders before pruning, not one group.

Proposed editor flow:

1. Capture the old graph/config/alias before applying a returned config. Compare
   old M and requested N using the node's resolved ports. On a reduction, retain
   the result as a draft; do not prune or commit its lower count first.
2. From `editor.py`'s `_node_config_closed` / `_apply_node_config_result`, open
   the shared picker over **all old M paths**. Require exactly N picks. Increasing
   a count, an unchanged count, and non-Branch saves take the ordinary route.
3. Keep selected paths in their old relative order and map them to the new
   contiguous slots. Copy names and `branch_payload_sources`; rewrite both
   sides of edges, Merge branch-key references and affected editor selections.
   Keeping old path D must not quietly send old path B's payload or lose D.
4. Compute removed members and Merge cleanup using the same group planner as
   deletion. On Apply, commit the pending alias/config and topology as one
   user action. Cancel leaves the live graph unchanged. Delay any jump or
   catch-errors continuation until this decision completes.
5. Recheck the plan if the graph changed while a modal was open. Require a new
   preview if the affected set/kept destinations changed. Do not apply stale
   confirmation to a larger group.

**Q4 — where a reduction's recovery stub lives:** the Branch remains live,
so it cannot itself become a tombstone. Both options retain one saved group and
one restore action; neither quietly discards persistent group undo:

- **Recommended:** store versioned recovery data on the still-live Branch and
  show one collapsed “Deleted 2 branches” recovery row under it in the editor.
  This is an archive record, not an executable node or an extra output port.
  Z on that row restores the old count/mapping and members; X removes the
  stored group. The new reduced graph remains runnable. No loose live member
  is exempted from validation. Existing unknown-config preservation must be
  tested through Node Config, save/reload and import/export; do not assume it.
- **Alternative:** insert one actual blocking tombstone before the surviving
  Branch. Restoring it restores that Branch's old config and members, without
  creating a second Branch; removing it bridges to the live Branch. This matches
  the existing deleted-owner stub model, but running requires an extra Remove
  action after an otherwise ordinary config save.

The approved deleted-owner stub does not settle representation for an owner
that remains live. Settle this UX/format distinction before implementing
reductions. No detached executable branch or validator exception is proposed.

**Save-and-stay integration risk:** Node Config's synchronous `on_save` callback
is followed by its own saved-state snapshot and row refresh. Simply opening an
asynchronous picker and returning “saved” would make cancellation dishonest.
The editor must own the deferred draft/completion, including `_save_and_stay`,
and prevent duplicate requests. Test Save/close, Ctrl+S, Ctrl+Enter and Save/
Discard/Stay exits. Preferred UX: the config form remains available under the
picker and Cancel returns to its draft, with no false saved notification or
clean baseline. If the existing callbacks cannot support that from editor-owned
code, coordinate an interface with the 4a-2 worker; **do not edit Node Config
or mutate its private snapshots as a workaround**. This is a phase-2 readiness
check, not a claim that the existing callback already acknowledges cancellation.

Picker contract: return stable original port IDs, requested cardinality and
operation identity; cancel returns no selection. Do not reuse the current
single `kept_port` result without a deliberate compatibility wrapper. No
preselected first path, no silent overflow replacement, and no automatic apply
on toggling the last checkbox. Under/over-selection disables Apply with a
visible count. W/S/arrows move; Space/E toggle; Enter applies when valid, except
on a focused button, where it activates that button (including Cancel).
Header/count/buttons stay outside the scroll area; all 64 paths remain usable.

## Group record, reachability and validation

Use a versioned JSON-safe `delete_group` payload on the existing tombstone
config for a deleted owner. Q4 determines the container for a still-live
Branch's reduction record. Neither needs another MemoryBank or a new executable
node type. It records:

- operation kind/ID and root; original owner plus every removed member's full
  saved node data (IDs, types, aliases, configs, ports and connection records);
- removed/kept original ports and any old-to-new mapping;
- before/after patches to surviving nodes' edges and structural config;
- expected post-operation state for safe undo/finalization and a format version.

Do not store widgets, Python resources, Vault values or external file contents.
Update adapter serialization helpers deliberately: today's `original_*` helpers
only copy known single-node fields and will not preserve a new group by magic.
Save/reload/export/import must retain the payload, without adding hidden live
members back into `WorkflowMap`. A new multi-node group should become an
execution-blocking tombstone immediately, even before a disk save, rather than
leaving an executable Branch with its children already removed. Render its one
kept continuation from explicit group data; do not redisplay the original
dropped ports after reload. An existing nested group is captured/restored as
the same pending stub, with its recovery data intact; do not resurrect its
previously deleted members or discard nested recovery records. Unknown future formats need a clear refusal
rather than destructive best-effort restoration. Legacy stubs remain readable.

Reuse **`stub_removal_plan`** and **`nodes_only_reached_from`** from #82 as the
starting points. Build a pure preview plan before mutation, with the union of
all dropped roots and protection computed from the proposed surviving graph.
Protect an external parent even in an already disconnected draft; do not equate
“not reachable from Start” with “owned by the deleted branch.” Merge orphan
handling needs the stronger existing pruning logic. Keep one plan for preview,
commit and undo; do not make separate ad hoc walkers for each modal.

Apply through WorkflowMap ownership and signals. Preflight all mutations, avoid
awaiting mid-commit, coalesce the UI refresh, and recover on failure. This is
one logical user action, not a claim that current individual WorkflowMap calls
already provide a database transaction. If a backend batch API is necessary,
raise that scope explicitly rather than bypassing graph/dirty-state ownership.
Undo uses before/after comparisons so it cannot replace unrelated newer config.

**Strict validation:** never suppress loose-node, port, Merge or tombstone
checks to disguise incomplete pruning. Removed members are archive data, not
unlinked live nodes. An actual tombstone remains blocking until restored or removed. Under the
recommended Q4 option, a recovery row is saved archive data on a live Branch,
not a node whose execution/validation is being skipped. Current `unreachable` and unjoined-Beacon findings are
**warnings**; tombstones block runs. Preserve those actual severities.

**Q5 — validator wording:** if “strict about unlinked nodes” means changing all
current unreachable warnings into errors, that is a separate backend policy
change, outside the frontend ownership above. Recommended here: preserve current
severity, ensure no accidental leftovers, and continue reporting existing drift.

## Compact sample screens

These are proposed wording/layout, not rendered or implemented screens. Names
and counts come from the preview; repeated names get short IDs. Only add a
second confirmation when needed for an additional consequence, not after a
picker already displayed the exact destructive plan.

Branch deletion (the picker is also the confirmation):

```text
Delete Dispatch — keep 1 branch             Selected 0 / 1
[ ] Download     3 nodes
[ ] Cache       1 node
[ ] Offline     empty
Dropped paths will be stored with Dispatch in one deleted group.
Shared nodes stay. Z restores the whole group.
Space/E toggle   W/S move   Enter apply   Esc cancel
[Delete] (disabled until 1 selected)   [Cancel]
```

Conditional deletion, same component:

```text
Delete Is cached? — keep 1 path             Selected 1 / 1
[x] True: Read cache
[ ] False: Fetch report
Deletes Is cached? and 4 nodes only False reaches. 2 shared nodes stay.
Z restores the whole group.
[Delete]   [Cancel]
```

Path count reduction:

```text
Dispatch: 4 branches → 2                    Selected 2 / 2
[x] Download
[ ] Cache
[x] Offline
[ ] Retry
Removes 5 exclusive nodes. Shared nodes stay.
Selected branches keep their names, payloads and destinations.
One recovery row stores the deleted branches; Z restores the group.
[Apply]   [Cancel]
```

This sample uses the recommended Q4 recovery row. If the owner chooses a
blocking stub instead, say “A deleted-group stub remains before Dispatch;
remove it to run” before implementing that variant.

Resolver deletion:

```text
Delete Error Resolver and 6 recovery nodes?
No error continues to Write report. 2 shared nodes stay.
Z restores the whole group, including its routes.
[Delete]   [Cancel]
```

Node with its exclusive handler:

```text
Delete Fetch, its Error Resolver and 6 recovery nodes?
No error continues to Write report. Shared nodes stay.
Z restores Fetch, its handler and all 6 nodes.
[Delete]   [Cancel]
```

Shared handler variation:

```text
Delete Fetch?
Its Error Resolver is kept: Load cache also uses it.
Fetch's links are removed; other nodes' handler links stay.
Z restores this deletion.
[Delete]   [Cancel]
```

Selected node with two parents:

```text
Delete Pause, used by Dice and Save note?
Both parents will continue to Read note. Other paths stay.
Z restores Pause and both incoming connections.
[Delete]   [Cancel]
```

Merge deletion, Q1 recommendation:

```text
Delete Join?
Home path continues to Show report without waiting here.
2 Merge Beacons stay, disconnected from Join; validation will warn.
Z restores Join, its links and affected settings.
[Delete]   [Cancel]
```

Merge Beacon deletion, Q2 recommendation:

```text
Delete Report ready?
This branch ends at Save report. Join no longer waits for it.
Other branches stay. Z restores the Beacon and Join's settings.
[Delete]   [Cancel]
```

Final stub removal, before or after save:

```text
Remove deleted Dispatch and its 8 stored nodes?
Continue to Read cache. This cannot be undone.
[Remove]   [Cancel]
```

This removes recovery data, not newly discovered live descendants. A Resolver
group uses the same message with its No error destination; a leaf says
“No continuation.” For a count-reduction recovery row, name the stored branches and say the live
Branch stays; no bridge is needed for the non-executable recovery row.

Replacing a group stub with another type:

```text
Replace deleted Fetch with Logger?
Its 7 stored nodes will be discarded. Continue to Write report.
This cannot be undone. Restore Fetch instead to recover the group.
[Replace]   [Cancel]
```

Conflicted group undo, Q3 recommendation:

```text
Cannot restore Dispatch's group
Read cache's input changed after this deletion.
No changes made. Resolve the conflict, then restore the group.
[Close]
```

No confirmation is added for the ordinary single-node soft delete. Start uses
its existing refusal. Cancellation of every proposed destructive dialog leaves
graph, config, stub data, selection and undo state unchanged.

## Later session history

Introduce a bounded in-memory action stack for **graph edits**, not network/file
side effects or run rollback. One delete/reduction entry stores the entire group
operation, not one entry per backend connect/delete call. Config saves,
insertions, reconnections, moves and other edits can join the same recorder
later. Ctrl+Z in graph navigation undoes the latest action, independent of the
selected stub; normal text editing retains its own native undo. Existing Z can
remain selected-stub restore for compatibility. No redo shortcut is promised.

Closing the app clears the action stack; it does not erase recovery records
already saved in workflows. Save does not silently clear session history, and
undo after a save marks dirty rather than overwriting the file immediately.
A later decision may retire persistent stubs, but that is not implied by this
in-memory feature. Set memory limits and conflict behavior before implementing
history; JSON snapshots refer to files rather than duplicating their contents.

## Phase-2 acceptance and delivery gate

No behavior is changed in phase 1, so no application regression test is added
here. In phase 2, reproduce each changed behavior with a failing test first:

- Branch/Conditional picker: exact 1; count reduction exact N from old M;
  zero/too many picks, empty slots, 64 paths, scroll/focus, Space/E/Enter,
  Enter on Cancel, Escape/Ctrl+Q, cancellation and unchanged-count saves.
- Preview and actual changed IDs agree. One Z restores owner, all dropped
  members, both sides of edges, Merge selections and branch seed/name mappings.
- Restore before Save, after Save, after Validate and after reload; final stub
  removal is consistent; export/import round trips the group and legacy stubs.
- Shared Resolver, shared recovery tails across dropped routes, kept/dropped
  convergence, two parents, nested Branch/Conditional/Resolver, loops, exclusive
  orphan Merges, surviving Merges/Beacons and terminals. Start is never collateral.
- Keep the regressions fixed by #82's 531e4c1: shared handler deletion,
  error-only shared tails and retained input edges whose source port vanished.
  Independently replayed checks now pass, including soft-deleted/saved/restored
  peer guards, mixed direct-error/Resolver tails and protection by No error.
  Re-inventory merged main; do not rebuild these fixes as though still absent.
- Saved/unsaved Beacon removal produces the same approved topology and config.
  Merge cases follow Q1/Q2, with no accidental fan-out or occupied Merge slot.
- Count reductions keep arbitrary old slots (for example A/D) with correct
  names, payload sources, destinations and Merge references. Undo reverses
  that mapping. Save-and-stay cancellation does not falsely mark the draft saved.
- Changed graph while a picker is open, restore conflicts, missing members,
  replacement IDs, unknown group versions, nested pending stubs and error
  rollback preserve user data. Saved group stubs show one kept continuation,
  not phantom old branches.
- Active stubs still block runs; live leftovers still produce diagnostics.
  No edits to owner workflows; no per-run resource or secret values in records.

Use production CSS and actual keypress tests at 60/100/140 columns, then the
full suite. Show rendered
samples if implementation changes the proposed visible text/layout. Update
Current State, Session Log, owning backlog/boundary rules and command guidance,
retaining other workers' entries. Recheck #82, #83 and 4a-2 integration at the
actual implementation base. Any backend-format or Node Config interface change
requires explicit scope coordination; the owned frontend files are not a license
to change the engine contract.

**Stop after opening this docs PR.** The owner reviews Q1–Q5 and the sample
screens. Phase 2 is not authorized by this document alone or by #82 merging;
it also needs the owner's approval of this review.
