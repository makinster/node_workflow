# Configuration UI audit — 2026-10-06

**Integration follow-up (2026-10-06):** File Output is now merged locally with
pending session fixes. Config preservation, critical input sizing, Chat zero
temperature, ambiguous window discovery, launch responsiveness, viewer request
queuing, Window Control's unsupported toggle and writer-path warnings are fixed.
Read [CONFIG_UI_BUILD_PLAN.md](CONFIG_UI_BUILD_PLAN.md) for remaining findings and
[current integrated evidence](audits/integrated_2026_10_06/README.md). Original
findings/counts below describe the earlier inspection, not the latest tree.

Follow-up: [File Output integration review](FILE_OUTPUT_INTEGRATION_REVIEW.md)
examines the unmerged feature against the pending fixes, with 304-test source-overlay
evidence, nine production-CSS mounts and integration findings. The current checkout
audit remains distinct from that prospective 37-type inventory.

Audit and implementation plan only. No application behavior or node layouts were
changed in this audit. The baseline includes the owner's uncommitted Wait Until
and user-input fixes. **Fix capability claims, save preservation and narrow-screen
usability before undertaking a library-wide layout pass.**

Planning update: [PENDING_CHANGES_REVIEW.md](PENDING_CHANGES_REVIEW.md) identifies
unmerged File Output work that adds three node types and Markdown mode while
removing the demo. This audit remains the current-checkout baseline; those
unmerged additions need a coverage extension if selected for the build plan.

## Baseline and evidence

- Authoritative root: `/home/makin/src/node_workflow`; app: `AttackOfTheNodes`.
- Branch: `codex/wait-until-vault-fix`; starting HEAD: `7161ef2`.
- `git fetch origin && git merge origin/main`: succeeded, already up to date.
- Starting dirty state: 18 modified and five untracked files. Preserved the runtime,
  Wait Until, tests, helper and documentation work; no stash/reset/commit.
- Actual environment: `.venv/bin/python` **3.14.4**, Textual **8.2.7**.
- Factory registers **35 types**. Mounted selector exposes **32 addable types**.
  Also mounted Start and legacy End because existing workflows can contain them.
  Tombstone is the sole intentionally unmounted configuration type (see exclusions).
- **34 node configuration screens × 60/100/140 columns × 24 lines** mounted with
  the production `frontend/styles.tcss`. All tabs were visited. At 100 columns,
  **278 alternate control states** were captured: available Select choices and
  checkbox inversions, branch count five and legacy Vault row count two.
- Save/reopen/save was exercised for all 34 types at 60 and 140 columns. All second
  saves were stable after the first save's normalization; this is **not** proof of
  preservation (F02). Cancel after edits was checked for all 34 at 100 columns.
- Synthetic graphs included a connected input, downstream node and a declared
  Vault writer, plus typed string/file/session entries and synthetic secret names.
  Supplemental probes cover populated Merge, five Parallel Branch seeds, direct
  execution discrepancies, invalid numeric saves and focused production-CSS renders.
- No owner workflows, actual credentials, network APIs or real file operations
  were used by the audit probes. Existing test fixtures were also run.

Evidence lives in [audits/node_config_2026_10_06](audits/node_config_2026_10_06/README.md):
[control inventory](audits/node_config_2026_10_06/INVENTORY.md), reproducible scripts,
compressed raw widget/state snapshots, and terminal render receipts. Each widget
inventory includes IDs, types, labels, descriptions, defaults, choices, visibility,
disabled state, preview text and navigation order. Raw evidence preserves all
three widths, alternate states, returned configurations and measured regions.
The inventory complements the concise matrix below; it is part of this audit.

Source references below use app-relative paths and current working-tree line
numbers. They describe this dirty baseline, not an unmodified upstream commit.

## Coverage and proposed layouts

Common current layouts:

- **L**: `1 Source / 2 Parameters / 3 Payloads / 4 Connections` legacy composer.
  Source has alias, type/description, upstream reveal/preview, Vault checkbox and
  selection list (or empty message), Vault reveal/preview. Parameters has the
  fields listed below, or “No parameters.” Payloads repeats upstream/Vault
  reveals, then names/descriptions for every output port. Nodes with zero or one
  output also get Write to Vault, payload count and dynamic key/description rows.
  Connections contains heading, editor instruction and read-only wiring.
- **S**: same four tabs, standard composer. Alias, metadata, automatic connected
  incoming-payload summaries and schema source selectors; generated Parameters;
  downstream names/descriptions, capability-gated forwarding, optional Vault
  disable/key/description controls and payload-specific schema fields; Connections.
- **B**: Parallel Branch's four tabs; alias/summary, reveals and Vault shortlist;
  branch count; repeated per-branch label/seed selectors plus reveals; Connections.
