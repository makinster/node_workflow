# AttackOfTheNodes Project Context

This workspace contains AttackOfTheNodes, a workflow engine and UI for building, running, pausing, branching, and inspecting node-based pipelines.

## Mental Model

Think of the project as a factory floor with a control room:

- The backend is the factory floor. Nodes are machines arranged into workflows, and supervisors walk execution paths through those nodes.
- The frontend is the control room. It displays workflow structure, execution state, memory, outputs, errors, and settings.
- A workflow is a recipe: nodes plus connections. Execution starts at a start node, follows connections, and can fork into branch supervisors.
- All supervisors in a run share one `MemoryBank` and report to `WorkflowMasterState`.

## Core Backend Responsibilities

- `WorkflowPersistenceManager`: dumb IndexedDB/Dexie wrapper for workflows, settings, API keys, run history, run outputs, and run errors. Workflow saves use `workflow_{id}` and internal checkpoints use `workflow_{id}_auto_save`.
- `ConfigurationManager`: settings cache and schema gatekeeper using `DEFAULT_SETTINGS`.
- `WorkflowMap`: live workflow cache as `Map<workflowId, WorkflowCacheEntry>`. Owns node CRUD, traversal, dirty tracking, UI windowing, and loose node persistence.
- `NodeFactory`: registry for executable node classes, config templates, metadata, and form schemas.
- Node classes: isolated machines extending `NodeBase`; they only know their config, inputs, and execution `context`.
- `MemoryBank`: per-run shared whiteboard with persistent variables and transient port data keyed like `sourceNodeId_portName`.
- `OutputManager`: collects output-node results during a run and persists them after completion.
- `WorkflowSupervisor`: stateful worker that executes one path through a workflow graph.
- `WorkflowMasterState`: conductor that starts runs, tracks supervisors, handles branching, pause/resume, checkpointing, user input, and run completion.
- `SaveManager`: assembles complete save objects from `WorkflowMap`, `MasterState`, `MemoryBank`, and persistence.
- `Validator`: DFS preflight from start node; errors on invalid node types/config/connections and warns on unreachable loose nodes.
- `ErrorHandler`: centralized structured error logging and broadcasting.
- `ApiManager`: encrypted API credential storage and runtime API dispatch.
- `HandleUI`: backend facade mapping frontend `REQ_*` and `CMD_*` messages to services.

## Frontend Responsibilities

- `BackendBridge`: single frontend/backend intercom for typed requests, commands, and backend events.
- `UIController`: Zustand source of truth for mode, workflow/run state, modal stack, supervisors, validation, errors, selected branch, pending input, and editor anchor.
- `TopToolbar`: workflow selector/settings, run/stop, results, options, dirty indicator, and error badge.
- `EditorPanel`: windowed node list for editing large workflows.
- `ExecutionPanel`: windowed node list with live execution highlighting for the selected supervisor.
- `ControlsPanel`: editor validation/navigation controls or execution pause/resume, branch, input, error, memory, and output controls.
- `NodeCard`: node alias/type/status plus edit/delete actions.
- Modal stack: workflow settings, node selector/config/delete, user input, branch viewer, memory viewer, output viewer, results, error details, API keys, and options.

## Important Behavioral Rules

- Workflow `nodes` are persisted as plain JSON objects and converted to live `Map`s at higher layers.
- Loose nodes are valid to save and load, but execution only visits nodes reachable from the start node. Validator reports loose nodes as warnings.
- Branching happens when a node calls `context.signalDone({ branches: [...] })`; `WorkflowMasterState` spawns one supervisor per branch and enforces `maxBranchDepth`.
- User input nodes suspend a supervisor until the frontend sends the answer back through `MasterState`.
- Internal checkpointing pauses supervisors at safe points, writes `_auto_save`, then resumes. Startup should prefer and then delete auto-save for session recovery.
- `MemoryBank` is ephemeral per run; `OutputManager` is the durable record of produced outputs.
- `WorkflowMap.isDirty` drives save decisions, and `SaveManager` clears dirty state only after successful persistence.

## Current Node Types

- `DataInputNode`: introduces data into the workflow.
- `DataOutputNode`: collects final output for `OutputManager`.
- `LogicBranchNode`: evaluates a condition and forks execution.
- `UserInputNode`: pauses execution for human input.
- `TransformNode`: mutates or processes passing data.
- `MergeNode`: deferred; recombining parallel paths requires cross-supervisor coordination.

For deeper architecture detail, see `docs/ARCHITECTURE.md`.
For component responsibilities, data trades, signals, and execution scenarios, see `docs/SIGNAL_FLOW.md`.
For the Python v0.5 proof-of-concept build plan and phase breakdown, see `docs/V05_BUILD_PLAN.md`.
