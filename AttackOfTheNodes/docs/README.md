# AttackOfTheNodes Docs

**Start here.** README routes you to the right document for your task.
`TASK_INDEX.md` gives the minimum reading set, likely files, and focused test
commands for each task type. Open deeper references only when a closer document
points you there.

The active project is the Python/Textual app in `AttackOfTheNodes/`. Historical
tkinter/proof-of-concept material lives under `docs/archive/`.

---

## Choose Your Task

| If you need to... | Read first | Then read if needed |
|---|---|---|
| Add or change a node | `NODE_STANDARDS.md`, `AGENT_START_GUIDE.md` | `NODE_HELPER.md`, `PROJECT_KNOWLEDGE.md`, `ARCHITECTURE.md` |
| Fix frontend/UI behavior | `UI_QUICK_REFERENCE.md`, `AGENT_START_GUIDE.md` | `TUI_DESIGN.md`, `BACKEND_FRONTEND_BOUNDARY.md` |
| Change backend/runtime behavior | `ARCHITECTURE.md`, `SIGNAL_FLOW.md` | `PROJECT_KNOWLEDGE.md`, `BACKEND_FRONTEND_BOUNDARY.md` |
| Design or update node taxonomy | `PHASE_17_NODE_VISUAL_IDENTITY.md`, `NODE_CATALOG.md`, `NODE_STANDARDS.md` | `TASK_INDEX.md`, `BACKEND_FRONTEND_BOUNDARY.md` |
| Continue Phase 17 node identity | `PHASE_17_NODE_VISUAL_IDENTITY.md`, `TASK_INDEX.md` | `UI_QUICK_REFERENCE.md`, `TUI_DESIGN.md`, `BACKEND_FRONTEND_BOUNDARY.md` |
| Continue the roadmap | `AGENT_HANDOFF.md`, `MASTER_BUILD_PLAN.md` | `SESSION_LOG.md`, `PROJECT_BACKLOG.md` |
| Update docs | `README.md`, `TASK_INDEX.md`, `DOCS_MIGRATION_NOTES.md` | — |
| Check what changed recently | `SESSION_LOG.md` | `archive/SESSION_LOG_HISTORY.md` |

---

## Document Directory

One-line purpose for every file. Use this to find the right document without
opening the wrong ones. Scan the section headings first, then the table in that
section.

### Roadmap and Session State

Read these to orient on current project status before starting any substantial
work.

| File | What it contains | When to open it |
|---|---|---|
| `AGENT_HANDOFF.md` | Current active phase, key recent design decisions, and agent entry checklist | Start of a session when you need a fast current-state summary |
| `MASTER_BUILD_PLAN.md` | Full roadmap phase list with status, current phase detail (done/remaining/todo), and later phase sketches | Continuing the roadmap or checking whether work belongs in the current phase |
| `SESSION_LOG.md` | What changed in the most recent sessions; one entry per completed work block | Checking what was done before you arrived, or logging your own completed changes |

### Node Authoring

Read these before adding, changing, or designing nodes.

| File | What it contains | When to open it |
|---|---|---|
| `NODE_STANDARDS.md` | Node classification rule (group/separate/mode-select/direct-add), I/O source and routing model, config tab layout, authoring checklist | Before defining any new node type or changing an existing node's I/O |
| `AGENT_START_GUIDE.md` | Step-by-step checklists for adding nodes, making config render correctly, keyboard/modal rules, file I/O patterns | When adding a node or fixing config UI and you want the quickest correct path |
| `NODE_HELPER.md` | YAML spec format, `create_node.py` / `check_node.py` / `check_ui.py` commands, and what the generator produces | When using `aotn_node_helper` to generate a node, or adding a new spec section |
| `NODE_CATALOG.md` | Complete node inventory — every implemented, planned, deferred, and concept node with status, group, and mapping from current registered types | Checking whether a node idea already exists, recording a new node idea, or planning overhaul scope |
| `PHASE_17_NODE_VISUAL_IDENTITY.md` | Core simplification rule, five-family taxonomy with I/O switch and section headers, two-level group picker design, keyboard flows, `group`/`selector_section` metadata fields, AI model approach | Designing where a node lives in the taxonomy, implementing the selector restructure or group picker, or adding Phase 17 identity metadata |

### Architecture and Boundaries

