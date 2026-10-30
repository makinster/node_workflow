# Palette selection machinery — 2026-10-29

Requested base: `ee0bca4` (#151); rebased onto `4775f5e` (#152) before
publication. Twelve admitted types, no new registered or drafter
node types. This implements milestone 1 part B of the accepted external
`agent_channel/palette-scaling-plan.md`, section 1 and owner choices.
No hosted calls, Secrets reads, target-palette expansion or live recall claim.

The existing requirements-analysis/resolve calls now return a separate
`selection` object: candidates name exact `type_id`, `requirement_ids`, a role
and a short reason; roles retain missing capabilities independently of the
candidates. Outcome requirements remain separate. Check reply validates these
identities and coverage references using the same function as the harness.
The soft target is 8–15 including support; simple requests are never padded.

The analysis receives all twelve eligible Brief records under family headings,
positive deterministic suggestions and implemented-but-unadmitted names clearly
marked as unproven hints for scope classification. Discovery freezes the
registry and original request hashes; selection checks them before publication
and records the frozen analysis and clarification hashes too. Positive matching
uses type/name, purpose/use_when, tags and the bounded reviewed synonym map;
`not_for` never produces a positive match. Families are presentation, not
capability boundaries. Brief JSON retains its existing schema.

`backend/palette_selection.py` owns the reviewed role-composition/support table.
Start/End are always included. Explicit `vault_state` requires Concat (its Vault
template reads/write capability); explicit `error_route` requires Text Output.
A true all-path `join` needs Merge, which is implemented but not admitted, so it
stops honestly. Parallel branching alone does not imply a join. Cross-run state
also stops as unadmitted. No dependency on every possible service helper is
inferred. Unknown compositions stop as missing/unproven capability rather than
certifying a keyword hit. Adding a role/alternative requires review and tests.

One deterministic expansion searches the entire reviewed catalogue with all
missing roles and the original request. It adds only a proven complete role
composition and refetches all Compact contracts. Still missing: an explicit
`selection_incomplete` error with missing roles, searches, expansion count and
not-admitted versus missing-capability status; no draft or success file. This
implementation expands before drafting, so no previous approval can survive an
expansion. There is no post-draft expansion loop. A drafter that still cannot
fulfill a role is instructed to stop honestly; it cannot silently substitute a
weaker outcome. The single existing structural repair remains separate.

Node catalogue adds `Exact IDs` and the v2 `Selected analysis` adapter. The
`type_ids_source` filter reads an upstream list, a Vault list, or the configured
`type_ids` multiselect (1–64 identities). Ordinary All/Filtered inputs remain
sequencing triggers. Exact lookup rejects unknown, duplicate, hidden and
unadmitted types. It sorts identities and returns every complete contract or a
size error, even if a registry projection unexpectedly loses an entry. No
substring matching, implicit deduplication or truncation applies to this mode.

The selected snapshot records identities, complete-contract hash, registry,
request, analysis, clarification, role coverage and the expansion search. Draft,
structural repair and judge all read the same Vault snapshot. Both structure
checks mechanically reject unselected types or a stale/mismatched snapshot.
The original fixed-query chain/inventory is deliberately retained as the
original-suite comparison baseline; it still asserts exact `PALETTE` equality.
Its output is replaced by the selected snapshot before any drafting call.
There is no additional ordinary inference call; local selection/expansion has
no call fee. Existing usage receipts, call/time/budget and unknown-cost guards
remain unchanged. A structural repair still incurs its existing extra call.

[Recall receipts](recall.json) measure all 20 frozen cases against their frozen
role alternatives, with candidate count, covered/missing roles and unnecessary
candidates separately from rule/behavior results. Unnecessary is a role-based
diagnostic, not proof a helper is useless. Status-only cases record the correct
status and no saved workflow. Canned candidates are transport test data; this
is not live retrieval quality evidence or held-out paraphrase evidence.

The deliberate [removed candidate](../../../tools/draft_trials/fixtures/removed_candidate.json)
retains a required `write_file` role while removing File Write. The real v2
runtime expands once, then passes with that type restored; a missing unproven
operation stops before drafting. Separate tests combine expansion with one
structural repair and prove there is no second repair. All twenty mocked cases
pass with unchanged call totals (77 set 1; 73 set 2, including 46 calibration
calls). All 23 calibration rule pairs retain their expected good/bad verdicts;
`calibration.json` is unchanged. Hosted judge reliability awaits owner trials.

[Measurements](measurements.json) distinguish characters and UTF-8 bytes.
At publication main (#152) versus this change, all-node Text Brief:
**14,603 → 14,687**; Compact: **53,317 → 53,146**. Brief JSON **18,233**
unchanged; Compact JSON **76,818 → 77,731**. The original requested #151 base
measured Text Brief 14,569 and Compact 53,217 (JSON 18,214 / 76,638); #152
added the now-declared numeric counter ports before this PR was published. Compact Text declares universal `node_error` once in the
header instead of repeating it on each entry; no error contract is removed.
The default 64k Text catalogue retains the existing headroom check. Full JSON
still needs an explicit larger cap, and never truncates to fit the default.

The fixed v2 bundle is **21,619 / 50,000** characters (base 21,513).
Selected snapshots including receipts are **6,096–13,184 / 50,000** characters
across the eighteen runnable cases, at most **26.4%** of that budget. Tests
check actual assembled ordinary mock prompts and worst-case bounded question
material against at least 20% headroom below the 100k Context cap. Characters,
bytes and output-token settings remain separate limits; mock token receipts do
not estimate serving costs.

Reviewed metadata text is unchanged. The shared Vault declaration changes are
limited to meta-node selection/snapshot reads; the twelve reviewed execution
claims were rechecked and their source attestations refreshed. Claims evidence
now binds the selection/catalogue helpers as dependencies. No new claim/code
conflict was found. Integrated #152 preserves all four owner-decided repairs
(Counter/Repeat Counter numeric ports, If Changed suppression and Window Control
unsupported policy). The refreshed baseline/claims receipt keeps those repairs,
adds the three changed meta-node source fingerprints and binds selection helpers.
All previous xfails now pass; no pending type is newly admitted by this work.

Verification: full `pytest -n auto`: **4,524 passed, 187 skipped, zero xfails**
in 42.71 seconds; `git diff --check` clean. The earlier parallel run exposed
one unrelated UI timing failure; its focused 15-test module and subsequent
full runs passed without a UI change. No real API calls.
