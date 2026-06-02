# AttackOfTheNodes File Tree

Generated from the current workspace source layout during Phase 10
documentation modernization. Runtime data, logs, caches, virtual environments,
`.git/`, `.claude/`, and scratch files are omitted.

```text
node_workflow/
├── .gitignore
├── AGENTS.md
├── docs/
│   ├── AGENT_HANDOFF.md
│   ├── ARCHITECTURE.md
│   ├── BACKEND_FRONTEND_BOUNDARY.md
│   ├── FILE_TREE.md
│   ├── FRONTEND_AUDIT_BUILD_PLAN.md
│   ├── MASTER_BUILD_PLAN.md
│   ├── PROJECT_BACKLOG.md
│   ├── PROJECT_KNOWLEDGE.md
│   ├── README.md
│   ├── SESSION_LOG.md
│   ├── SIGNAL_FLOW.md
│   ├── TUI_DESIGN.md
│   └── V05_BUILD_PLAN.md
└── attackofthenodes_v05/
    ├── __init__.py
    ├── demo_execution.py
    ├── main.py
    ├── pyproject.toml
    ├── pytest.ini
    ├── requirements.lock
    ├── test_error_recovery.py
    ├── test_execution.py
    ├── test_v095_nodes.py
    ├── test_v09_managers.py
    ├── backend/
    │   ├── __init__.py
    │   ├── configuration_manager.py
    │   ├── error_handler.py
    │   ├── event_bus.py
    │   ├── events.py
    │   ├── field_types.py
    │   ├── master_state.py
    │   ├── memory_bank.py
    │   ├── node_base.py
    │   ├── node_category.py
    │   ├── node_factory.py
    │   ├── output_entry.py
    │   ├── output_manager.py
    │   ├── persistence.py
    │   ├── run_history.py
    │   ├── save_manager.py
    │   ├── supervisor.py
    │   ├── validator.py
    │   ├── workflow_map.py
    │   ├── utils/
    │   │   ├── __init__.py
    │   │   └── try_catch.py
    │   └── nodes/
    │       ├── __init__.py
    │       ├── branch_end_node.py
    │       ├── branch_node.py
    │       ├── chat_completion_node.py
    │       ├── concat_node.py
    │       ├── conditional_node.py
    │       ├── embedding_node.py
    │       ├── end_node.py
    │       ├── file_reader_node.py
    │       ├── get_variable_node.py
    │       ├── image_generation_node.py
    │       ├── merge_node.py
    │       ├── set_variable_node.py
    │       ├── start_node.py
    │       ├── text_output_node.py
    │       ├── user_text_input_node.py
    │       ├── wait_until_node.py
    │       └── debug/
    │           ├── __init__.py
    │           ├── counter_node.py
    │           ├── deep_branch_node.py
    │           ├── echo_node.py
    │           ├── error_node.py
    │           ├── logger_node.py
    │           ├── memory_snapshot_node.py
    │           ├── no_op_node.py
    │           ├── probe_node.py
    │           ├── random_branch_node.py
    │           ├── repeat_node.py
    │           ├── sleep_node.py
    │           ├── tombstone_node.py
    │           ├── variable_reader_node.py
    │           └── variable_setter_node.py
    ├── frontend/
    │   ├── __init__.py
    │   ├── app.py
    │   ├── notifications.py
    │   ├── output_records.py
    │   ├── styles.tcss
    │   ├── ui_state.py
    │   ├── screens/
    │   │   ├── __init__.py
    │   │   ├── branch_selector.py
    │   │   ├── confirm.py
    │   │   ├── editor.py
    │   │   ├── error_details.py
    │   │   ├── execution.py
    │   │   ├── help.py
    │   │   ├── memory_viewer.py
    │   │   ├── node_config.py
    │   │   ├── node_selector.py
    │   │   ├── output_viewer.py
    │   │   ├── settings.py
    │   │   ├── user_input.py
    │   │   └── workflow_library.py
    │   └── widgets/
    │       ├── __init__.py
    │       ├── command_input.py
    │       ├── command_navigation.py
    │       ├── dynamic_sections.py
    │       ├── form_generator.py
    │       ├── list_navigation.py
    │       ├── node_card.py
    │       ├── node_list.py
    │       └── status_bar.py
    └── tests/
        ├── __init__.py
        └── test_debug_nodes.py
```

## Omitted Local/Runtime Paths

- `.git/`
- `.venv/`
- `.claude/`
- `__pycache__/`
- `.pytest_cache/`
- `attackofthenodes_v05/logs/`
- `attackofthenodes_v05/settings/`
- `attackofthenodes_v05/workflows/`
- `attackofthenodes_v05/run_history/`
- `attackofthenodes_v05/run_outputs/`
- `attackofthenodes_v05/run_errors/`
- local scratch files such as `attackofthenodes_v05/read_test.txt`

## Notes

- The active frontend is Textual under `frontend/screens/` and
  `frontend/widgets/`.
- `frontend/modals/` no longer contains source files in the current tree; any
  remaining cache files there are historical artifacts.
- `requirements.lock` records the current venv freeze. `pyproject.toml` is the
  source dependency declaration.
