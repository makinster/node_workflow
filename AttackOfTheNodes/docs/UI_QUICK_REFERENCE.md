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
- `W/S` and arrows move focus while in nav mode.
- `E` or Enter activates the highlighted control.
- Text fields require activation unless a prompt/filter opts into
  `auto_edit_on_focus=True`.
- `Esc`, Enter, and small-field Tab leave text editing while preserving typed
  text for Save.
- `Ctrl+Q` while editing reverts that field to its edit-start value.
- Selection lists must not trap movement: W/S or up/down should exit to the
  previous/next widget at list boundaries.

## Node Config Shape

Standard node configs use fixed tabs:

- `Source`: alias, node summary, upstream/Vault preview controls, memory reads.
- `Parameters`: schema-generated fields.
- `Payloads`: payload preview controls, transient output overrides, Vault
  output declarations.
- `Connections`: read-only connection summary.

Ordinary nodes should not require custom frontend code. Use node metadata,
`config_schema`, `input_port_metadata`, `output_port_metadata`, and `ui_hints`.

## Phase 17 Node Identity

Use `PHASE_17_NODE_VISUAL_IDENTITY.md` for the active plan.

- Selector family tabs: `Inputs`, `Flow Control`, `Outputs`, `Complex`.
- Subcategory filters are multi-tag metadata, not mutually exclusive families.
- Subcategory filters are checkboxes with `AND` behavior.
- Initial selector focus should land on the first subcategory control, not the
  string filter.
- The string filter should be activate-to-edit; `/` can jump to it.
- Editor rows may use two lines: alias first, family/subcategory identity
  second.
- Prefer an ASCII text-box border around the alias and family/subcategory text.
  Keep the depth column outside the box, render node interiors on the default
  background, and truncate long subcategory text with an ellipsis when needed.
- Between two ordinary node rows, show a centered non-focusable `↓` gap marker.
  Branch and merge jump widgets own that gap when present and should be
  centered under the node box.
- Details panel should show primary family and all subcategories.
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
