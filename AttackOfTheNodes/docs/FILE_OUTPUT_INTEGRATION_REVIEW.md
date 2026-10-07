# File Output integration review — 2026-10-06

**Integration follow-up (2026-10-06):** File Output is now merged locally with
pending session fixes. Config preservation, critical input sizing, Chat zero
temperature, ambiguous window discovery, launch responsiveness, viewer request
queuing, Window Control's unsupported toggle and writer-path warnings are fixed.
Read [CONFIG_UI_BUILD_PLAN.md](CONFIG_UI_BUILD_PLAN.md) for remaining findings and
[current integrated evidence](audits/integrated_2026_10_06/README.md). Original
findings/counts below describe the earlier inspection, not the latest tree.

## Recommendation

Retain this work and incorporate it into the configuration build plan. Its file
writing, formatting, typed references and resource lifecycle fit the current
architecture. Do not treat the complete Windows feature as verified or merge it
blindly. Resolve the findings below, preserve the pending runtime fixes, then
refresh the node audit against the integrated inventory.

This is a review, not a feature merge or application redesign. Existing dirty
application files and the recovery-only OneDrive checkout were preserved.

## Exact baseline and method

- Authoritative root: `/home/makin/src/node_workflow`.
- Current branch: `codex/wait-until-vault-fix`, HEAD `7161ef2c79c6ac568876b4d9d78d76a7b19b815e`.
- Origin fetched during this review; current HEAD equals `origin/main`.
- Reviewed feature: `origin/claude/file-output-pywin32-32tnv9`,
  `0a19718dd1c6118df9c76f807f6c4159e8cbe92b`.
- Common ancestor: `af04c5f06586795acf49f4e41a72a05592f8abf8`;
  nine commits unique to each branch. File Output is not already in main.
- Working tree remains dirty with the prior runtime, Wait Until, tests and
  documentation work, plus audit/review artifacts. No stash/reset/commit made.
- `git merge-tree --write-tree HEAD <feature>` found one committed-tree conflict:
  `docs/SESSION_LOG.md`. It did not alter the index or working files.
- A separate source overlay three-way merged changed Python files against the
  actual dirty working copies. No Python merge conflicts. It imported the combined
  sources in memory and placed test sources in a temporary directory; it did not
  create or switch to another checkout. Production CSS came from this checkout.
- This overlay is compatibility evidence, not a full installed integration build.
  Non-Python docs/specs and Windows launchers were not installed or merged.

Paths below are relative to `AttackOfTheNodes/`; feature-only line references
refer to the feature commit above, not to nonexistent files in the current tree.

## How the work fits

| Work | Fit with current implementation |
|---|---|
| File Write (`file_output_node`) | Replaces the nonfunctional File Instance example. Resolves separate content/path sources, writes text or Base64-decoded bytes, supports overwrite/append/unique names, emits a typed file reference and can write that reference to the Vault. |
| Text Transform: Markdown format | Extends the existing transform node; formatting remains separate from file writing. `wrap_width=0` explicitly keeps line breaks. Correct single-purpose separation. |
| File Viewer (`file_view_node`) | Resolves a file and emits a JSON event through NodeContext/Supervisor/EventBus. Frontend owns reading/rendering the viewer. Headless execution remains valid. |
| Window Control (`window_control_node`) | Resolves a window through file identity in RunSession. Missing/disappeared windows warn and continue, as deliberately designed. |
| RunSession | Reuses existing file handles, resources and close hooks. No competing lifecycle manager; current chat-session support survives the source merge. |
| Wait Until and pending runtime fixes | No reason to change Wait Until. File Write publishes the Vault reference before signaling done; the pending Supervisor ordering publishes transient results before completion unblocks waiters. Wait Until still waits for all targets and forwards its own incoming dead-drop unchanged. Downstream file nodes explicitly choose Vault when needed. |
| Validation | Adds source-conditional path/secret checks. This avoids requiring hidden configured fields when an input uses Vault/upstream. Useful shared improvement. |
| Backend/frontend boundary | Nodes do not import the frontend; viewer requests carry identifiers/path/render hints. Window adapter has no Textual or MasterState dependency. Optional pywin32 remains platform guarded. |

Example supported composition: Text Transform → File Write → File Viewer.
For a parallel workflow, File Write can publish `report_file` to the Vault;
Wait Until waits for the writer, then File Viewer explicitly reads `report_file`.
Waiting itself does not transfer that file reference into the waiting branch.

