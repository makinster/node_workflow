# File Output Build Plan — File Nodes, Formatting, and OS Window Placement

**Created:** 2026-07-10
**Revised:** 2026-07-11 — design-review amendments: D2/D3/D4/D5 caveats,
new D11/D12, FO4/FO5/FO7 additions. No scope change.
**Branch:** `claude/output-nodes-file-windows-wq07q6` (merged to `main` 2026-07-11)
**Status:** planned — no phase started

Goal: output nodes that treat files as first-class workflow objects — write
them, format them human-friendly, open them in the user's default apps at
sensible screen positions (next to the AOTN terminal, on another monitor), and
close them — with the workflow acting as a mini file system that nodes share.

**Scope rule:** phases FO1–FO3 must be fully implementable and verifiable with
`compileall` + `pytest` on any OS. Phases FO4–FO6 contain Windows-only window
code that cannot be pytest-verified in the Linux dev environment; they ship
with unit tests against a fake adapter plus the manual Windows verification
protocol at the end of this document.

Execution rules (same as previous plans):

- Work phases in order; each phase is independently committable.
- Per phase: implement, add focused tests, run the focused check, log a
  `SESSION_LOG.md` entry, tick the phase checkbox here.
- Backend code must not import from `frontend`
  (see `BACKEND_FRONTEND_BOUNDARY.md`).
- New nodes go through `aotn_node_helper` YAML specs, not hand-rolled classes
  (see `NODE_HELPER.md`; `chat_completion_node` is the reference `execute()`).
- EventBus payloads stay JSON-serializable and carry `run_id`.
- When the plan completes, fold outcomes into `MASTER_BUILD_PLAN.md` /
  `PROJECT_BACKLOG.md` / `NODE_CATALOG.md` and archive this file under
  `archive/plans/` with a `DOCS_MIGRATION_NOTES.md` entry.

## Phase Checklist

- [x] FO1 — `file_output_node`: write + typed file reference (2026-07-11)
- [x] FO2 — Markdown/text formatting for humans (2026-07-11)
- [ ] FO3 — In-TUI file viewer (zero OS-window dependency)
- [ ] FO4 — `backend/window_manager.py` platform adapter
- [ ] FO5 — Launch + placement on `file_output_node`
- [ ] FO6 — `window_control_node`
- [ ] FO7 — Windows live verification + docs reconciliation

---

## Design Decisions and Reasoning

These decisions shape every phase. Recorded here so later sessions do not
re-litigate them; if one must change, update this section with the new
reasoning.

### D1 — `RunSession` IS the mini file system; do not build a new one

