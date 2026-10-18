# AttackOfTheNodes Project Backlog

## Distributed direction approved — 2026-10-11

See [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md). The headless twin, Start-node variant, nested headless validation,
headless-export and always-running watcher sections below carry superseded
banners. Their text is kept for history. Execution of steps 1–3 plus the
ESP32 slice was authorized on 2026-10-12.

## Owner live-test findings — 2026-10-13 (noted, not yet investigated)

Reported by the owner after using the app during UX5. Several are old. Each
needs a reproduction before any fix is claimed; investigate when the
affected area is next touched.

1. **Older nodes are out of date.** Some do not work well together; port
   expectations look mismatched between neighbours (the data type one side
   offers versus what the other expects).
2. **Window placement in the file nodes does not work.** The owner wants
   window management taken out of the file I/O nodes (File Write's "Open
   after write" placement, File Manager) and given to dedicated window
   nodes. `window_control_node` / `backend/window_manager.py` (FO6, see
   "Deferred — File/Window Output Follow-Ups") were a start but have not
   been live tested.
3. **Pass-through missing.** Some nodes the owner expects to forward their
   incoming payload have no pass-through option. List which ones first.
4. **Vault payload config UI is outdated on many nodes**: not on the
   current shared Vault read/write controls.
5. **Reveal does not autoscroll.** When a toggle reveals dependent controls,
   the new widget appears below the viewport. The agreed rule is to scroll
   just enough to show the whole revealed widget; it keeps getting lost in
   new node UIs (see `NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md`,
   `UI_QUICK_REFERENCE.md`). A shared helper or a `check_ui` test would stop
   it regressing.
6. **Error UI keyboard navigation does not work while a workflow runs**
   (the error/recovery modals during execution).

7. **Lazy loading for busy node editors** (owner, during UX6). A 64-path
   Branch editor still takes ~0.55 s to open, almost all of it Textual
   building and styling 64 dropdowns. Owner's rule for a fix: show and make
   keyboard-navigable what is loaded first, mount the rest afterwards, and
   queue Save / Close until everything has loaded.

A node audit of PR #51 (same day) confirmed several of these with
reproductions and proposed a node contract plan:
[NODE_CONTRACT_PLAN.md](NODE_CONTRACT_PLAN.md) (proposed, not approved).

## Payload/file implementation — 2026-10-07

The requested payload/file build is implemented locally on `main` at `1211e68`
(uncommitted changes). See [the completed contract and migration notes](archive/PAYLOAD_FILE_IO_BUILD_PLAN.md)
and [verification evidence](audits/payload_file_io_2026_10_07/README.md).
Includes File Manager multi-file references, Reader text routing, Writer
prepend/append/newline options, typed source selection, forwarding previews,
Start/Text Output Vault routing, explicit termination and Merge home payloads.
Line-number insertion remains deferred. Native Windows FO7 and the reported
user/host path prefix remain live-verification items, not confirmed fixes.
This status supersedes older planned descriptions below.

## Owner-requested Payload And File I/O Follow-up (2026-10-07)

See [PAYLOAD_FILE_IO_BUILD_PLAN.md](archive/PAYLOAD_FILE_IO_BUILD_PLAN.md) for the
ordered implementation and agent ownership of forwarding previews, typed
Upstream/Vault choices, Start/Text Output Vault behavior, multi-file Viewer,
Writer newline/Prepend/Append, optional termination-control removal and Merge
carry-forward completeness. These changes are planned, not implemented.
Line-number insertion remains a TODO, including a possible typed numeric input
and defined indexing/out-of-range semantics. Existing single-file reference
reuse, Windows/WSL paths and deleted-source filtering must be preserved.
File Viewer is now File Manager. Extend existing File Reader to copy file
contents as text to downstream/Vault (P2a), accepting configured paths or
Upstream/Vault file references; do not add another Reader type.
P0a also investigates the owner's quoted Windows Copy as path example and
apparent user/host prefix, separating expected WSL normalization from config
mutation/display defects and hardening path syntax/runtime classification.

Current configuration/UI follow-up: [CONFIG_UI_BUILD_PLAN.md](archive/CONFIG_UI_BUILD_PLAN.md)
records unresolved F01/F05–F12 and FO-R5 with priorities and verification stages.
File Output is now integrated on the session PR branch; the original audit and
review retain their before-fix findings. Windows FO7 remains live-owner work.

## Future Direction — Cross-Platform App Distribution And Node Compatibility

Owner decision (2026-10-06): debug the current project under WSL, and eventually
provide app versions for the mainstream desktop operating systems: Windows,
macOS, and Linux. Nodes should behave correctly in their actual runtime
environment. This records product direction; packaging and additional platform
implementations are not yet scoped or completed.

- Provide appropriate installation, launch, and app packaging for each OS.
- Keep portable node behavior consistent; use platform adapters for filesystem,
  application launching, window control, and other OS-dependent operations.
- Handle path formats and host/runtime boundaries explicitly. Under WSL,
  Windows interoperability is a separate capability, not native Windows support.
- Detect capabilities and gate OS-specific dependencies and controls. Explain
  unavailable optional operations and report clear errors for essential ones;
  do not silently claim a successful unsupported operation.
- Verify portable nodes and OS-specific behavior in native Windows, macOS,
  and Linux environments, alongside WSL debugging. Track support per capability;
  passing Linux/WSL tests alone does not complete native OS verification.

The owner confirmed File Reader's copied Windows-path handling works under WSL.
Apply the same environment-aware principle to future node work. Existing Windows
FO7 live verification and deferred macOS/Linux window adapters remain open;
this direction does not imply every OS exposes identical window capabilities.
See [Development Environment And OS Support Direction](archive/PROJECT_KNOWLEDGE.md#development-environment-and-os-support-direction).

## Completed Project — Documentation Modernization

The docs folder previously had split-brain history from the Chrome-extension
concept, tkinter prototype, and current Textual TUI. Phase 10 refreshed the
active reference docs; the 2026-06-09 documentation overhaul then made the docs
task-first and archived deep history.

`docs/README.md` is now the entry point, `TASK_INDEX.md` is the task router,
and `MASTER_BUILD_PLAN.md` is the concise roadmap.

Completed cleanup:

- Refreshed `PROJECT_KNOWLEDGE.md` so it is again safe as the current-state
  single-source overview.
- Rewrote `ARCHITECTURE.md` around the Python/Textual implementation instead of
  the older IndexedDB/Dexie/BackendBridge architecture.
- Rewrote `SIGNAL_FLOW.md` around local backend services, Textual screens, and
  the current event bus.
- Regenerated `FILE_TREE.md` from the current workspace and included the
  standardization/debug-node files.
- Archived historical tkinter roadmap material in `archive/V05_BUILD_PLAN.md`
  so it is available as history without sitting in the default read path.
- Added `UI_QUICK_REFERENCE.md` so routine frontend fixes can start from a
  short current keybinding/config summary instead of the full TUI design file.

Ongoing rule: implementation phases should keep `SESSION_LOG.md` current and
update `MASTER_BUILD_PLAN.md`, `TASK_INDEX.md`, or `AGENT_HANDOFF.md` when
roadmap status or task routes change.

## Near-Term Project — Backend Features Not Yet Surfaced In UI

The backend has several useful capabilities that are intentionally reusable and
UI-agnostic, but the Textual frontend does not yet expose them fully. Keep this
list current when backend features land ahead of live-TUI work.

Current frontend gaps (audited 2026-06-15):

- **Run history browser:** `RunHistory` records persisted run summaries,
  per-node timings, and emits `RUN_HISTORY_UPDATED`. The editor currently uses
  history only to compute average node timings; there is no run-history screen
  for browsing previous runs, opening outputs/errors by run, comparing timings,
  or clearing old history.
- **Tombstone restore report UI:** `restore_tombstone()` can restore a deleted
  node and return detailed input/output/memory warnings when connections cannot
  be reattached. Editor undo and replace-with-original paths can call the
  backend/frontend adapter, but the promised alert that summarizes partial
  restore warnings is still deferred.
- **Branch health visualization:** `backend/branch_health.py` derives
  `valid`, `ended_unmerged`, and `floating` branch states. The editor has not
  yet consumed `branch_health_by_port()` to color branch rows independently of
  execution status.
- **Schema-driven file picker in node config:** validators understand schema
  fields with `path_hint: "file"` and `frontend/file_io.py` provides OS picker
  helpers for workflow import/export. Generated node config fields still render
  file paths as typed text inputs, so `FileReaderNode` and future file nodes do
  not yet get a picker button/overlay from schema metadata.
- **Save/load memory snapshots:** `SaveManager.save_current_workflow()` can
  include `memory_state`, and `load_workflow(..., restore_execution=True)` can
  restore it. The workflow library and save/load flows do not expose include
  memory / restore memory choices.
- **Workflow rename and bookmarks:** `SaveManager.rename_current_workflow()` and
  `WorkflowMap.set_bookmark()` / bookmark filtering exist. The frontend does
  not yet expose workflow rename controls or node bookmark navigation/filtering.
- **Error clearing controls:** `ErrorHandler.clear_errors_for_run()` publishes
  `ERRORS_CLEARED`. The current error/details UI is read-oriented and does not
  provide clear-current-run or clear-all actions.

Recommended cleanup:

- Add each UI surface in a small live-TUI-verifiable slice rather than bundling
  them into Phase 17. Phase 17 should stay focused on node identity, selector
  taxonomy, and editor row rendering.
- Prefer frontend adapters/screens that consume existing backend APIs. Do not
  move UI-specific state into backend services just to make these controls
  easier to render.
- When a gap is closed, move its bullet to `SESSION_LOG.md` and the relevant
  completed/near-term section below.

## Capability-driven node configuration follow-up

The completed integration/audit evidence remains in archive. Active contract
requirements live in Node Standards and Node Contract Plan; the remaining
[configuration follow-ups](#configuration-and-inspection-follow-ups-preserved-from-audits)
require fresh code checks before work. Preserve runtime capability truth and
unknown saved config rather than assuming old audit defects remain unfixed.

## Planned Project — Execution Screen Branch View

**Scheduled as Step 4 stage EX (2026-10-18).** Owner direction then: the run
shown as a keyboard-navigable node map like the Editor's, the memory view
scoped to the highlighted node (`M` for the whole log), A/D cycling branches,
and drill-in to subworkflow calls. Design and sample screens come first.

Owner direction (2026-10-06) is branch inspection, A/D navigation and stable
selection/scroll. The [preserved proposal](#execution-branch-inspection-proposal)
contains the full recommendations, preview budgets and acceptance cases.
[Architecture](ARCHITECTURE.md#execution-display-contract) owns the delivered
lifecycle/cache contract; the branch navigation/layout remains future work.

## Later Project — Return Merge Family and Merge-Early Guidance

Owner ideas, 2026-10-18, from the Step 4 review:

- **Return Merge nodes** with different return behaviour (first result wins,
  all required, collect into a list), to relax Step 4's single Return End
  (C3) with defined rules instead of last-write-wins.
- **Merge-early guidance:** the owner's style is to fan out quickly and
  merge as soon as a branch's purpose is done. The validator could gently
  suggest merging long-lived parallel branches. Guidance, never a rule; wide
  workflows stay possible.

## Planned Project — Backend / Frontend Boundary Cleanup

The backend should remain reusable for future CLI, web, or API frontends.

Use `BACKEND_FRONTEND_BOUNDARY.md` as the plan. Audit refreshed 2026-06-10:
Phase A (frontend tombstone adapter) is done, and `replace_with_tombstone()`,
tombstone-specific `replace_node_type()`, and backend-written
`_timing_invalidated` are already gone.

**Tombstone design decision (2026-06-11):** `tombstone_node` was previously
targeted for Phase B decommission (remove from backend, replace with generic
unknown-type error). That plan has been reversed. `tombstone_node` is now an
intentional backend type — the save-persistent deleted-node record. Saves write
a tombstone with full original node data (type, alias, config, connections)
instead of materializing to a `branch_end_node` with a `_system_role` marker.
This gives undo-after-reload, richer validator error messages, and meaningful
port-validity errors from the original port shape. Phase B decommission is
cancelled. See `BACKEND_FRONTEND_BOUNDARY.md` for the full rationale and
tombstone config contract.

Remaining Phase B work (redefined — frontend migration):

Done (2026-06-13):
- `editor_workflow_adapter.py`: `migrate_legacy_deleted_node()` and
  `migrate_workflow_on_load()` convert old `branch_end_node + _system_role`
  records to `tombstone_node` on load (7 tests in `test_tombstone_migration.py`).
- Validator tombstone error block now appends orphaned port context from config.
- `node_identity.py` marks tombstone with `editor_only: True`; `NodeFactory`
  exposes it; all other node types have `editor_only: False`.

Done (2026-06-13, Headless Plan H1/H2):
- `editor_workflow_adapter.py` writes `tombstone_node` directly on save
  (`materialize_deleted_nodes`), full original-data config per the contract
  below. Legacy `branch_end_node + _system_role` saves still migrate on load
  and now carry full restore data. Covered by `test_tombstone_phase_b.py` and
  `test_tombstone_migration.py`.
- Tombstone restore implemented as `restore_tombstone()` with connection
  validation and partial restore (the design spec below). Returns a
  `TombstoneRestoreReport`; editor undo and replace-with-original route
  through it. Covered by `test_tombstone_restore.py` (11 tests). The frontend
  alert that renders the report is the only remaining piece and is deferred
  (needs live-TUI verification).

Still remaining:
- Decide whether layout metadata such as `position` and navigation metadata
  such as `bookmarked` belong in portable workflow saves or editor sidecars
  (Phase C).

**Tombstone restore — connection validation (design spec 2026-06-11):**

Before reconnecting a restored tombstone's stored connections, the frontend
adapter must validate each one because the workflow may have drifted since the
node was deleted. Three drift categories:

- **Upstream output drift:** the source node that fed into the deleted node may
  have removed or renamed its output port, or changed the dead-drop payload type.
- **Downstream input drift:** the target node that received from the deleted node
  may have removed or renamed its input port, or that port may now be occupied
  by a different source.
- **Memory bank drift:** `membank_inputs` the deleted node read may no longer be
  declared by any surviving node's `membank_outputs`.

Restore procedure:
1. Always restore node type, alias, and config — never blocked by connection drift.
2. Per stored input connection: verify source node exists AND declares the
   referenced output port → reconnect if yes, leave unconnected if no.
3. Per stored output connection: verify target node exists AND declares the
   referenced input port AND that port is not already occupied → reconnect if
   all pass, leave unconnected if any fail.
4. Per stored membank input: check if any surviving node declares the variable
   in `membank_outputs` → restore the declaration regardless, but flag if the
   source is missing.
5. Surface a frontend alert after restore if any connections could not be
   re-established, with two named sections:
   - **Input connection errors** — original source node alias + port + reason
     (source gone / port gone).
   - **Output connection errors** — original target node alias + port + reason
     (target gone / port gone / port already occupied).
   - **Memory input warnings** — membank variable names whose declared source is
     no longer present.
6. A partial restore (node back, some connections missing) is always preferred
   over leaving a tombstone. The validator will surface remaining loose ends.

## Planned Project — Legacy Bypass / Compatibility-Code Audit

Goal: periodically sweep the codebase for accumulated legacy/back-compat
"bypasses" and remove each once the thing it bridges is gone. Multiple
migrations (typed vault, tombstones, the canonical data-type + helper-spec work
2026-06-19, etc.) have each added *additive* compatibility — aliases, format
fallbacks, dual-path support — specifically to keep tests green and avoid
mass-rewrites at the time. That is the right call per-migration, but the shims
accumulate and quietly become permanent if never revisited.

**Distinguish shim from semantics.** Not every fallback is debt. Schema
*defaults* that define behavior (absent `data_type` ⇒ `any`, absent `required`
⇒ optional in `node_base`/`node_factory`) are the contract, not legacy code —
keep them. The audit targets *bridges between an old and a new form* that exist
only because old data/specs/nodes still exist.

Known shims to reevaluate (extend this list as more are found):

- **Helper legacy spec sections** (`aotn_node_helper/generator.py`):
  `input_sources` / `output_routing` / `input_port_metadata` /
  `output_port_metadata` are kept working alongside the unified `inputs:` /
  `outputs:` blocks (handoff §7). Removable — with their `test_node_helper`
  cases — once every spec/node is recreated in the unified form. This is the
  natural payoff of the planned full node-recreation pass.
- **`boolean` → `bool` data-type alias** (`backend/data_types.py`
  `LEGACY_ALIASES`): a safety net for any persisted vault `type_tag` spelled
  `boolean`. Before deleting, grep `workflows/*.json` for
  `"type_tag": "boolean"`; if none, the alias is dead code. This is the only
  data-type shim tied to *user data* rather than node code.
- **Tombstone legacy migration**: `migrate_legacy_deleted_node()` /
  `branch_end_node + _system_role` conversion on load (see Boundary Cleanup
  above) — removable once no saved workflow predates `tombstone_node`.

Recommended:

- Keep a short inventory of compat shims, each with an explicit *remove-when*
  condition, so they are deliberately temporary rather than silently permanent.
- Fold shim removal into the migration that obsoletes it (e.g. delete the helper
  legacy paths during the node-recreation pass), not as a separate risky sweep.
- When removing a shim, remove its tests in the same change so coverage tracks
  the supported surface, not the retired one.

## Closed (2026-06-22) — Selector Family Taxonomy Reconciliation

**Resolved.** The selector now uses **five tabs mapping 1:1 to the five backend
`primary_family` values**, ordered `In` (Inputs) · `Flow Control` · `Utility` ·
`Out` (Outputs) · `Complex` with hotkeys 1–5. The combined `I/O` tab and its
Input/Output segmented toggle were removed. `In`/`Out` are abbreviated display
labels mapped via `TAB_FAMILY` in `frontend/screens/node_selector.py`. Docs
(`UI_QUICK_REFERENCE.md`, `PHASE_17_NODE_VISUAL_IDENTITY.md`,
`IO_CONTRACT_UI_DESIGN.md`) and tests updated to match. Code and the five backend
families now agree, so there is no longer a taxonomy split to reconcile.

## Future Direction — Outputs Family: Live UI-Display Nodes

The Outputs tab is intended to grow its own identity: nodes whose job is to make
UI appear on screen *during* workflow execution so data is easy to view, with
likely **multiple output-rendering options** (e.g. panels, tables, inline value
displays). The same pattern applies — less commonly — to certain user-input
nodes on the Inputs side. This is the motivation behind giving Outputs a
dedicated selector tab (2026-06-22). No implementation scoped yet; capture
concrete node concepts in `NODE_CATALOG.md` as they firm up.

## Deferred — File/Window Output Follow-Ups (from FILE_OUTPUT_BUILD_PLAN)

FO1–FO6 landed 2026-07-11 (`file_output_node`, markdown formatting mode,
`file_view_node` + viewer screen, `backend/window_manager.py`,
open-after-write placement, `window_control_node`). Deferred out of that
plan's scope, per its design decisions:

- **Virtual desktop moves (pyvda)** — D7: relies on undocumented Windows
  internals that break across feature updates; the core use case never
  needed it. The adapter protocol leaves room for a `desktop` capability.
- **macOS (`pyobjc`/AppleScript) and Linux (`ewmh`/`xdotool`) window
  adapters** — the `WindowManager` protocol and D3 preset vocabulary are
  designed for them; no stub classes ship until one is implemented.
- **Validator warning for `Open after write` on a loop path** — one window
  opens per iteration today (documented on the field and in
  `NODE_CATALOG.md`); loop detection is not free, so the warning is
  deferred (FO5 task 4).
- **Cross-run window adoption** — intentionally out (D12): windows that
  outlive the run are unmanaged orphans; adoption would require
  re-discovery, which D4 forbids.
- **Refocus AOTN after a user prompt** — possible follow-up depending on
  the FO7 focus-fight observation (open-after-write directly upstream of
  `user_text_input_node` steals OS focus as the TUI prompts).
- **Remote-backend window effector** — D11: when the backend becomes a
  server (Multi-Frontend Expansion below), window actions migrate behind
  the EventBus to a local effector; `capabilities()` already gates it.

## Future Direction — Headless CLI Execution (`aotn`)

> **Partly superseded (2026-10-11).** Headless execution now follows [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md)
> steps 1–2:
> - an unattended policy passed in at run start;
> - a run service API;
> - `RecoveryPolicy`/`InputProvider` interfaces;
> - an `aotn run` CLI.
>
> Compile-and-swap twins are replaced by providers (decision D1). Still
> active: the goal, "Configurable Data Directory" and the "What to avoid"
> list. Each superseded subsection below is marked; the original text is
> kept for history.

Goal: execute a workflow from the terminal without launching the TUI —
`aotn <workflow name>` — for scripting, automation, and scheduled runs.

**What is already safe:** The backend (`MasterState`, `Supervisor`,
`WorkflowMap`, `Validator`) has no frontend imports and can be instantiated
without Textual. The path to a CLI entrypoint is adding a thin wrapper that
wires the backend without starting the app.

### Compile-and-Swap Model

> **Superseded (2026-10-11)** by [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) decision D1. No headless twin node
> types: input comes from the run's `InputProvider` (stdin, CLI args, API, AI),
> and output from the run service's events and results.

Headless execution uses a **duplicate saved file** produced by a "Save for
headless execution" export option. The TUI workflow is always the editable
source of truth; the headless file is compiler output, not hand-edited.

The export step works by **node-type swap**: every I/O node that is
TUI-specific is replaced with its headless twin — a node with the exact same
port shape (same input/output ports, same data types) so all graph connections
transfer without change. The graph topology is preserved exactly; only the
I/O boundary nodes change.

Each headless twin declares its TUI counterpart via a `headless_equivalent`
pointer in node metadata (or a registry entry). That pointer is what the
validator/compiler uses to drive the swap. A node with no declared
`headless_equivalent` and no headless-safe flag blocks the export with a clear
error: `"Cannot compile for headless — node '[Alias]' has no terminal
equivalent."` This surfaces cleanly before the file is ever written.

### Headless Input Node: Interaction Format from Type

> **Superseded (2026-10-11)** by [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) decision D1. No headless twin node
> types: input comes from the run's `InputProvider` (stdin, CLI args, API, AI),
> and output from the run service's events and results.

The default mode for every headless input twin is **prompt stdin at runtime**.
No configuration is required at export time — the swap alone is sufficient for
a working headless workflow.

Each twin knows how to prompt and validate based on its node type. The
interaction format is inherited, not separately configured:

**Text input twin** — free text, enter to confirm:
```
Enter value for "Search Query": _
```

**Single-select twin** (radio equivalent) — user enters exactly one valid
index; reprompts on invalid entry:
```
Choose an option for "Processing Mode":
  1. Option A
  2. Option B
  3. Option C
Enter choice: _
```

**Multi-select twin** (checkbox equivalent) — user enters a comma-separated
list of valid indices; reprompts on invalid entry or out-of-range values:
```
Select options for "Export Formats":
  1. PDF
  2. CSV
  3. JSON
Enter choices (e.g. 1,2): _
```

The options list, label, and validation rules all come from the same node
config the TUI node carried — they transfer through the swap automatically.

### Headless Input Mode (Optional Power-User Config)

> **Superseded (2026-10-11)** by [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) decision D1. No headless twin node
> types: input comes from the run's `InputProvider` (stdin, CLI args, API, AI),
> and output from the run service's events and results.

After export, individual input nodes can be reconfigured for automation. Each
headless input twin exposes a `headless_input_mode` field:

| Mode | Behavior |
|---|---|
| `prompted` (default) | Prompt stdin at runtime as above |
| `cli_arg` | Read from `--input alias=value` at launch; no prompt |
| `static_default` | Value baked into node config; no prompt, no arg needed |

A user scripting `aotn` into a cron job configures their input nodes to
`cli_arg` or `static_default` so the run is fully non-interactive. The
default `prompted` mode always works for a human running the workflow manually.

### Headless Output Node

> **Superseded (2026-10-11)** by [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) decision D1. No headless twin node
> types: input comes from the run's `InputProvider` (stdin, CLI args, API, AI),
> and output from the run service's events and results.

Output twin defaults to **stdout**. Optional `output_file` config on the node
redirects output to a file path. No configuration required at export time.

### Start Node Redesign

> **Partly superseded (2026-10-11).** `HeadlessStartNode` is replaced by the
> provider model (D1), and `TriggerStartNode` by start triggers that launch runs
> through a workflow contract (D2). `NestedStartNode` becomes the typed Start
> contract of [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) step 4.
> **Superseded (2026-10-18):** one Start node with typed, routed rows replaces
> the variants; see [SUBWORKFLOWS_PROPOSAL.md](SUBWORKFLOWS_PROPOSAL.md) C1/C2.

The `StartNode` is currently auto-generated and functionally minimal — it is
hidden in the editor by default and carries no user-facing config. The redesign
keeps this default but introduces context-specific start node variants revealed
when the user declares an execution context for the workflow.

| Start node type | When revealed | Purpose |
|---|---|---|
| `StandardStartNode` | Always (hidden by default) | Current behavior — TUI workflow |
| `HeadlessStartNode` | Selected on "Save for headless" export | CLI preamble setup |
| `NestedStartNode` | Workflow marked as callable sub-workflow (Phases 19/20) | Receives data from parent dispatch |
| `TriggerStartNode` | Always-running watcher workflow (far future) | Persistent listener lifecycle |

Each variant has the same downstream port shape as `StandardStartNode` so
the rest of the graph is unaffected. Only the start boundary changes.

**`HeadlessStartNode` — CLI preamble configurator.**
When revealed at headless export, this node runs before the first workflow node
executes. Its config carries:

- **Banner text** — workflow title and description printed to stdout at launch.
- **Global session prompts** — values shared by multiple downstream nodes
  (e.g. an API key or a working directory) collected once here rather than
  re-prompted inside each individual input node.
- **Setup commands** — any environment assertions or pre-flight checks before
  execution begins.

Centralising setup in the start node keeps individual input nodes focused on
their single data point and avoids the user being interrupted repeatedly for
related values that belong together.

### Nested Workflows and Headless Validation

> **Superseded (2026-10-11).** There is no headless export, so there is no
> `headless_valid` flag. Subworkflows are child runs linked by `parent_run_id`
> (D3) and are validated against their typed contract ([DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) step 4). The
> black-box trust idea (check the contract, not the internals) carries over.

Nested workflow nodes (Phases 19/20) are treated as a **black box** by the
headless validator. The validator does not re-traverse the nested workflow's
internal graph. Instead it checks two things only:

1. **Headless validity flag.** The nested workflow node carries a
   `headless_valid: bool` flag derived when that workflow last passed headless
   validation. If `false` or absent, the parent headless export blocks with:
   `"Nested workflow '[name]' has not been validated for headless execution."`
2. **Port compatibility.** The nested workflow's exposed input/output ports
   are compatible with the parent graph's connections (same check as any other
   node).

This is the compiled-library trust model: the nested workflow is validated as a
unit independently; the parent trusts that pre-validated result. Any nested
workflow designed for headless must itself pass the same compile-and-swap
validation before the `headless_valid` flag is set, and any nested workflows
*it* contains are validated by the same rule recursively — but each level
trusts its children's flags rather than re-walking the full graph.

### Configurable Data Directory

> **Still active (2026-10-11):** scheduled in [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) step 2, before the CLI.

The current `Path(__file__).resolve().parent.parent` anchor in `persistence.py`
assumes the source tree layout. CLI users need a configurable base path (env
var or config file). Implement this before the CLI entrypoint — every new
hardcoded relative path caller makes the migration larger.

**What to avoid now that would close off this direction:**

- Expanding `signal_waiting_for_input` usage without specifying the headless
  fallback — every new use tightens TUI coupling deeper into the node graph.
- Building Outputs-family nodes that assume a Textual screen exists — the
  output destination must be an abstraction, not hardcoded to the TUI panel.
- Adding more hardcoded relative paths in `persistence.py` callers.
- Designing TUI I/O nodes whose port shape cannot be matched by a headless twin
  — identical port shape is what makes the swap mechanical.

See also: `Future Direction — Always-Running Trigger Watcher` (depends on this).
See also: `Future Direction — Metadata Conditional Nodes` (complementary approach
for workflows that run in multiple contexts without a separate export).

---

## Future Direction — Metadata Conditional Nodes and Context-Aware Validation

Goal: a dedicated node group that branches on run-time execution context rather
than on data values, allowing a single workflow to route itself correctly
depending on how it was launched — TUI, headless CLI, nested sub-workflow, or
trigger watcher.

This is complementary to the compile-and-swap headless export. Compile-and-swap
produces a clean headless-only artifact. Metadata conditionals let a single
workflow handle multiple modes intelligently without a separate export.

### The Node Group

**Execution Context Conditional** nodes live in their own selector group
(suggested home: Flow Control → Context Branching, or a dedicated
"Context" direct-add section). Initial members:

- **`ExecutionModeConditionalNode`** — branches on the current execution mode:
  `tui` / `headless` / `nested` / `triggered`. Each output port corresponds
  to one mode; the workflow follows the matching path.
- **`RunMetadataConditionalNode`** — branches on any named run metadata key
  and value. Generalises the execution-mode node to arbitrary context tags set
  at launch time or by a parent workflow.

Future extensions (not scoped yet): environment conditionals (`OS`, Python
version, installed packages), settings conditionals (branches on a
`ConfigurationManager` key), custom run-tag conditionals set by a caller.

### How Validation Changes

With context-aware branches in the graph, the validator gains a **context
filter** layer on top of its current full-graph structural pass:

| Finding | Current model | With context conditionals |
|---|---|---|
| Structural error (broken connection, missing node) | Error in all modes | Error in all modes — unchanged |
| TUI-only node on an `execution_mode == headless` branch | Error (blocks headless export) | Warning — "node unreachable in headless mode but gated correctly" |
| Headless twin on a `execution_mode == tui` branch | N/A | Warning — noted, not blocking |
| TUI-only node with no context gate in a headless-flagged workflow | Error | Error — not protected by a gate |

The rule: **a node that does not work in a given context is a warning if it
is properly gated behind a context conditional, and an error if it is not.**
The validator still runs a full structural pass on all paths; it only softens
the severity for nodes that are explicitly isolated from the contexts where
they would fail.

This means workflows can contain TUI-only nodes (rich display, interactive
prompts) alongside headless-compatible paths, and headless validation does not
error on the TUI branches as long as they are behind an execution-mode gate.

### Interaction with Headless Export

> **Superseded (2026-10-11).** There is no headless export (D1 in [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md)).
> The metadata conditional nodes themselves remain a possible future option,
> keyed on the run's launch context.

When a user runs "Save for headless execution" on a workflow containing
execution-mode conditionals:

- Paths behind `execution_mode == headless` gates are kept as-is.
- Paths behind `execution_mode == tui` gates are either pruned from the export
  (the headless file contains only the headless paths) or preserved with a
  warning notation. Decision to be made at implementation time.
- The `ExecutionModeConditionalNode` itself is replaced in the export with a
  direct connection to the headless branch (the conditional is no longer needed
  when the execution mode is fixed).

### Design Constraints

- Metadata conditionals branch on **read-only context** — they cannot modify
  run metadata, only read it. Side-effect-free branching keeps the validator's
  context-filter analysis tractable.
- The execution mode must be set once at run start by the entry point
  (`MasterState` or the CLI entrypoint) and must not change mid-run. It is a
  property of the launch context, not mutable workflow state.
- Context conditional nodes must be transparent to nested workflow validation —
  a nested workflow's `headless_valid` flag is set based on whether its
  headless-mode paths (behind its own context gates) are valid, not on whether
  it also has valid TUI paths.

---

## Future Direction — Always-Running Trigger Watcher

> **Superseded (2026-10-11)** by [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) decision D2: a trigger launches a new
> run per event, through the workflow's contract, with per-trigger
> concurrency modes (step 5). A wait-for-event node in the middle of a
> workflow is an open question in that plan.
>
> The cross-run persistent state point below carries forward into step 5.
> **Correction:** "Cycles are currently rejected by the validator" is wrong.
> The validator has no cycle check, and loops run today (verified
> 2026-10-09). The original text is kept for history.

Goal: a long-running headless workflow that never terminates — it monitors for
external triggers (file changes, webhooks, cron schedules, socket messages) and
dispatches sub-workflows when conditions fire. Acts as a lightweight OS-level
automation layer.

**Depends on:** Headless CLI execution (above) and nested workflows (Phases
19/20).

**New primitives required:**

- **Trigger nodes.** An Inputs-family node type that blocks waiting for an
  external event rather than reading a one-shot value. These are persistent
  async listeners. They must be exempt from `node_timeout_seconds` — the global
  timeout would kill a blocking listener. Implement a per-node or per-family
  timeout override before building trigger nodes.
- **Loop/cycle support.** The always-running workflow must loop — watch →
  trigger fires → dispatch → return to watching. Cycles are currently rejected
  by the validator and BFS traversal. A deliberate loop node type (or explicit
  restart mechanism) must be supported as a first-class design, not accidentally
  un-rejected.
- **Nested workflow dispatch.** The dispatch step launches a sub-workflow as a
  child. Must support fire-and-forget (watcher continues immediately) vs.
  wait-for-result modes.

**Architecture constraints to maintain now:**

- **Resource lifecycle.** `RunSession.close_all()` is called only on terminal
  paths — a non-terminating workflow never triggers it. Do not add new resource
  types that assume a single terminal cleanup call. Resource cleanup must be
  periodic or per-trigger-cycle for the watcher pattern to work.
- **MasterState isolation.** Dispatched sub-workflows need isolated execution
  contexts (separate `MemoryBank`, supervisor tracking, run state). Do not
  deepen the assumption that only one workflow can be in `RUNNING` state at a
  time.
- **OutputManager / ErrorHandler eviction.** Per-run in-memory caches are
  evicted in `_record_run`, which is only called at terminal paths. A
  non-terminating workflow's caches grow unboundedly without periodic
  checkpointing. Do not expand in-memory-only accumulation patterns.
- **Cross-run persistent state.** The watcher may need to carry state between
  trigger fires (counter, last-seen timestamp, accumulated results). This is
  different from the per-run ephemeral `MemoryBank`. Design it as a separate
  "persistent context" concept — not an extension of `MemoryBank` across runs.

**What to avoid now:**

- Applying `node_timeout_seconds` uniformly without a per-node override path —
  this makes trigger nodes impossible.
- Writing new code that assumes `_record_run` is eventually called — anything
  depending on that assumption breaks for non-terminating workflows.
- Deepening single-`MasterState` / single-active-run assumptions in event
  routing or completion logic.

---

## Future Direction — Multi-Frontend Expansion (Chrome Extension, Desktop GUI)

> **Scheduled (2026-10-11)** as [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) step 6, over the step 2 run service.
> The invariants listed below remain in force.

Goal: run the backend as a standalone persistent server that multiple
simultaneous frontends connect to — the existing TUI, a Chrome extension, and a
separate desktop GUI. Frontends are naturally aware of shared state because they
all talk to the same backend server.

**Architecture model.** All frontends become thin clients to `localhost:PORT`.
The Chrome extension (browser sandbox, JavaScript) connects via HTTP + WebSocket.
The desktop GUI does the same, or keeps a direct in-process Python path like the
current TUI. The backend is the single source of truth; frontends subscribe to
events over WebSocket and issue commands over HTTP. `RunSession` handles (file
objects, AI sessions) stay Python objects in the backend — frontends receive
only serializable representations.

**What is already well-positioned:**

- Backend has no frontend imports — the load-bearing separation holds today.
- JSON workflow format is portable — any frontend can read and write the same files.
- `EventBus` already uses named events with structured payloads — maps cleanly
  to WebSocket push.
- `NodeContext`, `MasterState`, `Supervisor`, `Validator` carry no Textual
  references.

**What will need to change (not now — but design with it in mind):**

- **Backend as a standalone process.** Currently `MasterState` is instantiated
  inside the same process as Textual (`main.py` wires both together). The
  multi-frontend model requires the backend to run as its own process with an
  HTTP + WebSocket API layer. The TUI either becomes a thin client or retains
  an optional direct in-process path.
- **EventBus subscriptions become network streams.** Subscriptions are currently
  Python closures — they work in-process only. For remote clients, events must
  be pushed over WebSocket. The payloads are already JSON-serializable; the
  subscription model needs a network layer on top.
- **Configurable data directory.** Same requirement as the CLI direction —
  `persistence.py` path anchoring must become an env var or config file before
  a backend server can be installed anywhere.

**Invariants to protect right now — these are load-bearing walls:**

1. **No frontend imports in backend code.** One accidental
   `from frontend.screens import ...` in a node file permanently breaks that
   node for any non-Textual context. Enforce on every change.
2. **EventBus payloads must remain JSON-serializable.** No Python objects,
   Textual widgets, or reactive references in event data. If a payload needs a
   Python object, store it in `RunSession` and put only the reference key in
   the event.
3. **No non-serializable Textual state on MasterState.** If widgets or reactive
   objects end up referenced from `MasterState`, it cannot be separated into its
   own process.
4. **All event payloads carry `run_id`.** The `EventBus` has no run isolation
   today — events from all supervisors share one bus. As multi-run and
   multi-frontend scenarios grow, consumers must be able to filter by `run_id`.
   Ensure new event payloads always carry `run_id` so future isolation is an
   additive subscriber filter, not a breaking schema change.

## Near-Term Project — Frontend Command UI Toolkit

**Adopted scope (owner, 2026-10-18):** a typed Python registry compiled into
native Textual bindings owns keys, stable command IDs and pure NAV/TEXT/Select
and modal availability. It supplies generated presentation; Textual remains
responsible for dispatch. One authoritative route/display source per migrated
command. Preserve defaults except the listed defects; show samples for any
visible text/layout change. Three PRs, one at a time, each against main, then
stop for the owner/reviewer:

| Phase | Scope | Status |
|---|---|---|
| 1 | Registry/runtime, stable IDs, class-time compilation, pure shared availability and characterization; one simple profile end to end | Merged #77: Confirm, including its unchanged generated hint and navigation |
| 2 | Shared mixin/navigation policies, retire duplicated action-name lists; Input/TextArea and Select adapters; Stash, Node Config (P insert), Editor, Workflow Library and list pickers | Awaiting review on `codex/keymap-policies`; each listed defect reproduced failing first and fixed. Multi-state policies and native adapters installed; current display text remains for phase 3 |
| 3 | Generated Help/hints for migrated screens; replace handwritten key text and stale A/D-tab descriptions in Node Config/selector | After phase 2 merges |

Deferred: remaining read-only viewers until next touched, generated
`UI_QUICK_REFERENCE.md` tables/source checks, Settings rebinding UI. Keep IDs
stable for those follow-ups. No backend/workflow format changes.

**Post-S3 re-inventory:** baseline `714f190` (merged #75, 2026-10-18), Textual
8.2.7. Still 22 screen classes in 20 modules; 182 literal app/screen binding
rows before this migration, plus 10 shared navigation rows and raw widget/key
handlers. S3 adds `p -> stash_insert` as a priority binding in Node Config,
disabled while typing; target capture/accepted types/source switching and
focus return are covered in `test_stash_insert.py`. **Plain P, not Ctrl+P**:
the command palette and Ctrl+P are untouched. The earlier research's claim
that S3 requires disabling/moving the palette is withdrawn; it is not a
migration hazard or a reserved-key change.

Phase 1 compiles every Confirm alias before Textual's class merge and reuses
the existing focus mechanics. Other screens, root App policy, the Select
compatibility patch and legacy guard lists remain unchanged until phase 2.
Phase 1's isolated hosts established the policies; phase 2 migrates their
production owners. Help/Error Details/unsaved and input prompts receive the
same mechanical profile integration because they share CommandScreenMixin.
Memory/Output/File viewers remain deferred. See [Contributing](CONTRIBUTING.md#adding-a-registered-command).

Recommended cleanup:

- Continue using shared command helpers for new modal screens. `SettingsScreen`,
  path prompts, user input, generated config fields, and modal selectors already
  have baseline helper coverage.
- Keep future notification copy routed through `frontend/notifications.py`.
- Keep schema-generated node config as the default path; extend field schemas or
  frontend render helpers before adding per-node custom modal logic.
- Add a focused keyboard-only smoke suite for common modal flows: open, move,
  activate, type, escape typing mode, save/cancel, and scroll to off-screen
  fields.

## Near-Term Project — Helper-Backed UI Standardization

Goal: evolve `aotn_node_helper` from a backend node generator into a guardrail
for repeatable Textual UI work. The recurring failure modes are keyboard
navigation, autoscroll, widget sizing, and dynamic UI that changes after a
checkbox/select/input changes.

Done (2026-06-12):

- `aotn_node_helper/check_ui.py <node_type>` mounts `NodeConfigScreen`, checks
  top-level tab placement for schema fields, verifies generated controls
  participate in keyboard focus, and validates dynamic rule state at mount.
- Generic dynamic-form schema keys `enabled_when`, `visible_when`, and
  `mutually_exclusive_with` are implemented in `form_generator.py`, applied
  live by `NodeConfigScreen` (across tabs), and covered by
  `tests/test_form_rules.py`.
- Helper specs expand the NODE_STANDARDS standard model through
  `input_sources` and `output_routing` sections.
- A config-UI smoke test (`test_<node_type>_ui.py`) is generated for specs
  that use `config_tabs` or the standard sections.

Recommended cleanup:

- Extend the generated UI smoke test to full keyboard simulation: switch tabs
  with number keys (`1`–`5`), move between rows with W/S, move within a row
  with A/D, activate with E/Enter, exit edit mode, and reach Save/Cancel.
- `repeatable_inputs` now covers bounded ordered source-input groups through
  helper-expanded count + slot fields, complementing
  `visible_when`/`enabled_when`.
- Done (2026-06-13, Headless Plan H4): label/value pairs for select options in
  `form_generator.py` (`_select_options` accepts `{label, value}` mappings and
  2-item sequences) so backend reads stable machine values; plain-string
  options unchanged. Schema-key test matrix in `test_form_generator.py`.
- Add a screen scaffold command for non-node screens. The scaffold should create
  a `CommandScreenMixin` screen with a status bar, visible Cancel control,
  vertical button order, and a generated keyboard-navigation test.
- Add a small UI manifest format for screens and generated config surfaces:
  first focus target, last focus target, scroll container, dynamic controls,
  selection lists, and expected Save/Cancel behavior.
- Make widget sizing testable with mounted-screen assertions: long labels do not
  overflow command controls, dynamic rows do not resize the whole layout, and
  scroll-to-focus keeps the active control visible.
- Keep generated UI support frontend-only. The helper may inspect node metadata
  and generate frontend tests, but backend nodes should not depend on Textual.

## Near-Term Project — Branch Health Visualization

Goal: make branch validity visible while editing, before users need to run full
validation.

Done (2026-06-13, Headless Plan H5): the derivation logic is implemented in
`backend/branch_health.py` — pure-logic `derive_branch_health()` /
`branch_health_by_port()` classify each branch path as `valid` /
`ended_unmerged` / `floating` from workflow structure (not stored UI state),
keyed by `(branch_node_id, port)`. `output_types_from_factory()` tracks the
node taxonomy. Covered by `test_branch_health.py` (14 tests). The remaining
work below is the editor visual surfacing, which needs live-TUI verification.

Recommended cleanup:

- (Done) Derive branch health from workflow structure, not stored UI state.
- (Done) Represent at least three branch states:
  - valid branch ending: end/output node or connected Merge Beacon node;
  - branch ended but not merged: Merge Beacon exists but is not connected to a
    Merge node;
  - floating branch: no valid output/end node and no Merge Beacon.
- Surface those states in the editor with clear but restrained state markers or
  labels; keep node interiors on the default background. (Consume
  `branch_health_by_port()`.)
- Extend `NodeCard` or a future editor display adapter so branch-health
  indicators are separate from execution status icons.
- Fold this into the FA-7 visual pass: VS Code-like dark styling, readable
  node-card borders/icons, larger editor rows, and dimmer command text fields
  when not editing.

## Later Project — Schema-Driven Node UI Expansion

Goal: make adding a node feel like adding backend metadata, not hand-editing
frontend menus.

Recommended cleanup:

- Continue the Phase 17 taxonomy work from
  `PHASE_17_NODE_VISUAL_IDENTITY.md`. The user-facing selector families are
  Inputs, Flow Control, Outputs, and Complex; reusable subcategories should
  carry capabilities such as Triggered, File I/O, Internet, AI, Passive Output,
  Active Output, Parallel, Conditional, Runtime Resource, and Utility.
- Redesign the node library around that taxonomy. Flow Control should
  eventually distinguish always-parallel branch nodes, conditional branch nodes,
  merge/wait nodes, loop nodes, and utility markers instead of forcing all
  branching behavior through one generic node.
- Extend config schema only with generic keys: placeholder text, min/max/step for
  numeric fields, optional blank-select behavior, and multiline height hints.
  Visibility/enablement conditions and mutual exclusion are done (2026-06-12):
  `enabled_when`, `visible_when`, `mutually_exclusive_with`.
- Done (2026-06-13, Headless Plan H4): `tests/test_form_generator.py` covers
  every schema key in `frontend/widgets/form_generator.py` (label/required/
  description, default, options as label/value pairs, boolean, numeric
  min/max, string length, code language, multiline height, numeric coercion).
- Move branch-label generation and pass-through notes toward documented generic
  `ui_hints` where possible.
- Simplify generated config surfaces: ordinary nodes should show only the fields
  they declare, semantic transient input/output metadata, memory-bank sections
  when enabled, and generic topology selectors when required.
- Node author checklist exists in `NODE_STANDARDS.md` (Authoring Checklist
  section); extend it with categories/pass-through/memory-bank specifics as the
  node overhaul progresses.
- Add a validation test that every registered node can mount its generated config
  without frontend custom code unless it is explicitly listed as a structural
  topology editor.

## Later Project — Runtime Resources And Hidden Helper Nodes

Goal: support richer node behavior without making the editor visually noisy.
Visible nodes should stay user-friendly, while reusable utility behavior can be
attached behind the scenes when a node needs it.

Full design note: `archive/plans/RUNTIME_RESOURCE_SESSION.md`

Done — the core `RunSession` is implemented, including chat session API:

- `backend/run_session.py` holds per-run handles (`open_file`,
  `register_resource`, `validate_path`, `close_all`) and multi-turn chat
  histories (`get_or_create_chat_session`, `append_chat_message`,
  `get_chat_history`, cleared by `close_all`).
- `MasterState` creates the session at run start, passes it to all
  supervisors, and closes it in `_record_run` on every terminal path.
- Nodes reach it through `context.run_session`; `FileReaderNode` is the
  first consumer. The validator checks schema fields hinted with
  `path_hint: "file"` (empty required path = error, missing on disk =
  warning). Coverage lives in `tests/test_run_session.py`.
- Validator warns when a node declares `use_chat_session: True` without a
  `session_key` configured.

`get_resource(key)` is already implemented — retrieves a previously registered
handle by key (see `tests/test_run_session.py::test_register_and_get_resource`).
Nodes that receive a typed vault reference key will call
`context.run_session.get_resource(ref_key)` to resolve the actual Python handle.

Remaining design notes:
- Keep the resource session backend-generic. It should not know about Textual,
  OS dialogs, or editor UI. Frontends choose files; nodes receive portable file
  references or session-managed handles through execution context.
- Treat files as a first-class input family during the node overhaul. Nodes can
  accept a selected file path/resource and perform validation before execution.
  Users should see files by their normal names/paths in config; actual open
  handles and access continuity are runtime concerns.
- Consider long-lived listening resources later: keyboard triggers, folders,
  sockets, or other automation inputs. Keep this opt-in and lightweight so idle
  workflows do not hold unnecessary resources.
- Add path-field affordances in config UI: when focus is on a schema field that
  declares a file/path picker hint, show a short placeholder such as
  `choose file` until the user overrides it. The exact key is not final; avoid
  committing to `I` or `X` until the key map is reviewed.
- Introduce hidden helper nodes only as portable workflow structure, not
  frontend-only magic. A visible node may own an internal input-configuration
  helper such as a memory-bank mux, but save files and validation must make the
  helper relationship inspectable and deterministic.
- Support at least two input mux styles:
  - non-gating mux: gathers configured memory/transient inputs when available;
  - gating mux: waits until all configured inputs have updated before allowing
    the visible node to run.
- Let visible nodes expose simple options that configure helper behavior, such
  as `wait for all inputs before running`, while the detailed helper UI can open
  as an "Input Configuration" view.
- Validation must understand hidden helpers so errors point back to the visible
  node and the specific helper setting that caused the problem.
- Execution views should be able to reveal hidden helper activity when debugging,
  but the editor should default to the simpler visible node graph.

## Near-Term Project — Typed Vault Entries and AI Session Handles

Architecture finalized 2026-06-11. Backend foundation landed 2026-06-13.

**Typed vault entries.** `MemoryBank` (the Vault) gains a `type` field on
every entry. Types at minimum: `string`, `number`, `boolean`, `file`,
`ai_session`. Existing `string`/`number`/`boolean` entries remain pure JSON
values — behavior unchanged. `file` and `ai_session` entries store the type
tag plus a string reference key; the actual Python handle (file object or AI
provider session) lives in `RunSession` and is retrieved by calling
`context.run_session.get_resource(ref_key)`.

From the user's perspective the type is invisible; they see `filename (file)`
or `chat_name (ai_session)` in the Vault dropdown.

**Input dropdown type filtering.** Config dropdowns that select a Vault source
filter by declared input type. An input that accepts `file` shows only `file`
entries; an LLM continuation input shows only `ai_session` entries. This
prevents type mismatches and keeps the Vault navigable as it grows.

**AI session as config-driven output on LLM nodes.** There is no separate Chat
Session Node. Any LLM node can opt into session persistence via a config
checkbox ("keep active AI session") and a user-supplied session key. When
checked and the node executes:
- A `(type: ai_session, ref_key: <session_key>)` entry is written to the Vault.
- The session handle (provider client + message history) is registered in
  `RunSession` under that key.

Downstream LLM nodes that select the same Vault key append their turn to the
existing history. The first node with a given key starts the session; all
subsequent nodes continue it. Message history lives in the session object in
`RunSession`, not in `MemoryBank`. `MemoryBank` holds only the type tag and
reference key.

**Validator error/warning split.** Applies uniformly to all typed vault
references (string, number, file, ai_session):
- Error: no node in the workflow declares the vault key at all. Structurally
  impossible at runtime. Blocks the workflow.
- Warning: a node declares the key but lives on a parallel branch where
  execution order cannot be guaranteed. Recommend a Wait Until node or branch
  merge before the key is read or written.

The validator must not infer timing from node count, node type, or branch
depth. Static analysis cannot know which branch is slower. Warning plus
Wait Until guidance is the correct ceiling.

**Done (2026-06-13):**
- `MemoryBank.store_persistent` accepts `type_tag`; `read_persistent_by_type`
  filters vault by tag; state snapshot includes type tags; backward compatible.
- `RunSession` multi-turn chat session API: `get_or_create_chat_session`,
  `append_chat_message`, `get_chat_history` (deep copy), `close_all` clears.
- Validator: ai_session type mismatch warning; parallel-branch vault race
  warning (backward BFS, error/warning split per design spec); `use_chat_session`
  without `session_key` warning.

**Done (2026-07-04, Chat Completion real-execution build):**
- "Keep active AI session" checkbox and session key field on
  `chat_completion_node` (schema-driven; `session_key` gated on the checkbox).
- Vault write path for `ai_session`-typed entries on successful execution:
  `store_persistent(session_key, {"type": "ai_session", "ref_key": ...},
  type_tag="ai_session")`; history lives in `RunSession` only.
- Node-local `ai_session` continuation dropdown: string fields declaring a
  `vault_type` schema key render as a key dropdown (persisted entries of that
  tag + session keys declared in the current workflow).

**Done (2026-07-07, config UI redesign):**
- General type-filtered Vault source dropdowns across all standard-model
  inputs (Track B Phase 4b, `IO_CONTRACT_UI_DESIGN.md` §3): every
  `<port>_vault_key` field renders as a dropdown filtered by the port's data
  type, hidden unless the Vault source is selected. Untagged legacy entries
  satisfy `string`; declared workflow writers are included pre-run. The
  validator derives vault declarations from standard-model config
  (`vault_write_key`, `session_key`, `<port>_vault_key`,
  `continue_session_key`) so existence/mismatch/race checks no longer depend
  on the retired membank UI.

## Completed Project — Secrets Module (UI Integration)

Backend done (2026-06-13): `backend/secrets_manager.py` is a plain-text JSON
store wired through `MasterState → Supervisor → NodeContext`. Nodes call
`context.get_secret(key_name)`. The validator checks config schema fields
marked `"secret": True` (empty required key = error; key absent from store =
warning; no manager = skip check). Designed for encryption as a one-module
upgrade.

Done (2026-06-13, Headless Plan H3):
- `"secret": True` added to API-key config fields: `api_key_secret` on
  `chat_completion_node`, `embedding_node`, `image_generation_node`;
  `auth_token_secret` on `http_request_node` (which sends a Bearer header via
  `context.get_secret()` when set). Helper spec carries the field.
- `SecretsManager` constructed in `main.py` and threaded through `MasterState`
  (runtime) and `App` → `EditorScreen.action_validate_workflow`, so editor
  validation surfaces missing-key warnings live. Covered by
  `test_validator_secrets.py`.

Done (2026-06-25):
- `SettingsScreen` is now a numbered two-tab options modal: `1 - General` and
  `2 - Secrets`.
- The Secrets tab supports adding/updating stored key/value pairs, clearing the
  draft fields, listing saved key names, and deleting the selected key after a
  confirmation popup.
- Node config fields marked `"secret": True` render as key-name dropdowns when
  a `SecretsManager` is available, including current legacy values not yet in
  the store.

Remaining future work:
- Replace plain-text JSON with at-rest encryption inside
  `SecretsManager._ensure_loaded` / `_save` without touching nodes or wiring.

## Later Project — Unified Toast / Alert System

The project has `frontend/notifications.py` and frontend screens route common
notifications through it. Add richer toast behavior on top of that helper.

Recommended cleanup:

- Add a frontend alert helper with standard severities, duration defaults, and
  copy conventions.
- Route common actions through named helpers: saved, loaded, validation passed,
  missing selection, destructive action canceled, destructive action completed,
  run started/stopped, import/export failed.
- Add de-duplication for repeated keyboard mistakes such as "No node selected".
- Keep the helper frontend-only; backend services should continue publishing
  structured events, not UI copy.

## Later Project — Backend LLM Chat Session Persistence

Goal: allow a workflow to maintain an active LLM chat session across multiple
node visits, preserving message history so the model retains context between
calls within a run.

Use case: workflows that make several incremental calls to the same LLM for
iterative tasks — refining a document, multi-step reasoning, or accumulating
a conversation — benefit from the model seeing prior turns rather than treating
each node call as a fresh prompt.

Design direction:

- Session handles should live in `RunSession` alongside file handles. A chat
  session is a per-run resource: created on first use, reused by later nodes
  in the same run, and released on run completion.
- Nodes opt into session reuse via a config flag (e.g., `use_chat_session: true`
  and a `session_key` that names the session within the run). Nodes without
  this flag behave as stateless single-call LLM nodes.
- Message history is stored in the session object in `RunSession`, not in
  `MemoryBank`. `MemoryBank` holds the final outputs; the chat session holds the
  intermediate turn history that the LLM provider needs.
- Multiple nodes using the same `session_key` in a run share one history.
  Nodes with different keys maintain independent sessions.
- The validator should warn if a node declares `use_chat_session: true` but
  `RunSession` is not available in the execution context.
- Keep the LLM provider client backend-only. Frontend nodes declare the session
  intent through metadata; the backend resolves the provider and manages
  the connection.

## Planned Project — Backend Execution & Edit-Time Performance

Context: a backend execution-overhead audit (2026-06-13, see `SESSION_LOG.md`)
measured per-node cost over the real Supervisor/MasterState/EventBus/MemoryBank
stack at ~15 us/node and linear — small relative to real node I/O, so a C
rewrite of the execution manager is not warranted. Two O(n^2) hot spots were
found and fixed (the `MEMORY_UPDATE` full-store snapshot and the per-mutation
workflow-cache deepcopy). The items below are the remaining, lower-leverage
optimizations from that audit, deferred so they can be reevaluated as workflows
grow and the save format finalizes.

**Guiding constraints (must hold for any item here):**

- Preserve concurrent async-branch execution (one cooperative event loop).
- Preserve all node / branch / merge / WaitUntil / recovery / breakpoint
  semantics and the live Memory Viewer + dead-drop preview.
- Any precomputed/derived data stays regenerable from `connections`/config (the
  source of truth) and is validated on load — never authoritative.

**Deferred items (priority order):**

1. **Node-instance caching ("cache repeated nodes").** `WorkflowMap
   .get_node_instance()` builds a fresh `Node` and copies config on every visit;
   loops/cycles re-instantiate each iteration. Cache instances keyed by
   `node_id`; invalidate on config/alias/delete, clear on load/create/switch.
   Safe — nodes are verified stateless (no per-visit mutable `self` state), so
   caching by `node_id` (not by type) never reuses across differing configs.
   Optional follow-ons: drop the per-build `dict(config)` copy (config is
   read-only during a run); and, given the unfinalized save format, store config
   as a shared base + per-node override diff to cut redundant-data footprint for
   many similar nodes (keep a plain-dict accessor so UI/validator/save readers
   are unaffected).

2. **Edit-time execution index in the save file.** Extend the existing derived
   `input_sources` mechanism (`SaveManager` already writes it) into a persisted
   per-node index: input resolution `{input_port -> (source_node_id,
   source_port)}` and output routing `{output_port -> target_node_id}`, plus a
   structure hash. Execution (`Supervisor._prepare_inputs`,
   `WorkflowMap.find_next_node_id`) would do O(1) lookups instead of scanning
   connection lists; regenerated on load if absent or hash-mismatched. Graph
   lookups are currently flat in benchmarks, so this is a structural enabler for
   future efficiency algorithms more than a raw-speed win. The save format is
   not finalized, so the index can be a first-class top-level section.

3. **Per-node allocation / overhead trims.** `Supervisor._execute_node`
   allocates 5 closures + a `NodeContext` + `_NodeResult` per node; reuse a
   per-supervisor signal sink and a mutable context. Fetch the node record once
   per step (the breakpoint check and instance lookup currently both read it).
   `EventBus.publish` copies its subscriber list on every publish; snapshot only
   on subscribe/unsubscribe instead.

4. **Superseded 2026-10-11** by the WaitRegistry in [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md) step 1b.
   **Conditional completion-notify.** `MasterState.mark_node_completed` acquires
   an `asyncio.Condition` and calls `notify_all()` on every node completion even
   when no WaitUntil node exists. Skip the lock/notify when there are zero wait
   targets; preserve WaitUntil and the separate merge barrier.

**Considered and not pursued — transient-output eviction.** Freeing each node's
transient output once its consumers have read it ("don't keep outputs in
memory") is, after the `MEMORY_UPDATE` fix, no longer needed for speed — it is a
memory-footprint optimization only. It is also unsafe without cycle-aware
refcounting (re-visited nodes in loops re-read upstream outputs; fan-out/merge
creates late reads) and would change the live Memory Viewer, which shows the
full transient store. Revisit only if run memory footprint becomes a real
constraint, and gate any implementation behind a config flag.

## Execution branch inspection proposal

Preserved from the 2026-10-06 branch UI proposal. This is future design, not
implemented bindings or approved new scope. Owner direction is branch-level
inspection with A/D, stable selection/scroll and output summaries; the detailed
labels, layout, key change and budgets below are recommendations to review.
The current implementation contract is in [Architecture](ARCHITECTURE.md).

### Branch navigation

Use `app.execution_state.branches` and its stable insertion order. Select the
first registered root initially. Labels are `Root`, `Root 2` for additional
roots, and `Branch N` for child supervisors, with child numbers assigned once
in registration order. Show parent label, depth, start-node alias and a shortened
branch ID in details. Do not infer graph port names from supervisor IDs.

A/left selects the previous runtime branch; D/right selects the next; wrap at
both ends. Include ended branches. With zero branches show “Waiting for branch
registration”; with one branch cycling is a no-op. New registrations append
without changing the selection. A branch completing never selects its parent
or sibling automatically. A header shows `Branch 2 of 5`, state, parent and
visited-node count; it does not need a horizontally scrolling tab strip.

Navigation is owned by ExecutionScreen: `selected_branch_id` and, per branch,
`selected_row_key`, list scroll offset, detail scroll offset, and `follow_live`.
Reset navigation on a new run or workflow replacement, preserve it through
modal resume and resizing. Restore selection before scroll after layout, clamp
scroll after resize, and ignore superseded asynchronous list rebuilds.

### Rows describe actual execution

Use one row per visit in ascending visit_index. Identity is
`(branch_id, visit_index)`, not node_id. Repeated execution of the same node
produces separate rows. Use the visit's latest attempt status and total visit
seconds; details list every attempt and its own status/timing. Attempt 0 is
shown as setup failure where present. A successful retry reads `done · attempt
2`, while the failed first attempt remains in details.

`node_statuses(branch_id)` remains useful for branch-local aggregate badges,
but must not supply every visit row: it describes the latest visit of a node.
Never use global `app.node_statuses` or global timing totals for these rows.

At most one additional `Next: alias [not started]` row appears when branch
position has node_phase queued and no corresponding active visit. Its key is
`(branch_id, "queued", node_id)`; replace it with the actual visit on entry.
Follow mode transfers selection to that visit. Inspect mode keeps its prior
visit selected, or transfers a selected queued row to its replacement.
No speculative walk through conditional/fork/merge paths. Parent visits are
not copied into children; provenance points back to the parent. Disconnected
and never-selected graph nodes do not appear in a branch's visit list.
Missing graph metadata falls back to node ID without dropping history.

W/S and up/down move rows; PageUp/PageDown scroll pages, Home selects the first
row, End selects the newest row and resumes follow mode. Initial selection
follows the current visit. Manual movement or mouse selection disables follow;
F toggles it. Each branch remembers its own follow setting. Inspect mode never
jumps when visits append or timings/status change. Only the selected branch
updates visible cards; keyed reconciliation preserves mounted rows.

**Keyboard conflict:** current execution S stops the workflow. Proposed design
moves stop to X, makes W/S navigation consistent with the editor, and updates
bindings, on_key, help and footer together. P remains pause/resume, M opens
Vault, O opens existing run output, E opens errors, Esc/Ctrl+Q preserve their
existing stop-and-editor behavior. The stop key change must be visibly called
out in the delivered UI. Do not bind S to both actions.

### Outcomes and branch state

Keep the established node glyphs: executing, success, error and waiting for
input. Keep explicit [skipped]/[stopped] labels. A branch's ended state must
not recolor all its visit rows as successful. Branch header and node outcomes
are separate; use state and stop_requested without inventing a success count
from supervisor termination.

Paused branch headers use the supervisor's confirmed state. While global pause
is requested and branches still run, show “Pause requested” in the run header.
Queued breakpoint nodes stay not started. Running merge/WaitUntil visits stay
running; details may say “Coordination node executing”, but must not claim a
confirmed barrier wait because the existing feed has no barrier-enter/exit
facts. New pause/barrier glyphs are unnecessary for this version.

### Layout and output scope

At 100+ columns show a visit list on the left and selected-visit details on the
right. At narrower widths stack the list above a bounded details panel. Keep
run header, branch header and footer outside scrolling regions. The visit list
gets remaining height; details scroll independently with Tab to focus and
standard arrow/page controls. Branch A/D remain screen commands. Keep at least
five visible visit rows at a 60x24 terminal; short terminals prioritize the list
and compact details. Escape from detail focus retains existing screen behavior.

Example wide layout (illustrative text, not a rendered implementation):

```text
Workflow: Example [RUNNING]
< Branch 2 of 3 > Branch 1 | parent Root | depth 1
Visits                          Selected visit #3: Text Output
  1 Start        done  0.01s     Attempt 1: done 0.02s
  2 Transform    done  0.04s     Dead-drop payloads
> 3 Text Output  done  0.02s       default: text (120 chars) “Result...”
  4 Next: Sleep  not started    Branch summary: 3 visits; 1 preview
A/D branch | W/S visit | F follow | P pause | X stop | O run output
```

Details describe the selected visit and attempt, including produced dead-drop
ports. A compact branch summary shows visit/outcome counts and preview counts
for that branch; it does not concatenate every value. Vault remains shared
run state accessible through M and is never labeled branch-owned. O continues
to open run-wide durable output records, explicitly titled “Run output”.

### Preview attribution and bounded retention

Existing OutputManager stores run/node/value records; MasterState finalization
rebuilds them from shared output_log. These are not an attribution source.
Do not guess a branch from node ID, timestamps or the last active supervisor,
and do not inspect shared transient memory to reconstruct older visit values.

Introduce a separate opt-in observational preview feed, independent of
NODE_EXECUTION_UPDATE and durable output persistence. Every preview identifies
run_id, branch_id, node_id, visit_index, attempt_index, port_name and kind
(`dead_drop` initially). Capture from the successful attempt's result.payload
`data` immediately after execute returns, before any awaited handoff or reuse;
the current _handle_payload stores data before terminate_branch returns,
but preview capture must still preserve attempt identity and success semantics. Observe without modifying the result, routing or Vault.
Exclude routing control entries such as _route_via_port. Failed/cancelled
attempts have no success preview. Retry previews are scoped to their attempt.

This feed describes successful reported port data, not every side effect or
output_log write. Durable output-node records remain run-wide. A later explicit
output-record attribution hook may add an `output_record` kind; it needs real
execution identity at write time and must preserve legacy finalization behavior.
Do not put an unattributed durable record into a branch summary.

The backend emits only bounded JSON-safe descriptors: type, known safe size,
short preview text, truncation/omission reason and identity. Never emit payload
objects, resource handles, secret configuration or inputs. No arbitrary repr,
str, iteration, serializer or resource dereference. Restrict formatting to
built-in primitive values and shallow built-in containers. Binary data shows
byte count; resources/custom objects show an opaque type descriptor, no open,
read, network fetch, thumbnail creation or copying. Escape terminal controls
and render as plain text. Text outputs may themselves contain sensitive user
data, so previews are off by default; enabling affects future attempts only.
Disabling clears retained previews immediately and suppresses later capture.

Proposed configurable ceilings: 512 characters of preview text per port,
8 ports per attempt, 4 KiB serialized descriptor budget per attempt, 256 KiB
per run and 200 retained attempt-preview groups, whichever is reached first.
Bound inspection work too: depth 2 and 16 inspected items total per attempt;
do not serialize a whole value before truncation. If a group exceeds budget,
retain omission metadata within the same budget. Evict oldest groups; no duplicate
branch payload cache. Missing summary states distinguish disabled, not captured,
no reported ports, truncated and evicted. Counts are capped/aggregate metadata,
not an unbounded index of omitted records. Reset at the next run/replacement;
retain through natural FINISHED/ERROR while the display run remains available.

Scope limitation: current App clears execution state on backend IDLE, including
explicit workflow stop. This version preserves that reset and stale-run guard;
branch-local stopped attempts remain inspectable while their run is retained.
Post-workflow-stop inspection requires a separate snapshot/retirement decision.
Do not accidentally resurrect the stopped run to satisfy the new layout.

### Delivery stages and acceptance

1. Implement branch/visit list and navigation using existing facts. Use an
   execution-specific list with visit-keyed rows; NodeList.refresh_nodes is
   node-ID keyed and cannot represent repeats. Reuse NodeCard appearance and
   shared navigation helpers without changing editor row behavior. Add details
   for attempts/timing and honest unavailable-preview messages.
2. Add opt-in bounded preview descriptors and an App-owned reducer/cache.
   Keep subscriptions session-scoped and apply current run/retired-run guards.
   Formatter failures are contained and cannot alter node execution/recovery.
3. Wire selected-visit previews and branch counts, then verify live at multiple
   terminal widths. Keep this work in a separate feature PR from PR #28.

Tests should cover wrap/zero/one/many branches, nested provenance, retained ended
branches, independent shared-node visits, repeated visits and retries, queued
row replacement, per-branch scroll/selection/follow, modal resume and resize.
Verify S navigates without stopping and X stops, plus existing recovery keys.
Mounted checks at 60/100/140 columns must assert selection and scroll stability
while events arrive, narrow details access and terminal-control escaping.

Preview tests must cover overwritten shared ports, successful terminate-branch
payloads, stale runs, disabled/enable/disable transitions, resource/custom-object
formatting without invoking methods, oversized/deep values, all retention limits
and explicit evicted/unavailable states. Existing run-output persistence and
run-output contracts must remain intact; use Current State for the test baseline. Before runtime delivery run focused
execution tests, full tests/, compileall and git diff --check. Design-only
verification checks links and whitespace; runtime delivery needs the tests above.

## Native file/window verification (FO7)

Preserved from File Output FO7. Native results remain an owner verification gate;
[Current State](CURRENT_STATE.md) owns its status. Check the actual Windows
machine and record host, monitors, apps, results and degraded behavior:

1. Single monitor: Markdown file with Right of AOTN; verify position and size.
2. Multiple/mixed-resolution monitors: image with Other monitor; verify placement.
3. Existing single-process app/window (for example a workbook): discovery must
   not steal an unrelated pre-existing window; inspect fallback behavior.
4. Close when run ends on/off, and Window Control close during a run.
5. Slow launch/discovery timeout: warning and bounded wait, not a hang.
6. Repeat placement in Windows Terminal and legacy conhost; terminal-window
   identification differs. Inspect fallback when the visible terminal is unknown.
7. Write/open immediately before User Text Input: verify focus can return to
   the prompt; record whether a refocus option is needed rather than guessing.

Keep HWND reuse, ambiguous discovery, application window reuse and parent-process
handle resolution in the review. Deferred: virtual desktops, native macOS/Linux
placement adapters, line-number insertion, rich terminal image previews and
cross-run window adoption. Keep pywin32 optional; no speculative adapter stubs.
File/window reasoning D1–D12 now lives in Node Standards.

## Configuration and inspection follow-ups preserved from audits

These are directions/limitations to recheck against code before implementation,
not instructions to repeat completed numeric, Random Number or Echo fixes:

- Audit legacy controls by actual runtime capability. Do not implement fake
  Vault behavior to justify a generic checkbox; retain unrelated saved config.
- Continue compact/applicable section composition and conformance across source,
  routing and mode variants, using production CSS at multiple widths.
- Clarify simulated AI capabilities and inert secret controls; do not advertise
  a real provider call merely because a schema has a secret field.
- Explain unsupported window actions at configuration/preflight boundaries.
- Viewer requests use a FIFO run-scoped queue; search/history, queue bounds and
  content snapshots are separate product decisions. Large viewer reads and
  synchronous writes merit measured performance work, not presumed fixes.
- A reported user/host path prefix and execution-screen F-key issue were not
  reproduced by this docs work. Preserve them as reports requiring evidence.
- Lazy loading for large forms should show usable content early and queue
  Save/Close until loading completes; this is a proposal needing UI review.
- Keep live output-display node ambitions distinct from the existing run output
  log: user-facing interactive outputs deserve clear capability and lifecycle
  contracts. Reusable subworkflow/node libraries follow child-run contracts,
  not hidden state in a parent supervisor.
