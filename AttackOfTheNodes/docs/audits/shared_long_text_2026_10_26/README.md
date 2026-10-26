# Shared long-text editor — built screens

2026-10-26, own worktree `nw-shared-long-text`, branch
`codex/shared-long-text`, base `334cb67`. These are captures of the built
shared widgets on the real Node Config screen with production `styles.tcss`
and `colors.py` roles. There are no prototype overrides or application style
patches. The editor's existing text colour/left bar are unchanged.

| State | 80×24 | 120×40 |
|---|---|---|
| Ask Hermes previews | [PNG](node-previews-80x24.png) · [SVG](node-previews-80x24.svg) | [PNG](node-previews-120x40.png) · [SVG](node-previews-120x40.svg) |
| Long wrapping editor | [PNG](editor-wrapped-80x24.png) · [SVG](editor-wrapped-80x24.svg) | [PNG](editor-wrapped-120x40.png) · [SVG](editor-wrapped-120x40.svg) |
| Empty editor | [PNG](editor-empty-80x24.png) · [SVG](editor-empty-80x24.svg) | [PNG](editor-empty-120x40.png) · [SVG](editor-empty-120x40.svg) |
| Commands mode | [PNG](editor-commands-80x24.png) · [SVG](editor-commands-80x24.svg) | [PNG](editor-commands-120x40.png) · [SVG](editor-commands-120x40.svg) |
| Discard changes, Keep editing selected | [PNG](discard-confirm-80x24.png) · [SVG](discard-confirm-80x24.svg) | [PNG](discard-confirm-120x40.png) · [SVG](discard-confirm-120x40.svg) |
| Stash replace, Cancel selected | [PNG](replace-confirm-80x24.png) · [SVG](replace-confirm-80x24.svg) | [PNG](replace-confirm-120x40.png) · [SVG](replace-confirm-120x40.svg) |
| One unbroken line | [PNG](node-unbroken-80x24.png) · [SVG](node-unbroken-80x24.svg) | [PNG](node-unbroken-120x40.png) · [SVG](node-unbroken-120x40.svg) |
| Context Pack nested item editor | [PNG](nested-editor-80x24.png) · [SVG](nested-editor-80x24.svg) | [PNG](nested-editor-120x40.png) · [SVG](nested-editor-120x40.svg) |
| Text Output Template | [PNG](text-output-template-80x24.png) · [SVG](text-output-template-80x24.svg) | [PNG](text-output-template-120x40.png) · [SVG](text-output-template-120x40.svg) |

`render.py` uses temporary app data, synthetic text and a simulated Stash choice.
It does not save owner workflows, call a model or touch live configuration.
`manifest.json` records source hashes and terminal sizes. SVG captures retain
Textual's font declarations; PNG companions substitute DejaVu Sans Mono for
offline viewing (optional cairosvg dependency, not an app requirement).

Keyboard tests separately cover the real app and real Stash picker, field
versus node Save, Cancel, both Esc stages, Ctrl+Q, Keep/Discard, replacement and
cursor insertion, plain p, counts, full values, line endings, nested fields,
source visibility, disabled/read-only fields and live HIGHLIGHT selection.
These headless checks do not replace the owner's live terminal review.

Verification: **105 focused checks passed**, including 15 shared-editor cases;
Text Output helper **2 passed**, UI contract OK. Full suite **2,825 passed in
477.41 seconds**, with no WaitUntil retry needed. Compilation and whitespace
checks passed.

The captures/source hashes above describe build `4e75a62`. The later #121 P2
line-ending/history correction changes no layout or colours; its CRLF/CR/mixed
keyboard regressions are recorded in the newest Session Log entry.
