# AttackOfTheNodes File Tree

Generated from the current workspace snapshot. Python cache folders and compiled
`.pyc` files are omitted; runtime data folders are summarized where they contain
many generated files.

```text
node_workflow/
├── .agents/
├── .codex/
├── .gitignore
├── AGENTS.md
├── requirements.txt
├── docs/
│   ├── ARCHITECTURE.md
│   ├── FILE_TREE.md
│   ├── PROJECT_KNOWLEDGE.md
│   ├── SIGNAL_FLOW.md
│   ├── TUI_DESIGN.md
│   └── V05_BUILD_PLAN.md
└── attackofthenodes_v05/
    ├── __init__.py
    ├── demo_execution.py
    ├── main.py
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
    │   ├── master_state.py
    │   ├── memory_bank.py
    │   ├── node_base.py
    │   ├── node_factory.py
    │   ├── output_manager.py
    │   ├── persistence.py
    │   ├── run_history.py
    │   ├── save_manager.py
    │   ├── supervisor.py
    │   ├── validator.py
    │   ├── workflow_map.py
    │   └── nodes/
    │       ├── __init__.py
    │       ├── branch_node.py
    │       ├── chat_completion_node.py
    │       ├── concat_node.py
    │       ├── conditional_node.py
    │       ├── embedding_node.py
    │       ├── end_node.py
    │       ├── file_reader_node.py
    │       ├── get_variable_node.py
    │       ├── image_generation_node.py
    │       ├── set_variable_node.py
    │       ├── start_node.py
    │       ├── text_output_node.py
    │       └── user_text_input_node.py
    ├── frontend/
    │   ├── __init__.py
    │   ├── app.py
    │   ├── styles.tcss
    │   ├── ui_state.py
    │   ├── screens/
    │   │   ├── __init__.py
    │   │   ├── branch_selector.py
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
    │       ├── form_generator.py
    │       ├── node_card.py
    │       ├── node_list.py
    │       └── status_bar.py
    ├── logs/
    │   └── attackofthenodes.log
    ├── run_errors/
    │   └── run_*.json (7 files)
    ├── run_history/
    │   └── run_*.json (53 files)
    ├── run_outputs/
    │   └── run_*.json (34 files)
    ├── settings/
    │   └── settings.json
    └── workflows/
        ├── .gitkeep
        ├── test_workflow_001.json
        └── wf_c688845f3881.json
```

## Notes

- `backend/` contains the workflow engine, execution orchestration, persistence,
  validation, events, memory, outputs, and executable node implementations.
- `frontend/` now contains the Textual TUI shell, screens, widgets, schema form
  generator, and terminal styles.
- `run_history/`, `run_outputs/`, `run_errors/`, `logs/`, `settings/`, and
  `workflows/` are runtime or persisted project data.
- `__pycache__/` folders exist throughout the Python package but are intentionally
  excluded from this tree.