`backend/run_session.py` already opens and caches file handles per run
(`open_file`), holds arbitrary resources with close hooks
(`register_resource` / `get_resource`), and closes everything at run end
(`close_all`). Its own docstring anticipates this plan ("files now; streams,
listeners, and browser sessions later"), and `FileReaderNode` already consumes
it. Building a separate file-system layer would duplicate lifecycle logic and
create two sources of truth for "what does this run have open." Every new
capability here — written files, opened OS windows — registers in `RunSession`
and inherits run-end cleanup for free.

### D2 — Nodes pass typed `file` references, not paths or handles

The typed-vault design (`PROJECT_BACKLOG.md` → typed vault entries) stores a
type tag plus a string reference key; the real Python handle lives in
`RunSession` and is resolved with `get_resource(ref_key)`. File nodes follow
that model: `file_output_node` emits a `file` reference downstream/vault, and
downstream nodes (viewer, window control) resolve it. Reasoning: saves and
EventBus payloads must stay JSON-serializable (standing rule), handles must
die with the run, and reference keys give later nodes an unambiguous way to
say "that exact file," which D6 depends on.

Cross-run note: the file *on disk* outlives the run, but its `file` reference
(and RunSession handle) dies with the run. A later run that wants "the file
from last time" reconstructs from a saved path string — the same rule the
file reader already follows. No cross-run reference continuity is promised.

### D3 — Placement presets, not coordinates

Users configure `Open at: Right of AOTN / Left of AOTN / Other monitor /
Same monitor, right half / OS default` — never `x=1920`. The backend computes
pixels from monitor geometry plus AOTN's own window rect
(`kernel32.GetConsoleWindow()` on Windows). Reasoning: nobody knows their
pixel coordinates; coordinates break the moment a monitor is unplugged; and a
semantic preset vocabulary is OS-neutral, so a future macOS/Linux adapter
implements the same options instead of forcing a config-schema migration.

A preset defines a full target rect — **position and size** ("Same monitor,
right half" is a size claim). The FO4 geometry function returns both from the
start so the preset vocabulary never needs a breaking change.

**Windows Terminal caveat (2026-07-11):** on modern Windows the default
console host is Windows Terminal, where console apps run under ConPTY and
`kernel32.GetConsoleWindow()` returns a *hidden pseudo-console window* whose
rect is not the visible terminal's. Placement relative to AOTN computed from
it is wrong on exactly the machine FO7 runs on. FO4 must resolve the real
terminal window (e.g. walk the parent-process chain to the
`WindowsTerminal.exe` top-level window, falling back to `GetConsoleWindow()`
under legacy conhost), and FO7 must verify placement under **both** hosts.
If the real window cannot be resolved, AOTN-relative presets degrade to their
monitor-relative equivalents with a logged warning.

### D4 — Window discovery by launch-time snapshot diff, stored once

The reviewed pywin32 proposal found windows with `EnumWindows` + title
substring. Title matching is fragile (Excel shows "budget - Excel", not
"budget.xlsx"; titles vary by app and locale). Instead: snapshot visible
top-level windows, launch the file, poll for the *new* window with a timeout,
fall back to title-contains-filename only if the diff is ambiguous (e.g.
single-process apps like Excel reusing an existing window). The resulting
HWND is registered in `RunSession` under the file's reference key and **never
re-searched**. Reasoning: discovery is unreliable, so do it exactly once at
the moment it is most reliable (immediately after launch) and treat the
result as a run resource thereafter.

Discovery will still misfire sometimes — browsers open files as a tab in an
existing window (no new top-level HWND at all), and an unrelated window
appearing during the poll can be misattributed. Standing rule: **discovery
failure is never a node error.** The file is opened; placement/control
degrade to "opened but unplaced" with a warning, and no `WindowRef` is
registered (FO6 then soft-errors per its own rule).

### D5 — pywin32 is an optional, guarded dependency; unsupported OS degrades

Project deps are currently just `textual`. The dev environment, CI, and
tests run on Linux; an unconditional pywin32 dependency breaks all of them.
The Windows adapter imports pywin32 lazily behind `platform.system()`; other
platforms get a fallback adapter that still opens files (`xdg-open` / `open`)
but no-ops placement with a logged warning. The validator warns (not errors)
when a workflow uses placement on an unsupported platform — same pattern as
the existing `use_chat_session` warning. Reasoning: workflows must stay
portable documents; a workflow authored on Windows should still *run*
elsewhere, just without window choreography.

**pywin32 vs raw ctypes — decision recorded (2026-07-11):** this project has
a precedent for avoiding dependencies (`backend/llm_provider.py` is a raw
HTTPS client rather than the Anthropic SDK; deps are just `textual`), and
everything FO4 needs is reachable via stdlib `ctypes.windll`. The decision is
**pywin32 as an optional extra anyway**: window enumeration, monitor
geometry, and message sending via raw ctypes are verbose and error-prone,
and this code can only be verified manually on Windows (FO7) — the
maintenance risk of hand-rolled ctypes outweighs the zero-dep purism here.
Unlike the LLM client (hot path, exercised every run, testable), the window
adapter is cold, optional, and unverifiable in CI. Revisit only if the
optional-extra install proves a real friction point for users.

### D6 — Target windows by file identity, never by app type

A downstream node controls "the window showing `budget.xlsx`" (resolved via
its `file` reference → `RunSession` → stored HWND), never "any open Excel."
Reasoning: workflows are file-centric; two nodes or two runs touching
different `.txt` files must not grab each other's windows. App-type targeting
is a race condition dressed up as a feature.

### D7 — No virtual desktops (pyvda) in v1

pyvda relies on undocumented Windows internals and breaks across Windows
feature updates. The stated core use case — "open the file next to my
terminal / on my other monitor" — never needs it. Deferred to the backlog;
the adapter protocol leaves room to add a `desktop` capability later.

### D8 — TUI viewer before OS windows

Textual renders Markdown natively, so "show me this md file, human-friendly"
needs zero OS code — an output node fires an event and the frontend opens a
viewer screen. That covers text/md on every platform; OS window launching is
only *required* for what the terminal cannot render (images, spreadsheets,
PDFs). Reasoning: it front-loads the phases that are cheap, cross-platform,
and pytest-verifiable in this repo's Linux environment, and it gives the
feature a working v1 before any Windows-specific risk is taken.

### D9 — Declarative placement on the output node; a separate small control node

The common case — "write the file and open it over there" — is one node with
config, not a chain of imperative move/focus/minimize nodes. A separate
`window_control_node` exists only for workflows that choreograph windows
mid-run (focus after a later step, close when a phase completes). Reasoning:
the 5-action `control_window(hwnd, action, …)` API in the reviewed proposal
is a good *adapter* surface but a bad *node* surface; per `NODE_STANDARDS.md`
classification, the mainline behavior belongs as config on one node, with the
rare imperative verbs split into one utility node rather than five.

### D10 — Window management lives in the backend, not the frontend

Opening and placing an OS window is a node side effect during execution —
like an HTTP request — not editor UI. It goes in `backend/window_manager.py`
behind a small protocol, created per platform by a factory, and must never
import Textual. Per `BACKEND_FRONTEND_BOUNDARY.md`, the frontend's only role
is config affordances (path pickers, preset dropdowns).

### D11 — Window management is a *local-execution* capability (2026-07-11)

D10 is correct for today's deployment (backend and TUI in one process on the
user's machine) and for the headless CLI direction. But under
`PROJECT_BACKLOG.md` → Multi-Frontend Expansion, the backend becomes a
standalone server — and then **the backend host and the user's display are no
longer the same place**: `open_path` would open Excel on the server, and the
AOTN window rect would belong to the server's console (or nothing).

Recorded so future sessions neither re-litigate D10 nor entrench direct
calls that block the server split:

- In a remote-backend deployment, window choreography migrates behind the
  EventBus — the node emits a `WINDOW_ACTION_REQUESTED`-style JSON event and
  a *local effector* (the frontend, or a thin local agent) executes it. This
  is the same pattern FO3 already uses for the viewer.
- The FO4 protocol and the D3 preset vocabulary are the stable surface; only
  the call site relocates. Keep the adapter free of `MasterState`/run-state
  coupling so it can be lifted behind an event boundary unchanged.
- `capabilities()` is the hook that will declare display access: a backend
  with no local display reports no window capabilities, and the existing D5
  validator warning covers it with no new mechanism.

### D12 — Windows that outlive the run are unmanaged orphans

With `Close when run ends` off (the default, per FO5), the OS window stays
open after `RunSession.close_all()` — but its `WindowRef` registration dies
with the run, so a *later* run's `window_control_node` cannot target it.
This is intentional, documented behavior, not a bug: the run hands the
window to the user and forgets it. Anything smarter (cross-run window
adoption) would require re-discovery, which D4 forbids.

---

## Phase FO1 — `file_output_node`: Write + Typed File Reference

Goal: an Outputs-family node that takes content (upstream payload / vault /
configured), writes it to a path (text or binary), registers the handle in
`RunSession`, and emits a typed `file` reference downstream/vault. No
launching yet.

Why first: it is the core output primitive every later phase consumes, it is
pure-Python and fully testable here, and it exercises the helper generator's
new standardized output model on a fresh node.

Tasks:

1. Helper spec `../aotn_node_helper/specs/file_output_node.yaml`: content
   input (upstream/vault/configured), file path (configured with
   `path_hint: "file"`, or upstream/vault `file` reference), write mode
   (overwrite / append / create-unique), binary toggle for image bytes.
2. Hand-write `execute()` (like `chat_completion_node`): write via
   `context.run_session.open_file` when available, direct `Path` I/O
   otherwise; emit the `file` reference per D2.
3. Validator: reuse existing `path_hint: "file"` checks; empty required
   path = error.
4. Retire or absorb the `example_file_instance_node` stub — it was the
   scaffold for exactly this node; keeping both would leave a dead example
   masquerading as a real capability. Decide during implementation whether
   the example spec is still needed by helper tests.

Likely files: `../aotn_node_helper/specs/file_output_node.yaml`,
`backend/nodes/io/file_output_node.py`, `backend/nodes/__init__.py`,
`tests/generated/test_file_output_node.py`, `tests/test_run_session.py`.

Focused check:

```bash
../.venv/bin/python ../aotn_node_helper/check_node.py file_output_node
../.venv/bin/python -m pytest tests/generated/test_file_output_node.py tests/test_run_session.py -v
```

Exit criteria: round-trip test writes text and binary content, emits a
resolvable `file` reference, and the handle closes at `close_all()`.

## Phase FO2 — Markdown/Text Formatting for Humans

Goal: format text as clean, human-friendly Markdown (normalize headings,
wrap, tidy lists/tables) so a workflow can pipe LLM or raw text output through
a formatter before writing/viewing it.

Decision to make at implementation time, per the `NODE_STANDARDS.md`
classification rule (group vs separate vs mode-select): extend
`text_transform_node` with markdown modes **or** add a `markdown_format_node`.
Default expectation is mode-select on the existing transform node — formatting
is a pure string→string transform, and a new node type is only justified if
the config surface (wrap width, heading style, etc.) would bloat the shared
node.

Why a pure transform: formatting must not be welded into `file_output_node`
(D9 altitude reasoning applies — composition over mega-nodes), and pure
functions are trivially testable.

Likely files: `backend/nodes/data/text_transform_node.py` or a new spec +
node, matching tests.

Focused check: node's generated/focused pytest slice.

Exit criteria: given messy markdown-ish text, output renders cleanly in both
the FO3 viewer and an external editor.

## Phase FO3 — In-TUI File Viewer

Goal: an output-node option (or small viewer node) that displays a text/md
file inside AOTN in a Textual Markdown/text viewer screen.

Why: per D8 this is the zero-OS-dependency "open the file" for text content,
verifiable with Textual `run_test` pilots on Linux.

Design constraints:

- The node cannot import frontend code. It emits an EventBus event (e.g.
  `FILE_VIEW_REQUESTED`) with a JSON payload: `run_id`, path, reference key,
  render hint (`markdown` / `plain`).
- The frontend subscribes (like `USER_INPUT_NEEDED`) and pushes a viewer
  screen; headless/no-frontend runs simply have no subscriber and the event
  is inert — no validator error.

Likely files: `backend/event_bus.py` (event name), node spec/class,
`frontend/screens/` (new viewer screen), `frontend/app.py` subscription,
`tests/test_debug_nodes.py`.

Focused check:

```bash
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "file_view"
```

Exit criteria: run a workflow → viewer screen opens rendering the md; ESC
closes; no backend→frontend import appears.

## Phase FO4 — `backend/window_manager.py` Platform Adapter

Goal: the OS abstraction, with no node wiring yet.

Protocol (small on purpose, per D9):

- `open_path(path, placement) -> WindowRef | None` — launch in the OS-default
  app, discover the window per D4, apply the placement preset per D3.
- `focus(ref)`, `minimize(ref)`, `close(ref)`.
- `capabilities() -> set[str]` — lets the validator warn per D5 without the
  frontend knowing OS details.

Implementations:

- `WindowsWindowManager`: `os.startfile` / `start` launch, pywin32 guarded
  import, snapshot-diff discovery with timeout + title fallback, monitor
  geometry via `EnumDisplayMonitors`, own-window rect per the D3 Windows
  Terminal caveat (parent-process walk to the real terminal window,
  `GetConsoleWindow` fallback under legacy conhost), `WM_CLOSE` for close.
- `FallbackWindowManager`: `xdg-open` / `open` launch, placement no-ops with
  a logged warning, `close` no-op (no handle to close).
- `get_window_manager()` factory keyed on `platform.system()`.

Testing: unit tests cover the factory, the fallback manager, preset →
geometry math (pure function, fully testable with fake monitor rects), and a
`FakeWindowManager` used by FO5/FO6 node tests. The pywin32 branch is
import-guarded so `compileall` passes on Linux; its behavior is verified
manually in FO7.

Likely files: `backend/window_manager.py`, `tests/test_window_manager.py`,
`pyproject.toml` (optional `[project.optional-dependencies] windows` extra).

Exit criteria: full suite green on Linux with no pywin32 installed; geometry
math covered (each preset yields a full position + size rect, per D3); fake
adapter available for node tests; adapter has no `MasterState`/run-state
coupling (per D11, it must be liftable behind an event boundary unchanged).

## Phase FO5 — Launch + Placement on `file_output_node`

Goal: the payoff — "write this md/image and open it to the right of AOTN."

Tasks:

1. Config additions: `Open after write` checkbox; placement preset select
   (visible when open is on); `Close when run ends` toggle (default **off** —
   the user usually wants to look at the result after the run; run-end
   cleanup is opt-in, unlike file handles which always close).
2. Execute path: after writing, call `window_manager.open_path`; register the
   returned `WindowRef` in `RunSession` under the file reference key
   (`register_resource(f"window:{ref_key}", ...)`) with a close hook only
   when `Close when run ends` is on.
3. Validator: warn when open/placement is configured and the current
   platform's `capabilities()` lacks it (D5).
4. Document that `Open after write` inside a repeat/counter loop opens one
   window per iteration (with `create-unique` write mode, one per file). A
   validator warning for open-after-write on a loop path is a backlog item,
   not FO5 scope — loop detection is not free.

Node tests run against `FakeWindowManager` — they assert the calls and the
RunSession registration, not real windows. Discovery failure (adapter
returns `None`) must leave the node successful with a warning — never a node
error (D4).

Likely files: `file_output_node` spec + class, `backend/master_state.py` or
node context wiring if the manager is session-scoped,
`tests/generated/test_file_output_node.py`.

Exit criteria: with the fake adapter, a run opens-and-places on execute,
leaves the window registered, and closes it at run end only when configured.

## Phase FO6 — `window_control_node`

Goal: a small Utility node for mid-run choreography: action select
(focus / minimize / close), target = a `file` reference from upstream/vault.
Resolves the stored `WindowRef` via `RunSession` per D6; erroring softly
(warning + pass-through) when the window was never opened or is already gone,
since window state is inherently racy against the user.

Likely files: new spec + node under `backend/nodes/io/`, generated tests with
`FakeWindowManager`.

Exit criteria: focus/minimize/close dispatch to the adapter by reference;
missing-window behavior covered by tests.

## Phase FO7 — Windows Live Verification + Docs Reconciliation

Manual protocol, run on the user's Windows machine (cannot be automated
here):

1. Single monitor: md file → `Right of AOTN`; verify side-by-side placement.
2. Multi-monitor: image → `Other monitor`; verify it lands there and the
   preset math respects mixed resolutions.
3. Single-process app (Excel with a workbook already open): verify discovery
   falls back correctly and does not steal the pre-existing window.
4. `Close when run ends` on and off; `window_control_node` close mid-run.
5. Slow-launching app: discovery timeout produces a warning, not a hang.
6. Host coverage: repeat placement checks under **Windows Terminal** and
   legacy **conhost** — the AOTN-rect resolution differs between them (D3
   caveat) and Windows Terminal is the default on the target machine.
7. Focus fight: `file_output_node` (open after write) directly upstream of a
   `user_text_input_node` — the opened window steals OS focus from the
   terminal right as the TUI prompts for input. Verify the user can recover
   focus and answer; note observed behavior for a possible "refocus AOTN
   after prompt" follow-up.

Docs: fold outcomes into `MASTER_BUILD_PLAN.md`, `NODE_CATALOG.md`,
`PROJECT_BACKLOG.md` (defer pyvda/macOS/Linux adapters there), update
`TASK_INDEX.md` with a file/window task route, archive this plan with a
`DOCS_MIGRATION_NOTES.md` entry. In `NODE_CATALOG.md`, resolve the deferred
**Window Focus** entry explicitly: it is superseded by `window_control_node`,
which scopes focus to workflow-owned file windows per D6 — arbitrary
named-app-window targeting stays out of the catalog.

---

## Out of Scope (Deferred to Backlog)

- Virtual desktop moves (pyvda) — D7.
- macOS (`pyobjc`/AppleScript) and Linux (`ewmh`/`xdotool`) window adapters —
  the protocol and preset vocabulary are designed for them, but no stub
  classes ship until one is actually implemented.
- Watch/trigger nodes on file changes — belongs to the Always-Running Trigger
  Watcher direction in `PROJECT_BACKLOG.md`.
- Rich in-TUI image preview (terminal graphics protocols) — revisit only if
  the OS-open path proves insufficient for images.
