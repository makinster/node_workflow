# Deletion picker review follow-up

Fresh main `b5426ab` (#88 merged), branch `codex/deletion-picker-polish`.
Lists fit their rows; the hint and buttons sit directly below. Long lists keep
scrolling within the screen. No deletion, recovery or keymap semantics change.

## Samples

[Before: keep](../deletion_phase2_2026_10_19/delete-60.svg),
[before: recover](../deletion_phase2_2026_10_19/recover-picker-60.svg).
The retained #88 captures show the former stretched lists.

| Width | Keep | Recover |
|---|---|---|
| 60 | [SVG](keep-60.svg), [text](keep-60.txt) | [SVG](recover-60.svg), [text](recover-60.txt) |
| 100 | [text](keep-100.txt) | [text](recover-100.txt) |
| 140 | [text](keep-140.txt) | [text](recover-140.txt) |

Actual mounted flows use production CSS at 34 rows. Tests also cover wrapped
labels after resize and 64 paths with W/S, E/Space, Enter and Cancel. Native
terminal manual checks were not performed.

## Wording

| Before | After |
|---|---|
| Stores 6 nodes with the deleted group. Shared nodes stay. Z restores the group. | Deletes 6 nodes. Shared nodes stay. Z brings them back. |
| Pick one path. Other paths stay saved with the deleted node. | Pick one path to keep. Z brings deleted nodes back. |
| Shared nodes stay. Z restores the group. | Shared nodes stay. Z brings them back. |
| Z restores the group. | Z brings them back. |
| Its Merge Beacons stay, unconnected. Reconnect them to a valid target. Validation warns; this warning does not block a run. | Its Beacons stay. Reconnect them. Unconnected Beacons give a warning. Runs are allowed. |
| This branch ends. No bypass into Merge. | This branch ends here. |
| Deleted group restored | Nodes restored |
| The other nodes and valid links can return. | Restore the rest? |
| Pick the paths to keep. Removed paths stay saved and never run. | Pick paths to keep. Others stay saved and never run. |
| Stores 6 nodes under this Branch. Shared nodes stay. | Saves 6 nodes under this Branch. Shared nodes stay. |

Other new messages were reviewed and retained where already short and plain.
Editor changes are string literals only; EX map/profile ownership is untouched.

## Checks

- Eight new geometry/wording checks failed on main before the fixes.
- Focused deletion suites: **63 passed**. Full suite: **1856 passed in 265.73s (0:04:25)**.
- Original test ASTs match, excluding added tests. A token/AST check confirms
  no semicolon-joined statements or one-line definitions remain in either file.
- Compile, docs link/archive and `git diff --check` checks pass.
- Tests isolate storage with `AOTN_DATA_DIR=/tmp/aotn-picker-polish` before
  backend imports. No owner workflows or settings are edited.
