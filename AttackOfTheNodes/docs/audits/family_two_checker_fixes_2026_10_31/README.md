# Family 2 checker repairs — 2026-10-31

Branch `codex/family-two-checker-fixes`, started from main `e7efdae` in its own
worktree and rebased onto `784df48` (#175) before final verification. The original
checkout and owner workflows were not modified. No API/model requests were made;
redraft tests use in-process SDK fixtures. No admission, palette, guidance,
trial-tool, MasterState or Supervisor source changes.

## Behavior

- Control-loop findings no longer return before other checks. The bounded
  structural walk omits DFS feedback edges; dependency exports retain the full
  graph. Self/missing/downstream targets and independent mutual wait cycles
  remain checked. A disconnected loop cannot suppress unreachable/exclusive
  target findings. Guard/visit proofs downstream of a control cycle remain
  conservative, and a control-cycle SCC is not called an impossible completion
  cycle just because it is cyclic. Existing later-loop target execution passes.
  Merge with a control loop remains an error, alongside other applicable findings.
- The existing lineage walk checks actual nesting against `max_branch_depth`.
  Merge resets the lineage/depth budget before a later independent split.
  App Run, RunService validation and the check node pass their live setting;
  authoring accepts the same explicit limit. Legacy direct analyser/coordinator
  calls resolve the persisted limit once when none is supplied, without changing
  runtime files. Public setting changes persist through ConfigurationManager;
  the coordinator's runtime batch guard remains intact.
- A direct Text Output/Concat consumer rejects a literal `input[path_…]`
  lookup whose slot has no connection on its proved collecting Merge. Escaped
  braces, unproved expressions, standalone pass-through, alternate inputs,
  Text Output Vault selection and replacement prompts are not guessed at.
  Connected slots remain valid even if their values can be absent at runtime.
  Findings include a plain repair and reach the existing one structural redraft
  through #175's shared finding-message path and normal redaction/caps.
- Branch health and flow analysis share first-wire route extraction and the
  success/error exclusivity rule. A default route and recovering error route
  rejoining the same Merge slot are healthy; each alternative is still checked.

## Evidence

`tests/test_family_two_checker_fixes.py` covers the four original cases, normal
startup refusal without fixture MergePlans, effective live/persisted limits,
eight sequential groups at limit one, valid direct templates, runtime-missing
connected slots, real successful and recovering File Reader paths, and one
structural redraft for missing slots/over-depth drafts. All new run tests use
normal automatic plans. Existing explicit runtime guard fixtures stay unchanged.

Deliberate updates to existing expectations:

- `test_flow_behaviors.py`: loop findings retain first position while dependency
  exports and certain self-wait errors now remain visible.
- `test_merge_plan_integration.py`: six-level nesting at the default limit now
  refuses before any supervisor starts, rather than failing at the sixth Branch.
- `test_meta_nodes.py`: cancellation instrumentation forwards the new optional
  limit keyword; its no-publication assertions remain intact.

Flow claims now execute **104** source-bound real-engine scenarios (previously
95). Generic claims were also re-executed. Record prose/content hashes and input
source contracts are unchanged; affected source fingerprints and the check-node
execute pin are refreshed after local code/test rechecks. These are local
rechecks, not an independent human attestation or new family admission.

## Bundled graphs

[bundled.json](bundled.json) compares all **17** graph objects in `examples/`
and `docs/delivery_tests/` against isolated main `784df48`, with an empty secrets
store and no graph execution. **Nothing is newly refused.** Sixteen remain
error-free. The same historical rejected draft remains refused:
`docs/delivery_tests/draft-a-workflow.json`, `/trial/draft_spec`, four
`undeclared_port` errors. No owner workflow directory was scanned or rewritten.

## Verification

- Initial regression run: ten expected failures before implementation.
- Focused flow/wait/new regression checks: **100 passed**.
- Redraft/new regression/shared-refusal checks: **38 passed** before the last
  additional disconnected-loop regression.
- Final full `python -m pytest -n auto -q`: **5,282 passed / 187 skipped in 62.64 seconds**.
- `git diff --check`; documentation links checked locally.

Re-export receipts from `AttackOfTheNodes/` with the project interpreter:

```bash
AOTN_FLOW_CLAIMS_REPORT="$PWD/docs/audits/family_two_records_2026_10_31/claims.json" AOTN_CLAIMS_REPORT="$PWD/docs/audits/claims_baseline_2026_10_29/claims.json" python -m pytest tests/test_flow_claims.py tests/test_node_claims.py -k claims_receipt -q
python -m pytest -n auto -q
```

The bundled comparison extends the standard app-validation exporter with main's
before rows, changed checker source hashes and the explicit `newly_refused` list.
