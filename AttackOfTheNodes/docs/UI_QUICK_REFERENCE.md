# UI Quick Reference

Use this as the keyboard and interaction reference. [Contributing](CONTRIBUTING.md)
owns implementation/testing patterns; [Architecture](ARCHITECTURE.md) owns
execution semantics. [Current State](CURRENT_STATE.md) separates delivered and
pending work. Historical layouts are in `archive/TUI_DESIGN.md`.

Every window has a primary button for its Enter action, plus Close or Cancel; the Stash never stashes the same file or text twice.

Editor and Execution Help and compact hints come from the keymap profiles.
In Help, W/S or up/down scrolls the text; E/Enter closes it. Close stays visible.

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
- `P`: Stash screen (paste or drop paths and text; manage entries).
- `B`: toggle the selected node breakpoint; `Ctrl+B`: clear breakpoints.
- `Z`: undo deletion.
- Tab / Shift+Tab: move between panels.
- `H` or `?`: context help.
- `V`: open or close the Validation panel (top of the right pane). Its
  **Run validation** button (or `R`) checks the workflow; the last run's
  issues follow, errors first, one line each (`✗` error, `!` warning, node,
  message). `W`/`S` move, `E`/Enter on an issue goes to its node: the panel
  hides, the node is highlighted and the hint bar shows the full message
  until you move. `Esc` also closes the panel. Warning badges on the map
  reflect that last run, not continuous validation.
- `Ctrl+S`: quick save.
- `Ctrl+R`: execute workflow.
- `Ctrl+Q`: quit only from the editor.

`A` is not add-node. New nodes are introduced through insert/add flows driven by
the highlighted editor row.

## Deleting and recovering paths

Branch and Conditional first delete: pick one path to keep, then Delete.
Space/E toggles, W/S moves, Enter applies, Esc/Ctrl+Q cancels; Enter on Cancel
cancels. Shared nodes stay. Z on the deleted group restores its members, with a
preview before restoring what fits if the graph changed. Removing the stub
asks before discarding its stored nodes permanently.

Lowering a Branch's count asks which old paths to keep (exactly the new count).
Removed paths stay under **Saved paths**, never run and survive save/reload.
E opens that row; X asks before discarding it. Raising the count offers
**Recover**, **Leave empty** or **Cancel**. If needed, the recovery picker allows
zero through the number of new ports; unpicked paths stay saved. Cancel returns
to the unsaved config draft. Callable workflows show ` [sub]` in the header.

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
- `Esc` ends text editing and preserves text. In a single-line field Enter
  and Tab also finish editing; Enter remains a newline in CommandTextArea.
  `Ctrl+Enter` ends multiline editing (a screen may use it to submit/save).
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
- Number fields (C5): a value that is not a number, not finite or out of
  range blocks the save; the problem shows in red under the field, the
  typed text stays and the field gets focus. Blank saves the default.
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
See [the visibility/scrolling audit](archive/NODE_CONFIG_VISIBILITY_SCROLL_AUDIT.md) for
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

The selector uses portable metadata; [Node Standards](NODE_STANDARDS.md) owns
the identity and contract rules. Older Phase 17 layouts are historical.

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
  the string filter (see Node Standards: Portable contract and authoring boundaries).
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
  Node Standards: Portable contract and authoring boundaries).
- Preserve selection, autoscroll, validation markers, breakpoint markers,
  execution state, and Merge Beacon state indicators.

## Current Style Language

- Graph-passed data is a dead-drop payload.
- Named memory-bank data is the Vault.
- `branch_end_node` is displayed to users as Merge Beacon.
- Parallel Branch has 2–64 paths; Merge defaults to five slots and can grow.
  Branch width and the runtime nesting-depth limit are separate.
- A Merge Beacon's selector row and gutter color follow the branch containing
  the merge node it's connected to, not the beacon's own branch.
- A merge node's config only offers Merge Beacons whose branch starts upstream
  of (or unrelated to) that merge — never one downstream of it.

## Colours

One meaning, one colour (owner, 2026-10-20). Code uses the names in
`frontend/colors.py`, never colour literals (`tests/test_colors.py` checks).
Colour is never the only signal: statuses keep their marks.

