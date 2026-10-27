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
| Node Config Insert button | Use its immediately preceding eligible field; any intervening unsupported focus clears it |
| Node Config Select, implicit enum, Vault/secret picker, topology control | Refuse; no redirect to a configured value or previously focused field |
| Model override, working or fallback | Refuse; Question and Context stay unchanged |
| Options, including default model | Refuse; no Stash assignment contract or fall-through to a node behind the modal |
| Expanded native Select | The central Select adapter routes P to the active screen guard; otherwise it gives the same refusal |
| Start Default / Context Pack Text editor | Stash requires focus on Default / Text, including callback ownership |
| Subworkflow binding | Choose Stash as the source, then focus its compact entry control; selecting an entry changes that binding only |
| Subworkflow result / Return End editor | Refuse Stash text |
| Full text editor | Require focus on the text area; buttons cannot insert into it |

A delayed reply to Node Config is discarded if focus changed or the originating
widget was removed/replaced. The ordinary text/file insertion and Replace
confirmation paths remain tested. Typing P in active text edit mode remains
ordinary text input.

The former Source-selector shortcut intentionally filled another field. It is
retired by this owner instruction: choose Configured first, then focus its value
and press P. Two old tests were rewritten to assert refusal; positive file-field
insertion through the explicit button remains covered.

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

One review round on `28fa003`, one P2. Builder checks are not an independent
re-check; reviewer confirmation and owner merge remain pending. No generation,
live settings or workflow changes. The original five source-discovery findings
remain a separate, dated audit.
