# Payload routing and File I/O build plan

Status: implemented locally, 2026-10-07; final verification is recorded in
[audit evidence](audits/payload_file_io_2026_10_07/README.md) and SESSION_LOG.
The stages below retain the original acceptance contract and investigation
history. Line-number insertion is deferred; native Windows/live terminal FO7
and the unreproduced user/host path prefix still require live confirmation.

## Implemented contract and migration

- P0/P1: previews use the immediate captured output while tracing the correct
  forwarded input for origin/type. Saved unavailable sources are labeled;
  incompatible, absent and disabled downstream sources are pruned. Real legacy
  text writers and standard declarations supply types before execution.
- P0a: path classification distinguishes drives, UNC, extended paths and WSL
  shares; drive-relative and malformed converter results fail explicitly.
  Quoted Copy as path values remain in configuration; filesystem normalization
  occurs at use time. Slash direction alone cannot identify the runtime OS.
- P2/P2a: Start publishes real typed Vault text; Text Output selects Upstream or
  Vault. File Reader reads configured paths or typed references and publishes
  string contents downstream and/or to Vault independently.
- P3/P4: Writer supports Overwrite, Append, Prepend and Create unique, with
  opt-in literal `\n` and `/n` interpretation. File Manager opens configured
  rows in order, selects one reference downstream and requires Vault keys for
  other rows. Forwarding changes only the downstream payload. Batch validation
  precedes publication; references retain same-file identity.
- P5/P6: file nodes continue; End terminates explicitly; Text Output continues when connected (2026-10-08 compatibility correction). Merge
  carries the participating home payload or selected sibling payload, allocates
  only selected branches and reports its fixed five-input capacity.
- Shared forms support object lists, configured-field aliases and zero-input
  output controls. Generic legacy Vault controls appear only where implemented.

`backend/config_migrations.py` runs on workflow load, config update and node
creation. Retired File Manager/Writer `terminate_branch` values are archived
under `_config_migrations.file_io_continuation_v1`; insert End for an explicit terminal route. An unconnected Text Output ends naturally. A single legacy Text Output Vault selection becomes its
source; multiple selections require choosing one (blank key, preflight error).
Explicit new source settings win. A single legacy Start declaration upgrades
to standard Vault routing; multiple legacy writes remain supported at runtime.
Old Reader configs default to Configured. Unknown fields are preserved, and
nested defaults are copied independently between node instances.

File Manager displays/opens files and supplies file references; File Reader
copies a file's contents into a typed text payload. Keep these separate purposes.
Retain `file_view_node`, `FILE_VIEW_REQUESTED` and `FileViewerScreen` as internal
identifiers; existing saved aliases are preserved. Extend the existing
`file_reader_node` rather than registering a duplicate Reader node.

Authoritative checkout: `/home/makin/src/node_workflow`, branch `main`, HEAD
`1211e68`; origin/main synchronized. The current tree also contains earlier
uncommitted fixes, including deleted Vault-source filtering. Preserve them and
both unrelated untracked files. OneDrive is recovery-only. Last completed
application baseline: **686 tests passed**, recorded in SESSION_LOG; this is
historical verification, not verification of this new plan's features.

This is the focused continuation of CONFIG_UI_BUILD_PLAN stages 1/4. It does
not start the execution-screen redesign or reopen completed runtime work.

## Original findings and investigation limits (before implementation)

