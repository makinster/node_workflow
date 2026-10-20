# Keymap phase 3 — Editor and Execution

Fresh main `106c437` (#89/#90 merged), branch
`codex/keymap-editor-execution`. Awaiting owner review.

## Visible text

| Topic | Before | After |
|---|---|---|
| Editor Help | [text](editor-before.txt) | [text](editor-after.txt) |
| Execution Help | [text](execution-before.txt) | [text](execution-after.txt) |
| Compact hints | [before/after text](hints-before-after.txt) | Default wording is identical |

Execution Help previously said S Stop and omitted the merged movement,
path, follow and error-panel keys. It now lists the profile: X Stop, S Down,
A/D paths, F Follow, V error panel, and all existing aliases. Editor Help
lists the complete profile, including panel focus and File/Options keys.
Labels use profile descriptions; the General section lists inherited
application commands. Its existing Back command quits from Editor or returns
from a secondary screen. No binding, action route, ID or policy is changed.

Command groups control compact hint order and short labels by stable ID;
the profiles supply the actual keys. Help lists all aliases. Both displays
follow native overrides; old overridden aliases are not retained. Native
punctuation/control names display as ?, Esc and Backspace, not internal names
or control characters. Other Help topic text remains unchanged.

Mounted with production CSS at 24 rows (headless captures):

| Width | Editor | Execution |
|---|---|---|
| 60 | [text](editor-mounted-60.txt) | [text](execution-mounted-60.txt) |
| 100 | [text](editor-mounted-100.txt) | [text](execution-mounted-100.txt) |
| 140 | [text](editor-mounted-140.txt) | [text](execution-mounted-140.txt) |

W/S or up/down scrolls Help. E/Enter closes it; Close remains visible.
Native terminal manual checks were not performed.

## Verification

- Eight new checks failed first; the existing Execution key characterization
  passed. Additional punctuation and Escape display checks failed before fixes.
- Twelve new tests cover Help generation, default keys/hints, profile edits,
  native rebindings, error-panel hint state, modal isolation and Help scrolling.
  The older Help regression now checks the generated labels and alias spelling;
  its close-button/focus and contextual checks remain.
- Full suite: **1,884 passed in 277.58s**. Compile, docs links/archive and
  `git diff --check` pass. Tests isolate data before backend imports with
  `AOTN_DATA_DIR=/tmp/aotn-keymap-phase3`.
- AST comparison confirms APP, EDITOR and EXECUTION definitions are unchanged.
  Default compact hint text matches main byte for byte.
- `node_config.py`, backend, Vault log and owner workflows are unchanged.
  No preferences UI, new dispatcher or new default keys are introduced.
