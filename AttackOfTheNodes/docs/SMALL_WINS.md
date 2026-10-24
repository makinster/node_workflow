# Read lines, Find lines and Check reply

Owner-approved small wins, 2026-10-23. Three separate nodes, built after the
[samples](audits/small_wins_2026_10_23/README.md), including the two approval
changes: retain recent matches with the true total; use Start's compact row
editor pattern for expected fields. No inference, shell, file changes or new
permissions are part of these nodes.

## Read lines

**In → Files → Text files → Read lines** returns an Excerpt `[string]`.
Choose a File inside **Options → system_node_folders**. From line comes from
Configured, Upstream payload or the Vault. A configured value is one integer;
upstream/Vault may also supply a list of at most 1,000 integers. First/Last
chooses a list entry, **Last** by default. An empty list gives `no_matches`
(“No matching line to read.”), without falling back to a tail read.

Lines start at 1 and include both ends. Negative values count from the end:
From **-50**, To **-1** reads the last 50 lines. Values before the start clamp
to 1; To beyond the end clamps to the last line. Zero, reversed ranges and
positive From beyond the end fail. Empty files return empty text in range
mode. **Lines around** uses From as its centre, with **5 lines each side** by
default (0–200). It hides To, keeping the saved value. Around an empty file
fails with `no_lines`.

## Find lines

**In → Files → Text files → Find lines** returns Line numbers `[var]`, a list
of positive integers, ascending. Text to find uses Configured, Upstream payload
or Vault; the File stays configured. Search is literal within each line;
**Match case** starts on. Turning it off uses Unicode casefolding. Empty or
multiline search text fails. A line counts once even if the text occurs twice.
No match returns `[]` successfully.

**Max matches: 100** (1–1,000) keeps the most recent matching lines, still
ascending. The complete bounded file is scanned. The optional Vault-only
**Match count `[number]`** is the true number of matching lines, including
those outside the retained list. For example, 312 matches with a cap of 100
returns the last 100 line numbers and can store 312 in the Vault. Read lines'
Last then selects the latest matching line. Going over the file-size cap
still fails; no partial list or count is published on failure.

## Shared file limits and access

Both nodes check `system_access` and `system_node_folders`; an empty allowed
folder list grants no access. They resolve links, refuse targets outside those
folders and open only regular files. On Linux, directory-descriptor walks with
`O_NOFOLLOW` prevent a replacement link from redirecting the open;
`O_NONBLOCK` prevents a replacement FIFO from hanging. Systems without these
secure-open primitives fail closed. Native desktop platforms were not tested.

Read UTF-8 (an optional initial BOM is accepted). LF counts lines; CRLF counts
once and becomes LF in the excerpt. A final unterminated line counts; a final
newline adds no invented line. U+2028 and U+0085 remain text. Each file line is
limited to 64,000 bytes. File size defaults to **10 MB**, up to **100 MB**;
MB means 1,000,000 bytes. Read lines also caps its excerpt at **500 lines**,
**8,000 characters** by default (up to **20,000**) and **80,000 UTF-8 bytes**.
An oversized excerpt fails rather than being silently shortened.

Reads stream a bounded initial byte snapshot, check cancellation between
64 KiB reads and close descriptors on completion/error/Stop. Appended bytes
are ignored; observed truncation, replacement or same-size modification fails.
Find and Read do not share a locked snapshot. A file can rotate or change
between nodes; choose a fixed workflow-created snapshot when that matters.
These are deliberate file readers, not automatic secret detectors.

File errors: `file_missing`, `not_allowed`, `not_regular`, `file_unreadable`,
`not_utf8`, `file_too_large`, `line_too_long`, `file_changed`. Read adds
`invalid_range`, `no_matches`, `no_lines`, `excerpt_too_long`; Find adds
`text_missing`. Error messages do not include file contents.

## Check reply

**Utility → Transform → Check reply** checks one JSON object against 1–32
expected fields. Reply uses Configured, Upstream payload or Vault; the default
is **Upstream payload**. Expected fields use one row per field with
**Field · Type · Required?**. W/S navigates; E/Enter edits a row; X removes it;
Add field opens the same style of row editor as Start's inputs table. Cancel
keeps the original, and Node Config saves the complete ordered rows.

The hint leads the form: “Checks that a reply has the fields below. If not, it
takes the error path.” **Extra fields are OK** starts off. When enabled,
unknown fields are kept in the parsed record. Max reply size follows the table.
Names are case-sensitive, unique, 1–64 characters, start with a letter or `_`,
and otherwise use letters, digits, `_` or `-` (ASCII). Long names are shortened
only in the table display; the editor and saved configuration keep them whole.

| Type | Accepted JSON value |
|---|---|
| Text | String, including empty text |
| Number | Finite integer or decimal; never true/false |
| Yes or no | Boolean |
| List | Array; no nested shape constraints |
| Record | Object; no nested shape constraints |
| Empty | null |

Required means present. Optional fields may be absent, but when present must
still match their type. One strict JSON object only: no fences, commentary,
trailing text, duplicate keys (including nested objects), non-finite numbers,
repair or conversion. All values, including extra fields, must be valid.

Valid replies produce Checked reply `[var]`, the parsed record. Invalid replies
raise `reply_mismatch`, **“Reply didn't match.”**, through the engine's normal
error path. Bad expected-field setup gives `shape_invalid`. No success payload
or Vault output is published for a mismatch, even when forwarding is checked.
The default reply cap is **16,000 characters**, adjustable to **64,000**, with
hard limits of **256,000 UTF-8 bytes** and **eight nesting levels**. Nesting is
checked before parsing; Stop is checked while scanning and before publishing.
This checks shape, not the truth or usefulness of an answer.

Configured Reply uses the shared, opt-in long-text preview: two lines plus
“… N more lines”, E/Enter for a wrapping full-screen editor, Save/Cancel and
confirmation on Esc with unsaved changes. Focus returns to the preview.
P replaces all preview text after confirmation when nonempty. In the editor,
Esc stops typing, P inserts Stash text at the cursor, E resumes typing; plain
P still types “p” while editing. Existing multiline fields are unchanged; the
broader UI consistency rollout stays separately proposed in the backlog.

## Routing and example

All three offer the standard **Forward incoming payload unchanged** checkbox,
initially off. Off publishes the node's own result; on forwards the original
incoming value after success. Enabled Vault outputs always keep the node's
own value and type. Find's Match count is independent of downstream forwarding.

Example: Find lines `ERROR` → Read lines around (Last, five each side) →
existing Concat (add a question asking for JSON summary/optional cause/next_step)
→ Ask Hermes → Check reply → Notify me. Use the existing error path for an
empty match list or invalid reply. Nothing invokes Hermes automatically.
