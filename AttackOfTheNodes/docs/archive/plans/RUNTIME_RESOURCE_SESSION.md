# Runtime Resource Session — Design Note

**Status:** Implemented (core session, lifecycle wiring, validation, first
consumer). Hidden helper nodes and long-lived listener resources remain
future work.  
**Phase target:** Post-Phase 17, after the node overhaul settles file/resource subcategories.  
**Related docs:** `PROJECT_BACKLOG.md` ("Later Project — Runtime Resources And Hidden Helper Nodes"), `PHASE_17_NODE_VISUAL_IDENTITY.md` ("File Resource Direction"), `BACKEND_FRONTEND_BOUNDARY.md`

---

## Problem Statement

Future file input/output nodes, and eventually streaming, listening, and
browser-session nodes, need to hold runtime handles during a workflow run.
Those handles should open once, stay available to later nodes in the same
run, and close reliably when the run ends. No current component owns that
responsibility cleanly.

- `MasterState` coordinates run lifecycle but should not become a resource
  manager — it already owns supervisor orchestration, branch depth, timing
  accumulation, and completion detection.
- `MemoryBank` is intentionally ephemeral per-run key/value storage. File
  handles are not data values.
- `persistence.py` is intentionally dumb flat-file JSON I/O and must not
  become a resource manager.
- Saved workflow JSON must stay portable (paths and config references,
  never live handles).

---

## Proposed Object — `RunSession`

A lightweight per-run object that carries open resource handles for the
duration of one workflow run. It is not a general service; it is a container
with a clear lifecycle boundary.

### Responsibilities

- Open and cache resource handles on demand (files, streams, browser
  sessions, listeners — initially files).
- Return the same handle when two nodes in the same run request the same
  path/resource key.
- Close all handles reliably when the run ends, whether the run finished
  cleanly, errored, or was terminated.
- Expose a `validate_resource(ref)` check that nodes or the validator can
  call before execution to report missing or unavailable files without
  raising a runtime error.

### What `RunSession` does NOT own

- Path selection or file-picker UI — the frontend owns those.
- Persistence, settings, or workflow saves — `persistence.py` and
  `SaveManager` own those.
- Node graph traversal, branch depth, or supervisor state.
- Any import from `frontend/`.

### Likely interface sketch (not final)

```python
class RunSession:
    def __init__(self, run_id: str) -> None: ...

    def open_file(self, path: str, mode: str = "r") -> IO:
        """Open a file handle, caching it by (path, mode) for reuse."""

    def get_resource(self, key: str) -> Any | None:
        """Return a previously registered resource by key, or None."""

    def register_resource(self, key: str, handle: Any) -> None:
        """Register an arbitrary handle under a user-defined key."""

    def validate_path(self, path: str) -> tuple[bool, str]:
        """Return (ok, reason). Checks existence/accessibility without opening."""

    def close_all(self) -> None:
        """Close every open handle. Called by MasterState at run finalization."""

    @property
    def run_id(self) -> str: ...
```

---

## Lifecycle Ownership

```
MasterState.start_workflow()
    -> generate run_id
    -> create RunSession(run_id)
    -> pass session into Supervisor constructors (alongside MemoryBank)

Supervisor run loop
    -> passes session reference into NodeContext on each execute() call

NodeContext (updated)
    -> context.run_session: RunSession   # new field

Node.execute(context)
    -> calls context.run_session.open_file(path) or .get_resource(key)
    -> receives handle; does not open its own files directly

MasterState._check_run_completion()
    -> run_session.close_all()            # before OutputManager.finalize_run
    -> run_session = None                 # release reference
```

Key invariants:
- `RunSession` is created once per run, immediately before supervisor
  creation.
- It is passed by reference into every supervisor and into every
  `NodeContext` for that run.
- `close_all()` is always called — on FINISHED, ERROR, and forced
  termination — before the in-memory run caches are evicted.
- No component outside `MasterState` holds a reference to `RunSession`
  after `close_all()`. Nodes receive it only through `NodeContext` while
  they are executing.

---

## How Nodes Receive Paths And Resource References

Workflow saves store **portable config** only: path strings, resource keys,
or user-supplied identifiers — never live handles.

When a node executes:

1. The node reads its `config["file_path"]` (or equivalent field) from the
   `NodeContext` inputs as it always would.
2. The node calls `context.run_session.open_file(path)` to get a handle.
3. On subsequent calls with the same path/mode, `RunSession` returns the
   cached handle rather than re-opening.
4. The node uses the handle and calls `signal_done`; it does not close the
   handle.

This means:
- A `FileReaderNode` early in the workflow can open a log file; a later
  `FileWriterNode` on a different branch can append to the same handle
  without racing on open/close.
- Nodes stay graph-ignorant — they do not know whether another node already
  opened the file.

---

## Validation — Missing Or Unavailable Files

Pre-run validation (via `Validator`) should be extended to recognize file
fields in `config_schema` (e.g., a schema key with a `"file_path"` hint
type) and call `RunSession.validate_path(path)` or an equivalent static
check.

Validation rules:
- A **missing path** (empty config field for a required file input) is an
  error, like a missing required config key.
- An **inaccessible path** (file does not exist or lacks read permission) at
  validation time is a **warning**, not a hard error — the file may be
  created by a preceding node or mounted at runtime. The validator should
  note that the path was not found at validation time.