- **W**: Wait / Connections, alias, target list/count/help, timeout/help/error,
  unchanged-payload route and connection summary. No Vault or routing settings.
- **M**: flat Branches To Close list, Carry Forward Output selector and selected
  output details; empty-state explanation if no eligible branches.
- **Beacon**: flat read-only connection/status explanation.
- All have a title including node ID, help, Save, Cancel and status bar. M/Beacon
  still advertise numbered tabs although they have none. Generated labels for
  multi-output nodes are added by the UI, beyond the original schema.

Proposed **compact** means alias + applicable parameter/source/output sections
in a shared flat form, with a compact read-only wiring block. It does not mean a
new bespoke screen. Retain editable output names/descriptions where useful as
editor metadata; they do not rename runtime ports or transform values. “Remove
legacy controls” below means capability-gate unsupported reads/writes/previews,
not silently delete saved keys or add new runtime behavior.

All rows except Tombstone have mounted defaults at all three widths, schema/
default/port/execution inspection, cancel and default save/reopen coverage. The
variant column records additional alternate states; interaction combinations
and limitations are explicitly bounded in the verification section.

| Type / selector location | Current fields beyond common layout; material variants | Execution assessment / recommendation |
|---|---|---|
| `start_node` / hidden, automatic | L; greeting=`Workflow started` | Emits greeting, has no inputs. Compact greeting + output metadata/wiring; remove source/Vault controls. Preserve automatic Start. F01/F02/F05. |
| `end_node` / hidden, legacy | L; message=`Branch completed`; no downstream ports | Logs completion including input. Compact message + wiring for compatibility; no source override or Vault-output UI. Do not offer as a newly addable node. F01/F02/F05; termination standard remains unimplemented elsewhere, D02. |
| `branch_node` / Flow → Branch | B; count 2–5, five labels and seed selectors; selected Vault shortlist unlocks `vault:key` seed options. Count 2 and 5, upstream and Vault seed mounted | Seed selection really reads Vault; preserve it. Propose `Branches / Connections`: count, labels and seeds together; one optional incoming preview. Hide legacy conditional fields deliberately (D01). Do not remove actual Vault seed behavior. F02/F05/F06. |
| `conditional_node` / Flow → Branch | L; condition contains(default)/equals/not_equals/regex, left source input(default)/variable, variable name, right value; generated true/false branch labels | Condition/source choices execute. Variable name irrelevant in input mode: gate it; rename variable to Vault key. Proposed `Condition / Connections`, branch labels/output metadata alongside paths; no generic Vault-source selection or writers. F01/F02/F06. |
| `deep_branch_node` / Flow → Branch | L; no original parameters; generated default/branch labels and two output name/description pairs | Spawns one child and continues on default. Compact fixed behavior + path labels/wiring. No generic Vault reads. Multi-output names are real editor metadata, not additional routing modes. F02/F05. |
| `random_branch_node` / Flow → Branch | L; seed empty=random, generated path_a/path_b labels | Seed controls RNG; same nonempty seed reinitializes on each execution. Compact seed + path labels/wiring; explain deterministic repeats. No Vault overrides. F02/F05. |
| `merge_node` / Flow (single Merge group member promoted) | M; no options / none selected / both selected; carry selector disabled until selected, selected output description | Topology-driven layout is deliberate. Retain flat form and editor wiring callback; improve contextual help and preserve unrelated config. No alias field today; do not invent runtime config for display convenience. F02/F05, D03. |
| `branch_end_node` / Flow direct | Beacon; status-only, open/connected behavior in focused existing tests | Merge Beacon is deliberate topology marker, not End Branch. Keep compact status/actions and accurate help; no generic parameters, reads or writes. F02/F05. |
| `wait_until_node` / Flow (Wait / Timer promoted) | W; targets empty/selected/unavailable and timeout zero/positive/invalid via focused suite | Intentional all-target gate + unchanged incoming dead-drop, no Vault. Retain two tabs and zero=forever explanation; fix shared horizontal overflow affecting timeout at 60 columns. F03. |
| `concat_node` / Utility → Data Transform | L; multiline template=`{input}` | Reads all persistent values and inputs into format map; Vault shortlist does not restrict reads. Compact template, placeholder help and optional input preview, output metadata/wiring. Clarify missing placeholders become empty; no generic writes. F01/F02. |
| `set_variable_node` / Utility → Data Transform | L; variable name=`value`, input/literal, literal value, Dead drop payload=true | Named write really executes; output is input when forwarding, stored value otherwise. Compact Vault key, source choice and conditionally visible literal; label forwarding explicitly. Generic writer controls duplicate a different contract and do not write. F01/F02/F06. |
| `get_variable_node` / Utility → Data Transform | L; variable name=`value`, default empty | Named read executes independently of legacy shortlist. Compact Vault key + fallback + output metadata/wiring; preserve fallback semantics, permit repair of undeclared keys. F01/F02/F06. |
| `variable_setter_node` / Utility → Data Transform | L; variable name empty, value empty=use input, forwarding=true/false | Similar to Set Variable but intentionally distinct literal-empty semantics and blank-name no-op. Keep separate compatible type; compact explicit key/value/fallback explanation. No new grouping/type merge. F01/F02/F06. |
| `variable_reader_node` / Utility → Data Transform | L; variable name empty, default empty | Empty name returns fallback; real named read. Compact Vault key + fallback; preserve difference from Get Variable. F01/F02/F06. |
| `text_transform_node` / Utility → Data Transform | L; uppercase(default), lowercase, strip, title, reverse | All five options execute, fixed string conversion/input. Compact operation and input/output explanation; no configurable Vault routing. Helper spec exists. F01/F02/F05. |
| `json_path_node` / Utility → Data Transform | L; dot path empty, default-on-miss empty; generated default/error branch labels; both output pairs | Extraction and error data ports implemented. Explain blank path=whole value, dot/list indexing and fallback; do not imply generic Vault reads/writes. Compact extraction + optional output/wiring section. Routing/error path behavior is outside layout changes. Helper spec exists. F02/F06. |
| `random_number_node` / Utility → Data Transform | L; integer(default)/float, min=0/max=100, seed empty, **Payload** empty | Mode/range/seed execute; Payload is ignored generator residue. Compact mode/range/seed, explain integer conversion and seed repeatability; remove unsupported Payload field. Helper spec exists. F01/F02/F07/F08. |
| `file_reader_node` / In (File Reader promoted) | L; required file path empty; text input, no browse button | Reads configured file path, not incoming dead-drop or Vault selection. Compact path + file-reading description/output metadata/wiring. Path picker is optional frontend enhancement, not an absent runtime feature. F01/F02/F05. |
| `example_file_instance_node` / In direct | S; Configured/Upstream/Vault path, typed file key, bool Open Result metadata, forwarding, optional Vault output | **Demo stub**, not a file opener. None of those source/routing controls drives execution. Recommend clearly mark/hide from ordinary add flow pending owner decision, retaining registry/save compatibility. Do not implement file resources as a UI fix. F04, D04. |
| `http_request_node` / In (Web Request promoted) | L; URL, GET(default)/POST, body, timeout=10, bearer secret key; generated default/error labels | Request fields execute; body irrelevant for GET. Hide body for GET; clarify timeout 0 currently falls back to 10, not forever. Compact request + optional output/wiring section. No Vault substitution. Helper spec exists. F02/F06/F08. |
| `user_text_input_node` / In (Text Input promoted) | L; prompt=`Enter text:`; generic Vault writer checkbox/count/rows | Prompt and legacy named answer copies are supported by current dirty runtime. Preserve answer-copy controls; remove unsupported reads/duplicate reveals. Propose `Prompt / Payloads / Connections` only if multiple named copies need room, otherwise compact. F02/F05; do not undo prior fix. |
| `text_output_node` / Out (Text Output promoted) | L; label=`Output`, template=`{input}`, request-user-input=false/true, prompt always visible | Logs formatted output, optionally asks user; emits formatted output. Hide prompt unless requested; eliminate unsupported generic Vault writes. Compact output settings or `Output / Connections`. No termination checkbox until an independently approved runtime contract exists. F01/F02/F03/F06, D02. |
| `chat_completion_node` / Complex → AI Processing | S; prompt Upstream/Vault/Configured/Continue session; context count 0–8 and ordered slots, Document sources; model, max_tokens=1024, temperature=1, API secret; forwarding, Vault result, session keep/key | Most capabilities actually execute; retain four tabs for this dense node. Conditional source/session rules and duplicate-source gating are deliberate. Fix save/overflow, explain forwarding's document-then-prompt precedence and absence for context-only input; temperature 0 is silently sent as 1. Vault enabled with blank key writes nothing. Helper spec is contract, executable is hand-written. F02/F03/F08/F09. |
| `embedding_node` / Complex → AI Processing | L; two models, text_field=`input`, optional API secret | Intentionally simulated vector string, not a provider call. Model changes diagnostic text; secret is never read. Compact simulation settings; remove/mark inactive credentials, explicitly identify simulation. No generic Vault controls. F01/F02/F10. |
| `image_generation_node` / Complex → AI Processing | L; prompt=`An image of {input}`, three sizes, natural/vivid, optional API secret | Intentionally returns descriptive simulation text. Prompt/size/style affect it; secret unused. Compact simulation parameters; no real-image or Vault promise. F01/F02/F10. |
| `echo_node` / Utility debug | L; label empty | Actually stringifies input and optionally prefixes label, despite “unchanged” description. Compact label and truthful string-output description. Do not change semantics to fit name. F01/F02/F11. |
| `logger_node` / Utility debug | L; label empty→Logger, include_input=true, timestamp=false (both toggled) | Appends output_log and forwards input. Compact logging fields; explain fixed log destination, no arbitrary Vault writes. F01/F02. |
| `memory_snapshot_node` / Utility debug | L; label empty→Memory Snapshot | Logs persistent-store snapshot and forwards input. Compact label + explicit entire-Vault scope, no selectable subset/write destinations. F01/F02. |
| `probe_node` / Utility debug | L; label empty→Probe | Logs repr/type, forwards input. Compact label + fixed behavior; do not imply arbitrary writes. F01/F02. |
| `no_op_node` / Utility debug | L; empty Parameters | No configuration beyond alias and optional display metadata; fixed pass-through. Flat alias + behavior/wiring. F01/F02/F05. |
| `sleep_node` / Utility debug | L; duration=0.1, schema bounds 0–60; fixed pass-through hint | Sleep then unchanged payload; no Vault. Compact duration with units, 0=no delay, fixed forwarding. Negative saves currently accepted then runtime clamps. F01/F02/F08. |
| `counter_node` / Utility loop helpers | L; counter name=`counter` | Increments named Vault integer, forwards input and emits extra `count` data key not declared as a port. Compact counter key; describe fixed increment. Do not offer generic writer copies. Port-contract gap needs separate decision, F12. F01/F02. |
| `repeat_counter_node` / Utility loop helpers | L; max visits=3 | Errors **on** the configured visit (`>=`), not after it; internal per-node Vault counter, extra undeclared visits data. Compact failure-threshold field and exact description. F01/F02/F11/F12. |
| `error_node` / Utility debug | L; message default deliberate error; fail(default)/warn | Fail signals error; warn emits `[warn] message` as output (does not use runtime warning channel). Compact mode/message, describe distinction. No generic Vault. F01/F02. |
| `tombstone_node` / hidden internal | **No NodeConfigScreen inspection intentionally** | Deleted-node save record; editor restore/replace workflow and validator block are intentional. Preserve original configuration/connections and registration. Not a cleanup target; see boundary contract. |