| Report | Evidence at planning baseline | Planned follow-up |
|---|---|---|
| Reveal upstream misrepresents File Manager forwarding | `frontend/node_io_display.py:is_pass_through_node` recognizes metadata/legacy `pass_through`, but not `dead_drop_passthrough`. Tracing follows the first connection; File Writer actually forwards Content. Incoming summaries combine traced metadata with the immediate upstream port's captured value. | Reproduce with deliberately different payloads and names; fix effective origin, type and selected input together. Do not substitute an earlier node's value for the actual forwarded output. |
| Start Vault output missing from Text Output | Start executes only `signal_done` with its greeting; it has no Vault write. Text Output reads `context.inputs['input']` and has no standard source metadata or Vault read. Legacy selection/preview registries scan `membank_outputs`, unlike standard `vault_write_key` declarations. | Make Start's offered Vault operation real and make Text Output consume the selected source; fix discovery before and after execution. |
| File Content and File Path choices too broad | File Writer's Content is declared `any`; its Vault schema is `vault_type: any`. Standard source composition prunes empty Vault lists, but does not generally prune incompatible upstream sources. | Use the canonical `string` type for text Content; share compatibility rules between previews, options and validation. |
| Multi-file Manager | Manager currently resolves one file, emits one display request and optionally writes one typed Vault key. | Extend configuration, declarations and execution together; FIFO viewer queue already exists. |
| File Reader text routing | Existing `file_reader_node` reads a configured UTF-8 file and emits contents downstream. It lacks standard typed file inputs and explicit typed Vault text output. | Add Upstream/Vault file-reference sources and downstream/Vault `string` routing while preserving configured-path saves. |
| Windows Copy as path / apparent host prefix | Owner entered `"C:\Users\makin\Documents\App_Tests\test.md"` and observed `makin@kelly:/mnt/c/Users/makin/Documents/App_Tests/test.md`. Direct read-only normalization on 2026-10-07 returns `/mnt/c/Users/makin/Documents/App_Tests/test.md`; that file exists. Current converter uses drive/UNC detection and `wslpath -u`, and does not add a user/host prefix. | P0a audits original config, emitted refs/events and rendered path separately; harden syntax/runtime classification and preserve copied config. Do not claim the host-prefix defect reproduced. |
| Writer additions | Modes currently Overwrite, Append and Create unique; text writes stringify nonstrings. | Add explicit newline handling and Prepend, retain Append as bottom insertion; defer line-number insertion. |
| Completion checkbox | Writer/Manager schema, specs and execution contain `terminate_branch`. Supervisor also uses the same signal internally for Merge. `next_node_id: None` does not itself stop traversal when a graph connection exists. | Remove the user option without deleting internal merge termination; verify designated terminal behavior and old-save policy. |
| Missing carry-forward branches | Carry-forward lives on `merge_node`. `branch_end_node` is Merge Beacon and forwards its input. `merge_input_options` enumerates eligible beacons; carry-forward then restricts entries to selected branches-to-close. Merge has five fixed input ports. | Establish which filter loses the user's branches, including the home branch and nested branches. Do not list arbitrary unfinished/downstream branches. |

These were planning-baseline code findings, not a live reproduction of every report. No screenshot
or exact failing graph was available in this request. P0 supplies deterministic
reproductions and distinguishes preview defects from actual routing defects.

## Shared behavior contract

1. Every input chooses one source through a dropdown: Upstream payload, Vault,
   and Configured where the node supports it. Text Output gets Upstream/Vault;
   its existing template and optional user prompt remain Parameters.
2. Name, description, effective data type and preview value describe the same
   payload. Forwarding follows the input actually forwarded, not the first
   connection or the node's ordinary result. Read the immediate output's
   captured value when available, even if the displayed origin is earlier.
   Missing and captured `None` must be distinguishable; do not invent a value
   before a run or resurrect a value from another run as the current result.
3. Standard `dead_drop_passthrough`, legacy forwarding and unconditional
   pass-through nodes need one frontend interpretation of backend metadata.
   Prefer declarative forwarded-input metadata, preserving legacy hints.
   Configured/Vault input resolution is separate from unchanged incoming
   forwarding: inspect actual node execution rather than guessing its meaning.
4. Use `backend/data_types.py`: text is `string`, references are `file`; do not
   introduce a second `text` spelling. Text Output can retain `any` input
   compatibility because its template formats values. File Writer text Content
   is `string`; File Path/reference consumers are `file`. Ordinary string
   payloads must not become file references just because they resemble paths.
   Configured paths retain supported Windows/WSL normalization.
5. Hide known incompatible sources for fresh configs. Do not offer Upstream
   when there is no connected, compatible payload; do not offer Vault when
   there are no eligible compatible keys. Keep old invalid selections visible
   as unavailable for repair, without including them as ordinary choices.
   Recompute choices when relevant source/mode/graph changes.
6. Unknown `any` producer types are not proof of incompatibility. Trace
   forwarding first; narrow from trustworthy contract/runtime evidence when
   possible. Otherwise label uncertainty and validate at execution. A known
   number/bool result cannot supply File Path. Sleep is a pass-through node:
   Sleep carrying a file reference remains a valid file source.
7. Vault choices include real active declarations before execution and typed
   captured entries where permitted. Retain deleted-node, self/downstream and
   duplicate-input exclusions. Shared keys remain usable if another eligible
   producer survives. Parallel references are accessible through the shared
   Vault, but consumers still need ordering/Wait Until where races matter.