- An inaccessible path that causes `open_file()` to fail at actual node
  execution triggers `context.signal_error()`, which enters the normal
  recovery flow (RETRY / SKIP / TERMINATE_BRANCH / TERMINATE_WORKFLOW).

Error messages should name the config field and the path string, and point
back to the visible node (not to `RunSession` internals).

---

## Frontend File Picking Stays Frontend-Owned

The backend does not open OS dialogs, inspect platform paths beyond
`os.path.exists`, or know about Textual widgets. Path picking belongs in
the frontend for the same reasons that other UI interactions do:

- A CLI frontend would use `argparse` paths; a web frontend would use a
  browser upload or a path text input; the Textual TUI would use a picker
  dialog or a `file_path` command input. These are all distinct UX choices
  with no shared implementation.
- The backend engine should accept any path string that a node's config
  contains, regardless of how the user provided it.
- `BACKEND_FRONTEND_BOUNDARY.md` rule: path picking belongs in the
  frontend; backend services accept paths.

The frontend affordance for file fields (a placeholder prompt, a picker
key, a file-browser dialog) is a Phase 17 or post-Phase 17 config UI
concern. When it lands, it writes a path string into the node's config and
the backend never sees the dialog.

---

## Backend Resource Management Must Stay UI-Agnostic

`RunSession` must not import or reference anything from `frontend/`. This
is the same invariant that applies to every backend component.

Rationale:
- Testability: backend execution tests should be able to run `RunSession`
  under `pytest` without a Textual app or screen.
- Portability: a future CLI or API frontend must be able to drive
  `MasterState` and receive the same resource lifecycle guarantees without
  a TUI.
- Separation of concerns: frontend concerns are visual interaction,
  platform-specific dialogs, and TUI event routing. `RunSession` is a
  resource ledger.

---

## Forward Compatibility — Beyond Files

The `RunSession` design should support future resource types without
structural changes:

| Future resource | Likely `RunSession` API |
|---|---|
| Writable output file / stream | `open_file(path, mode="w")` — same interface, write mode |
| Network socket / HTTP session | `register_resource(key, session)` from a setup node |
| Browser session (playwright, etc.) | `register_resource("browser", browser)` |
| Folder watcher / listener | `register_resource("watcher", watcher)` |
| Keyboard / hotkey trigger | `register_resource("trigger_key", handler)` |

Long-lived listening resources (folder watchers, hotkey triggers) should be
opt-in and registered only when a node explicitly requests them during
execution. Idle workflows should not hold open watchers by default.

The `close_all()` method should iterate over all registered handles and
call the appropriate close/cleanup method. A small close-hook registry (a
list of `(handle, close_fn)` tuples) keeps this generic enough that
`RunSession` does not need to know about every future handle type at
compile time.

---

## Implemented Files

| File | Change |
|---|---|
| `backend/run_session.py` | New: `RunSession` class with `open_file`, `register_resource`, `get_resource`, `validate_path`, `close_all` |
| `backend/master_state.py` | Creates `RunSession` at run start; passes it to root and branch supervisors; calls `close_all()` in `_record_run` so every terminal path (FINISHED, supervisor error, forced termination) releases resources |
| `backend/supervisor.py` | Accepts `run_session` as a constructor arg; passes it into `NodeContext` |
| `backend/node_base.py` | `NodeContext.run_session: Optional[RunSession] = None` |
| `backend/validator.py` | File-path validation pass for schema fields with `path_hint: "file"` — empty required path is an error; path missing on disk is a warning |
| `backend/nodes/file_reader_node.py` | First consumer: `file_path` schema field carries `path_hint: "file"`; reads through `context.run_session` when available, falls back to direct read otherwise |
| `tests/test_run_session.py` | Unit tests (open/cache/validate/close_all/register) plus run-lifecycle and validator integration tests |

No changes were made to `frontend/`, `persistence.py`, or `save_manager.py`.

Implementation notes:

- Close hooks run in reverse registration order so dependent resources close
  before the resources they depend on.
- `open_file` caches by `(resolved path, mode)`; a cached handle that was
  externally closed is reopened transparently.
- Using a closed session raises `RuntimeError`, which a node surfaces through
  the normal `signal_error` recovery flow.
- `path_hint` is an extra schema key; `field_types.validate_config_schema`
  permits unknown extra keys, so no schema-validation change was needed.
- Write-mode caveat for future writer nodes: a cached `"w"` handle is only
  flushed when the session closes at run end. A node that reads the same
  path through a separate `"r"` handle mid-run may see partial data. When a
  file writer node lands, it should either flush after each write or the
  session should flush write handles before serving a read handle for the
  same path.

---

## What Should NOT Change

- Workflow saves remain portable JSON with path strings and config values,
  not handles.
- `persistence.py` remains raw JSON I/O and must not gain resource
  management behavior.
- `MemoryBank` remains a key/value data store for transient port data and
  named workflow variables, not a handle store.
- `MasterState` delegates resource lifecycle to `RunSession`; it does not
  manage individual handles itself.
- Phase 17 selector, editor, and metadata UI work is not blocked by this
  design. Phase 17 can name file and runtime-resource subcategories without
  implementing the session.