| Name | Colour | Use for | Example |
|---|---|---|---|
| (normal) | theme text | Messages and headings (bold) | **Inputs**, "Choose a subworkflow" |
| `MUTED` | #A0A6B0 grey | Hints, descriptions, ids, "nothing yet", separators | `e/enter  open it`, `(none)` |
| `TYPE` | #4EC9B0 teal | Data types only | `[string]` |
| `SOURCE` | #9CDCFE light blue | Where a value comes from or goes | `Vault key "count"`, `next node`, `S2B1 Keep` |
| `NAME` | #E8E8E8 bold | Node names and aliases | **Greet**, **Greeter** |
| `PAYLOAD` | #D7A3D3 lilac | Input and payload names | `who`, `greeted` |
| `KEY` | #DCDCAA pale yellow | Vault key names | the `"count"` in `Vault key "count"` |
| `VALUE` | #E0A383 soft orange | Literal values | `"Kim"`, `2` |
| `SUCCESS` | #5FD068 green | Done, saved, finished | `✓ done` |
| `RUNNING` | #56C8D8 cyan | Running now | `▶ running` |
| `WARNING` | #E5C07B amber | Waiting for you, warnings, "may ask" | `⏸ waiting for you`, `⚠` |
| `ERROR` | #F48A90 red | Errors and failures | `✗ Unexpected failure` |
| `HIGHLIGHT` | #1a3a5c background | The highlighted row or card: one solid colour over the whole row, plain text on it | |
| `MAP_BACKGROUND` | #101418 background | Map rows behind the cards | |
| `BRANCH_PATHS` | ten path colours | A Branch path's gutter and label, in path order | |

