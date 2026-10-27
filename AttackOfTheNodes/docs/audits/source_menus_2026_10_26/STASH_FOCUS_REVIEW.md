# PR #124 P2 · Stash field ownership

[Review](https://github.com/makinster/node_workflow/pull/124#issuecomment-6431769219)
on `28fa003`: Question → S → Model override → P could replace Question.
The nested picker did not update the remembered `field-*` target. Unrelated
controls could retain it too.

The owner chose focus-only insertion on 2026-10-26. **All Selects and model
pickers refuse with “Stash text can't go into this field”.** This includes the
model picker's text fallback. No model selection is pasted into another field.

| Path | Behaviour |
|---|---|
| Node Config text/file field | Capture the exact focused widget; insert only there |
| Node Config Insert button | Refuse; no remembered target |
| Node Config Select, implicit enum, Vault/secret picker, topology control | Refuse; no redirect to a configured value or previously focused field |
| Model override, working or fallback | Refuse; Question and Context stay unchanged |
| Options, including default model | Refuse; no Stash assignment contract or fall-through to a node behind the modal |
| Expanded native Select | The central Select adapter routes P to the active screen guard; otherwise it gives the same refusal |
| Start Default / Context Pack Text editor | Stash requires focus on Default / Text, including callback ownership |
| Subworkflow binding | Activate the binding button with E/Enter; P refuses text insertion |
| Subworkflow result / Return End editor | Refuse Stash text |
| Full text editor | Require focus on the text area; buttons cannot insert into it |

A delayed reply to Node Config is discarded if focus changed or the originating
widget was removed/replaced. The ordinary text/file insertion and Replace
confirmation paths remain tested. Typing P in active text edit mode remains
ordinary text input.

The former Source-selector shortcut intentionally filled another field. It is
retired by this owner instruction: choose Configured first, then focus its value
and press P. Two old tests were rewritten to assert refusal; the explicit Insert button
now also refuses instead of targeting another field.

## Evidence

- **Five tests fail on `28fa003`**: real Stash + Replace at 80×24 and 120×40,
  for both successful discovery and fallback, plus unrelated-control focus.
- The general test renders every registered schema Select, including nested
  row schemas, implicit string enums, Vault/secret keys and a topology control.
  P cannot change the focused selector or any neighbouring form value.
- Actual custom row editors test closed/expanded Selects and neighbouring text
  fields. Positive text/file/binding tests preserve the intended insertion paths.
- Options is tested both alone and above a node with a primed Question target.
  Delayed replies and two-field text insertion have separate checks.
- Before the final broad run: **237 focused tests passed**, **64 dialog/text
  tests passed**, **104 keymap tests passed**, and the final four row-editor
  cases passed. These overlap; do not sum them. The full-suite result is in
  [verification](verification.json) and the [loop case](../../delivery_tests/source-menu-audit.json).
- **3032 passed in 633.99 seconds** in the full suite; no WaitUntil retry.
  Compilation, helper UI, artifact/schema, consolidation and whitespace checks pass.

The original screen captures are retained at `28fa003`; their source hashes
are checked against that revision. This behavioural fix uses the regression
evidence above.

First review round on `28fa003`: one P2. Builder checks are not an independent
re-check; reviewer confirmation and owner merge remain pending. No generation,
live settings or workflow changes. The original five source-discovery findings
remain a separate, dated audit.

## Re-check on f360e8a

The [second review](https://github.com/makinster/node_workflow/pull/124#issuecomment-6432584941)
found another P2: after editing the Options URL, clicking a Select and closing
its menu, P could append `p` to the unfocused URL and Ctrl+S could save it.
The previous tests moved focus without entering edit mode; they missed the
shared key-rescue path.

The root fix removes printable-key rescue and the CommandInput/TextArea
focus-drift redirect. Typing policy and mode now use current focus only.
Node Config has no remembered Stash field, including its Insert button, and
no navigation rescue to an earlier editor. The full-text callback captures its
exact area and never focuses it after a refused/cancelled result. Subworkflow
binding selection is an explicit E/Enter action, separate from P text insertion.

`tests/test_stash_current_focus.py` uses real edit/key/click paths and production
CSS, including Options at 80×24 and 120×40. It checks closed/open Selects,
checkboxes, buttons, and another field after actual typing, with both clean and
already-unsaved drafts. Values, focus, dirty status, persisted workflow/settings
and the later Options Save must stay unchanged by P. The completed test file
has **13 failures and 3 passes on f360e8a in 22.69 seconds**; open-Select cases
already passed. Candidate verification is recorded in the linked JSON records.
**226 focused tests passed in 205.76 seconds**, covering Stash, keymaps and
long-text editing. The final full suite has **3048 passed in 674.42 seconds**,
with no WaitUntil retry. One earlier full attempt stopped for an embedded-screen
mode correction and an obsolete retained-editor expectation; those two focused
checks then passed. Compilation, artifact/schema, consolidation and whitespace
checks pass. Details are in the linked verification records.
Two review rounds, both with one P2; independent re-check and merge are pending.