Actual multi-member groups are **Branch (4)**, **Data Transform (8)** and
**AI Processing (3)**. Every member has its own row above. Single-member groups
auto-promote; no additional hidden execution variants are implied by the picker.
Start/End/Tombstone exclusions come from `node_selector.py:62`; mounted selector
entries are preserved in raw evidence. No `end_branch_node`, File Output, AI Input,
MCP or planned vector node is registered. The unregistered helper
`example_pass_through_node.yaml` is an authoring example, not a missing audit row.

## Findings

### F01 — P1: Legacy Vault controls promise behavior absent from execution

`frontend/screens/node_config.py:682` unconditionally adds legacy reads/previews;
`:2025` permits writers solely when output-port count is <=1; `:2522` composes
Write to Vault/count/rows. `backend/supervisor.py:275` resolves connected transient
ports only; `:450` publishes result data transiently. It does not apply arbitrary
`membank_inputs`/`membank_outputs` declarations.

**Reproduce:** mount No-Op, enable Write to Vault, enter count 2 and keys; Save
stores declarations. Execute with a named declaration: `probes.json/no_op_node`
shows unchanged downstream object and an empty persistent store. This can make a
workflow validator/editor advertise a writer that never produces the key.
Selecting a legacy Vault read does not replace the node's input either.