Every colour is a fixed hex value, so it looks the same in every terminal
(named colours such as "green" are redrawn by each terminal's own theme).
The values live in `colors.PALETTES` (one palette per theme; `dark` today)
and `colors.use(name)` switches them. Each text colour must reach 4.5:1
contrast on the map, panel and highlight backgrounds; the test checks this,
so a new palette can't ship an unreadable colour. Code that should follow a
palette switch reads `colors.NAME` when it draws.

In `styles.tcss` use Textual's variables with the same meanings:
`$text-muted` (MUTED), `$success`, `$warning`, `$error`, `$accent` for
focus borders.

## Execution screen

The run is shown on the editor's map; each card's second line says how that
node is doing. The right pane shows the highlighted node (what it received,
sent and saved to the Vault). When a node needs a recovery choice, the error
panel opens at the top of the right pane.

| Key | Action |
|---|---|
| W/S or ↑/↓ | Move the highlight (stops following the run) |
| A/D or ←/→ | Show another path at the branch above the highlight |
| F | Follow the running node again |
| V | Hide / show the error panel (the branch still waits for a choice) |
| P | Pause/resume the whole run, subworkflows included |
| X / Shift+X | Stop (moved from S on 2026-10-19) |
| M | Vault log: Time, Key, Type, Value, Source (`S3B2 Save note`); E opens an entry, A/D its earlier/later writes, / filters |
| O | Run output viewer |
| E / Enter | On a running Subworkflow card: open that subworkflow's run (4c-2). Elsewhere E shows the latest run error details |
| Esc / Ctrl+Q | Return to editor, stopping a live run. Inside a subworkflow, Esc goes back one level and stops nothing |

Inside a subworkflow the title is a breadcrumb (`Fetch report › Greet ›
Greeter`); a long one keeps the first name, "…" and the last names, with the
level. A calling card reads "⏸ waiting for you" when its subworkflow waits.
A finished call can't be opened; its results show on the calling node. A
prompt says who asks and from where ("Greeter asks", "From Fetch report ›
Greet › Greeter › Ask name").

The error panel's buttons: Retry, Skip, Stop branch, Go to node (hides the
panel and highlights the failed node, switching paths if needed), Stop run,
Details. Under 80 columns the details sit below the map.

## Library, prompts and viewers

| Screen | Keys beyond shared navigation |
|---|---|
| Subworkflow node (Node Config) | 1 Inputs / 2 Payloads / 3 Connections. Change (on the Subworkflow row) opens the picker: type to search, W/S move, E choose. E on an input row: Value comes from Typed value / The incoming payload / Vault key / Stash entry / Its default; P picks the Stash entry (saved by name; `✗ no such Stash entry` in the row when it is gone, a validation error). E on a payload row: Goes to Next node / Vault / Both (blank key: the payload's name). |
| Workflow library | 1/2 Workflows / Subworkflows tab; W/S or arrows move; E/Enter opens; N new (a subworkflow on tab 2); C copies a workflow to Subworkflows (tab 1); R rename; D duplicate; I import; O export; X delete; ? key list; Esc/Q/Ctrl+Q close |
| New/rename name prompt | Enter or Ctrl+S confirms; Ctrl+Enter also submits; Esc cancels |
| User Text Input | Ordinary text editing starts on mount; W/S type letters. Ctrl+Enter submits; Esc/Ctrl+Q first leave editing, then cancel |
| Typed import/export path | Ctrl+Enter submits; B retries Browse when available and not typing; Tab moves out; Esc/Ctrl+Q cancel after edit mode |
| Settings | 1 General, 2 Secrets; Ctrl+S saves; X deletes selected secret when applicable; Esc/Ctrl+Q cancel after edit mode |
| Group picker | W/S or arrows move; E/Enter adds; Esc/Ctrl+Q returns to selector |
| Branch selector | W/S or arrows move; E/Enter (also D) chooses; Esc/Ctrl+Q cancels |
| Memory viewer | W/S or arrows move; E/Enter activates; Esc/Ctrl+Q closes |
| Output, file, help and error viewers | Esc/Q/Ctrl+Q closes, subject to recovery rules in the error dialog |

The selector uses Tab to focus its list and `/` to focus its filter. Screen
commands must not consume letters/digits while a text field is editing.

## Stash screen (S2)

Merged in #71. P in the editor opens the Paste / drop tab; E there types again.

| Context | Controls |
|---|---|
| 1 Paste / drop | Paste/drop adds immediately; Enter/Add stores typed text; T/Keep as text stores a refused paste as text; R renames a just-added entry |
| 2 Entries | W/S moves; / starts live search; T cycles all/files/strings; R/E renames; X deletes with confirmation |
| 3 Saved values (C2) | Values workflows keep between runs, under their workflow's name or All workflows. W/S moves (headings are skipped); / searches names, values and places; E/Enter changes a value (typed by its type); X forgets it with confirmation. The line below the list says which node saved it, when, and from where. Not shown in insert mode |
| All tabs | 1/2/3 switches tabs outside editing; Esc/Q/Ctrl+Q closes after text editing; buttons expose the same actions |

Enter or Esc from search returns focus to the list. Typed letters remain text.
File entries show `[file]`, text entries `[string]` (a type label always uses
the type's name; `aotn stash list --type string`); refused paths/folders show a
reason rather than becoming file entries. Paste handling is local to this screen.
S3 field insertion is separate planned work; manage mode does not insert values
into a node config. An entry's own rename uses the shared name prompt.

## Recovery editing

Preserved UX decisions, with the later display-suffix rollback applied:

- Recovery is edited once, in the mux editor. The originating node lists friendly
  errors and offers Add/Open Error Resolver; it does not duplicate route controls.
- Reuse a mux only when the normal output connects directly to its `input`.
  Otherwise insert a mux and preserve the old downstream on No error. Stay on
  the normal editor path after insertion.
- Cancelling the first edit of a newly inserted mux removes it and restores
  wiring. Unpicking a route containing nodes offers Leave unlinked, Delete
  branch or Cancel; do not silently discard its graph.
- Save is per node. Jumping with unsaved changes asks Save/Discard/Stay.
  A no-edit save preserves unsupported config and unresolved stored choices.
- Existing direct `error` connections still execute and display, but the UI
  promotes inline recovery. IDs remain stable; aliases/type names are display
  labels and raw IDs remain inspectable. The numbered suffix was rolled back.

## Read-only displays and scrolling

Retained convenience displays have concrete purposes: incoming payload previews
support inspection/copy; Connections explains wiring; an empty Vault message
explains an enabled read with no candidates. A setter's literal can still control
its Vault write while forwarding, Text Output formatting still applies to requested
input, and file write modes still apply when OS opening is off. Do not hide a
still-effective control merely because a neighboring feature is disabled.

Keep tab headers visible outside scrolling content. Hide inactive controls with
their labels/messages while preserving values; do not silently reset them.
Only the highlighted field should drive reveal scrolling. Use production-CSS
mounts to verify focus and viewport stability, as described in Contributing.