Read these before changing how components talk to each other, before adding
backend code driven by a UI need, or when diagnosing a runtime bug.

| File | What it contains | When to open it |
|---|---|---|
| `BACKEND_FRONTEND_BOUNDARY.md` | What backend owns vs frontend owns; tombstone design decision; Phase B migration plan | Before any backend change motivated by UI behavior, or before moving UI logic to backend services |
| `ARCHITECTURE.md` | Component responsibilities, execution pipeline, MasterState, supervisor/branch model, MemoryBank, persistence | When you need to understand how the runtime hangs together before changing it |
| `SIGNAL_FLOW.md` | Runtime event and data flow: EventBus, supervisor execution path, OutputManager, screen subscriptions | When diagnosing an event not arriving, or tracing data through the execution chain |
| `PROJECT_KNOWLEDGE.md` | Current-state reference: Python 3.14, Textual 8.2.7, asyncio, entry point, test conventions, registered node families | Quick fact-check on versions, file conventions, or data-flow patterns |

### Frontend Reference

Read these for frontend work. Start with `UI_QUICK_REFERENCE.md`; open
`TUI_DESIGN.md` only when you need full screen/widget detail.

| File | What it contains | When to open it |
|---|---|---|
| `UI_QUICK_REFERENCE.md` | Editor keybindings, command-mode rules, and modal navigation summary | Start here for any frontend or keyboard-flow fix |
| `TUI_DESIGN.md` | Full Textual conventions: async setup, screen lifecycle, widget layout, keyboard handling, modal patterns, field type mapping | When the quick reference isn't enough — full screen or widget design work |
| `FILE_TREE.md` | Tracked file map for the current workspace | Finding where a file lives or verifying the directory structure is still current |

### Planning and Backlog

Read these before starting a new major project or moving/archiving docs.

| File | What it contains | When to open it |
|---|---|---|
| `PROJECT_BACKLOG.md` | Deferred projects with full design specs: boundary cleanup, tombstone restore, runtime resources, typed vault, toast system, AI sessions | Before starting any work listed here — it may already be designed; check before re-designing |
| `TASK_INDEX.md` | Task-first reading lists, likely files per task, focused `pytest -k` commands, helper tool commands | After choosing a task type — the minimum reading set and the right verification pattern |
| `DOCS_MIGRATION_NOTES.md` | Record of documentation moves, collapses, and archives during overhauls | When moving, merging, archiving, or deleting a doc — log it here |

---

## Archive

Historical documents. Do not open these by default. Open only when you need
context that is not covered by the active docs.

| File | What it contains | When to open it |
|---|---|---|
| `archive/BUILD_PLAN_HISTORY.md` | Completed phase details collapsed out of `MASTER_BUILD_PLAN.md` | When you need deep history on a completed phase (0–16, FA-0–FA-5) |
| `archive/SESSION_LOG_HISTORY.md` | Older session log entries collapsed out of `SESSION_LOG.md` | When you need context on work done before the most recent sessions |
| `archive/V05_BUILD_PLAN.md` | Historical Python/tkinter proof-of-concept plan | Background context only — not the current implementation |
| `archive/plans/FRONTEND_AUDIT_BUILD_PLAN.md` | Completed frontend audit plan (FA-0–FA-5); active rules now live in `AGENT_START_GUIDE.md` and `TUI_DESIGN.md` | Only if tracing why a frontend convention exists |
| `archive/plans/RUNTIME_RESOURCE_SESSION.md` | Original design notes for the `RunSession` resource lifecycle | Core implementation is done; open if you need the extended design (hidden helpers, listening resources) |
| `archive/plans/USER_FRIENDLY_POLISH_BUILD_PLAN.md` | Completed visual/navigation polish plan; roadmap is now in `MASTER_BUILD_PLAN.md` | Only if tracing why a specific visual decision was made |

---

## Documentation Rules

- Keep the default read path small. Summarize in active docs; link to archives
  for deep history.
- Update `SESSION_LOG.md` after every completed change.
- Update `MASTER_BUILD_PLAN.md` when roadmap status or phase order changes.
- Update `TASK_INDEX.md` when task routes, helper commands, or focused checks
  change.
- Add an entry to `DOCS_MIGRATION_NOTES.md` when moving, collapsing, archiving,
  or deleting docs.
- Add a row to the Document Directory above when a new active doc is created.
