# Wait Until Configuration UI Plan

**Integration follow-up (2026-10-06):** File Output is now merged locally with
pending session fixes. Config preservation, critical input sizing, Chat zero
temperature, ambiguous window discovery, launch responsiveness, viewer request
queuing, Window Control's unsupported toggle and writer-path warnings are fixed.
Read [CONFIG_UI_BUILD_PLAN.md](CONFIG_UI_BUILD_PLAN.md) for remaining findings and
[current integrated evidence](audits/integrated_2026_10_06/README.md). Original
findings/counts below describe the earlier inspection, not the latest tree.

Proposed 2026-10-06 on `codex/wait-until-vault-fix`, based on main `7161ef2`.
Implemented 2026-10-06 in NodeConfigScreen. Wait and Connections tabs replace the
legacy fallback for this node. Mounted layout/navigation/save tests cover widths
60/100/140, unavailable targets, no targets and invalid timeouts. Target labels
use alias/type plus full stable ID; branch-path decoration and search are deferred.
Verification: focused suites 52 passed; full suite 445 passed in 63.03s;
node UI check, compileall, diff and local links passed.
Prior current-UI investigation below describes the replaced layout.
Owner contract: wait for configured targets, forward incoming dead-drop unchanged,
and let the downstream node explicitly read the newly available Vault data.

## Post-implementation audit follow-up

The configuration audit found production-CSS overflow: at 60 columns the timeout
input starts beyond the visible terminal. Existing bare-App tests do not load
that stylesheet. The focused control layout remains the intended design, but
visual completion is pending the shared form-sizing work (audit F03). See
[PENDING_CHANGES_REVIEW.md](PENDING_CHANGES_REVIEW.md) for current verification
and [NODE_CONFIG_UI_AUDIT.md](NODE_CONFIG_UI_AUDIT.md) for evidence.

## Current UI and defects

Mounted inspection of NodeConfigScreen confirmed four generic tabs:

| Tab | Current controls | Problem |
|---|---|---|
| Source | Alias, upstream reveal, Vault reads/list/reveal, wait targets | Vault reads suggest Wait Until fetches data, but it does not |
| Parameters | Timeout | Essential setting is separated from targets |
| Payloads | Upstream/Vault reveals, default output name/description, Vault writes/count/rows | Suggests configurable routing/publication absent from runtime |
| Connections | Read-only wiring | Useful; retain |

WaitUntilNode exposes only target_node_ids and timeout_seconds in its schema;
its execute waits, then forwards context.inputs[input] on default. The additional
controls come from legacy fallback composition in _compose_standard_config_tabs,
not from node capabilities. Saving also collects generic membank/transient values.
Current modal help says A/D tabs although numbered keys actually switch tabs.

## Implemented layout

Use two numbered tabs, following the existing command-navigation convention:

**1 - Wait** (initial tab):

1. Alias, using the existing activate-to-edit CommandInput.
2. Fixed explanation: “Wait for all selected nodes to complete, then forward
   the incoming dead-drop payload unchanged. The next node can read the Vault.”
3. “Wait for these nodes” SelectionList, with selected count. Show alias/type
   and shortened node ID; show an available editor branch/path label as secondary
   provenance to distinguish duplicate aliases. These are graph nodes, not
   supervisors or runtime branch IDs. Sort deterministically by label then ID.
4. Timeout seconds, default 0.0. Permanent note: “0 waits forever. A positive
   value limits the wait; reaching the limit produces an error.”
5. A compact read-only route: incoming node/port -> unchanged -> next node/port.
   This describes wiring, not a captured runtime value. Missing connections
   display “Not connected”; editing remains in the editor.

**2 - Connections**: the existing read-only connection summary. No editable
ports, Vault settings or payload fields. Keep Save and Cancel outside tab scroll.

Illustrative first tab:

```text
1 - Wait                         2 - Connections
Alias: [Wait Until]
Wait for all selected nodes, then forward the incoming
 dead-drop unchanged. The next node can read the Vault.
Wait for these nodes (1 selected)
[ ] LLM mood setter (node_0bb74ded)
[x] User Text Input  (node_d33abdff)
Timeout seconds: [0.0]
0 waits forever; a positive value limits the wait.
Incoming: LLM mood setter.default
Next: Chat Completion.prompt
[Save]
[Cancel]
```

The example illustrates the implemented field order, not a literal box layout. Keep target list scrolling independent/bounded so timeout and buttons
remain reachable at 60x24. At 100/140 columns use the same logical field order;
no horizontal form lanes are needed. Read-only descriptions do not take focus.
Do not add a filter for the first implementation; introduce search later only
if real graph size makes it necessary.

