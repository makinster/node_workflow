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
| Payloads, forwarding checked | 120×48 | [PNG](payloads-forwarding.png), [SVG](payloads-forwarding.svg) |
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

The standard **Forward incoming payload unchanged** checkbox replaces the
answer downstream with the original upstream payload. Checking it hides and
disables the node's own downstream name/description; unchecking it restores the answer.
Enabled Vault destinations still receive the answer and Pick details.
There is no Publish downstream payload checkbox on this node.

A code review of PRs #103–#112 checked the payload-name/storage-key distinction.
The relevant new outputs in #104, #109, #110 and #112 retain separate display
names and Vault keys; #110's Saved as is a persistent-store lookup name.
A related control inconsistency remains: #104's System nodes and #110's
Remember/Recall use Publish downstream payload rather than the forwarding
control used by #109 and the corrected Pick one. Those controls need a
separate consistency follow-up; this review did not run every older PR's UI.
