# Family 2 block 4, first half — 2026-10-31

Based on main `58a2299` (merged #162/#163/#164); source implementation `46daf57245c8797c3a504ce1dd757d1ef73d6815`.
Scorer/fixtures only. Merge, Wait Until and set 4 remain unadmitted. No backend records, engine, checker, palette, roles, drafter or judge prompts changed.
The original thirty calibration pairs are byte-for-byte unchanged. Stage 2 requires an explicit offline flag.

Full suite: **5,005 passed / 187 skipped**, zero failures or xfails, in **103.13 s** (`pytest -n 8 -q`).
The claims receipt was regenerated with unchanged 234 pass / 179 skip observations; only the two changed trial-tool source fingerprints differ. No node record attestation was changed.

## Reproduce offline evidence

```bash
python -m tools.draft_trials.family_two --output /fresh/absolute/stage1
python -m tools.draft_trials.family_two --output /fresh/absolute/stage2 --stage 2
python -m tools.draft_trials --trial-root /fresh/absolute/replay \
  --replay ~/draft-trial-01/runs/000046 --case-set all
```

The first command runs F2-01/02 and pairs 1/6 only. The second explicitly verifies withheld Stage 2 locally; it grants no admission. The ordinary trial CLI still selects only sets 1/2/3, including `--case-set all`. There is no real-call option in the new offline command.

The evaluator uses `analyze_flow` profiles/groups/lineages/slot shapes. Its event scheduler, value receipts, collection, provenance and field-use checks are independent of the production collector. Real fixtures use production RunService, Supervisor, node execute methods, MemoryBank and collector; only execute permission is gated to control scheduling. Invalid graphs go through real startup validation, with no injected plans or disabled checker.

**120 real-engine start attempts**: **104 completed workflows**, **16 preflight refusals**, all expected. Every request variant and both sides of every pair were checked forward and reverse. These two schedules are not exhaustive interleaving proof. [The receipt](verification.json) includes all 120 observations, typed collected values, completion/gate/continuation facts, controlled steps, source hashes and unchanged admission.

## Request fixtures: actual engine results

| Request | Variant | Forward / reverse | Actual Show bodies (both orders) |
|---|---|---|---|
| F2-01 | plain | finished / finished; correct | `["A: Alpha report\nB: Beta report"]` |
| F2-01 | changed | finished / finished; correct | `["A: Café opened\nB: Line one\nLine two"]` |
| F2-01 | empty-b | finished / finished; correct | `["A: Alpha report\nB: "]` |
| F2-02 | plain | finished / finished; correct | `["Value: 42\nFlag: True\nNote: Hello"]` |
| F2-02 | zero-false | finished / finished; correct | `["Value: 0\nFlag: False\nNote: Hello"]` |
| F2-02 | null | finished / finished; correct | `["Value: None\nFlag: True\nNote: Hello"]` |
| F2-02 | empty-text | finished / finished; correct | `["Value: \nFlag: False\nNote: Hello"]` |
| F2-02 | list | finished / finished; correct | `["Value: [1, 2]\nFlag: True\nNote: Hello"]` |
| F2-02 | object | finished / finished; correct | `["Value: {'a': 1}\nFlag: True\nNote: Hello"]` |
| F2-03 | plain | finished / finished; correct | `["Slow: Slow result\nUpper: MIXED CASE\nLower: mixed case"]` |
| F2-03 | changed | finished / finished; correct | `["Slow: Other\nUpper: ÜNÏ CODE\nLower: ünï code"]` |
| F2-04 | plain | finished / finished; correct | `["Ready", "File: Source text\nStatus: Ready"]` |
| F2-04 | changed | finished / finished; correct | `["Ready", "File: Other text\nStatus: Ready"]` |
| F2-05 | yes | finished / finished; correct | `["Note: Hello\nDecision: Approved"]` |
| F2-05 | no | finished / finished; correct | `["Note: Hello\nDecision: Needs review"]` |
| F2-05 | not-exact | finished / finished; correct | `["Note: Hello\nDecision: Needs review"]` |
| F2-05 | capital | finished / finished; correct | `["Note: Hello\nDecision: Needs review"]` |

F2-02 retains 0, False, None, empty text, list and object types in the collected record. F2-03 continues on the shallow slow-reader supervisor even when both deep paths finish first. F2-04 Ready follows reader completion. F2-05 joins one scalar decision, including not-exact and uppercase negative choices. All fixture files are unchanged by execution.

## Calibration fixtures: good and bad actual results

Each row below covers both scheduling orders. Every GOOD finishes with the independent request output; every BAD is mechanically rejected. A completed BAD means its actual output is wrong, rather than a runtime failure. A preflight refusal means no node execute work ran.

| Pair | Stage | Variant | GOOD | BAD engine disposition | Actual BAD Show bodies / error codes |
|---|---|---|---|---|
| 1 `collect_vs_pick_one` | 1 | plain | finished; correct | finished; rejected | `["42"]` |
| 1 `collect_vs_pick_one` | 1 | zero-false | finished; correct | finished; rejected | `["0"]` |
| 1 `collect_vs_pick_one` | 1 | null | finished; correct | finished; rejected | `["None"]` |
| 1 `collect_vs_pick_one` | 1 | empty-text | finished; correct | finished; rejected | `[""]` |
| 1 `collect_vs_pick_one` | 1 | list | finished; correct | finished; rejected | `["[1, 2]"]` |
| 1 `collect_vs_pick_one` | 1 | object | finished; correct | finished; rejected | `["{'a': 1}"]` |
| 2 `handoff_vs_lost_child` | 2 | plain | finished; correct | finished; rejected | `["Slow: Slow result\nUpper: MIXED CASE"]` |
| 2 `handoff_vs_lost_child` | 2 | changed | finished; correct | finished; rejected | `["Slow: Other\nUpper: ÜNÏ CODE"]` |
| 3 `either_or_vs_escape` | 2 | yes | finished; correct | preflight_rejected; rejected | `["merge_required_path_escape"]` |
| 3 `either_or_vs_escape` | 2 | no | finished; correct | preflight_rejected; rejected | `["merge_required_path_escape"]` |
| 3 `either_or_vs_escape` | 2 | not-exact | finished; correct | preflight_rejected; rejected | `["merge_required_path_escape"]` |
| 3 `either_or_vs_escape` | 2 | capital | finished; correct | preflight_rejected; rejected | `["merge_required_path_escape"]` |
| 4 `gate_vs_impossible_wait` | 2 | plain | finished; correct | preflight_rejected; rejected | `["impossible_wait"]` |
| 4 `gate_vs_impossible_wait` | 2 | changed | finished; correct | preflight_rejected; rejected | `["impossible_wait"]` |
| 5 `same_slot_list_vs_overwrite` | 2 | plain | finished; correct | finished; rejected | `["Slow: Slow result\nUpper: ['MIXED CASE', 'mixed case']\nLower: mixed case"]` |
| 5 `same_slot_list_vs_overwrite` | 2 | changed | finished; correct | finished; rejected | `["Slow: Other\nUpper: ['ÜNÏ CODE', 'ünï code']\nLower: ünï code"]` |
| 6 `join_vs_shared_end` | 1 | plain | finished; correct | finished; rejected | `["A: Alpha report", "B: Beta report"]` |
| 6 `join_vs_shared_end` | 1 | changed | finished; correct | finished; rejected | `["A: Café opened", "B: Line one\nLine two"]` |
| 6 `join_vs_shared_end` | 1 | empty-b | finished; correct | finished; rejected | `["A: Alpha report", "B: "]` |

Pair 5 GOOD collects `path_b` as a stable ordered list, with separate projections for Upper/Lower. BAD prints the whole list under Upper. Pair 6 BAD really runs two independent Shows into a shared End: the End is a legal endpoint and supplies no join barrier.

## Controls

| Control | Stage | Actual engine result | Draft/evaluator result |
|---|---|---|---|
| `standalone_merge` | 1 | finished / finished | fail (expected) |
| `second_merge_same_group` | 1 | preflight_rejected / preflight_rejected | fail (expected) |
| `control_back_edge` | 1 | preflight_rejected / preflight_rejected | fail (expected) |
| `independent_side_end` | 2 | finished / finished | pass (expected) |
| `shared_vault_replacement_unordered` | 2 | finished / finished | fail (expected) |

The shared Vault control produces Beta then Alpha as the last-written value under opposite schedules, so it has no guaranteed winner. Additional tests exercise missing versus empty, terminal failure without partial join success, quiet Stop, the Ready label trap, waiting on Branch instead of the reader, source duplication/literal fabrication, serial work, renamed handles and equivalent Concat/bracket-label forms.

## Free replay comparison

| Gate | Main 58a2299 | Updated scorer |
|---|---:|---:|
| Set 1 | 10/10 | 10/10 |
| Set 2 | 10/10 | 10/10 |
| Set 3 | 3/4 | 3/4 |
| Original 30-pair calibration | pass | pass |
| Real API calls | 0 | 0 |

All **24 case outcomes** and **60 calibration observations** are unchanged: zero newly passing, newly failing or diverged. Both consume exactly 128 saved replies. The inherited set-3 case-4 failure (`No saved draft / no completed success gate`) remains, so both overall replay reports say fail. This is free replay evidence, not fresh drafting-quality evidence.

## Proposal / merged-code differences and limits

- The proposal heading says five calibration pairs, but its coordinator decision adds pair 6: this implementation has six, with only pairs 1/6 in the default offline stage.
- Merged 58a2299 refuses direct Merge-to-Merge chains and overlapping joins at app startup as well as in drafts; the older plan limited the repeated-join refusal to drafts. Fresh splits after a completed join form new groups in merged analysis. No engine/checker changes were made.
- F2-04 deliberately has an intermediate Ready Show and one final combined Show; the intermediate label is blank. All text representations follow merged Python formatting.
- No engine/checker bug was found in this fixture matrix. Unsupported formatting/Context Pack masking or shortening returns needs_review, rather than a quality claim.

Full raw engine artifacts are in `/tmp/family2-set4-final-stage2/report.json`; Stage 1 in `/tmp/family2-set4-final-stage1/report.json`. Baseline/final replay reports are under `/tmp/family2-set4-baseline/runs/000001/` and `/tmp/family2-set4-final-replay/runs/000001/`. The tracked receipt retains the relevant evidence independent of those temporary paths.
