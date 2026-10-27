# Source menus and installed-model pickers · 2026-10-26

Base `f0aa39d`, branch `codex/source-menu-audit`,
[PR #124](https://github.com/makinster/node_workflow/pull/124), implementation `3ac0168`. **Five mismatches fixed**
(shared defects, not five affected ports). Audited **56 registered types,
131 declared input ports**, including all 64 Merge slots, hidden/debug nodes,
and **31 standard-source ports**. No node execution contract was broadened.

[Complete per-port inventory](INVENTORY.md), [affected input rows](AFFECTED_PORTS.md), [reviewed machine contract](contracts.json),
[loop case](../../delivery_tests/source-menu-audit.json),
[screen contact sheet](contact-sheet.png).

## Mismatches

| Node · port | Accepts | Previously offered | Fix |
|---|---|---|---|
| File Reader · input; File Manager · file; Window Control · file; File Output · file_path | Vault file references from a dynamic writer (`any`) | Unknown Set Variable / Variable Setter writes became `string`; key and sometimes Vault itself disappeared | Preserve unknown writer types as `any`; retain runtime reference checks |
| Every typed standard input · see inventory | Any compatible eligible writer for a named key | Only the last writer's type counted; e.g. Context Pack text was hidden by Pick one details writing the same name | Keep types per writer; offer the key when an eligible writer matches; exclude self/downstream/deleted writer types |
| Every Vault reader · including Context Pack item rows and Branch selected reads | Subworkflow results routed to Vault/Both | Child result keys absent before a run; validator also lacked their declarations | Add child result routes to the shared Vault-write model (`any` until the child supplies a value) |
| Every standard input with multiple incoming edges · e.g. File Manager file | A compatible payload from any incoming path | An incompatible first parent hid Upstream even if another parent matched | Check every incoming connection; preserve type and publication checks |
| Every standard input with multiple incoming edges · same port | Node Config can inspect those supported paths | Duplicate incoming-summary widget IDs crashed the modal | Keep the first ID and suffix later summaries for that port |

Sources are still mutually exclusive per input. Availability rules remain:
unconnected/incompatible/nonpublishing upstream, empty compatible Vault, and
duplicate input use are hidden; a saved unavailable choice is retained and labelled.
The exact source-set comparison uses fixtures where every accepted source is
available independently. Optional `Not used`, session continuation, trigger
edges and contract-row defaults are modes, not extra standard data sources.

## Vault and type findings

- Standard primary **and secondary** outputs were already discovered correctly:
  Pick one details, Ask local model Run details, Ask Hermes details, investigation
  state, Find lines count, and Context Pack's Vault copy. Regression fixtures now
  enumerate every registered standard Vault output, rather than one example.
- Recall's selected Type resolves before filtering; Remember's dynamic output is
  `any`. Saved values are a separate store: use Recall to publish one downstream
  or to a Vault key; do not list every saved name as an existing run Vault value.
- Stash has **no persistent per-machine binding files** in the built product.
  Start's P action copies a default; CLI `@stash:` and Subworkflow's Stash source
  supply contract inputs. A Start row sent to Vault declares its typed key;
  Stash entries themselves are not Vault entries. See [the built contract](../../STASH_PROPOSAL.md).
- Compatible run-level entries from MemoryBank remain selectable. Legacy
  untagged persisted values retain text compatibility. Stale file references
  still require a live workflow declaration, as the delete/restore tests require.
- `any` may satisfy a text input; a known `var` list/record does not. Details are
  available to Context Pack/other `any` readers, not silently converted into
  valid Question text. Runtime shape/cap checks remain decisive. Read lines'
  coarse `any` port accepts an integer or a list of integers, not arbitrary data.
- Custom controls were checked too: Context Pack item sources; HTTP POST's
  config/input choice; Conditional's input/variable; Set Variable's input/literal;
  Subworkflow's typed mappings (including Stash); Return End's results; Branch
  seeds and Merge's structural input choice. Named-key free-text controls accept
  a key directly; they do not have a restricted key list to lose entries from.

## Proposals only

| Node · input | Proposed addition | Reason |
|---|---|---|
| Text Output · input | Configured text | Print a fixed message without an extra producer |
| Notify me · input | Configured text | Supply a literal value to `{input}`; its Message already supports fixed text |
| Record event · input | Configured text | Supply a literal value to the summary; a fixed Summary already works |
| Text Transform · input | Vault | Transform a named value without a Get Variable node |
| JSON Path · input | Vault | Extract directly from a named JSON value |
| Concat · input | Whole-input Vault choice | Choose what `{input}` means without rewriting the template; other Vault placeholders already work |

These are new input contracts, not missing supported options. None was built.

## Model pickers

Both controls reuse `LocalModelPicker`. The node starts with
`Options default (<current default>)`; the saved empty override still means
Options. The Options picker fills an empty draft when exactly one installed
model is listed. Save commits that draft; Cancel preserves the setting.
Multiple/zero installed models do not choose one. Existing names no longer
listed are retained with a `not installed` label.

Discovery uses only [GET /api/tags](https://docs.ollama.com/api/tags), a two-second
total deadline, a 1 MiB response cap, at most 1,024 entries, no redirects or
proxy discovery. Editing the Options URL refreshes the list after a short
pause; stale requests are cancelled. A failed/invalid catalogue produces an
editable text box and **Couldn't list models**. Discovery never pulls, loads,
generates, retries or changes a server. Execution still validates the chosen model.

## Verification

- On the original base, the five focused regression cases **all fail**:
  three hidden-key cases, fan-in availability, and fan-in modal mounting.
- On the candidate, the all-type contract check compares reviewed runtime
  acceptance, metadata, schema options and field visibility. Real forms cover
  all 31 standard ports; custom source menus are mounted too. A deliberately
  broken local-model Context schema (Vault removed) is caught by the same check.
  A separate unwrapped probe exits 1 with `context: offered sources`, proving
  that the checker itself fails, rather than only asserting an expected exception.
- The all-writer fixture covers compatible primary/secondary outputs, typed
  Start/Stash copies, Recall, dynamic writers, child results and run-level keys.
  Incompatible records and ineligible writer cases remain covered.
- Focused command: `pytest tests/test_source_menu_audit.py tests/test_local_model_picker.py tests/test_local_model_ui.py tests/test_payload_source_contract.py tests/test_deleted_vault_sources.py -q`: **125 passed**.
- Node helper, UI helper and compilation pass. Full suite: **3,016 passed in 516.49 seconds**; no WaitUntil retry needed.
  [Verification](verification.json) and the loop case retain the two earlier
  interrupted attempts, stopped for picker hardening rather than test failures. No generation calls were made for this run; pytest and captures use canned local HTTP.

To reproduce the original failures in this worktree without altering it, read
the five tests against base versions of `node_config.py` and `vault_declarations.py`.
The recorded experiment temporarily substituted those two base files, ran
`pytest tests/test_source_menu_audit.py -q -k 'regressions_hidden or fanin'`,
then restored both candidate files. Exit 1: five failed, 78 deselected.

## Screens

Real registered nodes, production `styles.tcss`, synthetic data, isolated
persistence, no executed workflows. Both SVG and PNG are retained.
`before-*` captures used base code; `after-*` use the candidate.
The base fan-in screen **could not mount**, so no honest before screenshot
exists for that case; the failing regression records the duplicate-ID exception.

| Case | Before | After |
|---|---|---|
| Dynamic file key / Source choice | [PNG](before-unknown.png) | [PNG](after-unknown.png) |
| Shared text/record key | [PNG](before-collision.png) | [PNG](after-collision.png) |
| Child Vault result | [PNG](before-child.png) | [PNG](after-child.png) |
| Fan-in source / summaries | Mount failed | [PNG](after-fanin.png) |
| Node model control | [PNG](before-node-picker.png) | [PNG](after-node-picker.png) |
| Options model control | [PNG](before-options-picker.png) | [PNG](after-options-picker.png) |
| Node / Options, server down | — | [Node](after-node-picker-down.png), [Options](after-options-picker-down.png) |
| Node / Options, 80×24 | — | [Node](after-node-picker-80.png), [Options](after-options-picker-80.png) |

[Capture harness](render_screens.py), [rasterizer](rasterize.py),
[before manifest](before-manifest.json), [after manifest](after-manifest.json).
The manifests record source/style hashes and HTTP methods/paths; every capture
request is a fake-server GET. Generated names are synthetic, not owner settings.
