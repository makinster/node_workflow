# Node configuration visibility and scrolling audit — 2026-10-06

Owner rule: hide controls and their labels/descriptions until their enabling
switch or source/mode makes them usable. A visible unavailable control needs a
specific convenience reason. Preserve entered values when temporarily hidden.
Open the initial tab on its first field and scroll only enough to reveal the
highlighted field. Initialization, other fields, and stale callbacks must not
move the viewport.

Audit the authoritative `/home/makin/src/node_workflow` tree with production
CSS and synthetic workflows. Include all 36 editable types (Start/End
compatibility types included); exclude only the intentional internal tombstone.
Evidence and the reproducible runner live in
[audits/toggle_scroll_2026_10_06](audits/toggle_scroll_2026_10_06/README.md).
Earlier audit evidence remains unchanged.

## Findings and repairs

| Finding | Result |
|---|---|
| Text Output prompt displayed while user input is off | Hide prompt, label, and description until `request_user_input` is enabled. |
| Set Variable literal value displayed while reading input | Hide the literal value unless its source is `literal`. |
| Conditional variable name displayed while testing input | Hide the variable name unless its left-value source is `variable`. |
| HTTP request body displayed for GET | Hide the body unless method is POST; update executable schema and helper spec together without regenerating custom execution. |
| Disabled legacy Write to Vault checkboxes on Set Variable and Variable Setter | Hide those checkboxes while pass-through disables them. They provide no useful interactive choice in that state. |
| Offscreen highlights in short Payloads viewports (Image Generation, then Conditional/Embedding at 60 columns) | Disable competing deferred focus-centering/reveal paths for Node Config navigation; use one minimal reveal after layout and ignore stale callbacks for another field. |

Earlier fixes were re-audited: Vault read lists and empty messages, Vault write
counts/rows, optional output key/description fields, downstream fields when
forwarding, Merge carry-forward selection, session-key and file-window fields,
source-gated parameters, and initial LLM focus/scrolling.

## Why some information remains visible

These are deliberate convenience displays, not disabled dropdown exceptions:

| Display | User benefit |
|---|---|
| Incoming payload summary and revealable read-only previews | Inspect or copy the value and its provenance without editing workflow data. |
| Connections tab | Inspect graph wiring even though wiring is not edited in this form. |
| Empty Vault message after enabling Vault reads | Explain why there are no selectable entries; hidden while Vault reads are off. |
| Variable Setter's literal/empty-input field while forwarding | It still determines the value written to the Vault. Forwarding changes only the downstream payload. |
| Text Output label/template while requesting input | They still format the eventual output; requesting input changes where the value comes from. |
| File Write format/mode while Open after write is off | They still control the file written to disk. Only window-dependent options are hidden. |

Keep future exceptions explicit: use explanatory read-only information where
possible, and document the concrete benefit of any visible locked control.
General disabled styling is not an explanation.

## Verification and limits

Final results: **108 mounts of 36 editable types** at 60/100/140 × 24,
**1,202 toggle/source states**, **4,008 navigation samples**, Cancel unchanged
**108/108**, and **zero** remaining scroll findings, generated visibility-rule
mismatches, or visible disabled selectors/checkboxes in the audited states.
The final full suite passed **589 tests in 92.82s**; 17 focused visibility/scroll
tests, HTTP's node helper (five focused tests), four affected-node UI helpers,
compilation, and `git diff --check` also passed. Counts overlap.

Details and per-type coverage are recorded in the evidence README and
SESSION_LOG. The runner checks default first focus/scroll, navigation in both
directions through every tab, toggles at all three widths, select/source variants
at 100 columns, generated visibility rules, non-focused checkbox changes,
visible disabled selectors, and Cancel preservation. Focused tests cover actual
keyboard toggles, edited-value retention, session/routing interactions, list
navigation, and short-viewport scroll stability.

The first rapid scan recorded transient geometry before Textual settled; those
are diagnostic candidates, not 226 separate confirmed defects. The settled
before scan confirmed one scroll defect and two visible disabled controls.
Semantic source inspection additionally found the four missing field rules.
The first three-width after scan then exposed two remaining short-viewport
failures; that intermediate evidence is retained separately from the final run.

This is headless WSL verification at 24 rows, with one-factor selector variants;
it is not exhaustive Cartesian coverage, native OS testing, or live accessibility
certification. Empty-tab cleanup, legacy Vault runtime-capability truth, simulated
AI controls, and unsupported window capabilities remain in CONFIG_UI_BUILD_PLAN.
No new runtime operations or platform integrations were added for this audit.