8. A node's Vault result can differ from its forwarded downstream payload.
   Manager/Writer Vault results remain file references while forwarded payloads
   retain their actual type. File reference identity and same-file reuse stay
   intact; additional Vault names do not create files or versions.
9. File Reader consumes a configured file path or typed file reference and emits
   the file contents as `string` downstream and/or to Vault. Its file input and
   text output must remain distinct in every picker and preview.

## Stages and acceptance criteria

### P0 — Reproduce and freeze contracts

Integrator owns fixtures and the compatibility/routing matrix before parallel
implementation. Read NODE_STANDARDS, AGENT_START_GUIDE, NODE_HELPER and
BACKEND_FRONTEND_BOUNDARY, then the focused files in the findings table.

Create small graphs covering Start → Manager in Configured mode with forwarding
→ Text Output; two differently named inputs → forwarding Writer → consumer;
Start Vault → Text Output; string/number/file producers → File Writer inputs;
Sleep carrying string versus file; and home/sibling/nested Merge branches.
Add File Manager → Reader → Writer Content and a Reader text-Vault consumer.
Record expected immediate output versus traced origin, both before and after a
run. Exercise source values distinct from a viewer's configured file reference.
Confirm which UI control the user calls Reveal in the standard/legacy forms.

Freeze forwarding metadata, Start/Text Output config migration, unknown-type
policy, multi-file row format and terminal-node policy in the PR description
and this plan before dependent stages. Do not create fake input ports to make
Start enter the standard UI: output composition must support zero-input nodes.

### P0a — Windows copied-path compatibility and truthful path display

File owner audits `backend/file_paths.py`, `backend/file_refs.py`, File Manager,
Writer, Reader and Window Control; Frontend owner checks configuration Save,
`FILE_VIEW_REQUESTED`, `frontend/screens/file_viewer.py` and any path labels.
Start before file feature extensions; preserve earlier conversion/reuse fixes.

Use the owner's exact quoted Copy as path example as a regression fixture.
Capture pasted/configured text, normalized filesystem path, reference path/key,
event path and displayed path. A WSL process opening a Windows drive file needs
its WSL-accessible path; conversion to `/mnt/c/...` is expected, not evidence
that the file moved or the configuration was rewritten. `makin@kelly:` is not
part of that local filesystem path. Locate whether it originates in an app
label, supplied value or terminal context; do not infer the origin from its
appearance or silently strip a possible remote-path prefix.

Classify using path syntax **and** actual runtime: Windows drive-absolute paths
with either slash style, UNC/extended Windows forms, WSL share paths and native
POSIX paths. Slash direction alone is insufficient: Windows accepts forward
slashes; POSIX filenames can contain backslashes. Keep native paths native.
Under WSL, prefer `wslpath`/verified mappings over a hardcoded `/mnt/<drive>`
replacement because mount configuration may differ. On native Windows accept
Windows paths directly; on non-WSL Linux/macOS do not invent access to a Windows
drive. Report unsupported/unmounted forms clearly. Distinguish drive-relative
`C:notes.md` from absolute `C:\notes.md`; do not treat arbitrary colon-bearing
filenames as Windows drives.

