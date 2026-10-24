# Small wins — built screens, 2026-10-23

Real registered nodes, `NodeConfigScreen`, selector/editor and production
`styles.tcss`. Synthetic workflow and paths; no workflow execution, evidence
reads or model calls. [Contract and limits](../../SMALL_WINS.md).

- Check reply: [Parameters](check-parameters.svg), [80×24](check-parameters-80x24.svg),
  [row editor](check-row-editor-80x24.svg), [Payloads](check-payloads.svg),
  [forwarding](check-payloads-forwarding.svg), [selector](check-selector.svg).
  Reply is upstream from Ask Hermes; no configured Reply box.
- One extra Configured example: [preview](check-parameters-configured.svg),
  [full-screen editor at 80×24](check-text-editor-configured-80x24.svg).
- Read lines: [Around](read-parameters.svg), [range](read-parameters-range.svg),
  [80×24](read-parameters-80x24.svg), [Source](read-source.svg),
  [Payloads](read-payloads.svg), [forwarding](read-payloads-forwarding.svg),
  [selector](read-selector.svg).
- Find lines: [Parameters](find-parameters.svg), [80×24](find-parameters-80x24.svg),
  [Payloads](find-payloads.svg), [Match count Vault key](find-payloads-count.svg),
  [forwarding](find-payloads-forwarding.svg), [selector](find-selector.svg).
- [Example workflow](check-workflow.svg); [capture manifest](manifest.json).

The compact table keeps all three rows and Add field together at 80×24; Max
reply sits lower in the scrolling form. Payloads tabs scroll normally; the
second Find Vault key is below the initial 40-row viewport. Save/Close stay
visible. The mounted regression checks exact row heights, adjacency, actual
E/Enter/W/S/X keys, row edits/add/remove, cancel, Save and routing preservation.
The preview test covers full-screen Save/discard and both Stash modes.

Seven PNG previews were visually inspected after rendering the SVGs. Use
[render.py](render.py) with the intended interpreter to reproduce the SVGs;
it sets a temporary AOTN data directory before backend imports. Headless checks
do not replace owner live/native-platform review.
