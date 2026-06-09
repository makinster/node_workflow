# AttackOfTheNodes File Tree

Generated from the current tracked workspace layout after the project folder
was simplified to `AttackOfTheNodes/`. Runtime data, logs, caches, virtual
environments, `.git/`, `.claude/`, and scratch files are omitted.

```text
node_workflow/
├── AttackOfTheNodes/
│   ├── backend/
│   │   ├── nodes/
│   │   │   ├── debug/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── counter_node.py
│   │   │   │   ├── deep_branch_node.py
│   │   │   │   ├── echo_node.py
│   │   │   │   ├── error_node.py
│   │   │   │   ├── logger_node.py
│   │   │   │   ├── memory_snapshot_node.py
│   │   │   │   ├── no_op_node.py
│   │   │   │   ├── probe_node.py
│   │   │   │   ├── random_branch_node.py
│   │   │   │   ├── repeat_node.py
│   │   │   │   ├── sleep_node.py
│   │   │   │   ├── tombstone_node.py
│   │   │   │   ├── variable_reader_node.py
│   │   │   │   └── variable_setter_node.py
│   │   │   ├── __init__.py
│   │   │   ├── branch_end_node.py
│   │   │   ├── branch_node.py
│   │   │   ├── chat_completion_node.py
│   │   │   ├── concat_node.py
│   │   │   ├── conditional_node.py
│   │   │   ├── embedding_node.py
│   │   │   ├── end_node.py
│   │   │   ├── file_reader_node.py
│   │   │   ├── get_variable_node.py
│   │   │   ├── image_generation_node.py
│   │   │   ├── merge_node.py
│   │   │   ├── set_variable_node.py
│   │   │   ├── start_node.py
│   │   │   ├── text_output_node.py
│   │   │   ├── user_text_input_node.py
│   │   │   └── wait_until_node.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   └── try_catch.py
│   │   ├── __init__.py
│   │   ├── configuration_manager.py
│   │   ├── error_handler.py
│   │   ├── event_bus.py
│   │   ├── events.py
│   │   ├── field_types.py
│   │   ├── master_state.py
│   │   ├── memory_bank.py
│   │   ├── node_base.py
│   │   ├── node_category.py
│   │   ├── node_factory.py
│   │   ├── output_entry.py
│   │   ├── output_manager.py
│   │   ├── persistence.py
│   │   ├── run_history.py
│   │   ├── save_manager.py
│   │   ├── supervisor.py
│   │   ├── validator.py
│   │   └── workflow_map.py
│   ├── docs/
│   │   ├── AGENT_HANDOFF.md
│   │   ├── AGENT_START_GUIDE.md
│   │   ├── ARCHITECTURE.md
│   │   ├── BACKEND_FRONTEND_BOUNDARY.md
│   │   ├── FILE_TREE.md
│   │   ├── FRONTEND_AUDIT_BUILD_PLAN.md
│   │   ├── MASTER_BUILD_PLAN.md
│   │   ├── PROJECT_BACKLOG.md
│   │   ├── PROJECT_KNOWLEDGE.md
│   │   ├── README.md
│   │   ├── SESSION_LOG.md
│   │   ├── SIGNAL_FLOW.md
│   │   ├── TUI_DESIGN.md
│   │   ├── USER_FRIENDLY_POLISH_BUILD_PLAN.md
│   │   └── V05_BUILD_PLAN.md
│   ├── frontend/
│   │   ├── screens/
│   │   │   ├── __init__.py
│   │   │   ├── branch_selector.py
│   │   │   ├── confirm.py
│   │   │   ├── editor.py
│   │   │   ├── error_details.py
│   │   │   ├── execution.py
│   │   │   ├── help.py
│   │   │   ├── memory_viewer.py
│   │   │   ├── merge_beacon_selector.py
│   │   │   ├── node_config.py
│   │   │   ├── node_selector.py
│   │   │   ├── output_viewer.py
│   │   │   ├── settings.py
│   │   │   ├── user_input.py
│   │   │   └── workflow_library.py
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── command_input.py
│   │   │   ├── command_navigation.py
│   │   │   ├── command_screen_mixin.py
│   │   │   ├── cursor_state.py
│   │   │   ├── dynamic_sections.py
│   │   │   ├── form_generator.py
│   │   │   ├── list_navigation.py
│   │   │   ├── node_card.py
│   │   │   ├── node_list.py
│   │   │   └── status_bar.py
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── editor_workflow_adapter.py
│   │   ├── file_io.py
│   │   ├── node_io_display.py
│   │   ├── notifications.py
│   │   ├── output_records.py
│   │   ├── styles.tcss
│   │   └── ui_state.py
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_debug_nodes.py
│   ├── workflows/
│   │   └── .gitkeep
│   ├── __init__.py
│   ├── demo_execution.py
│   ├── main.py
│   ├── pyproject.toml
│   ├── pytest.ini
│   ├── requirements.lock
│   ├── run_windows.cmd
│   ├── test_error_recovery.py
│   ├── test_execution.py
│   ├── test_v095_nodes.py
│   └── test_v09_managers.py
└── AGENTS.md
```

## Omitted Local/Runtime Paths

- `.git/`
- `.venv/`
- `.claude/`
- `__pycache__/`
- `.pytest_cache/`
- `AttackOfTheNodes/logs/`
- `AttackOfTheNodes/settings/`
- `AttackOfTheNodes/workflows/*.json`
- `AttackOfTheNodes/run_history/`
- `AttackOfTheNodes/run_outputs/`
- `AttackOfTheNodes/run_errors/`
- `AttackOfTheNodes/.venv-win/`
- `AttackOfTheNodes/attackofthenodes.egg-info/`
- local scratch files such as `AttackOfTheNodes/read_test.txt`

## Notes

- The active frontend is Textual under `frontend/screens/` and
  `frontend/widgets/`.
- `frontend/editor_workflow_adapter.py`, `frontend/node_io_display.py`, and
  frontend-owned selector/navigation helpers are where UI-only workflow display
  behavior belongs.
- `backend/nodes/branch_end_node.py` remains the persisted node type, but the
  user-facing app calls it **Merge Beacon**.
- `run_windows.cmd` is a Windows Command Prompt / PowerShell launcher that
  creates `.venv-win`, checks dependencies, and launches `main.py`.
- `requirements.lock` records the current venv freeze. `pyproject.toml` is the
  source dependency declaration.
