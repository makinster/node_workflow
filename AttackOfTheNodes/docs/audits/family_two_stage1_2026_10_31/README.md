# Family 2 Stage 1 admission — 2026-10-31

Base: main `821688d`. Foundational. No API or model calls, no `--real-calls`, no
change to the engine, the flow checker or `frontend/`. These results cover what the
code does with known drafts; they say nothing yet about drafting quality.

**Stage 1:** one split, every path wired directly to one collecting Merge, with the
Merge's output used downstream.

## What changed

- `merge_node` is admitted (sixteen types). The role IDs are unchanged; `join`
  already existed. Wait Until, Merge Beacon and Set/Get Variable stay out.
- Draft checks refuse anything beyond Stage 1 in plain words, through the existing
  one structural redraft. The refusals read the flow report the check already
  produced, so there is no second analysis.
- The analysis and draft prompts gain two short passages, including a worked
  `{input[path_a]}` example. They say a shared End only finishes paths and never
  joins them. The judge prompt is unchanged.
- F2-01, F2-02 and pairs 1 and 6 join the normal run and `--case-set all`, making 32
  calibration pairs / 64 judge calls. F2-03 to F2-05 and pairs 2 to 5 stay opt-in.
- `ADMISSION_VERSIONS` moves admission, role schema, contracts and cache together to
  2, with `draft_stage` 1. The evaluator policy moves to `family-2-evaluator-2`.
- `admission_baseline.json` gains a `stage_1` section.

**Sets 1, 2 and 3 are deliberately frozen.** Each keeps its exact palette. Configuring
the designer for those scopes gives output byte-identical to unchanged main (digests
are pinned in the baseline), so the prompts and schemas they receive do not move.
Their snapshot receipts do gain two fields, which is the only new text they see. The
stage check does not apply to them. Only set 4 exercises the sixteen-type drafter.

## Free replay of saved run 000046

```bash
python -m tools.draft_trials --trial-root <fresh> --replay ~/draft-trial-01/runs/000046 --case-set all
```

| Gate | Main `821688d` | This branch |
|---|---:|---:|
| Set 1 | 10/10 | 10/10 |
| Set 2 | 10/10 | 10/10 |
| Set 3 | 3/4 | 3/4 |
| Set 4 (F2-01, F2-02) | not in run | 0/2, both `diverged` |
| Saved replies consumed, sets 1–3 | 68 of 68 | 68 of 68 |
| Calibration, frozen 60 verdicts | 60 same | 60 same |
| Calibration, four new verdicts | not in run | 4 `diverged` |
| Calibration result | pass | **fail**, only because of those 4 |
| Overall | fail | fail |
| Real API calls | 0 | 0 |

Sets 1–3: 24 of 24 cases have the same outcome, with no newly passing, newly failing
or diverged cases. All 21 saved drafts are byte-identical once the relocated fixture
folder is normalized. The overall `fail` on both sides comes from the set-3 case 4
failure carried in the saved run (`No saved draft / no completed success gate`).

**Set 4 has no saved replies.** F2-01 and F2-02 report `replay_diverged`: "current call
analysis; saved no further saved reply". The four new pair rows do the same for their
judge verdict. Nothing is invented. Their mechanical rules still run and are correct:
good passes and bad fails on both pairs. So the calibration `fail` here is expected
and is not a regression. A set-4 replay only becomes possible after a paid run saves
replies.

**Do the version changes make saved replies unusable? No.** Nothing binds a saved reply
to a version, and every replay builds a fresh snapshot, so all saved replies still
apply. **Is the comparison still meaningful? Yes, for sets 1–3:** they get the same
prompts and rules as before, so this is a real no-regression check. It says nothing
about set 4 or about how a model would respond to the new prompts. Run 000046 is
itself a replay of paid run 000044, so its token and cost figures are synthetic: use
it for reply text, not as a cost baseline.

## Real engine

`python -m tools.draft_trials.family_two --output <fresh>`: **pass**. 60 engine start
attempts in controlled forward and reverse orders: 54 request and pair runs all
finished, plus 6 control runs. Two orders are not exhaustive proof.

| Request | Variant | Show output (both orders) |
|---|---|---|
| F2-01 | plain | `A: Alpha report\nB: Beta report` |
| F2-01 | changed | `A: Café opened\nB: Line one\nLine two` |
| F2-01 | empty-b | `A: Alpha report\nB: ` |
| F2-02 | plain | `Value: 42\nFlag: True\nNote: Hello` |
| F2-02 | zero-false | `Value: 0\nFlag: False\nNote: Hello` |
| F2-02 | null | `Value: None\nFlag: True\nNote: Hello` |
| F2-02 | empty-text | `Value: \nFlag: False\nNote: Hello` |
| F2-02 | list | `Value: [1, 2]\nFlag: True\nNote: Hello` |
| F2-02 | object | `Value: {'a': 1}\nFlag: True\nNote: Hello` |

Pairs 1 and 6 pass: good is correct, bad is rejected. Controls pass:
`standalone_merge` runs but is refused as a draft; `second_merge_same_group` and
`control_back_edge` are refused at startup.

A mock `--case-set all` run passes through the full designer graph: 10/10, 10/10, 4/4,
2/2, with 65 fixture runs and 140 mock calls.

## Sizes