Affects L screens offering writers except User Text Input. Nodes such as Set
Variable, Counter and Logger do write persistent data, but through their own
keys/contracts, not those arbitrary declarations. Parallel Branch's actual Vault
seed lookup is a supported exception, not a reason to remove it. Concat reads
all Vault data regardless of shortlist. Source/read declarations can have
validation/preview meaning without doing runtime input substitution; labels must
make that distinction, or the irrelevant controls should be absent.

**Fix once:** capability-based composition independent of port count and independent
of whether an input happens to declare `sources`. Preserve actual User Text Input
copy writes. Do not implement generic supervisor writes to make a mistaken UI true.

### F02 — P1: Save drops unrelated configuration on 33 of 34 inspected types

`node_config.py:1582` starts from generated form values; `:928` merges only form
getters. `frontend/screens/editor.py:588` applies the result through
`backend/workflow_map.py:341`, which replaces the whole config. Wait Until alone
starts from existing config. Parallel Branch explicitly preserves known legacy
keys, but not arbitrary unrelated ones.

**Reproduce:** add `audit_unrelated={"retain": true}` to any inspected node except
Wait Until; open, Save, apply returned config as editor does, reopen. The key is
lost at both 60 and 140 columns. Raw `unrelated_preserved=false` records this;
`second_save_equal=true` merely shows the normalized replacement is stable.
All 34 Cancel checks preserved the original stored node, including edits first.

