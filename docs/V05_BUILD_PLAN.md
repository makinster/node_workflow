# AttackOfTheNodes v0.5 Python Proof Of Concept Build Plan

This document is the implementation reference for the Python proof of concept. The goal is a minimal but architecturally faithful workflow engine that can build, save, load, and execute connected offline nodes.

## Philosophy

Preserve structure, simplify implementation. Components should keep their long-term responsibilities even when their v0.5 internals are small. Do not collapse `WorkflowSupervisor` into `WorkflowMasterState`, or persistence into workflow logic, just because the first workflow is linear.

## Technology

- Python 3.10 or later.
- tkinter for the UI.
- asyncio for node execution and supervisor loops.
- JSON files in `workflows/` for persistence.
- No third-party dependencies.

## Required v0.5 Shape

Backend:

- Node base and individual node classes.
- Node factory.
- Workflow map.
- Memory bank.
- Supervisor.
- Master state.
- Persistence.
- Simple validator.
- Simple structured error list.

Frontend:

- App window.
- Editor panel.
- Execution panel.
- Controls panel.
- Node card helper.
- Small modal set.
- Event bus connecting backend and frontend.

Simplified or deferred:

- `SaveManager` and `HandleUI` are folded into direct calls for v0.5.
- `OutputManager` is an in-memory list on `MasterState`.
- `Validator` is a simple function.
- `ErrorHandler` is a simple logger/list.
- No API manager, encryption, Chrome extension, service worker, auto-save, checkpointing, crash recovery, subworkflows, or multi-workflow cache.

## Target File Structure

```text
attackofthenodes_v05/
  main.py
  backend/
    __init__.py
    events.py
    event_bus.py
    node_base.py
    nodes/
      __init__.py
      start_node.py
      text_output_node.py
      branch_node.py
      end_node.py
    node_factory.py
    workflow_map.py
    memory_bank.py
    supervisor.py
    master_state.py
    persistence.py
    validator.py
  frontend/
    __init__.py
    app.py
    editor_panel.py
    execution_panel.py
    controls_panel.py
    node_card.py
    modals.py
    ui_state.py
  workflows/
```

## Phase 1 Scope

Phase 1 establishes the foundation:

- Persistence functions for workflow JSON.
- Event bus.
- Node base and `NodeContext`.
- Node factory.
- Registered node files.
- Concrete `StartNode`.
- Placeholder phase-2 nodes with metadata.
- A `main.py` smoke test that saves/loads a workflow, publishes an event, verifies factory registration, and validates a start node config.

## Acceptance Notes

At the end of phase 1, running `attackofthenodes_v05/main.py` should:

- Create `attackofthenodes_v05/workflows/` if absent.
- Save and load a test workflow.
- List available workflows.
- Publish and receive a test event.
- Register all four node types.
- Instantiate and validate a `StartNode`.