**Existing File Reader is not upgraded by this branch.** Its execute method still
reads only `config.file_path` (`backend/nodes/file_reader_node.py:27`). Connecting
a typed file reference does not make it read that file. Extending it would be a
separate, explicitly scoped capability change, not a UI repair.

## UI coverage and implications

Combined NodeFactory inventory: **37 registered types**, replacing one demo with
three functional nodes. This changes the earlier 35-type audit baseline. The
existing internal tombstone exclusion remains intentional.

Mounted all three incoming configuration screens with production CSS at
60, 100 and 140 columns × 24 rows: nine mounts, each visiting all four tabs.
Complete widget/label/value/region inventories are in
[audits/file_output_2026_10_06/mounted.json](audits/file_output_2026_10_06/mounted.json).
Feature UI smoke tests additionally check metadata-driven visibility.
This review does **not** claim a full per-field keyboard, save/reopen and every
conditional-state audit of these new nodes; extend the main audit after integration.

| Node | Actual current controls | Proposed layout treatment |
|---|---|---|
| File Write | Source: alias, summary, incoming preview, content/path source selectors and conditional typed Vault keys. Parameters: conditional content/path, write mode, Base64, open-after-write and conditional placement/close. Payloads: downstream name/description, forwarding, Vault disable/key/description, terminate. Connections: summary. | Four sections can be justified here, but do not require four tabs. Keep source-dependent fields close to their selectors; group write behavior and optional window behavior. Retain genuine Vault output; explain which incoming payload forwarding preserves. Platform capability messaging is required for window controls. |
| File Viewer | Source: alias, incoming preview, source/key. Parameters: configured path when selected and render mode. Payloads: downstream name/description, forwarding, terminate. Connections: summary. No Vault output block. | Compact File/Display form plus applicable routing/connections; do not add Vault writes. Explicitly say execution continues after requesting display. |
| Window Control | Source: alias, incoming preview, upstream/Vault selector/key. Parameters: Focus/Minimize/Close. Payloads: downstream name/description and forwarding checkbox. Connections: summary. No configured source or Vault output block. | Compact target/action form and connections. Resolve redundant/unsupported forwarding semantics before exposing a toggle. Explain missing-window behavior and platform support. |
| Text Transform, Markdown variant | Adds `markdown format` operation and conditional wrap width. | Reuse shared conditional form, retain explanation of zero. Include this additional mode in the expanded audit. |

The standard-source metadata correctly prevents the legacy generic Vault blocks
on the three new nodes. That is a useful example for the shared audit fixes.
They still inherit shared four-tab composition, form sizing and save behavior;
this branch does not repair the main audit's shared layout/config-preservation
findings. Do not create bespoke screens to work around those shared defects.

## Findings to resolve before calling this complete

| ID / priority | Evidence and reproduction | User impact and treatment |
|---|---|---|
| FO-R1 / P1 | `backend/window_manager.py`, `_discover_window`: when multiple new HWNDs appear and none matches the filename, returns `next(iter(new_windows))`. Deterministic probe with `{101,202}` and no title match returned `202`. | May move, focus or close an unrelated window, including from a run-end close hook. D4 deliberately accepts imperfect discovery, but also defines unidentified windows as opened/unplaced with no registered handle. Return unknown on ambiguity; add targeted adapter tests. Single-new-window attribution remains a documented heuristic requiring live review. |
| FO-R2 / P1 | `file_output_node.py:116` calls synchronous `_open_window`; Windows discovery polls with `time.sleep(0.25)` for up to five seconds inside async node execution. | A slow launch can block the event loop, freezing TUI responsiveness and other branches. Preserve launch/discovery semantics but run blocking adapter work outside the event loop; test a concurrent heartbeat/stop request. File writing itself is also synchronous, so scope/performance limits should be explicit. |
| FO-R3 / P2 | `frontend/app.py:254–267`: `_on_file_view_requested` returns immediately whenever `_file_viewer_open` is true. Close merely clears the flag. Send requests A then B before closing A: B is discarded. | Sequential or parallel viewer nodes can report success without showing their file. Nonblocking display is deliberate; silently dropping requests is not described as a user contract. Choose queue, replace or accessible history; retain run identity and define interaction with user-input modals. |
| FO-R4 / P2 | `window_control_node.py:91` always emits resolved `raw`; it never reads `dead_drop_passthrough`, although metadata advertises `pass_through=True` and the mounted Payloads tab displays the checkbox. With Vault selected and a different upstream file, toggling it still emits the Vault value. | A control promises a change that execution never makes—the same class of issue that sparked this audit. Prefer documenting fixed reference forwarding and omitting the toggle unless preserving a different incoming payload is an intentional requirement. |
| FO-R5 / P2 | On this WSL/Linux host, `get_window_manager()` uses fallback open-only capabilities. Placement and close-at-run-end remain visible when open-after-write is selected; Window Control offers all actions. Validator warns for placement/close config, but has no corresponding Window Control action capability check. | Users can configure behavior unavailable on the actual runtime host. Keep portable saved configuration but show clear capability explanations and consistent preflight warnings. Running in WSL does not activate the Windows pywin32 adapter. |
| FO-R6 / P2 | `backend/validator.py:180–215` treats every visible `path_hint=file` as an expected existing file. A configured new File Write destination emits a missing-file warning even though creating it is normal. | Routine valid writer workflows receive misleading warnings. Add shared read-vs-write path intent; avoid node-type conditionals or disabling path validation globally. |