**Fix once:** start from a deep copy of stored config and overlay owned field
values; explicitly retire only keys whose migration is agreed (Wait Until's
membank/transient cleanup is deliberate). Preserve hidden/inactive known values
and unknown extensions; do not default stale source selections silently without
an explicit repair path. Include structural forms in the same save contract.

### F03 — P1: Production CSS horizontally clips critical inputs

`frontend/widgets/form_generator.py:_field_children` places a single-line label,
description and input in one Horizontal. `frontend/styles.tcss:280` supplies no
responsive stacking; labels/descriptions have auto width and height 1. The
`.form-inline-row .command-input` stylesheet rule requests `1fr`, but
`frontend/widgets/command_input.py:117` sets inline width to `100%`, overriding
that constraint and overflowing the remaining row space. The shared modal has 90% width/height (`styles.tcss:102`).

**Reproduce:** production CSS at 60×24, Wait Until → focus Timeout. Field begins
at x=80 (outside the terminal), due to the inline timeout description. Text Output
→ Parameters → template begins at x=70. At 100 columns the fields still extend
past the modal; at 140 they have more visible area but still overflow. See
`focused.json` measured regions and `focus_wait_until_node_60.txt` /
`focus_text_output_node_60.txt`. W/S focus can move to a field that cannot be read.
Bare-App mounted tests miss this because they omit `frontend/styles.tcss`.

**Fix once:** shared responsive field rows: stack descriptions, constrain inputs
and wrap labels; verify the actual focused input/caret intersects the viewport.
Retain W/S/A/D semantics. Do not add a Wait-specific widget to bypass this.

### F04 — P1: File Instance is a registered demonstration advertised as functional

`backend/nodes/io/example_file_instance_node.py:29` only forwards
`context.inputs.get("input", "")`; its declared port is `file_path`. It does not
read source/path configuration, open files, emit a boolean open result, forward
according to the checkbox or write a Vault result. All these controls and claims
are present in the S screen and selector metadata.

**Reproduce:** configure `/does/not/exist` with Vault write enabled; the direct
probe emits the unrelated input object, reports no error and writes no key.
With only its declared file_path input it would emit an empty string.

**History:** SESSION_LOG's 2026-06-12 helper entry explicitly registered this
example for live dynamic-form review, with removal after review if not kept.
The helper spec says `execution_template: transform_stub`; NODE_HELPER's Current
Limitations says templates are starter bodies. This is a demo exposure defect,
not evidence that a real file-resource implementation regressed. Owner decision
D04; recommended next step is explicit demo treatment, not new execution code.

### F05 — P2: Empty/redundant navigation and misleading general help

`node_config.py:682` always creates four tabs, including “No parameters” for
No-Op. Source and Payloads repeat the same upstream/Vault reveals for L nodes;
Start even offers upstream/Vault controls without input ports. Merge and Beacon
skip tabs but inherit “number keys tabs” help (`:649`). No-Op's single-purpose
operation requires four tabs to review generic controls that it does not use.

At 60×24 the tab header truncates Connections; wrapped help plus title/footer
and two bordered vertical buttons leave very little visible form content. Save
and Cancel remain available, but constant scrolling is costly. Production
render receipts show this at all three widths; 140 improves horizontal room,
not the 24-line height budget.

**Plan:** compute applicable sections, choose compact/focused/dense composition,
number visible tabs consecutively and derive help from actual controls. Keep
buttons outside content scrolling; reduce chrome through shared styles/layout,
subject to owner visual review. Output display metadata is useful, but not always
worth its own tab. Follow the current section standard, not old fixed-tab tests.

### F06 — P2: Legacy schema misses conditional visibility and clear terms

Actual mounts retain Conditional's variable name in input mode, Set Variable's
literal value in input mode, HTTP POST body in GET mode and Text Output's prompt
when request-user-input is off. `visible_when` already exists; no bespoke screen
is needed. Old “Variable Name”, “Dead drop payload” and generated “default/error
branch name” wording obscures Vault keys, forwarding switches and output ports.
Legacy output-name blocks also omit the bracketed data type promised by the
current standard. Branch-name wording is especially misleading for HTTP/JSON
error outputs, which are not parallel branch spawners. Output names/descriptions remain valid display metadata.

