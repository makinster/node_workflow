# Node configuration audit evidence

Read [the audit and plan](../../NODE_CONFIG_UI_AUDIT.md) first, then the
[complete mounted control inventory](INVENTORY.md).

Baseline: authoritative WSL checkout, `codex/wait-until-vault-fix` at `7161ef2`
plus preserved dirty runtime/Wait Until work, 2026-10-06. Python 3.14.4,
Textual 8.2.7. This is synthetic evidence, not captured owner workflows.

## Contents

- [capture.py](capture.py): mounts actual NodeConfigScreen and NodeSelectorScreen
  with production CSS, inventories every control/static block, changes choices,
  records shared navigation actions, and checks Save/reopen and Cancel.
- [probes.py](probes.py): capability discrepancies, invalid saves, populated
  Merge, Parallel Branch Vault seeds and representative production renders.
- [focused.py](focused.py): focused field regions/rendering, plus fake-provider
  Chat temperature/forwarding evidence. Never calls a real provider.
- [roundtrip.py](roundtrip.py): replays captured schema mode/routing changes,
  saves and reopens each (87 cases, all chosen values retained).
- [package.py](package.py): validates coverage and preservation observations,
  generates INVENTORY.md and packs raw synthetic intermediate JSON files.
- [evidence.json.gz](evidence.json.gz): compressed JSON object keyed by original
  evidence filename. Includes `metadata.json`, `selector.json`, `probes.json`,
  `focused.json`, `roundtrip.json` and `<node_type>_<width>.json` for 34 types × 3 widths.
- `render_*.txt` / `render_*.svg`: terminal strips and Textual exported renders
  for six representative nodes at all three widths.
- `focus_*.txt` / `focus_*.svg`: focused timeout/template/temperature fields at
  60/100/140 columns. These demonstrate clipping with actual application CSS.

Particularly useful receipts:

- [Wait Until timeout, 60 columns](focus_wait_until_node_60.txt)
- [Text Output template, 60 columns](focus_text_output_node_60.txt)
- [Chat temperature, 60 columns](focus_chat_completion_node_60.txt)
- [Text Output parameters, 60 columns](render_text_output_node_60.txt)
- [Wait Until, 140 columns](render_wait_until_node_140.txt)

SVGs preserve colors; terminal text strips expose visible content but cannot
establish contrast or screen-reader accessibility. Some captures taken soon
after a tab change can show a tab-underline animation in progress; conclusions
use active pane/widget state and focused geometry, not underline position.

## Reproduce

Run from `/home/makin/src/node_workflow/AttackOfTheNodes` using the authoritative
venv. Scripts use synthetic in-memory workflows and do not save owner settings.
They overwrite only their own evidence files in this directory.

```bash
/home/makin/src/node_workflow/.venv/bin/python docs/audits/node_config_2026_10_06/capture.py
/home/makin/src/node_workflow/.venv/bin/python docs/audits/node_config_2026_10_06/probes.py
/home/makin/src/node_workflow/.venv/bin/python docs/audits/node_config_2026_10_06/focused.py
/home/makin/src/node_workflow/.venv/bin/python docs/audits/node_config_2026_10_06/package.py
/home/makin/src/node_workflow/.venv/bin/python docs/audits/node_config_2026_10_06/roundtrip.py
/home/makin/src/node_workflow/.venv/bin/python docs/audits/node_config_2026_10_06/package.py
```

Synthetic IDs and unseeded random values vary on rerun. To inspect raw evidence:

```python
import gzip, json
with gzip.open("docs/audits/node_config_2026_10_06/evidence.json.gz", "rt") as f:
    data = json.load(f)
print(data["no_op_node_60.json"]["unrelated_preserved"])  # False on audit baseline
print(data["wait_until_node_60.json"]["unrelated_preserved"])  # True
```

The packaging assertions characterize current defects. They are audit integrity
checks, **not regression tests that future fixes should preserve**. Update the
baseline deliberately after implementation, or retain this directory as history.

## Actual checks

- 35 registered types; 32 addable types; 34 config screens inspected (Start and
  legacy End included, Tombstone intentionally excluded).
- 102 default width records, 68 reopen mounts, 278 alternate control states;
  no capture state exceptions. Production stylesheet used in every width record.
- 87 additional changed-mode/routing save/reopen cases retained selected values.
- 34/34 Cancel cases unchanged. Both default-save widths produced stable second
  saves and did not mutate the original until the caller applied the result.
- Unrelated config preserved only by Wait Until: 33/34 types lose the sentinel.
- Populated Merge and five-branch Vault-seed probes completed at all three widths.
- Mock-provider Chat probes confirm temperature 0→1 and document/prompt precedence.
- Existing focused suites: **232 passed in 55.27s** (command in main audit).
- Audit scripts compiled; package integrity and local Markdown links checked;
  `git diff --check` passed. No full application-suite rerun claimed.

Coverage limits: alternate states use one-factor changes, not all combinations;
schema-mode/routing round trips are covered separately, but not every text edit
or multi-control combination is saved/reopened. Navigation traces
invoke shared actions, with Pilot keys for alias typing and targeted list probes;
existing suites supply additional keyboard interactions. Live terminal,
screen-reader, all conditional save combinations and complete editor disk-save
round trips remain implementation verification gates described in the audit.
