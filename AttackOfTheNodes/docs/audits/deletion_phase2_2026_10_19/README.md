# Deletion phase 2 — review evidence

Implementation branch `codex/deletion-phase2`, fresh `origin/main` `a31d721`.
The owner approved #86; #85/#87 are merged. This PR awaits owner review.
No changes to Node Config's source, Execution, backend or owner workflows.

## Rendered samples

Mounted Textual screens use production `frontend/styles.tcss` at 34 rows.
SVG and plain text show the actual compositor output. The 64-path scrolling
case is also tested with real W/S/E/Space/Enter input at all three widths.
These captures are automated renders, not a native terminal manual check.

| Width | First delete | Recover prompt | Which paths |
|---|---|---|---|
| 60 | [SVG](delete-60.svg), [text](delete-60.txt) | [SVG](recover-prompt-60.svg), [text](recover-prompt-60.txt) | [SVG](recover-picker-60.svg), [text](recover-picker-60.txt) |
| 100 | [SVG](delete-100.svg), [text](delete-100.txt) | [SVG](recover-prompt-100.svg), [text](recover-prompt-100.txt) | [SVG](recover-picker-100.svg), [text](recover-picker-100.txt) |
| 140 | [SVG](delete-140.svg), [text](delete-140.txt) | [SVG](recover-prompt-140.svg), [text](recover-prompt-140.txt) | [SVG](recover-picker-140.svg), [text](recover-picker-140.txt) |

The recover question and all three buttons remain visible at 60 columns.
Multi-line loss/repair previews use automatic height instead of the generic
one-line modal title. Long previews can scroll.

## Visible wording against the approved samples

The approved proposal remains the decision receipt. The shared picker uses
“path” for delete and count changes, and puts the count on a separate line.
Examples of the final wording (names/counts depend on the workflow):

```text
Delete Dispatch — keep 1 path
Selected 1 / 1
[x] Path 1
[ ] Path 2
Stores 2 nodes with the deleted group. Shared nodes stay. Z restores the group.
Space/E toggle | W/S move | Enter apply | Esc cancel
[Delete] [Cancel]

Dispatch: 2 paths → 3
2 saved paths. Recover any for the new paths?
[Recover] [Leave empty] [Cancel]

Recover paths for Dispatch
Picked 0 — up to 1
[ ] Local cache
[ ] Remote copy
Pick none to leave new paths empty. Others stay saved.
Space/E toggle | W/S move | Enter apply | Esc cancel
[Apply] [Cancel]
```

| Approved sample | Implemented text |
|---|---|
| `Delete Dispatch — keep 1 branch` | `Delete Dispatch — keep 1 path` |
| `Dispatch: 4 branches → 2` | `Dispatch: 4 paths → 2` |
| `2 saved paths. Recover any for the new path?` | `2 saved paths. Recover any for the new paths?` |
| `Pick up to 1` | `Picked 0 — up to 1` (updates with selection) |

The new ` [sub]` add-on appears only for callable workflows. Header markup is
disabled so bracketed text displays literally; the existing `[IDLE]` text also
becomes visible instead of being swallowed as markup. The [before/after compositor text](header-before-after.txt) confirms this
markup mismatch. No other existing screen wording changes with the header fix.

## Verification

- Failing tests first: initial topology/API probes (13 failures), mounted
  header/picker/form probes, then regression probes for draft seeds/names,
  remapped path recovery, reused IDs, partial recovery, retry after reload,
  saved-row insertion/selection and multi-line recovery question clipping.
- New coverage: **55 passed** across graph/recovery and mounted UI tests.
  Existing regressions were updated for the approved first-delete behavior;
  their cases remain present. Legacy stubs and shared-handler tests remain.
- Full suite: **1848 passed in 265.69s (0:04:25)**.
- Compile checks, `git diff --check` and docs link/archive checker pass.
- Tests use `AOTN_DATA_DIR=/tmp/aotn-delete-phase2` before backend imports;
  no real settings or workflow files are used.

Global session Ctrl+Z and saved-path expiry are deferred. An active group stub
still blocks execution; recovery under a live Branch does not. Unconnected
Beacons and unreachable nodes keep their existing warning severity.
