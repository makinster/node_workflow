# Registered-node claims baseline — 2026-10-29

Originally captured from `439e614` for PR #151, then refreshed from
`ee0bca449425eaa23792b08f442ac3fd81e6b2fb` after the owner's four decisions.
The original Scaffolding scope is historical. The block-3 refresh adds final
Merge/Wait review status and source hashes without changing admission. The
[2026-11-01 refresh](../network_notify_change_2026_11_01/README.md) adds HTTP Request,
Notify me and If changed review status; no admission or runtime behavior changes.

[`baseline.json`](baseline.json) is the refreshed source-reviewed snapshot of
all 59 types: 21 reviewed records, 22 pending and 16 dev-only. It records declared ports,
retained defaults, current authoring acceptance, execute support and LF-normalized
source hashes. The original pre-repair snapshot remains in PR #151's Git history.
Absent `to` means the legacy implicit downstream route. Tombstone is registered
but deliberately non-authorable. Authoring acceptance does not imply admission.

V = `vault_write`, T = `transient_output`, D = `dead_drop_passthrough`,
O = `transient_outputs`. The support column reflects current execute support.
Start V/T applies to greeting mode; explicit rows have their own destinations.
No type reads O. Window Control's retained transient default is unsupported:
it always forwards the file reference and build/check reject explicit switches.

| Registered type | Review | Honours | Declared output routes / optional forwarding |
|---|---|---|---|
| `ask_claude_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `hermes_ask_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `hermes_investigate_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `ask_local_model_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `chat_completion_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `check_reply_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `check_workflow_spec_node` | pending | V,T | default: downstream/vault; report: vault |
| `concat_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `conditional_node` | reviewed | none | true, false: implicit downstream |
| `context_pack_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `counter_node` | pending | none | default: downstream (fixed forwarding); count: downstream number |
| `deep_branch_node` | pending | none | branch: implicit downstream |
| `tombstone_node` | pending | none | none |
| `disk_space_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `echo_node` | pending | none | default: implicit downstream |
| `embedding_node` | pending | none | default: implicit downstream |
| `end_node` | reviewed | none | none |
| `error_mux_node` | pending | none | default, unmatched: implicit downstream |
| `error_node` | pending | none | default: implicit downstream |
| `file_view_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `file_reader_node` | reviewed | V,T | default: downstream/vault |
| `file_output_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `file_age_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `find_lines_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding; match_count: vault |
| `get_variable_node` | pending | none | default: implicit downstream |
| `git_status_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `http_request_node` | reviewed | none | default: implicit downstream |
| `if_changed_node` | reviewed | T | changed, no_change: downstream |
| `image_generation_node` | pending | none | default: implicit downstream |
| `hermes_investigation_result_node` | pending | V,T,D | default: downstream/vault; optional forwarding; state: vault |
| `json_path_node` | reviewed | none | default: implicit downstream |
| `pick_one_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `logger_node` | pending | none | default: implicit downstream |
| `memory_snapshot_node` | pending | none | default: implicit downstream |
| `merge_node` | reviewed | none | default: implicit downstream |
| `branch_end_node` | reviewed | none | default: implicit downstream |
| `no_op_node` | pending | none | default: implicit downstream |
| `node_catalogue_node` | pending | V,T | default: downstream/vault |
| `hermes_notify_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `branch_node` | reviewed | none | path_a…path_bl (64 ports): implicit downstream |
| `probe_node` | pending | none | default: implicit downstream |
| `random_branch_node` | pending | none | path_a, path_b: implicit downstream |
| `random_number_node` | pending | none | default: implicit downstream |
| `read_lines_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `recall_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `record_event_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `remember_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `repeat_counter_node` | pending | none | default: downstream (fixed forwarding); visits: downstream number |
| `set_variable_node` | pending | none | default: implicit downstream |
| `sleep_node` | pending | none | default: implicit downstream |
| `start_node` | reviewed | V,T | default: downstream/vault |
| `subworkflow_node` | pending | none | default: implicit downstream |
| `text_output_node` | reviewed | none | default: downstream |
| `text_transform_node` | reviewed | none | default: implicit downstream |
| `user_text_input_node` | reviewed | none | default: implicit downstream |
| `variable_reader_node` | pending | none | default: implicit downstream |
| `variable_setter_node` | pending | none | default: implicit downstream |
| `wait_until_node` | reviewed | none | default: implicit downstream |
| `window_control_node` | pending | none | default: downstream |