**Reproduce:** choose the listed opposite mode in the 100-column alternate-state
inventory; relevant field stays displayed. Update schema + matching helper spec
where present, preserve inactive values, use action labels (“Forward incoming
dead-drop payload unchanged”), and use output/path terminology appropriate to
actual topology. Keep internal IDs stable; no execution branching on groups.

### F07 — P2: Random Number's Payload field is ignored

`backend/nodes/data/random_number_node.py:26` includes `value` labelled Payload;
`:29` uses mode, min, max and seed only. The producer template inserted `value`,
while the hand-written random body no longer consumes it. The YAML spec does
not declare that field. Mounted field and save result confirm it is editable
and persisted. Direct probe ignores `value="IGNORED"` and returns a number.
Remove the misleading editable field through metadata/schema, preserving any
old saved key under F02 until a deliberate migration is chosen.

### F08 — P2: Numeric saves and special-value contracts are inconsistent

`form_generator.py:_value_from_widget` silently converts invalid integer/float
text to 0/0.0. `node_config.py:1582` does not reject generic validation failures.
**Mounted probes:** Sleep saves -5 despite schema min 0 (execution clamps it);
Random Number min `bad` saves 0.0; Chat max_tokens `bad` saves 0. Wait Until
properly rejects invalid, non-finite and negative values in its special path.

Also, `chat_completion_node.py:378` uses `float(config.get("temperature") or 1.0)`:
configured 0 becomes 1. Mock-provider probe confirms sent_temperature=1.0.
HTTP timeout 0 becomes 10 (`io/http_request_node.py:40`); it is not Wait Until's
forever sentinel. Sleep 0 is no delay; Repeat Counter counts the failure visit;
Random Number integer mode truncates bounds. These distinctions need explicit
copy and faithful validation, not a global “0 means forever” convention.

Separate runtime numeric-fallback correction from UI validation; do not quietly
change execution during this audit. Shared error presentation should retain
input text, identify invalid fields and focus the first error on Save.

### F09 — P2: Chat forwarding and enabled-with-blank destinations need clearer contracts

Most Chat standard controls are backed by real code, but “Forward incoming payload
unchanged” is ambiguous with ten input ports. `chat_completion_node.py:397`
chooses raw document input, otherwise prompt input, ignoring context slots.
Mock-provider evidence: context-only incoming data forwards None; when prompt
and document are both present it forwards document. The fixed declared string
output type/name can also misdescribe a forwarded value. Explain the current
precedence before considering any semantic change.

Vault output defaults enabled with an empty key; runtime silently skips the write
when key is blank (`:392`). Keep-session with a blank key likewise cannot create
a useful session destination. Mounting shows editable controls but no save-time
explanation of these effective no-ops. Clarify conditional requirements and show
an actionable error or explicit “no destination configured” state. Changing the
default-on policy or forwarding source selection is an owner decision, D05.

### F10 — P2: Simulation nodes expose unused API-secret controls

`embedding_node.py:34` and `image_generation_node.py:34` intentionally simulate.
Their descriptions say so, which should be preserved. Both mount an API-secret
selector but never call `context.get_secret`; generic Vault writes also do
nothing. Size/style/model affect diagnostic strings, not an external service.
Hide unsupported credential/write controls and make simulation status prominent.
Turning these into real providers would be a separate authorized backend project.

### F11 — P2: Echo and Repeat Counter descriptions disagree with execution

`debug/echo_node.py:23` calls str(input) and optionally prefixes it; mounted
metadata claims unchanged pass-through. The probe turns an object into a string.
`debug/repeat_node.py:29` errors at `count >= max_visits`; the description says
“more than max_visits.” With max_visits=1 the first visit errors. Correct copy
and threshold explanation to match code; do not change either runtime to fit
stale copy. Error Trigger's warn mode should similarly describe emitted text.

### F12 — P2: Metadata/helper coverage is not a runtime contract check

Counter emits `count`, Repeat Counter emits `visits`, but each declares only
`default`; their extra outputs cannot be configured as ordinary ports. Treat
that as a contract issue to assess separately, not an invitation to add ports
in a UI cleanup. Several legacy nodes have permissive any/optional metadata by
design; adding stronger types requires checking actual values first.

`aotn_node_helper/ui_checks.py` checks declared widgets/default rules, not whether
composed extras are executable, save preservation, production CSS, every mode,
or full keyboard traversal. Existing green generated checks therefore do not
invalidate F01/F03/F04/F07. Add negative assertions for forbidden controls and
focused execution-contract evidence where a UI promises a side effect. Do not
regenerate hand-written nodes to obtain prettier forms.

## Deliberate design, stale docs and decisions

