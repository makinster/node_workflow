# Stash Proposal — Drag-and-Drop Entries, Field Insert, and Contract Inputs

> **Status: proposal, not approved (2026-10-16).** Owner discussion only; no
> code. Nothing here changes an approved decision in
> [DISTRIBUTED_BUILD_PLAN.md](DISTRIBUTED_BUILD_PLAN.md). "Stash" is a working
> name.

## 1. Summary

A **Stash** is a durable, per-machine store of named values (file paths and
text snippets) that lives outside any workflow graph. You fill it by dropping
files or pasting text into a full-screen panel, and you use it by inserting
entries into node config fields with `ctrl+p`.

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
| Persistence (`backend/persistence.py`) | Data dirs anchored at `resolve_data_dir()` (`$AOTN_DATA_DIR` / `--data-dir`); `save_json_record` / `load_json_record` / `list_json_records` | Add `STASH_DIR = DATA_DIR / "stash"`. Using the existing record helpers means headless and server data dirs work for free. |
| Data types (`backend/data_types.py`) | Canonical `string`, `number`, `bool`, `var`, `file`, `ai_session`, `any` | Entry types use this vocabulary, so filtering and contract matching need no translation. |
| File refs (`backend/file_refs.py`) | `file_reference(path)` gives `{"type": "file", "ref_key", "path"}`; `reference_path()` accepts a ref or a raw path | A file entry stores a `file_reference`. Copy-insert writes `reference_path()` into the field. (Known doc conflict C11: `data_types.py` still calls refs strings.) |
| Path normalization (`backend/file_paths.py`) | `normalize_local_path`; used by the validator for fields with `normalize_local_path: True` | Dropped paths are normalized when stored, so inserted values match hand-typed ones. |
| Field hints in schemas | Path fields declare `"path_hint": "file"` (`file_reader_node.py:31`, `file_view_node.py:51`, `file_output_node.py`); the validator checks them (`validator.py:288-317`). The frontend does not read the hint yet. | `path_hint` is the main signal for filtering the picker. An audit is needed for path fields missing it. |
| Source selectors | Ports declare `sources: [upstream, vault, configured]` with a `configured_field`; config holds `<port>_source` plus `<port>_vault_key` (`vault_declarations.py`) | Copy-insert into a field hidden behind `input_source != "Configured"` should switch the source to `Configured`. |
| Config form (`frontend/widgets/form_generator.py`, `frontend/screens/node_config.py`) | Widgets have id `field-<name>`; `node_config.py` already maps ids back to schema fields | Insert target = the focused `field-*` widget; read its schema entry, then filter and write. |
| Edit widgets (`frontend/widgets/command_input.py`) | `CommandInput` / `CommandTextArea` with `editing` mode and `begin_edit` / `end_edit` | `ctrl+p` as a priority binding: commit the active edit first (same pattern as `ctrl+s` save-and-stay), then open the picker. |
| Key bindings | Editor: `p` unused. Node config: `ctrl+p` unused. App: Textual's command palette is **on by default and uses `ctrl+p`**. | Turn the palette off (`ENABLE_COMMAND_PALETTE = False`) or move it to another key. |
| Paste handling | No `events.Paste` handler anywhere in `frontend/` | New. Drops arrive as bracketed paste. Parse quoting per terminal (Windows Terminal `"..."`, macOS `\ `, several files separated by spaces). |
| Headless (`aotn_cli.py`, `backend/run_service.py`) | `aotn run` with `--input KEY=VALUE`, which is "recorded for the run, consumed by workflow contracts once they exist"; `RunService.start(inputs=...)` passes them to `MasterState` | The hook for stage 3 already exists. Nothing consumes the inputs yet. |
| Contracts (`DISTRIBUTED_BUILD_PLAN.md` Step 4; `NODE_CONTRACT_PLAN.md` owner direction 2026-10-14) | Planned: typed declared inputs on Start; "one contract for every caller"; a required read with no writer and no declared workflow input is an error | The "exposed inputs" idea **is** the Step 4 contract. The Stash should not invent a parallel manifest. |

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
  normalizes it. If every piece is an existing path, the result is file
  entries; otherwise it is one text entry.
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
- **Insert:** in node config, highlight a field, press `ctrl+p`. The list shows
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

Order for filling each input, the same for every caller:

1. Explicit caller value (`--input k=v`, API body, trigger payload, the parent
   subworkflow node)
2. Inputs/preset file (`--inputs-file run.json`)
3. **Saved Stash binding on this machine** (input → entry id, stored per
   workflow in the data dir, *not* in the workflow JSON)
4. The contract's default
5. Required and still empty: **fail before the run starts**, with a clear exit
   code and a list of what's missing

Plus: `--input key=@stash:name` on the command line, and `file`-typed inputs
coerced through `file_reference()` with a check that the file exists.
Bindings are set in the TUI with the same `ctrl+p` picker, from the
Start/contract panel or a subworkflow node's "required inputs" section.

Result: set a workflow up once in the TUI, then `aotn run wf` works
unattended. On another machine you bind once and the same file runs unchanged.

## 5. Roadmap (very high level)

| Stage | Contents | Depends on | Rough size |
|---|---|---|---|
| **S1 — Stash core** | `StashManager`, `STASH_DIR`, paste parser, `accepted_types`, JSON export/import, unit tests | — | S |
| **S2 — Stash modal** | Full-screen modal (Drop/Paste + Entries), `p` from Editor, name/rename/delete | S1 | M |
| **S3 — Field insert** | `ctrl+p` in node config (palette turned off/moved), filtered picker, write to focused field, switch source to `Configured`, `path_hint` audit | S1, S2 | M |
| **S3b — CLI (optional)** | `aotn stash list/add/rm/export/import` | S1 | S |
| **S4 — Folder import** | Count/limits, refusal with numbers, grouped entries | S2 | S–M |
| **S5 — Contract integration** | Fill order, per-machine bindings, `@stash:`, fail-fast on missing inputs, binding UI on Start/subworkflow node | DISTRIBUTED Step 4 | L (most of it shared with Step 4 itself) |
| **S6 — Presets / sharing (exploratory)** | Bundle of values matched to a contract version; preview before applying; data only, never code | S5 | Undefined: design when needed |

S1–S4 are independent of the distributed roadmap and could slot in after
Phase 17 work. S5 should be designed **as part of** Step 4, not after it.

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

## 8. Risks

- **Terminal variance:** drop quoting differs by terminal and OS; the parser
  needs a fixture table per terminal.
- **SSH / remote:** pasted paths belong to the client machine; validate on drop.
- **Scope creep:** S6 ambitions must not bloat S1–S3. The JSON export format
  is the only forward-looking commitment in the near-term stages.
- **Focus edge cases:** `ctrl+p` during an active edit must commit cleanly
  (follow the save-and-stay pattern) and must not fight the focus-drift guard
  in `command_input.py`.