## Executable evidence and limits

[`claims.json`](claims.json) records post-repair observations for each type and
claim, including explicit skips and unsupported-capability reasons,
attempted/committed writes, declared required/optional reads, per-key reads,
snapshot accesses, emitted ports and external-boundary protocol names.
The source/scenario hashes bind the receipt to the runner, fixtures, runtime
and declaration helpers. Ordinary pytest runs never rewrite these artifacts.
Run from the app directory to regenerate deliberately, then review the diff:

```bash
AOTN_CLAIMS_REPORT="$PWD/docs/audits/claims_baseline_2026_10_29/claims.json" \
  python -m pytest tests/test_node_claims.py -q -k claims_receipt
python -m pytest tests/test_node_claims.py -q
```

The shared runner instantiates real classes with merged real defaults and
config, calls execute with a real observed MemoryBank and records callbacks.
External transports/commands/windows are faked; investigation validation uses
its real isolated file queue, without starting a worker. Network/process escape
is blocked. Fake provider success proves local routing, not provider quality.

Palette scenarios additionally check actual value/source/mode semantics,
legacy copies, types/null/false/zero, missing values and formatting errors.
Real RunService graphs check source resolution, publication, branch routes,
shared Ends, Vault handoffs and successor traversal, repeated twice with a stale
transient value injected before the second run. Cancellation cases prohibit
late success or writes after a user-input wait is cancelled. Concat dependencies
are tested by changing a seeded value, checking precedence and removing a key;
a snapshot spy alone is not treated as proof of semantic reads.

Pending types receive default-mode and applicable generic claims, not admission.
Full source/mode/session/native-platform matrices remain family work. Skips
for absent capabilities are coverage receipts, never passing behavior claims.
This is representative scenario coverage, not proof of every configuration.

## Compatibility before rejection

The read-only audit covered **17** workflow specs nested in tracked examples
and delivery documents, including both designer versions. **Zero** would newly
fail for unsupported explicit standard flags. `tools/claims_compatibility.py`
repeats the audit against the actual authoring check; its JSON receipt is
[`compatibility.json`](compatibility.json). Owner workflows and historical audit
snapshots were not scanned or rewritten.

New authoring rejects unsupported flags as errors even for explicit false/empty
values. Existing saved workflows still load with their retained defaults; no
automatic cleanup/reinterpretation occurs. `transient_outputs` has no runtime
consumer and is rejected everywhere. Unsupported neutral defaults retained by
node classes do not become supported authoring options. Start row mode rejects
explicit greeting-routing flags. `describe` and factory metadata expose the
supported flag list; a config key merely existing is not proof of its behavior.

## Reproduced mismatches fixed in code

- Legacy Chat Completion: honour suppression, store result with string tag,
  and error on an activated blank Vault key before calling a provider.
- File Write: error on an activated blank Vault key before touching a file.
- Text Output: absent required upstream input errors; explicit empty/null
  values and a requested replacement answer keep their existing meanings.
- User Text Input: honour every legacy output-key form the shared declaration
  model accepts, via the same key helper used by Start/Text Output.
- Remember/If Changed: distinguish absent required upstream/Vault values from
  explicit null; reject absence before saving or comparing.
- Concat: expose template-root dependencies through the shared read model;
  required missing reads no longer appear undeclared in authoring metadata.

Reviewed metadata record text is unchanged. Re-attestation records source review
and links these scenarios; passing hashes are not an independent admission review.

## Owner decisions resolved — Scaffolding follow-up

All four former expected failures are passing claims; no xfail exemptions remain.
No wider palette is admitted.

- Counter declares its existing `count` output as `number`.
- Repeat Counter declares its existing `visits` output as `number`.
- Both keep `default` as fixed forwarding. Shared producer tracing scopes that
  forwarding to `default`, so numeric outputs retain their declared type.
