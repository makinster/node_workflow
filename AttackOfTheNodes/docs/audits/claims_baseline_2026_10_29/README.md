# Registered-node claims baseline — 2026-10-29

Captured before this repair from `439e6148e29eaab951e187592d484b508190aa15`
(main including #150). The owner accepted the eight recommendations in
`/home/makin/src/agent_channel/palette-scaling-plan.md`; this PR implements
claims only, without shortlist work, new nodes, metadata backfill or admission.

[`baseline.json`](baseline.json) is the immutable source-reviewed snapshot of
all 59 types: 12 reviewed records and 47 pending. It records every declared
input/output (including `to` / `pass_through` where present), retained default
flags, global authoring acceptance, execute support and LF-normalized sources.
Absent `to` means the legacy implicit downstream route, not a newly invented
Vault capability. Tombstone is registered but deliberately non-authorable.

Before this PR, all four flags were globally accepted as explicit overrides.
V = `vault_write`, T = `transient_output`, D = `dead_drop_passthrough`,
O = `transient_outputs`. The support column is the pre-change execute audit;
it does not promise all retained defaults are supported. Start V/T applies to
legacy greeting mode; explicit rows have their own destinations. No type reads O.

| Registered type | Review | Honours | Declared output routes / optional forwarding |
|---|---|---|---|
| `ask_claude_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `hermes_ask_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `hermes_investigate_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `ask_local_model_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `chat_completion_node` | pending | V,D | default: downstream/vault; optional forwarding |
| `check_reply_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `check_workflow_spec_node` | pending | V,T | default: downstream/vault; report: vault |
| `concat_node` | reviewed | V,T,D | default: downstream/vault; optional forwarding |
| `conditional_node` | reviewed | none | true, false: implicit downstream |
| `context_pack_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `counter_node` | pending | none | default: implicit downstream |
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
| `find_lines_node` | pending | V,T,D | default: downstream/vault; optional forwarding; match_count: vault |
| `get_variable_node` | pending | none | default: implicit downstream |
| `git_status_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `http_request_node` | pending | none | default: implicit downstream |
| `if_changed_node` | pending | none | changed, no_change: downstream |
| `image_generation_node` | pending | none | default: implicit downstream |
| `hermes_investigation_result_node` | pending | V,T,D | default: downstream/vault; optional forwarding; state: vault |
| `json_path_node` | reviewed | none | default: implicit downstream |
| `pick_one_node` | pending | V,T,D | default: downstream/vault; optional forwarding; details: vault |
| `logger_node` | pending | none | default: implicit downstream |
| `memory_snapshot_node` | pending | none | default: implicit downstream |
| `merge_node` | pending | none | default: implicit downstream |
| `branch_end_node` | reviewed | none | default: implicit downstream |
| `no_op_node` | pending | none | default: implicit downstream |
| `node_catalogue_node` | pending | V,T | default: downstream/vault |
| `hermes_notify_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `branch_node` | reviewed | none | path_a…path_bl (64 ports): implicit downstream |
| `probe_node` | pending | none | default: implicit downstream |
| `random_branch_node` | pending | none | path_a, path_b: implicit downstream |
| `random_number_node` | pending | none | default: implicit downstream |
| `read_lines_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `recall_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `record_event_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `remember_node` | pending | V,T,D | default: downstream/vault; optional forwarding |
| `repeat_counter_node` | pending | none | default: implicit downstream |
| `set_variable_node` | pending | none | default: implicit downstream |
| `sleep_node` | pending | none | default: implicit downstream |
| `start_node` | reviewed | V,T | default: downstream/vault |
| `subworkflow_node` | pending | none | default: implicit downstream |
| `text_output_node` | reviewed | none | default: downstream |
| `text_transform_node` | reviewed | none | default: implicit downstream |
| `user_text_input_node` | reviewed | none | default: implicit downstream |
| `variable_reader_node` | pending | none | default: implicit downstream |
| `variable_setter_node` | pending | none | default: implicit downstream |
| `wait_until_node` | pending | none | default: implicit downstream |
| `window_control_node` | pending | none | default: downstream |

## Executable evidence and limits

[`claims.json`](claims.json) records post-repair observations for each type and
claim, including explicit skips and strict expected failures with reasons,
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

## Owner decisions: fix code or fix claim?

Each item is a strict per-claim xfail; an unexpected pass fails the suite and
requires review. None is a reviewed palette type. No wider palette is admitted.

- `counter_node` / `ports`: Emits undeclared count data port; owner must choose an output port or remove the extra data.
- `repeat_counter_node` / `ports`: Emits undeclared visits data port; owner must choose an output port or remove the extra data.
- `if_changed_node` / `transient_output`: Declared transient switch is ignored on changed/no_change; clarify suppression versus route traversal.
- `window_control_node` / `transient_output`: Declared transient switch is ignored; decide whether this fixed-forwarding action supports suppression.

## Verification

Full `pytest -n auto`: **4,488 passed, 187 skipped, 4 xfailed in 40.62 s**.
All **23** calibration pairs keep their expected rule verdicts; fixtures did not
change. The shared receipt has **230 pass / 179 skip / 4 xfail** node claims.
Eight further skips are non-authorable-tombstone flag-policy cases. The value
matrix has **78** rows; **21** engine graphs run twice. The real CLI rejects an
unsupported false flag with exit 1 / `unsupported_standard_flag` and no save.

Catalogue sizes are unchanged: Brief Text **14,569**, Compact Text **53,217**,
JSON **18,214 / 76,638**, v2 selected contracts **21,513 / 50,000**. Existing
caps/headroom pass. No live API calls, native OS proof or owner workflow run.