Strip paired clipboard quotes and outside whitespace without rewriting embedded
spaces, Unicode, separators in filenames or case. Define support/failure policy
for UNC network paths, `\\?\` extended paths and `\\wsl.localhost\...`/`\\wsl$\...`
paths; do not promise that every network share is mounted. Retain shell-free
argument passing, converter timeouts and useful errors. No general file-URL or
SSH-path feature is implied by Copy as path support.

Preserve the entered path in saved config. Convert at validation/access
boundaries using the same helper; UI should distinguish configured path from
resolved runtime path where both are shown. Never include a shell prompt in a
file reference/event. Keep identity stable when equivalent pasted paths resolve
to the same file, without invalidating valid incoming reference/resource keys.

Acceptance: quoted/unquoted Windows drive paths with both separator styles,
spaces/Unicode, native POSIX paths, configured/Upstream/Vault inputs, native
Windows/WSL/non-WSL branches, drive-relative rejection, supported/unsupported
UNC/extended/WSL-share forms, repeated normalization, custom mounts, missing
converter/timeouts/invalid output, config Save/reopen and correct preview path.
Direct converter evidence does not close the user's reported UI symptom; verify
the complete Manager run path live and record any unobserved host-prefix source.

### P1 — Shared payload provenance, types and source availability

Frontend owner updates `frontend/node_io_display.py`, shared source composition
in `frontend/screens/node_config.py`, editor input choice and relevant form
helpers. Runtime/contract owner supplies portable metadata and reusable type
validation only where backend behavior requires it; backend must not import
the frontend or implement widget visibility.

Use one source descriptor for effective producer, forwarded input, type,
description and availability across Incoming Payload, Reveal, quick view and
Merge output descriptions. Respect output-port-specific forwarding capability,
multi-input forwarding selection, Vault branch seeds and cycle guards. Read
captured immediate output rather than guessing from upstream values.

Acceptance: forwarded string/file previews have correct origin/name/type/value;
Writer forwards Content, never File Path; forwarding on/off changes effective
type correctly; incompatible upstream options disappear; unknowns stay explicit;
deleted Vault filtering, saved invalid selections, duplicate-source safeguards,
parallel eligibility and legacy tracing continue to work.

### P2 — Start Vault output and Text Output source dropdown

Runtime/contract owner updates `backend/nodes/start_node.py` and
`backend/nodes/text_output_node.py`, helper specs and generated checks where
applicable. Frontend owner integrates their capabilities through P1 helpers.

Start emits its greeting as `string` and optionally writes it to the declared
typed Vault key. Its key is discoverable before running. Text Output resolves
either upstream or the selected Vault key before formatting; remove its legacy
Vault and Reveal Vault checkboxes in favor of standard source controls and a
preview of the selected value. Preserve label/template/prompt/output logging.

Translate meaningful old `membank_inputs`/`membank_outputs` declarations where
unambiguous; preserve unrelated config and expose ambiguous old choices for
repair. Do not let a schema promise a Vault operation that execution ignores.

Acceptance: Start's declared greeting key appears in Text Output before a run,
contains the greeting after execution, and can be selected without an upstream
connection. Only the selected source is consumed. Save/reopen and Cancel retain
correct values; user prompting still behaves as configured. No new ports.

### P2a — File Reader copies file contents to text payloads

File owner extends `backend/nodes/file_reader_node.py`, adding a matching helper
spec if needed; Frontend owner integrates it through P1 source/output helpers.
Depends on P1 and the common routing/declaration contract from P0.

Keep existing `file_reader_node` identity and input/output port ids. Add standard
source selection: a configured path, an upstream typed file reference, or a
typed file reference selected from Vault. Preserve old `file_path` configs as
Configured on migration. Resolve references through existing file helpers and
RunSession capabilities; retain copied Windows-path/quote normalization under
WSL. Reading a file must not modify it or open a viewer/window.

Emit the entire decoded file contents as `string`, not the file reference or
its path. Offer downstream transient output and an optional named typed Vault
text output independently, including Vault-only routing. The output name/key
must be discoverable as `string` before execution so it appears in File Writer
Content and compatible text consumers. Reader file-input dropdowns use `file`
eligibility and exclude text output keys. A reference passed unchanged from
File Manager selects a file; Reader's result is the text inside that file.
Do not offer unchanged-file forwarding as a substitute for reading its contents.

Preserve UTF-8 behavior, actionable errors and lifecycle-managed resources.
Empty files produce a valid empty string. Reused handles must read from the
start; reading again after Writer updates must return current contents. Failed
reads must not publish a new text result or Vault entry. Keep blocking reads
off the event loop when extending the read path; no structured parsing or
bulk/glob reading is included in this stage.

Acceptance: configured Windows/WSL paths, upstream/Vault refs from File Manager,
text equality including Unicode/newlines/empty content, all downstream/Vault
routing combinations, repeated reads, missing/directory/unreadable/invalid-UTF-8
files, save/reopen/Cancel, and reference-versus-text dropdown filtering. Test
Manager → Reader → Writer Content and Manager file Vault → Reader → text Vault
→ Text Output. Existing single-file Reader workflows remain functional.

### P3 — Text-only File Content and Writer editing modes

File owner changes `backend/nodes/io/file_output_node.py` and its helper spec;
frontend owner receives schema changes and uses shared composition.

Change text Content metadata/Vault filtering to `string`; audit File Reader and
other real text emitters so missing metadata does not defeat filtering. Preserve
the existing binary/Base64 capability with an explicit mode-specific contract,
not an accidental return to all-type text choices. Provide meaningful errors
for incompatible supplied values instead of silently stringifying file refs.

Keep Overwrite and Create unique. Display Append as adding at the bottom; add
Prepend for the top. Add an opt-in text newline interpretation setting, with
literal text preserved by default. Proposed interpretation of the owner's
`/n`: support conventional `\n` and document `/n` as an optional alias only
when interpretation is enabled. Do not use a general escape decoder that
rewrites Windows paths, backslashes or unrelated escape sequences. Never
interpret escapes in file paths or binary data. Define separator behavior at
insertion boundaries, including no accidental extra blank line.

Acceptance: multiline text, explicit escapes, literal slash/backslash strings,
empty/new files, top/bottom insertion, existing terminal newline, CRLF/LF,
Unicode, binary mode and same-file refs are covered. Reject unsupported mode
combinations before modifying a file. Validate all data before truncation.

**Deferred TODO:** insert at a given line number, with a separate typed number
input (Upstream/Vault/Configured) if needed. Define 1-based indexing, insertion
boundaries and out-of-range handling before implementation. No inert control
ships in this build.

### P4 — Multi-file Manager and multiple declared Vault references

Depends on P1 and the output-declaration contract frozen in P0. File owner
extends `backend/nodes/io/file_view_node.py`, its spec and focused tests;
frontend owner owns repeatable configuration rows and declaration discovery.

Retain the current File source as the first entry for old saves. Add configured
path rows with stable ids, explicit Vault keys, and exactly one selection for
the normal downstream file reference. Every remaining row must declare/write
its typed file reference to Vault. The selected row may also have an optional
Vault name. Paths become references during execution, not during config editing.

Proposed persisted shape: an ordered list of row objects containing id, path,
Vault key/description, plus the selected downstream row id. Reuse ordinary
repeatable-form helpers; if the generator cannot express the structure, extend
the helper contract first and record its structural UI requirement.

Discover every configured Vault key before running, not just the selected
file's key. Validate duplicate/blank required keys, duplicate ids, an absent
selection and invalid paths before publishing partial effects. Resolve and
validate all files, write required Vault entries, then emit display requests
and completion. Document failure handling; do not silently complete a partial
batch. Reuse existing FIFO display requests; maintain run-scoped queue behavior.

Forwarding still replaces only the downstream payload with unchanged incoming
data; it does not suppress viewing files or required Vault references. The
selected file supplies the normal result only when forwarding is off. Preserve
same-file identities and Windows/WSL path handling. Parallel consumers still
require execution ordering; shared storage alone does not remove a race.

Acceptance: one-file old save works; several files are requested in order;
exactly one dead-drop result is selected; all other typed keys appear in other
File I/O pickers before running and contain usable refs afterward; deletion,
restore, row removal and replacement leave no ghost keys; selection/save/reopen,
pass-through, invalid paths and parallel consumers are covered.

### P5 — Remove completion switches and make termination explicit

Integrator coordinates runtime/contract and File owners. Inventory every
user-visible `terminate_branch` control/spec, not just the two file nodes.
Remove the optional checkbox from generic forms/specs. File Reader/Manager/Writer
and Window Control remain continuation nodes even when classified under Out.
Designated terminal outputs/End and Merge Beacon branch completion use explicit
node behavior, not a blanket rule based on family/category.

This owner direction supersedes older docs requiring the optional output-node
checkbox. Preserve internal `terminate_branch` signaling for Merge's losing
supervisors, recovery and cancellation. Merge Beacon completes a branch and
can hand its payload to Merge; do not stop before the rendezvous.

P0 must freeze handling of old file configs containing `terminate_branch: true`.
Removing the widget while silently honoring a hidden flag is not a complete
fix; silently changing every old workflow is also not a migration contract.
Choose and document versioned normalization to continuation behavior and how
users represent a previously requested terminal path with designated nodes.
Do not implement a broad Supervisor rewrite just to hide the checkbox.

Acceptance: file chains continue; designated terminal paths stop; connected
terminal outputs behave deliberately (not merely because `next_node_id` is
None); beacons reach Merge, exactly one merge supervisor continues, recovery
termination still works, and migrated saved configs have explainable behavior.
Update NODE_STANDARDS, helper defaults and any contradictory identity comments.

### P6 — Complete Merge branch/carry-forward choices

Frontend owner inspects `merge_input_options`, branch contexts, reserved ports,
beacon output details and carry-forward filtering. Runtime/contract owner
supplies rendezvous evidence in `backend/nodes/merge_node.py` and
`backend/master_state.py` only if a runtime defect is reproduced.

Treat the home branch payload separately from sibling branches selected for
closure: the user must be able to carry a valid participating home-branch
payload even when it is not a sibling beacon to close. Include eligible selected
sibling/nested branch payloads with stable branch/port identity and full branch
path labels. Explain why unfinished, downstream-only, already-owned or
unselected branches are unavailable instead of accidentally offering an
unreachable rendezvous. Do not add auto-selection of all branches.

Audit the five input-port limit. If it explains omissions, expose the limit and
track dynamic merge ports separately; do not silently reuse an occupied port
or alter port shape in this fix. Fix missing eligible branches within the
current port contract. Reuse P1 provenance for forwarded payload labels/types.

Acceptance: home plus two siblings, nested branches, aliases, forwarded file
payloads, selected/unselected closures, deletion/restoration and capacity
boundaries are covered. Save/reopen preserves stable identity; selected payload
equals runtime merge output; no deadlock or duplicate continuation.

## Agent ownership and integration order

The frontend, runtime/contract and file agents implemented their assigned
tracks. The integrator completed shared audits, migrations, integration tests
and documentation after agent usage limits interrupted their final audits.

| Role | Owns | Handoff |
|---|---|---|
| Integrator | P0 fixtures/contracts; plan/status docs; migration coordination; integration gates | Publishes config/type/forwarding contracts first, reviews each stage and records verification. |
| Frontend | `frontend/node_io_display.py`, `frontend/screens/node_config.py`, editor wiring and shared form helpers; P1/P6 UI | Receives node metadata/schema changes and integrates all shared-screen changes serially. Other agents propose patches rather than editing these files. |
| Runtime/contract | Start/Text Output, canonical metadata/validation, runtime regressions; internal termination/merge only when necessary | P2 and P5 node policy; provides contract additions for effective forwarding and multi-Vault declarations. |
| File | Path compatibility P0a, Writer/Manager/File Reader contracts, file specs and dedicated tests; P2a/P3/P4 | Supplies node schemas/declarations to Frontend; preserves existing file-reference/path fixes. |

Order: P0 → P1; then P2 and the File track can proceed independently in their
owned files. File owner implements P2a Reader routing before P3/P4 so text and
file-reference consumers can be verified together.
P0a path investigation may run alongside P1 in separately owned files, but its
path contract must be settled before P2a/P3/P4 changes to file access.
P4 follows shared multi-output declaration support. P6 consumes P1 and may run
alongside node work, but its edits to NodeConfig must serialize with P2/P4 UI
integration. P5 begins after terminal/migration policy is settled. Integrator
then performs the combined gate. Shared `tests/test_debug_nodes.py`, generated
registration files and status docs have one writer at a time; prefer separate
behavioral regression files for independent tracks.

Use one authoritative checkout. If concurrent agents need isolated branches,
take a reviewed baseline including the current uncommitted fixes first; a new
worktree from HEAD alone omits them. Do not stash/discard the owner's tree or
work from OneDrive. Follow the project's fetch/merge rule, keep branches close
to main, and use focused changes with explicit contracts and test evidence.

## Verification and completion gate

Use `/home/makin/src/node_workflow/.venv/bin/python` from AttackOfTheNodes.
For affected ordinary nodes run the documented helper spec generation/check
flow, reviewing generated diffs so custom execution is not overwritten.
`check_ui.py` intentionally rejects structural Merge/Beacon screens; test their
real topology UI instead.

Each stage: focused behavioral regressions, helper checks where applicable,
save/reopen/Cancel and production-CSS navigation at 60/100/140 columns. Exercise
W/S, A/D, E/Enter, Esc/Ctrl+Q, numbered tabs and digits in edit mode. Include
known-incompatible, unknown, empty and saved-invalid sources, and reruns.

Combined gate: compile application, full debug suite and full application suite;
check spec/runtime alignment and `git diff --check`; record actual counts and
failures in SESSION_LOG. Run an integrated workflow: Start greeting Vault,
multi-file Manager preserving an incoming payload, parallel File consumers with
ordering, Reader copying file contents downstream and to typed text Vault,
text-only Writer Content with top/bottom/newline handling, beacons,
Merge selecting a participating payload, terminal Text Output. Save/reload and
repeat after producer deletion/undo. Keep headless evidence distinct from
owner live-TUI/Windows/WSL verification; existing FO7 remains open.

Done means every reported source/preview defect is reproduced and covered,
all implemented features have truthful controls and runtime behavior, migrations
are documented, and only line-number insertion remains an explicit TODO. Do not
mark the implementation complete merely because this build plan exists.