- If Changed honours `transient_output=false`: saves/compares normally, publishes
  no data and still traverses the selected Changed/No change edge. Both routes
  have real-engine regressions. It now advertises suppression as supported.
- Window Control does not support suppression: its file reference always passes
  onward. Build/check reject explicit true/false switches. The passing policy
  claim records `supported: false` and the reason, and verifies fixed forwarding
  for retained saved settings. This is no suppression-behavior claim.

Baseline, receipt and relevant source attestations were refreshed after source
review. The If Changed input-source contract is unchanged; only its runtime
fingerprint changed. Reviewed record text and reviewed/pending counts stay intact.

## Verification

Full `pytest -n auto`: **4,496 passed, 187 skipped, zero xfails in 42.37 s**.
All **23** calibration pairs keep their expected rule verdicts; fixtures did not
change. The shared receipt has **234 pass / 179 skip / 0 xfail** node claims.
Eight further skips are non-authorable-tombstone flag-policy cases. The value
matrix has **78** rows; **21** engine graphs run twice. The real CLI rejects an
unsupported false flag with exit 1 / `unsupported_standard_flag` and no save.

Catalogue and designer caps/headroom remain covered by the full suite.
No live API calls, native OS proof or owner workflow run.


## Helper family admission — 2026-10-30

Base `8ee108b`, branch `codex/helper-family`: sixteen reviewed / 43 pending out
of 59 registered types. All four helpers support optional within-run Vault
writes (including Find lines' independent total-match count), suppression and
unchanged-input forwarding. No helper execute implementation changed. No
claim/code mismatches were found; no xfails or owner decisions were added.

The shared data-driven matrix now includes helper source/limit/error cases and
fixed Context Pack run/error snapshots. Fake Secrets prove masking without
reading actual keys. File byte/mtime snapshots assert that every helper execute
leaves the fixture filesystem unchanged. Existing security, cancellation,
Unicode, snapshot-race, deep JSON and pack-shortening tests remain in the review
attestations. Updated receipt includes helper code and scenario/trial digests.

The [admission receipt](helper_family_admission.json) gives the exact schema enum
lists, before/after catalogue counts and per-case selected snapshot sizes.
Regenerate the executable receipt only after source and scenario review:

```bash
AOTN_CLAIMS_REPORT="$PWD/docs/audits/claims_baseline_2026_10_29/claims.json" \
  python -m pytest tests/test_node_claims.py -q -k claims_receipt
```

The full-catalogue counts are Brief 14,687 → 15,794 and Compact
53,204 → 57,481 after restoring per-node standard/source prose in the PR #158
follow-up. The initial `16a764c` sizes remain in the admission receipt's
`previous` fields. Complete sixteen-type contracts use 26,144 of 50,000
characters; Brief uses 8,484. Context remains capped at 100,000, full catalogue
at 64,000, and selected contracts retain the 20% planning margin. The fixed
twelve-type bundle uses 22,345 characters. No fields, defaults or claims were
removed to fit. The shared validation dependency's repair was re-reviewed;
record content and the four helper execute implementations remain unchanged.

Follow-up full `pytest -n auto`: **4,692 passed, 187 skipped, zero xfails**.
All three mock sets and thirty calibration rule pairs retain expected results.
The run 000035 case-3 regression uses the real node implementations plus a
separate engine run; unsupported admitted compositions report `needs_review`.
No real API calls or paid-judge quality claim.

## PR #158 follow-up 2 — exact layout and constraint requirements

Context Pack's expanded reviewed record describes the literal header, section
and per-line framing, mask, empty/omitted/shortened JSON markers and both shortening
footer forms. Two new value scenarios compare independent UTF-8 bytes, including
multiline trailing blanks, a mocked secret and prefix-removal counts. Execute is
unchanged. The record and Check reply selection dependency were re-reviewed and
attested before regenerating `claims.json`: scenario version 4, 152 value scenarios,
234 passing / 179 reasoned skipped generic claims, 33 twice-run engine graphs.

Requirement `kind` is optional before `acceptance`, default action; constraints
need no capability role but remain in draft/judge inputs and judge coverage.
The full mock pipeline and forbidden-write mutation cover continued enforcement.
Schemas were regenerated with `python -m tools.draft_trials.reply_schemas --write`.
No admission change; sets 1/2 retain their exact twelve-type baseline.

Latest full `pytest -n auto`: **4,705 passed, 187 skipped, zero xfails** (42.67 s).
Mock sets 1–3 and all thirty calibration pairs pass. Full Brief/Compact:
15,794 / 57,781 (cap 64,000); admitted: 8,484 / 26,444 (contract cap 50,000).
The twelve-type bundle remains 22,345. Representative selected snapshots peak at
11,929 with context cap 100,000. Judge prompt and workflows/ are unchanged.
No API calls or paid-reviewer improvement claim; no claim/code mismatches found.


## Family 2 block 2 dependency recheck — 2026-10-30

The authoring hook now calls shared graph preflight in draft mode. Source review
confirmed that record prose, node execution, value/source behavior, standard flag
policy and admission remain unchanged. Twelve existing records transitively
referencing authoring or branch health have refreshed source attestations,
including the new flow owner, validator and issue-code registry. These are
source-dependency rechecks, not independent admission reviews or new flow records.

`baseline.json.flow_analysis_recheck` pins the changed graph/check sources and
new graph fixtures. `claims.json` was regenerated through the executable claims
runner using its existing local doubles; the authoring fingerprint changes and
all recorded observations remain identical. No API/model execution or owner
workflow scan was performed. Full-suite verification is in the latest Session Log.

## Collecting Merge runtime dependency recheck — 2026-10-30

The baseline source hashes for Branch and Merge are refreshed from `f57f4ed`.
Reviewed record text and admission are unchanged. The receipt now also binds
MasterState, RunContext and the real-engine Merge arrival tests; the reviewed
ordinary source/Vault/forwarding graphs remain required. Merge remains pending
metadata review and drafter admission. The original explicit
`MergePlan` fixtures remain; the follow-up now derives normal-startup plans from
the shared flow proof after rebasing onto #162/#163. Saved and child workflows
are covered by normal-startup engine tests; unproved shapes fail preflight.

2026-10-31 recheck: fresh groups after Merge, plain startup refusals, and the
child-call error translation are covered by the refreshed receipt. Added the
child-call source dependency; no reviewed metadata text or admission changed.
The 57 explicit-plan cases remain, alongside 30 startup integration cases.

## Family-2 receipt refresh (2026-10-31)

Generic flag checks remain protocol-level tests; they do not prove join or wait
coordination through callback mocks. The separate [real-engine receipt](../family_two_records_2026_10_31/README.md)
binds 95 scenarios to source hashes and observed runs. Metadata review and drafter
admission are separate; the generic receipt now reads actual record status.

2026-10-31 Family 2 scorer recheck: the requested Beacon cleanup changes the
`rules_set_three.py` and `structure_rules.py` source fingerprints. Regenerated
the executable receipt with unchanged observations (234 pass / 179 skip); no
node source, record, palette or admission change. The separate
[set-4 receipt](../family_two_set4_2026_10_31/README.md) carries new evaluator/data
hashes and real-engine results; set 4 is not part of the thirty-pair default.

2026-10-31 Family 2 Stage 1 recheck: `palette_selection.py` and the Check workflow
spec node changed, so `check_reply_node`'s source hash, the Check node's baseline row
and its source-contract runtime hash are refreshed. The node's only change passes
its existing flow report to the draft check; no record text, source option or
standard flag moved. Merge joins the admitted engine scenarios (normal plus
supported Vault modes). [Stage 1 audit](../family_two_stage1_2026_10_31/README.md).

2026-10-31 Family 2 Stage 2 recheck: `palette_selection.py` and the trial admission
sources changed, so `check_reply_node`'s source hash and this receipt are refreshed. No
node source, record text, source option or standard flag moved. Wait Until joins the
admitted engine scenarios. [Stage 2 audit](../family_two_stage2_2026_10_31/README.md).
