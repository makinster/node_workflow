# Family 2 review fixes — 2026-10-31

Started from current main `e7efdae` in `/home/makin/src/family-two-review-fixes`,
branch `codex/family-two-review-fixes`. Rebased onto main `784df48` when the
plain-refusal PR landed. No API or model calls. `flow_behaviors.py`, `validator.py`,
`branch_health.py`, palettes and draft guidance are unchanged by this work.

## Pause race

`_supervisors` contains only supervisors whose tasks have published registration.
Branch handoff already puts every prepared child in `RunContext.live_supervisors`
before scheduling any child. Pause, breakpoint pause and Resume now use that
complete registry. New supervisors inherit a current pause, including children
created by an already executing Branch after pause was requested. An in-flight
input/recovery state update cannot replace the master's PAUSED state.

The regression tests also exposed a second race: Resume resolves several waiters,
then one hits the next breakpoint before the other waiters get a turn. Supervisors
now recheck their current pause flag after waking, both between nodes and at a
breakpoint. Stop still wakes/cancels them; the existing breakpoint skip behavior
remains in place.

The real-engine tests cover outer Branch → nested Branch A and breakpoint B, with
A launching C/D. Both port/scheduling orders cover Resume, Stop and stepping from
B to the next breakpoint. A separate held Branch launches children during a manual
pause, then tests Resume and Stop in both orders. They assert no node starts while
PAUSED, no C/D/B execution before Resume, clean task/group teardown, and exactly
one Merge completion on resumed runs. These ten pause cases failed before the fix.

## Scorer false failure

The logical scorer previously required every active group worker to park at the
Merge. F2-01 plus a third path `Wait Until(join) → End` therefore failed as stuck,
even though shared analysis and the real engine accepted it. The scorer now takes
joining lineages from that Merge's analysis and waits only for their workers.
Prefix matching accounts for pending nested handoffs. Handed-off parents are
separate from finished workers: a required worker ending without its delivery
still blocks/fails. Independent workers keep their active-group membership when
the Merge's winner detaches. Evaluator policy is `family-2-evaluator-5`.

Both forward and reverse orders compare the positive example against real-engine
outputs and one Merge completion. Negative checks cover a required reader failing
before arrival in the real engine and scorer. A logical fault-injection test drops
a required delivery after analysis and verifies that the resulting end cannot be
mistaken for an independent path. Both positive cases failed before the fix.

## Picker timing

The picker dismisses first, then its async callback awaits two form updates before
setting the chosen name. A fixed 0.2-second delay could read the earlier name.
The affected test now waits, with bounded condition checks and Textual idle yields,
for the full picker, filtered count/preview, and returned screen with the chosen
name and workflow ID. No app bug was found and no frontend production code changed.

## Saved replay

Source: `/home/makin/draft-trial-01/runs/000048`. Each replay used
`python -m tools.draft_trials --replay <source> --case-set all --trial-root <fresh-root>`.

| Evidence | Set 1 | Set 2 | Set 3 | Set 4 | Overall |
|---|---:|---:|---:|---:|---|
| Original saved run | 10/10 | 10/10 | 3/4 | 1/2 | fail |
| Replay before this fix | 10/10 | 10/10 | 3/4 | 1/2 | fail |
| Replay after this fix | 10/10 | 10/10 | 3/4 | 1/2 | fail |

All 26 saved case outcomes match; none newly pass/fail or diverge. The source has
only two set-4 cases, so this does not claim saved-reply coverage for F2-03/04/05.
Calibration retains the saved false failure on the good
`helper_json_extra_fields_allowed` fixture. Current Stage 2 has eight calibration
replies absent from the saved run; replay marks all eight `replay_diverged` and
invents no replies. Both before/after replay calibration summaries are 64 unchanged,
zero newly passing/failing, eight diverged. The saved source had 64 calibration
rows; current replay has 72. These missing replies are not new scorer failures.
The new independent-waiter regression is demonstrated by the tests above rather
than a changed saved case outcome.

Fresh roots:

- Before: `/home/makin/draft-trial-review-before-20261031/runs/000001`.
- After initial fix: `/home/makin/draft-trial-review-after-20261031/runs/000001`.
- Final combined main: `/home/makin/draft-trial-review-final-20261031/runs/000001`.

## Verification and fingerprints

The initial full suite on `e7efdae` plus these changes passed **5,250 tests with
187 skipped**. On final combined main `784df48` plus these changes:

- Full `python -m pytest -n auto`: **5,255 passed, 187 skipped**, 71.81 seconds.
- New review regressions plus all subworkflow screen tests and the two receipt
  exporters: **35 passed** under `-n auto` before the main rebase.
- Picker test alone: **eight separate successful `-n auto` invocations**.
- `git diff --check` and local Markdown links in changed docs pass.

Generic and real-engine flow claims were re-exported and reviewed: observations
and claim outcomes are unchanged; only source hashes/runtime provenance moved.
Source-bound metadata fingerprints were refreshed without changing record text.
Pinned designer text and trial input fixtures are unchanged.
