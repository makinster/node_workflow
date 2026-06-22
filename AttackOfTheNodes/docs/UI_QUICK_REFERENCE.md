# UI Quick Reference

Use this for quick frontend orientation. Open `TUI_DESIGN.md` only when changing
screen layout, command navigation internals, or detailed Textual behavior.

## Editor Keys

- `W/S` or up/down: move through visible rows.
- `A/D` or left/right: cycle all branch views.
- `Ctrl+A/D` or `Ctrl+left/right`: cycle incomplete branch views.
- `E` or Enter: edit selected node or activate highlighted selector row.
- `I`: insert after the highlighted row.
- `X` or Backspace: delete selected node or tombstone.
- `F`: File/workflow menu.
- `O`: options/settings.
- `H`: context help.
- `V`: validate workflow.
- `Ctrl+S`: quick save.
- `Ctrl+R`: execute workflow.
- `Ctrl+Q`: quit only from the editor.

`A` is not add-node. New nodes are introduced through insert/add flows driven by
the highlighted editor row.

## Command-Mode Rules

- Command-mode screens use `CommandScreenMixin`.
- `W/S` and up/down move line-by-line between rows; a multi-widget row (widgets
  stacked on one line) counts as a single line, and vertical moves preserve the
  horizontal column position where possible.
- `A/D` and left/right are within-row horizontal navigation: they move between
  widgets sharing a row and are a no-op on single-widget rows (the common
  single-column case, where the key falls through to caret movement on a
  focused text field).
- Tabbed command-mode screens (node config, node selector) switch tabs by
  **number key** (`1`–`5`): a digit jumps directly to the Nth tab. Past the tab
  count it is a no-op; while editing a field a digit types normally. Tab headers
  show the hotkey as `N - Label`.
- `E` or Enter activates the highlighted control; on a `Switch`/`Checkbox` it
  toggles the value in a single press.
- Text fields require activation unless a prompt/filter opts into
  `auto_edit_on_focus=True`.
- `Esc`, Enter, and small-field Tab leave text editing while preserving typed
  text for Save.
- `Ctrl+Q` while editing reverts that field to its edit-start value.
- Selection lists must not trap movement: W/S or up/down should exit to the
  previous/next widget at list boundaries.

## Node Config Shape

Standard node configs use fixed numbered tabs (switch with number keys):

- `1 - Source`: alias, node summary, upstream/Vault preview controls, memory reads.
- `2 - Parameters`: schema-generated fields.
- `3 - Payloads`: payload preview controls, transient output overrides, Vault
  output declarations.
- `4 - Connections`: read-only connection summary.

Ordinary nodes should not require custom frontend code. Use node metadata,
`config_schema`, `input_port_metadata`, `output_port_metadata`, and `ui_hints`.

## Phase 17 Node Identity

Use `PHASE_17_NODE_VISUAL_IDENTITY.md` for the active plan.

- Selector family tabs (2026-06-22): five tabs mapping 1:1 to the five backend
  families, in this order with hotkeys `1`–`5`: `In` (Inputs), `Flow Control`,
  `Utility`, `Out` (Outputs), `Complex`. The earlier combined `I/O` tab with an
  Input/Output segmented toggle is retired so Outputs (live UI-display nodes)
  has its own tab. `In`/`Out` are abbreviated display labels; `TAB_FAMILY` in
  `node_selector.py` maps them to the `Inputs`/`Outputs` `primary_family` values.
  See `IO_CONTRACT_UI_DESIGN.md`. The taxonomy-reconciliation follow-up is closed.
- Family tabs switch by number key (`1`–`5`) and show numbered headers
  (`N - Label`).
- There is no subcategory filter checkbox column. The rigid subcategory taxonomy
  was retired 2026-06-19; node `tags` survive only as freeform keywords that feed
  the string filter (see `NODE_STANDARDIZATION_HANDOFF.md` Revision 2026-06-19).
- Initial selector focus lands on the string filter (not in typing mode).
- The string filter is activate-to-edit; `/` can jump to it.
- Editor rows may use two lines: alias first, family identity second.
- Prefer an ASCII text-box border around the alias and family text. Keep the
  depth column outside the box, render node interiors on the default
  background, and truncate long text with an ellipsis when needed.
- Between two ordinary node rows, show a centered non-focusable `↓` gap marker.
  Branch and merge jump widgets own that gap when present and should be
  centered under the node box.
- Details panel should show the node's per-port I/O contract (see
  `NODE_STANDARDIZATION_HANDOFF.md` §8).
- Preserve selection, autoscroll, validation markers, breakpoint markers,
  execution state, and Merge Beacon state indicators.

## Current Style Language

- Graph-passed data is a dead-drop payload.
- Named memory-bank data is the Vault.
- `branch_end_node` is displayed to users as Merge Beacon.
- Branch v1 is always-parallel with 2-5 spawn points.
- A Merge Beacon's selector row and gutter color follow the branch containing
  the merge node it's connected to, not the beacon's own branch.
- A merge node's config only offers Merge Beacons whose branch starts upstream
  of (or unrelated to) that merge — never one downstream of it.

## Deep Reference

Use `TUI_DESIGN.md` for detailed screen descriptions, file picker behavior,
payload preview rules, learned Textual detours, and historical UI decisions.
