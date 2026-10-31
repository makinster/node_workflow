# Family 2 Stage 2 admission — 2026-10-31

Base: main `b52ed36`. Foundational. No API or model calls, no `--real-calls`, no change
to the engine, the flow checker or `frontend/`. These results cover what the code does
with known drafts and saved replies; they say nothing yet about drafting quality.

**Stage 2 adds to drafts:** a path that splits again with its children joining the same
Merge, Wait Until gates, and same-slot rejoins (either-or routes give one value;
concurrent paths give a list).

## What changed

- `wait_until_node` is admitted (seventeen types), through a new role `wait_for_step`
  that adds it, as `join` adds Merge. Merge Beacon and Set/Get stay out.
- `stage_one_problems` is now `draft_stage_problems(flow, draft)`, the check for the
  current stage.
- The analysis and draft prompts gain short worked examples for the three shapes, the
  Show label trap and the Wait Until target. The judge prompt is unchanged.
- F2-03 to F2-05 and pairs 2 to 5 join the normal run and `--case-set all`: 36 pairs / 72
  judge calls, 29 cases, 73 fixture runs.
- `ADMISSION_VERSIONS` moves admission, role schema, contracts and cache together to 3,
  with `draft_stage` 2. The evaluator policy is `family-2-evaluator-4`.
- `admission_baseline.json` gains `stage_2`; `stage_1` stays as the record of that stage.

**Sets 1, 2 and 3 are unchanged.** Their configured designers still match the digests
pinned at Stage 1, and `role_ids` keeps `wait_for_step` out of their role lists. The only
text that moves for them is the version numbers in their snapshot receipts. Their stage
check stays off.

## What the draft stage check refuses

| Shape | Who refuses | What the drafter is told |
|---|---|---|
| Second Merge in one group | Shared check | "This Merge joins paths that an earlier Merge already joined. Connect these paths to one Merge." |
| Merge with no split | Shared check | "Merge "Merge" is outside a split; it passes through one arrival." |
| Loop | Shared check | "loops are not supported in drafts yet" |
| Beacon | Shared check | "Use direct connections to Merge here. Merge Beacons are supported in the editor, but not in drafts." |
| Route escaping a required join | Shared check | "Merge "Merge" waits for path through "Conditional" (path_b), but route false leads away from it." |
| Impossible wait | Shared check | "Wait "Wait Until" depends on downstream node Text Output." |
| Merge's error output wired | Stage check | "a route leaving the Merge is not available in drafts. Remove the Merge's error wire." |
| Merge result unused | Stage check | "the Merge's collected result must feed a later step before End." |
| Split inside a path or beside a Merge, not joining it | Stage check | "a split inside a path, or beside a Merge, must have its paths join that Merge. …" |
| Wait Until on a split, or on nothing | Stage check | "Wait Until must name the step it waits for, not a split. …" |

The stage check also has its own words for the first four, used if a report ever reaches
it with them. In real use the shared check stops those first.

**Choices made, each with a test:**

- **A path ending before the Merge is allowed.** The set 4 proposal says an independent
  side path ending at End is legal at Stage 2, and plan decision 4 agrees. The Merge
  summary tells the judge "X ends; supplies no Merge value". A path the request needed
  still fails: `handoff_vs_lost_child` catches that on output.
- **One Merge per group is literal.** Stage 1 refused any second Merge. Two Merges in
  separate groups on either-or routes now pass; the real engine runs that shape correctly
  in both orders.
- **"A route leaving a Merge"** covers a waited-for path that can leave a required join
  (decision 7, shared check) and the Merge's own error output (stage check). A Conditional
  directly after the Merge stays allowed: the group has closed, nothing can escape, and
  it is a real later step.
- **A nested split with no Merge stays refused.** Stage 2 admits sub-path joins, not nested
  splits in general.
- **An error route that rejoins the same input is allowed,** as the shared check treats it
  as an either-or. No request or fixture here exercises it.

## The Stage 1 known limit is closed

