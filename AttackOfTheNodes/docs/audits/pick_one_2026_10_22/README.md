# Pick one: built-screen review

These are the registered `pick_one_node` and real Node Config, selector and
editor screens, using production `frontend/styles.tcss`. No prototype node,
provider call, API credential or repository workflow save is involved.

The capture script clears the review shell's `NO_COLOR=1` override and selects
a truecolor terminal before importing Textual. It uses the production palette
in `frontend/colors.py`: `TYPE` for data types and `PAYLOAD` for payload names.
No new palette or literal UI colours were added. PNGs are rendered from the
original Textual SVGs with CairoSVG in a temporary tooling environment.

| Screen | Size | Capture |
|---|---|---|
| Parameters, all fields | 100×66 | [PNG](parameters.png), [SVG](parameters.svg) |
| Parameters, scrolled to timeout | 80×24 | [PNG](parameters-80x24.png), [SVG](parameters-80x24.svg) |
| Source | 100×34 | [PNG](source.png), [SVG](source.svg) |
| Payloads, both Vault copies off | 120×40 | [PNG](payloads-default.png), [SVG](payloads-default.svg) |
| Payloads, independent keys enabled | 120×48 | [PNG](payloads-enabled.png), [SVG](payloads-enabled.svg) |
| Payloads, scrolled to details key | 80×24 | [PNG](payloads-80x24.png), [SVG](payloads-80x24.svg) |
| Complex selector | 110×30 | [PNG](selector.png), [SVG](selector.svg) |
| Plain answer into Conditional | 120×34 | [PNG](route-map.png), [SVG](route-map.svg) |

`capture.py` recreates the SVGs using the shared interpreter. Automated form
checks cover 80×24 and 120×40, keyboard edit/save, duplicate-answer refusal,
independent Vault destinations, reopen and Cancel. The compact captures assert
that Save and Close remain on screen; the status bar stays below them.

The form has no provider/model selector, configurable unsure answer, Stop
option or unsure error. Below the cutoff, the result is literal `unsure`.
Pick details starts disabled and has no downstream path or branch-name box.
