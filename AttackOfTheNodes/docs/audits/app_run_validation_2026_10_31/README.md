# App Run preflight — 2026-10-31

Base: `821688d461f17166d78ded5dd3fc182b708b929e` (merged #165).
No validator rule, backend startup, subworkflow or RunService behavior changed.
No paid/API calls, palette/admission changes or trial-harness edits.

## Run behavior

`action_run_workflow` materializes editor deletion stubs, then calls the existing
`validate_workflow` with the same workflow, factory and SecretsManager as manual
validation. On errors it stays in the editor (or returns there from a secondary
screen), opens the existing Validation panel and renders the same issue rows,
node markers and navigation. It does not save, clear prior run display state,
switch to execution or schedule startup. The user can repair and press Run again.
Warnings do not block. Successful preflight keeps the existing save/start path.

`EditorScreen.show_validation_result` is the shared display method for Run and
manual validation; it contains no checker. Normal backend startup still uses the
shared flow analysis as a safety net. The asynchronous App startup handler still
shows `Can't start: ...` for contract/flow refusals when called without preflight.
No second checker or alternate severity policy was introduced.

## Compatibility evidence

[bundled.json](bundled.json) records the existing **full validator** result for
all 17 authored graph objects in `examples/` and `docs/delivery_tests/`. It uses
an empty test Secrets store; no real keys are read. Spec node references are
translated with the existing authoring helper before checking actual graphs.
No bundled graph or saved workflow content was edited.

- **16/17 have no errors.** All valid examples and delivery graphs pass.
- The historical failed draft at
  `docs/delivery_tests/draft-a-workflow.json#/trial/draft_spec` has four
  `undeclared_port` errors: labels pasted into port IDs (`default/Greeting`, `default/Formatted output`, `input/Input`). This remains invalid, not a newly discovered false block.
- Missing local example files and absent Secrets produce warnings, not blocks.
  The owner's external library and actual credentials were not scanned.
- The app's actual normal starter initializer is exercised in a pilot: its
  one-Start workflow validates and runs.
- A warnings-only graph with an unreachable spare node validates and really
  runs through App Run, with the expected visible output.
- Real App Run scenarios write a previously absent Vault key before reading it:
  standard Start Vault write, Set Variable and Concat. All produce `seed`.
- Real App Run scenarios write a file that does not exist at preflight, then read
  it through Upstream, Vault or Configured. All read the newly created `seed`.
  Upstream/Vault ignore the unused blank Configured path; Configured produces
  only `file_not_found` until the writer runs.

The supported declared-Vault and runtime-file cases above are not blocked.
A separate [real-engine probe](implicit_output_log.json) found one compatibility
exception: `Start(seed) → Text Output → Text Output(Vault output_log,
{input[0]}) → End`. The first Text Output implicitly writes the internal
`output_log` key; raw execution produces `seed` twice with no errors, but the
validator reports `undeclared_vault_key` and App Run blocks the second run.
`MemoryBank.INTERNAL_KEYS` explicitly treats this key as bookkeeping, not a
publicly declared Vault output. **This existing check was left unchanged.**
Proposal for the owner: either support the log as an explicit reviewed contract
and declare its implicit writers through the shared Vault declarations, or keep
it internal and move these workflows to explicit named values (Set Variable or
Concat Vault writes). Do not blanket-whitelist a key that may not exist yet.

Invalid unreachable nodes are still errors under
the existing whole-workflow policy; Run now enforces that policy rather than
silently ignoring them. None of the checks was loosened or tightened.

Static validation cannot prove a file will exist when a reader executes, or
that a declared Vault writer will actually execute successfully before a reader.
Proposal: retain missing-on-disk as a warning and runtime file/required-input
checks as the final authority; keep blank required selections and keys without
any declared writer as errors. If ordering diagnostics are expanded later, use
the shared flow analysis to distinguish proven unsafe order from uncertain
cases. No new ordering rule is implemented here.

## Tests and receipts

`tests/test_app_run_validation.py` presses Run on real tombstone, two-Start and
escaping-route graphs, asserts no run/task/node events or execution screen, then
repairs each graph and runs again in the same app. It also covers warnings,
starter initialization, Vault/file runtime supply and invalid rerun from the
execution screen.

Existing tests updated:

- `test_merge_plan_integration::test_app_run_shows_refusal_and_can_run_after_repair`
  now expects the editor's Validation panel before repair; runtime assertions stay.
- `test_flow_startup_refusals::test_app_run_shows_escape_refusal` calls the
  asynchronous startup handler directly to retain real coverage of its
  `Can't start` safety-net display, independently of Run's preflight.

Source dependencies for Beacon/Merge/Wait are re-attested without changing their
claims. The 95-scenario real-engine flow receipt and generic claims receipt are
re-exported because their bound test/UI sources changed. This is a local source
recheck, not a new admission or independent human review.

Regenerate the bundle receipt from `AttackOfTheNodes/`:

```bash
AOTN_APP_VALIDATION_REPORT="$PWD/docs/audits/app_run_validation_2026_10_31/bundled.json" python -m pytest tests/test_app_run_compatibility.py -q
python -m pytest -n auto -q
```

Full suite: **5,147 passed, 187 skipped in 51.88 seconds**. Documentation links
and whitespace checks pass. No real API calls.