`analyze_flow` cannot tell the port: its control rows have no port name. Adding one would
be a checker change, so the stage check reads one thing from the draft instead: the first
wire on `<merge>.default` and on `<merge>.error`. That walks nothing; graph facts still
come from the analysis. A Merge wired on only through its error output is now refused
with both messages above.

## Free replay of saved runs

```bash
python -m tools.draft_trials --trial-root <fresh> --replay ~/draft-trial-01/runs/000050 --case-set 4
python -m tools.draft_trials --trial-root <fresh> --replay ~/draft-trial-01/runs/000048 --case-set all
```

| Gate | 000050 on main | 000050 here | 000048 on main | 000048 here |
|---|---:|---:|---:|---:|
| Set 1 / 2 / 3 | not in run | not in run | 10/10, 10/10, 3/4 | 10/10, 10/10, 3/4 |
| Set 4 saved cases | 2/2 | 2/2 | 1/2 | 1/2 |
| Same / newly passing / newly failing / diverged | 1 / 1 / 0 / 0 | 1 / 1 / 0 / 0 | 26 / 0 / 0 / 0 | 26 / 0 / 0 / 0 |
| Calibration, frozen 64 verdicts | 64 same | 64 same | 64 same | 64 same |
| Calibration, eight new verdicts | not in run | 8 `diverged` | not in run | 8 `diverged` |
| Calibration result | pass | **fail** | fail | fail |
| Overall | pass | **fail** | fail | fail |
| Real API calls | 0 | 0 | 0 | 0 |

**The only thing that moved is the eight new verdicts,** and neither run has saved replies
for them, so the replay reports them as `diverged` rather than inventing an answer. Their
mechanical rules still give good pass and bad fail on all four pairs. That is why 000050
goes from pass to fail: not a regression. The F2-01 row is `newly_passing` on both sides
because of the label scoring in #170. 000048's F2-02 failure is the saved "exposes only
two parallel outputs" stop, and its calibration failure is the old row-splitting one.
The saved real drafts that reach the new stage check pass it.

**New cases do not appear by default.** Replay runs the case IDs a run saved. Asking for
them with `--cases 1,2,3,4,5` gives F2-03, F2-04 and F2-05 as `replay_diverged`: "current
call analysis; saved no further saved reply".

## Real engine

`python -m tools.draft_trials.family_two --output <fresh>`: **pass**. 120 engine start
attempts in controlled forward and reverse orders: 104 finished and 16 refused at startup,
all expected. Two orders are not exhaustive proof.

| Request | Variant | Show output (both orders) |
|---|---|---|
| F2-03 | plain | `Slow: Slow result\nUpper: MIXED CASE\nLower: mixed case` |
| F2-03 | changed | `Slow: Other\nUpper: ÜNÏ CODE\nLower: ünï code` |
| F2-04 | plain | `Ready`, then `File: Source text\nStatus: Ready` |
| F2-04 | changed | `Ready`, then `File: Other text\nStatus: Ready` |
| F2-05 | yes | `Note: Hello\nDecision: Approved` |
| F2-05 | no, not-exact, capital | `Note: Hello\nDecision: Needs review` |

F2-01 and F2-02 are unchanged from the Stage 1 audit. Also checked on every run: one
Merge completion, F2-03 continues as the slow path, F2-04's Ready starts after the read
is done.

| Pair | Good | Bad, rules | Bad, engine |
|---|---|---|---|
| 1 `collect_vs_pick_one` | correct | fail | finishes, wrong output |
| 2 `handoff_vs_lost_child` | correct | fail | finishes, wrong output |
| 3 `either_or_vs_escape` | correct | fail | refused at startup |
| 4 `gate_vs_impossible_wait` | correct | fail | refused at startup |
| 5 `same_slot_list_vs_overwrite` | correct | fail | finishes, wrong output |
| 6 `join_vs_shared_end` | correct | fail | finishes, wrong output |

