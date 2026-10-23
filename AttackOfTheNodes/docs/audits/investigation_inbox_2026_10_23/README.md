# C3c built screens — 2026-10-23

Actual registered nodes and production `styles.tcss`/palette, captured in a
temporary data directory. No mock metadata, workflow execution, model calls,
Hermes job/config changes or live install. These supersede the design mockups
for the owner's simpler **no-tools analysis** v1. Existing multiline widgets
are used; the shared preview/editor proposal remains later work.

- [Request Parameters](request-parameters.svg), [80×24](request-parameters-80x24.svg)
- [Request Source](request-source.svg), [selector group](request-selector.svg)
- [Request Payloads](request-payloads.svg), [enabled Vault](request-payloads-enabled.svg), [forwarding](request-payloads-forwarding.svg), [80×24](request-payloads-enabled-80x24.svg)
- [Result Parameters](result-parameters.svg), [80×24](result-parameters-80x24.svg)
- [Result Source](result-source.svg), [selector](result-selector.svg)
- [Result Payloads](result-payloads.svg), [enabled Vault](result-payloads-enabled.svg), [forwarding](result-payloads-forwarding.svg), [80×24](result-payloads-enabled-80x24.svg)
- [Options](request-options.svg)

[capture.py](capture.py) reproduces the 17 SVGs listed in [manifest.json](manifest.json).
Checks: real metadata, routing checkbox values, forwarding row visibility,
unchanged stored config during captures, visible Save/Close geometry.
[check_roundtrip.py](check_roundtrip.py) also passed actual-keypress forwarding
Save/reopen/Discard preservation for both nodes. Both
inputs use independent standard source pickers. State is Vault-only, for
Conditional; Finding remains the report. Headless captures do not replace
owner live/native-platform review.

PNG previews were rendered locally from the SVGs and visually inspected:
[request](request-parameters.png), [80×24](request-parameters-80x24.png),
[result Payloads](result-payloads-enabled.png), [selector](request-selector.png),
[Options](request-options.png). No image generation or style substitutions.