## Remove and preserve

Remove Vault read controls and selection, both Vault reveal controls, Vault
write controls/count/rows, transient output naming/description, routing toggles,
source selectors and both upstream runtime reveal blocks. The fixed forwarding
explanation and read-only wiring are sufficient. There is no separate Payloads
tab and no configurable source: Wait Until always receives the upstream payload.

Saving Wait Until should return alias plus actual runtime config (targets and
timeout), preserving unrelated existing config keys through the existing save
contract. Explicitly clear obsolete membank_inputs, membank_outputs and
transient_outputs for this node on Save, so the validator/editor does not keep
advertising Vault capabilities removed from the UI. Cancel must leave stored
config unchanged. Recompute derived input_sources through the existing save path;
do not leave a stale Vault read there. Do not clean other node types or mutate
saved workflow files simply by opening the dialog.

## Navigation

- Initial focus: alias in navigation mode, as in other config screens.
- 1/2 switches tabs in navigation mode; digits type normally during editing.
- W/S or up/down move alias -> target rows -> timeout -> Save -> Cancel.
- In the target list E/Enter toggles only the highlighted target. W/S moves
  through rows; up on first row leaves toward alias, down on last leaves toward
  timeout. Enter does not submit the whole dialog from the list.
- A/D follows within-row/caret behavior; it never switches tabs. While editing,
  letters remain text. Use the shared CommandScreenMixin and list handlers.
- Ctrl+S saves from either tab. Esc ends an active text edit first, then cancels
  the dialog; Ctrl+Q reverts an active edit first, then cancels using existing
  command-screen rules. Save/Cancel must not be trapped behind a long list.
- Remember highlighted target and tab scroll during tab changes. Scroll the
  selected row/field into view without losing the target check selections.
- Help/footer: “1/2 tabs | W/S move | E toggle/edit | Ctrl+S save | Esc cancel”.
  Editing-mode help should retain existing contextual end-edit/revert wording.

## Targets and edge cases

Continue excluding self and nodes downstream of Wait Until; they cannot satisfy
the gate before it passes. Keep eligible upstream/sibling nodes; do not restrict
the engine to different branches, infer target identity from aliases, or claim
all graph-reachable targets will actually execute under conditional routing.

Preserve saved target IDs even if absent or no longer eligible. Display them as
“Unavailable target” with a reason (missing/self/downstream), and permit explicit
removal. Never silently discard a saved target as the current selection helper
can do. Saving with such a target selected should show a clear correction message.
Any preflight validation change belongs to the backend validator, separately
from UI filtering; the frontend must not reinterpret runtime completion facts.

No selected targets preserves current pass-through semantics; show “No targets
selected: this node will continue immediately.” Do not auto-select all targets
or silently turn it into a blocking validation error. Timeout is nonnegative;
invalid numeric input must be explained before save, not silently coerced to 0.
Wait means all selected nodes have completed at least once in this run, after
publishing outputs. A target that never executes can wait indefinitely at zero;
state that in target-list help without introducing a new execution policy.

## Implementation plan

1. Add a focused _compose_wait_config_tabs path in NodeConfigScreen, beside
   existing structural branch/merge paths. Reuse alias row, generated timeout
   field, SelectionList, tab scroll, connections, buttons and command helpers.
   Keep timeout generated from schema; targets depend on graph topology and
   therefore belong in frontend composition.
2. Add a frontend target-row model preserving invalid selections, selected
   count and stable labels. Keep the stored list of node IDs unchanged in shape.
   Do not extend the runtime with UI branch labels or payload previews.
3. Gate generic save collectors for Wait Until, clear only retired presentation
   declarations on Save, and verify input_sources regeneration in the editor.
   Fix help copy for the proposed screen; generic A/D wording can be corrected
   as a small independent change if it affects all config screens.
4. Test mounted layout/navigation at 60/100/140 columns, including a long list,
   duplicate aliases, empty/invalid saved targets, edit-mode letter/digit input,
   target toggles, list-boundary exit, tab return, save and cancel. Assert removed
   controls are absent, returned runtime config is correct and obsolete Vault
   declarations no longer produce writer/read claims after Save.
5. Run relevant node-config and cross-branch execution suites, check_ui where
   applicable, compileall and full tests before delivery of the UI change.

Initial design verification used mounted control inventory and documentation
checks. Implementation verification is recorded in SESSION_LOG.md. The common
section policy is now documented in NODE_STANDARDS, UI_QUICK_REFERENCE,
AGENT_START_GUIDE, TUI_DESIGN and NODE_HELPER. Other node layouts are unchanged.