- **D01 — Keep Parallel Branch v1 parallel.** Older conditional keys are retained
  for save compatibility, intentionally hidden by the 2026-06-09 branch pass
  (`archive/SESSION_LOG_HISTORY.md`). A separate Conditional type is registered.
  Do not expose hidden branch modes or merge the types in this project.
- **D02 — Output termination is a design gap, not a missing UI switch for an
  existing runtime feature.** NODE_STANDARDS and 2026-06-12 taxonomy notes specify
  a termination checkbox and End Branch replacement. Current Text Output does
  not inspect such a flag; no End Branch type exists. Supervisor supports an
  explicit completion payload signal, which is not the same as implementing
  that node config. Recommend a separate small backend contract/design task;
  do not add a nonfunctional checkbox. Owner must prioritize that task.
- **D03 — Keep topology-specific forms.** Merge/Beacon flat paths and Wait's
  focused tabs are intentional. Merge has no alias control; whether alias
  editing belongs in that status/topology form is a small owner preference,
  not a reason to force four tabs. Recommended: keep compact and add alias only
  if users need it, reusing the shared alias row.
- **D04 — File Instance disposition needs owner input.** Recommended: remove it
  from ordinary add choices or label it unmistakably as a demonstration while
  keeping registration and old saves. Alternatives are a developer-only demo
  surface or a separately designed real file-resource node. No deletion made.
- **D05 — Chat choices needing owner input:** keep current document-then-prompt
  forwarding and describe it (recommended minimal correction), or schedule a
  separate explicit forwarding-source design. Decide whether an enabled blank
  Vault/session destination should block Save or show a clear incomplete state;
  recommended block only when the user explicitly enables the output/session.
- **D06 — Compact-layout presentation:** flat forms are already authorized by
  the standard. No owner decision is needed to omit empty/unsupported sections.
  Live review should select acceptable chrome density and readable descriptions,
  not revisit settled keyboard grammar or invent a uniform layout for every node.

History reconciliation: old fixed four-tab layouts and A/D tab-switching appear
in `archive/SESSION_LOG_HISTORY.md:74` and `:114`; July's
`IO_CONTRACT_UI_DESIGN.md:17` intentionally kept a legacy fallback. Those explain
how L arose, but do not override October's capability/section policy. The
2026-06-12 helper log explains File Instance. NODE_HELPER still contains an old
combined I/O selector note and an outdated label/value limitation; TASK_INDEX
and MASTER_BUILD_PLAN contain older selector-filter prose. Current mounted
selector is five tabs with search keywords, not subcategory checkboxes. The
boundary document's older decommission/materialization sections are superseded
by its later intentional Tombstone/save contract. Record these as stale context,
not authorization for taxonomy changes or tombstone removal.

## Proposed shared layout policy

1. Define actual configurable capabilities independently for input sourcing,
   runtime parameters, result routing, Vault reads/writes, fixed forwarding and
   output display metadata. Input port count or presence of `sources` must not
   decide unrelated output capabilities. Do not infer writes from Outputs family.
2. Use Source/Parameters/Payloads/Connections as meanings. Compact nodes combine
   them in a flat form; dense Chat retains meaningful tabs; graph-driven Branch,
   Merge and Wait use focused composition with the same widgets/navigation.
3. Hide irrelevant controls and their labels/descriptions/empty section headers.
   Grey only a genuinely locked supported control, with an adjacent reason.
   Keep values for temporarily hidden fields; restore them when mode returns.
4. Keep one relevant input summary/optional preview, clearly identified as wiring
   or last captured data. Never imply a preview is the current run's future value.
   Do not use a Vault declaration as a pretend live source override.
5. Name data precisely: dead-drop payload, Vault key, Parallel Branch, Merge
   Beacon. Use “output” for data ports, “branch/path” for actual topology. Explain
   units, blank values, 0, truncation and failure thresholds beside their controls.
6. Use shared command navigation: W/S rows, A/D within row, number keys for visible
   tabs, E/Enter activation, ordinary letters/digits while editing, Esc finish
   edit then cancel, Ctrl+Q revert edit then cancel; lists exit at boundaries.
   Read-only noninteractive descriptions are not extra focus stops.
7. Save/Cancel remain outside content scrolling. Reflow rows at narrow widths;
   focus and caret must remain visible. Test actual CSS at 60/100/140×24, plus
   long labels, multiline content and maximal dynamic forms.
8. Save overlays owned fields onto stored data. Explicit cleanup has a named,
   tested migration contract. Cancel and opening never change workflow data.
   Engine metadata remains portable; frontend owns layout/topology descriptions.

## Small ordered implementation stages (proposed, not implemented)