[Full figures](admission.json). Nothing is near a cap.

| What | Characters | Cap |
|---|---:|---:|
| Sixteen-type Brief / Compact contracts | 9,707 / 30,391 | 50,000 contracts |
| Fifteen-type Brief / Compact, for comparison | 8,855 / 27,536 | 50,000 contracts |
| Selected snapshot, F2-01 / F2-02 | 13,830 / 14,944 | 50,000 (40,000 planning) |
| Draft prompt, before / after | 1,762 / 2,312 | none of its own |
| Analysis prompt, before / after | 4,669 / 4,915 | none of its own |
| Largest actual call, F2-01 / F2-02 (judge) | 26,426 / 31,195 | 100,000 context |
| Whole catalogue Brief / Compact | 15,736 / 56,704 | 64,000 |

## Where the plan and merged code disagree

The code won in every case.

1. **Versions.** The plan says to bump admission, role schema, contract and cache
   versions. No such versions existed apart from the evaluator policy, so I added one
   shared set and put it in the snapshot receipt. The role list did not actually
   change, and provider caching follows content rather than a version number.
2. **One Merge.** The plan says one Merge per group, and the shared analysis only
   catches two Merges in the same group. This task says no more than one Merge, so the
   Stage 1 check also refuses two Merges on either-or routes.
3. **Split inside a path.** The plan treats this as a Merge obligation. On the
   sixteen-type drafter it is refused even with no Merge in the draft, as this task
   lists it. An ordinary single split with no Merge stays allowed, and set 2 case 8
   needs that.
4. **Merge record text.** The plan's draft record said "Drafts require a split and at
   most one Merge per group". The merged record does not; it mentions later sub-paths
   and side paths ending, which are Stage 2. I left the record alone, so the drafter
   learns the limit from its prompt and the check.
5. **Judge wording.** The plan expects the judge to see a Merge summary. It does, inside
   the structural report, but the prompt itself is unchanged and existing tests pin it.
6. **Pairs and records.** The plan's section 6 counts (20/23/16) predate dropping
   Set/Get; the code has 18 reviewed, 25 pending, 16 dev-only. The plan has five pairs
   and F2-06; the set-4 proposal and code have six pairs and no F2-06.
7. **Fingerprints.** Passing the flow report to the draft check changes the Check node's
   `execute`, so its source-contract runtime hash and baseline row are refreshed. Merge
   also joined the admitted engine claims, which needed its `path_a` input and value.

## Known limit

"Result used downstream" comes from the analysis's control edges, which do not name
ports. A Merge wired only through its error output to a later step would pass this
check. The set-4 rules and real fixtures still fail such a draft in trials, but a live
draft would rely on the judge.

## What the paid run should watch

1. **Pair 6 could stop the whole batch.** The judge is told a shared End is not a
   problem, and pair 6's bad draft uses one. A judge false pass fails calibration, which
   blocks all cases. This is the largest risk.
2. **Analysis must declare `join`.** If it does not, a draft using Merge is refused as
   "unselected", and the redraft cannot fix that because the selection is frozen. Check
   `selection.roles` on any F2 failure.
3. **Redraft use.** The Merge record may tempt nested or side-path shapes. Count
   `draft_retry` on F2-01/02 and read `first_check_error`.
4. **Possible scorer false failures.** A correct draft using a node outside the
   evaluator's local list (for example Check reply to parse JSON in F2-02) fails rather
   than asking for review. A File Reader not set to Configured returns `needs_review`.
5. **Merge slots.** Watch for `{input}` printing the whole record, and for Show labels.
   Python spellings (`True`, `None`) are expected.
6. **Target runs use real timing,** not the controlled orders above.
7. **Sets 1–3 are unchanged.** Any movement there is model variation or an existing
   issue, not this admission. They also say nothing about the sixteen-type drafter.
8. **Cost.** Ten more calls than before (6 case, 4 judge) plus any redrafts, a third
   cached contract block, and judge prompts of 26–31 thousand characters. Not measured.

## Paid run 000048 and the three-path fix

First real drafts with Merge: F2-01 fully right; F2-02 blocked itself, saying Branch
"exposes only two parallel outputs". The Branch contract says 2 to 64 and lists
`branch_count`, but its output line shows the two default ports. The draft guidance
now says `branch_count` sets the number of paths and that Merge has `path_a` to
`path_e` unless `input_slots` raises it. Sets 1, 2 and 3 do not see this text.

## Judge report size

Runs 000048 and 000049 failed calibration on the old pair
`helper_json_extra_fields_allowed`: the verdict was right, but the reply split its one
requirement into several rows. The pair passed in 000044. The only difference in its
judge question since then is the raw flow analysis added to the check report, which
took it from 5,854 to 10,122 characters. The published report now carries each Merge's
plain summary and any findings; with no Merge and no finding it adds nothing, so these
older questions match 000044 again. `check` still returns the full analysis, which the
Stage 1 draft check uses. That this caused the row splitting is a likely cause, not a
proven one.

## Label on its own line

Run 000050's F2-01 draft printed each label alone on the line above its value. The
output was correct and the judge passed it, but the scorer only accepted `A: value` or
`[A] value`. It now accepts all three (`family-2-evaluator-3`). The label must still be
alone on its line, and order and values are still checked.