Other integration considerations:

- File Viewer uses Escape/Q/Ctrl+Q and ordinary Textual scrolling, not the shared
  W/S command navigation mixin (`frontend/screens/file_viewer.py:23`). Verify and
  align viewer keyboard behavior separately from its configuration screen.
- The branch removes the old `example_file_instance_node` registry entry and
  tests. Deliberate demo retirement is sensible; inventory saved examples before
  integration and document recovery for workflows containing it. Do not rename
  those nodes to File Write automatically: their ports/behavior differ.
- `Open after write` describes “one window per iteration,” but applications can
  reuse an existing window/tab. Say “opens the file each iteration” instead.
- Existing shared source/forwarding labels use “payload” inconsistently with
  “dead-drop payload.” Fix terminology in shared helpers/specs together.
- The File Output plan header says “planned — no phase started,” while its checked
  FO1–FO6 and feature session entries show implementation. This is stale status,
  not evidence that the code is absent. FO7 Windows live verification remains open.

## Ordered integration/build-plan input

1. Preserve and review the current dirty runtime/Wait Until work as its own
   coherent change, including the audit's production-CSS sizing issue. Do not
   replace Supervisor wholesale with the older feature version.
2. Reconcile the File Output feature with current main and retained local fixes.
   Preserve both session histories and the updated capability-based layout policy.
   Keep demo retirement explicit. Do not overwrite current audit/handoff docs with
   the feature branch's older status descriptions.
3. Resolve FO-R1/R2 and viewer request handling; resolve misleading UI promises
   through metadata/shared helpers. Keep execution changes narrowly tied to defects.
4. Extend the audit matrix to the actual integrated selector and registry, all
   three nodes, Text Transform Markdown mode and conditional window/source states.
   Then finalize the small shared-UI implementation stages from the main audit.
5. Verify an actual integrated tree with the full suite, production-CSS keyboard
   and save/cancel checks at all three widths, and cross-branch File Write → Wait
   Until → explicit Vault reader scenarios. Overlay success is not that final gate.
6. Perform the existing FO7 Windows protocol before claiming placement/control
   complete: reused application windows, slow launch, unrelated windows, monitor
   layouts, terminal hosts, close hooks and focus interaction with user input.

Owner input genuinely needed: the display policy for multiple file-view requests;
whether existing File Reader should gain typed-reference input as a later feature;
and a live Windows verification environment. The recorded decisions to use typed
references, RunSession, optional pywin32 and nonblocking viewer events need not be
reopened.

## Verification

See [the reproducible source-overlay harness](audits/file_output_2026_10_06/check_integration.py).
Final result is recorded below and in SESSION_LOG.md. Early harness attempts used
the wrong pytest config, then lacked the temporary tests' relative CSS path;
those setup failures are not product regressions. The corrected harness uses
`pytest.ini` and links tests to the authoritative production stylesheet.

- Corrected overlay run: **304 passed in 59.16s**, exit 0. Includes feature-changed
  test modules merged against local copies, plus both pending Wait Until suites.
- **9 production-CSS configuration mounts**, all three new nodes × three widths;
  all four tabs inventoried. Combined registry **37**.
- Ambiguous-window deterministic probe returned HWND **202** with no title match,
  confirming FO-R1 without opening or controlling any OS window.
- `git diff --check`: passed. No Windows live test, full integrated-tree suite,
  exhaustive new-node save/reopen/keyboard audit or launcher execution claimed.
- Corrected test output: [verification.txt](audits/file_output_2026_10_06/verification.txt).