Controls pass: `independent_side_end` now passes as a draft and runs; `standalone_merge`
runs but is refused as a draft; `second_merge_same_group` and `control_back_edge` are
refused at startup; `shared_vault_replacement_unordered` is scored as a failure.

A mock `--case-set all` run passes through the full designer graph: 10/10, 10/10, 4/4,
5/5, with 73 fixture runs and 157 mock calls.

## Sizes

[Full figures](admission.json). Nothing is near a cap.

| What | Characters | Cap |
|---|---:|---:|
| Seventeen-type Brief / Compact contracts | 10,340 / 32,591 | 50,000 contracts |
| Selected snapshot, largest (F2-05) | 16,913 | 50,000 (40,000 planning) |
| Draft prompt, frozen / Stage 1 / Stage 2 | 1,762 / 2,492 / 3,438 | none of its own |
| Analysis prompt, frozen / Stage 1 / Stage 2 | 4,669 / 4,915 / 5,136 | none of its own |
| Judge prompt | 2,883, unchanged | none of its own |
| Largest actual call, F2-03 / F2-04 / F2-05 (judge) | 21,892 / 22,284 / 23,850 | 100,000 context |

The judge's report stays in words: 369 to 668 characters of the 6,486 to 9,389 the full
check report holds, for the five good drafts. It has no raw analysis.

## Where the plan and merged code disagree

The code won in every case.

1. **Replay of new cases.** The task expected new cases to show as `diverged`. By default
   they are absent, because replay runs saved case IDs. Only the new pair verdicts diverge.
2. **Plan F2-04 wording.** The plan says store the text as `ready_text`; the proposal
   removed that and the code follows the proposal.
3. **Same-slot list.** The plan calls it a pending owner choice and pair 5 pending. The owner
   approved it, and the proposal and code have it active.
4. **Pairs and requests.** The plan has five pairs and F2-06; the proposal and code have
   six pairs and no F2-06.
5. **One Merge.** See the choice above. Stage 1 was stricter than the plan.
6. **Merge record text.** The plan's draft record said "Drafts require a split and at most
   one Merge per group". The merged record does not; the drafter learns it from the prompt
   and the check.

## Known limit: refusals from the shared check are not plain at the top

When the shared check refuses, the error's top message is generic, for example "Check
this node's configuration: merge required path escape." The plain words are there, but
inside `details.flow_analysis.findings`, among roughly 9,000 characters of raw analysis
that the one redraft receives. The stage check's own refusals are plain at the top. This
is in `meta_workflow.problem_report` and how a blocked draft is reported, which is being
changed elsewhere, so it is left alone here.

## What the paid run should watch

1. **Calibration could stop the batch.** The judge prompt is unchanged and now reviews
   Wait Until, nested joins, either-or and list shapes. A false pass on any new pair fails
   calibration, which blocks all cases. Pair 5 bad, a list shown as one value, is the most
   likely.
2. **Analysis must declare the roles.** If F2-04 lacks `wait_for_step`, or F2-03 to F2-05
   lack `join`, the draft is refused as "unselected" and the redraft cannot fix that. Check
   `selection.roles` on any failure.
3. **F2-04.** Watch the Show label on Ready, the target being the reader, and Ready
   appearing first. A draft that holds the Show after the Merge fails the fixture.
4. **F2-03.** A second Merge for the inner split is the likely mistake, and it gets the
   generic message above. Count `draft_retry` and read `first_check_error`.
5. **F2-05.** Conditional's default `contains` fails `not-exact`. A Show used to make the
   message prints an extra output and fails, so the guidance about blank labels could
   nudge towards that; Concat is the clean form.
6. **Possible scorer false failures.** A correct draft using a node outside the evaluator's
   local list fails rather than asking for review, as at Stage 1.
7. **Target runs use real timing,** not the controlled orders above.
8. **Sets 1–3.** Any movement there is model variation or an existing issue, not this
   admission.
9. **Cost.** 17 more calls than Stage 1 (9 case, 8 judge) plus any redrafts, a larger
   contract block and a longer draft prompt. Not measured.
