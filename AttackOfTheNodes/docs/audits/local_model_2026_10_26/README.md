# Ask local model · built screens, 2026-10-26

Actual registered `ask_local_model_node`, real Node Config/selector/Editor/
Options screens and unmodified production `frontend/styles.tcss`, base `27d16bc`.
No proposed node metadata or replacement widgets. Example facts are synthetic;
no workflow was executed or saved while capturing these views.

| View | PNG | SVG |
|---|---|---|
| Parameters / Question preview | [80×24](parameters-80x24.png), [110×38](parameters-110x38.png) | [80×24](parameters-80x24.svg), [110×38](parameters-110x38.svg) |
| JSON / thinking | [80×24](parameters-limits-80x24.png), [110×38](parameters-limits-110x38.png) | [80×24](parameters-limits-80x24.svg), [110×38](parameters-limits-110x38.svg) |
| Context / temperature / output tuning | [80×24](parameters-advanced-80x24.png) | [80×24](parameters-advanced-80x24.svg) |
| Configured Context | [110×38](parameters-configured-context-110x38.png) | [110×38](parameters-configured-context-110x38.svg) |
| Full-screen Question editor | [80×24](editor-80x24.png) | [80×24](editor-80x24.svg) |
| Payloads / forwarding | [80×24](payloads-80x24.png), [110×38](payloads-110x38.png) | [80×24](payloads-80x24.svg), [110×38](payloads-110x38.svg) |
| Run details Vault | [80×24](payloads-details-80x24.png) | [80×24](payloads-details-80x24.svg) |
| Source / incoming Context | [80×24](source-80x24.png), [110×38](source-110x38.png) | [80×24](source-80x24.svg), [110×38](source-110x38.svg) |
| Source selectors, scrolled | [80×24](source-inputs-80x24.png) | [80×24](source-inputs-80x24.svg) |
| Direct selector entry | [110×34](selector-110x34.png) | [110×34](selector-110x34.svg) |
| Context Pack → Ask local model (JSON) → Check reply → Notify me | [140×44](workflow-140x44.png) | [140×44](workflow-140x44.svg) |
| Options URL / default model | [80×24](options-80x24.png), [110×38](options-110x38.png) | [80×24](options-80x24.svg), [110×38](options-110x38.svg) |

[Contact sheet](contact-sheet.png). At 80×24 the standard form scrolls; separate
captures reveal the lower controls. Model selection is per machine, so the
shipped default-model field is blank; the node override is also blank.

[Capture harness](render_screens.py) uses a temporary data root before backend
imports. It never calls execute or HTTP. Save/Close geometry, unchanged draft
config, the actual long-text editor, default forwarding and Run details Vault
key were checked while capturing. The [manifest](manifest.json) records sizes
and source hashes. Run the harness with the shared venv, then [rasterize](rasterize.py)
for PNG copies (existing optional CairoSVG/Pillow rendering libraries, no new
runtime dependency). PNG font substitution changes no UI styling.

Visually inspected the principal Parameters, Payloads, Options and workflow
views and the contact sheet. Headless screenshots do not replace later owner
terminal/device review. Source-menu contract tests additionally mount eligible
upstream/secondary Vault writers so all three supported sources can be compared
with metadata/runtime acceptance; these views retain normal availability pruning.

[Contract](../../integrations/LOCAL_MODEL.md),
[delivery record with smoke numbers](../../delivery_tests/ask-local-model.json).
