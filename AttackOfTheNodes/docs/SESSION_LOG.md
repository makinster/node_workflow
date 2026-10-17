# AttackOfTheNodes Session Log

This active log keeps recent/current entries only. Full older history was
collapsed into `archive/SESSION_LOG_HISTORY.md` during the documentation
overhaul.

## 2026-10-17 — C7: Deep Branch Offers Only `branch`

Branch `dist/c7-deep-branch`, stacked on `dist/c6-random-chat` (PR #65).
Before: 1456 passed. After: 1457 passed.

- **Owner decision (2026-10-17):** Deep Branch is a debug node for the
  branch depth limit; narrow it rather than add engine behaviour, and keep
  debug nodes consistent without going further.
- A node that spawns branches ends its own supervisor, so Deep Branch's
  `default` port was filled but never ran. It is removed; the node offers
  only `branch`. Saved workflows that wired `default` get `undeclared_port`.
- `test_deep_branch_respects_depth_limit` used to wire only `default` to
  End and accept FINISHED or ERROR. It now loops `branch` into the node and
  asserts supervisors at depths 0–5 and a FINISHED run. New
  `test_deep_branch_offers_only_the_branch_port` fails on the old node.

## 2026-10-17 — C6: Random Number's Payload Field; Chat Vault Output Off

Branch `dist/c6-random-chat`, stacked on `dist/c4-forwarding` (PR #64).
Before: 1449 passed. After: 1456 passed (7 new tests in
`test_c6_payload_and_chat_defaults.py`).

- **C6 root cause:** the helper generator's `producer` template adds a
  "Payload" (`value`) field to every producer; Random Number computes its
  output and never read it. New spec option `payload_field: false`
  (generator, NODE_HELPER.md); Random Number's spec sets it.
- **Regeneration refused:** regenerating Random Number from its spec also
  changed its family (Complex → Utility), colour and group, and dropped
  the output's `data_type: number` (the generator's `_port_metadata` keeps
  only name/description). Reverted; the field was removed from the class
  by hand. Both recorded under C8.
- **Saved `value` keys** stay in the config and are ignored; no migration
  is needed (nothing transforms them; the editor and loader keep unknown
  keys). Tested through load, the node editor's save, and a run. A spec
  for `aotn build` that sets `value` now gets `unknown_config_key`.
- **Owner decision (2026-10-17):** Chat Completion's Vault output defaults
  to off; a fresh Chat node now fails Validate only for its secret.
  `examples/summarise_file.json` turns Vault output on explicitly. Two tests
  encoded the old default and were updated deliberately: the generated
  `test_chat_completion_node_session_and_routing_fields` now asserts
  `vault_write is False`; `test_wait_until_releases_llm_after_answer_is_published`
  sets `vault_write: True` with its key.

## 2026-10-17 — C4: Fixed Forwarding Declared

Branch `dist/c4-forwarding`, from `main` at `105623d` (PR #63). The owner
asked for a brief self-review of #62/#63, merge, and continue: the review
found HTTP Request's error path listed twice in `inspect` (fixed with a
test before merging #62 and #63). Before: 1424 passed. After: 1449 passed
(new `test_forwarding.py`).

- No-Op, Logger, Probe, Memory Snapshot, Merge Beacon and Repeat Counter
  return their input unchanged (read in their `execute`); they now declare
  `ui_hints` `pass_through` (one-line summary, shown read-only in the node
  editor as "Dead drop payload: ...") and `forwarded_input_port: input`,
  like Sleep and Counter. `test_forwarding.py` runs each node and checks
  the payload comes out as the same object.
- Effect: types flow through them. Random Number → Logger → File Reader now
  warns "Type mismatch"; the Source dropdowns, the selector filter and
  `aotn inspect` see the producer's type.
- Tests changed deliberately: four preview tests in `test_debug_nodes.py`
  used a standalone Logger as a named producer; with forwarding a Logger
  with nothing connected passes nothing on, so they now use Get Variable
  (same "Output" port, produces its own value). `test_any_paths_keep_working`
  (C2) and `test_data_flow_statuses` (inspect) used No-Op as an untyped
  node; they now use Echo, which computes its output.
- Not done (plan says config-selected): Conditional forwards its input or
  a Vault variable depending on its source; Merge forwards a selected
  branch.
- **Review fix:** forwarding was applied to every port, including
  `error`, so Random Number → Logger's error output was typed `number`
  although it carries the failure record (false "Type mismatch";
  wrong preview). Sleep and Counter already had this; C4 spread it.
  `port_types.is_pass_through_node` now never forwards on `error`;
  `test_error_output_is_not_forwarded` covers all eight forwarding nodes.

## 2026-10-17 — Workflow Authoring Tool, PR 2 (Inspect + Examples)

Branch `dist/authoring-inspect`, stacked on `docs/stash-proposal` (PR #62).
Before: 1400 passed. After: 1424 passed (24 new tests in
`test_authoring_examples.py`).

- **`authoring.inspect_workflow`** and **`aotn inspect <id|name|path>`**:
  execution outline from Start (first-connection rule, ignored extra
  connections, parallel splits, one-of choices, on-error paths, loops,
  joins, nodes not reached), Vault writers/readers with ordering (before /
  not guaranteed / no writer), data-flow statuses (ok, ok (accepts any),
  mismatch, unchecked), unchecked config, changed-from-default config,
  validation. Duplicate names get an id suffix (`No-Op #3f2a`).
- **Shared lookup:** `run_service.resolve_workflow_data` (id, name
  case-insensitive, or .json path), used by `aotn run` and `aotn inspect`.
- **`custom_config_keys`** on node classes, published by the factory:
  config a custom editor section manages. Error Mux declares `routes` and
  `unmatched_route` (before this a spec could not configure a mux).
- **`examples/`**: six specs (parallel wait, ask and branch, Vault handoff,
  fetch and save, catch HTTP errors, summarise a file) with a README; the
  suite builds and inspects each.
- **Finding for the owner (not changed):** a freshly added Chat Completion
  fails Validate: its defaults turn Vault output on with an empty key
  (`vault_output_key_missing`), besides the expected "secret required".
  Only File Reader/Write (path) and Chat fail with their own defaults.
- **PR 63 review (five findings, all reproduced, fixed on the branch):**
  1. Vault "before" was claimed for any ancestor writer, even one on a
     Conditional branch the run can bypass. Now "before" only when every
     path from Start to the reader passes a writer; otherwise "not
     guaranteed" (a path skips every writer / writers on a parallel path);
     plus "its own key" (Counter) and "not reached".
  2. The outline walked hidden outputs (a two-path Branch with a kept
     `path_c` connection split three ways); only active ports are walked,
     hidden connections are listed as never running.
  3. Wait Until targets saved as a list (the editor) showed as `?`; both
     list and comma-string forms are read, as the engine does.
  4. Error Mux `unmatched_label` / `unmatched_forward` were rejected;
     declared as custom keys.
  5. `aotn inspect` on a file that is not a workflow (`[]`) raised a
     traceback; it now applies `aotn run`'s shape checks and exits 2.
  9 new tests fail on the first PR head. Stash proposal: paste outcomes
  reconciled (section 9.7) on #62's branch and merged in.

## 2026-10-17 — Stash Proposal Brought Into The Plan

Docs only. The owner's `STASH_PROPOSAL.md` (written in another session on
`claude/drag-drop-file-paths-j7o5r1`, cut from an older main) was
cherry-picked onto `main` as `docs/stash-proposal`, its commit message
reworded to drop a model-name attribution line (owner rule). Added
section 9 (review notes the owner agreed with, and the order) and put
Stash S1–S3 into `NODE_CONTRACT_PLAN.md`'s agreed order, before Step 4.
Still a proposal, not approved. The `ctrl+p` terminal test waits until S3.

## 2026-10-16 — Workflow Authoring Tool, PR 1 (Core)

Branch `dist/authoring-core`, from `main` at `4f045bd` (PR #60). The owner
merged #59 and #60 and asked to continue. Before: 1376 passed. After:
1400 passed (24 new tests in `test_authoring.py`).

- **Reproduced first** (the proposal's findings, on main): `connect()`
  accepts a port that does not exist; `update_node_config` replaces the
  config; a misspelled key (`duraton`) passes validation silently; Merge
  has five config keys and an empty schema.
- **`backend/authoring.py`**: `list_node_types`, `describe_node_type`
  (config-aware: resolved ports and types, field limits and visibility,
  Vault reads/writes, declared errors, node-reference fields, keys without
  schema reported as unchecked) and `build_workflow` (spec
  `aotn-workflow/1`: handles, real config keys merged over defaults,
  explicit ports, Wait Until targets as handles; every problem reported in
  one pass; the validator's errors fail the build; SaveManager save;
  duplicate names refused; reload into a fresh map and re-check; nothing
  written on failure).
- **CLI**: `aotn nodes`, `aotn describe <type> [--set k=v]`, `aotn build
  <spec|-> [--check]`, all with `--json` and `--data-dir`
  (`aotn_author.py`, dispatched from `main.py`; added to `py-modules`).
- **Shared change**: `persistence.save_workflow` writes atomically (temp
  file, then rename), for the app too.
- **Kept as is on purpose**: `WorkflowMap.connect()` and
  `update_node_config()` (the editor relies on both); the builder checks
  ports and merges overrides itself.
- Tried end to end on a temporary data folder: a bad spec listed all
  seven problems; a good spec saved, its Wait Until target was the
  generated id, and `aotn run` finished it.
- New `docs/WORKFLOW_AUTHORING.md`; README, TASK_INDEX and AGENTS.md
  point to it.
- **PR 61 review (four P2 findings, all reproduced, fixed on the branch):**
  1. Concurrent saves shared one temporary filename (six of eight writers
     failed in the probe); `save_workflow` now uses `tempfile.mkstemp`.
  2. One output wired to two nodes built cleanly but only the first runs
     (`find_next_node_id`). New validator warning `ignored_fan_out`
     (label "Ignored connection"; the `error` port and inline Error Mux
     catches are exempt); the builder treats it as an error.
  3. Duplicate names were compared case-sensitively while `aotn run`
     matches case-insensitively; now `casefold`.
  4. `--json` output could start with a plain-text warning: persistence
     now logs warnings instead of printing, and the CLI sends any stray
     stdout to stderr. Checked in a real shell pipe.
  Five new tests fail on the first PR head; the sixth (inline Error Mux
  exemption) guards the new rule.
  `test_prune_merge_node_survives_when_another_branch_still_feeds_it`
  asserted no warnings, but its fixture wires `start.default` to two nodes;
  it now expects exactly that `ignored_fan_out` (updated deliberately).
  Read-only check of the owner's saves: one "Untitled Workflow" has a
  Parallel Branch `path_a` wired to two different Merge nodes; only the
  first runs, and the editor's Validate now says so.

## 2026-10-15 — C5: Number Field Policy

Branch `dist/c5-number-validation`, stacked on `dist/c3-mode-output-types`
(PR #59; merge that first). Before: 1328 passed. After: 1376 passed
(new `test_number_policy.py`; `test_form_generator.py`'s coercion test
rewritten).

Owner approved the policy: block save with an inline error, limits declared
per field, blank means default, the same check in the validator.

- **Reproduced first:** on main the validator passed Sleep durations
  `'definitely not a number'`, `-1` and `'inf'`; the form turned unparseable
  or blank numbers into 0.
- **Shared check:** `field_types.check_number(field, raw, default)` returns
  `(value, problem)`; `number_fields`, and `field_visible` (moved from the
  validator so the editor and validator share it).
- **Editor:** `NodeConfigScreen._checked_numbers` runs on every save;
  problems show in red under the field (under the whole row for inline
  fields), the typed text stays, focus goes to the first bad field, and
  a toast says how many to fix. Blank saves the default. Number inputs
  show the placeholder `blank = default`.
- **Validator:** `invalid_number` (label "Invalid number") for a visible
  saved value that fails; it blocks the run. The owner's saved workflows
  have none (read-only check).
- **Limits:** Chat Completion max tokens ≥ 1 and temperature 0–1 (the
  provider's range); HTTP timeout > 0 (`min_exclusive`); Repeat Counter
  max visits ≥ 1. Existing: Sleep 0–60, Branch count 2–64, wrap width ≥ 0,
  Wait Until timeout ≥ 0. A test checks every default passes its field.
- **Helper specs:** HTTP Request changed through its spec and regenerated
  (custom body and test cases restored). Chat Completion's spec has
  drifted from its class (512 differing lines, plan item C8), so a
  regenerate would destroy the node: its class and spec fields were edited
  by hand to match.
- **Test changed deliberately:** `test_numeric_coercion_on_invalid_input_
  defaults_to_zero` encoded the old coercion; now
  `test_numeric_fields_keep_unparseable_text`.
- Sample screen (Sleep with -2) sent before the PR.
- **PR 60 review (four findings, all reproduced, fixed on the branch):**
  1. Integers went through float (9007199254740993 became …992) and a
     saved 10**400 crashed with OverflowError. Integer fields now parse
     exactly (`_whole_number`); float overflow reports "Number is too
     large".
  2. Preflight accepted values execution could not use (Sleep `""`,
     Repeat Counter `"3.0"` raised at run time). `Node.__init__` now
     stores number fields through `field_types.normalize_numbers`, so
     every node receives exactly what preflight checked.
  3. Custom controls bypassed the policy: Branch count 65 saved as 64 and
     `abc` as 2; Wait Until still rejected a blank timeout. The editor now
     checks the type's whole schema, including custom controls
     (`CUSTOM_NUMBER_CONTROLS`: Branch count), and Wait Until's timeout
     uses `check_number` (blank = 0, wait forever). Its own "nonnegative
     number" message is gone; `test_wait_timeout_validation_and_cancel`
     was updated deliberately to assert the shared inline error.
  4. An untouched save of a partial config (Sleep `{}`) added keys; the
     no-edit comparison now runs before checked numbers are written.
  12 new tests fail on the first PR head.
- **PR 58 review (maintainability):** `test_validation_codes.py` counted
  source snippets; it now parses `validator.py` with `ast` and requires every
  issue dict (a dict literal with a "message" key) to carry a registered
  literal code, independent of formatting. A mutation check (one code
  removed) fails with the line number.

## 2026-10-15 — C3: Mode-Resolved Output Types

Branch `dist/c3-mode-output-types`, from `main` at `9809a90` (PR #58).
Before: 1314 passed. After: 1328 passed (14 new tests in
`test_mode_output_types.py`).

- **HTTP Request** (helper-generated): the spec now declares the `default`
  port ("Response", static type `any`); regenerated with
  `create_node.py --force`, custom body restored, and the custom hook
  `describe_output_ports` resolves the type to `string` or `file` by
  "Response as". The generated test file's custom cases were restored
  unchanged (the generated part did not differ).
- **Consumers:** the validator's type check, the Source dropdowns, the
  selector filter, previews (`trace_transient_producer`) and auto-wiring
  already read per-config metadata through the factory hook, so they pick
  the type up with no change. Vault typing did not: new
  `port_types.resolved_metadata(factory, type, config)` now feeds
  `typed_vault_writes` in the validator, the Vault pickers
  (`_declared_vault_writer_keys`), `memory_registry` and the Branch-seed
  tracer.
- **Audit:** of the nodes with a concrete output type (string, number,
  file), HTTP Request is the only one whose type changes with a setting;
  Random Number's integer/float mode is `number` either way, and
  pass-through options were already handled by `is_pass_through_node`.
  Nodes typed `any` whose real type could be known (Get Variable from its
  key's writer, JSON Path) are later contract work.
- **Reproduced first:** with the HTTP change reverted, 10 of the 14 new
  tests fail, including the audit's case (file mode into File Write wired
  `content`; now `file_path`).
- Plan updated with the agreed order (C3 → C5 → authoring tool → C4, C6,
  C7 → Step 4), the authoring tool's scope, and the queued naming PR.
- **PR 59 review (P3, fixed):** the editor's details panel still showed
  `Response [any]` in both modes; `_detail_output_lines` now reads
  `resolved_metadata` (2 new tests; suite 1330).

## 2026-10-15 — Validator Issue Codes

Branch `dist/validation-issue-codes`, stacked on
`dist/selector-upstream-filter` (PR #57; merge that first). Before: 1308
passed. After: 1314 passed (6 new tests in `test_validation_codes.py`).

- Owner chose this small PR before C3 so labels stop depending on message
  text (C1 and C2 had each added another text match).
- `backend/validation_codes.py`: `ISSUE_CODES`, 34 codes with one-line
  meanings. All 38 message sites in `validator.py` now add `code`;
  `type_mismatch` also carries `port` and `source_node_id`,
  `unwritten_vault_key` carries `port`. `message` is unchanged, so the CLI
  and logs read the same.
- Validation Details: `VALIDATION_LABELS` (code to label) replaces the
  text matching in `_validation_type`; unknown codes fall back to
  "Validation issue". Every issue now gets a specific label; new names:
  "Missing node" (was "Missing connection target"), "No Start node" /
  "Several Start nodes" (was "Start node"), plus labels for checks that
  had none (secrets, files, Vault keys, Error Mux, unused ports).
- Tests: codes used equal codes registered, every append carries a code,
  every code has a label, a messy workflow yields only registered codes
  with port/source details, labels ignore message wording. One C1 test
  that compared a whole issue dict now includes the code (intended).
- Wording noticed for the owner's batch: an unknown type reads "Unknown
  node type: Unknown node type: ..." (label and message repeat).
- Sample screen sent before the PR.

## 2026-10-14 — Node Selector: Fitting-Only Toggle (owner request)

Branch `dist/selector-upstream-filter`, stacked on
`dist/c2-edge-compatibility` (PR #56; merge that first). Before: 1292
passed. After: 1308 passed (16 new tests in
`test_selector_upstream_filter.py`).

- Owner asked for a key in the node selector that shows either all nodes
  or only those that can take what is upstream. `T` toggles it; default
  is all nodes (unchanged behaviour) and the choice is remembered for the
  app session (`NodeSelectorScreen.show_fitting_only`).
- Backend `port_types.accepts_producers(factory, node_type, types)`: a
  node fits when any input port takes any of the upstream types
  (`types_compatible`); nodes without inputs never fit.
- The editor traces the upstream of the add/insert point with
  `trace_producers` (so Sleep after Dice counts as number) and passes
  `{name, types}`; the title reads `Add Node · after Dice (number)`.
- Upstream only: an insert between two nodes does not yet check that the
  new node's output suits the downstream node. Most ports are `any`
  today, so the filter hides few nodes (file and text ports); it gets
  sharper as C3 and the migration declare types.
- Sample screens (all vs fitting, inserting after Dice) sent before the PR.

## 2026-10-14 — C2: Edge Compatibility Diagnostics

Branch `dist/c2-edge-compatibility`, from `main` at `4d7eca2` (PR #55).
Before: 1260 passed. After: 1292 passed (32 new tests in
`test_edge_compatibility.py`).

- **One rule:** `data_types.types_compatible(actual, wanted)`: `any` or no
  type on either side matches, otherwise canonical types must be equal (no
  implicit conversion; File Write rejects a number on its text input). The
  editor's connector choice (`_matching_typed_input_ports`), the Source
  dropdowns (Upstream option filter, Vault key filter; untagged legacy keys
  still count as text) and the validator use it. Dropdown behaviour is
  unchanged.
- **Backend tracing:** new `backend/port_types.py` (`metadata_for_type`,
  `is_pass_through_node`, `port_metadata`, `input_port_type`,
  `trace_producer`). `frontend/node_io_display.py` now imports the first
  three instead of keeping its own copies.
- **Preflight:** an active Upstream edge (`<port>_source` is Upstream
  payload, or the port has no selector) whose traced producer type the
  port does not accept is a warning, labelled "Type mismatch" in
  Validation Details: `Input 'File' expects file but Dice sends number`.
  No-op and other `any` outputs never warn. The owner's saved workflows
  produce no new warnings (read-only check).
- **Runtime:** `data_types.describe_value` and `input_mismatch_message`;
  File Reader, File Write (File Path and Content) and File View now say
  `Input 'File' (Upstream payload) expects a file reference but got a
  number (42).` instead of "must contain a typed file reference".
- Reproduction: Random Number → File Reader on Upstream validated clean
  before and failed at run time with a message naming neither port nor
  value; the new tests fail on the old code.
- Sample screen sent to the owner before the PR.
- **PR 56 review (fixed):** the tracer followed only the first connection
  into a pass-through node, so File Write and Random Number both feeding a
  Sleep before File Reader warned or not depending on connection order.
  `port_types.trace_producers` now returns every producer a pass-through
  chain can forward (each connection into its forwarded port, without
  repeats, ending on cycles) and the validator checks each. Reproduced
  first (the File-Write-first order failed).
- **Owner follow-up (2026-10-14): Source dropdown checks every producer.**
  The Upstream option used the display tracer, which follows only the
  first connection, so a Sleep fed by Random Number then File Write hid
  it from File Reader. It now uses `trace_producers` and is offered when
  any producer fits (the validator warns about the rest). To keep the
  dropdown's Branch behaviour, `trace_producers` now follows Branch paths
  like the display tracer does: a path forwards the Branch's input, or a
  Vault-seeded path carries its key's writer types. So Random Number →
  Branch → File Reader now warns too. The display tracer
  (`trace_transient_producer`) still names only the first producer in
  previews; that is display, not a check.

## 2026-10-14 — C1: Preflight Warnings for Node-Specific Vault Reads

Branch `dist/c1-vault-read-warnings`, from `main` at `959eb58` (PR #54).
Before: 1247 passed. After: 1260 passed (13 new tests in
`test_validator_node_vault_reads.py`).

Owner approved `NODE_CONTRACT_PLAN.md` C1–C7 (C8–C12 stay proposed).

- **Shared model:** `vault_declarations.vault_read_entries` returns every
  Vault read as `{source_id, target_port, required}`. `membank_inputs` and
  standard-model reads are required; `config_vault_read_entries` (Get
  Variable, Variable Reader, Conditional on a variable, Counter, Branch
  `vault:` seeds) are all optional because each has a runtime fallback.
  `config_vault_reads` and `active_vault_reads` are derived from them, so the
  Connections tab is unchanged.
- **Validator:** an optional node-specific read whose key no node writes is
  a warning ("Reads Vault key 'value' but no node writes it; the node uses its
  fallback value", or "Path 'Branch 1' seeds from Vault key ..." for Branch
  seeds); a required one is the existing "Membank input source not declared"
  error. Counter writes its own key, so it never warns. The parallel-branch
  race warning now also covers node-specific reads.
- **Validation Details** labels the warning "Unwritten Vault key". Sample
  screen sent to the owner before the PR.
- Reproduction: Start → Get Variable (default key `value`) validated clean
  before; the new tests fail on the old code (missing model functions, no
  warning).

## 2026-10-14 — Session Handoff: UX Detour Complete

Docs only. New `NODE_CONTRACT_EXECUTION_PROMPT.md` starts the next phase: what
to read, where things stand after PRs #43–#53, the owner's direction
(required/optional, data types, help popup, lazy loading, stable labels),
the next step (confirm, then `NODE_CONTRACT_PLAN.md` C1 as warnings plus a
required/optional flag), the working practice and the paste-in message.
`RECOVERY_UX_EXECUTION_PROMPT.md` points to it. Suite unchanged: 1247 passed.

## 2026-10-14 — UX6 Follow-up: One Help Ribbon, A/D on Branch Selects, IDs on Their Own Line

Branch `dist/ux6b-ids-errors-keys`, from `main` at `6f70f85` (PR #52).
Before: 1244 passed. After: 1245 passed (1 new A/D test; `test_node_labels.py`
rewritten for the rolled-back suffix and the new headings: 4 tests).

Owner requests (2026-10-14):

1. **One key-hint ribbon, at the bottom.** Settings, User Input and the
   workflow path prompt still showed a top copy above their status bar; the
   top copies are gone (node editors lost theirs in UX6). Screens without a
   status bar keep their single hint line. A per-panel `H` key-list popup is
   planned (`NODE_CONTRACT_PLAN.md`, owner direction).
2. **A/D on a branch-select row** steps through that node's branches, error
   recovery included (`EditorScreen._cycle_selected_branch_select`); `E` still
   opens the selector. Elsewhere A/D are unchanged (PR #49 rule).
3. **Node IDs:** the UX6 numbered suffix is rolled back; names are the alias
   or type name everywhere. The ID moved off labels onto its own line: under
   the node editor title (`#node-config-id`) and under `Name:` in the details
   panel; execution cards no longer show it; "Merge Node" / "Merges To
   Branch" lines and the "Jumped to" toast use names.
4. **Error headings:** the runtime error screen and validation results open
   with `<name> (<type>) · depth <n> · <branch>` (`frontend/node_location.py`),
   then `Node ID: …`; the runtime screen keeps the run branch, category,
   message and traceback below.
5. Recorded in `NODE_CONTRACT_PLAN.md` (owner direction): required vs
   optional inputs/outputs will be defined when nodes are re-touched; more
   Vault/dead-drop data types are needed for community nodes; C1 proposed as
   a warning with a required/optional flag.

**Tests updated (behaviour the owner changed):** six assertions in
`test_debug_nodes.py` expected IDs inside names (`Merge Node: Merge (id)`,
`Merges To Branch: Approve (id:path_a)`, `Name: Logger (id)`, the editor title
`Edit Node: Logger (id)`, the details line order) or the suffix (`Merge ·1001`);
they now assert the names and the separate `Node ID:` line.

**Review of PR #53 (two crashes, both reproduced and fixed).** After: 1247
passed (2 new in `test_node_labels.py`; both fail before the fix).

1. A node name such as `Fetch [/draft]` was parsed as markup and crashed Error
   Details and validation results. Both now render as literal text
   (`markup=False`), which also covers brackets in messages and tracebacks.
2. The heading reused `_branch_contexts_by_node`, which recursed once per
   node and crashed past ~1,000 connected nodes. It now walks with an explicit
   stack, pushing children in reverse so the visit order (and each node's
   first branch path) is unchanged; the UX3 equivalence tests against the old
   scan still pass.

## 2026-10-13 — UX6: Friendly Labels and Presentation Pass

Branch `dist/ux6-labels-and-presentation`, from `main` at `1a92b43` (PR #51).
Before: 1240 passed. After: 1244 passed (4 new in `tests/test_node_labels.py`).
Sample screens were reviewed by the owner before and after the Branch-row
revision; the owner checked the result live and approved it.

**Owner answers:** Q8 — a counter suffix from 1000 ("something simple for
now, we can re-address this"); details below. Timing of the node contract plan
— the owner asked for best judgement: after UX6 and before Step 4 (Step 4's
contracts build on it), bug items C1–C7 first. Cancel is renamed Close.

1. **Friendly labels** (U5, `frontend/node_labels.py`): a node's usual name,
   plus ` ·1000`, ` ·1001`, … for every node whose name is shared, in
   workflow order. Display only. Used in editor cards (the editor computes
   the labels once per refresh), Connections rows (which no longer repeat the
   node ID), Wait Until targets, the Error Resolver unpick list, the unsaved
   prompt and Merge selectors. The details panel and editor title keep the ID.
2. **Presentation:** tab headers `1 Source` instead of `1 - Source` on every
   tabbed screen (node config, node selector, settings); the duplicate key
   hint line at the top of the node editor is gone (the status bar keeps it,
   reworded to fit 100 columns); Save / Close are compact one-row buttons.
3. **Branch path rows:** one row per path, Branch ID beside its Start Payload
   dropdown, with column headings. The first version used compact borderless
   dropdowns; the owner found them indistinguishable from the names and the
   open list indistinguishable from the rows, so the dropdowns keep their
   border, and every open dropdown list now has a rounded accent border, a
   darker background and a bold highlighted option (global style).
4. **Row navigation in node editors:** W/S and up/down moved one widget at a
   time, so in a path row they went name → its own dropdown → next name (the
   owner saw this as an invisible stop). `NodeConfigScreen._move_keyboard_focus`
   now moves by rows (`group_widgets_into_rows` / `row_move_target`), as
   `UI_QUICK_REFERENCE.md` already specified, and `row_move_target` keeps the
   column index when both rows have the same number of widgets.
5. **64-path Branch open:** 695 → 567 widgets; 0.50–0.67 s → about 0.5–0.6 s
   (target under 0.5 s not met: the rest is Textual building 64 dropdowns).
   Lazy loading is logged in `PROJECT_BACKLOG.md` with the owner's rule (load
   what is shown first, queue Save / Close until all is loaded). Errors text
   was already shortened in UX4.

**Tests updated (behaviour the owner changed):** three Connections tests and
the Merge Beacon selector test expected labels with IDs or without a suffix
(two Merges named "Merge" now read `Merge ·1001`);
`test_branch_config_uses_parallel_payload_ui` read the removed top help line
(it now reads the status bar) and expected S to visit every dropdown (it now
checks S keeps the Branch ID column, D reaches the row's dropdown and W keeps
the dropdown column).

**Behavior changes:** suffixed labels for repeated names; `N Label` tab
headers; Close instead of Cancel; row-wise W/S wherever widgets sit side by
side in a node editor; open dropdown lists look different everywhere.

## 2026-10-13 — UX5: Connections Tab With Jumps, Ctrl+S Save and Stay

Branch `dist/ux5-connections-and-saving`, from `main` at `4bb89cd` (PR #50).
Before: 1212 passed. After: 1230 passed (18 new in
`tests/test_connections_and_saving.py`; all fail on the old code).

**Owner decisions in this phase (replace Q2 and revise U3):** the key check
in the app's terminal panel showed Ctrl+Space arriving as `ctrl+@`, and F2
never arrived (it is a volume key on the owner's keyboard). The owner then
chose: **Ctrl+S saves and stays** (also commits a text field being edited),
**Ctrl+Enter does the same**, **Esc closes** and asks Save / Discard / Stay
when there are unsaved changes. No Ctrl+Space or F2 binding.

1. **Connections tab** (`frontend/connection_rows.py`, node config tab 4,
   Wait Until tab 2): Incoming and Outgoing rows name the node at the other
   end, both port display names and what flows (the producer's payload name,
   or "No payload" when the source publishes nothing). Vault reads (declared
   `membank_inputs` and `<port>_source: Vault` keys) are listed separately
   with their writer, or "no node writes it". A row whose node exists is a
   compact button; Enter opens that node's editor. Rows refresh after a save
   and after Error Resolver picks (the "removed on save" note moved here). It
   replaces the `#connection-summary` text; the Errors section stays below.
2. **Save and stay**: `NodeConfigScreen(on_save=…)`; the editor applies the
   save at once (`EditorScreen._save_and_stay`) and the screen takes a new
   no-edit snapshot. Without `on_save` the last saved result is returned on
   close. The Save button still saves and closes. Ctrl+S / Ctrl+Enter are
   priority bindings so they work while a field is being edited.
3. **Save / Discard / Stay** (U9, `screens/unsaved_changes.py`) on Esc,
   Cancel, Ctrl+Q and Connections jumps. "Unsaved" compares the widgets with
   the snapshot (UX2) and the alias. A fresh Error Resolver saved with Ctrl+S
   is kept when its editor closes (U8 revert only for a never-saved one).
4. The editor opens node editors through `_open_node_config(node_id)`: saves
   and jumps go to that node, not to whatever the editor has selected.

**Tests updated (behaviour the owner changed):** seven test cases pressed Ctrl+S
and expected the editor to close
(`test_file_writer_configured_content_has_visible_keyboard_editor`,
`test_node_config_saves_transient_output_overrides_and_vertical_buttons`,
both `test_viewer_payload_ui_saves_vault_option_with_or_without_forwarding`
cases, the three `test_wait_layout_navigation_and_clean_save` widths); they
now assert the editor stays open, then press Esc and check the same saved
config. The five `test_wait_timeout_validation_and_cancel` cases expected
Cancel to discard an edit silently; they now assert the prompt appears and
press Discard. `test_mux_connections_summary_follows_the_picks` reads the
new rows instead of the removed summary.

**Self-review / found while probing:** (a) the editor's refresh after a
stay-save moved focus to the node list behind the modal, so Esc did nothing;
the screen now restores its own focus. (b) a jump to a node the editor view
does not show (a second target on the same port) opened and would have saved
the *selected* node; fixed by item 4 and covered by a test. (c) the rows'
container had the default `1fr` height and the Errors section was drawn over
them; it is `height: auto` now. Sample SVGs were sent to the owner.

**Manual check (owner, 2026-10-13, app terminal panel):** Ctrl+S saves and
stays, the Save/Discard prompt on a Connections jump works, key bindings as
expected.

**Also recorded:** the owner's live-test findings (outdated older nodes,
window placement in file nodes, missing pass-through, outdated Vault UI,
reveal without autoscroll, error UI keys during runs) as a new section in
`PROJECT_BACKLOG.md`; to be investigated when relevant.

**Behavior changes:** Ctrl+S in a node editor no longer closes it; Esc and
Cancel ask before discarding edits; the Connections tab is rows with jumps.

**Review of PR #51 (four P2 findings, all reproduced and fixed on the
branch).** After: 1239 passed (9 new: 8 in
`test_connections_and_saving.py`, 1 runtime test in `test_error_routing.py`;
7 of the new tests fail on the first PR head, the other two confirm existing
engine behaviour and a fallback).

1. *Saving from a row moved the next jump.* The row refresh replaced the
   focused button and focus fell back to the first row. Rows now carry a
   connection identity (direction plus both node/port ends, or Vault key and
   writer); after a refresh the same connection gets focus, or the first row
   if it was removed, and the tab keeps its scroll position.
2. *Active Vault reads were missing* (Branch `vault:` seeds, Get Variable,
   Chat continuation key). New shared model in `backend/vault_declarations.py`
   (`active_vault_reads`, `standard_vault_reads`, `config_vault_reads`); the
   validator's standard-model rules (`continuation_selected`,
   `repeatable_slot_active`) moved there and the validator calls them, with
   identical results (validator suite unchanged).
3. *An existing writer was reported as absent* (Set Variable). Writers come
   from `active_vault_writes` (declared outputs, standard writes, Set
   Variable / Variable Setter / Counter fields), one entry per node. When no
   writer is declared the row says "no writer found" instead of claiming none
   exists.
4. *Error port described as "No payload"* when normal output is off. The
   Publish toggle now only affects `default`; an `error` port reads "Error
   details on failure". A runtime test routes a File Write failure with
   normal output off and checks the error payload.

**Not changed (follow-up):** `memory_registry` (Vault key pickers) and the
validator's write checks still use `standard_vault_writes` only, so Set
Variable keys are not yet offered in Vault pickers or used by validator
warnings. Moving them onto `active_vault_writes` changes what pickers offer
and what the validator warns about, so it waits for the owner. The review's
documentation drift (README → `SESSION_SUMMARY.md`, `AGENT_HANDOFF.md`
selector text, the README description of `NODE_STANDARDIZATION_HANDOFF.md`,
`AGENTS.md` data-directory/RunContext lines) is reported to the owner, not
fixed here. The plan's second-terminal manual check (Windows Terminal) was
not done at that point (see below).

**Node audit of PR #51 (owner chose: Vault fix in #51, rest planned).**
After: 1240 passed (1 new end-to-end test, which fails on `4e7af7d`).

- The Vault pickers (`memory_registry`, the node config's declared-writer
  scan) and the validator's existence/type/race checks now use
  `vault_declarations.typed_vault_writes`: standard writes with their tags
  plus node-specific writers (Set Variable, Variable Setter, Counter) with an
  unknown type. Before, a Set Variable key showed in Connections but was
  missing from Text Output's Vault picker and failed preflight with
  "Membank input source not declared". The new test checks the row, the
  picker, preflight and a real run agree. Validator reads are unchanged
  (node-specific reads: plan item C1).
- `NODE_STANDARDS.md` / `AGENT_START_GUIDE.md`: `signal_done` is a plain
  call; the examples awaited it.
- The audit's other findings (edge type checks, HTTP mode types, forwarding
  provenance, numeric save validation, Random Number's dead field, Deep
  Branch continuation, spec/generator gaps, author gate) are recorded in the
  new `NODE_CONTRACT_PLAN.md` as proposed phases C1–C12, not approved.

**Manual check, second terminal (owner, 2026-10-13):** Windows Terminal,
passed: Ctrl+S, the Esc prompt and Connections jumps behave as in the panel.

## 2026-10-13 — Session Handoff After UX4

Docs only (`RECOVERY_UX_EXECUTION_PROMPT.md`): environment notes now use the
Windows `gh` CLI for PRs and record the WSL-share edit workaround; "Current
position" has the handoff entry with the concrete UX5 steps, the owner's UI
taste, the pending Ctrl+Space/F2 key check (Q2) and one unreproduced watch
item (a new Error Resolver once missing from the editor after saving).
Suite unchanged: 1212 passed.

## 2026-10-13 — UX4 Follow-up: a/d Cycling Skips Error Recovery

Branch `dist/ux4c-resolver-branch-select`, from `main` at `7fc8e9d` (PR #48).
Before: 1210 passed. After: 1212 passed (2 new in `tests/test_recovery_flow.py`;
both fail on the old code).

Owner request: error recovery branches should not be picked up by a/d
cycling; they are reached by pressing `e` on the branch-select row under the
Error Resolver node.

- `EditorScreen._branch_view_candidates` (a/d and ctrl+a/d) leaves out
  recovery ports (`_is_recovery_port`: any node's `error` port, and an Error
  Resolver port other than No error) and nodes that Start reaches only
  through a recovery port (`_nodes_only_on_recovery_paths`), such as a Branch
  inside a recovery branch, because cycling to them would switch the
  resolver off No error.
- Unchanged: the resolver's branch-select row and `e` (BranchSelectorScreen)
  still list every branch, including recovery ones.

Also recorded: **Q4** (missing connections) — the owner reported it came
after adding a Branch midway and deleting its tombstone, and can no longer
reproduce it; it matches the Branch-tombstone prune bug fixed in PR #46.
**Q2** groundwork: Textual reports Ctrl+Space as `ctrl+@` when a terminal
sends NUL (the usual case) and as `ctrl+space` with the kitty keyboard
protocol, so UX5 binds both; F2 arrives unambiguously and is the proposed
fallback, pending the owner's check in Windows Terminal and the browser.

## 2026-10-13 — UX4 Follow-up: Error Resolver Picker Without "Any Other Error"

Branch `dist/ux4b-picker-cleanup`, from `main` at `1e6c8b4` (PR #47).
Before: 1208 passed. After: 1210 passed (2 new in `tests/test_recovery_flow.py`).

Owner question: why does the picker offer both "Unexpected failure" and "Any
other error", and can both branches be reached? Answer from the code: every
code a node can fail with is already listed (the supervisor rewrites any
undeclared code to `node_error`, and only Wait Until and User Text Input can
raise engine codes, which they declare), so "Any other error" only ever
repeated the unpicked choices; with both picked, the first listing wins and
its branch never runs. The owner chose to remove it.

- `recovery_choices` no longer offers "Any other error". A mux that already
  has `unmatched_route` still shows it, ticked and marked "Older setting …
  Unpick to remove", and keeps working until unpicked. Engine, validator and
  the `unmatched` port are unchanged.
- Picker lines use the Errors-list format, `[code] description`
  (`friendly_error_choice`, stale codes `[code] Not raised by the connected
  node`). The picker's prompts are passed as plain `Text`, because
  `SelectionList` read `[timeout]` as markup and dropped it.

**Tests updated (behaviour the owner changed):**
`test_errors_are_offered_in_plain_words` asserts the new line format and that
"Any other error" is offered only for an existing setting;
`test_config_tabs_source_picks_fill_parameters_and_payloads` no longer picks
it and asserts it is not offered.

## 2026-10-13 — UX4: Recovery Flow From the Originating Node

Branch `dist/ux4-recovery-flow`, from `main` at `1ae7d82`, then `4e1090e`
(PR #46) merged in. Before: 1195 passed. After: 1208 passed (13 new in
`tests/test_recovery_flow.py`).

Owner answers in this phase: **Q5** — the button sits under the Errors
header; after reviewing samples the owner asked for a simpler look: one
compact solid button, no status line, and each error as one plain line with
its code first (`• [timeout] The server did not answer…`). The button reads
**Add Error Resolver Node**, or **Open Error Resolver Node (N caught)** when a
mux catches the node. The node type keeps the name "Error Mux"; its default
alias is now **Error Resolver** (spec change, regenerated, custom body and the
generated test's custom cases restored; `check_node` / `check_ui` pass;
existing nodes keep their alias). **Q6** — Delete branch removes only nodes
reached through that route, stopping at a Merge or any node Start also
reaches another way. **Q7** — insert a new mux in between; the old
downstream continues on No error, which the editor keeps selected.

1. **Errors section** (`node_config._compose_errors_section`): the Show error
   path checkbox is gone (U4); `_error_path_config_values` returns nothing, so
   a stored `show_error_path` stays in the config and keeps its path (U10).
   No button on the Error Mux itself or on nodes without outputs.
2. **Spawn or open** (U2, U7, U8): the button saves the node and returns
   `then: "catch_errors"`; `EditorScreen._catch_errors_for` reuses the mux the
   node feeds directly (`error_mux_ui.inline_mux_for`, the engine's own rule)
   or inserts one with `_connect_new_node` (old downstream moves to No
   error), then opens the mux config. Cancelling the first edit of a fresh
   mux deletes it and reconnects the original edges; the editor stays on the
   originating node with the mux's No error path active. The editor's save
   path is `_apply_node_config_result`.
3. **Unpick confirmation** (U1): unpicking the last error of a branch whose
   port has a connection opens `RecoveryBranchUnpickScreen`, which lists the
   branch nodes (`error_mux_ui.branch_nodes_for_port`) with **Leave
   unlinked**, **Delete branch**, **Cancel**. Cancel picks the error again (the
   draft restores the branch); the other choices apply on save — leave drops
   the connection (the existing prune), delete turns the nodes into
   tombstones first, so undo still works.

**Tests updated (behaviour the owner changed in U4):**
`test_node_config_fixed_tabs_are_keyboard_navigable` now expects the resolver
button as the Connections tab's first field;
`test_errors_section_offers_the_toggle_only_where_error_is_not_listed` became
`test_errors_section_has_no_toggle_and_offers_the_resolver_button`;
UX2's `test_edits_are_still_saved_and_an_undone_edit_is_not` edits the URL
field instead of the removed checkbox.

**Acceptance:** mounted tests cover insertion keeping the downstream on No
error, cancel leaving the graph identical, reopening finding the same mux,
reuse only for a directly fed mux, the three unpick choices, delete stopping
at a Merge and at shared nodes, and the UX1 Merge identity with an inserted
mux.

**Self-review:** the catch button saves the node first, so pending edits are
not lost (UX5 adds Save/Discard/Stay for jumps); with UX2's invariant a
no-edit save changes nothing. Delete branch tombstones nodes before the save
prunes the connection, so each tombstone keeps its original wiring for undo.

**Behavior changes:** no Show error path toggle; new Error Muxes are named
"Error Resolver"; unpicking a branch with nodes asks first.

## 2026-10-13 — Fix: Deleting a Branch Tombstone Loses or Strands Nodes

Branch `fix/branch-prune-output-nodes`, from `main` at `1ae7d82` (PR #45).
Owner report, mid-UX4: deleting a Branch node's tombstone and keeping Branch 1
lost nodes, and the validator then reported unreachable nodes. The owner's
current save (`wf_dfe1f9277865`, read only) showed Start → File Manager → File
Write plus a detached File Reader → Text Output. UX4 work is parked in a stash
on `dist/ux4-recovery-flow`.
Before: 1191 passed. After: 1195 passed (4 new in
`tests/test_branch_prune.py`; 3 fail on the old code).

- **Cause.** `EditorWorkflowAdapter._is_branch_prune_terminal` treated Text
  Output and every Outputs-family node (File Manager, File Write) as the end
  of a path. Since `file_io_continuation_v1` those nodes continue along their
  connections, and `NODE_STANDARDS.md` says termination is declared only by
  `terminates_branch`. So keeping a path whose head is File Manager cut its
  link to File Write (`_disconnect_kept_branch_terminal_outputs`), stranding
  File Write; and dropping such a path pruned File Manager but stopped there,
  stranding everything after it.
- **Fix.** A path end is a Merge Beacon or a type with `terminates_branch`
  (End). Pruning now continues past output nodes, so one guard was added: a
  node still reachable from Start through a surviving route (the kept path or
  anything else) is never pruned (the same rule as UX4's planned Delete
  branch). Merge handling is unchanged.
- Reproduced with a probe on a temp data folder (both kept-path directions);
  after the fix neither leaves unreachable nodes.

**Behavior changes:** deleting a Branch tombstone removes the whole dropped
path, including what follows an output node, and never deletes a node that a
surviving route still reaches.

## 2026-10-13 — UX3: Measured Performance (Branch Rows, Topology Scan, Editor)

Branch `dist/ux3-measured-performance`, from `main` at `79776c3` (PR #43).
Before: 1124 passed. After: 1191 passed (67 new in
`tests/test_branch_topology_scan.py`; the timing, row-map, debounce and
metadata tests fail on the old code).

All numbers are from this machine, `frontend/styles.tcss`, 100×40, using the
review probes (`aotn_review43_probe.py`, `aotn_review43_perf.py`) and two
session scripts (a Branch-open profile and a wide-editor navigation profile).
The plan's "before" column was measured on another run (1.48 s / 0.42 s);
here the same code measured 2.006 s / 0.364 s.

| Measurement | Before | After | Target |
|---|---|---|---|
| 64-branch config open | 2.006 s | 0.58–0.65 s | under 0.5 s (owner accepted, see below) |
| 64-branch row sync | 0.364 s | 0.009–0.010 s | under 0.03 s |
| 12 fork/rejoin pairs scan | 0.0277 s | 0.0001 s | under 5 ms |
| Wide editor open (340 nodes) | 0.782 s | 0.18 s | (profile first) |
| Wide editor key press, median / p90 | 0.588 / 0.633 s | 0.139 / 0.156 s | (profile first) |

1. **Branch rows.** `NodeConfigScreen._branch_rows` maps each port to its
   row, label input and source select, filled as rows are built; the sync
   and `_branch_config_values` use it instead of three whole-screen queries
   per port. Options go through `_set_select_options_preserving_value`, which
   skips unchanged options. New rows mount in one batch. Typing in the count
   field syncs 150 ms after the last keystroke (`BRANCH_COUNT_DEBOUNCE_SECONDS`).
   UX2's open-time snapshot made `_transient_config_values` run two queries
   per output port (1.2 s of a profiled open); it now walks the screen once.
   **Open stays at ~0.6 s:** what remains is Textual applying CSS to ~700
   widgets (64 rows × ~10). The owner accepted ~0.6 s for now; lighter Branch
   rows (fewer labels per row) move into UX6's presentation pass.
2. **Topology scan.** `_branch_contexts_by_node` keeps one visited set keyed
   by (node, branch_id, branch_port) for the whole scan instead of copying it
   per edge. A node reached by several routes in the same context keeps the
   first route's `branch_path` display text (documented in the docstring).
   Identical results to the old scan (kept as a reference copy in the test)
   on fork/rejoin chains, 60 random graphs with Branches, Conditionals,
   beacons, rejoins and cycles, and every saved workflow (read-only).
3. **Main editor (Q3: the owner chose a synthetic wide graph).** 340 nodes:
   Branch(64) → HTTP Request → No Op per path, eight paths with a nested
   Branch(4) of 3-node paths, beacons and Merges; 58 navigation keys (`s`,
   `w`, `d`, `a`). The profile showed 87 of 102 profiled seconds in
   `metadata_for_type`, which rebuilt every type's metadata (including the
   64-port tables) on each of 152,188 calls. `NodeFactory.metadata_for_type`
   now builds the per-type table once (types are fixed after construction;
   the result is shared and must not be modified) and
   `node_io_display.metadata_for_type` uses it; `get_node_types_metadata`
   still returns fresh copies. Left as is: the remaining per-key cost is
   spread over port display names (`node_output_port_metadata`, ~1.9 s of a
   12 s profiled run) and Textual layout.

**Self-review:** the metadata cache must not leak edits between callers;
nothing in `frontend/` or `backend/` writes into looked-up metadata (checked by
search), and the list API is unchanged. The Branch-row map is filled where
rows are built, so a row mounted later is found too (debounce test). Timing
assertions are limited to the topology scan (best of five runs, 50× margin);
the row tests count queries and `set_options` calls instead of timing.

**Behavior changes:** Branch count edits apply after a 150 ms pause in typing.
No functional change otherwise.

## 2026-10-13 — UX2: PR #43 Made Safe (Pass-Along, Route Draft, No-Edit Save)

Branch `dist/p4-inline-error-mux` (PR #43), with `main` at `acc8e2f` (UX1, PR
#44) merged in first; the only conflict was this log. Before: 1071 passed
(P4 + UX1). After: 1124 passed (53 new in `tests/test_no_edit_save.py`; 50
fail on the pre-UX2 code). `check_node` / `check_ui` pass for
`error_mux_node`. The UX1 probe also passes with an inline Error Mux after
HTTP Request inside the Branch path (only possible on this branch).

`aotn_review43_probe.py` before → after:
- LEGACY_SAVED: `failed_input` became `forward: error` on the route and
  `unmatched_forward: error` → both keep `failed_input`.
- GROUPED_RESELECT: `timeout` came back on a new `route_…` branch with
  `error` → back on `both` with `failed_input`.
- REPEATED_RESELECT: label reverted to `Timeout` on a new branch → `Revised`
  on `both`.

1. **Legacy pass-along.** New migration `error_mux_forward_v1`
   (`config_migrations.py`): a node-wide `forward` is copied onto every route
   whose own `forward` is missing or invalid and onto `unmatched_forward`
   when that is missing or invalid, then removed and kept as evidence under
   `_config_migrations`. This reproduces the old fallback exactly. The
   fallback in `node_errors._forward` / `mux_routes` / `mux_forward_for` is
   gone: one rule remains (the branch's own choice, else `error`).
2. **Route draft record.** `frontend/error_mux_ui.MuxRouteDraft` replaces
   `routes_for_selection` and the screen's append-only `_mux_removed`:
   `routes_by_id` (id, label, forward, codes in original order) and
   `owner_by_code`. Unpicking keeps ownership; re-picking restores the same
   branch with its latest name and pass-along choice; grouped routes stay
   grouped; a newly picked code gets a branch that is remembered too.
3. **No-edit-save invariant.** The node config screen takes a snapshot of
   what its widgets describe after mount (`_collected_config`, now shared with
   `action_save`). When a save's collected config equals that snapshot (no
   edit), a key the stored config lacked stays absent and a stored empty
   value ("", None, [], {}) is kept; non-empty corrections (migrations,
   retired Wait Until declarations) are still written. A save with any edit
   is written as collected, exactly as before. This removes every noise key
   the probe found (all 38 types added some: `show_error_path: false`, empty
   `<port>_label`, default `transient_outputs`, `""`→`None` Vault keys, a
   Merge `home:path_a` carry, Branch payload sources, empty mux routes, …).
   The editor's save path is now `_apply_node_config_result(node_id,
   result)` so the test can apply it unmounted. The mounted test covers every
   registered type with its default config plus six representative configs,
   and compares config, alias and every node's connections.
4. `EXECUTION_STATUS_CONTRACT.md`: `recovered` added (statuses, priority
   order, card text); the Skip bullet that said Skip advances to the next node
   now matches D9 (Skip ends the branch).
5. Mux Connections summary refreshes after each pick and marks a connection
   whose branch is unpicked "(branch unpicked: removed on save)". UX5's
   Connections tab replaces it.

**Tests updated (behaviour the plan changed):**
`test_each_branch_chooses_what_it_passes_along` asserted the removed runtime
fallback; it now asserts raw legacy config gives `error` and the migrated
config gives `failed_input` (route and catch-all).
`test_picks_become_branches_that_keep_their_ids` uses `MuxRouteDraft` with the
same assertions. `test_wait_target_toggle_empty_selection_and_no_options`
expected a no-edit save to rewrite Wait Until's stored `target_node_ids: ""`
as `[]`; it now asserts `""` is kept and that the node reads it as no targets.

**Self-review:** the first version of item 3 applied the rule per key on
every save, so an edited save (for example enabling Vault write) would have
stored `""` instead of the prefilled default description; it now applies only
when nothing changed. A probe command in this session hung on a stray
`python -` waiting for stdin; it was stopped and nothing was written.

**Behavior changes:** a no-edit save no longer changes config; legacy muxes
migrate their node-wide pass-along on load; the P4 note that "node-wide
`forward` is the fallback" is superseded by the migration.

## 2026-10-13 — UX1: Merge Branch Identity and the Never-Drop Backstop

Branch `dist/ux1-merge-branch-identity`, from `main` at `09a1402` (PR #42).
First phase of `RECOVERY_UX_BUILD_PLAN.md`; this PR also commits that plan and
`RECOVERY_UX_EXECUTION_PROMPT.md`.
Before: 1053 passed. After: 1071 passed (18 new in
`tests/test_merge_branch_identity.py`; 16 fail on the old code).

- **Reproduced** with the review's `aotn_review41_probe.py` on `main`: turning
  on Show error path for a node inside Branch path_b changed the Merge option
  from `<branch>:path_b` to `<node>:default`; a no-edit Merge save wrote
  `branches_to_close: []`, `carry_forward_branch_id: home:path_a`, and the
  editor disconnected the Merge Beacon. After the fix the probe keeps all
  three.
- **Backend:** `Node.spawns_branches: ClassVar[bool] = False`; True on
  `BranchNode` and `DeepBranchNode`, the only nodes that signal `branches`
  (a test scans every registered class's source so a new one cannot be
  missed). Factory metadata `spawns_branches` and
  `NodeFactory.spawns_branches(type)`. No engine change.
- **Topology:** `node_config._branch_contexts_by_node` starts new branch
  contexts only at nodes whose type spawns branches. Every other node passes
  the current context to all connected targets, whatever its output count.
  Covered: Show error path on, HTTP Request (lists `error`), Error Mux
  routes, Conditional, Random Branch (picks one path, spawns none). The
  inline-mux variant from the plan only exists on PR #43's branch; UX4's
  acceptance re-runs this probe with an inserted mux.
- **Backstop:** `unmatched_merge_values(options, config, reserved_ports)` finds
  stored `branches_to_close` / carry-forward values (including the legacy
  `selected_branch_id`) that match no current option. The Merge config shows
  them as checked "Kept, no longer matches a branch" rows, with a warning, and
  a no-edit save writes them back unchanged (carry, `selected_branch_id` and
  `selected_input_port` exactly as stored). Unchecking or reselecting drops
  them explicitly. The editor's `_sync_merge_branch_end_connections` does not
  disconnect any beacon while an unmatched closure remains (it cannot know
  which beacon the value meant) and, on a Merge save, notifies the warning.
- `NODE_STANDARDS.md`: new "Branch spawning" section.
- Not changed: the editor's other `len(output_ports) > 1` checks (port
  cycling, Merge slot hints, branch selector paths) are navigation, not
  branch identity; `WorkflowMap.get_nodes("branches")` is unused by Merge.

**Checked read-only:** every workflow under `workflows/` (4 files, 1 Merge in
`wf_0d75f6241f3d`) has identical Merge options with the old and new rule and no
unmatched values; file hashes were unchanged after the check.

**Self-review:** first version computed the kept values after the "no open
branches" early return, so a Merge whose only branch identity changed and had
no home inputs would still have saved an empty closure; moved before it. The
editor first notified on every whole-workflow Merge sync (load, any node
save); now only on a Merge save. A `home:` carry-forward is judged only when
the caller passes the home inputs, so the editor never flags a valid one.

**Behavior changes:** a node with several outputs inside a Branch path no
longer creates its own Merge option (existing configs that relied on the old
identity would show as kept rows; none exist in the saved workflows). Merge
saves never drop unmatched values silently.

## 2026-10-12 — P4: Error Mux Redesign (Inline Catch, No Error Branch)

Branch `dist/p4-inline-error-mux`, from `main` at `09a1402` (P3b, PR #42).
Before: 1053 passed. After: 1053 passed (P2's route-list UI tests replaced
by tests of the new design; see below).

Owner feedback: the P2 mux was confusing. Intended use: override chosen
error codes so a failure takes a recovery path instead of stopping with an
error; a default No error branch for normal execution; pick errors in Source
(readable), get one entry per pick in Parameters (scrollable), and choose per
branch in Payloads whether to pass the error or the previous node's input.

- **Engine.** The mux sits inline: the guarded node's output feeds its
  `input`. `Supervisor._inline_error_route` routes a failure to a mux fed by
  the failed node when the mux (`catches_upstream_errors`) accepts the code;
  an explicit `error`-port connection still wins. Routed to the mux, the
  supervisor passes `inputs["error"]` (the payload) and
  `inputs["failed_input"]`; reached normally, `error` is removed so a stale
  payload never leaks. A routed failure publishes node status `recovered`
  (reason = code) instead of `errored`; unrouted failures stay `errored`.
- **Error Mux** (spec change, regenerated, custom body restored; `check_node`
  / `check_ui` pass): inputs `input`, `error` (older layout); outputs
  `default` (No error) + one per branch + `unmatched` (Any other error). No
  generic config fields; per-branch `forward` in `routes`, plus
  `unmatched_label` / `unmatched_forward`. Node-wide `forward` from P2 is the
  fallback.
- **Config UI** (custom tabs, frontend-only): Source explains the mux, names
  the guarded node and lists its errors in plain words (`HTTP status: The
  server answered with an HTTP error status... `, "Retrying may help." when
  retryable, "Unexpected failure" for `node_error`, "Any other error"); each
  pick adds a row on Parameters (branch name, prefilled) and Payloads (pass
  along: error details or the failed node's input). Unpicking and re-picking
  restores the branch's id, name and choice. P2's auto-fill on wiring, route
  list and "Refill from upstream" are removed (`ObjectListField`'s generic
  additions stay).
- **Execution display:** node cards show `↪ [recovered: HTTP status]`;
  `recovered` ranks below `errored` and `stopped`.
- Validator: a mux fed inline is valid; "Error Mux has no incoming
  connection" replaces the error-input-only warning.

**Behavior changes:** routed failures (to a mux or any `error` handler) show
`recovered`, not `errored` (`test_routing_to_the_error_port_skips_the_default_path`
updated); a new mux has a No error output; inserting a mux after a node wires
it inline. **Tests replaced, not weakened:** P2's tests of auto-fill, refill
and the route-list editor were rewritten for the new picker flow (the
features were removed at the owner's request); `test_error_mux_routes.py`
and the generated mux tests now cover inline catching, No error, per-branch
pass-along, readable choices and the Source → Parameters → Payloads flow.
`test_file_picker_export_and_import_paths` and
`test_error_buttons_have_keyboard_focus_and_scroll[True-60]` failed once
under full-suite load and pass alone (timing-sensitive UI tests).

## 2026-10-12 — P3b: Branch Beyond Five Paths, Merge Slots to Match

Branch `dist/p3b-branch-merge-slots`, from `main` at `745fed3` (P3a, PR #41).
Before: 1029 passed. After: 1053 passed.

The owner chose "Branch + Merge" over raising only Branch's cap or deferring.

- `backend/branch_paths.py`: one naming scheme for Branch paths and Merge
  slots (`path_a` … `path_z`, `path_aa` …), `MIN_BRANCH_COUNT` 2,
  `MAX_BRANCH_COUNT` 64 (a safety limit on run width), `DEFAULT_MERGE_SLOTS`
  5, `branch_count_from_config`, `merge_slot_count`, `slots_covering`.
- Branch: the type lists all 64 paths; `resolve_output_ports` returns the
  first `branch_count`; `execute` spawns exactly those.
- Merge: the type lists all 64 slots; new `input_slots` config (default 5)
  and `resolve_input_ports`. Inputs now have the mirror of the P1 output
  model: `Node.resolve_input_ports`, `get_input_ports()` uses it,
  `NodeFactory.input_ports_for` / `node_input_ports` / `declared_input_ports`,
  `WorkflowMap.input_ports`.
- Validator: inputs per node; a connection into a slot above `input_slots`
  is a warning ("never read"); a port the type never had stays an error.
- Editor: slot allocation draws from every slot name;
  `_ensure_merge_input_slots` raises `input_slots` to cover connected slots
  after each Merge sync; input-port reads (connect, insert, typed-input
  reassignment, repair) use the backend resolver. Tombstone restore checks
  inputs per node (the type-level `_ports_by_type` table is gone).
- Node config: Branch rows are composed for `max(count, 5)` paths and
  mounted on demand when the count grows (labels of hidden paths are kept on
  save); "Choose 2 to 64 spawn points"; Merge capacity text uses every slot.
- Node card colours use the path index, so `path_f`+ cycle the palette.

**Behavior changes:** Branch accepts up to 64 paths; a Merge can close more
than five branches. Old saves: Branch and Merge behave exactly as before (five
slots, same names). Tests that encoded the five-path cap
(`test_branch_node_default_labels_are_configurable`, the P1 port-model
tests) now assert the new contract; the `FakeFactory` gained
`node_input_ports`.

**Checked read-only:** every workflow under `workflows/` validates the same on
this branch and on `main` (`wf_597a2a4f596f`'s two errors pre-date this work:
an Error Mux fed from Error Node's `default` port, and an input on a port
Error Node lacks).

## 2026-10-12 — P3a: Error Paths on Every Node in the Editor

Branch `dist/p3-error-path-and-branch`, from `main` at `57a0709` (P2, PR #40).
Before: 1022 passed. After: 1029 passed.

- `frontend/error_paths.py`: `editor_output_ports(factory, node)` is the
  backend's ports plus `error` when the node shows it — always for nodes that
  list `error` (HTTP Request, JSON Path), otherwise when config
  `show_error_path` is on or an `error` connection exists. The editor's
  `_output_ports_for_node` and node config's `_node_output_ports` use it, so a
  shown error path cycles, is selectable for add/insert (which auto-fills an
  empty Error Mux), and appears in branch selector rows.
- Node config Errors section: **Show error path in the editor** checkbox
  (hidden on nodes that list `error`), saved as `show_error_path` for every
  node type including Wait Until.
- Tombstone restore treats `error` as a port every node has (matching the
  validator), so a restored handler reconnects to its failing node.

**Behavior changes:** the Connections tab now has a focusable field, so
switching to it focuses the checkbox before Save
(`test_node_config_fixed_tabs_are_keyboard_navigable` updated to assert
that, then `s` reaches Save). Nothing changes for nodes that do not opt in.

## 2026-10-12 — P2: Error Mux Routes, Code Pickers and Auto-Fill

Branch `dist/p2-error-mux-routes`, from `main` at `49c5587` (P1, PR #39).
Before: 1000 passed. After: 1022 passed.

- **Routes (backend, `node_errors.py`).** `routes: [{id, label, codes}]` plus
  `unmatched_route`. `mux_routes`, `mux_output_ports`, `mux_route_for_code`
  (first listing wins, then `unmatched`), `mux_route_problems` (missing,
  reserved or repeated ids; a code on two routes), `error_codes`.
- **Error Mux** (spec change, regenerated, custom body restored; `check_node` /
  `check_ui` pass): class `output_ports` is `["unmatched"]`; ports come from
  `resolve_output_ports` (route ids) and names from the new
  `Node.describe_output_ports` (route labels).
  `NodeFactory.node_output_port_metadata(node)` and
  `declared_output_ports(type)` serve them; `output_display_name` uses them.
- **Migration** (`config_migrations`, `error_mux_routes_v1`): `path_a_codes`
  ... `path_c_codes` become routes `path_a`–`path_c` labelled Path A–C, so old
  connections and tests keep working; the old keys are kept as evidence.
- **Validator:** route problems and duplicate codes are warnings; unknown codes
  name the route label; an unconnected route with codes or an unconnected
  unmatched route is a warning; a connection on a deleted route is an
  undeclared-port error.
- **UI only** (`frontend/error_mux_ui.py`): codes from the node wired into
  `error` (its declared errors, then engine codes, then any code a route
  already lists) fill each route's code picker; an empty mux is prefilled with
  one route per code when its config opens, and when the editor wires an
  `error` port into it; **Refill from upstream** rebuilds the routes, keeping
  the id and name of any single-code route. `ObjectListField` gained
  `add_label` / `remove_label` / `id_prefix` / `refill_label` and
  `replace_rows`; file lists keep "Add file" / "Remove file".
- **Prune on save:** `WorkflowMap.prune_removed_output_connections(node,
  previous_ports)` drops connections on ports the save removed (deleted
  routes). Hidden Branch paths and already-invalid connections are untouched.

**Behavior changes:** Error Mux config is a route list (old configs migrate);
new muxes start with no outputs until routes exist; generated `<port>_label`
fields are limited to the type's declared ports.

**Self-review fixes:** the prune first ran on every config save and would
have silently removed already-invalid connections; it is now limited to ports
the save removed. Route ports no longer get generated `_label` fields.

**Open items:** the editor still offers `error` only on nodes that list it (P3);
auto-fill on wiring covers the editor's add/insert flow.

## 2026-10-12 — P1: Port Model, Ports Resolved by the Backend

Branch `dist/p1-port-model`, from `main` at `60b6f37` (P0, PR #38).
Before: 977 passed. After: 1000 passed.

- `Node.resolve_output_ports(config)` (classmethod; default: the class list)
  and `get_output_ports()` now use it. `BranchNode` overrides it with
  `branch_count_from_config` (moved from the UI, with `MIN_BRANCH_COUNT` /
  `MAX_BRANCH_COUNT`, into `backend/nodes/branch_node.py`).
- `NodeFactory.output_ports_for(type, config)`, `node_output_ports(node_data)`
  and `WorkflowMap.output_ports(node_id)`. Metadata `output_ports` is unchanged
  (the type's full list).
- Consumers switched to the backend: the editor's `_output_ports_for_node`
  (about 20 call sites) and Branch tombstone keep-selector; node config's
  `_node_output_ports`, generated port-label fields, downstream/vault port
  lists and transient (dead drop) rows; the editor's insert-between wiring;
  the tombstone restore source-port check and `_declares_output_port`.
- Validator: per-node ports. A connection on a port the type has but the
  config hides (a Branch path above its count) is a **warning** ("never
  runs"); ports the type never had stay errors. No saved workflow under
  `workflows/` has such a connection (checked read-only).

**Behavior changes:** the hidden-path warning; node config's dead drop rows for
a Branch list only its counted paths (overrides for hidden paths are kept on
save so raising the count brings them back); tombstone restore no longer
reconnects a connection from a Branch path the source now hides.

**Tests:** `tests/test_port_model.py` (23). The `FakeFactory` in
`test_debug_nodes.py` gained `node_output_ports` to match the factory API.

**Open items:** Merge has five fixed input ports (`path_a`–`path_e`) and the
Branch config rows use the same five; lifting Branch's cap (P3) must decide
Merge's capacity too. `test_refresh_coalescer` timing test failed once under
full-suite load (passes alone, with and without this change).

## 2026-10-12 — P0: Handled Errors Do Not Fail a Run (D10)

Branch `dist/p0-handled-errors`, from `main` at `0667520` (ESP32 slice, PR #37).
The owner approved the port-model spin-off P0–P3 ahead of step 4.

- **D10.** `ErrorHandler.log_error(..., handled=False)` adds a top-level
  `handled` flag to every error record. `Supervisor` now decides the error
  route *before* logging, so a failure routed along `error` is logged with
  `handled: true`; one that falls through to recovery or the policy is
  `handled: false`. `error_handler.unhandled_errors()` filters records
  (records without the flag count as unhandled).
- `RunResult.exit_code` returns 1 only for unhandled errors;
  `RunResult.unhandled_errors` and `to_dict()["unhandled_error_count"]`.
- `MasterState._record_run` deletes run files when there are no *unhandled*
  errors, and run history records `unhandled_error_count` beside
  `error_count`.
- `aotn run` summary: `1 error(s), 1 handled`.
- Plans: ESP32 row marked done; P0–P3 added to the DISTRIBUTED_BUILD_PLAN
  step table with a spin-off section; D10 in the decision record.

**Behavior change:** a run whose only errors were routed (for example the
failing ESP32 capture that notifies) now exits 0 instead of 1 and deletes its
run files. Errors are still logged and shown in the Errors view.

## 2026-10-12 — ESP32 Proof Slice: Binary-Safe HTTP, Run-Owned Files, Error Notification

Branch `dist/esp32-proof-slice`, from `main` at `f2c1677` (step 3, PR #36).
Before: 952 passed. After: 967 passed.

- **Run-owned temporary files (R4).** `RunSession.new_run_file`,
  `run_file_reference`, `keep_file`, `file_lifetime`; files live under
  `<data dir>/run_files/<run_id>/` (`persistence.RUN_FILES_DIR`, gitignored,
  created only when a run writes one). `file_refs.file_reference(path,
  lifetime=None)` and `reference_lifetime()`; absent lifetime means `kept`.
  `close_all(delete_run_files=...)`: `MasterState._record_run` deletes `run`
  files (and the empty run directory) only when the run succeeded — FINISHED,
  no errors logged, not stopped by the user — and keeps them otherwise.
- **HTTP Request** (spec change, regenerated, custom body restored,
  `check_node` / `check_ui` pass):
  - **Response as** (`response_mode`: `text` default | `file`): `file`
    streams the raw bytes into a run-owned file named after the node with an
    extension from the Content-Type, and outputs the `file` ref. Without a run
    session it fails with `node_error`.
  - **Keep the response file** (`keep_response_file`): marks the file `kept`.
  - **Body from** (`body_source`: `config` default | `input`): POSTs the
    node's input; text as `text/plain`, bytes as `application/octet-stream`,
    anything else as JSON (`application/json`, made JSON-safe).
- **Error to notification:** capture `error` → Error Mux (`http_status,
  network, timeout`) → HTTP POST with Body from `input`, which sends the
  versioned error payload.

**Done checks (`tests/test_esp32_slice.py`, local `http.server`):**

- A JPEG-shaped body (invalid UTF-8) is saved byte-for-byte as a run-owned
  `.jpg` under `run_files/<run_id>/`, and the ref is JSON.
- A 503 endpoint routes `http_status` (status, body) through the mux to the
  notification endpoint, which receives the JSON payload with `run_id` and
  `node_id`.
- Run files are deleted on success (directory removed), kept on ERROR, on
  FINISHED-with-errors and on Stop, and kept on success when marked `kept`.
- `aotn run capture.json --data-dir <tmp>` exits 0 and leaves no run files;
  the failing variant notifies and exits 1.

**Behavior changes:** none for existing workflows (new options default to the
old behavior; refs without `lifetime` are unchanged). `RunSession.close_all()`
without arguments keeps run files.

**Open items / risks:**

- A routed (handled) error still makes `aotn run` exit 1 (step 3 open item),
  so the failing capture run exits 1 even though it notified.
- `urlopen` runs on the event loop thread, so a slow camera blocks other
  branches of the same run (pre-existing for HTTP Request).
- A run-owned file deleted on success may still be named in run outputs; use
  Keep the response file when the file is the result.
- Interrupted processes leave run files behind (no sweeper yet).

## 2026-10-12 — Distributed Step 3: Error Codes, Error Mux, Errors Section, Skipped Status

Branch `dist/step-3-error-routing`, from `main` at `5e65265` (step 2, PR #35).
Before: 905 passed. After: 952 passed.

- **D7 codes** (`backend/node_errors.py`): `NodeError`, declared
  `error_definitions` (helper specs: `errors:`), the default generic
  `node_error` on every node, `engine.*` codes, and the versioned error
  payload (`version`, `code`, `message`, `node_id`, `run_id`, `stage`,
  `details`, `retryable`, `error_id` = the `ErrorHandler` record id). The
  payload lives on the transient store only. `ErrorHandler` records and
  `RECOVERY_OPTIONS_AVAILABLE` carry the code.
- **One engine-level `error` port.** Every failure (exception or a signal on
  `error`) is coded and logged once, then routes along a connected `error`
  port or falls through to recovery / the run's policy. The validator accepts
  `error` connections from any node.
- **Error Mux** (`error_mux_node`, helper spec): routes by code to path A/B/C;
  no matching code falls through. The validator checks its codes against the
  upstream node's declarations (plus engine codes) and flags a mux fed from a
  non-`error` port.
- **Helper**: `errors:` parsing/validation, emitted `error_definitions`, a
  generated codes assertion and a `ui_checks` Errors-section check. HTTP
  Request (`missing_url`, `timeout`, `network`, `http_status` with status and
  body in details) and JSON Path (`invalid_json`) declare codes; both were
  regenerated with custom bodies and tests restored. Wait Until and User Text
  Input list the engine codes they raise.
- **D8 Errors section** beside Connections (all config layouts, including Wait
  Until and branch/merge).
- **D9 skipped status** with reasons, spreading, run history
  `skipped_nodes`, logs, and `[skipped: <reason>]` on execution cards. Wait
  Until on an unreachable target fails with `engine.upstream_unreachable`.

**Interpretation notes (owner agreed 2026-10-12):**

- "One engine-level `error` port for every node" is implemented in the engine
  and validator; nodes do not list `error` in `output_ports` (the editor treats
  any node with several output ports as a branch). Wiring `error` from nodes
  that do not list it in the editor is an **open item**.
- A non-mux node connected to `error` receives every code (catch-all); only an
  Error Mux filters by code.
- A node whose error was routed is `failed` (not completed); its `default`
  target is skipped `not_taken`.

**Behavior changes:**

- The recovery **Skip** button no longer runs the next node with an empty
  input. Its downstream path is skipped until it rejoins something live.
- Untaken paths now show as skipped (`not_taken`, or `upstream_failed` /
  `upstream_skipped`) rather than having no status.
- A failure routed along a connected `error` port now carries the versioned
  error payload (a dict) instead of the node's message string, and the node
  is failed rather than completed.

**Tests:** new `tests/test_error_routing.py` (34) covering every test the plan
lists (linear spread, Merge with a live sibling, not-taken Conditional port,
error routing skips `default`, recovery Skip spreads, Wait Until on a skipped
target fails with `engine.upstream_unreachable`, mux fall-through to the
policy, skipped never completed) plus codes, payload, generator, Errors
section and validator checks; `tests/generated/test_error_mux_node.py`.
Updated for the logged behavior changes: two tests in
`test_execution_status.py` (Skip no longer runs the next node; the untaken
`end` is skipped) and one in `test_run_lifecycle.py` (the error port carries
the payload dict).

**Fixed after the adversarial review** (each with a regression test in
`tests/test_error_routing.py`):

- A mux or catch-all fed by several `error` connections read the first
  connection's slot, not the node that failed (empty or stale payload). The
  supervisor now remembers which node and port routed it to its current node,
  and an input port with several connections reads that one
  (`WorkflowMap.find_input_sources`). This also applies to ordinary ports fed
  by several connections.
- Non-JSON error `details` (e.g. bytes) or inputs broke the persisted
  `run_errors` file and stopped the run. Logged details and inputs now go
  through `node_errors.json_safe`.
- Skip spreading scanned the whole graph after every node (quadratic on long
  runs). A completed node that delivered to all its successors now skips the
  scan.
- A user Stop during a recovery prompt marked downstream nodes skipped
  `upstream_failed`. A user Stop (`RunContext.stop_requested`) no longer
  spreads skips. A failure that terminates the workflow (`_halt`) still does.

**Owner request during review: Error Mux "Pass along".** A path after an
Error Mux only received the error record, so the data the failed node was
working on was lost to the handling path. The mux spec gained a `forward`
select (`error` default, `failed_input`); the node was regenerated and its
custom body restored, and `check_node` / `check_ui` pass. Engine hook:
`receives_failed_input` on the node class (`node_errors.FAILED_INPUT`). The
error payload stays on the failed node's `error` slot either way. Tests:
`test_mux_can_pass_the_failed_nodes_input_down_its_path`,
`test_a_catch_all_node_does_not_get_the_failed_input`, and a generated-test
case.

**Open items from the review (not fixed, need a decision):**

- A routed (handled) error is still logged, so `aotn run` exits 1 for a run
  that handled its errors through a mux. Error records do not say whether an
  error was routed.
- Nodes on an untaken loop (or fed by an orphan node that never runs) are
  never marked skipped, because skipping waits for every source to be final.
  D5 waits still treat them correctly; only the displayed status is missing.
- Spread skip events use `visit_index` 0 on the branch that triggered them.
  Nothing displays per-visit data yet.

## 2026-10-12 — Distributed Step 2: Run Service, Policies, Data Directory, CLI

Branch `dist/step-2-run-service`, from `main` at `5749b9e`. Before: 866
passed. After: 905 passed.

- **Run service** (`backend/run_service.py`): load (saved id, saved name, or
  `.json` file; never touches `last_active_workflow_id`), validate, start with
  inputs and policies (**validates on start**), subscribe/unsubscribe, submit
  input or recovery, pause/resume/stop, wait, `RunResult` with shared exit
  codes. No frontend import.
- **`RecoveryPolicy` / `InputProvider`** (`backend/run_policies.py`, D1). The
  engine asks them when a run was started with them; otherwise the attended
  event-and-wait path is unchanged. Step 1's `unattended=` is now shorthand
  for `TerminatePolicy` + `NoInputProvider`. A policy that does not pause at
  breakpoints skips them. `UNATTENDED_ACTIONS`/`UnattendedInputError` moved
  here and are still importable from `backend.supervisor`.
- **Configurable data directory**: `AOTN_DATA_DIR` (or `--data-dir`) moves
  workflows, settings, secrets, logs and run records; unset, nothing moves.
  Persistence now creates missing parent folders.
- **Logging** moved to `backend/logging_setup.py`; the log file follows the
  data directory.
- **CLI** `aotn run <workflow>` (`aotn_cli.py`, routed from `main.main`): errors on
  stderr from `ERROR_LOGGED`, outputs on stdout (or `--json`), exit codes 0 /
  1 / 2 / 3 / 4 / 130, stdin policies when interactive, `--policy` (default
  `terminate_workflow`) when not, `--input KEY=VALUE` recorded on the run.
  Verified in a subprocess that no Textual module is imported.

**Deviations / notes:**

- The TUI still calls `MasterState`'s public methods rather than the run
  service, so its behavior (including no validation on start) is unchanged,
  as step 2's done-check requires. Moving it onto `RunService` is a later
  change.
- Run inputs are recorded on the `RunContext` only; the Start contract that
  consumes them is step 4.
- The engine still has no `STOPPED` workflow state (step 1 follow-up). The
  run service reports a stopped run as `STOPPED` (exit 130) in `RunResult`;
  run history still records it as `FINISHED`.

**Review fixes (independent diff review before merge):**

- Ctrl+C at an interactive CLI prompt hung the process: the stdin reader ran
  in the default executor, which `asyncio.run` waits for. Prompts now read in
  a daemon thread and are serialized, so parallel branches cannot interleave.
- A run ending in `ERROR` stored and printed no outputs; `MasterState` now
  captures the output log on the `ERROR` paths too.
- A provider raising `CancelledError` (its own future, not a stop) cancelled
  the supervisor and the run looked successful; it now fails the node. A
  recovery policy that raises is logged through `ErrorHandler` and ends the
  branch.
- Unloadable workflow files and unstartable workflows (`--no-validate`) exit
  cleanly (4 and 3) instead of with a traceback.
- `RunService` keeps only the current run's error list; the new tests write
  run records to a temporary folder; the CLI module is `aotn_cli` (not the
  generic `cli`).
- Provider-answered input now reports the node `waiting` while it waits.

**Behavior changes:**

- `aotn` accepts a `run` subcommand; plain `aotn` still launches the TUI.
- Data folders are created with their parents when missing.
- A run that ends in `ERROR` now records the outputs it produced in
  `run_outputs/` (previously only finished runs did).

**Tests:** `tests/test_run_service.py` (24) and `tests/test_cli.py` (15, CLI
runs in a subprocess against a temporary data directory, including Ctrl+C at
an interactive prompt on a pseudo-terminal).

## 2026-10-12 — Distributed Plan: Refresh Coalescer (Frontend Only)

Branch `dist/refresh-coalescer`, built in its own worktree alongside step 1b
and merged with step 1b's `main` (`41f2063`). Before: 860 passed. After: 866
passed. Only `frontend/app.py` and frontend tests changed.

- `NODE_EXECUTION_UPDATE`, `SUPERVISOR_STATE_UPDATE`, `NODE_TIMING_UPDATE`,
  `MEMORY_UPDATE`, `SUPERVISOR_REGISTER`, `SUPERVISOR_TERMINATING` update App
  state and mark the screen dirty; a 75 ms timer (`REFRESH_COALESCE_SECONDS`)
  refreshes once.
- `USER_INPUT_NEEDED`, `RECOVERY_OPTIONS_AVAILABLE`, `WORKFLOW_STATE_UPDATE`,
  `ERROR_LOGGED`, `ERROR_OCCURRED` act at once and flush. `WORKFLOW_DIRTY`
  (editor edits) also flushes, which keeps its immediate refresh.
- `App.flush_refresh()` is exposed for tests. With no running app the refresh
  stays immediate.
- Measured on a 32-node run with a mounted `ExecutionScreen`: 168 screen
  refreshes before, at most 10 after (proposal v2 Task 1 Case B).

**Behavior change:** during a run the execution screen updates at most every
75 ms instead of on every event; the final frame after a run is unchanged.

**Tests:** new `tests/test_refresh_coalescer.py` (6). Two mounted-screen tests
in `test_execution_status.py` now call `app.flush_refresh()` before asserting
a card changed, rather than relying on a refresh per event; their assertions
are unchanged. One unrelated run of the full suite saw
`test_error_details_navigation.py::test_error_buttons_have_keyboard_focus_and_scroll[True-140]`
fail once; it passed on six reruns, on both this branch and `main`.

## 2026-10-12 — Distributed Step 1b: RunContext, WaitRegistry, Delivery Tracking

Branch `dist/step-1b-run-context`, from `main` at `e39f5f7` (step 1, PR #32).
Before: 818 passed. After: 860 passed.

- **`RunContext`** (`backend/run_context.py`): one per run, holding the memory
  bank reference, `RunSession`, `WaitRegistry`, node timings, branch/merge
  groups, delivery tracking, live supervisors, `run_id`/`parent_run_id`, the
  unattended policy and the start time. Supervisors get callables bound to
  their own run. The Supervisor constructor only gained an optional
  `report_node_outcome` keyword. `MasterState.completed_nodes`,
  `node_timings` and `_run_session` remain as views of the current run.
- **`WaitRegistry`** (`backend/wait_registry.py`): tuple keys
  (`("node", id)`), sticky completion, wait-for-all on one Future, any
  unreachable key fails the wait at once, `stop()` gives waiters a `stopped`
  result. Merge is unchanged apart from its state moving into `RunContext`.
- **Delivery tracking + D5**: supervisors report each visit's final state and
  routed targets; pending wait keys are re-evaluated when a node finishes, a
  supervisor terminates or a wait registers. Never timeout-based.
- **Wait Until** fails with `TargetUnreachableError` naming the target instead
  of waiting forever. The code `engine.upstream_unreachable` comes in step 3.
- **Benchmarks (D6)**: `benchmarks/bench_linear_run.py` (5.04 events per node
  on a 200-node linear run, matching the Oct 9 figure) and
  `benchmarks/bench_wait_registry.py`. A test checks pytest collects nothing
  from `benchmarks/`. Proposal v2 Task 1 Case B (refresh rate with a mounted
  `ExecutionScreen`) is a frontend measurement and belongs to the coalescer.

**Interpretation notes (no decision reopened):**

- Proposal v2 was not available in the repo, so its WaitRegistry unit tests
  could not be copied; `tests/test_wait_registry.py` covers the behavior the
  plan specifies instead.
- The plan says 1b fixes the Oct 9 hang "where the target was terminated". A
  target that itself failed was reached, so the literal D5 incoming-connection
  test does not cover it. The rule therefore also treats a target whose own
  latest visit failed or was skipped, and that no live supervisor can reach
  again, as unable to complete.
- A source that never ran and that no live supervisor can reach is treated as
  settled (it can only ever become `skipped`, which D9 does explicitly in step
  3). Without this, a target two or more hops past a failure or an untaken
  port still hung; the independent review reproduced that.
- The memory bank stays the one shared instance the TUI displays (cleared per
  run); separate memory per run is part of step 6's parallel runs.

**Review fixes (independent diff review before merge):**

- Multi-hop hang (above).
- Outcomes are now reported after a node is marked completed, so evaluation
  never sees a finished node that is not yet completed.
- A branch refused by `max_branch_depth` counted as delivered; deliveries
  for branches are now recorded by `MasterState` only when the child exists
  (`SUPERVISOR_REQUEST_BRANCH` gains `source_node_id`).
- Recorded, not fixed (deadlock detection is beyond D5): a target reachable
  only through the parked waiter, and a Merge whose group includes the
  waiter's branch (that one also hangs on earlier code). Because Stop cancels
  tasks, a waiter in a real run sees cancellation; the registry's `stopped`
  result matters for waits that are not task-cancelled.

**Behavior changes:**

- A Wait Until whose target can no longer complete (failed and not
  re-reachable, no incoming connections, or every source finished without
  routing to it) now fails and goes to recovery (or the unattended policy)
  instead of waiting forever.
- When Stop is requested while a node is running, the supervisor discards the
  node's result and reports it `stopped` (it no longer routes the result or
  marks the node completed).

**Tests:** `tests/test_wait_registry.py` (17), `tests/test_wait_until_reachability.py`
(24: terminated target, source failure, two hops past a failure, untaken
Conditional port one and two hops, no incoming connections, depth-refused
branch, Merge before the target, a real loop, long wait behind a pending
input never failed, stale supervisor isolation, unattended Wait Until), and
`tests/test_benchmarks_not_collected.py` (3). The step 1 lifecycle tests'
Wait Until fixture now targets a node downstream of the waiter: its old
target had no incoming connections, which D5 now rightly fails at once.

## 2026-10-12 — Distributed Step 1: Bug Fixes

Branch `dist/step-1-bug-fixes`, one commit per fix. **Baseline on unchanged
`main` (`51c1f0c`): 796 passed.** After this step: 818 passed.

- **1a, error-port routing.** HTTP Request and JSON Path signal failures with
  `{"data": {"error": msg}, "output_port": "error"}`; HTTP Request also
  catches `TimeoutError`. The Supervisor turns a payload routed to an
  unconnected `error` port into a node error, so recovery runs. Both nodes
  were regenerated from their specs with the custom bodies and tests
  restored; the generated header gains `group`/`selector_section` from the
  spec (runtime identity is unchanged — `node_identity` already applied it).
- **1b-fix, Stop and leak.** `MasterState.stop()` cancels supervisor tasks
  after requesting stop, and `start_workflow` cancels and awaits leftover
  tasks before resetting state.
- **1c, unattended policy.** `start_workflow(unattended=None |
  "terminate_branch" | "terminate_workflow")`, passed to every Supervisor.
  Errors are logged and persisted, then the policy applies without waiting;
  input requests fail with `UnattendedInputError`; breakpoints are skipped.
  The TUI passes nothing.

**Behavior changes:**

- Saved workflows that previously continued silently after an HTTP Request or
  JSON Path failure now stop for recovery, unless their `error` port is
  connected.
- Stop interrupts a node that is executing or waiting (reported `stopped`)
  instead of only stopping at the next safe point, and releases Wait Until.
  A stopped run is still recorded as `FINISHED` (known follow-up: no
  `STOPPED` state).

**Review fixes (independent diff review before merge):**

- A supervisor task cancelled before its first step never published
  `SUPERVISOR_TERMINATING`, so the run stayed `RUNNING` and
  `wait_for_completion` spun without yielding (Stop right after Start; or
  `terminate_workflow` with parallel failing branches). Tasks are now pruned
  by a done-callback that re-checks completion.
- Two overlapping `start_workflow` calls could lose track of a live
  supervisor; starts are now serialized by a lock.
- Not fixed, recorded: cancelling does not stop work running in a thread
  (`asyncio.to_thread` in Chat Completion and File Output), and a Wait Until
  whose target can never complete still hangs an unattended run until step
  1b's unreachable rule lands.

**Tests:** new `tests/test_run_lifecycle.py` from the Oct 9 probes: error port
connected/unconnected/retry, HTTP timeout and URL errors, Stop releases Wait
Until, no wake-up leak into the next run (with and without Stop), and an
unattended run hitting an error, an input request and a breakpoint under both
policies. The Stop/leak tests fail on the previous code.

## 2026-10-12 — Authorize Distributed Plan Execution; Merge Plan To Main

Docs only. The owner authorized execution of steps 1, 1b, the refresh
coalescer, 2, 3 and the ESP32 proof slice. Each step lands as its own PR,
which the agent merges to `main` once the suite is green. The agents stop
before step 4.

Added `DISTRIBUTED_EXECUTION_PROMPT.md`, a copy-ready prompt for the next
session, and updated the plan, master plan and backlog status notes plus
README. The plan branch `ccr-1b2501bf-dgol6g` was merged to `main` by PR.

## 2026-10-12 — Record Step 1b And Step 3 Decisions (D5–D9)

Docs only; no code changes. Branch `ccr-1b2501bf-dgol6g`. The owner resolved
the open decisions in `DISTRIBUTED_BUILD_PLAN.md`:

- **D5, unreachable.** Structural and based on incoming connections, never on
  a timeout. A node is unreachable when every source of an incoming
  connection is final and none of them routed to it, and no live supervisor
  can still reach those sources. A required input that is never delivered
  stays a data error.
- **D6, benchmarks.** `AttackOfTheNodes/benchmarks/`, backend only, outside
  `tests/`.
- **D7, error matching.** Stable codes, with a default generic code on every
  node. Messages stay free text. A mux with no matching code falls through to
  pause (app) or the failure policy (headless).
- **D8, node config.** Keep the Connections tab and add an Errors section
  (confirms the 2026-10-09 recommendation).
- **D9, skipped status.** Skipped is its own status, with a reason. It counts
  as finished but never as completed, and spreads downstream until the path
  rejoins something live. Untaken paths are marked `not_taken`. A Wait Until
  whose target is unreachable fails with `engine.upstream_unreachable`.

**Design.** One delivery-tracking mechanism in `RunContext` serves D5 in
step 1b and D9 in step 3. Step 1b also fixes the Oct 9 Wait Until hang: Wait
Until now fails with a clear message instead of waiting forever.

**Behavior changes queued for step 3:**

- The recovery Skip button spreads the skip downstream instead of running the
  next node with an empty input.
- Untaken paths show as skipped.

Also updated: the `MASTER_BUILD_PLAN.md` step table. Step 1 still waits on the
owner's read of the plan.

## 2026-10-11 — Record Approved Distributed Direction Build Plan

Docs only; no code changes. Branch `ccr-1b2501bf-dgol6g`, based on `main` at
`32e9132`. The plan builds on the Oct 9 investigation and a review of the
WaitRegistry/Refresh Coalescer v2 proposal.

**Approved.** The owner signed off decisions D1–D4:

- providers instead of headless twins;
- triggers launch runs;
- subworkflows as child runs;
- `RunContext` extraction as step 1b.

They also accepted refinements R1–R4:

- step 1 is bug fixes only;
- the unattended policy is passed in at run start;
- per-trigger `single`/`queued` modes first, `restart` once Stop is clean,
  `parallel` at step 6;
- `file` reuse with run-owned temp files, kept when a run fails.

**Added** `DISTRIBUTED_BUILD_PLAN.md`. The wait-for-event node is recorded as
an open question with its tradeoffs, not as a decision.

**Superseded, not deleted:**

- `PROJECT_BACKLOG.md`: superseded banners on the headless twin, Start-node
  variant, nested headless validation, headless-export, watcher and
  completion-notify sections. The text is kept.
- `MASTER_BUILD_PLAN.md`: a step table, with the old Phase N/N+1/N+2 bullets
  kept under a superseded heading.

**Pointers and fixes:**

- Pointers in `AGENT_HANDOFF.md`, `README.md` and `TASK_INDEX.md`.
- Corrected the `NODE_CATALOG.md` Wait Until row (node completion, not a
  Vault key).
- Logged in `DOCS_MIGRATION_NOTES.md`.

**Corrections recorded in the plan:**

- Merge does not stall when a sibling branch fails (corrects the Oct 9 entry).
- `node_timeout_seconds` effectively bounds nothing.
- The backlog's cycle-rejection claim is wrong.

**Probes run during the review:**

- Wait Until hangs when its target was terminated or skipped.
- Stop does not release Wait Until, and a stopped run's waiter wakes inside
  the next run and writes into its memory.
- About 5 events per node, each causing a synchronous full screen refresh.

**Step 1 has not started.** It waits on the owner's read of the plan.
Verification: `git diff --check`, and relative links checked.

## 2026-10-09 — Investigate AOTN Distributed Direction Brief

Investigation only; no code or other doc changes. Started from `main` at
`32e9132` (PR #30). Checked the owner's distributed-direction brief (triggers,
workflow contracts, headless server, supervisor/router, AI inputs, `[error]`
type, error details tab, error mux) against code and docs. Full findings went
to the owner in the session reply; key code facts:

- Triggers, nested workflows, headless CLI and the multi-frontend API are
  already recorded as Phase 19/20 and Phase N/N+1/N+2 in MASTER_BUILD_PLAN and
  PROJECT_BACKLOG. The backlog makes the trigger watcher depend on headless and
  nested workflows. No separate rejection-record file exists in the repo.
- The backend runs without Textual installed (`demo_execution.py` finished).
  Headless runs block forever on any node error (recovery future), user input,
  or a saved breakpoint. `MasterState.start_workflow` does not validate.
- `http_request_node`/`json_path_node` failures write the `error` port but
  route via `default`. The node reports `done`, the run finishes, and a node
  wired to `error` never runs (scratch probe).
- "Dead-drop" and "transient" are synonyms in the docs and code; the second
  output kind is Vault. Config tab 4 is the read-only Connections tab, which
  WAIT_UNTIL_UI_PLAN marks "retain" and tests depend on.
- The backlog's "cycles are rejected by the validator" does not match the code:
  there is no cycle check. `node_timeout_seconds` only bounds Wait Until and
  Merge waits, not `execute()`.

No tests run (no code changed).

## 2026-10-09 — Publish Payload/File Routing PR

Owner confirmed the saved-workflow fixes live and requested a PR. Authoritative
root `/home/makin/src/node_workflow`, starting `main` at `1211e68`; fetched
origin/main and confirmed synchronization. Created `codex/payload-file-routing`
for the accumulated payload/file implementation and saved-workflow follow-up.
Preserved the unrelated Windows-path test file, `Workflow started` output,
and recovery-only checkout. Updated handoff publication status.

Fresh verification: **796 tests passed in 126.79s**; app/helper compilation
and `git diff --check` passed. Publish for review; merging is a separate step.

## 2026-10-08 — Fix Saved File Forwarding And Connected Text Output

Resumed the interrupted follow-up in `/home/makin/src/node_workflow`, `main`,
base `1211e68`. Fetched origin and confirmed already up to date before edits.
Changes remain uncommitted; preserved existing work and the recovery checkout.
Recovered the attached screenshot through `/mnt/c/Users/...` and inspected the
saved file-test graph read-only, without executing or modifying owner files.

Reproduced Writer's configured Content + incoming File Path connection: both
runtime and tracing assumed Content. Both now prefer connected Content and
fall back to connected File Path, preserving the actual incoming payload and
its provenance. A forwarding node without a connected source does not claim
its own result. UI labels follow the selected connected forwarding input.

Start now has one value editor in Parameters, with a read-only live value
preview in Payloads plus its routing controls. Old custom output-name overrides
no longer mislabel its greeting and are cleared on Save. Text Output now shows
selected source, template/label, captured-value preview and routing in Payloads.
Its existing any-input contract is intentional: values are formatted as text;
file references are displayed, not read. This is explained in the UI and tested.

The saved Wait Until was downstream of Text Output b2. Unconditional termination
introduced in the previous build prevented reaching Wait Until at all. Restored
Text Output continuation when connected, naturally ending when unconnected;
End remains an explicit stop. Branch-health traversal follows connected Text
Output nodes. This supersedes the prior unconditional Text Output termination
contract. No change to Wait Until's target/completion barrier was necessary.
The optional routing preference was unanswered; continuation was chosen to
restore the owner's demonstrated existing workflow, as stated during the work.

Verification: **796 full-suite tests passed in 127.58s**. Focused combined regression slice: 46 passed.
Existing Wait Until UI/runtime slice plus new UI/file tests: 38 passed before
continuation changes. New integration covers configured file writes on one
parallel branch and Text Output → Wait Until → File Reader on the other,
waiting for either Writer or its following Text Output, across save/reload and
two runs. Start/Text Output production-CSS mounts cover 60/100/140 columns.
Helper UI checks pass for Start, Text Output and Writer; all three specs were
regenerated in temporary projects, preserving custom runtime implementations.
Compile and whitespace checks pass. Earlier full-run failures were obsolete
Content-only label and terminal-output assertions, corrected to exercise the
new contracts; the integrated End completion log is now asserted explicitly.

Evidence: `docs/audits/payload_followup_2026_10_08/README.md` and
`tests/test_reported_payload_routing.py`. Owner workflows remain unchanged;
reopen/restart the app to load the updated implementation. Native Windows FO7,
line-number insertion and the unreproduced host-prefix issue are unchanged.

## 2026-10-07 — Complete Payload/File Build And Integration Audit

Continued the interrupted build in `/home/makin/src/node_workflow`, `main`,
base HEAD `1211e68` (origin synchronized during this build). All changes remain
uncommitted. Preserved existing edits, unrelated untracked files and the
recovery-only OneDrive checkout. Three agents implemented the file, runtime
and frontend tracks; the integrator finished their audits after usage limits.

Implemented the PAYLOAD_FILE_IO_BUILD_PLAN contract: File Manager rename and
multiple files with selected downstream reference/remaining typed Vault keys;
File Reader configured/upstream/Vault reference reads with independent text
publication; Writer string Content, prepend/append and opt-in newline escapes;
Start typed Vault output; Text Output source dropdown; accurate forwarding
previews/types; compatible source filtering and deleted-reference lifecycle;
explicit terminal nodes; Merge home/selected-sibling carry-forward and capacity
checks. Earlier Content/error-modal keyboard fixes remain included.

Shared audit fixes: actual legacy Vault capabilities gate controls, output
metadata identifies text/number producers, User Text Input declarations carry
string type, nested defaults are copied, and Vault-only outputs are excluded
from upstream choices. Saved file forwarding uses `transient_output=False`
to suppress the own result, not the forwarded input; both runtime and source
eligibility now preserve that distinction with regression coverage.

Versioned migrations preserve old values under `_config_migrations` and unknown
config keys. Retired file termination flags become continuation; End/Text Output
express terminal paths. Text Output legacy multi-key source selection requires
choosing one. Existing Reader configs remain Configured. See the build plan for
all migration details. Preserved the original Reader path tests in a dedicated
file after helper generation replaced the generated test file.

Verification: **784 full-suite tests passed in 121.97s**, including the full debug suite. Compile checks passed for app/helper and
`git diff --check` passed. Helper UI contracts passed for Reader, Writer,
Manager, Start and Text Output. Mounted production-CSS audit: 37 types in the
registry, 36 editable types, 108 mounts at 60/100/140 columns; 36/36 Cancel,
72/72 unrelated-config preservation, 72/72 repeated-save equality, 163
conditional states, no state exceptions. Both integrated home/sibling Merge
workflows pass, including save/reload, file/text Vaults, Reader/Writer,
terminal output, and deletion/undo. Earlier failed runs exposed obsolete UI
fixtures/error wording; updated tests retain their behavioral assertions.
Evidence: `docs/audits/payload_file_io_2026_10_07/`.

Remaining: numbered-line insertion is deferred. Native Windows/window placement
and owner's live terminal FO7 remain manual checks. The quoted Windows example
normalizes to its existing WSL path; the reported `makin@kelly:` prefix was not
reproduced and its origin is unconfirmed. No claim of live Windows verification.

## 2026-10-07 — Add Windows Copy-As-Path Investigation To Build Plan

Owner reported a quoted Windows path displayed as
`makin@kelly:/mnt/c/Users/makin/Documents/App_Tests/test.md` on execution.
Authoritative root `/home/makin/src/node_workflow`, `main`, HEAD `1211e68`;
origin/main synchronized. Preserved existing edits and unrelated files.

Read-only check of the exact quoted Windows input through normalize_local_path
returned `/mnt/c/Users/makin/Documents/App_Tests/test.md`; is_file was True.
No contents read or file changes made. Current converter does not construct a
user/host prefix, and FileViewerScreen displays the supplied path directly.
The expected WSL translation is verified; the reported prefix/UI symptom is
not reproduced and remains open.

Added P0a to PAYLOAD_FILE_IO_BUILD_PLAN and linked the concern in PROJECT_BACKLOG:
trace config/reference/event/display separately, preserve entered paths,
classify drive/UNC/POSIX forms with runtime OS rather than slash direction alone,
retain wslpath for actual mount mappings, and define extended/WSL-share/network
support and errors. Path tests must cover Save/reopen and complete execution,
not only the converter. File track owns this before new file-access features.

Existing Reader/path regression slice **61 passed in 0.11s**; this does not
establish coverage of every newly planned path form. Local plan Markdown links
and `git diff --check` passed. No runtime changes; documentation uncommitted.

## 2026-10-07 — Rename File Manager And Plan Reader Text Routing

Owner renamed File Viewer to File Manager and requested File Reader contents
as text transient/Vault payloads. Authoritative root
`/home/makin/src/node_workflow`, branch `main`, HEAD `1211e68`; origin/main
fetch/fast-forward merge up to date. Earlier dirty/untracked work preserved.

Changed the node's display name and new-node default alias to File Manager,
aligned its helper spec and existing generated metadata expectation, and updated
NODE_CATALOG. Internal `file_view_node`, viewer screen/event identifiers and
existing saved aliases remain intact. The node still displays one file until
the planned multi-file stage lands.

Existing FileReaderNode already reads a configured UTF-8 file into downstream
text. Extended PAYLOAD_FILE_IO_BUILD_PLAN with P2a to add typed file-reference
Upstream/Vault sources and independent typed string downstream/Vault outputs;
preserve old file_path/port identities, read-only behavior, empty-file handling
and current Windows/WSL normalization. Reader remains separate from Manager's
file-reference output. Updated track ownership, integration scenarios and
CONFIG_UI_BUILD_PLAN/MASTER_BUILD_PLAN/PROJECT_BACKLOG links. Reader extensions
are planned, not implemented; no duplicate Reader node added.

Verification: `check_node.py file_view_node` compiled the application and passed
**9 existing node tests**; `check_ui.py file_view_node` passed. Local Markdown
links and `git diff --check` passed. No new tests needed for the label-only
runtime change; no full-suite rerun. Changes uncommitted.

## 2026-10-07 — Plan Payload, Vault And File I/O Follow-up

Owner requested a coordinated build plan for forwarding preview/source-type
defects, Start/Text Output Vault controls, multi-file Viewer, Writer newline and
top/bottom insertion, completion-checkbox removal and Merge branch choices.
Worked in `/home/makin/src/node_workflow`, `main`, HEAD `1211e68`;
fetch/fast-forward merge origin/main up to date. Preserved earlier uncommitted
fixes and unrelated untracked files; recovery checkout untouched.

Investigated current code. Found legacy-only pass-through detection, first-input
tracing, Start's absent Vault write, Text Output's absent standard source/Vault
read, Writer Content declared any, empty-Vault-only source pruning, single-file
Viewer execution, file completion controls and selected-beacon-only Merge carry
choices. Noted Sleep forwards incoming data and `next_node_id: None` does not
stop connected traversal. These are code findings; exact owner graphs were not
live-reproduced. No application changes or agents launched in this planning task.

Created PAYLOAD_FILE_IO_BUILD_PLAN with P0–P6, shared type/provenance contracts,
separate frontend/runtime/file/integrator ownership, serialized shared-file
editing, multi-file declaration/execution rules, migration decisions, explicit
line-number TODO and behavioral/live verification gates. Linked it from README,
TASK_INDEX, CONFIG_UI_BUILD_PLAN, MASTER_BUILD_PLAN and PROJECT_BACKLOG. The new
owner terminal-node direction is identified as superseding the old optional
checkbox policy, with old-save migration to settle before implementation.

Documentation-only verification: local Markdown links and `git diff --check`.
No new application tests run; prior **686 passed** remains the last completed
implementation baseline. Plan and related documentation are uncommitted.

## 2026-10-07 — Hide Deleted File Producers From Vault Source Pickers

Owner reported deleted file-reference producers still offered as Vault sources
for new File I/O nodes. Authoritative root `/home/makin/src/node_workflow`,
branch `main`, starting HEAD `1211e68`; fetch/merge origin/main up to date.
Preserved all earlier uncommitted fixes, unrelated untracked file, and the
recovery checkout.

Found two causes: soft-delete is a frontend overlay, so scanning backend
configs counted deleted nodes as live writers; after tombstone materialization
or permanent removal, leftover Vault values were treated as external entries.
Editor now passes its workflow adapter to NodeConfigScreen. Writer declarations
use the adapter to recognize soft deletion and tombstones, retain original
keys with no active writer ids, and filter those keys from compatible source
options. A surviving eligible writer keeps a shared key available. Persisted
file entries without a current graph declaration are hidden even after full
removal or replacement. Vault data and tombstone restoration remain intact;
undo restores choices. External nonfile entries retain existing compatibility.
Saved invalid selections remain visible as not declared for repair; fresh
consumers do not offer those choices or an empty Vault source option.

Added 15 regressions covering Viewer/Writer producers before/after execution,
soft delete/undo, JSON save/reload and restore, permanent removal, replacement,
shared parallel keys, self/downstream exclusions after parallel deletion,
external nonfile values, and mounted editor-to-config Writer/Viewer/Window
Control source pickers with fresh and previously saved selections. Updated
NODE_STANDARDS eligibility documentation. Initial mounted tests accidentally
selected the editor's highlighted deleted row; fixed the fixture to select the
consumer's actual displayed row. Final new regression slice **15 passed**;
existing config/tombstone/Vault slice **35 passed**. Frontend compilation and
`git diff --check` passed. Full application suite **686 passed in 118.51s**;
final `git diff --check` passed. UI verification used headless Textual with
production CSS; live-terminal verification remains with the owner.
Changes uncommitted.

## 2026-10-07 — Reuse Same-File References And Clarify Output Labels

Owner confirmed the rewired workflow works, then asked to automatically reuse
a file reference used as input instead of suggesting incremental references to
the same file. Authoritative root `/home/makin/src/node_workflow`, branch `main`,
starting HEAD `1211e68`; fetch/merge origin/main up to date. Preserved all earlier
fixes, unrelated untracked file, and recovery checkout.

References already use resolved paths as identity, not incrementing counters.
File Writer now retains the actual source reference and resource key when it
writes the same file. This matches Viewer/Window Control reuse and preserves
noncanonical incoming keys. Create unique still returns a new reference when
it writes another file. Vault outputs keep the file reference even when
downstream forwarding emits Content; output remains usable by later nodes.

Shared file-output Payloads forms explain reuse and label the editable name
Display name. Additional Vault keys are explained as names for the same file,
not copies or versions. File Writer advertises its forwarded input in ui_hints
and its helper spec; the shared checkbox now explicitly names Content, avoiding
the misleading suggestion that selecting it is required to reuse File Path.
No automatic checkbox changes or disabling of downstream/Vault output.

Added 20 regressions: upstream/Vault references, repeated Overwrite/Append,
forwarding on/off, with/without RunSession, preserved keys/registered handles,
distinct Create unique file identity, reconstruction of a reference missing its
identity key, and mounted 60-column Writer/Viewer copy.
Updated Windows-path expectations to preserve incoming typed references while
still converting paths for actual file access.

Focused affected-file slice **95 passed**; Writer/Viewer UI helpers, compilation,
and `git diff --check` passed. First full run: **669 passed / 1 failed** in the
previously intermittent Settings navigation test. It directly moves focus and
toggles a checkbox without awaiting queued messages before switching tabs;
added a Pilot pause at that boundary. No Settings production code changed.
Final reference + Settings slice **21 passed**. Final full application suite
**671 passed in 116.26s**. Writer forwarding hint matches its normalized helper
spec; final `git diff --check` passed. Headless UI used production CSS; owner
live-terminal verification remains.
Changes uncommitted.

## 2026-10-07 — File Viewer Vault Reference And Downstream File Wiring

Owner confirmed Windows file access and reported File Writer failing to receive
File Viewer's reference. Requested default reference downstream unless forwarding
is selected, and an independent optional typed Vault reference accessible to
parallel branches. Authoritative root `/home/makin/src/node_workflow`, branch
`main`, starting HEAD `1211e68`; fetch/merge origin/main up to date. Preserved
all preceding fixes, the unrelated untracked file, and recovery checkout.

- Viewer already emitted a file reference by default. Added optional Vault
  output metadata/defaults and execution that writes the viewed reference with
  type `file`, independently of downstream forwarding. Updated its helper spec;
  reused standard Payloads controls without custom node-screen UI.
- Identified editor insertion always wiring the first input: File Writer
  Content, leaving File Path empty. Prefer a unique exact metadata type match;
  new typed non-first-input connections select Upstream in that input's source.
  Insert-between reconnection uses the same selector. Unknown/forwarded or
  ambiguous output types retain the existing first-input behavior.
- On configuration Save, move an inactive connection (its input now Configured
  or Vault) to a unique matching unconnected Upstream input. This repairs the
  existing Viewer→Writer Content misconnection when Content is Configured/Vault
  and File Path is Upstream. Preserve active Content wiring and configured paths;
  no automatic load/refresh migration or changes to owner's saved workflows.
- Added eleven tests: Viewer default/pass-through × Vault on/off, real
  Viewer→Writer execution after insertion and existing-config Save, preservation
  of intentional/occupied wiring, mounted production-CSS Vault controls/save/type
  declarations with forwarding on/off, and actual parallel Vault consumers.

Focused routing tests **11 passed**; existing Viewer/path tests **44 passed**.
Viewer node/UI helpers, normalized helper-spec optional Vault defaults,
compilation, and `git diff --check` passed. Final full suite **651 passed in
116.19s**. First full run had **649 passed / 1 failed** in the existing Settings
modal navigation test (late tab change); it passed in isolation and unchanged
in the final full run. Added occupied-port insertion preservation before that
final run. No Settings production changes were made.
Changes uncommitted; owner must restart and save the existing Writer config to
apply the connection repair.

## 2026-10-07 — Windows Copied Paths And Error Dialog Keyboard Recovery

Owner supplied two Error Details screenshots: File Viewer could not find an
existing Windows path under WSL, and File Writer reported an empty path. Both
dialogs lacked command navigation. Authoritative root
`/home/makin/src/node_workflow`, branch `main`, starting HEAD `1211e68`;
fetch/merge origin/main was up to date. Preserved the preceding Content editor
fix, unrelated untracked Windows-path-named file, and recovery checkout.

- File Writer and File Viewer now use the existing `normalize_local_path`
  service at execution, offloading WSL conversion to a thread. Quoted Windows
  Copy as path values work with Configured, upstream, and Vault sources;
  configured-path preflight uses the same normalization. Helper specs retain
  the matching schema hint without regenerating hand-written execution.
- Confirmed the exact screenshot's `test.md` exists at its `/mnt/c/...`
  equivalent. Executed the viewer node against quoted and unquoted copies:
  both completed and emitted the correct Linux path. Did not write that file.
- An empty selected path source remains an error. Writer now names the source
  and explains where to supply the path; no implicit source fallback was added.
- Error Details adopts CommandScreenMixin and vertically arranged buttons,
  human-readable recovery labels, and a scroll container. Deferred first focus
  reveals buttons after long-traceback layout; validation jump/Close controls
  share the behavior. App Back yields to Error Details so Ctrl+Q runs dismissal
  and clears the pending-error flag via the callback.
- Added 35 path tests covering sources, quoted paths, session/no-session,
  reference identity, preflight, conversion failures, and missing-source help.
  Added 15 production-CSS keyboard tests using the real app, three widths,
  long tracebacks, all recovery actions, dismissal callbacks, and validation
  jumps. Early tests exposed default App Ctrl+Q interception and initial scroll
  timing; final tests use the real app and deferred focus.

Verification: path/Reader/Writer/Viewer slice **91 passed**; error UI slice
**15 passed**; final full application suite **640 passed in 112.66s**.
Writer/Viewer node and UI helpers, compilation, and `git diff --check` passed.
Real WSL path/node verification passed; keyboard checks used headless mounted
production CSS, with owner live-terminal verification remaining. Changes
uncommitted.

## 2026-10-07 — Restore Visible File Writer Content Editing

Owner reported that File Writer Content appeared unable to enter editing after
selecting Configured in Source and switching to Parameters. Authoritative root
`/home/makin/src/node_workflow`, branch `main`, starting HEAD `1211e68`;
fetch/merge origin/main was up to date. Preserved the unrelated untracked
Windows-path-named file and left the recovery checkout untouched.

Production-CSS reproduction showed a two-row TextArea with zero content rows.
E correctly entered editing and accepted text, but the border-only layout hid
both text and cursor. Generated multiline/code fields now default to six rows
when their schema omits height; explicit schema heights retain their behavior.
No node execution or keyboard bindings changed. Documented the sizing rule.

Added a mounted File Writer regression at 60/100/140 columns and 24 rows:
enable Configured from Source, switch with 2, verify visible content geometry,
activate with E, type multiline text including navigation letters and a digit,
leave with Escape, navigate, and Save with the text preserved. Synthetic
workflow remains untouched until the caller applies the returned config.

Verification: focused regression passed; full application suite **590 passed
in 99.61s**. Compilation and `git diff --check` passed. Headless mounted tests
used production CSS; live owner-terminal verification remains. Changes
uncommitted.

## 2026-10-07 — Publish Confirmed Fixes And Synchronize

Owner confirmed the node UI fixes live and requested a PR and an up-to-date
project. Reuse existing PR #29 on `codex/wait-until-vault-fix`, which remained
open after fetching origin; main baseline `7161ef2`, starting HEAD `6b34303`.
Include the tested File Reader/path documentation and visibility/scroll audit
work in the integrated PR. Owner authorized merging and checkout synchronization;
GitHub and Git history record the resulting merge commit. Preserve the unrelated
Windows-path-named test file and the recovery checkout. Refreshed current agent
handoff with verified coverage and the remaining capability/layout work.

Verification before publication: 589 tests passed, final 108-mount audit clean,
compilation/helpers passed as recorded below; `git diff --check` passed.

## 2026-10-06 — Audit Every Editable Node For Visibility And Scrolling

Owner confirmed the preceding UI fix and requested a whole-node audit of
toggle-dependent controls, convenience reasons for retained information, and
scrolling. Authoritative root `/home/makin/src/node_workflow`; branch
`codex/wait-until-vault-fix`; starting HEAD `6b34303`, with preceding session
changes dirty. Fetch/merge origin/main was already up to date. Preserved those
changes and the owner's untracked Windows-path-named test file. No recovery
checkout changes, commit, push, PR merge, or new platform integration.

- Reviewed registered schemas/execution use and mounted all 36 editable types,
  including compatibility Start/End and excluding the internal tombstone.
  Reused owner-safe synthetic audit helpers with explicit production CSS.
- Added schema visibility for Text Output's user-input prompt, Set Variable's
  literal value, Conditional's variable name, and HTTP's POST body. Updated
  HTTP helper spec alongside the executable schema without regenerating its
  custom execution. No backend execution logic changed for these controls.
- Hide unavailable legacy Write to Vault checkboxes on both setter types while
  forwarding; no useful visible disabled choices remain in the audited states.
- Removed competing automatic/deferred scroll reveals. Shared focus helper
  supports caller-owned scrolling; Node Config opts out and reveals only its
  current focused target after layout. Other screens retain existing behavior.
  Guard against stale reveal requests and avoid scrolling outside the tab.
- Added NODE_CONFIG_VISIBILITY_SCROLL_AUDIT, before/intermediate/final evidence,
  reproducible audit runner with optional failure gate, and convenience reasons
  for read-only previews, wiring, empty states and still-active parameter fields.
  Updated README/TASK_INDEX, shared style standards and the UI build plan.

Final actual verification: **589 full-suite tests passed in 92.82s**.
**108 mounts**, **1,202 toggle/source states**, **4,008 navigation samples**,
Cancel unchanged **108/108**, **zero** final scroll findings, generated-rule
visibility mismatches, or visible disabled selectors/checkboxes. Explicitly
validated the saved final summary. Focused visibility/scroll tests: **17 passed**;
earlier affected-UI subset: 48 passed (overlaps). HTTP node helper/five tests and
UI helpers for HTTP Request, Text Output, Set Variable, Conditional passed.
Compileall app/helper and `git diff --check` passed.

Retained rapid-before scan's transient candidates rather than claiming 226 real
defects. Settled-before confirmed one Image Generation scroll failure and two
visible disabled checkboxes; intermediate three-width scan exposed two further
short-viewport failures in Conditional/Embedding. All are clear in the final
scan after consolidating the scroll path. Evidence uses synthetic populated
Vaults, 24-row headless WSL screens, and one-factor selector variants; it is not
exhaustive combinations or native/live accessibility verification. Unsupported
runtime Vault controls, empty tabs, simulated-AI options and platform capabilities
remain separately scoped in CONFIG_UI_BUILD_PLAN.

## 2026-10-06 — Hide Toggle-Dependent Config And Fix Initial LLM Scrolling

Owner requested hidden dependent configuration instead of disabled clutter,
and first-field focus without the initial LLM tab jumping to the bottom.
Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, starting HEAD `6b34303`. Fetch/merge origin/main
was already up to date. Preserved pending File Reader/docs edits and the owner's
untracked test file. This work remains local and uncommitted.

- Shared legacy Vault lists and empty-state messages hide until reads are
  enabled. Write count, label, and rows hide until writes are enabled. Keep
  hidden edited rows mounted so toggling back restores unsaved values.
- Hide standard downstream name/description rows when forwarding incoming
  data, and Vault key/description rows when output is disabled. Merge's carry
  selector, label, and details hide until a branch is selected. Hidden fields
  remain excluded from keyboard navigation and preserve appropriate values.
- Only changes on the focused widget may request scrolling, including the
  deferred callback. Initial/programmatic events no longer scroll toward
  unhighlighted fields. Config navigation reveals its current target without
  pre-scrolling to the next neighbour. First-field/tab focus remains intact.
- Added the general visibility and scrolling rules to UI_QUICK_REFERENCE;
  updated NODE_STANDARDS routing examples and CONFIG_UI_BUILD_PLAN. This is a
  focused stage-2 slice; stage-1 capability auditing and empty-tab cleanup remain.

Final verification: **580 full-suite tests passed in 86.24s**, including eight
new production-CSS UI tests covering Text Output and LLM at 60/100/140 columns,
toggle preservation, hidden navigation exclusion, Cancel preservation, initial
scroll position, non-focused changes, and routing visibility. Existing Merge
test now checks hiding/reappearance as branches are selected. Compilation and
Chat Completion/Text Output helper UI checks passed. Merge helper reports
structural UI is unsupported; the actual mounted Merge test passed instead.
`git diff --check` passed. An intermediate callback rename missed the selection
list handler; that failure was corrected before the final complete suite.

## 2026-10-06 — Owner-Confirmed WSL Fix And Future OS Support Direction

Owner confirmed the File Reader path fix works in the running app. Documented
WSL/Linux as the current development/debugging environment and Windows, macOS,
and Linux app versions as the intended future product direction in
PROJECT_KNOWLEDGE and PROJECT_BACKLOG. Nodes should adapt to actual runtime
paths and capabilities through platform adapters, with clear unsupported-operation
feedback and native verification before support claims. No packaging or additional
OS integration was implemented by this documentation change.

Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, HEAD `6b34303`. Fetched origin and merged origin/main:
already up to date. Preserved the pending File Reader changes and the owner's
untracked test file. Verification: `git diff --check` passed; no tests rerun for
this docs-only change. Prior actual full-suite result remains 572 passed.

## 2026-10-06 — File Reader Copied Windows Paths And Read Errors

Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, starting commit `6b34303`, initially clean.
Fetched origin and merged origin/main: already up to date. Changes remain local
and uncommitted; no PR merge or recovery-checkout changes.

- File Reader removes paired copied quotes and surrounding clipboard whitespace,
  expands home paths, and converts Windows paths using `wslpath` under WSL.
  Conversion during execution runs in a worker thread. Native Windows paths
  retain their normal behavior; incompatible Windows paths on other systems
  produce guidance rather than a misleading missing-file error.
- Schema opt-in `normalize_local_path` keeps pre-run validation consistent with
  execution without changing other file nodes. Missing files remain warnings
  because earlier nodes can create them. Empty, null-containing, incompatible,
  or unconvertible paths produce errors. Stored workflow config is preserved.
- Runtime errors explain missing files, folders, denied access, and non-UTF-8
  content. Both direct reads and RunSession handle reuse are covered.
- Verification: **572 full-suite tests passed in 72.29s**, including 26 focused
  File Reader tests. Helper `check_node.py file_reader_node` (including compileall)
  and `check_ui.py file_reader_node` passed. Real temporary Windows-drive file
  read under WSL passed quoted/unquoted with and without RunSession (four checks).
  Native Windows handling was simulated, not live verified. `git diff --check`
  passed. Legacy File Reader has no helper spec; its implementation was edited
  directly and its focused helper test added without regenerating the node.

## 2026-10-06 — Next-Session Project Rundown

Rechecked Git and GitHub: PR #29 open, unmerged and mergeable; main remains
`7161ef2`. Added SESSION_SUMMARY.md, corrected stale selector/AI/status roadmap
paragraphs, and linked the rundown from the docs entry point and handoff. This
is a docs-only follow-up on the same PR. No new runtime/UI changes or tests;
546-test integration result above/below remains the last actual full run.
`git diff --check` passed. Real Windows FO7 and remaining UI stages stay open.

## 2026-10-06 — Integrate File Output, Repair Audit Blockers, Prepare One Session PR

Authoritative root `/home/makin/src/node_workflow`; branch
`codex/wait-until-vault-fix`. Fetched origin/main `7161ef2`, already current.
Preserved prior dirty runtime/UI/tests/docs in checkpoint `1c4a57e`, then merged
File Output `0a19718` in `95f9049`. Resolved SESSION_LOG conflict by preserving
both histories. No recovery-copy changes, stash/reset, or automatic main merge.

- Added `SESSION_INTEGRATION_BUILD_PLAN.md` and `CONFIG_UI_BUILD_PLAN.md`,
  reconciled current handoffs/roadmap, retained original audit evidence and
  documented unresolved findings with priorities and follow-up verification.
- Integrated File Write, File Viewer, Window Control, Markdown formatting,
  typed file refs, optional Windows adapter and launcher work. Registry 37;
  actual selector 34; editable/user-facing 36; tombstone intentionally internal.
- Fixed arbitrary ambiguous window selection and nonunique title matches;
  offloaded blocking launch/discovery, kept resource registration on the loop;
  missing OS opener logs a warning after successful writing.
- File view events are scoped to the active displayed run and queued FIFO;
  input/recovery modal priority and retired-run queue reset are explicit.
  Updated mounted test that formerly specified dropping a second request.
- Removed Window Control's unsupported forwarding capability/control in spec
  and executable metadata. Kept its existing fixed selected-reference output.
- Shared save overlays existing config. Descriptions wrap beneath fields;
  stylesheet controls CommandInput width and labels leave input room.
  Wait Until remains Wait/Connections and never accesses the Vault.
- Added write-path schema intent, avoiding missing-input warnings for new
  destinations while retaining empty-required-path errors. Chat temperature
  zero reaches the provider unchanged. Helper specs match these metadata fixes.
- Added meaningful regression tests for ambiguous discovery, slow launch loop
  responsiveness, queued displays, config preservation, geometry and a real
  parallel File Write → Wait Until → explicit Vault File Viewer workflow.

Actual verification of the integrated tree:

- Final full suite: **546 passed in 71.26s**. Earlier full attempt: 544 passed,
  one expected-old-viewer-policy test failed; that test was updated to the new
  FIFO contract, passed narrowly, then the final whole suite passed.
- Focused initial checks: 94 passed; integration/Wait/Chat checks: 44 passed;
  final session regressions including parallel file/Vault: 15 passed; mounted
  viewer tests: 2 passed. These overlap; do not sum them as a baseline.
- Compileall app/helper and helper UI checks for File Write, File Viewer,
  Window Control and Wait Until passed. `git diff --check` passed.
- Current production-CSS audit: **108 mounts**, 306 alternate states, no state
  errors; Cancel unchanged 36/36; unrelated config retained and stable second
  saves 72/72; variant roundtrips **115/115**, zero mismatches. Nine focused
  fields fit at 60/100/140. Synthetic data only; no owner workflows/settings.
- Evidence under `docs/audits/integrated_2026_10_06/`; before-fix artifacts retained.

Outstanding: capability-gating legacy Vault controls, broader tab/layout cleanup,
other schema/numeric/routing descriptions and port issues recorded in
CONFIG_UI_BUILD_PLAN; unsupported-window explanations/validation and Windows FO7
live owner checks. File Reader still uses configured paths. Large file work,
window heuristics and complete live accessibility remain unverified. No broad
UI redesign or new node behavior was silently introduced.

Published one session PR: [#29](https://github.com/makinster/node_workflow/pull/29),
“Integrate file workflows and fix Wait Until/configuration UI blockers,” targeting
main. Verified feature/main ancestry, pushed `5f944de`, and attached the PR to
this chat. This publication record is a final docs-only commit on the same PR.
Main remains unchanged pending PR review.

## 2026-10-06 — File Output Integration Review

Reviewed fetched `origin/claude/file-output-pywin32-32tnv9` at `0a19718`
against authoritative `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, HEAD/origin-main `7161ef2`, including dirty
runtime/Wait Until code. Preserved existing work; no application edits,
feature merge, checkout switch, stash, commit or push.

- Added `FILE_OUTPUT_INTEGRATION_REVIEW.md`: architecture fit, current UI
  inventory, six prioritized findings, integration order and explicit limits.
- Git merge-tree found only SESSION_LOG conflict between committed branches.
  Temporary three-way Python source overlay found no conflicts against actual
  dirty files; it preserved pending runtime fixes and current chat resources.
- Corrected source-overlay verification: **304 passed in 59.16s**, including
  feature-changed tests and both pending Wait Until suites. This is not an
  installed merged-tree/full-suite baseline. Initial harness configuration/CSS
  path errors were corrected; they were not application regressions.
- Mounted three incoming config screens at 60/100/140 × 24 with production CSS;
  nine mounts, all four tabs captured, combined registry 37. This extends review
  evidence but does not replace exhaustive conditional/keyboard/save audits.
- Deterministic ambiguous-window probe selected HWND 202 despite no title match:
  document as P1 along with blocking synchronous launch polling. No real window
  opened/controlled. Other findings: dropped viewer requests, ineffective Window
  Control forwarding toggle, platform explanations and writer-path warnings.
- File Reader still only accepts a configured path; typed-reference consumption
  is an explicit future scope decision. Wait Until still has no Vault behavior.
- Evidence/harness: `docs/audits/file_output_2026_10_06/`. `git diff --check`
  passed. Windows FO7 protocol, actual integrated full suite and exhaustive new
  node interaction audit remain outstanding. Owner display-policy choice remains.

## 2026-10-06 — Pending Work Review Before Configuration Build Plan

Authoritative root `/home/makin/src/node_workflow`, branch
`codex/wait-until-vault-fix`, HEAD `7161ef2`. Fetched origin and merged
origin/main: already current, zero divergence. Existing uncommitted changes,
audit artifacts and recovery checkout preserved; no application code changed,
no commits/pushes/feature merges made in this review.

- Reviewed pending answer-Vault publication, transient-before-completion ordering,
  stopped-input cancellation, W/S typing, zero-timeout semantics, Wait/Connections
  composition, target/timeout validation, Save/Cancel and helper adaptation.
  Reviewed both new test files and pending design/standards/audit documents.
- Added PENDING_CHANGES_REVIEW.md with file-group dispositions and remaining
  readiness limits. No additional runtime defect confirmed. Wait Until's
  production-CSS timeout clipping (audit F03) prevents visual sign-off despite
  green functional tests; keep the focused design and fix shared sizing later.
- Inspected fetched File Output feature `0a19718` read-only: nine feature-only
  commits and nine main-only commits, 48 changed files. Adds File Write, File
  Viewer, Window Control and Markdown mode; removes File Instance demo. FO7
  Windows checks remain pending on that branch. This was an integration-impact
  check, not full validation of that feature; no separate checkout or merge.
  GitHub PR status unverified because gh is unavailable.
- Updated current handoff, roadmap, backlog and documentation routes to the
  configuration build-plan checkpoint; retained historical entries/proposals.
  Flagged File Output baseline selection before finalizing a build plan and
  linked the existing audit/Wait Until plan to the reviewed state.
- Fresh verification: full `pytest tests/ -q` **445 passed in 64.00s**;
  compileall for app/helper passed; `check_ui.py wait_until_node` passed;
  local documentation links and git diff --check passed. No owner live UI or
  Windows verification claimed. Pending work remains local and uncommitted.

## 2026-10-06 — Configuration UI Audit and Staged Plan

Branch: `codex/wait-until-vault-fix`, starting/current HEAD `7161ef2`, authoritative
`/home/makin/src/node_workflow`. Fetched origin and merged origin/main: already
up to date. Preserved all 18 initially modified and five untracked files; no
runtime/UI implementation edits, commits or OneDrive recovery changes.

- Added NODE_CONFIG_UI_AUDIT.md: all 35 registered types, 32 selector-visible
  types, group/mode coverage, current/recommended controls, 12 prioritized
  findings, deliberate exclusions/history, reusable fixes and six small stages.
- Mounted 34 configurations (including automatic Start and legacy End; intentional
  Tombstone exclusion) at 60/100/140x24 using production styles.tcss. Captured 102
  width records, 278 alternate states, 68 default save/reopen mounts and 87
  additional changed-mode/routing save/reopen cases. The 87 selected values all
  persisted; all 34 Cancel cases left stored data unchanged. Default second-save
  results were stable, but unrelated config survived only on Wait Until (33/34
  other screens lose it). Assertions document defects, not expected future behavior.
- Confirmed unsupported generic Vault controls, registered File Instance demo
  stub exposure, shared save-key loss and off-screen inputs under production CSS.
  Wait timeout starts at x=80 at 60 columns; CommandInput's inline 100% width and
  inline descriptions defeat row sizing. Existing bare-App tests miss this.
- Additional findings cover irrelevant conditional fields, empty/duplicate tabs,
  ignored Random Number Payload, numeric coercion, Chat forwarding/blank keys,
  unused simulation credentials, inaccurate Echo/Repeat descriptions and helper
  contract gaps. Fake-provider probe confirms Chat temperature 0 is sent as 1.
- Retained scripts, complete control inventory, compressed raw evidence and
  terminal text/SVG receipts under docs/audits/node_config_2026_10_06. Updated
  README and TASK_INDEX routes without replacing preceding session edits.
- Verification: Python 3.14.4/Textual 8.2.7; focused pytest command covering
  test_wait_until_ui.py, test_chat_completion_node.py, test_node_helper.py,
  tests/generated and test_debug_nodes.py: **232 passed in 55.27s**. Audit scripts
  compiled; packaging coverage assertions, local Markdown links, matrix coverage,
  and git diff --check passed. No new full-suite result claimed.
- Limitations recorded: one-factor alternate states rather than exhaustive
  combinations, no full per-field live keyboard/accessibility sign-off, no real
  providers, and no per-node disk export/reload audit. Owner live review and demo/
  termination/Chat contract decisions remain; broad implementation has not begun.

## 2026-10-06 — Wait Until Focused UI and Shared Section Standard

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; fetched origin/main,
merge already current. Preserved preceding runtime fixes/design documentation.

- Implemented Wait + Connections tabs: alias, graph-derived targets, timeout,
  unchanged dead-drop explanation and read-only route; removed Vault reads/writes,
  payload reveals and editable output metadata from Wait Until.
- Bounded target list, explicit unavailable-target rows, selected-count/empty
  hints, list-boundary keyboard movement and per-tab focus/scroll restoration.
  Save rejects invalid/non-finite/negative timeouts and invalid selected targets.
- Save preserves unrelated config and clears retired Wait Until membank/transient
  declarations; opening/Cancel does not mutate workflow config. SaveManager's
  existing derived input_sources calculation removes stale Vault read claims.
- Updated NODE_STANDARDS, UI_QUICK_REFERENCE, TUI_DESIGN, AGENT_START_GUIDE and
  NODE_HELPER: shared section meanings, only applicable controls/tabs, consecutive
  number navigation, flat/focused forms allowed. Other node layouts unchanged.
- Updated Wait Until UI plan, task routes, roadmap/handoff and helper UI check
  for timeout's placement in Wait. Initial full run caught an omitted Ctrl+Q revert
  hint; restored it before final rerun.
- Added 12 mounted regressions covering 60/100/140-column layouts, long-list
  navigation, tab focus/scroll, typed letters/digits, unavailable targets,
  timeout validation, toggle/no-target cases and save/cancel configuration.
- Focused execution/UI suites **52 passed**; check_ui.py wait_until_node,
  compileall, git diff --check and local documentation-link checks passed.
  Final full suite: **445 passed in 63.03s**. No owner live UI
  confirmation yet; restart app for the configuration change. Uncommitted.

## 2026-10-06 — Wait Until Configuration UI Plan

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; fetched origin/main,
merge already current. Preserved all prior dirty runtime/design work.

- Mounted current Wait Until screen to inventory controls across all four tabs.
  Legacy generic composition exposes unsupported Vault reads/writes, previews
  and output metadata; help copy incorrectly advertises A/D tab navigation.
- Proposed two tabs (Wait, Connections), targets and timeout together, fixed
  pass-through explanation, keyboard/list navigation and responsive scrolling.
- Specified explicit stale-target handling, no-target immediate pass-through,
  save-only removal of obsolete Vault declarations and derived source refresh.
- Added WAIT_UNTIL_UI_PLAN.md and documentation routes. Design only; config UI
  remains unchanged. Verification: mounted inventory, git diff --check and local
  Markdown links passed. No runtime suite rerun for this docs-only task.

## 2026-10-06 — Wait Until Zero Timeout Means Forever

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; origin/main already current.

- Owner confirmed the cross-branch flow works live after the input fixes and
  requested 0.0 mean wait forever and remain default. Previously zero became
  None and Supervisor substituted the global timeout. Pass zero explicitly;
  positive values still enforce a limit. Updated Parameters description.
- Extended four cross-branch LLM cases with zero/positive timeout variants and
  a shorter in-memory global timeout to prove zero does not inherit it.
- Focused new/execution suites **40 passed in 7.21s**; compileall and diff checks
  passed. Prior full suite **429 passed** before this timeout edit; not rerun.
- Initial test setup mistakenly persisted a 0.005 global timeout. Test now uses
  monkeypatch on the in-memory cache; local global timeout restored to 30 seconds.
  The prior custom value was not captured. Other settings retained.

## 2026-10-06 — User Input Dialog Drops W/S While Typing

Branch: `codex/wait-until-vault-fix`, base `7161ef2`; fetched origin/main,
merge already current. Existing dirty design/runtime work preserved.

- Owner reported continued-session missing context at node_8ec97b0a. Exact saved
  workflow diagnostic using fake provider held the second LLM until input, wrote
  `user_text`, and completed both calls successfully. Running app was canonical
  and started after the earlier Vault fix; stale code was not assumed.
- Mounted dialog reproduction found auto-edit input treats W/S as navigation
  while editing: a single w/s yielded empty input and sentences lost characters.
  This can cause the reported error; owner's exact typed answer/timing remains
  unconfirmed. Backend-only tests missed this keyboard path.
- UserInputScreen explicitly starts ordinary text editing on mount. W/S now type
  during editing; command navigation resumes after edit. Shared auto-edit behavior
  for other screens remains intact. No saved workflow or live process modified.
- Added four mounted typing/submission regressions: all failed before the change,
  all pass afterward. Focused suites **36 passed**; full tests/ **429 passed in
  52.25s**; compileall and git diff --check passed. Updated investigation/handoff.
  App restart required to load the new UI code; no live owner verification yet.

## 2026-10-06 — Cross-Branch User Input Vault Fix

Branch: `codex/wait-until-vault-fix`, based on merged main `7161ef2`;
fetched origin/main and merge was already current. Preserved uncommitted branch
UI design/investigation docs from the preceding work. No saved workflow edits.

- Owner confirmed the User Text Input -> Wait Until -> cross-branch LLM case.
  Saved LLM already reads Document/Context from Vault `user_text` while continuing
  an AI session; configured input declarations previously never wrote that key.
- UserTextInputNode copies the answer to declared legacy Vault keys before success,
  supporting output/id aliases and tagging the values as strings. Dead-drop answer
  remains available. Supervisor publishes transient output before completion gates.
- Stop cancels the pending input future rather than injecting an empty answer;
  interrupted prompts cannot publish output or satisfy the completion registry.
- Added 11 regressions: list/string wait targets, fresh and continued LLM calls
  using a fake provider, legacy declarations, genuine empty answers and stop.
  Before fix: 11 failed, including completion observed before data publication
  and stopped input incorrectly appearing in completed_nodes. After fix: all pass.
- Verification: focused new/execution tests **32 passed**; full tests/ **425 passed
  in 49.81s**; compileall, git diff --check, local documentation links and
  check_ui.py user_text_input_node passed. check_node.py compiled but could not run
  its expected generated test because this legacy node has no helper spec/generated
  test file; focused real runtime tests and full suite cover the change instead.
- Updated execution contract, investigation and handoff. No real LLM calls or
  owner live verification yet. Changes remain local and uncommitted.

## 2026-10-06 — Wait Until / Vault Investigation

Branch: `codex/execution-branch-ui-design`, base `7161ef2`, synchronized with
origin/main. Preserved existing uncommitted branch-UI design documentation.

- Reproduced two parallel branches with an unanswered User Text Input target.
  Wait Until held its branch until the answer; downstream reader did not start.
- After answering, target transient output existed but configured `user_text`
  Vault declaration was never written; downstream Get Variable returned missing.
  Generic membank declarations have no runtime application in Supervisor.
- Read-only local workflow inspection found a matching candidate. No live LLM
  calls, saved workflow edits, runtime changes or symbol changes.
- Recorded evidence and proposed focused fix in WAIT_UNTIL_INVESTIGATION.md.
  Existing cross-branch test: 1 passed, 153 deselected. Real runtime diagnostic,
  git diff --check and local Markdown links passed. Full suite not rerun.

## 2026-10-06 — Execution Branch UI Design

Branch: `codex/execution-branch-ui-design`, starting from clean main `7161ef2`
(merged PR #28). Fetched origin; main matched origin/main; merge already current.

- Reviewed retained branch/visit/attempt state, execution screen navigation,
  Supervisor payload handling and OutputManager finalization.
- Proposed A/D wrap, stable runtime labels, actual-visit rows, queued-node row,
  independent scroll/selection/follow and attempt details; proposed S navigation
  with X stop to resolve the current binding conflict.
- Defined selected-visit summaries and branch counts, opt-in bounded safe
  descriptors with explicit attribution, and shared run-wide durable output.
  Recorded current IDLE reset limitation and barriers' observability limits.
- Added EXECUTION_BRANCH_UI_DESIGN.md and routed handoff/index/backlog to it.
  Application unchanged. Verification: git diff --check and local Markdown links
  passed. Prior 414-test result remains historical; no runtime tests rerun.

## 2026-10-06 — Owner Confirmed Execution Symbols; PR #28 Review

Branch: `codex/execution-symbol-investigation`, fix `a31900d`, handoff `1f7ac2c`.

- Owner confirmed the execution-symbol fix works live and requested PR work
  before starting the next chat. Recorded confirmation and merge authorization.
- Reviewed the fix diff; automated validation remains 414 passing tests.
  No implementation changes in this follow-up; git diff --check passed.
- Updated build plan and next-chat handoff: use fetched main once PR #28 is
  merged, then design branch navigation/output summaries. Recovery/modal edge
  cases have automated coverage; owner confirmation specifically covers symbols.

## 2026-10-06 — Execution Status Fix Implementation (ES0–ES3)

Branch: `codex/execution-symbol-investigation`, continuing `fa91bd0` and
investigation `20d58c7`, based on fetched main `8ada5b2`. Canonical WSL checkout.

- Added NODE_EXECUTION_UPDATE with run/branch/node/visit/attempt/status facts;
  expanded supervisor position/provenance and timing identity. Report each
  execution, retry, input wait/resume, successful/failed/skipped/stopped outcome.
- Replaced frontend success guesses with ExecutionDisplayState. Retain ended
  branches and visit/attempt timing/history; derive independent branch statuses
  and a deterministic global summary. Ignore stale/retired runs and clear the
  cache on workflow replacement.
- Preserved failed outcomes through termination/cancellation, and safe-point
  successes through stop. Corrected SKIP marking the next node completed before
  it executed; regression asserts completion registry behavior.
- Refresh run view after modals; update stable cards in place to retain scroll
  and selection. Skipped/stopped use text labels without success checkmarks.
- ES0 regression cases failed on original code (5 failed); now 21 execution
  checks pass covering linear live/final rendering, parallel shared nodes,
  retries/repeat visits, recovery, user input, cancellation, barriers, pause,
  stale events, workflow replacement and three terminal widths.
- Final verification: `pytest tests/ -q` **414 passed in 49.74s** (includes all
  154 existing debug tests); focused execution suite **21 passed**; compileall;
  git diff --check; local Markdown link checks. No live owner confirmation yet.
- Current implementation recorded in EXECUTION_STATUS_CONTRACT.md. Updated
  plan/roadmap/backlog/UI routes and NEXT_CHAT_HANDOFF.md. Future A/D branch
  view, scrolling and output summaries remain a separate design/layout task.
- ES4 automated work complete; owner live check and review/merge remain.
  Implementation commit `a31900d` pushed; draft PR #28 opened at
  https://github.com/makinster/node_workflow/pull/28 (not merged).
  NEXT_CHAT_HANDOFF.md records exact state and next-chat instructions.

## 2026-10-06 — Execution Fix Build Plan and Future Branch UI

Branch: `codex/execution-symbol-investigation`, continuing investigation commit
`20d58c7` from fetched main `8ada5b2`. Documentation only.

- Added `EXECUTION_STATUS_BUILD_PLAN.md`: ES0 regression cases, ES1 explicit
  lifecycle facts, ES2 branch-specific display state, ES3 rendering/resume,
  ES4 verification and handoff. All stages pending; no application fix made.
- Recorded owner direction: A/D cycles execution branches, scrollable node
  lists per branch, and output-summary UI in a separate future task/PR.
- Defined preparation for branch/visit identity and completed-branch retention;
  documented output-summary attribution/retention and layout decisions still
  requiring design. Preserve runtime semantics and current glyph meanings.
- Linked investigation, README, task index, master plan, handoff, backlog and
  TUI design so subsequent work finds both immediate and future scope.
- Verification: documentation link/heading review and `git diff --check`.

## 2026-10-06 — Execution Symbol Investigation and Proposed Plan

Branch: `codex/execution-symbol-investigation`, based on fetched main `8ada5b2`
in `/home/makin/src/node_workflow`. Investigation and docs only.

- Reproduced missing per-node supervisor events: Start -> Sleep -> Sleep -> End
  executes fully but leaves the latter three nodes idle in App's status cache.
- Reproduced error status overwritten as done on branch termination, and a
  mounted ExecutionScreen remaining stale after a modal closes.
- Documented event -> cache -> rendering behavior, current symbol meanings,
  safe-point pauses, barrier waits, timing, run-scoping and concurrent-visit gaps.
- Added `EXECUTION_STATUS_INVESTIGATION.md` with a staged correctness fix plan
  and guidance for the upcoming execution UI redesign; linked docs/task routes.
- Verification: real-run event/cache probes, mounted Textual modal probe;
  existing focused debug tests 5 passed, 149 deselected; git diff --check.
- Owner clarified that completed nodes retain circles instead of checkmarks,
  matching the reproduced missing-transition defect. No application fix
  implemented; proposed implementation/design decisions recorded for follow-up.

## 2026-10-06 — Chat Completion Config Opening Delay

Branch: `codex/chat-config-opening-lag`, based on fetched `origin/main`
`af04c5f`, in `/home/makin/src/node_workflow`.

- Profiled the mounted Chat Completion config interaction: repeated dynamic
  rule passes traversed the entire widget tree for each field/label/row.
- Changed shared form-rule application to build one widget-id lookup per pass,
  preserving conditional visibility, enabled state, required labels, section
  titles, and forced select values. Rebuild each pass to reflect DOM changes.
- Added a traversal-count regression assertion to the mounted Continue AI
  session test; existing tests cover repeatable context and source choices.
- Same cProfile test before/after: rule processing 7.664s -> 0.093s;
  pytest duration 11.08s -> 2.25s. These include profiling overhead and are
  automated interaction timings, not live-terminal opening measurements.
- Verification: compileall; focused config/form tests (32 passed, 122
  deselected); full debug suite (154 passed); node-helper tests (14 passed);
  git diff --check. Owner confirmed the fix in the live app on 2026-10-06
  after local implementation commit `de04338`.
- Local fix only; no push or merge into main.
## 2026-07-11 — FO7 Prep: Two Windows-Environment Fixes

Branch: `claude/file-output-pywin32-32tnv9`

Found while preparing the FO7 manual run on the owner's Windows machine —
both would have made the verification measure the wrong thing.

- **`run_windows.cmd` never installed pywin32.** It ran `pip install -e .`
  without the `[windows]` extra, and `requirements.lock` carries no
  pywin32, so the standard Windows launch path silently produced the
  degraded open-only manager. Now installs `-e ".[windows]"`. The
  dependency short-circuit check also gained `win32gui`, so an existing
  `.venv-win` created before the extra existed reinstalls instead of
  skipping straight to launch.
- **`test_windows_manager_without_pywin32_degrades` asserted a
  Linux-only truth** (`_win32 is None`) and would have failed on Windows
  once pywin32 was installed. Rewritten as
  `test_windows_manager_capabilities_track_pywin32_availability`: the
  invariant is that `capabilities()` matches whatever actually imported —
  open-only without pywin32, the full five with it. Both branches were
  executed before commit (the pywin32-present branch by injecting stub
  `win32gui`/`win32api`/`win32con` modules), so neither side ships
  unrun.

Verification: `tests/test_window_manager.py` 22 passed on Linux; the
pywin32-present branch passes under stubbed modules.

## 2026-07-11 — FO7 (docs half): File-Output Plan Reconciliation

Branch: `claude/file-output-pywin32-32tnv9`

The docs-reconciliation half of FO7. The live-verification half (the 7-step
manual Windows protocol in `FILE_OUTPUT_BUILD_PLAN.md`) needs the owner's
Windows machine and stays open; the plan is NOT archived until it runs.

- `MASTER_BUILD_PLAN.md`: FO row in the Phase Status table; FO1–FO6 summary
  under Recently Completed.
- `PROJECT_BACKLOG.md`: new "Deferred — File/Window Output Follow-Ups"
  section (pyvda per D7, macOS/Linux adapters, loop open-after-write
  validator warning, cross-run window adoption non-goal per D12, possible
  refocus-after-prompt follow-up pending FO7's focus-fight check, D11
  remote-backend effector).
- `TASK_INDEX.md`: new "Change File Output, File Viewer, Or OS Window
  Behavior" route with the focused pytest slices.
- `AGENT_HANDOFF.md`: current-state paragraph for the landed FO work.
- `NODE_CATALOG.md` Window Focus supersession was already resolved in the
  FO6 entry below.

## 2026-07-11 — FO6: `window_control_node` (Focus / Minimize / Close by File)

Branch: `claude/file-output-pywin32-32tnv9`

Phase FO6 of `FILE_OUTPUT_BUILD_PLAN.md` implemented — mid-run window
choreography.

- **New node `window_control_node` ("Window Control", Utility family,
  section `Windows`)**: action select (Focus / Minimize / Close), target =
  a `file` reference from **upstream or vault only** (a window target is
  always a workflow-owned file, never hand-typed — D6). Resolves the stored
  `WindowRef` from RunSession under `window:<ref_key>`; raw path strings
  resolve to the same identity key the writer registered.
- **Soft-error rule**: a window that was never opened, never discovered
  (D4), lost to a race, or a run without a session ⇒ logged warning +
  pass-through of the file reference — never a node error. Only a missing
  file input errors.
- **New `backend/nodes/io/window_support.py`** — the shared
  RunSession↔window-manager lookup (`WINDOW_MANAGER_RESOURCE`,
  `run_window_manager`), extracted from `file_output_node` so both nodes
  and their tests use one injection point (the adapter itself stays
  run-state free per D11).
- `NODE_CATALOG.md`: Window Control added under a new Utility `Windows`
  section; the deferred **Window Focus** concept marked Superseded by it.

Verification: 9 focused tests in
`tests/generated/test_window_control_node.py` (parametrized action
dispatch, vault-sourced and raw-path targeting, missing-window /
no-session / failed-action soft paths, empty-input error) with
`FakeWindowManager`; `check_ui.py window_control_node` passes; full suite
green.

## 2026-07-11 — FO5: Open After Write + Placement on `file_output_node`

Branch: `claude/file-output-pywin32-32tnv9`

Phase FO5 of `FILE_OUTPUT_BUILD_PLAN.md` implemented — "write this md/image
and open it to the right of AOTN."

- **Config (Parameters tab, `OS Window` section):** `Open after write`
  checkbox; `Open at` placement preset select (options =
  `window_manager.PLACEMENT_PRESETS`, visible when open is on); `Close when
  run ends` toggle, default **off** (run-end cleanup is opt-in, unlike file
  handles — D12). Spec and class updated together; the loop-multiplied
  windows behavior is documented on the field and in `NODE_CATALOG.md`
  (validator warning for loops stays backlog).
- **Execute path:** after writing, the node resolves the run's window
  manager — injected/cached under the RunSession resource key
  `window_manager` (tests register `FakeWindowManager` there), else the
  platform factory — and calls `open_path(path, placement)`. A discovered
  `WindowRef` registers under `window:<ref_key>`, with a `manager.close`
  hook only when `Close when run ends` is on. Discovery failure logs a
  warning and registers nothing; the node stays successful (D4).
- **Validator (D5):** warns — never errors — when `open_after_write` is
  configured with a non-default placement and the platform lacks the
  `place` capability, or with `close_on_run_end` and no `close` capability.

Verification: four new FakeWindowManager node tests (open+place+register,
close-at-`close_all` only when configured, discovery-failure degraded
success, manager untouched when open is off) plus a validator capability
warning test; `check_ui.py file_output_node` passes; full suite green.

## 2026-07-11 — FO4: `backend/window_manager.py` Platform Adapter

Branch: `claude/file-output-pywin32-32tnv9`

Phase FO4 of `FILE_OUTPUT_BUILD_PLAN.md` implemented — the OS window
abstraction, no node wiring yet (that is FO5/FO6).

- **Protocol** (small per D9): `open_path(path, placement) → WindowRef |
  None`, `focus`/`minimize`/`close(ref) → bool`, `capabilities() → set[str]`
  (`open`/`place`/`focus`/`minimize`/`close` — the D5 validator warning's
  vocabulary). Discovery failure returns `None`, never raises (D4). The
  module imports only stdlib + logging — no MasterState/RunSession/Textual
  coupling (D11 liftability).
- **`placement_rect(preset, monitors, own_rect)`** — pure preset→rect math
  (D3: every preset yields position AND size). Presets: `OS default`,
  `Right of AOTN`, `Left of AOTN`, `Other monitor`, `Same monitor, right
  half`. Side slivers under 200px degrade to monitor halves; unresolvable
  own rect degrades AOTN-relative presets to monitor-relative (D3 Windows
  Terminal caveat); single-monitor `Other monitor` degrades to the current
  monitor. All with logged warnings.
- **`WindowsWindowManager`** — pywin32 guarded per the D5 decision record
  (recorded 2026-07-11: pywin32 over raw ctypes): `os.startfile` launch,
  snapshot-diff discovery with a 5s poll + title-contains-filename fallback
  (D4), `EnumDisplayMonitors` geometry, own-rect resolution via a
  parent-process walk (`NtQueryInformationProcess` ancestor chain → visible
  ancestor-owned top-level window) with a visible-`GetConsoleWindow`
  fallback for legacy conhost, `MoveWindow` placement, `WM_CLOSE` close.
  Without pywin32 it degrades to open-only. This branch is FO7
  manual-verification territory, not CI.
- **`FallbackWindowManager`** (`xdg-open`/`open`, placement no-op with
  warning), **`FakeWindowManager`** (records calls; `discovery_fails` mode
  for D4 tests — the FO5/FO6 node-test double), and the
  `get_window_manager()` platform factory.
- **`pyproject.toml`**: optional `windows` extra
  (`pywin32>=306; platform_system == "Windows"`).

Verification: new `tests/test_window_manager.py` (22 tests: factory,
fallback soft-fail launch/control, fake double, full preset geometry
matrix incl. mixed-resolution other-monitor and degraded modes, and
`WindowsWindowManager` degrading cleanly with no pywin32 on Linux);
`compileall` clean.

## 2026-07-11 — FO3: In-TUI File Viewer (`file_view_node` + `FileViewerScreen`)

Branch: `claude/file-output-pywin32-32tnv9`

Phase FO3 of `FILE_OUTPUT_BUILD_PLAN.md` implemented — the zero-OS-dependency
"open the file" path (D8).

- **Node-emitted EventBus events.** `NodeContext` gains an optional
  `publish_event` callback plus an `emit_event(name, payload)` helper that
  no-ops (returns False) when unwired. The supervisor wires it and stamps
  `run_id`/`branch_id`/`node_id` into every payload, keeping the standing
  JSON+run_id rule without giving nodes the bus itself. Fire-and-forget:
  execution never waits on a subscriber; headless runs have none and the
  event is inert.
- **New `backend/file_refs.py`** — shared typed-`file`-reference helpers
  (`file_reference`, `is_file_reference`, `reference_path`, `reference_key`);
  `file_output_node` now imports these instead of its module-local builder.
- **New node `file_view_node` ("File Viewer", Outputs family, direct-add)**
  from a unified helper spec + hand-written `execute()`: resolves its `file`
  input (reference dict or path; upstream/vault/configured), errors when the
  file is missing, emits `FILE_VIEW_REQUESTED` (`path`, `ref_key`, `render`),
  and forwards the file reference downstream (dead-drop and
  terminate-branch options as on File Write). Render hint: Auto by extension
  (`.md`/`.markdown` → markdown) with Markdown / Plain text overrides.
- **New `frontend/screens/file_viewer.py`** (`FileViewerScreen`, fill-modal):
  renders via Textual `Markdown` or plain `Static`, reads the file at
  display time (the event never carries contents), ESC/q/Close dismisses.
  `app.py` subscribes `FILE_VIEW_REQUESTED` → pushes the screen, ignoring
  requests while one viewer is already open.

Verification: 9 focused node tests in
`tests/generated/test_file_view_node.py`; two pilot tests in
`tests/test_debug_nodes.py -k file_view` (full workflow start→echo→File
Write→File Viewer→end opens the viewer rendering the md, ESC closes;
open-guard ignores a second request and re-opens after close);
`check_node.py`/`check_ui.py file_view_node` pass; full suite 439 passed
(same known settings-screen flake only). `SIGNAL_FLOW.md`, `FILE_TREE.md`,
`NODE_CATALOG.md` updated.

## 2026-07-11 — FO2: Markdown Formatting as a Text Transform Mode

Branch: `claude/file-output-pywin32-32tnv9`

Phase FO2 of `FILE_OUTPUT_BUILD_PLAN.md` implemented. Per the
`NODE_STANDARDS.md` classification rule the plan anticipated, this is a
**mode-select on `text_transform_node`** (same ports, one extra conditional
field), not a new node type.

- **New `backend/text_format.py`** — pure `format_markdown(text, wrap_width)`
  with no node/runtime coupling: normalizes line endings and trailing
  whitespace, ATX heading spacing (`##Title` → `## Title`, closing hashes
  dropped, blank line before/after), bullet markers to `- ` and ordered
  markers to `N. `, aligns table columns (preserving `:` alignment markers,
  inserting a blank line when a table butts against preceding text), collapses
  blank-line runs, and — when `wrap_width > 0` — re-flows plain paragraphs
  only (headings/lists/tables/blockquotes/code never wrap). Fenced code
  blocks pass through untouched. Deliberately conservative; not a full
  CommonMark canonicalizer.
- **`text_transform_node`**: new `markdown format` operation + `wrap_width`
  integer field (`visible_when` the markdown operation is selected; 0 keeps
  existing breaks). Spec and class updated together.

Verification: new `tests/test_text_format.py` (16 tests, including a messy
LLM-output end-to-end case) plus markdown-mode cases in the generated
transform tests; `check_node.py text_transform_node` and `check_ui.py
text_transform_node` pass.

## 2026-07-11 — FO1: `file_output_node` (File Write) + Typed File Reference

Branch: `claude/file-output-pywin32-32tnv9` (started from `main` @ `af04c5f`)

Phase FO1 of `FILE_OUTPUT_BUILD_PLAN.md` implemented.

- **New node `file_output_node` ("File Write", Outputs family, group
  `File Write`)** generated from the unified `inputs:`/`outputs:` spec
  `aotn_node_helper/specs/file_output_node.yaml` with a hand-written
  `execute()`. Content and file path use the standard three-source model
  (`content` accepts `any`; `file_path` is `file`-typed and also accepts an
  upstream/vault file reference dict, resolving its `path`). Write modes:
  Overwrite / Append / Create unique (numeric ` (n)` suffix); Base64 binary
  toggle; parent directories are created. Writes go through
  `context.run_session.open_file` when in a run (cached `"w"` handles are
  seek(0)+truncated so overwrite stays deterministic; writes flushed so the
  file is readable mid-run), direct `Path` I/O otherwise.
- **Typed `file` reference (D2)** emitted downstream and optionally to the
  vault (`type_tag="file"`): `{"type": "file", "ref_key": "file:<resolved>",
  "path": <resolved>}`; the open handle registers in `RunSession` under
  `ref_key` (keyed by file identity, per D6) and closes at `close_all()`.
  Dead-drop passthrough forwards the incoming content unchanged.
- **Standard "Terminate branch after completion"** (`terminate_branch`,
  Payloads tab) — first Outputs-family node to carry the NODE_STANDARDS
  branch-termination option; rides the `signal_done` payload the supervisor
  already honors.
- **Validator: source-gated field awareness.** The `path_hint: "file"` and
  `secret: true` checks now skip fields whose `visible_when` doesn't hold
  (new `_field_visible`, defaults-aware) — a required Configured path no
  longer false-errors when the input reads from Upstream/Vault. Empty
  required path with Configured selected stays an error; missing-on-disk
  stays a warning (an earlier node may create the file mid-run).
- **Retired `example_file_instance_node`** (spec, node, generated tests,
  registration) per FO1 task 4 — `file_output_node`'s spec absorbed its
  unified-spec reference role. Repointed `test_node_contract.py`, the editor
  details-panel test, and node-selector expected sets; updated
  `NODE_HELPER.md`, `NODE_STANDARDS.md`, `AGENT_START_GUIDE.md`,
  `FILE_TREE.md`, and `NODE_CATALOG.md` (File Instance row removed; File
  Write now Live).

Verification: `check_node.py file_output_node` and `check_ui.py
file_output_node` pass; new focused tests in
`tests/generated/test_file_output_node.py` (17) plus run-lifecycle and
validator-gating tests in `tests/test_run_session.py`; full suite 409 passed
with one pre-existing settings-screen pilot-timing flake
(`test_simple_command_modals_use_shared_navigation_helpers`) that fails only
under full-suite load, on the untouched baseline too, and passes in
isolation.

## 2026-07-11 — File Output Build Plan: Design-Review Amendments

Branch: `main` (plan merged from `claude/output-nodes-file-windows-wq07q6`
earlier today)

Reviewed `FILE_OUTPUT_BUILD_PLAN.md` against the project vision docs
(`PROJECT_KNOWLEDGE.md`, `MASTER_BUILD_PLAN.md`, `PROJECT_BACKLOG.md` future
directions) and amended the plan. No scope change; no phase started.

- **New D11 — window management is a local-execution capability.** Records
  the tension between D10 (backend window manager) and the Multi-Frontend
  Expansion direction (backend as a standalone server, where the backend
  host and the user's display diverge). Migration path: window actions move
  behind the EventBus to a local effector — the same pattern FO3 uses —
  with `capabilities()` declaring display access. FO4 exit criteria now
  require the adapter to be free of run-state coupling so it can be lifted
  behind an event boundary unchanged.
- **New D12 — windows that outlive the run are unmanaged orphans.** With
  `Close when run ends` off, the `WindowRef` dies with `RunSession`; later
  runs cannot target the window. Documented as intentional.
- **D3 caveats:** presets define position *and* size (full target rect);
  Windows Terminal/ConPTY makes `GetConsoleWindow()` return a hidden
  pseudo-console window, so FO4 must resolve the real terminal window via a
  parent-process walk with conhost fallback, degrading AOTN-relative presets
  to monitor-relative with a warning when unresolvable.
- **D4 rule:** discovery failure is never a node error — file opens,
  placement degrades to "opened but unplaced" warning, no `WindowRef`
  registered. Mirrored in FO5 test expectations.
- **D5 decision record:** pywin32 stays (as an optional extra) over raw
  ctypes despite the `llm_provider.py` no-dependency precedent — the window
  adapter is cold, optional, and only manually verifiable, so hand-rolled
  ctypes maintenance risk outweighs zero-dep purism.
- **FO5:** documented loop-multiplied windows (validator warning is backlog,
  not FO5 scope). **FO7:** added Windows Terminal vs conhost host coverage
  and a focus-fight check (open-after-write directly upstream of
  `user_text_input_node`); docs reconciliation now explicitly resolves the
  deferred `NODE_CATALOG.md` **Window Focus** entry as superseded by the
  file-scoped `window_control_node`.

Verification: docs-only change; `git diff --check` clean.

## 2026-07-08 — Helper Generator Aligned with the Standardized Node UI

Branch: `llm-node`

Owner direction: the Chat Completion UI work is the standard for future nodes;
the node helper must get new nodes as close as possible automatically.

- **Generator emits the new output model.** `output_routing` no longer
  produces the retired Payloads checkbox fields (`transient_output` /
  `dead_drop_passthrough` / `vault_write*` schema entries). It now emits
  routing **defaults** into `default_config` and maps the vault mode onto the
  default output port's metadata (`to` gains `vault`;
  `required_unless_transient` sets `vault_required`). Mode mapping: `optional`
  → Disable output starts checked; `default_on` → unchecked;
  `required_unless_transient` → always writes, no Disable checkbox. Legacy
  label keys accepted and ignored; routing config key names reserved.
- **Forwarding checkbox is capability-gated**: `Forward incoming payload
  unchanged` renders only when a downstream port declares
  `pass_through: true`.
- **Stale-schema guard**: standard-model nodes exclude any leftover routing
  schema fields from rendering, so pre-redesign generated nodes cannot
  double-render routing controls.
- **Reference node regenerated**: `example_file_instance_node` rebuilt with
  the new generator (no routing schema fields; `to: [downstream, vault]`;
  vault optional/disabled by default). Both specs' `output_routing` blocks
  simplified.
- **Docs standardized**: new `NODE_HELPER.md` section **"What the Config UI
  Renders Automatically"** — the full standardization contract (Source
  incoming-payload block, Required/Optional sections, typed vault dropdowns +
  eligibility/pruning, composed Payloads tab, dynamic rule keys, validator
  derivation) that every standard-model node gets with zero frontend edits;
  rewritten `output_routing` reference; NODE_STANDARDS helper note, File
  Instance example, and Authoring Checklist updated to the new model (with
  `chat_completion_node` named as the reference `execute()` implementation).

Verified: full pytest suite green, `check_ui` OK for both
`example_file_instance_node` and `chat_completion_node`, helper tests updated
to the new expansion (46 passed).

---

## 2026-07-08 — Fix: a node cannot continue its own AI session

Branch: `llm-node`

Bug: after a workflow with a self-declared AI session was saved and run, the
session key persisted to the vault. Reopening that node's config then offered
"Continue AI session" and let the node select its own session key. Root cause:
`_vault_key_options` added **persisted** vault entries unconditionally, bypassing
the same-node/downstream eligibility filter that only gated *declared writers*.

Fix: the eligibility check (`writers - {self}` non-empty and not
downstream-only) now gates **every** candidate — persisted entries included.
Keys with no workflow writer stay allowed (external/legacy). With no eligible
`ai_session` key, `_prune_unavailable_source_options` drops the "Continue AI
session" prompt-source option entirely. New regression test
`test_node_config_own_session_not_continuable`. Full suite 378 passed.

---

## 2026-07-08 — Output Model Redesign: Downstream Payload + Keyed Vault Payloads

Branch: `llm-node`

Owner-directed reconception of the node output model plus a Continue-mode fix.

- **Source fix**: Continue AI session no longer locks `document_source` to
  Configured — the input becomes required (section retitles Optional →
  Required) but the user still picks Upstream / Vault / Configured.
  `force_value_when` removed from the chat schema.
- **New output model** (NODE_STANDARDS): every node has one designated
  **Downstream node payload** and any other outputs are **keyed Vault
  payloads**. The standard-model Payloads tab is now composed from
  `output_port_metadata.to` by `NodeConfigScreen._compose_standard_payloads`:
  - Downstream node payload at the top: `Name (type)` header + editable
    payload name and description (seed from metadata, overwritable).
  - Single `Forward incoming payload unchanged` checkbox beneath it (greys the
    downstream fields when checked).
  - `Vault Payload(s)`: editable key + description per vault-routed output,
    with a `Disable output` checkbox for optional ones (greys key/desc).
  - AI Session section stays at the bottom.
  - The per-output `Send to next node` / `Save to Vault` checkboxes and the
    compact Outgoing summary are gone.
- Data **type shown in parentheses** wherever a payload name appears (incoming
  block and the downstream/vault headers).
- **Chat node**: routing/vault schema fields removed (composed instead);
  defaults flipped so `Result (string)` is the downstream payload
  (`dead_drop_passthrough` default False) and duplicated to the vault
  (`vault_write` default True); `execute()` routes on `dead_drop_passthrough`;
  added `vault_write_description`.
- Tests: new `_compose_standard_payloads` save/greying test; updated
  standard-model layout, continue-mode, and schema tests. Full suite 377
  passed; `check_node`/`check_ui` OK.
- Docs: NODE_STANDARDS (output routing model + Payloads tab + Basic LLM
  example), IO_CONTRACT_UI_DESIGN (three decision rows), helper spec.

---

## 2026-07-08 — Continue-Session Document Turn + Generic Mode-Driven Rule Keys

Branch: `llm-node`

Owner feedback: in Continue AI session mode the Document input must carry the
new turn's text, and a real bug — continue mode read only the document port and
silently sent a bare "Continue." nudge, producing responses unrelated to the
user's actual input.

- **New generic form rule keys** (`form_generator.apply_field_rules`): so
  future nodes get this behavior declaratively, not via node-specific code.
  - `required_when` — adds the `*` marker live when a condition holds.
  - `section_when` — retitles a field's section header (`{title: condition}`).
  - `force_value_when` — locks a `select` to a value while a condition holds
    (`{value: condition}`); re-enabled otherwise. `NodeConfigScreen` guards
    reentrancy since forcing a value re-fires `Select.Changed`.
  - Generator `_validate_field_rules` accepts and validates the new keys.
- **Chat node Continue-mode edge case**: `document_source` gains
  `required_when` / `section_when` (Optional → Required Inputs) /
  `force_value_when` (→ Configured) keyed to `prompt_source == Continue AI
  session`; a `document` multiline param textbox (visible_when
  document_source == Configured) mirrors the prompt textbox; document sources
  gain "Configured".
- **Bug fix**: continue mode now requires and sends the resolved Document text
  as the new user turn (errors clearly when empty) instead of the silent
  nudge. Fixes unrelated responses when the upstream landed on the prompt port.
- **Session reuse**: checking "Keep active AI session" while continuing extends
  the resumed session in place (onward key = the resumed ref); the session-key
  field is hidden in continue mode (`visible_when` list-OR of non-continue
  prompt sources). `_persist_session` now takes the resolved `onward_key`.
- Docs: `NODE_HELPER.md` (three new rule keys), `NODE_STANDARDS.md` (Basic LLM
  continue-mode edge case + session reuse), `IO_CONTRACT_UI_DESIGN.md`
  (decision row), helper spec refreshed.

Verified: full pytest suite (376 passed), `check_node`/`check_ui` OK,
`compileall` clean.

---

## 2026-07-07 — Dropdown Eligibility, Option Pruning, Nav-Skip Payload Summary

Branch: `llm-node`

Owner feedback round 3:

- **Incoming Payload block is skipped by keyboard navigation** — rendered as a
  plain read-only `Static` instead of a focusable `PayloadPreview`.
- **Vault/session dropdown eligibility**: declared keys whose only writers sit
  downstream of the configured node on the same branch (or are the node
  itself) are excluded — they cannot exist when the node runs. Parallel-branch
  writers stay listed since static analysis cannot order branch timing (the
  validator race warning covers that). Implemented in
  `NodeConfigScreen._vault_key_options` via `nodes_reachable_from`.
- **Source option pruning**: a source option that would reveal an empty typed
  vault dropdown (`Vault`, `Continue AI session`) is dropped from the source
  selector; a previously saved selection stays selectable so old configs
  display faithfully (`_prune_unavailable_source_options`).
- Docs reviewed per `README.md` routing table; updated `NODE_STANDARDS.md`
  (eligibility bullets, File Instance hidden-field wording),
  `IO_CONTRACT_UI_DESIGN.md` (§3 eligibility/pruning, §4 nav-skip),
  `NODE_HELPER.md` (`vault_type` eligibility), `AGENT_START_GUIDE.md` and
  `TUI_DESIGN.md` (payload preview shapes: auto block vs legacy reveal
  checkboxes).

Verified: full pytest suite (374 passed), `check_ui` contract OK,
`compileall` clean.

---

## 2026-07-07 — Config UI Polish Round 2 + Continue-Session Prompt Mode

Branch: `llm-node`

Owner feedback on the first redesign pass (live screenshots):

- **Incoming Payload block** reformatted and made portless — showing
  `prompt <- Start` confused when the prompt source was Configured. Now:
  `Node source: Start node` / `Payload: Output (string)` /
  `Payload desc: ...` / `Value: ...` (desc/value lines only when present;
  an `Input:` line is added only when several inputs are wired).
- **Dropdown layout**: dropdowns were offset by varying label widths. They
  now render full-width under a `label: description` header line
  (description inline with the header, not below the widget). Single-line
  inputs keep the inline row, with descriptions inline; checkbox
  descriptions ride on the checkbox row.
- **Continue AI session is a prompt-source mode**: the prompt source
  dropdown gains a fourth option that reveals an `ai_session`-filtered
  Session dropdown and replaces the prompt. Runtime: resumes the selected
  session's history; the document input (when wired) becomes the next user
  turn, else a bare "Continue." nudge; errors cleanly when no session is
  selected or it has no history. `continue_session_key` moved from the
  Payloads AI Session section back to Source under this mode; the validator
  derives its vault read only while the mode is selected (stale hidden
  values stay quiet).

Verified: full pytest suite (372 passed), `check_ui` contract OK,
`compileall` clean.

---

## 2026-07-07 — Node Config UI Redesign (standard-model layout)

Branch: `llm-node` (continuing from the Chat Completion build)

Owner feedback on the Chat Completion config screens drove a general config-UI
simplification. All changes are schema/composition-driven; legacy nodes keep
the old flat layout.

- **Form primitives** (`form_generator.py`, `styles.tcss`): checkboxes carry
  their own label (single row); descriptions render below their own field;
  selects/dropdowns join inputs as inline `Label: [widget]` rows; new generic
  `section` schema key renders bold section headers; inline rows are
  height-auto so bordered widgets (Select/secret dropdowns) no longer clip.
- **Gating**: irrelevant fields are now *hidden* (`visible_when`) — vault
  keys until Vault is selected, the configured prompt until Configured, the
  session key until the checkbox is on. Grey-out (`enabled_when`) is reserved
  for the locked vault-write checkbox.
- **Source tab** (standard-model nodes): inline alias row; auto-revealed
  Incoming Payload block (producer chain, `[type]`, description, last value —
  replaces the reveal checkboxes); Required/Optional Inputs sections;
  per-input vault key dropdowns filtered by port data type (untagged legacy
  entries satisfy `string`; declared workflow writer keys included pre-run).
  Legacy Vault selection list removed.
- **Payloads tab** (standard-model nodes): Result Routing section (checkbox +
  key rows); AI Session section — `use_chat_session`, `session_key`, and the
  `continue_session_key` dropdown all moved here; compact read-only Outgoing
  contract line; legacy Write to Vault rows and reveal checkboxes removed.
- **Validator** derives vault declarations from standard-model config:
  `vault_write_key` (typed by default output port) and `session_key`
  (`ai_session`) as writers; `<port>_vault_key` (typed by port) and
  `continue_session_key` (`ai_session`) as readers — existence error,
  ai_session mismatch warning, and parallel-race warning all covered
  (`tests/test_validator_standard_model_vault.py`).
- **Helper generator** emits the new pattern (`visible_when`, `vault_type`,
  Required/Optional + Result Routing sections). Docs updated:
  `NODE_STANDARDS.md` (hidden-not-greyed, tab layouts, Basic LLM example),
  `IO_CONTRACT_UI_DESIGN.md` (§3/§4 done, new decisions),
  `NODE_HELPER.md`, `PROJECT_BACKLOG.md` (Track B 4b dropdowns done).

Verified:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/ -q                      # full suite green
../.venv/bin/python ../aotn_node_helper/check_node.py chat_completion_node
../.venv/bin/python ../aotn_node_helper/check_ui.py chat_completion_node
git diff --check
```

---

## 2026-07-04 — Chat Completion Real Execution + AI Sessions (Phases 0–6)

Branch: `llm-node` (from `main` @ 6a7c51e)

Full approved build plan executed in phase-sized commits.

- **Phase 0 (docs):** `NODE_STANDARDS.md` Basic LLM example's `Model:` field is
  now a curated dropdown (was stale free text), citing Phase 17 AI Model
  Approach.
- **Phase 1:** new `backend/llm_provider.py` — raw stdlib HTTPS Anthropic
  Messages client (no SDK dependency), `SUPPORTED_MODELS` as the single curated
  list constant (`claude-opus-4-8` default, `claude-sonnet-5`,
  `claude-sonnet-4-6`, `claude-haiku-4-5`; verified current 2026-07-04),
  `CompletionResult`, `get_client()` provider seam. `ModelInfo.supports_temperature`
  omits `temperature` for models that 400 on sampling params (Opus 4.8,
  Sonnet 5). Mocked-transport tests; API key never logged.
- **Phases 2–3:** `chat_completion_node` executes for real. Standard
  prompt/document input sources (ports renamed `input` → `prompt`/`document`),
  secrets-store API key (now `required`), dead-drop passthrough default with
  locked-on vault write, "Keep active AI session" + `session_key` persisting
  history in `RunSession` and an `ai_session`-tagged vault reference, and a
  `continue_session_key` continuation input. Failures use the node-error path:
  no vault write, no history mutation. Client call runs via
  `asyncio.to_thread` so the TUI event loop never blocks.
- **Phase 4:** `build_form` gained `vault_keys_by_type`; string fields
  declaring `vault_type` render as key dropdowns (persisted entries of that
  tag + workflow-declared session keys). Model dropdown and session-key gating
  render from schema alone.
- **Phase 5:** `specs/chat_completion_node.yaml` (unified `inputs:`/`outputs:`
  contract; execute is hand-written — do not regenerate blindly), generated
  contract + UI smoke tests; `check_node.py` and `check_ui.py` pass. Also
  fixed the missing Configured-prompt Parameters field.
- **Phase 6 (docs):** `NODE_CATALOG.md` Chat Completion → Live;
  `PROJECT_BACKLOG.md` typed-vault items ticked (general 4b type-filtered
  source dropdowns remain deferred); `MASTER_BUILD_PLAN.md` roadmap lines;
  `TASK_INDEX.md` route "Change LLM Node Execution Or AI Sessions".

Flagged decisions (per plan, for Kelly): (1) raw HTTP chosen — the stdlib path
was sufficient, no SDK dependency added; (2) curated list seeded as above —
note Opus 4.8/Sonnet 5 reject `temperature`, handled per-model; (3) node-local
`vault_type` dropdown shipped instead of the general 4b widget, gap logged in
`PROJECT_BACKLOG.md`.

Verified:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -q          # 140 passed
../.venv/bin/python -m pytest tests/test_llm_provider.py tests/test_chat_completion_node.py tests/test_validator_secrets.py -q
../.venv/bin/python ../aotn_node_helper/check_node.py chat_completion_node
../.venv/bin/python ../aotn_node_helper/check_ui.py chat_completion_node
git diff --check
```

---

## 2026-06-25 — Settings Secrets Manager UI

Branch: `codex/node-type-constants`

Implemented the user-facing secrets manager workflow from Editor → `O` Options.

- `SettingsScreen` is now a numbered tab modal with `1 - General` for existing
  app settings and `2 - Secrets` for saved secret keys.
- Secrets tab includes Key and API-key fields, an Add/Clear button row, a saved
  key dropdown, and `X` deletion with `ConfirmScreen` confirmation.
- `App.action_settings()` passes the existing `SecretsManager` into settings;
  `EditorScreen` passes it into `NodeConfigScreen`.
- `build_form()` accepts stored secret key names, and schema fields marked
  `"secret": True` render as dropdowns in node config when a manager is wired.
  Existing configured key names that are not in the store remain selectable as
  `(not stored)` legacy values.
- Focused tests added for settings tab navigation, secrets add/clear/delete,
  and node-config secret dropdown population.

Verified:

```bash
../.venv/bin/python -m pytest tests/test_debug_nodes.py -q -k "simple_command_modals or settings_secrets_manager or node_config_secret_fields or migrated_command_screens or node_config_fixed_tabs"
../.venv/bin/python -m pytest tests/test_secrets_manager.py tests/test_validator_secrets.py tests/test_form_generator.py -q
../.venv/bin/python -m compileall -q .
git diff --check
```

Results: focused debug slice 5 passed; related secrets/form suite 47 passed;
compile and whitespace checks clean.

---

## 2026-06-24 — Architecture Direction: Start Node Redesign, Metadata Conditionals, Nested Headless Validation

Branch: `claude/readme-review-main-sync-mtzc25`

Planning session extending the headless CLI design with three additional concepts.
No code changes.

- **Start node redesign.** `StartNode` stays hidden by default. Context-specific
  variants are revealed when the user declares an execution context: `HeadlessStartNode`
  (exposed on "Save for headless" export — configures CLI preamble: banner,
  global session prompts, pre-flight setup), `NestedStartNode` (workflow
  callable as sub-workflow, Phases 19/20), `TriggerStartNode` (always-running
  watcher, far future). All variants share the same downstream port shape so the
  rest of the graph is unaffected.
- **Nested workflows as headless black boxes.** The headless validator does not
  re-traverse a nested workflow's internal graph. It checks two things only: the
  nested workflow's `headless_valid` flag (set when that workflow passed its own
  headless validation) and port compatibility. Each validation level trusts its
  children's flags — the compiled-library trust model.
- **Metadata conditional nodes.** New node group (Flow Control → Context
  Branching): `ExecutionModeConditionalNode` branches on `tui`/`headless`/
  `nested`/`triggered`; `RunMetadataConditionalNode` branches on arbitrary
  context keys. Enables one workflow to route correctly across execution modes
  without a separate export. Validator softening rule: TUI-only node behind a
  correct context gate → warning; TUI-only node ungated in a headless-flagged
  workflow → error. Structural errors (broken connections) remain errors in all
  modes regardless of gating. Context is read-only, set once at run start by
  `MasterState`/CLI entrypoint, immutable mid-run.

Updated: `PROJECT_BACKLOG.md` (start node, nested validation, metadata
conditional sections added to headless future direction; new metadata conditional
future direction section), `AGENT_HANDOFF.md` (expanded long-range summary).

---

## 2026-06-24 — Architecture Direction: Headless CLI, Trigger Watcher, Multi-Frontend

Branch: `claude/readme-review-main-sync-mtzc25`

Planning session to establish long-range architecture direction and ensure
current build decisions do not close off future expansion goals. No code
changes.

Three future directions documented in `PROJECT_BACKLOG.md`:

- **Headless CLI execution (`aotn`).** "Save for headless" exports a duplicate
  file — the TUI workflow stays the editable source of truth. The export swaps
  TUI I/O nodes for headless twins with identical port shapes so all graph
  connections transfer unchanged. Twins default to stdin-prompted interaction;
  format is inherited from node type (free text / single-index / comma-separated
  multi-index). Optional `headless_input_mode` per node: `prompted` (default),
  `cli_arg`, or `static_default`. Nodes with no declared twin block export with
  a clear error. Configurable data directory required before CLI entrypoint.
  Full design in `PROJECT_BACKLOG.md` → "Future Direction — Headless CLI Execution".
- **Always-running trigger watcher.** A non-terminating headless workflow that
  monitors for external events and dispatches sub-workflows when conditions fire.
  Requires: trigger node primitives that block on external events (exempt from
  `node_timeout_seconds`), deliberate loop/cycle support in the workflow model,
  a resource lifecycle that does not assume terminal-path cleanup, and sub-workflow
  execution isolation so dispatched runs do not share `MasterState` context with
  the watcher. Depends on headless CLI and nested workflows (Phases 19/20).
- **Multi-frontend expansion.** TUI, Chrome extension, and desktop GUI all as
  thin clients to a shared backend HTTP + WebSocket server. The backend has no
  frontend imports today — the load-bearing separation holds. The eventual
  structural shift is extracting the backend into a standalone process; the TUI
  either becomes a thin client or keeps a direct in-process path.

Key invariants to enforce from now on, added to `AGENT_HANDOFF.md` and
`MASTER_BUILD_PLAN.md` standing rules:

1. No frontend imports in backend code.
2. EventBus payloads must remain JSON-serializable — no Python objects, Textual
   widgets, or reactive references.
3. No non-serializable Textual state stored on `MasterState`.
4. All new event payloads carry `run_id` for future multi-run and multi-frontend
   isolation.

Updated: `PROJECT_BACKLOG.md` (three new Future Direction sections),
`AGENT_HANDOFF.md` (Long-Range Direction section + invariants),
`MASTER_BUILD_PLAN.md` (three far-future roadmap phases + two standing rules).

---

## 2026-06-23 — Editor Details Panel: Configured Contract Layout

Branch: `claude/attackofthenodes-frontend-design-nn6put`

Reformatted the editor's right-hand `#node-details` panel to use the node
selector's contract layout and labeling conventions, specialized to how the
node instance is wired and configured.

**`frontend/io_contract.py` (new):** Shared `TYPE_COLOR`, `type_label()`, and
`wrap_dim()` (hanging-indent wrap) used by both the selector and the editor.

**`frontend/screens/node_selector.py`:** Now imports the shared helpers;
`_wrap_dim` delegates to `io_contract.wrap_dim`, `_fmt_port` uses `type_label`.
Dropped the local `textwrap` import.

**`frontend/screens/editor.py`:**
- Rewrote `_format_node_details` to the new header (Name / Description /
  Family / Tags), a runtime block (Depth / Breakpoint / Avg Time), then
  `Inputs:` / `Outputs:` sections in the selector's 3-line port style.
- Per-port `└─<` / `└─>` lines name the configured producer/target node(s)
  when connected; otherwise fall back to allowed source/destination kinds, or
  bold `↔ pass-thru` for pass-through outputs.
- Vault reads/writes render as `key [vault]` entries.
- Added `_detail_width`/`_wrap_detail` + `on_resize` so the panel re-wraps to
  its column width; port names honor config overrides via the existing
  `input_display_name`/`output_display_name` helpers.
- Removed the now-dead `_metadata_subcategories`, `_format_io_summary`,
  `_format_transient_input_lines`, `_format_transient_output_lines`,
  `_format_memory_lines`, and the `Kind:`/`Step:`/`About:` labels.

**`tests/test_debug_nodes.py`:** Added
`test_editor_details_panel_uses_contract_layout`; updated the editor quick-view
and depth-counter assertions to the new format.

**`docs/IO_CONTRACT_UI_DESIGN.md`:** Documented the editor details layout and
marked the phase Done (2026-06-23).

---

## 2026-06-22 — Track B Phase 3: Selector Drill-in Navigation

Branch: `claude/attackofthenodes-frontend-design-nn6put`

`D`/`→` on a group row in the node selector now drills into a quick-list
that appears at the top of the right detail panel (up to 6 members, sorted
alphabetically). Navigating the quick list with `W`/`S` updates the I/O
contract below. `E` adds the highlighted node directly. `A`/`←` returns
focus to the left list. Tab switching and filter typing auto-exit.
The full `GroupBrowserScreen` remains deferred.

**`frontend/screens/node_selector.py`:**
- `__init__`: Added `_drilled_in`, `_quick_list_members`, `_quick_list_nodes`.
- `compose()`: Added `ListView(id="node-quick-list")` before the contract
  `Static` in the detail panel; added `id="selector-help"` to help text.
- New methods: `_enter_quick_list`, `_exit_quick_list`, `_reset_drill_in`,
  `_move_quick_list`, `_update_quick_detail`, `_sync_help_text`.
- `action_cursor_right`: Drills in when list focus is on a group entry.
- `action_cursor_left`: Exits drill-in when `_drilled_in`.
- `action_cursor_up/down`: Delegates to `_move_quick_list` when in quick list.
- `action_choose`: Adds the quick-list-selected type when drilled in.
- `on_list_view_highlighted/selected`: Updated for quick list events.
- `_render_group_detail`: Added `D/→ = quick list` hint.
- `_apply_filter`, `_set_active_tab`: Call `_reset_drill_in` on state change.

**`frontend/styles.tcss`:** Added `.node-quick-list` and
`.node-quick-list ListItem` rules.

**`tests/test_debug_nodes.py`:** Added `test_node_selector_group_drill_in`.

**`docs/IO_CONTRACT_UI_DESIGN.md`:** Updated phase table — Drill-in nav
marked Done (2026-06-22).

---

## 2026-06-22 — Track B Phase 4c: ⚠ Badge on Editor Node Cards

Branch: `claude/attackofthenodes-frontend-design-nn6put`

Node cards in the editor now show a `⚠` glyph when the last `V`
(validate) run flagged that node with errors or warnings. The badge clears
when validation runs clean. Driven by last-run result (Option A from the
design); continuous background checking remains a backlog item.

**`frontend/widgets/node_card.py`:**
- `NodeCard.__init__` accepts `has_warning: bool = False`.
- `refresh_card()` prepends `"⚠ "` to `main_text` when set — visible in
  both the simple single-line and the 4-line identity-box display paths.

**`frontend/widgets/node_list.py`:**
- `refresh_rows()` accepts `flagged_node_ids: set | None` and passes
  `has_warning=node_id in flagged_node_ids` when constructing each `NodeCard`.
- `_append_row()` receives `flagged_node_ids` as an optional parameter.

**`frontend/screens/editor.py`:**
- `EditorScreen.__init__` initialises `self._flagged_node_ids: set[str] = set()`.
- `action_validate_workflow()` computes the flagged set from the union of
  error and warning `node_id` fields, stores it, then calls
  `refresh_from_backend()` so badges appear immediately.
- `refresh_from_backend()` passes `flagged_node_ids=self._flagged_node_ids`
  to `node_list.refresh_rows()`.

**`tests/test_debug_nodes.py`:** added `test_node_card_warning_badge_appears_when_flagged`.

**`docs/IO_CONTRACT_UI_DESIGN.md`:** updated phase table — Tab fix, Selector
panel, and ⚠ badge marked Done (2026-06-22).

---

## 2026-06-22 — Selector Taxonomy: Five Family Tabs (retire I/O toggle)

Branch: `claude/attackofthenodes-frontend-design-nn6put`

Owner decision: split the combined `I/O` tab into separate Inputs and Outputs
tabs so the Outputs family can grow its own identity (live UI-display nodes that
render data on screen during workflow execution; richer user-input nodes less
commonly on the Inputs side).

**`frontend/screens/node_selector.py`:**
- `TABS = ["In", "Flow Control", "Utility", "Out", "Complex"]` — five tabs,
  hotkeys 1–5, ordered to read like data flow (in → process → out).
- Added `TAB_FAMILY` mapping so abbreviated `In`/`Out` display labels resolve to
  the `Inputs`/`Outputs` backend `primary_family` values; the other three are 1:1.
- Removed the entire I/O segmented toggle: `IO_TAB`, `_io_output_side`,
  `_sync_io_toggle`, `_set_io_side`, `_active_io_button`, `_focus_active_io_button`,
  the `io-direction-row`/`io-side-input`/`io-side-output` widgets, and their
  branches in `on_button_pressed`, `action_choose`, and `_nav_widgets`.
- `_active_family()` simplified to `TAB_FAMILY.get(...)`. Added `jump_tab(5)`
  binding. Help text `1-4 tabs` → `1-5 tabs`.
- Now maps 1:1 to the five backend families — closes the "Selector Family
  Taxonomy Reconciliation" backlog item.

**`frontend/styles.tcss`:** removed dead `#io-direction-row` and
`.segmented-toggle` rules.

**Tests (`tests/test_debug_nodes.py`):**
- Rewrote `test_node_selector_io_toggle_keyboard_contract` →
  `test_node_selector_tab_keyboard_contract` (number-key tab switching across
  the five tabs; added to the script runner list).
- Updated `test_node_selector_uses_family_tabs` (default tab `In`/Inputs, `Out`
  tab for Outputs, explicit `_set_active_tab` for the new order).
- Updated `test_node_selector_layout_is_compact` (no I/O toggle row; list sits
  below the filter).
- Updated `test_node_selector_rows_are_one_line_with_detail` to assert the new
  master-detail contract panel render (was asserting the old single-line detail).

**Docs:** `IO_CONTRACT_UI_DESIGN.md` (mockup + taxonomy note),
`UI_QUICK_REFERENCE.md`, `PHASE_17_NODE_VISUAL_IDENTITY.md` (2026-06-22 revision
callout), `PROJECT_BACKLOG.md` (closed reconciliation item, added Outputs
UI-display future direction).

**Verified:** installed `rich`/`textual`/`pytest-asyncio` in the session env and
ran the real UI suite — **full `tests/` suite 331 passed**. (Earlier in the
session these were uncollectable due to missing packages.)

## 2026-06-22 — Track B Phase 1: Tab Fix + Selector Master-Detail

Branch: `claude/attackofthenodes-frontend-design-nn6put`

**Design decisions finalized (from Track B planning session):**
- Type mismatch display: Option B (amber `[type]` label) as fallback; primary prevention is dropdown type filtering.
- Vault incompatibles: hidden entirely from dropdown (no divider).
- Legacy nodes (no `inputs:` block): silent fallback to flat Source tab.
- ⚠ badge: driven by last `V` (validate) run (Option A); Option B (continuous) is backlog.
- Spec written to `docs/IO_CONTRACT_UI_DESIGN.md`.

**Tab-sticking fix (`frontend/screens/node_config.py` + `frontend/styles.tcss`):**
- Removed the outer `VerticalScroll(id="node-config-scroll")` that wrapped `TabbedContent` in `NodeConfigScreen.compose()`. When the form scrolled, the tab bar scrolled away with it.
- `TabbedContent` is now a direct child of the modal `Vertical` — pinned at the top.
- Each `TabPane` (`1-Source`, `2-Parameters`, `3-Payloads`, `4-Connections`) contains its own `VerticalScroll(classes="tab-scroll")`. Same fix applied to `_compose_branch_config_tabs`.
- Non-tabbed modal paths (Merge node, Branch End) keep a flat `VerticalScroll(id="node-config-scroll")` so legacy scroll-helper code still falls back correctly.
- `_scroll_container()` updated: tries to find the active pane's `.tab-scroll` first, falls back to `#node-config-scroll`.
- `on_mount()` updated: disables focus on all `.tab-scroll` and `#node-config-scroll` containers.
- `_move_keyboard_focus()`, `_scroll_config_widget_into_view()`, `_focus_first_config_tab_widget()` all updated to use `_scroll_container()` instead of direct `#node-config-scroll` query.
- CSS: added `.tab-scroll { height: 1fr; overflow-y: auto; }` and `#node-config-tabs { height: 1fr; }`.
- **This fixes the critical tab-disappearing bug on dense config forms.**

**Selector master-detail (`frontend/screens/node_selector.py` + `frontend/styles.tcss`):**
- Replaced the single-line `Static("", id="node-detail")` with a horizontal split: `ListView` (40%) + `VerticalScroll(id="node-detail-panel")` (60%) inside a `Horizontal(id="node-selector-body")`.
- `_update_detail()` now renders a full multi-line I/O contract instead of a truncated one-liner.
- Added `_render_node_contract()`: displays display name + description + Required Inputs / Optional Inputs / Required Outputs / Optional Outputs sections in 3-line-per-port format (`name* [type]` / description / `└─< sources` or `└─> dests`). Type labels use VS Code Dark+ teal `#4EC9B0` via Rich markup.
- Added `_render_group_detail()`: shows group name, description, member list, and hint text.
- Added `_fmt_port()` helper for per-port Rich markup formatting.
- CSS: `#node-selector-body { height: 1fr }`, `#node-type-list` narrowed to 40% width, `#node-detail-panel` 60% width with left border. `.node-detail` changed from single-line `height: 1` to expanding content style.

**Test baseline verified:** 138 failed / 189 passed before and after (all failures are pre-existing environment issues: missing `rich` and `pytest-asyncio` packages in system Python; no regressions introduced).

## 2026-06-19 — Docs: Reconcile Removed Subcategory Filter

- Follow-up to step 4: updated the UI docs that still described the removed
  subcategory filter-checkbox column. `UI_QUICK_REFERENCE.md` and `TUI_DESIGN.md`
  fully reconciled — no subcategory checkboxes, focus lands on the string filter,
  `tags` are freeform search keywords, details panel shows the per-port contract.
- `PHASE_17_NODE_VISUAL_IDENTITY.md` (the authoritative selector/visual-identity
  design doc, woven through with the subcategory concept): added a prominent
  "Revision — 2026-06-19" callout superseding the subcategory-filter design, and
  surgically fixed the most concrete false-existence claims (the per-tab filter
  table, the `tags` metadata description, the editor-row identity line, the
  details-panel statement). The deeper narrative rewrite is deliberately folded
  into the upcoming selector UI redesign rather than duplicated here.
- Branch `codex/docs-subcategory-reconcile` → fast-forwarded into `main`.

## 2026-06-19 — Track A Step 4 (owner-revised): Retire Subcategory Filter

- Continued on `codex/canonical-data-types` (after step 3). **Owner revised the
  adopted handoff:** the Category > Family > Type rename (§2.1/§3) is
  **cancelled** — the top tier keeps `primary_family` ("family") and the variant
  grouping keeps `group`. Instead, step 4 became **retiring the subcategory
  taxonomy** (`tags`), "never utilized correctly." Chosen scope (owner): remove
  the subcategory filter UI, keep `tags` as freeform search keywords.
- Frontend: removed the subcategory **filter-checkbox column** and all its
  machinery from `frontend/screens/node_selector.py` — the
  `#node-subcategory-filters` block, the `_selected_subcategories` filtering in
  `_apply_filter`, `on_checkbox_changed`, `_sync_subcategory_filter_visibility`,
  `_sync_selected_subcategories`, `_visible_subcategory_checkboxes`, the
  `TAB_FILTER_TAGS`/`ALL_FILTER_TAGS` constants, and the `Checkbox` import.
  `tags` still feed `_matches_query` (search). Dropped the matching
  `#node-subcategory-filters` rule from `styles.tcss`.
- Helper: dropped the rigid `VALID_TAGS` enforcement in
  `aotn_node_helper/generator.py`; tags are now freeform (any non-empty string).
- Tests: reworked the three selector tests in `test_debug_nodes.py` that
  depended on the filter checkboxes — renamed to drop "checkboxes/subcategory"
  and re-pointed navigation through the filter input; updated the runner list.
  Updated `test_node_helper.py` to assert freeform tags are accepted (was
  asserting rejection).
- Verified: `compileall -q .` clean; **full suite 331 passed**.
- Scope held: NO rename of `primary_family`/`group`/`category` (cancelled by
  owner); `tags` retained for search only. Docs: handoff Revision callout,
  `PROJECT_KNOWLEDGE.md`, `NODE_HELPER.md`. **Follow-up:** `PHASE_17_NODE_VISUAL_
  IDENTITY.md`, `TUI_DESIGN.md`, and `UI_QUICK_REFERENCE.md` still describe the
  removed subcategory filter UI and need a reconciliation pass.

## 2026-06-19 — Track A Step 3: Unified inputs:/outputs: Helper Spec

- Continued on `codex/canonical-data-types` (after step 2). Track A step 3 (§7):
  unified `inputs:` / `outputs:` helper-spec blocks carrying the full per-port
  contract, plus generator/check/test updates and one regenerated reference
  node. Read §7 precisely: it replaces `input_sources` + `input_port_metadata`
  (→ `inputs:`) and `output_port_metadata` (→ `outputs:`); node-level
  `output_routing` (Payloads config) is unchanged. Implemented additively so the
  six existing legacy specs keep generating.
- `aotn_node_helper/generator.py`: added `_expand_inputs_block` /
  `_expand_outputs_block` / `_contract_metadata`, and refactored the per-input
  source expansion into a shared `_input_source_fields` so the unified `inputs:`
  block and the legacy `input_sources` section emit byte-identical
  Source/Parameters fields. Port lists derive from the block keys; declaring a
  block alongside its legacy section (or `input_ports`/`output_ports`) is
  rejected. Port metadata now carries `data_type` / `required` / `sources`
  (inputs) and `data_type` / `required` / `to` / `pass_through` (outputs).
  Unknown port types **warn** (stderr), matching §5's soft-convention intent;
  `boolean` canonicalizes to `bool`. Added a local `CANONICAL_DATA_TYPES` mirror
  (kept in sync with `backend/data_types.py`, same pattern as `VALID_FAMILIES`).
  Render type hints for port metadata widened to `Dict[str, Dict[str, Any]]`;
  the generated focused test now asserts the per-port contract is exposed.
- Regenerated the reference node `example_file_instance_node` from the rewritten
  unified spec (`--force`). Diff confirms `config_schema` is **byte-for-byte
  unchanged** (round-trip equivalence — the `file_path_*` selectors are
  identical) while the port metadata gains the contract (`data_type` file/bool,
  `required`, `sources`/`to`, `pass_through`). Its input port is renamed
  `input → file_path` so the port name and source-field prefix are one name (the
  point of the unified model). `check_node` and `check_ui` both pass.
- Updated `tests/test_node_contract.py` (the step-2 assertion that the reference
  node had no declared type now asserts the declared bool/file contract).
  Added `tests/test_node_helper.py` cases: unified block emits the same
  selectors + adds contract, rejects legacy-section mix, rejects unknown `to`
  destinations, and warns (without raising) on an unknown port type.
- Verified: `compileall -q .` clean; helper + contract + data-type tests 26
  passed; **full suite 331 passed** (was 328; +3 new helper tests).
- Scope held: only ONE node regenerated (mass regeneration deferred, §11);
  Payloads routing still per-node via `output_routing` (per-port routing config
  is Track B step 7); no rename of `primary_family→category` / `group→family`
  (step 4). Docs: `NODE_HELPER.md` (new Unified inputs:/outputs: Blocks section).

## 2026-06-19 — Track A Step 2: Per-Port I/O Contract Fields

- Continued on `codex/canonical-data-types` (after the step 1 commit). Track A
  step 2 (§4/§6): add the per-port contract fields to node classes and expose
  them through `NodeFactory`, additive with documented defaults.
- `node_base.py`: documented the `input_port_metadata` / `output_port_metadata`
  contract (now `Dict[str, Dict[str, Any]]`) and added
  `_validate_port_data_types()`, called from `__init_subclass__`, which warns
  (not raises) via `data_types.validate_type` when a declared port `data_type`
  is outside the canonical set. This is the helper-facing validation surface the
  step 1 note promised, wired at class-definition time.
- `node_factory.py` `_port_metadata`: fills the §6 forward-compat defaults on
  exposure — absent `data_type` ⇒ `any`, absent `required` ⇒ `False` — and
  canonicalizes declared types (deprecated `boolean` ⇒ `bool`) via
  `coerce_type`. Existing nodes (which declare neither field) now expose
  `data_type: "any"` / `required: false` on every port with no node-file edits.
- Tests: `tests/test_node_contract.py` (defaults on every registered port,
  absent ⇒ any/optional, canonicalize+coerce, declared metadata survives
  exposure, unknown port type warns at class definition, canonical/alias types
  stay quiet). Verified: `compileall -q .` clean; `test_node_contract.py` +
  `test_data_types.py` 15 passed; `test_debug_nodes.py` + `test_node_helper.py`
  + `test_typed_vault.py` 150 passed; **full suite 328 passed**.
- Scope held: no node files regenerated (defaults are filled at exposure, so no
  per-node `required`/`data_type` were authored — that reference-node pass is
  step 3); `from:` / `to:` routing destinations are **not** exposed yet (they
  belong to the unified helper-spec step 3); validator does not yet consume
  `required` for incomplete-input detection (deferred with the frontend
  coloring per §6). No rename (step 4). Docs: `NODE_STANDARDS.md` (new Per-Port
  Contract Metadata section), `PROJECT_KNOWLEDGE.md` (metadata-exposure note).

## 2026-06-19 — Track A Step 1: Canonical Data-Type Module

- Branched `codex/canonical-data-types` from `main` @ `872ae66` (Add adopted
  Node Standardization Handoff doc). `git fetch` left the local base as the
  freshest reachable commit (SSL trust issue, per repo norm).
- Implemented `NODE_STANDARDIZATION_HANDOFF.md` Track A step 1 (§5): new
  `backend/data_types.py` is the single source of truth for the coarse
  data-type vocabulary shared by node port data types **and** typed vault-entry
  tags. Canonical set: `string`, `number`, `bool`, `var`, `file`, `ai_session`,
  `any`. `file`/`ai_session` are RunSession-backed reference types; `any` is the
  explicit permissive default (no silent untyped).
- **Reconciled** the vault-vs-port spelling conflict the handoff flagged: the
  typed-vault docs spelled boolean `boolean`; §5 (authoritative) uses `bool`.
  Canonical is now `bool`; `boolean` survives only as a deprecated alias that
  `canonicalize()` maps to `bool`, so older specs / saved workflows still
  resolve. No code stored the `boolean` literal (only docs + the `ai_session`
  literal in the validator), so the reconciliation is doc + alias only.
- Routed the one existing typed-vault consumer through the module: `validator.py`
  now compares against `DataType.AI_SESSION.value` instead of a free `"ai_session"`
  string. MemoryBank stores free `type_tag`s and is unchanged (no validation
  there); the validator is the meaningful single consumer today.
- Public surface: `DataType` enum, `CANONICAL_TYPES`, `REFERENCE_TYPES`,
  `DEFAULT_TYPE`, `LEGACY_ALIASES`, `UnknownDataTypeWarning`, and functions
  `is_valid_type`, `validate_type` (helper-facing — warns on unknown),
  `is_reference_type`, `canonicalize`, `coerce_type`, `port_data_types`,
  `vault_entry_types`, `unknown_types`.
- Tests: `tests/test_data_types.py` (canonical set, membership/validation,
  bool-not-boolean, reference types, explicit-`any` default, unknown-type
  warning, canonical-types-do-not-warn, vault/port lists agree). Verified:
  `compileall -q .` clean; `test_data_types.py` + `test_typed_vault.py` 18
  passed; `test_debug_nodes.py` 133 passed.
- Stayed in scope: no contract schema fields on node classes (step 2), no
  `primary_family→category` / `group→family` rename (step 4), no node
  regeneration or frontend selector edits. Docs touched: `NODE_STANDARDS.md`
  (Typed Vault Outputs), `PROJECT_KNOWLEDGE.md` (vault paragraph + Backend
  Components). Nothing required owner escalation — the only conflict (`boolean`
  vs `bool`) was resolved by the handoff itself.

## 2026-06-19 — Node Standardization Handoff Adopted

- Added `NODE_STANDARDIZATION_HANDOFF.md` (status: Adopted) — the design handoff
  consolidating the per-node I/O contract, Category > Family > Type rename,
  canonical data-type vocabulary, unified `inputs:`/`outputs:` helper spec, and
  master-detail selector into one implementation plan.
- Owner signed off the four §2 open decisions: (1) terminology rename approved,
  reusing the existing `category` key as canonical and retiring the
  `primary_family`/`legacy_category` aliases (`group → family`, `type`
  untouched); (2) drill-in family navigation; (3) one-line-per-port `to:`
  display in the detail panel; (4) no behavior badge — description carries
  behavior. Folded these into §2 (locked) and the affected body sections.
- Wired the router: README Document Directory row under Node Authoring + a
  `DOCS_MIGRATION_NOTES.md` "added" entry. Whitespace/LF clean.
- Not yet implemented — this is the plan. Next: Track A step 1 (canonical
  data-type module, §5). Track A step 4 (rename) runs after the contract schema
  work to avoid double-churning the same files.

## 2026-06-19 — Docs Audit: Taxonomy + Catalog Drift Fixes

- Ran the docs audit (active docs only) on `main` @ `2b681f2`. Verified
  environment: Python 3.14.4, Textual 8.2.7; registry has 35 nodes across 5
  families (Inputs, Outputs, Flow Control, Utility, Complex); backend has no
  `frontend` imports; `test_debug_nodes.py` 133 passed. Router integrity OK
  (all 19 active docs + 7 archive entries resolve).
- DRIFT (doc-vs-doc, Known Finding #1): `PROJECT_KNOWLEDGE.md` "Planned Node
  Taxonomy" listed four families with Utility as a subcategory. Reconciled to
  Phase 17's five families (Utility promoted) + four-tab / I/O-switch note.
  PHASE_17 is authoritative. Left the subcategory/`tags` concept intact
  (Known Finding #3 retirement still awaits owner decision).
- DRIFT (doc-vs-code): `NODE_CATALOG.md` omitted/mis-statused 4 live registered
  nodes. Added `http_request_node` (HTTP Request, Live) under Data Source;
  marked `text_transform_node` and `json_path_node` rows Live with `Maps from`;
  added `random_number_node` (Random Number, Live) under Data Transform.
- Did not edit `primary_family`/`tags` terminology in PROJECT_KNOWLEDGE or
  PHASE_17 (Known Findings #2 and #3 await owner decision).

## 2026-06-17 — Tabbed UI Keyboard Navigation Rework

- Branched `codex/keyboard-nav-rework` from `codex/textual-ui-overhaul`
  (commit `0bba5f6`, the just-committed Phase 17 visual overhaul), which is
  `main` + node-type-constants + the overhaul. `git fetch` is blocked by a
  local SSL trust issue, so the freshest reachable base was the local commit.
- WS1 — Row-based 2D navigation in the shared modules: added
  `group_widgets_into_rows` / `row_move_target` / `within_row_target` to
  `command_navigation.py` (rows grouped by nearest `Horizontal` ancestor, then
  by visual line, else one-per-row). `CommandScreenMixin` now moves W/S between
  rows (preserving column) and A/D within a row, gated so single-widget rows
  fall through to caret movement.
- WS1-apply — `node_config` and `node_selector` dropped A/D-as-tab-switch
  (including `CommandInput`'s `_run_screen_tab_action`); A/D is within-row. The
  selector I/O control is a two-button row (A/D between sides, E selects).
- WS2 — Number keys `1`–`5` jump tabs (gated to nav mode, no-op past the count);
  tab headers numbered `N - Label` in config and selector.
- WS3 — Verified the execution input prompt already uses `auto_edit_on_focus`.
- WS4 — `activate_command_widget` single-press toggles `Checkbox`/`Switch`.
- Stacked-widget audit (one-line rows of focusable widgets in command-mode
  screens): `node_selector` `node-family-tabs` (4 tab buttons) and
  `io-direction-row` (2-button I/O toggle). The simple modals
  (`confirm`/`error_details`/`user_input`) have `button-row` Horizontals but
  drive them with dedicated letter keys; the row model now also makes those
  navigable. `node_config` has no horizontal rows.
- Tests updated to the new contract and new tests added (row nav, within-row
  A/D, number jumps, digit-types-while-editing, single-press toggle). Full
  suite green: 311 passed.
- Flagged the selector family-taxonomy discrepancy (docs say Inputs/Outputs;
  code uses I/O + Utility) as a separate follow-up in `PROJECT_BACKLOG.md`.

## 2026-06-17 — Frontend Node-Type Constants Pass

- Started from branch `codex/node-type-constants` at `64dfb52`, after
  fast-forwarding `main` from `origin/main`.
- Added `frontend.node_types` as the frontend-owned home for structural node
  type identifiers used by editor/control-room behavior:
  `start_node`, `end_node`, `branch_node`, `branch_end_node`, `merge_node`,
  `text_output_node`, `tombstone_node`, and `wait_until_node`.
- Replaced repeated frontend literals in app startup, editor traversal/delete
  logic, editor workflow adapter tombstone/branch pruning logic, node config
  merge/wait/branch handling, node selector hiding, node card rendering, and
  node I/O display helpers.
- Preserved persisted workflow data shape: node `type` values remain the same
  strings. No branch pruning, merge deletion, tombstone restore, selector, or
  runtime logic was intentionally changed.
- Left test workflow fixture literals in place unless production imports
  benefited directly; those fixtures document saved/workflow data shapes.
- Deferred membank-registry consolidation and branch-port list consolidation
  to their separate passes.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "tombstone or branch_end or merge_node or node_selector or editor"` (41 passed)
  - `../.venv/bin/python -m pytest tests/test_branch_prune.py tests/test_branch_health.py tests/test_tombstone_restore.py tests/test_tombstone_migration.py tests/test_tombstone_phase_b.py -v` (58 passed)
  - `../.venv/bin/python -m pytest -q` (308 passed)

## 2026-06-16 — Frontend Review Cleanup Pass

- Started from branch `codex/frontend-review-cleanups` at `03e6432`, aligned
  with `origin/main` after PR #20.
- Continued the frontend convention review from the Pass 1/2/3 inventory.
- `EditorScreen._metadata_for_type()` and `NodeConfigScreen._metadata_for_type()`
  now delegate to the shared `frontend.node_io_display.metadata_for_type()`
  helper.
- `NodeConfigScreen` now uses the shared membank normalizers from
  `frontend.node_io_display` instead of maintaining duplicate definitions.
- Removed unused `EditorScreen._format_input_ports()` and
  `_format_output_ports()`.
- Deferred wider follow-ups to separate passes: node-type constants,
  membank-registry consolidation, branch-port list consolidation, and selector
  tab-name docs drift.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_config or editor_identity_rows or quick_view or payloads_tab or command_inputs"` (20 passed)
  - `../.venv/bin/python -m pytest tests -v` (308 passed)

## 2026-06-16 — Branch Pruning Ignores Unreachable Merge Feeds

- Continued debugging on branch `delete_branch_bug` after pulling
  `origin/delete_branch_bug`.
- Found a remaining branch-prune gap: `prune_branch_tombstone()` preserved a
  `merge_node` whenever any input source existed outside the pruned set, even
  if that source was itself unreachable from `start` after the branch tombstone
  was removed. That could leave merge tails alive in `_nodes`, and the
  validator would still report them as unreachable after the editor appeared to
  have pruned the branch.
- Fixed merge preservation to use post-prune reachability: simulate removing
  the branch tombstone and current prune set, add the kept-path upstream
  rewire, and only count merge input sources reachable in that future graph.
  Reachable alternate feeds still preserve the merge; loose/unreachable feeds
  no longer do.
- Added focused coverage for both cases in `tests/test_branch_prune.py`,
  including a validation assertion for the surviving-feed path.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_branch_prune.py -v` (15 passed)

## 2026-06-16 — Merge Delete Rewires Home Branch and Flags Open Beacons

- Reported as: deleting a `merge_node` made downstream nodes disappear from
  the usable path. Desired behavior is to delete only the merge node, bridge
  the branch where the merge lived to the immediate downstream node when ports
  are compatible, and disconnect Merge Beacon inputs from other branches so
  the user can rewire them manually.
- Fixed `EditorWorkflowAdapter.remove_placeholder()` with a merge-specific
  reconnect path: after `WorkflowMap.delete_node()` removes the merge and all
  beacon→merge references, the adapter reconnects the non-`branch_end_node`
  upstream input to the merge's direct downstream output if both ports are
  declared and currently open. Beacon branches are intentionally not rewired.
- `validate_workflow()` now uses backend branch-health derivation to warn when
  a branch reaches a Merge Beacon that is not connected to a merge node, so
  disconnected beacons left by merge deletion surface as repair work.
- Updated editor and branch-health tests for the new contract.
- Verification:
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_prune.py -v` (15 passed)

## 2026-06-16 — Branch Pruning Treats Output Nodes as Terminal Boundaries

- Reported as: deleting a branch could leave a `text_output_node` from the
  pruned branch alive in validation even though the editor no longer showed a
  reachable path to it.
- Decided against a mutable `valid_branch_end` config flag. The boundary is a
  node-type contract, so pruning now derives terminal behavior from node
  semantics: Outputs-family nodes, `text_output_node`, `end_node`, and Merge
  Beacons are inclusive branch-prune boundaries.
- Updated `prune_branch_tombstone()` so terminal nodes on non-kept branches are
  deleted but traversal does not continue past them. Merge Beacons remain a
  special terminal: they are deleted and any connected `merge_node` is still
  evaluated for orphan cleanup.
- Added a regression proving a pruned branch ending at `text_output_node`
  removes that output node and validation no longer reports it.
- Verification:
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_prune.py -v` (16 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest AttackOfTheNodes/tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)

## 2026-06-16 — Kept Merge Beacon Branch Drops Old Merge Output

- Reported as: simple branch workflow with path A containing a `merge_node` and
  path B containing a Merge Beacon connected to that merge. Deleting the branch
  node, keeping the Merge Beacon branch, and pruning the merge branch left the
  old merge connection in the kept beacon's later tombstone metadata; deleting
  the beacon then rendered the pruned merge below the tombstone.
- Root cause: branch-prune survival checks simulated future reachability by
  following the kept branch head's current outputs. For a kept Merge Beacon,
  that meant following its pre-prune output into the merge and treating the
  merge as still live.
- Fixed: Merge Beacons are now included in `_is_branch_prune_terminal()`.
  `prune_branch_tombstone()` disconnects outputs from the kept branch terminal
  before resolving pending merges, and the future-reachability simulation stops
  at terminal nodes. The kept beacon remains as an open terminal, while the
  old merge is pruned and cannot be captured in later tombstone
  `original_outputs`.
- Added a regression covering the exact keep-beacon/prune-merge sequence and
  later beacon tombstone materialization.
- Verification:
  - `.venv/bin/python -m pytest tests/test_branch_prune.py -v` (17 passed)
  - `.venv/bin/python -m pytest tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)
  - `.venv/bin/python -m compileall -q .`

## 2026-06-16 — Kept Merge Branch Preserves Merge Downstream Nodes

- Reported as the mirror case of the kept-beacon fix: path A contains a
  `merge_node` and downstream output node, path B contains a Merge Beacon
  connected to that merge. Deleting the branch node and keeping path A pruned
  the beacon branch, but also pruned the merge's downstream nodes.
- Root cause: pending merge cleanup only considered the merge's old input
  sources. In the kept-merge case, the old input source is the deleted branch
  node, but the future graph rewires the branch node's upstream directly into
  the merge. The cleanup therefore misclassified the kept merge as orphaned
  and cascaded into its downstream nodes.
- Fixed pending merge resolution to treat the kept branch head as live when it
  is the pending `merge_node` and it is reachable in the simulated future graph.
  The pruned Merge Beacon branch is still deleted; the kept merge and its
  downstream output chain remain intact.
- Added a regression for path A `merge_node -> text_output_node`, path B
  `Merge Beacon -> same merge`, keep path A.
- Verification:
  - `.venv/bin/python -m pytest tests/test_branch_prune.py -v` (18 passed)
  - `.venv/bin/python -m pytest tests/test_branch_health.py -v` (15 passed)
  - `.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "merge_node_delete or merge_beacon or branch_end or branch_keep"` (11 passed)
  - `.venv/bin/python -m compileall -q .`

## 2026-06-16 — Insert Into Empty Branch Now Targets the Branch Being Viewed

- Reported as: switch to an empty parallel branch (`d`), insert a node — it
  visually shows up there, but switching away and back makes it disappear
  from that branch and reappear on a different one (whichever branch's port
  is declared first on the `branch_node`).
- Root cause: when the active branch path is empty, there is no node to
  select yet, so the selected row falls back to the `branch_node` itself with
  `kind: "node"` rather than `kind: "branch_select"`. `_source_for_insert_node()`
  has a correct `branch_select`-specific case that reads `active_branch_ports`,
  but the generic `kind: "node"` fallback just used the branch node's first
  declared output port unconditionally — ignoring which branch was actually
  being viewed.
- Fixed: in that fallback, when the selected node has multiple output ports
  (i.e. it's a branch node) and an active branch port is recorded for it, use
  that active port instead of always taking the first one.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest -q` (303 passed, includes new
    `test_editor_insert_into_empty_branch_uses_active_branch_port`)
  - Reproduced via a standalone Textual pilot script matching the reported key
    sequence exactly (create branch, fill path_a, `d` to path_b, insert, `a`
    back to path_a, `a` again) before and after the fix.

## 2026-06-16 — Branch Pruning No Longer Leaves Orphaned Merge Beacons or Merge Nodes

- Reported as: deleting a branch whose non-kept path fed a Merge Beacon (which
  in turn fed a `merge_node`) left a node behind that the validator flagged as
  unreachable, even after the workflow looked fully repaired in the editor.
- Root cause #1: `prune_branch_tombstone()`'s stop-type set included
  `branch_end_node`, treating Merge Beacons as permanent structure. A beacon
  belongs exclusively to the one branch it closes, so a beacon reached while
  pruning a non-kept branch must be deleted along with the rest of that
  branch, not preserved.
- Root cause #2 (cascading orphan): `merge_node` was an *unconditional* stop
  type. If the branch being pruned was a `merge_node`'s only remaining input,
  the merge_node was left behind fully disconnected from upstream — alive in
  the workflow but unreachable from start, with no way to fix it short of a
  manual node delete (re-typing it via the node selector keeps the same
  disconnected node, since type-swap doesn't restore connections).
- Fixed: `branch_end_node` removed from the stop-type set entirely. `merge_node`
  is now a *conditional* stop — pruning resolves each encountered merge_node by
  checking whether any of its current inputs come from a source outside the
  pruned set (and outside the branch tombstone itself). If none remain, the
  merge_node is pruned too, and pruning cascades through its own downstream
  nodes (re-applying the same check to any further merge_node reached that
  way). A merge_node with a genuinely surviving feed (another live branch)
  is still preserved untouched.
- Confirms the broader guarantee: pruned nodes go through
  `WorkflowMap.delete_node()`, which removes them from the same `_nodes` dict
  that gets serialized on save — a pruned node cannot reappear in a save file
  or in any validator output once `prune_branch_tombstone()` correctly
  identifies it for pruning.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest -q` (302 passed)
  - End-to-end repro matching the reported scenario (branch → kept path into
    merge_node path_a, pruned path → Merge Beacon → merge_node path_b → output):
    validator returns `{"success": true, "errors": [], "warnings": []}` after
    pruning, with only 3 nodes left in the workflow.

## 2026-06-16 — Merge Config No Longer Offers Downstream Branches to Close

- `merge_input_options()` listed every `branch_end_node` in the workflow as a
  candidate to close, including beacons whose owning branch point only starts
  *after* passing through the merge node being configured. Closing such a
  branch is structurally backwards (the branch doesn't exist yet at the point
  the merge runs).
- Root cause: `_branch_contexts_by_node()`'s DFS stops at every Merge Beacon,
  so neither a merge node nor anything downstream of it is ever assigned a
  branch context — `merge_input_options` had no signal to exclude beacons
  whose branch point is downstream of the merge.
- Fixed by computing the forward-reachable descendant set of the merge node
  being configured (`_descendant_node_ids`) and excluding any beacon whose
  context `branch_id` (the originating branch node) falls in that set.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest -q` (299 passed)

## 2026-06-16 — Merge Beacon Selector Colors Match Connected Merge Branch

- When a Merge Beacon (`branch_end_node`) is connected to a `merge_node`, the
  beacon's selector row text/connector line and its own gutter/numline color
  now match the branch that contains the merge node, instead of the beacon's
  own branch color.
- Added `_merge_node_branch_color_key()`, which reuses
  `_branch_choices_to_node()` to find the branch-port decisions leading to the
  merge node; the last decision's port plus `len(choices) - 1` reproduces the
  same `branch_path_color_key` that `_build_visible_rows` would assign if that
  branch were the active view.
- `_build_visible_rows` now resolves this key for non-placeholder beacons with
  a connected merge node, stores it on the node dict
  (`_editor_branch_color_key`) so `NodeCard` picks it up for the gutter, and
  passes it into `_merge_beacon_select_row` as the row's `active_color_key`.
  Falls back to `current_branch_color_key` when the beacon has no connected
  merge node.
- Merged cleanly on top of the same-session "Merge Node Delete +
  Stranded-Beacon Visibility Fix" change below, which restructured the same
  `branch_end_node` block; the manual resolution preserves both the
  placeholder fall-through fix and this color-key override.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "merge_beacon_selector or node_selector or node_card or editor_depth or branch_end or branch_keep or tombstone"` (18 passed)

## 2026-06-16 — Merge Node Delete + Stranded-Beacon Visibility Fix

Branch: `claude/editor-keyboard-focus-highlight-9fp46y`.

- **`merge_node` is now deletable:** removed `_is_protected_structural_node`
  (it only ever blocked `merge_node`). Deletion follows the plain single-node
  rule — `WorkflowMap.delete_node()` already scrubs connection references on
  both sides, so every Merge Beacon that fed the deleted merge node (and
  anything downstream of it) simply becomes disconnected. Nothing is
  auto-rewired; the user reconnects each beacon manually. Dropped the now-dead
  `cannot_delete_structural_node` notification.
- **Merge Beacon delete already matched spec:** verified
  `_prune_merge_config_for_beacon` / `_disconnect_beacon_merge_outputs` only
  severs the one beacon→merge connection (and that beacon's stale entry in
  `branches_to_close`), leaving other branches and the merge node untouched.
- **Fixed the "stranded node" bug:** `_build_visible_rows` had an unconditional
  `break` on `branch_end_node` rows, even when the beacon was only
  soft-tombstoned (first delete press). Soft-delete never touches backend
  connections, so this made everything past the beacon — including the
  `merge_node` and its downstream — disappear from the editor despite still
  being fully connected. Once the user then saved or validated,
  `materialize_deleted_nodes()` converted the beacon into a real tombstone and
  *did* drop its connection, so what looked like a pre-existing problem turned
  into an actual disconnect, with the tombstone flagged by the validator and
  the editor still not showing any of it. Fixed by only taking the
  beacon-select-row-and-break path when the beacon is not currently a
  placeholder; a soft-deleted beacon now falls through to normal single-port
  traversal so downstream nodes stay visible until the delete is made
  permanent (at which point the node is actually gone and stops showing up in
  validation, as expected).
- Tests: replaced `test_editor_merge_node_delete_stays_blocked` with
  `test_editor_merge_node_delete_disconnects_beacons`; added
  `test_editor_soft_deleted_beacon_keeps_downstream_visible`. Full suite: 299
  passed (`python -m pytest -q`).
- Updated `BACKEND_FRONTEND_BOUNDARY.md` and `PROJECT_KNOWLEDGE.md` to describe
  the Merge Beacon / `merge_node` delete contract instead of "stays blocked."

## 2026-06-16 — Editor Delete Fixes: Keyboard Focus, Gap Shift-Up, Branch Delete

Branch: `claude/editor-keyboard-focus-highlight-9fp46y`.

- **Keyboard focus highlight:** added `up`/`down` editor bindings (priority)
  routed through `_move_selection` so arrow keys skip non-selectable gap rows
  like `W`/`S` already did; added a `NodeList.watch_index` safety net that snaps
  off any gap row. Arrow-key navigation no longer loses the focus highlight on
  the `▼`/`➥` gap lines between node cards.
- **Delete no longer hides downstream nodes:** `_build_visible_rows` was breaking
  the moment it hit a placeholder, discarding the rest of the chain. Soft-deleted
  nodes keep their live connections, so they now fall through to normal port
  traversal; materialized tombstones (outgoing connections dropped on save)
  continue via `original_outputs`.
- **Permanent delete shifts downstream up:** `remove_placeholder` now captures the
  tombstone's upstream/downstream connections before `delete_node` and rewires
  upstream → downstream so the gap closes instead of orphaning the tail. Branch /
  start / merge tombstones are excluded (they have structural reconnection paths).
- **Branch-node delete now reachable:** `_is_protected_structural_node` no longer
  blocks `branch_node` (only `merge_node`). A connected branch now soft-tombstones
  on first delete and opens `BranchKeepSelectorScreen` on the second, wiring the
  previously-dead `prune_branch_tombstone()` flow into the UI. Documented the
  branch-delete exception to the single-node rule in `BACKEND_FRONTEND_BOUNDARY.md`
  and `PROJECT_KNOWLEDGE.md`.
- **Tombstone label** shortened from `Deleted node:` to `Deleted:` in the editor
  card.
- Tests: added `test_editor_branch_node_deletes_through_keep_selector` and
  `test_editor_merge_node_delete_stays_blocked`; updated label and shift-up
  assertions in `test_debug_nodes.py`. Full suite: 298 passed
  (`python -m pytest -q`, with `pytest-asyncio` for the generated async tests).

## 2026-06-15 — Editor Branch Connectors: Branch Border Coloring (explored, reverted)

- Attempted to color the ASCII box borders (`+`, `-`, `|`) of branching nodes
  and branch-end (merge beacon) nodes to mirror the branch path colors already
  used on branch-select cards and numline gutters.
- Branching node border was set to `active_color_key` (the downstream branch
  color); merge beacon border was set to a stable hash-derived color from the
  connected merge node's ID; `BranchSelectCard` and `MergeBeaconSelectCard`
  foregrounds were switched to the merge-node color when connected.
- Reverted (commit `b55b38fb5`) because the approach has a fundamental design
  mismatch: the branching node is a single static card in the editor, but the
  active branch color changes every time the user switches which branch is
  visible. Coloring the box border with the currently-active branch would make
  it flicker on every branch switch rather than conveying stable structural
  identity.
- **Design note for future attempts:** border color on a branching node can only
  work if it conveys something that does not change per branch switch — for
  example, the node's own family color, a depth-level color, or a color derived
  from the branching node's own identity rather than from the active branch port.
  The downstream numline and branch-select colors are per-path and are not
  suitable as a static node-box border color.

## 2026-06-15 — Editor Branch Connectors: Ten-Color Branch Paths

- Fast-forwarded local `main` from `899c155` to `3139181` before starting,
  per the session sync rule.
- Replaced the five-entry branch path color map with a ten-color palette tuned
  for the dark Textual editor background / `ansi-dark` style usage.
- Branch path rendering now uses frontend-only color keys so each branch node
  consumes the palette in sequence: five-path branch one uses colors 1-5,
  branch two uses colors 6-10, then the next branch cycles back.
- Kept raw port-name color lookup (`path_a`-`path_e`) working for existing
  manual rows and tests while editor-built rows use the richer sequence keys.
- Threaded the sequence color key through node gutters, gap arrows, branch
  selector rows, and Merge Beacon selector rows so one visible path segment
  stays consistently colored from branch start through branch end.

## 2026-06-15 — Editor Branch Connectors: Path Colors

- Added branch path coloring for up to five Branch outputs in editor selector
  connector rows. Rich renders the requested CSS colors via hex equivalents:
  lightseagreen, lightblue, steelblue, turquoise, turquoise.
- Branch and merge selector rows now draw `├──` / `└──` from the depth gutter
  into a node-column `─` line that ends with `⟶ [ Branch name ]`, with no
  pointer symbol.
- Connector stems align under the node-row `|` continuation marker, connector
  tails extend to the node-column line, and branch selector labels are centered
  under the node box while accounting for the arrow/bracket prefix.
- The connector gutter and node-column line are styled with the same branch
  path foreground color; selected-row backgrounds still begin after the depth
  gutter.
- Selector lines stop at the branch/merge label instead of continuing on the
  far side of the widget text.
- Downstream node rows carry the visible branch path as frontend-only display
  metadata so number-column numbers and `|` symbols use the branch path color.
- The initial visible path now starts as `path_a`, giving the start/first branch
  segment the same branch color treatment as Branch path 1.
- Branch and merge selector labels use square brackets instead of a right-side
  `|` because the closing bar read poorly in the terminal.
- Depth-number rows use standard non-zero-padded numbers left-aligned in the
  number/gutter column; branch symbols and `|` continuation markers are also
  left-justified there.
- Gap rows between nodes carry branch path color so the `|` immediately before
  a branch node matches the active branch path.
- Merge incoming `┤` now renders on the first continuation line of the merge
  node itself, so a merge directly after a Branch selector no longer collides
  with the Branch selector connector.
- Branch-colored `|` continuation markers render bold to better match branch
  path connector weight.
- Gap markers now reflect source-node outputs: `↓` for transient output,
  `↳` for one configured Vault output, or `➥N` for multiple Vault outputs,
  centered under the node box.
- Continued the gutter rule from the boxed node rows: numbered top rows show
  the depth number, while node box continuation rows use `|` in the number
  column.
- Focused checks: `../.venv/bin/python -m compileall -q .` and
  `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector
  or node_card or editor_depth or branch_end or editor_identity_rows or
  merge_beacon_selector"` (17 passed).

## 2026-06-15 — Editor Node Rows: Gutter, Default Background, Gap Arrows

- Moved the depth number/gutter outside the node text box by drawing the ASCII
  border inside `NodeCard` instead of using a whole-widget border.
- Moved the visible selection highlight off the full `ListItem` row and onto
  the node/jump box text area only, so the depth gutter does not get covered by
  the selected-row background.
- Removed decorative family color fills from node rows; node interiors now
  render on the default editor background.
- Added centered non-focusable `↓`/`↓↓` markers in the existing insertion gap
  between ordinary node rows. They are disabled ListView rows, so selection
  jumps over them.
- Centered branch and merge jump widgets under the node box; these replace the
  down-arrow gap marker when present.
- Focused checks: `../.venv/bin/python -m compileall -q .` and
  `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector
  or node_card or editor_depth or branch_end or editor_identity_rows"` (15
  passed).

## 2026-06-15 — Editor Node Rows: Textual ASCII Borders

- Fixed the Phase 17 editor node rows on `main`: the previous merge still had
  the older family bracket/frame rendering (`[ ]`, `< >`, `{ }`) in
  `frontend/widgets/node_card.py`.
- `NodeCard` identity rows render plain alias and family/subcategory text
  inside an ASCII text box. Deleted-node rows use the same plain-text-in-box
  treatment. Later same-day follow-up moved the depth gutter outside the box.
- Removed the old bracket-specific branch selector indent so branch selector
  labels line up with node text again.
- Updated active UI docs to prefer Textual ASCII node-card borders instead of
  fixed bracket columns.
- Focused checks: `../.venv/bin/python -m compileall -q .` and
  `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or
  editor_depth or editor_identity_rows"` (4 passed).

## 2026-06-15 — Documentation Sync: Backend/UI Gap List

- Fast-forwarded local `main` to `origin/main` after confirming the previous
  docs work had landed remotely through the `codex-textual-tui-spinoff` merge.
- Confirmed `README.md` routes Phase 17 and active docs correctly, and
  `MASTER_BUILD_PLAN.md` still marks Phase 17 in progress.
- Added an explicit `PROJECT_BACKLOG.md` section for backend features not yet
  surfaced in the Textual UI: run history browser, secrets management UI,
  tombstone restore report alerts, branch-health visualization, schema-driven
  file pickers for node config, memory snapshot save/load choices, workflow
  rename/bookmark controls, and error clearing controls.
- Linked that gap list from `MASTER_BUILD_PLAN.md`, `AGENT_HANDOFF.md`, and
  the README document directory so future agents do not need to rediscover it.

## 2026-06-13 — Backend & edit-time performance: two O(n^2) fixes

- Audit context: a backend execution-overhead study measured per-node cost
  over the real Supervisor/MasterState/EventBus/MemoryBank stack and found it
  small and linear (~15 us/node) relative to real node I/O — so rewriting the
  execution manager in C is not warranted. Two O(n^2) hot spots were found and
  fixed; remaining lower-leverage items are deferred to `PROJECT_BACKLOG.md`.
- `backend/memory_bank.py`: `MEMORY_UPDATE` now publishes a lightweight delta
  (e.g. `{"change": "set", "key": ...}`) instead of `get_state()`. Each
  persistent write previously deep-copied both the persistent and transient
  stores; since both grow over a run, per-write cost scaled with run size
  (O(n^2) overall). The sole subscriber (`app._on_backend_event`) ignores the
  payload and re-pulls `get_state()` on demand, so the live Memory Viewer and
  dead-drop preview are unchanged. Measured vault-writing chain (us/node):
  24.4/28.8/36.2 at n=500/1000/2000 → flat 16.9/15.1/15.3.
- `backend/workflow_map.py`: `_mark_dirty()` no longer calls
  `_sync_active_to_cache()`. That sync deep-copied the entire `_nodes` graph
  into the open-workflow cache on every editor mutation (add/connect/config/
  delete), making building/editing an N-node workflow O(n^2) — a 4000-node
  graph never finished constructing. The active workflow's live state is
  `self._nodes`; the cache is refreshed lazily before every path that reads it
  (switch/close/list) or replaces the active workflow (load/create/save), all
  of which already sync. Editing is now O(n): build ~2.5 us/edit and flat
  (1000/2000/4000/8000 nodes → 5.4/9.8/20.2/46.1 ms); a 4000-node workflow now
  builds (34ms) and runs to FINISHED (50ms).
- Diagnosis used a throwaway microbenchmark and a `faulthandler` stack dump
  (which pinned the edit-time deepcopy); benchmark scripts were not committed.
  Full suite: 284 passed.

## 2026-06-13 — Headless Plan H6: docs reconciliation + plan archived

- Updated `PROJECT_BACKLOG.md`: tombstone save (H1) and restore (H2) marked
  done under boundary cleanup (only the restore-alert UI remains, deferred);
  Secrets project reduced to the `SettingsScreen` tab (schema fields +
  validator wiring done, H3); branch-health derivation marked done with the
  editor colour pass remaining (H5); form-generator label/value and schema-key
  tests marked done (H4).
- `MASTER_BUILD_PLAN.md`: phase 10.6 → Done (restore-alert UI + Phase C
  metadata deferred); added an H1–H5 entry to Recently Completed.
- Archived `HEADLESS_BUILD_PLAN.md` → `archive/plans/`; moved its README
  directory row to the Archive table; logged the move in
  `DOCS_MIGRATION_NOTES.md`.
- Headless plan complete: H1–H6 done, full suite 284 passed. Remaining backlog
  work from this plan is UI-only and needs live-TUI verification.

## 2026-06-13 — Headless Plan H5: backend branch health derivation

- New `backend/branch_health.py`: pure-logic `derive_branch_health(all_nodes,
  output_node_types=None)` classifies each `branch_node` outgoing edge (one
  spawned parallel path) into `valid` / `ended_unmerged` / `floating` by
  walking the path forward — `merge_node` or output/end node or
  merge-connected Merge Beacon → valid; Merge Beacon not wired to a merge →
  ended_unmerged; dead end / cycle / unconnected port → floating. Nested
  `branch_node`s count as valid for the outer path and are classified on
  their own merits. Returns frozen `BranchHealth` dataclasses; states are
  module constants (`VALID`, `ENDED_UNMERGED`, `FLOATING`).
- `branch_health_by_port()` keys results by `(branch_node_id, port)` to match
  how editor branch rows are keyed, so the deferred FA-7 visual pass can map
  states to colours with O(1) lookups and no re-derivation.
- `output_types_from_factory(factory)` builds the valid-output-type set from
  node metadata (Outputs family + `end_node`, plus `text_output_node`), so
  the policy tracks the taxonomy; the function also works with no factory via
  `DEFAULT_OUTPUT_NODE_TYPES`. No frontend imports — backend stays UI-agnostic.
- Tests: `tests/test_branch_health.py` (14 tests) — one fixture per state,
  chain-to-output, direct-merge, mixed multi-port branch, nested branches,
  unconnected port, cycle, no-branch empty, the by-port mapping, and the
  factory/default output-type paths. Full suite: 284 passed.
- Visual surfacing in the editor (branch-health colours, FA-7 pass) stays
  deferred — it needs live-TUI verification.

## 2026-06-13 — Headless Plan H4: form generator label/value selects + key coverage

- `frontend/widgets/form_generator.py`: `_select_options()` now normalizes
  option entries — plain scalars (label == value, unchanged),
  `{"label": ..., "value": ...}` mappings, and 2-item sequences — so the
  backend reads stable machine values while the dropdown shows display
  labels. Applied to `select`, option-bearing string fields, and
  `multiselect` (initial selection matches by machine value). Value
  read-back needed no change: `Select.value` / `SelectionList.selected`
  already return the value half.
- Helper specs need no changes: `aotn_node_helper` copies field schemas
  verbatim, so YAML specs can declare label/value option dicts today.
- Tests: new `tests/test_form_generator.py` (12 tests) — option
  normalization shapes, label/value round-trips per widget type, and the
  previously untested schema keys: `label`/`required` star, `description`,
  `default`, `boolean` round-trip, integer `min`/`max` validator, string
  `min_length`/`max_length` validator, `code` `language`, and numeric
  coercion fallback. Full suite: 270 passed.

## 2026-06-13 — Headless Plan H3: secrets schema flags + editor wiring

- Secret-ref schema fields added (`"secret": True`, optional while execution
  is stubbed): `api_key_secret` on `chat_completion_node`, `embedding_node`,
  `image_generation_node`; `auth_token_secret` on `http_request_node`. The
  HTTP node actually uses it: when configured, the request sends
  `Authorization: Bearer <secret>` resolved via `context.get_secret()`. The
  helper spec `aotn_node_helper/specs/http_request_node.yaml` carries the
  field so regeneration keeps it.
- `main.py` now constructs a `SecretsManager` and passes it to `MasterState`
  (runtime path was previously unwired) and to the app.
- `frontend/app.py` / `EditorScreen` accept `secrets_manager`;
  `action_validate_workflow` forwards it to `validate_workflow`, so
  editor-triggered validation surfaces missing-key warnings live.
- Tests appended to `test_validator_secrets.py`: all four nodes declare the
  secret field, per-node missing-store-key warning, and a pilot test proving
  the editor wiring (details screen opens with a manager, clean without).
  Full suite: 258 passed.

## 2026-06-13 — Headless Plan H2: tombstone restore engine

- `frontend/editor_workflow_adapter.py`: new
  `EditorWorkflowAdapter.restore_tombstone(node_id)` implements the
  connection-validated restore procedure from `BACKEND_FRONTEND_BOUNDARY.md`.
  Node type/alias/config always come back; each stored input connection is
  reconnected only when the source node exists and still declares the output
  port; each stored output connection only when the target exists, declares
  the input port, and that port is not occupied by a different source;
  membank input declarations are restored with the config and flagged when no
  surviving node declares the variable.
- Returns a `TombstoneRestoreReport` dataclass (input_errors, output_errors,
  membank_warnings with node id/alias/port/reason) — plain data for the
  deferred frontend alert; no UI copy in the adapter.
- `undo_placeholder()` and `replace_placeholder()` (restore-original path)
  now route through `restore_tombstone()`, so editor undo also validates
  drift instead of blindly reconnecting; `replace_placeholder()` returns the
  report under `restore_report`. The blind `_restore_downstream_inputs`
  helper was removed.
- Tests: `tests/test_tombstone_restore.py` (11 tests) covers the clean path,
  every drift category (source gone, source port gone, target gone, target
  port occupied, membank source missing), rejection paths, the replace-modal
  report, and that a partial restore clears the validator's tombstone error.
  Full suite: 252 passed.

## 2026-06-13 — Headless Plan H1: tombstone direct save

- `frontend/editor_workflow_adapter.py`: `materialize_deleted_nodes()` now
  writes `tombstone_node` with the full original-data config (contract shape
  from `BACKEND_FRONTEND_BOUNDARY.md`: `original_type/display_name/alias/
  config/inputs/outputs` plus the port lists the validator reads). No save
  path writes `branch_end_node + _system_role` anymore.
- New module helpers `tombstone_config_from_metadata()` /
  `metadata_from_tombstone_config()` define the config↔metadata mapping in
  one place; `migrate_legacy_deleted_node()` now carries full restore data
  (alias, config, connections) instead of ports only, so legacy saves keep
  undo-after-reload.
- `is_materialized_placeholder()` recognizes `tombstone_node` (legacy marker
  still recognized until load migration runs); `placeholder_metadata()` reads
  tombstone config directly — editor rendering, undo, and replace flows work
  on the new format unchanged.
- Tests: tombstone round-trip + undo-after-materialize-with-fresh-adapter in
  `test_tombstone_phase_b.py`; full-data migration carry in
  `test_tombstone_migration.py`; materialize/save/loaded-marker tests in
  `test_debug_nodes.py` updated to the tombstone format, with a
  tombstone-format loaded-row render check added. Full suite: 241 passed.

## 2026-06-13 — Headless Build Plan created

- Added `docs/HEADLESS_BUILD_PLAN.md`: phased plan (H1–H6) covering the
  backlog work that is fully verifiable with `compileall` + `pytest`, with
  no live-TUI verification required — tombstone direct save (H1), tombstone
  restore engine per the 2026-06-11 design spec (H2), secrets schema flags +
  editor validator wiring (H3), form generator label/value selects + schema
  key test coverage (H4), backend branch health derivation (H5), and docs
  reconciliation (H6).
- Each phase lists tasks, likely files, focused pytest checks, and exit
  criteria; live-app work (Phase 17 verification, Secrets settings tab, AI
  session config UI, branch health indicators) is explicitly deferred and stays
  in `PROJECT_BACKLOG.md`.
- Added the new doc to the `README.md` Document Directory.

## 2026-06-12 — SecretsManager + Backend Build Plan (Phases 1–6)

### SecretsManager module

- Added `backend/secrets_manager.py`: plain-text JSON store at
  `secrets/secrets.json` (gitignored). Public API: `get_secret`, `set_secret`,
  `delete_secret`, `list_keys`, `has_key`, `reload`. Lazy-load with single
  trust boundary — only this module changes when encryption is added.
- Extended `NodeContext` in `node_base.py` with `secrets_manager` field and
  `context.get_secret(key)` convenience wrapper (returns `None` when no manager
  wired in).
- Wired `SecretsManager` through `MasterState.__init__` → both `Supervisor`
  creation sites → `NodeContext` kwargs. Nodes never call the manager directly;
  they call `context.get_secret(key_name)`.
- Created `secrets/` directory with `.gitkeep`; added
  `AttackOfTheNodes/secrets/secrets.json` to `.gitignore`.
- 18 tests in `tests/test_secrets_manager.py` (CRUD, persistence, lazy-load,
  reload, invalid-JSON fallback, NodeContext integration).

### Backend Build Plan Phases 1–6

**Phase 1 — Tombstone `editor_only` + validator port context**
- `node_identity.py`: added `"editor_only": True` to tombstone entry;
  `apply_transitional_node_identity` copies flag onto node class.
- `node_factory.py`: `get_node_types_metadata` exposes `editor_only` key.
- `validator.py`: tombstone error message appends
  `"(orphaned inputs: X; outputs: Y)"` when port config is present.
- Tests: `tests/test_tombstone_phase_b.py` (4 tests).

**Phase 2 — Legacy save migration**
- `frontend/editor_workflow_adapter.py`: added `migrate_legacy_deleted_node()`
  (pure function) and `EditorWorkflowAdapter.migrate_workflow_on_load()`.
  Converts `branch_end_node + _system_role: deleted_node_branch_end` to
  `tombstone_node` in-place without touching plain Merge Beacons.
- Tests: `tests/test_tombstone_migration.py` (7 tests).

**Phase 3 — Typed vault entries**
- `memory_bank.py`: `store_persistent` accepts `type_tag=None`;
  `read_persistent_by_type(type_tag)` added; state snapshot includes
  `persistent_type_tags`; backward compatible with old snapshots.
- `validator.py`: `_declared_membank_outputs` returns `Dict[str, Optional[str]]`
  (key → type_tag); warns on ai_session type mismatch.
- Tests: `tests/test_typed_vault.py` (9 tests).

**Phase 4 — LLM chat session in RunSession**
- `run_session.py`: `get_or_create_chat_session`, `append_chat_message`,
  `get_chat_history` (deep copy), `close_all` clears sessions.
- `validator.py`: warns when `use_chat_session: True` but `session_key` absent.
- Tests: appended to `tests/test_run_session.py` (8 new tests).

**Phase 5 — Parallel-branch vault race warnings**
- `validator.py`: added `_build_reverse_adjacency` and `_build_ancestor_set`
  (backward BFS). When all writers of a vault key are on parallel branches
  (none is an ancestor of the reader), emits a warning — not an error — to
  recommend a Wait Until node.
- Tests: `tests/test_validator_race_warnings.py` (6 tests).

**Phase 6 — Four utility nodes via aotn_node_helper**
- `backend/nodes/data/text_transform_node.py`: uppercase/lowercase/strip/title/reverse.
- `backend/nodes/data/json_path_node.py`: dot-path JSON extraction, `error` port.
- `backend/nodes/data/random_number_node.py`: integer/float in range, optional seed.
- `backend/nodes/io/http_request_node.py`: GET/POST via stdlib `urllib`, `error` port.
- Spec YAML files added to `aotn_node_helper/specs/`.
- `node_identity.py` extended with entries for all four nodes.
- Tests: `tests/generated/` (4 generated suites, mocked network for HTTP node).

---

## 2026-06-12 — Taxonomy Revision Implementation: Selector Restructure, Group Picker, Metadata

Code session implementing the taxonomy revision documented below.

- `Node` base: new frontend-only ClassVars `group: Optional[str]` and
  `selector_section: Optional[str]`; `NodeFactory.get_node_types_metadata()`
  exposes both (None when unset).
- `node_identity.py`: five-family remap. Debug/data nodes moved to the new
  `Utility` family (Transform / Debug / Loop Helpers sections); Flow Control
  entries gained Branch/Merge/Wait-Timer groups under Branching/Timing
  sections; I/O-side and Complex entries gained their groups and sections per
  `NODE_CATALOG.md`. `FAMILY_COLOR_HINTS` gained `Utility: grey`.
- `node_card.py`: `Utility` family frame (`|`/`|`) and row background
  (the existing quiet `#9aa7b3`).
- `NodeSelectorScreen` restructured to the four-tab design:
  - Tabs `I/O`, `Flow Control`, `Utility`, `Complex`; the I/O tab has a
    Textual `Switch` row (Input/Output) above the filter that selects which
    family fills the list. Filters checked on one side no longer constrain
    the other side.
  - Filter checkboxes reduced to I/O (`File I/O`/`Internet`/`AI`) and
    Complex (`AI`); shown only when the active side actually has the tag.
  - The list renders three entry kinds: non-selectable section headers
    (skipped by W/S navigation, hidden while searching), single-line group
    entries with member counts, and two-line node rows. Single-member groups
    auto-promote to direct node rows.
  - `start_node` and `end_node` are hidden from the selector alongside
    `tombstone_node`.
  - String search dissolves groups and headers; matching node types render
    directly and the grouped view returns when the filter clears.
- New `frontend/screens/group_picker.py`: generic `GroupPickerScreen` modal
  parameterized by group name and member metadata; one node per line with the
  highlighted member's description below; `E`/Enter dismisses with the chosen
  type (selector then dismisses too), `ESC` pops only the picker.
- `aotn_node_helper/generator.py`: validates the five families, accepts
  `group` / `selector_section` spec fields (requiring a section when a group
  is declared, except on the flat Outputs side), and emits both as class
  metadata on generated nodes.
- `styles.tcss`: `#io-direction-row`, `.node-select-header`,
  `.node-select-group`, and group-picker styles.
- Tests: rewrote the selector taxonomy test for the new structure; added
  `test_node_selector_group_picker_flow` (open picker, ESC back, choose
  member closes both) and
  `test_node_selector_navigation_skips_section_headers`; updated the layout
  test for the switch row and family expectations in editor identity tests.
- Verification:
  - `python3 -m compileall -q . ../aotn_node_helper`
  - `python3 -m pytest tests/ -q` (147 passed; 1 pre-existing
    environment-only failure: generated example UI smoke test requires
    pytest-asyncio, absent in this container)
  - `../aotn_node_helper/check_ui.py echo_node` OK
- Remaining before Phase 17 close: live-TUI manual verification of the new
  selector and editor rows at several terminal widths.

## 2026-06-12 — Taxonomy Revision: Five Families, I/O Switch, Section Headers, Node Catalog

Design + documentation session (code implemented the same day — see the
entry above).

- Revised the Phase 17 taxonomy to five backend families — `Inputs`,
  `Outputs`, `Flow Control`, `Utility`, `Complex` — mapped onto four selector
  tabs. `Inputs`/`Outputs` share one `I/O` tab behind a Textual `Switch`
  (Input on one side, Output on the other) above the list; the switch is
  frontend-only presentation, so backend family metadata stays semantic.
- `Utility` is the new action-node family: UI Automation group (click, type,
  key press; screen-read variants deferred), Script Runner group (deferred,
  security gated — hidden from list and search until an explicit "allow
  script execution" setting is on), Data Transform group (set/get variable,
  concat, text ops, JSON, math, format text), Debug direct-adds (echo, probe,
  logger, sleep), and Loop Helper direct-adds (counter, accumulator, repeat
  limiter).
- AI became a subcategory tag, not a family. AI-flavored variants live in
  their natural groups (AI Conditional Branch under Flow Control → Branch,
  AI-Guided Read under File Reader); dedicated AI tools stay in Complex →
  AI Processing where the `AI` filter surfaces them.
- Filter checkboxes reduced to two tabs: I/O (`File I/O`/`Internet`/`AI`)
  and Complex (`AI`). Groups and in-list section headers do the organizing
  elsewhere. Headers are non-selectable rows keyboard navigation skips,
  hidden while a string filter is active or when empty.
- Removed Start/End from the user-facing taxonomy: Start is auto-generated;
  branches end through outputs (new standard "Terminate branch after
  completion" config option in `NODE_STANDARDS.md`), through merges, or
  through a new silent **End Branch** direct-add node in Flow Control.
- Designed the **AI Input** node (I/O Input side): seeds a chat session under
  a vault session key before the response is needed; default dead-drop
  passthrough with optional "Output AI response"; prompt can be customized
  mid-workflow before being passed in. Pattern documented in
  `NODE_STANDARDS.md`.
- Documented the AI model approach: capability-based AI nodes with curated
  supported-model lists (strictest for structured-output nodes such as AI
  Conditional Branch); a future fork point to per-model groups if supported
  models diverge.
- Added `selector_section: str | None` to the metadata direction alongside
  `group` — both frontend-only, exposed through `NodeFactory`.
- Created `NODE_CATALOG.md`: complete node inventory (Live / Planned /
  Deferred / Concept) with mappings from currently registered types, so no
  node idea is lost while non-critical nodes are deferred.
- Updated: `PHASE_17_NODE_VISUAL_IDENTITY.md` (rewritten for the revision),
  `NODE_STANDARDS.md` (terminate-branch standard, AI Input pattern),
  `NODE_HELPER.md` (five families, `group`/`selector_section` spec fields),
  `MASTER_BUILD_PLAN.md` (Phase 17 remaining work), `AGENT_HANDOFF.md`
  (direction summary), `README.md` (catalog directory row + task table).
- Verification:
  - `git diff --check`
  - `python3 -m pytest tests/ -q` (145 passed + 1 pre-existing generated-node
    flake, unchanged from before the docs edit)

## 2026-06-12 — Docs: README Document Directory Overhaul

- Rewrote `README.md` to give every document a clear "what it contains" and
  "when to open it" entry in a structured Document Directory table. Replaced
  the previous flat Read-First / Reference lists (which had overlapping entries
  and imprecise descriptions) with four organized sections: Roadmap and Session
  State, Node Authoring, Architecture and Boundaries, Frontend Reference, and
  Planning and Backlog.
- Archive section now explains when to open each archived file rather than just
  listing them.
- Documentation Rules in README now includes "add a row to the Document
  Directory when a new active doc is created."
- Added orienting intro to `TASK_INDEX.md` clarifying its role relative to
  README (README routes; TASK_INDEX gives the minimum reading set, likely files,
  and focused test commands).

## 2026-06-12 — Node Taxonomy: Core Simplification Rule, Full Expanded Taxonomy, Group Picker Design

- Documented the Core Simplification Rule for deciding node placement: variants
  with different port shapes → separate types; same ports + very different config
  → group with picker; minor config differences, same ports → one node + mode
  select; unique standalone node → direct-add. Rule is in both
  `PHASE_17_NODE_VISUAL_IDENTITY.md` and `NODE_STANDARDS.md`.
- Added Full Expanded Taxonomy to `PHASE_17_NODE_VISUAL_IDENTITY.md`:
  - INPUTS: Text Input group, File Reader group, Data Source group, Trigger group
    (with architecture note: triggers need a persistent listener process outside
    the supervisor model; config-only for now).
  - FLOW CONTROL: Branch group (separate types because port shapes differ),
    Merge group, Wait/Timer group, Loop Utility group, Merge Beacon (direct-add),
    Start/End (direct-add).
  - OUTPUTS: Text Output group, File Write group (File Write is one node with
    mode select — not separate Overwrite/Append types), Send/Notify group,
    User-Facing Prompt group.
  - COMPLEX: AI Processing group, Subworkflow group (reserved, phases 19/20),
    Data Transform group, Script Runner group (deferred; security gate required).
- Documented two-level group picker design in `PHASE_17_NODE_VISUAL_IDENTITY.md`:
  - Main selector shows group entries with member counts; counts reflect active
    subcategory filters; groups with filtered count 0 are hidden.
  - Group Picker second modal: generic/reusable, `ESC` returns to main selector,
    `E` adds and closes both modals, no filter input in the picker.
  - Auto-promotion: single-member groups become direct-add entries, no picker.
  - Search behavior: string filter dissolves groups; individual node types appear
    directly; groups re-form when filter is cleared.
- Added Keyboard Flows section: group-add flow, direct-add flow, search-first flow.
- Added Problems and Solutions Summary table.
- Added What Doesn't Need to Exist section.
- Added `group: str | None` metadata field design to Metadata Direction.
- Updated Completion Shape to include group picker criteria.
- Added "Design Or Update Node Taxonomy" task route to `TASK_INDEX.md`.
- Added taxonomy task row to `README.md` Choose Your Task table.
- Updated `MASTER_BUILD_PLAN.md` Phase 17 Done and Remaining sections.

## 2026-06-12 — Node Helper: Dynamic Forms, Standard Model Expansion, Config-UI Checks

- Implemented the dynamic-form schema keys planned in the Helper-Backed UI
  Standardization backlog:
  - `enabled_when`: field greys out unless a condition on other field values
    holds (mapping of field name to expected value; AND across entries, list
    values match any).
  - `visible_when`: hides the field, its label, and its description unless the
    condition holds.
  - `mutually_exclusive_with`: checking one boolean unchecks its declared
    partners; declarations are symmetric.
  - Implemented in `frontend/widgets/form_generator.py`
    (`evaluate_field_condition`, `apply_field_rules`,
    `mutual_exclusion_targets`, `schema_has_field_rules`); generated field
    labels/descriptions now carry `field-label-<name>` / `field-desc-<name>`
    ids so visibility rules can hide the whole block.
  - `NodeConfigScreen` applies rules at mount and on every generated-field
    change. Rules work across tabs: a Source tab selector can grey out a
    Parameters tab field, matching the NODE_STANDARDS greying behavior.
- Expanded `aotn_node_helper` with standard-model spec sections:
  - `input_sources`: expands each input into a `<name>_source` selector
    (Upstream payload / Vault / Configured), a gated `<name>_vault_key` field,
    and a gated Configured parameter field in the Parameters tab.
  - `output_routing`: expands into the mutually exclusive
    `transient_output` / `dead_drop_passthrough` pair plus optional
    `vault_write` / `vault_write_key` fields. Vault modes: `optional`,
    `default_on`, and `required_unless_transient` (locked on until transient
    output is checked — the Basic LLM node pattern).
  - Spec-time validation for rule keys: referenced fields must exist,
    mutual-exclusion participants must be booleans, standard fields must not
    collide with hand-written ones.
- Added `aotn_node_helper/check_ui.py <node_type>` and shared
  `aotn_node_helper/ui_checks.py`: mounts `NodeConfigScreen` and verifies
  every schema field renders, lands in its declared tab, participates in
  keyboard focus, and has correct rule state at mount. Structural nodes
  (branch/merge/branch-end) are rejected with a clear message.
- `create_node.py` now also emits `tests/generated/test_<node_type>_ui.py`
  (config-UI smoke test backed by `ui_checks`) when a spec uses `config_tabs`,
  `input_sources`, or `output_routing`.
- Added `aotn_node_helper/specs/example_file_instance_node.yaml` — the
  NODE_STANDARDS File Instance reference example expressed as a helper spec.
  Verified end-to-end: generated, check_node + check_ui + generated UI test
  all green. The generated node is REGISTERED in the project
  (`backend/nodes/io/example_file_instance_node.py`) for a live TUI pass of
  the dynamic config forms; remove it after the UI review if not kept.
- Registering the node surfaced a helper gap: generated nodes lacked Phase 17
  identity metadata, failing `test_node_factory_exposes_phase_17_identity_metadata`.
  Helper specs now require `primary_family` (Inputs / Flow Control / Outputs /
  Complex) and accept optional `tags` (validated against the Phase 17
  subcategory taxonomy), `icon_name`, and `color_hint` (defaults from the
  family color map). Generated nodes emit these as class metadata directly —
  no entry in the transitional `node_identity.py` table needed.
- Updated the node selector taxonomy test to include the registered example
  node in the Inputs family and File I/O filter expectations.
- Tests: new `tests/test_form_rules.py` (rule helpers + mounted
  NodeConfigScreen integration covering greying, visibility, and mutual
  exclusion both directions); extended `tests/test_node_helper.py` with
  standard-model expansion and validation cases. 11 focused tests pass.
- Known pre-existing flake (not from this change):
  `test_file_picker_export_and_import_paths` fails in a full-suite run but
  passes in isolation; reproduced identically on the clean tree.
- Docs updated: NODE_HELPER.md (standard sections, rule keys, check_ui,
  limitations/direction refresh), AGENT_START_GUIDE.md, NODE_STANDARDS.md
  (helper support note), PROJECT_BACKLOG.md (marked done items),
  PROJECT_KNOWLEDGE.md (form generator capabilities), FILE_TREE.md.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_node_helper.py tests/test_form_rules.py -v`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py` (121 passed +
    1 pre-existing flake)
  - `../.venv/bin/python -m compileall -q . ../aotn_node_helper`
  - `../aotn_node_helper/check_ui.py echo_node` / `logger_node` OK;
    `branch_node` correctly rejected as structural.

## 2026-06-11 — Node Standards Corrections: MemoryBank Model, Mutual Exclusion, JSON Payloads

- Corrected NODE_STANDARDS.md and PROJECT_KNOWLEDGE.md on three points:
  1. MemoryBank is always the underlying store for both transient and vault
     data. Transient uses ephemeral `(source_node_id, port_name)` keys; vault
     uses stable user-defined keys. The distinction is addressing scope, not
     separate storage systems.
  2. Transient output and vault write are not mutually exclusive. A node can
     write the same result to both simultaneously. The only mutual exclusion is
     "send my result as transient" vs "forward incoming transient unchanged
     (dead-drop passthrough)" — only one can occupy the transient port.
  3. Transient payloads are JSON and can carry any serializable value including
     large strings and LLM responses. The constraint is scope (path-scoped,
     not cross-branch), not size. Mentioned incremental document modification
     as a valid transient use case for LLM output.
- Clarified that active file I/O sessions are managed by the backend RunSession;
  files can serve as both inputs and outputs.
- Added "Later Project — Backend LLM Chat Session Persistence" to
  PROJECT_BACKLOG.md: session handles in RunSession, opt-in via session_key,
  shared history across nodes with the same key, validator warning if session
  not available.
- Updated docs: NODE_STANDARDS.md (input model note, output model mutual
  exclusion, data type scope, payloads tab diagram, LLM example notes,
  authoring checklist), PROJECT_KNOWLEDGE.md (Data Flow Patterns rewrite),
  PROJECT_BACKLOG.md (new LLM chat session backlog entry).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Node Design Standards Document

- Created `NODE_STANDARDS.md` as the authoritative reference for node I/O
  design before authoring any new node type.
- Documents the standard input source model: three mutually exclusive options
  per input (Upstream/transient, Vault, Configured). Selecting one greys out
  the other two in the form. Configured activates the matching Parameters tab
  field; Upstream or Vault selection greys that field out.
- Documents the standard output routing model: Transient output (send result
  downstream), Dead-drop passthrough (forward incoming payload unchanged,
  default for most nodes), and Vault write (save result under a named key,
  independent of transient/dead-drop choice). Transient and dead-drop are
  mutually exclusive per port; Vault write is independent.
- Documents data type scope: transient payloads carry only lightweight
  conditional data (bools, counters, flags); large strings, document text, and
  AI responses travel through the Vault or file I/O.
- Documents the standard Source / Parameters / Payloads / Connections tab
  structure with UI behavior rules for conditional field greying.
- Includes two reference examples:
  - File instance node: file path from upstream/vault/configured (mutually
    exclusive); bool transient output (success/failure); optional Vault write
    for error messages.
  - Basic LLM node: prompt from upstream/vault/configured (mutually exclusive);
    document/context from upstream or vault only (no configured option);
    dead-drop passthrough on by default; Vault write on by default and cannot
    be disabled unless transient output is active.
- Includes an authoring checklist: inputs, outputs, conditional fields, data
  types, mutual-exclusion rules, required vs optional Vault writes, and
  expected downstream pattern.
- Wired into `README.md` (task table and Read-First Files), `TASK_INDEX.md`
  (Add Or Change A Node route), and `AGENT_START_GUIDE.md` (Add A New Node
  section).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Tombstone Delete Semantics And Payload Design Context

- Clarified that node deletion is always single-node and non-cascading.
  Downstream nodes are never automatically deleted or modified. The tombstone
  sits in place as a swap-out and insert-staging placeholder; the graph beyond
  it remains intact. This is an editor-adapter invariant.
- Documented the transient payload vs vault (MemoryBank) design intent:
  transient payloads are primarily for conditional logic (booleans, counters,
  branch-decision flags); large strings, file contents, and shared data travel
  through the vault or file I/O. Many nodes consume from the vault directly and
  do not depend on the immediately upstream node's transient output.
- Added dead-drop context: the dead-drop option lets a node write a small
  conditional payload that a downstream node picks up without requiring a live
  transient connection through every intermediate node.
- Added restore severity context: because most data travels through the vault,
  tombstone restore-validation failures on transient ports are usually minor
  repairs, not broken workflows. The frontend alert should be informative but
  not alarming.
- Updated `PROJECT_KNOWLEDGE.md` (new "Data Flow Patterns" section, corrected
  Open Cleanup Areas entry) and `BACKEND_FRONTEND_BOUNDARY.md` (single-node
  delete rule and restore severity context added before the restore procedure).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Tombstone Restore Edge Cases And Connection Validation

- Specified tombstone restore validation rules for three categories of workflow
  drift that can occur between a node being deleted and a user triggering restore:
  (1) upstream output drift — source node removed or output port renamed/removed;
  (2) downstream input drift — target node removed, input port renamed/removed,
  or port now occupied by a different source; (3) memory bank drift — membank
  variables the deleted node depended on (`membank_inputs`) may no longer be
  declared by any surviving node.
- Restore procedure: always restore node type, alias, and config (never blocked).
  Validate each stored input connection and output connection before re-wiring.
  Leave failed connections unconnected. Surface a frontend alert after restore
  with named sections for input connection errors, output connection errors, and
  memory input warnings — each naming the original peer node alias, port, and
  failure reason. A partial restore is always preferred over leaving a tombstone.
- Edge case called out: branch-start nodes are particularly sensitive because the
  upstream branch node holds the dead-drop payload that seeds the branch. If the
  branch node's output port was renamed or its payload type changed since the
  delete, the connection will fail validation and the branch effectively remains
  broken until the user rewires it — the alert makes this visible.
- Updated `BACKEND_FRONTEND_BOUNDARY.md` (added "Tombstone restore — connection
  validation and partial restore" subsection) and `PROJECT_BACKLOG.md` (added
  restore validation spec to Phase B work items).
- No code changes — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Tombstone Design Decision: Backend Type Stays

- Reviewed the Phase B tombstone decommission plan and decided to reverse it.
  `tombstone_node` will remain an intentional registered backend type, not a
  cleanup target.
- **What we had:** Phase A (done) moved frontend deletes to a visual-overlay
  model where saves materialized deleted nodes into `branch_end_node` records
  with a `_system_role: "deleted_node_branch_end"` marker. This worked with
  zero backend changes but had a key limitation: it is session-scoped. Saving
  after a delete, closing, and reopening loses undo context. The
  `branch_end_node` port shape also limits how much original connection data
  the validator can surface.
- **Why we switched:** The save file is the only persistence layer. Keeping
  full original node data (type, alias, config, input connections, output
  connections) in a `tombstone_node` record gives: (1) undo that survives
  save/reload, (2) validator errors that name the original node and describe
  its original connections as a repair guide, (3) meaningful port-validity
  errors from the stored original port shape.
- **New contract:** tombstone config stores `original_type`, `original_alias`,
  `original_config`, `original_inputs`, `original_outputs`. The validator
  tombstone error block should be extended to surface the original connection
  context. The node selector already excludes tombstone. Execution is already
  blocked on workflows containing tombstones.
- **Phase B redefined:** instead of decommissioning tombstone, Phase B now
  updates `editor_workflow_adapter.py` to write `tombstone_node` on save
  (not `branch_end_node`), migrates existing `_system_role` marked records on
  load, extends the validator error block, and confirms `editor_only` flagging
  in `node_identity.py`.
- Updated docs: `BACKEND_FRONTEND_BOUNDARY.md` (major rewrite of Phase B and
  Deleted-Node Save Contract sections), `PROJECT_BACKLOG.md` (Phase B
  redefined), `MASTER_BUILD_PLAN.md` (added Phase 10.6), `ARCHITECTURE.md`
  (tombstone table row and description), `AGENTS.md` (tombstone footnote).
- No code changes in this session — documentation only.
- Verification:
  - `git diff --check`

## 2026-06-11 — Typed Vault Entries and AI Session Architecture

Architecture design session only. No runtime, frontend, or test changes.

- **Typed vault entries.** Decided that `MemoryBank` vault entries will carry
  a `type` field alongside their value. Types: `string`, `number`, `boolean`,
  `file`, `ai_session`. Simple types remain pure JSON. `file` and `ai_session`
  entries store a type tag and a string reference key; the actual Python handle
  lives in `RunSession` and is retrieved via `context.run_session.get_resource
  (ref_key)`.
- **RunSession as handle owner.** File handles and AI session objects are not
  JSON-serializable and must live in `RunSession`, not `MemoryBank`. `RunSession`
  already exists; the only addition needed is `get_resource(key)` to complement
  `register_resource(key, handle)`.
- **AI session as config-driven LLM node output.** No separate Chat Session
  Node. Any LLM node can opt into session persistence via a "keep active AI
  session" checkbox and a user-supplied session key. The first node with a given
  key starts the session and writes `(type: ai_session, ref_key)` to the vault;
  downstream nodes that select the same vault key continue the session. Message
  history stays in the session object in `RunSession`.
- **Input dropdown type filtering.** Config dropdowns that select a vault source
  filter by declared input type. Only `file` entries appear for file inputs;
  only `ai_session` entries appear for LLM continuation inputs.
- **Validator error/warning split for vault key ordering.** Error when no node
  in the workflow declares the key at all. Warning when the key is declared on
  a parallel branch with unguaranteed execution order. The validator must not
  infer timing from node count, type, or branch depth. Applies uniformly across
  all vault types.
- **Docs updated:** `PROJECT_BACKLOG.md` (new Near-Term section, extended
  RunSession remaining notes), `PROJECT_KNOWLEDGE.md` (RunSession backend
  component entry, new Data Flow Patterns section), `NODE_STANDARDS.md`
  (created; typed vault outputs, AI session config-driven pattern, validator
  rules), `MASTER_BUILD_PLAN.md` (new Later Roadmap bullet), `ARCHITECTURE.md`
  (RunSession subsection).

## 2026-06-10 — Two-Line Selector Rows, Editor Selector Spacing

- Node selector rows are now two lines: line one is the display name plus the
  subcategories in parentheses (the family is omitted as redundant with the
  active tab), line two is the node description indented four spaces (truncated
  past 76 chars) for clear visual separation between nodes. Added
  `_node_row_text`, a `.node-select-row` height-2 style, and
  `#node-type-list ListItem { height: auto }`.
- Editor: removed the blank line below branch/merge selector rows. The
  trailing spacer (`node-row-spaced`) now only applies to node rows that are
  not immediately followed by a selector; selector rows never add a blank
  line below themselves. The next node hugs the selector.
- Tests: added
  `test_node_selector_rows_are_two_lines_with_indented_description`; extended
  `test_editor_identity_rows_fit_rendered_panel_width` with a node after the
  branch selector to assert no blank line below the selector.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/ -v` (134 passed)
  - `git diff --check`

## 2026-06-10 — Node Selector/Config Layout And Navigation Audit

Focused pass on the Node Selector and Node Config modals.

- Selector headspace: `Horizontal`/`Vertical` containers default to
  `height: 1fr`, so `#node-family-tabs` and `#node-subcategory-filters`
  stretched and left dead space between the tab row and filter bar, and the
  stretch clipped the last subcategory checkbox on short terminals. Added
  explicit `height: auto` for the tab row, filter, and subcategory block, and
  `height: 1fr; min-height: 4` for `#node-type-list` so the node list absorbs
  the remaining space and every checkbox renders fully.
- Config phantom-focus / "two presses, highlight vanished": the hidden payload
  preview widgets (collapsed `PayloadPreview`s with their own
  `display: false`) were still keyboard-focus stops because
  `_keyboard_focus_widgets` only checked ancestor visibility, not the widget's
  own display. Focusing a hidden widget shows no cursor, so it read as a lost
  highlight needing a second key press. Now skips widgets whose own
  `display` is False; revealed previews remain real stops.
- Selector list highlight: re-entering the node list with an unchanged index
  left no visible cursor because `ListView.watch_index` only fires on a
  changed value. `focus_list` now re-asserts the highlight (None then index)
  so stepping down from the last subcategory checkbox lands on the first node
  with a visible highlight.
- Tests: added `test_node_config_keyboard_skips_hidden_payload_previews`,
  `test_node_selector_layout_is_compact_and_checkboxes_fit` (asserts no
  tabs->filter gap and no clipped checkboxes at 30- and 22-row terminals), and
  `test_node_selector_down_from_last_checkbox_highlights_first_node`.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/ -v` (133 passed)
  - `git diff --check`

## 2026-06-10 — Blank Editor Fix, Selector Row Placement, No-Alias Rows

- Fixed the blank editor: the family-background change defined
  `NodeCard._render_content`, which silently shadowed Textual's internal
  `Widget._render_content` paint method (textual/widget.py), making every
  card render blank while still holding correct content. Renamed to
  `_card_content` with a warning comment. The regression test now asserts
  actual painted output via `render_line`, not just stored content —
  content-only assertions completely missed this bug.
- Branch selector and merge-beacon jump rows now sit directly below their
  node: `NodeList.refresh_rows` places the spacer line after each node's
  full row group (after the node row, or after its trailing selector rows)
  instead of unconditionally after every node row.
- Selector rows gained two leading spaces so their label column lines up
  with the framed node text above; updated the editor-depth test's pinned
  selector string.
- Identity rows with an empty alias now render `No alias` on the first
  line instead of falling back to the raw node type string (Merge Beacon
  and legacy tombstone naming keep their special-cased names).
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows or node_card or branch_end or deleted"` (3 passed in slice)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Identity Row Family Backgrounds

- Editor node rows now fill the framed segment (between and including the
  brackets) with the family color previously used for the font, and flip
  the segment font to dark high-contrast `#0d1117`:
  Inputs `#7ee787`, Flow Control `#8ab4f8`, Outputs `#f2cc60`,
  Complex `#c586c0`, Utility-tagged rows `#9aa7b3`.
- The gutter (depth number) stays unstyled, so the depth column and the
  right inset still show selection highlight. Merge Beacon health rows and
  deleted-node rows keep their existing color priority and get no family
  background.
- Styled rendering only applies to mounted cards; unmounted cards (unit
  tests) fall back to plain text because Rich content requires the app
  console.
- Extended the identity-row regression test to assert the framed spans
  carry the family background and dark foreground while gutter columns
  stay unstyled.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows or node_card or branch_end or deleted"` (3 passed in slice)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Identity Row Polish: Right Inset And Row Spacing

- Closing frames now sit `FRAME_RIGHT_INSET` (2) columns in from the right
  edge of the node-list panel instead of touching it.
- Editor node rows get one blank spacer line below them: `NodeList`
  tags node-row `ListItem`s with `node-row-spaced` (margin-bottom in
  `styles.tcss`). Branch select and merge beacon rows keep their
  single-line height with no spacer. The margin lives on the `ListItem`
  because item auto-height clips a child card's own margin.
- `NodeCard.on_mount` re-fits once after first layout via
  `call_after_refresh`, fixing rows that rendered at the unmounted
  fallback width inside `ListView`s when no Resize event fired.
- Extended `test_editor_identity_rows_fit_rendered_panel_width` to run the
  real `NodeList.refresh_rows` path with the real `styles.tcss`, asserting
  the right inset, the one-line spacer between node rows, and the
  unspaced single-line branch selector row.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows"` (3 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Phase 17 Reopened: Identity Row Width Fix

- Live-TUI verification showed Phase 17 editor rows were broken in real
  panels: identity rows padded text to a fixed 48-char width, so the
  node-list panel (narrower than ~58 columns with gutter and frames)
  soft-wrapped each row — the closing frame landed alone at column 0 of the
  next visual line and the family/subcategory identity line was pushed out
  of the two-line row entirely.
- Fixed `NodeCard` to fit framed text to the rendered card width:
  `_identity_text_width()` derives the text column from `content_size`
  (fallback to the old fixed width for unmounted cards), `_fit_text` takes
  the width as a parameter, and `on_resize` re-renders rows so frames track
  panel-width changes. Applies to identity rows and deleted-overlay rows.
- Added `test_editor_identity_rows_fit_rendered_panel_width`: mounts a
  `NodeCard` in a 40-column panel and asserts two lines, no line wider than
  the panel, aligned closing frames, and a visible family identity line.
- Reverted the premature Phase 17 completion claims in
  `MASTER_BUILD_PLAN.md`: phase status back to In progress with a
  live-TUI verification todo (manual editor check at several terminal
  widths) before the phase can close.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -k "identity_rows or node_card or editor_depth or deleted"` (3 passed in slice)
  - `../.venv/bin/python -m pytest tests/ -v` (130 passed)
  - `git diff --check`

## 2026-06-10 — Working-Tree Port From OneDrive Checkout

- Discovered that this date's agent sessions had been editing a second
  checkout of the repo under OneDrive
  (`C:\users\makin\onedrive\documents\node_workflow`) instead of the
  WSL-local tree. Both trees shared the same HEAD commit.
- Ported all session source changes (backend RunSession + validation,
  Phase 17 frontend identity/selector/deleted-node work, tests, and docs)
  from the OneDrive working tree into this tree.
- Hand-merged the five docs that had independent local changes
  (`FILE_TREE.md`, `PROJECT_BACKLOG.md`, `README.md`, `SESSION_LOG.md`,
  `TASK_INDEX.md`) so the local `NODE_HELPER.md` documentation work and
  the ported entries both survive. Local `.gitignore` and `NODE_HELPER.md`
  were kept as-is. Runtime artifacts (`run_errors/`, `run_history/`,
  `run_outputs/`) were not ported.
- Pre-merge copies of the locally dirty files are saved at
  `~/src/node_workflow_port_backup/`.
- Verification (run from this tree):
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/ -v`
  - `git diff --check`

## 2026-06-10 — Frontend Deleted-Node Model

- Reworked editor delete behavior so a normal delete is visual-only: the
  original node stays in `WorkflowMap` while the editor stores deleted-row
  overlay state keyed by node id.
- Added deleted-row rendering in the Phase 17 two-line bracket style, with
  restore-aware controls (`x delete | z undo | e new node`) and a no-restore
  variant that hides `z undo`.
- Added editor actions for deleted rows: `z` undo restores the visual original,
  `e`/Enter opens replacement through the node selector, and a second `x`
  permanently removes the node and prunes merge-beacon config when needed.
- Before save/validate/run, soft-deleted rows materialize to `branch_end_node`
  with `_system_role: "deleted_node_branch_end"` and nested `deleted_node`
  restore metadata; materialization drops outgoing connections so execution
  stops safely at the placeholder.
- Saved/loaded marked branch-end placeholders render as friendly deleted rows,
  and original connections/config can be restored when restore data exists.
- Refreshed `BACKEND_FRONTEND_BOUNDARY.md` and `PROJECT_BACKLOG.md` to note
  that new deletes no longer write `tombstone_node`; legacy registration remains
  a future old-save compatibility cleanup.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "deleting_merge_beacon_prunes or deleted or tombstone or node_card or editor_depth or node_selector"` (11 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (129 passed)
  - `git diff --check`

## 2026-06-10 — Deleted-Node Save Contract Audit (no code changes)

- Audited whether the visual-deleted-node model (frontend-only delete while
  editing; save materializes deleted rows into `branch_end_node` with a
  `_system_role: "deleted_node_branch_end"` + `deleted_node` config marker)
  works against today's backend. Result: yes, with zero backend changes.
- Wrote the contract into `BACKEND_FRONTEND_BOUNDARY.md` ("Deleted-Node
  Save Contract"). Key findings:
  - SaveManager save/export/duplicate and WorkflowMap load/save preserve
    arbitrary JSON-serializable node config unchanged; import rewrites only
    id/name.
  - The marker must live in node config: top-level save keys are dropped by
    `WorkflowMap.save`/`get_workflow_data_for_save()`.
  - The validator ignores extra config keys, but original
    `membank_inputs`/`membank_outputs` must be nested inside `deleted_node`
    or they will be validated at top level.
  - Execution stops cleanly at a materialized beacon with no outgoing
    connection (supervisor advances to `None`; merge groups discard
    terminated branches). Materialization must drop outgoing connections or
    execution silently continues downstream.
  - Port-shape caveat: `branch_end_node` declares only `input`/`default`;
    surviving connections on other port names produce blocking
    port-validity errors.
  - Optional future hardening: ~8-line validator warning for marked nodes.
- Verification:
  - `git diff --check`

## 2026-06-10 — Phase 17 Tombstone Selector Follow-Up

- Hid editor-only `tombstone_node` metadata from `NodeSelectorScreen` so users
  cannot add a "Deleted Node" placeholder while backend tombstone
  decommission remains gated.
- Kept the filter frontend-owned: `NodeFactory` may still expose transitional
  tombstone metadata because the editor adapter still needs the registered
  type until Phase B cleanup.
- Extended selector coverage to assert `tombstone_node` is absent from the
  selector source set and from search results.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector"` (1 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"` (8 passed)
  - `git diff --check`

## 2026-06-10 — Tombstone Boundary Audit Refresh (planning only)

- Audited the actual tombstone footprint against
  `BACKEND_FRONTEND_BOUNDARY.md` and found the doc stale: Phase A is done.
  `frontend/editor_workflow_adapter.py` owns placeholder create/remove/
  replace, and `replace_with_tombstone()`, tombstone-specific
  `replace_node_type()`, and backend-written `_timing_invalidated` are
  already gone from the backend.
- Rewrote the boundary doc's audit and migration plan: Phase A marked done
  with its one transitional dependency (the adapter still writes
  `type: "tombstone_node"`, so backend registration is still required), and
  Phase B reduced to a concrete five-step decommission list covering
  `backend/nodes/debug/tombstone_node.py`, `backend/nodes/__init__.py`,
  the validator's tombstone error block, the `node_identity.py` entry, and
  an old-save loading decision.
- Added an explicit coordination gate: Phase B must not start while Phase 17
  selector/editor work is in flight, because it touches Phase 17 metadata,
  the selector's metadata source, and ~26 tombstone test references.
- Noted the known wart that `tombstone_node` currently appears in node-type
  metadata as an addable "Deleted Node".
- Synced the boundary cleanup section of `PROJECT_BACKLOG.md` to the
  refreshed audit. No code changes.
- Verification:
  - `git diff --check`

## 2026-06-10 — RunSession Edge-Case Audit

- Audited the RunSession integration paths and added focused tests for three
  previously untested load-bearing behaviors in `tests/test_run_session.py`:
  - two file readers of the same path in one run share the cached handle and
    both receive full contents (guards the `seek(0)` re-read behavior);
  - back-to-back runs each get a fresh session with the new run's id, and
    both sessions end up closed;
  - `open_file` transparently replaces a cached handle that was closed
    externally.
- Documented a write-mode caveat in `RUNTIME_RESOURCE_SESSION.md`: a cached
  `"w"` handle only flushes at run end, so a future file writer node should
  flush after writes (or the session should flush before serving a same-path
  read handle).
- No runtime, frontend, or save-format changes.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_run_session.py -v` (10 passed)
  - `git diff --check`

## 2026-06-10 — RunSession Implementation

- Implemented the per-run resource session from
  `archive/plans/RUNTIME_RESOURCE_SESSION.md`:
  - New `backend/run_session.py`: `RunSession` with `open_file` (cached by
    resolved path + mode), `register_resource`/`get_resource` with optional
    close hooks, `validate_path`, and idempotent `close_all`.
  - `MasterState` creates the session in `start_workflow()`, passes it to
    root and branch supervisors, and closes it in `_record_run` so FINISHED,
    supervisor-error, and forced-termination paths all release resources.
  - `Supervisor` accepts `run_session` and passes it into `NodeContext`;
    `NodeContext.run_session` defaults to `None` so existing direct
    constructions keep working.
  - `Validator` gained a file-path pass for schema fields hinted with
    `path_hint: "file"`: empty required path is an error; a path missing on
    disk is a warning (an earlier node may create it during the run).
  - `FileReaderNode` is the first consumer: its `file_path` field carries
    `path_hint: "file"` and it reads through `context.run_session` when
    available.
- No frontend, persistence, or save-format changes. Workflow saves still
  store plain path strings.
- Updated `RUNTIME_RESOURCE_SESSION.md` status/implemented-files and the
  backlog entry.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_run_session.py -v` (7 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (121 passed)
  - `git diff --check`

## 2026-06-10 — Phase 17 Editor Row Identity

- Implemented editor row visual identity for normal node rows:
  - Editor rows now opt into two-line `NodeCard` rendering with fixed
    left/right frame columns.
  - The first line keeps the editable alias as the primary text.
  - The second line shows primary family plus one or two high-signal
    subcategories, truncating long identity text with an ellipsis.
  - Utility-tagged rows are visually quieter, while Merge Beacon open/connected
    state indicators still take priority over decorative styling.
- The editor attaches frontend-only identity display metadata from
  `NodeFactory.get_node_types_metadata()` to row display copies. Runtime node
  data and backend execution behavior were not changed.
- The right-side details panel now shows full `Family` and `Subcategories`
  lines for the selected node.
- Added focused coverage for:
  - row frame alignment and truncation;
  - full details-panel identity;
  - keyboard selection stability across taller editor rows and backend refresh;
  - existing Merge Beacon health, branch selector rows, and selector behavior.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_card or editor_depth or editor_identity_rows"` (3 passed)
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"` (8 passed)
  - `../.venv/bin/python -m pytest tests/ -v` (126 passed)

## 2026-06-10 — Runtime Resource Session Design Note

- Created `archive/plans/RUNTIME_RESOURCE_SESSION.md`: backend-only design
  plan for a per-run `RunSession` object that holds file handles, streams,
  and future resource types during one workflow execution.
- Design covers: `RunSession` interface, lifecycle owned by `MasterState`
  (create at run start, `close_all()` before finalization), `NodeContext`
  receives session reference, file paths remain portable config strings in
  saves, validation rules for missing/inaccessible paths, why frontend file
  picking stays frontend-owned, and forward-compatibility for streams,
  browser sessions, and listeners.
- Likely new files when implemented: `backend/run_session.py`,
  `tests/test_run_session.py`; modified: `master_state.py`, `supervisor.py`,
  `node_base.py`, `validator.py`. No frontend or persistence changes.
- Updated `PROJECT_BACKLOG.md` "Later Project — Runtime Resources And Hidden
  Helper Nodes" to reference the new design doc and summarize `RunSession`.
- Verification:
  - `git diff --check`

## 2026-06-10 — Phase 17 Direction Alignment

- Added `PHASE_17_NODE_VISUAL_IDENTITY.md` as the active plan for node visual
  identity, selector taxonomy, subcategory filters, and editor row direction.
- Recorded follow-up design decisions: subcategory filters are `AND`
  checkboxes, selector search is activate-to-edit, filter lists differ per tab,
  editor rows should use aligned bracket columns with ellipsis truncation, and
  file access should eventually be owned by a run-scoped resource helper/session
  coordinated by `MasterState`.
- Marked the task-first docs overhaul complete and Phase 17 active in
  `MASTER_BUILD_PLAN.md`.
- Updated the task router, handoff, UI quick reference, TUI design notes,
  project knowledge, backlog, README, and file tree to point at the Phase 17
  taxonomy.
- Captured the metadata gap: `Node` has optional identity fields, but
  `NodeFactory.get_node_types_metadata()` must expose category/tag/icon/color
  metadata before the selector can depend on it.
- Verification:
  - `git diff --check`
  - stale active-status `rg` scan for docs-overhaul-in-progress wording (no
    matches)
  - Phase 17 reference `rg` scan across active docs
  - `find AttackOfTheNodes/docs -type f -name '*.md' | sort`

## 2026-06-10 — Phase 17 Metadata Exposure

- Added transitional Phase 17 identity metadata for the registered node library:
  primary family, subcategory tags, icon name, and color hint.
- `NodeFactory.get_node_types_metadata()` now exposes `category`,
  `primary_family`, `legacy_category`, `tags`, `icon_name`, and `color_hint`
  without changing runtime execution behavior.
- Clarified the current saved `branch_node` as the user-facing **Parallel
  Branch** node: it duplicates incoming payloads across multiple branch paths,
  carries the `Parallel` subcategory, and does not claim the `Conditional`
  subcategory reserved for a later dedicated node.
- Added focused coverage proving the metadata contract for all registered nodes
  plus representative Inputs, Flow Control, Outputs, and Complex nodes.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_factory_exposes_phase_17_identity_metadata or node_selector or node_card or editor_depth or branch_end"`
  - `git diff --check`

## 2026-06-10 — Phase 17 Selector Taxonomy Slice

- Updated `NodeSelectorScreen` to use Phase 17 family tabs: Inputs,
  Flow Control, Outputs, and Complex.
- Added tab-specific subcategory checkbox filters derived from factory metadata.
  Multiple checked subcategories use `AND` semantics.
- Changed selector search to command-mode activation: opening the selector and
  `/` focus the field without auto-editing; `E`/Enter activates text editing.
- Initial selector focus now lands on the first visible subcategory checkbox
  for the active family, falling back to the node list if a family has no
  filters.
- Added focused selector coverage for family switching, tab-specific filter
  visibility, `AND` filtering, string-plus-subcategory filtering, and
  activate-to-edit search behavior.
- Updated `MASTER_BUILD_PLAN.md` with current RunSession state, completed
  Phase 17 selector/metadata work, remaining editor-row/details-panel work, and
  the next focused todo list.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_factory_exposes_phase_17_identity_metadata or branch_config_uses_parallel or branch_node_parallel or branch_node_default_labels"`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"`
  - `../.venv/bin/python -m pytest tests/ -v` (121 passed)
  - `git diff --check`

## 2026-06-10 — Node Helper Documentation And UI Standardization Notes

- Added `NODE_HELPER.md` as the detailed guide for `aotn_node_helper` specs,
  generated files, supported templates, config tabs, structural UI guardrails,
  and current limitations.
- Linked the helper guide from `README.md` and `TASK_INDEX.md` so node work can
  start from the short docs and dive into the helper details only when needed.
- Added a backlog project for helper-backed UI standardization: generated
  config UI checks, keyboard smoke tests, dynamic-section schema support, screen
  scaffolds, and screen/UI manifests.
- Verification:
  - `git diff --check`
  - `rg -n "NODE_HELPER|aotn_node_helper|Pending in this session|docs/README.md|docs/TASK_INDEX.md" AttackOfTheNodes/docs AGENTS.md`
  - `./.venv/bin/python -m pytest AttackOfTheNodes/tests/test_node_helper.py -q`
  - `./.venv/bin/python -m compileall -q AttackOfTheNodes`
  - `./.venv/bin/python -m compileall -q aotn_node_helper`

## 2026-06-09 — Documentation Overhaul

- Rebuilt the docs entry path around task-first reading from `README.md` and
  `TASK_INDEX.md`.
- Collapsed oversized active docs and archived full historical content under
  `docs/archive/`.
- Moved historical proof-of-concept and completed planning docs out of the
  default read path.
- Added `UI_QUICK_REFERENCE.md` as the short current UI/keybinding summary for
  routine frontend work, leaving `TUI_DESIGN.md` as the detailed reference.
- Corrected stale active-doc keybinding references and updated `AGENTS.md` to
  point agents at the task router.
- Added `DOCS_MIGRATION_NOTES.md` to explain moved/collapsed docs and archive
  decisions.
- Verification:
  - `git diff --check`
  - stale-reference `rg` scan from the implementation plan (no matches)
  - active-doc stale keybinding scan for old add/library shortcuts (no matches)
  - `find AttackOfTheNodes/docs -type f -name '*.md' | sort`
  - `wc -l AttackOfTheNodes/docs/*.md AttackOfTheNodes/docs/archive/*.md AttackOfTheNodes/docs/archive/plans/*.md`

## 2026-06-09 — Node Helper Generator And Focused Checks

- Added standalone developer tooling at `../aotn_node_helper/` for generating
  ordinary metadata-driven node files from JSON/YAML specs.
- Helper specs support `config_tabs`, matching the workflow where a node is
  described first and then fields are listed under tab headers such as `Source`,
  `Parameters`, and `Payloads`.
- Generated nodes update backend registration, create a node-specific focused
  test under `tests/generated/`, and can be checked with
  `../aotn_node_helper/check_node.py <node_type>`.
- Node Config honors schema `tab` hints, so generated fields can land in the
  fixed Source / Parameters / Payloads tabs without per-node frontend code.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_node_helper.py -v` (3 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "schema_tab_hints"` (1 passed, 109 deselected)
  - `../.venv/bin/python -m compileall -q .`
  - `./.venv/bin/python -m compileall -q aotn_node_helper`

## 2026-06-09 — Payload Reveal Consistency

- Added opt-in `Reveal upstream payload` controls to the Payloads tab and
  matching `Reveal Vault payload` previews for selected Vault inputs.
- Made revealed payload previews read-only command stops, standardized preview
  copy, and fixed long-tab scrolling back to the tab header.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "payloads_tab_reveals or fixed_tabs_are_keyboard or branch_config_uses_parallel or previous_output_preview or branch_payload_preview or selection_lists_exit"` (8 passed)
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` (109 passed)

## 2026-06-09 — Node Config Copy, Scroll, And Payload Polish

- Polished Branch config copy and command text editing semantics.
- Improved Branch Payloads navigation/scrolling for 4-5 branch rows.
- Made inline selection lists exit at top/bottom with W/S or up/down.
- Branch seed display now treats the selected upstream dead-drop or Vault value
  as the branch port's visible payload.
- Verification:
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "selection_lists_exit or previous_output_preview or quick_view or branch_payload_preview or branch_config_uses_parallel or command_inputs_require_activation or click_edit_and_textarea or editor_ctrl_s"` (13 passed)
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` (108 passed)

## 2026-06-09 — Branch Config Payload Polish

- Shifted `branch_node` to the current Branch v1 UI: always-parallel branching,
  2-5 active spawn points, and per-branch payload seed selection.
- Kept legacy conditional Branch config keys readable/preserved for old saves
  but hidden from the current Branch config UI.
- Verification:
  - `../.venv/bin/python -m compileall -q .`
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "membank_registry or select_activates or previous_output_preview or click_edit_and_textarea or branch_config_uses_parallel or branch_node_parallel"` (7 passed)
  - `../.venv/bin/python -m pytest tests/test_debug_nodes.py -v` (104 passed)

## Older Entries

See `archive/SESSION_LOG_HISTORY.md`.