| Stage | Scope and completion gate |
|---|---|
| 0 — Preserve audit baseline | Review this audit; retain raw evidence, current dirty fixes and exclusions. Add focused failing reproductions for F01–F04 before fixes. Do not commit unrelated prior work implicitly. |
| 1 — Save and form safety | Shared config overlay, explicit retire lists, generic validation, production-CSS row sizing and visible-caret assertions. Include flat structural screens and Wait timeout. Gate: no unrelated key loss; Cancel unchanged; invalid values stay editable. |
| 2 — Capability truth | Add minimal portable capability metadata where absent and compose supported controls only. Remove false generic Vault controls; keep User Text Input copies and Parallel Branch seeds. Resolve demo disposition; omit unused simulation credentials and Random Number Payload. Gate: every displayed side-effect control has runtime evidence, no new engine semantics. |
| 3 — Compact low-complexity nodes | No-Op, Start/legacy End, Sleep, Echo/Probe/Logger/Snapshot/Counter/Repeat/Error, readers/writers and transforms via shared section helper. Fix conditional visibility and copy in schemas/specs. Gate: applicable controls only; preserved config and common keyboard grammar. |
| 4 — Structural and dense layouts | Consolidate Parallel Branch count/seeds; retain Merge/Beacon/Wait focused behavior; improve Chat descriptions/requirements and max-context form usability. Reuse existing topology helpers. Gate: 2/5 branches, no/all/missing targets, merge carry transitions, Chat context 0/1/8 and source/session combinations. |
| 5 — Separate runtime decisions and owner review | Only after authorization: termination contract, temperature-zero bug and any Chat forwarding semantic change; assess undeclared diagnostic output ports separately. Update specs/checks/docs together. Live owner review at three widths closes visual/accessibility sign-off; no provider expansion or node consolidation implied. |

Keep each stage reviewable. Stage 1's preservation/geometry fixes should not wait
for broader node design decisions. Runtime bug fixes may be prioritized earlier
as separate patches; do not mix them into metadata/layout changes invisibly.

## Verification performed and limits

- Production-CSS capture: 102 initial mounts, 68 save/reopen mounts; 278 alternate
  control states at 100 columns, no capture exceptions. Default second saves
  stable for 34/34 types at both save widths. Unrelated key retained only by Wait
  Until. Cancel unchanged for 34/34. Alternate states are **one factor at a time**,
  not all Cartesian combinations. A further **87 schema-mode/routing
  save/reopen checks** at 100 columns all retained the chosen value; preview
  toggles are intentionally not persisted. Not every text edit or multi-control
  combination was individually saved/reopened. Raw keyboard traces call shared
  cursor-down actions; alias
  editing uses real Pilot key events. These are not equivalent to live-terminal
  sign-off or a complete per-field keyboard activation test.
- Supplemental mounted probes: invalid numeric saves, five branch seeds including
  Vault at all widths, populated Merge selection/carry and list boundaries,
  focused field visibility and rendered text/SVG. Existing focused tests cover
  long Wait lists, missing/self/downstream targets, source availability,
  duplicate-source prevention, previews, hidden-control navigation, Enter/E,
  editing digits and list exits. They run on this baseline, not historical counts.
- Fresh test command from app: `.venv` Python with
  `-m pytest tests/test_wait_until_ui.py tests/test_chat_completion_node.py
  tests/test_node_helper.py tests/generated tests/test_debug_nodes.py -q`:
  **232 passed in 55.27s**. Some existing screen tests use bare App without CSS;
  their success does not clear F03. No full-suite result is claimed for this audit.
- Direct synthetic node probes establish F01/F04/F07/F11 behavior; Chat probe uses
  a fake provider and fake credential value, confirming 0→1 and forwarding
  precedence without contacting a service. No live APIs or real file reading
  were tested; executable paths were inspected and existing relevant tests run.
- Final audit integrity checks and documentation checks are recorded in
  SESSION_LOG.md and the evidence README. No application patch was made here.

**Still requiring focused verification during implementation:** changed values
saved/reopened for every affected conditional combination; editor/SaveManager
export/reload across these nodes (audit save test applies modal result to
WorkflowMap, not every disk format); obsolete/undeclared Vault keys; selection
loss while reducing/re-expanding dynamic counts; real-app parent keybinding
interactions; keyboard activation for each widget type under production CSS;
long aliases/non-ASCII text; mouse focus and terminal rendering at 60/100/140.

**Owner live review:** terminal font/contrast, selected-row highlight, scroll
tracking under long real graphs, screen-reader usability and comfortable dialog
height. No screen-reader test or owner live confirmation was performed. The
mounted evidence proves concrete overflow and contract defects, not full
accessibility compliance. Tombstone restore UI is deliberately excluded from
ordinary node configuration; planned/unregistered nodes are not implemented
coverage. No uninspected registered user-facing type is hidden behind a passing
schema check.
