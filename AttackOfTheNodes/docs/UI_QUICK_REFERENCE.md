# UI Quick Reference

Use this for quick frontend orientation. Open `TUI_DESIGN.md` only when changing
screen layout, command navigation internals, or detailed Textual behavior.

## Editor Keys

- `W/S` or up/down: move through visible rows.
- `A/D` or left/right: cycle all branch views, leaving error recovery out.
  With the highlight on a branch-select row, they instead step through that
  node's own branches, error recovery branches included (owner, 2026-10-14);
  `E` there opens the branch selector.
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
  show the hotkey as `N Label` (UX6; was `N - Label`).
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

Node configs share these section meanings (switch visible tabs with number keys):

- `1 Source`: alias, node summary, upstream/Vault preview controls, memory reads.
- `2 Parameters`: schema-generated fields.
- `3 Payloads`: payload preview controls, transient output overrides, Vault
  output declarations.
- `4 Connections`: one row per connection (Incoming, Outgoing) naming the
  node at the other end, both port names and what flows (the payload's name,
  or "No payload"), then Vault reads with the node that writes each key.
  Enter on a row opens that node's editor. Edit wiring from the editor.

## Node Config Saving (UX5)

- `Ctrl+S` (or `Ctrl+Enter`) saves and keeps the node editor open. While a
  text field or multi-line box is being edited it commits the text and leaves
  editing first; Enter in a multi-line box stays a newline.
- The Save button saves and closes.
- `Esc` (or the Close button, formerly Cancel) closes. With unsaved changes it asks **Save / Discard /
  Stay** first; Esc in that prompt means Stay. Jumping to another node from
  the Connections tab asks the same.
- "Unsaved" means the widgets differ from what the editor showed on opening
  or at the last save (the no-edit invariant from UX2).
- Ctrl+Space and F2 are not used: F2 is a media key on the owner's keyboard,
  and the owner chose Ctrl+S (2026-10-13).

Show only applicable sections; four tabs are not mandatory. Omit empty tabs and
controls for unsupported capabilities, number visible tabs consecutively, and
use a flat form when sufficient. Wait Until uses `1 Wait` for alias/targets/
timeout and `2 Connections` for read-only wiring. It has no Vault or payload
routing controls. Shared keyboard rules apply to every layout.

Ordinary nodes should not require custom frontend code. Use node metadata,
`config_schema`, `input_port_metadata`, `output_port_metadata`, and `ui_hints`.

Hide dependent options, labels, and empty-state messages until their enabling
toggle is selected. This applies to Vault read lists, Vault write fields, and
output fields made inapplicable by routing choices. Preserve their values when
hidden so toggling back restores the choices. For schema fields use
`visible_when`; reserve disabled styling for a genuinely locked control whose
state still needs explaining.
Any visible locked control needs an explicit explanation in the UI and a
documented convenience reason; prefer a read-only summary for inspection alone.
See [the visibility/scrolling audit](NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md) for
current retained displays and their purposes.

Open configuration on the first field of the initial tab. Initialization and
programmatic changes to other fields must not move the scroll position.
During navigation, scroll only as needed to keep the highlighted field visible;
do not scroll to reveal its next neighbour before it is highlighted.

## Node Names, IDs and Error Headings

- Nodes are shown by alias (or type name) everywhere: cards, Connections rows,
  pickers, prompts, Merge selectors (`frontend/node_labels.py`). The UX6
  numbered suffix for repeated names was rolled back (owner, 2026-10-14).
- The node ID is its own line: `Node ID: …` under the node editor's title and
  under `Name:` in the editor's details panel. Cards do not show it.
- Error and validation messages open with a plain line, then the ID:
  `Fetch (HTTP Request) · depth 1 · Main path` / `Node ID: node_…`
  (`frontend/node_location.py`; depth counts steps from Start, the branch is
  the Branch path the node sits on).
- Key hints: one ribbon per panel, at the bottom. A future `H` help popup will
  list every key for the current panel, and the ribbon will shrink to the
  basic movement keys plus `h help` (owner, 2026-10-14; not built yet).

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
  (`N Label`).
- There is no subcategory filter checkbox column. The rigid subcategory taxonomy
  was retired 2026-06-19; node `tags` survive only as freeform keywords that feed
  the string filter (see `NODE_STANDARDIZATION_HANDOFF.md` Revision 2026-06-19).
- Initial selector focus lands on the string filter (not in typing mode).
- `T` (2026-10-14) toggles between all nodes and only the nodes with an
  input that takes the upstream payload (`port_types.accepts_producers`,
  the C2 type rule). The title names the upstream (`Add Node · after Dice
  (number)`) and the ribbon shows `T fitting only` / `T show all`. The
  choice is remembered until the app closes. No upstream (nothing
  selected): no toggle. Typing `t` in the filter types a letter.
  Rule (owner, 2026-10-14): the filter uses only the shape of the upstream
  connection, never Vault contents (a large workflow's Vault holds every
  type, so it would filter nothing). A node that could read from the Vault
  instead is still hidden. Pass-through nodes are looked through to the
  producer; a Vault-seeded Branch path counts as its seed key's type,
  because that value is what the path carries.
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
