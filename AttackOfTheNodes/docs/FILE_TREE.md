# AttackOfTheNodes File Tree

Current tracked app layout. Runtime output folders, caches, logs, and local
untracked workspace folders are omitted.

```text
AttackOfTheNodes/
  main.py
  pyproject.toml
  pytest.ini
  requirements.lock
  run_windows.cmd

  backend/
    configuration_manager.py
    error_handler.py
    event_bus.py
    events.py
    field_types.py
    master_state.py
    memory_bank.py
    node_base.py
    node_category.py
    node_factory.py
    output_entry.py
    output_manager.py
    persistence.py
    run_history.py
    save_manager.py
    supervisor.py
    validator.py
    workflow_map.py
    utils/
      try_catch.py
    nodes/
      branch_end_node.py
      branch_node.py
      chat_completion_node.py
      concat_node.py
      conditional_node.py
      embedding_node.py
      end_node.py
      file_reader_node.py
      get_variable_node.py
      image_generation_node.py
      merge_node.py
      set_variable_node.py
      start_node.py
      text_output_node.py
      user_text_input_node.py
      wait_until_node.py
      debug/
        counter_node.py
        deep_branch_node.py
        echo_node.py
        error_node.py
        logger_node.py
        memory_snapshot_node.py
        no_op_node.py
        probe_node.py
        random_branch_node.py
        repeat_node.py
        sleep_node.py
        tombstone_node.py
        variable_reader_node.py
        variable_setter_node.py

  frontend/
    app.py
    editor_workflow_adapter.py
    file_io.py
    node_io_display.py
    notifications.py
    output_records.py
    styles.tcss
    ui_state.py
    screens/
      branch_selector.py
      confirm.py
      editor.py
      error_details.py
      execution.py
      help.py
      memory_viewer.py
      merge_beacon_selector.py
      node_config.py
      node_selector.py
      output_viewer.py
      settings.py
      user_input.py
      workflow_library.py
    widgets/
      command_input.py
      command_navigation.py
      command_screen_mixin.py
      cursor_state.py
      dynamic_sections.py
      form_generator.py
      list_navigation.py
      node_card.py
      node_list.py
      status_bar.py

  docs/
    README.md
    TASK_INDEX.md
    AGENT_HANDOFF.md
    AGENT_START_GUIDE.md
    ARCHITECTURE.md
    BACKEND_FRONTEND_BOUNDARY.md
    DOCS_MIGRATION_NOTES.md
    FILE_TREE.md
    MASTER_BUILD_PLAN.md
    PROJECT_BACKLOG.md
    PROJECT_KNOWLEDGE.md
    SESSION_LOG.md
    SIGNAL_FLOW.md
    TUI_DESIGN.md
    UI_QUICK_REFERENCE.md
    archive/
      BUILD_PLAN_HISTORY.md
      SESSION_LOG_HISTORY.md
      V05_BUILD_PLAN.md
      plans/
        FRONTEND_AUDIT_BUILD_PLAN.md
        USER_FRIENDLY_POLISH_BUILD_PLAN.md

  tests/
    test_debug_nodes.py
    test_node_helper.py

  workflows/
    .gitkeep
```

Workspace-level developer tooling:

```text
aotn_node_helper/
  create_node.py
  check_node.py
  generator.py
  specs/
    example_pass_through_node.yaml
```

## Omitted Paths

- `run_outputs/`, `run_errors/`, and `run_history/`: runtime data.
- `logs/`: local logs.
- `__pycache__/`, `.pytest_cache/`: generated caches.
- Root untracked `docs/`, `.claude/`, and legacy local copies: not part of the
  tracked active app docs.
