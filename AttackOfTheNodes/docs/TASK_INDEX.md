# Task Index

`README.md` routes you to this file. This file gives the minimum reading set,
likely code files, and the focused `pytest -k` or helper commands for each task
type. Open the docs listed here, then open deeper references only if those docs
point you further.

## Design Or Update Node Taxonomy

Read:

- `PHASE_17_NODE_VISUAL_IDENTITY.md` — Core Simplification Rule, full expanded
  taxonomy, group picker UI design, keyboard flows, metadata conventions
- `NODE_STANDARDS.md` — Node Type Classification rule (when to group vs
  separate vs mode-select)
- `BACKEND_FRONTEND_BOUNDARY.md` — the `group` field is a frontend-only
  navigation concept; no backend component should branch on it

Likely files:

- `backend/node_identity.py`
- `backend/node_factory.py`
- `frontend/screens/node_selector.py`

Note: adding a node to an existing group requires only declaring the `group`
field on the node class. No selector code changes are needed. Single-member
groups auto-promote to direct-add entries.

## Add Or Change A Node

Read:

- `NODE_STANDARDS.md` — input source model, output routing model, dynamic form
  rules, and reference examples. Read this first before defining any new node.
- `AGENT_START_GUIDE.md`
- `NODE_HELPER.md` for helper spec details and generated-file behavior
- `PROJECT_KNOWLEDGE.md` sections: Node Metadata Contract, Data Flow Patterns,
  Registered Node Families

Likely files:

- `../aotn_node_helper/specs/<node_type>.yaml`
- `backend/nodes/<category>/<name>_node.py`
- `backend/nodes/__init__.py`
- `tests/generated/test_<node_type>.py`

Preferred path:

```bash
../.venv/bin/python ../aotn_node_helper/create_node.py ../aotn_node_helper/specs/<node_type>.yaml
../.venv/bin/python ../aotn_node_helper/check_node.py <node_type>
```

Use frontend edits only when the node needs structural UI derived from workflow
topology. Ordinary node fields should render from metadata and `config_schema`.

## Fix Frontend Or UI Behavior

Read:

- `UI_QUICK_REFERENCE.md`
- `AGENT_START_GUIDE.md` sections: Keyboard And Modal Rules, When Frontend Edits
  Are Needed
- `BACKEND_FRONTEND_BOUNDARY.md` if the fix is tempting you toward backend code

Likely files:

- `frontend/screens/`
- `frontend/widgets/`
- `frontend/styles.tcss`
- `frontend/node_io_display.py`
- `tests/test_debug_nodes.py`

Focused checks:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "<focused_behavior_name>"
```

Use shared helpers before per-screen code: command navigation, list navigation,
dynamic sections, notifications, and form generation.

Open `TUI_DESIGN.md` only when you need full screen details, Textual detours, or
layout-level conventions.

## Continue Phase 17 Node Visual Identity

Read:

- `PHASE_17_NODE_VISUAL_IDENTITY.md`
- `UI_QUICK_REFERENCE.md`
- `TUI_DESIGN.md` sections: Modal Screens, Editor bindings/node rows, Command
  Navigation
- `BACKEND_FRONTEND_BOUNDARY.md` before changing backend metadata shape for UI
  needs

Likely files:

- `backend/node_base.py`
- `backend/node_factory.py`
- `frontend/screens/node_selector.py`
- `frontend/widgets/node_card.py`
- `frontend/widgets/node_list.py`
- `frontend/styles.tcss`
- `frontend/screens/editor.py`
- `tests/test_debug_nodes.py`

Focused checks:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_selector or node_card or editor_depth or branch_end"
```

Implementation direction:

- Five backend families: `Inputs`, `Outputs`, `Flow Control`, `Utility`,
  `Complex`. Four selector tabs: `I/O` (Input/Output switch), `Flow Control`,
  `Utility`, `Complex`. AI is a subcategory tag, not a family.
- `group` and `selector_section` are frontend-only navigation metadata; no
  backend component should branch on them.
- Use metadata subcategories for filters; nodes may have multiple.
- Keep selector filters and editor row identity frontend-owned, but expose
  portable family/tag/icon/color/group/section metadata through `NodeFactory`.
- Preserve keyboard-first focus, autoscroll, cursor/highlight stability,
  validation markers, and Merge Beacon state indicators.

## Change Backend Or Runtime Behavior

Read:

- `ARCHITECTURE.md`
- `SIGNAL_FLOW.md`
- `PROJECT_KNOWLEDGE.md`
- `BACKEND_FRONTEND_BOUNDARY.md` when the change is requested by the UI

Likely files:

- `backend/workflow_map.py`
- `backend/master_state.py`
- `backend/supervisor.py`
- `backend/memory_bank.py`
- `backend/validator.py`
- `backend/save_manager.py`
- `tests/test_debug_nodes.py`

Focused checks:

```bash
../.venv/bin/python -m compileall -q .
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "<runtime_behavior_name>"
```

Before committing broad runtime changes, run the full debug suite.

## Change File I/O Or Workflow Persistence

Read:

- `AGENT_START_GUIDE.md` section: File I/O UI Pattern
- `ARCHITECTURE.md` sections: persistence, SaveManager, WorkflowMap
- `BACKEND_FRONTEND_BOUNDARY.md`

Likely files:

- `frontend/file_io.py`
- `frontend/screens/workflow_library.py`
- `frontend/screens/user_input.py`
- `backend/save_manager.py`
- `backend/persistence.py`

Rule: path picking belongs in the frontend; backend services accept paths.

## Update Config UI Or Form Generation

Read:

- `AGENT_START_GUIDE.md` sections: Make Node Config Render Correctly, Keyboard
  And Modal Rules
- `UI_QUICK_REFERENCE.md`
- `NODE_HELPER.md` section: Direction: UI Standardization Helper, when adding
  helper support for config UI tests or screen scaffolds
- `TUI_DESIGN.md` sections: Field Type Mapping, Command Navigation, only when
  changing detailed renderer behavior

Likely files:

- `frontend/screens/node_config.py`
- `frontend/widgets/form_generator.py`
- `frontend/widgets/command_input.py`
- `frontend/widgets/command_navigation.py`
- `tests/test_debug_nodes.py`

Focused checks:

```bash
../.venv/bin/python -m pytest tests/test_debug_nodes.py -v -k "node_config or command_input or selection"
```

## Continue The Roadmap

Read:

- `AGENT_HANDOFF.md`
- `MASTER_BUILD_PLAN.md`
- `SESSION_LOG.md`

Optional deep history:

- `archive/BUILD_PLAN_HISTORY.md`
- `archive/SESSION_LOG_HISTORY.md`

Update `MASTER_BUILD_PLAN.md` and `SESSION_LOG.md` when a phase starts or
finishes.

## Update Documentation

Read:

- `README.md`
- `TASK_INDEX.md`
- `DOCS_MIGRATION_NOTES.md`

Likely files:

- `docs/*.md`
- `docs/archive/*.md`
- `docs/archive/plans/*.md`

Verification:

```bash
git diff --check
rg -n "<stale-folder-or-phase-pattern>" AttackOfTheNodes/docs AGENTS.md
find AttackOfTheNodes/docs -type f -name '*.md' | sort
```
