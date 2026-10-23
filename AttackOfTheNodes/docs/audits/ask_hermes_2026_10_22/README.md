# Ask Hermes: built screens

These captures use the registered `hermes_ask_node`, real Node Config,
selector, editor and Execution screens, and production `frontend/styles.tcss`.
Config paths are illustrative. No repository workflows were saved. The usage
screen is an actual isolated workflow run through a **fake subprocess worker**;
its answer and token counts are test data, not account measurements.
The installed Hermes is refused before inference; no compatible adapter is enabled.

| View | Size | Capture |
|---|---|---|
| Parameters | 100×36 | [SVG](parameters.svg), [PNG](parameters.png) |
| Parameters, timeout focused | 80×24 | [SVG](parameters-80x24.svg), [PNG](parameters-80x24.png) |
| Sources | 100×34 | [SVG](source.svg) |
| Payloads, both Vault outputs off | 120×40 | [SVG](payloads-default.svg) |
| Payloads, Vault keys enabled | 120×48 | [SVG](payloads-enabled.svg) |
| Standard forwarding checked | 120×48 | [SVG](payloads-forwarding.svg), [PNG](payloads-forwarding.png) |
| Run details key focused | 80×24 | [SVG](payloads-80x24.svg), [PNG](payloads-80x24.png) |
| Selector | 110×30 | [SVG](selector.svg) |
| Small workflow | 120×34 | [SVG](workflow.svg) |
| Usage with both Vault outputs off | 120×38 | [SVG](usage.svg), [PNG](usage.png) |

Reproduce with the shared interpreter from the app directory:

```bash
/home/makin/src/node_workflow/.venv/bin/python docs/audits/ask_hermes_2026_10_22/capture.py
/home/makin/src/node_workflow/.venv/bin/python docs/audits/ask_hermes_2026_10_22/capture_usage.py
```

Both scripts select a normal truecolor terminal and disposable data directories.
The config captures assert Save/Close geometry; generated UI checks exercise the
metadata contract. Screens at 80×24 scroll rather than claiming the whole form
fits. Parameters, compact Parameters, forwarding and usage PNGs were visually
inspected. PNGs render original SVGs through local headless Chrome with network
resolution disabled. [Source hashes](source-manifest.json) identify the built
node and production styles. The shared long-text preview/editor remains a
separate later proposal; today's actual multiline field is shown.

Verification and runtime limits: [Ask Hermes contract](../../integrations/ASK_HERMES.md)
and the dated [session log](../../SESSION_LOG.md).
