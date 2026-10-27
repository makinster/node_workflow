# Stash Proposal — Drag-and-Drop Entries, Field Insert, and Contract Inputs

> Design and staged scope. [Current State](CURRENT_STATE.md) owns approvals
> and delivery; [UI Quick Reference](UI_QUICK_REFERENCE.md#stash-screen-s2) owns the
> current controls. S1–S3 are implemented; S5 is implemented as simplified
> in Step 4d (see §4.5). Folder import (S4) and any later extensions remain
> separate work. Sections 8–9
> retain historical review context, superseded where the decisions below differ.

## 1. Summary

A **Stash** is a durable, per-machine store of named values (file paths and
text snippets) that lives outside any workflow graph. You fill it by dropping
files or pasting text into a full-screen panel, and you use it by inserting
entries into node config fields with `P`.

It grows in three stages:

1. **Copy (near term).** Insert writes the entry's value into the highlighted
   *configured* field. The workflow stays self-contained.
2. **Folder import (near term).** Dropping a folder imports up to a limit of
   files as entries.
3. **Contract inputs (mid term, with Step 4).** The Stash becomes one *source*
   for workflow contract inputs: subworkflows, `aotn run`, triggers and API
   calls. Values specific to one machine are bound per machine instead of being
   baked into the workflow.

Stage 3 is why the backend pieces must be headless-safe from day one.

## 2. Problem

- Typing file paths into config fields is slow and error-prone. Terminals
  already paste a file's path when it is dropped onto them, but nothing in the
  app collects or reuses those paths.
- There is no place to keep reusable text (prompt fragments, IDs) between
  sessions. The Vault exists only for one run.
- Workflows meant to run elsewhere (subworkflows, headless, triggers) have no
  clean way to say "this value depends on the machine running me".

## 3. Current implementation: what exists and how it fits

| Area | Today | Fit / gap |
|---|---|---|
| Vault (`backend/memory_bank.py`) | Per-run `MemoryBank`; persistent dict plus transient `(node_id, port)` data; filled only by nodes during a run | **Not** a home for Stash entries: they would trip `undeclared_vault_key` (`validation_codes.py:30`), and transient data needs a source node. The Stash must be its own store. |
| Out-of-graph store precedent (`backend/secrets_manager.py`) | `SecretsManager`: get/set/delete/list keyed values under `DATA_DIR/secrets`, reachable through `NodeContext` | The template for a `StashManager` (non-secret, typed entries). |
| Persistence (`backend/persistence.py`) | Storage is rooted at `resolve_data_dir()` (`AOTN_DATA_DIR` / `--data-dir`); `STASH_DIR` exists | `StashManager` uses the shared JSON-record helpers. |
| Data types (`backend/data_types.py`) | Canonical `string`, `number`, `bool`, `var`, `file`, `ai_session`, `any` | Entry types use this vocabulary, so filtering and contract matching need no translation. |
| File refs (`backend/file_refs.py`) | `file_reference(path)` creates a tagged JSON object; `reference_path()` resolves its path | File entries store that object; copy-insert writes its path into an accepting configured field. |
| Path normalization (`backend/file_paths.py`) | `normalize_local_path`; used by the validator for fields with `normalize_local_path: True` | Dropped paths are normalized when stored, so inserted values match hand-typed ones. |
| Field hints in schemas | `accepted_types()` in `backend/field_types.py` uses explicit `data_type`, otherwise `path_hint: file`, otherwise text-field type | File fields take file entries; ordinary text fields take text only. `path_hint` still describes file/path semantics. |
| Source selectors | Ports declare `sources: [upstream, vault, configured]` with a `configured_field`; config holds `<port>_source` plus `<port>_vault_key` (`vault_declarations.py`) | Choose Configured first, then focus its value for Stash insertion; source selectors refuse (owner, 2026-10-26). |
| Config form (`frontend/widgets/form_generator.py`, `frontend/screens/node_config.py`) | Widgets have id `field-<name>`; `node_config.py` already maps ids back to schema fields | Insert target = the focused `field-*` widget; read its schema entry, then filter and write. |
| Edit widgets (`frontend/widgets/command_input.py`) | CommandInput / CommandTextArea distinguish navigation and editing | Plain `P` opens insert only outside editing; typing remains literal. |
| Key bindings (`frontend/keymap.py`) | Editor `P` opens manage mode; Node Config `P` opens insert; the command palette keeps Ctrl+P | No command-palette change. |
| Paste handling (`frontend/screens/stash.py`) | The Stash handles bracketed paste through `parse_paste` / `StashManager` | Paste elsewhere stays normal text input; there is no app-wide interception. |
| Headless (`aotn_cli.py`, `backend/run_service.py`) | Typed `--input` and `--inputs-file` bind Start rows through `backend/contracts.py` | `--input key=@stash:name` reads a Stash entry (4d); there is no second contract manifest. |
| Contracts (`backend/contracts.py`) | Start rows and Return End results define the workflow contract | Step 4 extends that contract to child calls; a Subworkflow node input can come from a Stash entry (4d). |

**Boundary check** ([BACKEND_FRONTEND_BOUNDARY.md](BACKEND_FRONTEND_BOUNDARY.md)):
stages 1–2 add one small backend service (store, paste parser, field-type
rule) and otherwise stay in the frontend. Stage 3 is backend work inside the
already-approved Step 4.

## 4. Proposed design

### 4.1 Entry model

```json
{"id": "stash_8f3a…", "name": "march_report", "type": "file",
 "value": {"type": "file", "ref_key": "file:/…/march.csv", "path": "/…/march.csv"},
 "group": null, "created": "2026-10-16T…", "updated": "…"}
```

- **Stable `id`** separate from `name`, so renames never break a later binding.
- **`type`** comes from `data_types.py` (`file` and `string` at first).
- **`group`** holds the folder-import grouping (stage 2).
- **Scope: global per data dir** to start. Pinning entries to a workflow is
  left open.

### 4.2 Backend (headless-safe, no Textual imports)

- `backend/stash_manager.py`: CRUD, type checks, JSON export/import (versioned
  format).
- `backend/paste_parser.py`: turns a pasted string into a list of path
  candidates (handles quoting, escapes, several files), checks each exists, and
  normalizes it. Outcome per paste (reconciled with 4.3, see 9.7): pieces
  that look like paths become file entries when they exist and are
  flagged, not stored, when they do not; only a paste with no path-like
  piece becomes one text entry.
- `accepted_types(field_schema) -> set[str]`: one shared rule. `path_hint:
  file` accepts `file`; a plain string field accepts `string` (and maybe
  `file`, as a raw path). The picker uses it now; contract binding reuses it
  later.

### 4.3 Frontend

- **Stash modal** (full screen), two tabs:
  - *Drop/Paste*: one paste target, a list of what was just added, inline
    naming.
  - *Entries*: search, rename, delete, filter by type, folder groups that
    expand.
- **Open:** `p` from the Editor screen (manage mode, no insert).
- **Insert (owner, 2026-10-26):** in node config, focus a text/file field, then
  press `P`. All Selects/model pickers refuse with "Stash text can't go into
  this field"; they never redirect to another field. Choose Configured before
  focusing a hidden value. The explicit Insert button keeps only the immediately
  preceding eligible field. In row editors, focus Default/Text or the Subworkflow
  Stash entry control itself. The list shows
  only entries that fit, `e`/Enter inserts, the modal closes and the field is
  filled. If the field accepts nothing (checkbox, select), show a short notice.
- **Warnings:** a dropped path that doesn't exist (common over SSH) is flagged
  and not silently stored.

### 4.4 Folder import (stage 2)

- Count first, then import: files, total size and depth, each capped through
  `DEFAULT_SETTINGS`.
- Over a limit, **refuse with numbers** ("340 usable files, limit 50"). Never
  truncate silently.
- Don't follow symlinks. Skip hidden files and binary files the project can't
  use.
- No folder tree browser at first. Use a grouped entry with relative paths,
  plus the type filter.

### 4.5 Contract inputs (stage 3, inside Step 4)

When a run starts, Start writes each contract input into the Vault. Inner
nodes read it through the existing `<port>_source = Vault`. That is
"reference mode" without a new per-port source option.

**As built (Step 4d, owner 2026-10-20).** There are no per-machine bindings
and no `stash/bindings/` files; Start's Default keeps copy-insert with `P`.
Stash entries reach inputs two ways, both by entry **name**:

- A Subworkflow node input's "Value comes from: Stash entry", picked with
  `P` and saved in the workflow.
- `aotn run wf --input key=@stash:name` (quotes allowed around the name).

A file entry is passed as its file reference; a text entry is parsed by the
input's type like typed text. A missing entry is a validation error
(`subworkflow_stash_missing`); the CLI refuses to start and lists it with
every other input that has no value. Before a run, `aotn run` lists where
each input came from (`from Stash entry "x"`, `from --input`, `from its
default`).

Order for filling each input, the same for every caller (C10):

1. Explicit caller value (`--input k=v` or `k=@stash:name`, API body, trigger
   payload, the parent subworkflow node's mapping including a Stash entry)
2. Inputs/preset file (`--inputs-file run.json`)
3. The contract's default
4. Required and still empty: **fail before the run starts**, with a clear exit
   code and a list of what's missing

Originally proposed: a third step, a saved Stash binding on this machine
(input → entry id, stored per workflow in the data dir, not in the workflow
JSON), set from the Start/contract panel. Dropped in 4d as more than the use
case needed.

## 5. Roadmap (very high level)

| Stage | Contents | Depends on | Rough size |
|---|---|---|---|
| **S1 — Stash core** | `StashManager`, `STASH_DIR`, paste parser, `accepted_types`, JSON export/import, unit tests | — | S |
| **S2 — Stash modal** | Full-screen modal (Drop/Paste + Entries), `p` from Editor, name/rename/delete | S1 | M |
| **S3 — Field insert** | plain `P` in node config, off while typing (palette unchanged), filtered picker, write to focused field, switch source to `Configured`, `path_hint` audit | S1, S2 | M |
| **S3b — CLI (optional)** | `aotn stash list/add/rm/export/import` | S1 | S |
| **S4 — Folder import** | Count/limits, refusal with numbers, grouped entries | S2 | S–M |
| **S5 — Contract integration** | Fill order, per-machine bindings, `@stash:`, fail-fast on missing inputs, binding UI on Start/subworkflow node | DISTRIBUTED Step 4 | L (most of it shared with Step 4 itself) |
| **S6 — Presets / sharing (exploratory)** | Bundle of values matched to a contract version; preview before applying; data only, never code | S5 | Undefined: design when needed |

S1–S4 are independent of the distributed roadmap and could slot in after
frontend work. S5 should be designed **as part of** Step 4, not after it.

## 6. Hypothetical scope

**In (S1–S4):** file and text entries; global Stash per data dir; drop/paste
parsing for common terminals; copy-insert into configured fields;
type-filtered picker; folder import with hard limits; versioned JSON
export/import.

**In (S5):** Stash as one input source for workflow contracts; per-machine
bindings; CLI `@stash:` references; validation before the run starts.

**Out / deferred:**
- Reference mode on individual ports (replaced by contract inputs)
- Folder tree navigation
- Entry types beyond `file`/`string` (JSON blobs, image refs, folders as a single value)
- Per-workflow Stash scope
- Sharing, galleries and preset markets (S6). If it happens: presets are pure
  data, fill only exposed inputs, never carry absolute paths or secrets, and
  get a preview because of prompt-injection risk.
- Storing secrets in the Stash: those stay in `SecretsManager`. Export
  excludes them and warns on values that look like keys.

## 7. Open questions

1. Should a `string` field accept a `file` entry (inserting the raw path)?
2. Turn off Textual's command palette, or move it to another key?
3. Global-only Stash, or allow pinning entries to a workflow?
4. Does copy-insert flip `input_source` to `Configured` automatically, or ask?
5. For S5: where do bindings live (`stash/bindings/<workflow_id>.json`?), and
   does the run record capture which inputs came from the Stash?
6. Folder-import defaults (file count / total size / depth).

## 8. Historical risks

- **Terminal variance:** drop quoting differs by terminal and OS; the parser
  needs a fixture table per terminal.
- **SSH / remote:** pasted paths belong to the client machine; validate on drop.
- **Scope creep:** S6 ambitions must not bloat S1–S3. The JSON export format
  is the only forward-looking commitment in the near-term stages.
- **Focus edge cases:** `ctrl+p` during an active edit must commit cleanly
  (follow the save-and-stay pattern) and must not fight the focus-drift guard
  in `command_input.py`.

## 9. Review notes and fit with the plan (2026-10-17)

Historical review at the commit below: the original Ctrl+P proposal and
recorded-only run inputs have since been replaced by plain P and typed
Start-row binding. The command palette remains unchanged.

Reviewed against the code at `8815bcd` (PR #61 merged). At that baseline:
Textual's command palette was on and used `ctrl+p`;
`path_hint` is read only by the validator; nothing handles paste events;
`aotn run --input` exists and nothing consumes it yet. The owner agreed with
the notes below.

**Design notes**

1. **Superseded 2026-10-26:** the owner now requires focus-only Stash assignment;
   Source selectors refuse rather than switching/filling another field. The
   following retains the historical design. **Hidden fields cannot be focused.** A path field hidden behind
   `<port>_source != "Configured"` can never be highlighted, so `ctrl+p` on
   the port's *Source* selector row offers file entries, switches the source
   to Configured, fills the value and says so. This answers open question 4.
2. **Declare what a field accepts.** Rather than inferring from `path_hint`,
   schema fields declare a canonical `data_type` (`file`, `string`, ...);
   `accepted_types()` reads the declaration, and `path_hint` keeps driving the
   file picker. S3's audit sets the declarations.
3. **The insert key is tested in the owner's terminals first** (Windows
   Terminal, tmux, the Claude app's terminal panel; VS Code's terminal is known
   to intercept `ctrl+p`). Turning the command palette off is fine; the planned
   per-panel `H` help popup covers discoverability. Deferred until S3 (owner,
   2026-10-17: no PC access to test now).
4. **Windows drops into WSL** paste Windows paths: every candidate goes
   through `normalize_local_path`, and the parser's fixtures include quoted
   Windows paths (the stray `"C:\...\test.txt"` file in the owner's checkout
   is one that was mishandled).
5. **Paste is collected only inside the Stash panel.** Ordinary text fields
   keep receiving pastes as text, exactly as today; nothing intercepts paste
   app-wide.
7. **Paste outcomes (review of PR #63, reconciles 4.2 with 4.3).** The
   parser first decides whether each piece *looks like a path*: absolute
   (`/...`, `~/...`), a Windows drive path (`C:\...`, quoted or not), a
   `file://` URI, or a quoted or escaped token in a multi-file drop. Then:
   - looks like a path and exists (after `normalize_local_path`): a file
     entry;
   - looks like a path and does not exist: listed with a warning ("not
     found on this machine", common over SSH) and **not stored**; the
     panel offers "add as text instead" so nothing is lost silently;
   - no piece looks like a path: one text entry with the whole paste.
   A mixed paste (some path-like pieces, some not) is treated as text
   unless every piece looks like a path, so prose that mentions a path
   stays one text entry.
6. Agreed as written: generated entry ids, per-machine bindings outside the
   workflow JSON, secrets stay in `SecretsManager`, folder import refuses with
   counts.

**Order (owner, 2026-10-17):** authoring tool PR 2 → C4, C6, C7 → workflow
naming PR → **Stash S1–S3** (S3b CLI can ride with S1) → `DISTRIBUTED_BUILD_PLAN.md`
Step 4 with **S5 designed in** → S4 folder import when wanted. S6 stays
exploratory.

## Saved values (C2)

Built 2026-10-21 (AI coordination C2/C5: the persistent store pulled forward
from Step 5, built on the Stash's store). A workflow keeps values for its next
run with three nodes in the Utility group **Saved values** (see
[Node Catalog](NODE_CATALOG.md#group-saved-values)): **Remember**, **Recall**
and **If changed** (the H3 change detector: paths Changed / No change).

Owner answers (2026-10-21):

1. Three nodes in a "Saved values" group on the Utility tab; the name "Saved
   values" everywhere (group, Stash tab 3, CLI).
2. A workflow's values follow its **name**, not its id: rebuilding a cron
   workflow from its spec keeps them, and renaming it (library or editor)
   moves them. A value the new name already has is never overwritten.
3. "Kept for" defaults to This workflow; All workflows is shared by every
   workflow in the same data folder.
4. If changed, first run (nothing saved yet): **No change · save quietly** by
   default; **Changed · send it on** is a choice. Paths are named Changed and
   No change.
5. Recall with nothing saved uses its Starting value by default; Stop is a
   choice. Recall's Type is strict: a saved string never becomes a number.
6. Remember's Add makes counters.
7. Stash tab 3 lists values under their places: E changes a value (typed by
   its type), X forgets it. Saved values can't be inserted into fields, so the
   tab is absent in insert mode.
8. Values stay with the data folder; `aotn --data-dir <folder>` opens the app
   on another one (for example cron's `~/.local/share/aotn-cron`).
9. 64 KB per value. The old value isn't an output of If changed; put a Recall
   before it when a message needs it.

**Storage.** `<data dir>/stash/saved.json`, format `aotn-saved/1`, next to
the Stash's `entries.json` but separate: Stash entries refuse duplicate values,
saved values change every run. A value:

```json
{"id": "saved_3f9a0c1b2d4e", "name": "last_version",
 "place": {"kind": "workflow", "workflow": "hermes-release-watch"},
 "type": "string", "value": "v0.14.2",
 "created": "2026-10-20T16:00:02Z", "updated": "2026-10-21T16:00:03Z",
 "saved_by": {"node": "New version?", "node_id": "node_39e9571a",
              "run_id": "run_8c1d…", "from": "command line"}}
```

`place` is `{"kind": "workflow", "workflow": <name>}` or `{"kind": "all"}`;
`type` is a `data_types` name (string, number, bool, var, file; never
ai_session) and must match the value (`var` is a JSON list or record; numbers
are finite); `from` is `app`, `command line` or `MCP`. Names ignore case
within a place. A file that can't be read (bad JSON, bad UTF-8) or holds a
damaged or inconsistent record is reported as `store_unreadable` and never
overwritten or repaired by dropping records. A workflow named "All workflows"
is its own place, shown as "All workflows (workflow)".

A standard workflow and a subworkflow may share a name, and then share its
values; renaming one of them leaves the values with the name while the other
still has it.

**Two runs at once** (cron and the app). Every read goes to the file; every
change is one locked step (`saved.lock`: `fcntl` on Linux and macOS,
`msvcrt` on Windows; with neither, changes are refused): re-read, change one
value, write atomically, unlock. Different names never overwrite each other; for the
same name the later write wins. Add and If changed compare-and-save are one
step, so counters lose no counts and two runs can't both report one change.
`backend/saved_values.py` owns all of this; the nodes, Stash screen and CLI
share it.

**CLI.** `aotn stash saved list [--workflow NAME]`,
`aotn stash saved show|forget NAME (--workflow NAME | --all)`,
`aotn stash saved set NAME VALUE (--workflow NAME | --all) [--type T]`; all
take `--data-dir` (before `saved`) and `--json`.
