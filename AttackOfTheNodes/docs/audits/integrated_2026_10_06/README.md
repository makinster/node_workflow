# Integrated configuration audit evidence — 2026-10-06

This is current-tree evidence after merging File Output and applying the focused
integration fixes. The earlier `node_config_2026_10_06/` and
`file_output_2026_10_06/` artifacts preserve historical before-fix evidence.

- 37 registered types, 34 selector-addable, 36 editable/user-facing screens.
- Internal tombstone intentionally not mounted; hidden Start/End included.
- 108 default production-CSS mounts at 60/100/140 × 24; all visible tabs visited.
- 306 alternate selector/checkbox states; no captured state errors.
- 36/36 Cancel checks leave stored data unchanged.
- 72/72 default save/reopen checks preserve unrelated configuration and have stable second saves.
- 115/115 mode/routing variant save/reopen checks; zero mismatches.
- Nine focused Wait Until/Text Output/Chat fields now fit the screen horizontally.
  Focused Chat provider probes preserve temperature 0.0; the remaining routing
  behavior is retained as diagnostic evidence.

See [INVENTORY.md](INVENTORY.md) for full current coverage and control inventory,
`evidence.json.gz` for raw default/state/roundtrip/selector metadata, `focused.json`
and focused text/SVG renders for critical-field geometry, and `summary.json`.

Run `verify_ui.py` from any directory with the authoritative venv. It reuses the
original capture helpers and packs a separate current baseline. Variant roundtrip
and focused probes were run by importing the historical modules with OUT set to
this directory; their raw results are retained here. Production CSS is explicit.
The verification logs are copied here after the checks finish.

Limits: synthetic owner-safe workflows, fixed 24-row height, headless mounts.
Not every multi-input combination has exhaustive key-by-key coverage. Real
Windows apps/monitor/window behavior and owner live appearance/accessibility
review are outstanding. Default typing/list navigation uses the capture methods
explained in the original audit. No owner workflows/settings were loaded.
