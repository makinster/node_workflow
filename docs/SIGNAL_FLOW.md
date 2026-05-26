# Backend Responsibilities and Signal Flow

This document captures the operational wiring for AttackOfTheNodes: who owns what, which components trade data, and which signals/events move through the system.

## Component Responsibilities

### `WorkflowPersistenceManager`

Responsibilities:

- Raw IndexedDB CRUD through Dexie.js.
- Owns six tables: `workflows`, `settings`, `apiKeys`, `runHistory`, `runOutputs`, `runErrors`.
- Does not interpret workflow schema or business meaning.

Data trades:

- Receives raw save objects from `WorkflowMap`, `MemoryBank`, `OutputManager`, `ErrorHandler`, and `ConfigurationManager`.
- Sends raw persisted objects back to those requesters.

Signals:

- None. This layer is read/write/delete only.

### `ConfigurationManager`

Responsibilities:

- Load and cache global settings on first access.
- Validate setting keys against `DEFAULT_SETTINGS`.
- Serve repeated reads from memory.

Data trades:

- Provides `nodeTimeoutMs`, `maxBranchDepth`, `autoSaveInterval`, and last-active-workflow settings to execution and save services.
- Persists updated settings through `WorkflowPersistenceManager`.

Signals:

- None.

### `WorkflowMap`

Responsibilities:

- Maintain workflow cache as `Map<workflowId, WorkflowCacheEntry>`.
- Track dirty state and modified node IDs.
- Provide executable node instances through `NodeFactory`.
- Provide UI node windows.
- Handle node add, delete, and config updates.
- Traverse graph for start node, adjacent nodes, and BFS windows.
- Preserve loose nodes while reporting them through validation.

Data trades:

- Receives load/save instructions from `SaveManager`.
- Uses raw workflow objects from `WorkflowPersistenceManager`.
- Uses node instances, config templates, and metadata from `NodeFactory`.
- Sends node windows, node data, and dirty state to `HandleUI`.
- Sends workflow structure to `Validator` and `SaveManager`.
- Sends node instances and adjacency details to `WorkflowSupervisor`.

Signals:

- None. Returns data synchronously or through normal async calls.

### `NodeFactory`

Responsibilities:

- Registry of available node types.
- Create executable node instances.
- Generate default node config templates.
- Provide node metadata and socket definitions for UI.
- Validate that node types are registered.

Data trades:

- Receives requests from `WorkflowMap` and `Validator`.
- Returns instances, config templates, metadata, schemas, and type existence checks.

Signals:

- None.

### Individual Node Classes

Responsibilities:

- Execute node-specific work.
- Accept inputs and runtime context from a supervisor.
- Report done, error, progress, waiting, or long-running state through context signals.
- Read/write shared memory as needed.
- Call external APIs through `ApiManager` when needed.

Data trades:

- Receive inputs and context from `WorkflowSupervisor`.
- Send execution outcomes back to the supervisor through `context.signal*()` methods.
- Read/write `MemoryBank` through context.
- Output-type nodes contribute to `OutputManager` through supervisor handling.

Signals sent through context:

- `signalDone({ data, nextNodeId, branches })`
- `signalError(error)`
- `signalProgress(data)`
- `signalWaitingForInput(promptContext)`
- `signalLongRunning(estimatedMs, checkpoint)`

### `MemoryBank`

Responsibilities:

- Store persistent variables shared across one run.
- Store transient port data keyed like `sourceNodeId_portName`.
- Enforce write-depth protection for persistent variables.
- Track modification timestamps.
- Broadcast memory changes to frontend.

Data trades:

- Receives transient writes from `WorkflowSupervisor`.
- Receives persistent reads/writes from nodes through context.
- Provides snapshots to `SaveManager`.
- Restores snapshots from `SaveManager`.

Signals:

- `EVENT_MEMORY_UPDATE` to frontend.

### `OutputManager`

Responsibilities:

- Collect output-node data during a run.
- Accumulate outputs in memory by `runId`.
- Persist outputs when a run finishes.
- Serve historical outputs for results views.

Data trades:

- Receives output writes from `WorkflowSupervisor`.
- Persists through `WorkflowPersistenceManager`.
- Serves output history to frontend through `HandleUI`.

Signals:

- `EVENT_RUN_OUTPUTS_UPDATED` after run output finalization.

### `WorkflowSupervisor`

Responsibilities:

- Walk one execution path through the workflow.
- Maintain branch-local execution state: current node, branch ID, depth, parent info, and flags.
- Fetch nodes, prepare inputs, execute nodes, handle output, and advance.
- Manage node heartbeat timeouts.
- Pause for user input and long-running nodes.
- Implement error recovery flow.
- Serialize and restore full supervisor state.
- Respond to pause, resume, stop, step, internal pause, and internal resume.

Data trades:

- Receives control signals from `WorkflowMasterState`.
- Fetches node instances and adjacency from `WorkflowMap`.
- Reads/writes data in `MemoryBank`.
- Writes output-node results to `OutputManager`.
- Logs errors through `ErrorHandler`.
- Sends context to nodes.

Signals sent to `WorkflowMasterState`:

- `REGISTER`: emitted on construction.
- `STATE_UPDATE`: emitted when state changes.
- `REQUEST_BRANCH`: emitted when a node returns branches.
- `TERMINATING`: emitted when the path ends or is stopped.
- `SAFE_FOR_SAVE`: emitted after a safe point during internal checkpoint.
- `NODE_ERROR`: emitted for node errors and recovery options.

### `WorkflowMasterState`

Responsibilities:

- Manage all active supervisors.
- Spawn branch supervisors and enforce `maxBranchDepth`.
- Maintain run state machine: `IDLE`, `RUNNING`, `PAUSED`, `WAITING`, `FINISHED`, `TERMINATED`, `ERROR`.
- Route user input and recovery decisions back to waiting supervisors.
- Coordinate internal checkpointing.
- Detect run completion.
- Broadcast execution state to frontend.

Data trades:

- Receives run/control commands from `HandleUI`.
- Receives supervisor events.
- Reads branch-depth settings from `ConfigurationManager`.
- Sends control signals to supervisors.
- Sends finalization requests to `SaveManager`/`OutputManager`.
- Broadcasts state through `BackendBridge`.

Frontend events:

- `EVENT_WORKFLOW_STATE_UPDATE`
- `EVENT_WORKFLOW_RUNNING`
- `EVENT_TRIGGER_USER_INPUT_MODAL`
- `EVENT_SUPERVISOR_LIST_UPDATE`
- `EVENT_RUN_COMPLETED`

Supervisor control commands:

- `PAUSE`
- `RESUME`
- `STOP`
- `STEP`
- `INTERNAL_PAUSE`
- `INTERNAL_RESUME`

### `Validator`

Responsibilities:

- Analyze workflow structure before execution or subworkflow save.
- Verify node types are registered.
- Validate node config against JSON schema.
- Validate connection targets and sources.
- Detect unreachable loose nodes.
- Return blocking errors and advisory warnings.
- Mark workflows as subworkflows when validation passes during subworkflow preparation.

Data trades:

- Receives validate requests from `HandleUI` and `SaveManager`.
- Reads workflow structure from `WorkflowMap`.
- Checks node registration through `NodeFactory`.
- Writes subworkflow flags through `WorkflowMap` when preparing subworkflows.

Signals:

- None. Returns validation results.

### `ErrorHandler`

Responsibilities:

- Centralized structured error logging.
- Categorize errors as `NETWORK`, `VALIDATION`, `NODE_LOGIC`, or `UNKNOWN`.
- Attach node, run, supervisor, stack trace, and metadata.
- Persist errors.
- Cache errors by run.
- Broadcast error count changes.

Data trades:

- Receives errors from supervisors, master state, UI handlers, and any failing service.
- Saves errors through `WorkflowPersistenceManager`.
- Sends error events through `BackendBridge`.

Signals:

- `EVENT_ERROR_LOGGED`
- `EVENT_ERRORS_CLEARED`

### `ApiManager`

Responsibilities:

- Store encrypted API credentials.
- Derive encryption keys from master password.
- Cache decrypted keys for the session.
- Dispatch external API calls.
- Handle authentication flows.

Data trades:

- Receives node API requests through context.
- Receives key management requests from `HandleUI`.
- Persists encrypted keys through `WorkflowPersistenceManager`.
- Returns API responses to nodes.

Signals:

- None.

### `SaveManager`

Responsibilities:

- Assemble full workflow save payloads.
- Load workflows and distribute restored state.
- Convert runtime `Map` structures to persisted plain objects and back.
- Save and restore execution snapshots.
- Manage manual save and auto-save keys.
- Clear dirty flags only after successful persistence.
- Validate and prepare subworkflows.

Data trades:

- Receives save/load requests from `HandleUI`.
- Receives checkpoint requests from `WorkflowMasterState`.
- Reads workflow structure from `WorkflowMap`.
- Reads memory snapshots from `MemoryBank`.
- Reads active supervisor state from `WorkflowMasterState`.
- Reads collected outputs from `OutputManager`.
- Persists through `WorkflowPersistenceManager`.
- Updates last active workflow in `ConfigurationManager`.

Signals:

- None. Returns save/load results.

### `HandleUI`

Responsibilities:

- Receive frontend `REQ_*` and `CMD_*` messages.
- Route requests to backend services.
- Format responses for frontend consumption.
- Coordinate multi-service operations.
- Centralize UI request error handling.

Key delegations:

- `REQ_START_WORKFLOW` -> `WorkflowMasterState.handleStartWorkflow`
- `REQ_SAVE_WORKFLOW` -> `SaveManager.saveCurrentWorkflow`
- `REQ_LOAD_WORKFLOW` -> `SaveManager.loadWorkflowIntoApplication`
- `REQ_VALIDATE_WORKFLOW` -> `Validator.validateWorkflow`
- `REQ_ADD_NODE` -> `WorkflowMap.addNodeToWorkflow`
- `REQ_NODE_WINDOW` -> `WorkflowMap.getNodeWindowForUI`
- `REQ_PAUSE_WORKFLOW` -> `WorkflowMasterState.handleUICommand(CMD_PAUSE)`
- `REQ_SUBMIT_USER_INPUT` -> `WorkflowMasterState.handleUserInputSubmission`

Signals:

- Writes request responses through `BackendBridge`.

### `BackendBridge`

Responsibilities:

- Serialize and deserialize frontend/backend messages.
- Send frontend requests to `HandleUI`.
- Listen for backend event broadcasts.
- Route events to `UIController`.
- Provide a Promise-based frontend API.

Event routing examples:

- `EVENT_WORKFLOW_STATE_UPDATE` -> `uiController.setWorkflowRunState(state)`
- `EVENT_SUPERVISOR_LIST_UPDATE` -> `uiController.setActiveSupervisors(list)`
- `EVENT_MEMORY_UPDATE` -> `uiController.setMemoryState(memory)`
- `EVENT_ERROR_LOGGED` -> `uiController.incrementErrorCount()`
- `EVENT_TRIGGER_USER_INPUT_MODAL` -> `uiController.openModal("UserInput")`

## Scenario Flows

### User Starts A Workflow

```text
Frontend click Run
  -> BackendBridge sends CMD_START
  -> HandleUI.handleStartWorkflow()
  -> WorkflowMasterState starts run
     -> WorkflowMap.findStartNode()
     -> MemoryBank clears run memory
     -> SupervisorFactory creates root supervisor
     -> Supervisor emits REGISTER
     -> MasterState tracks supervisor and broadcasts supervisor list
     -> supervisor.start()
     -> MasterState broadcasts EVENT_WORKFLOW_STATE_UPDATE(RUNNING)
  -> BackendBridge updates UIController
  -> UI mode switches to execution
```

### Node Completes On A Simple Path

```text
WorkflowSupervisor loop
  -> WorkflowMap.getNodeInstance(nodeId)
  -> Supervisor prepares inputs from MemoryBank transient store
  -> node.execute(inputs, context)
  -> node calls context.signalDone({ data, nextNodeId })
  -> Supervisor writes transient output
  -> Output node data is stored in OutputManager
  -> Branch payloads become REQUEST_BRANCH events
  -> Supervisor advances currentNodeId
```

### Node Requests User Input

```text
node calls context.signalWaitingForInput(promptContext)
  -> Supervisor stores resolver and enters WAITING_FOR_USER_INPUT
  -> Supervisor emits STATE_UPDATE
  -> MasterState stores waiting input and broadcasts EVENT_TRIGGER_USER_INPUT_MODAL
  -> UI opens UserInputModal
  -> User submits input through BackendBridge
  -> HandleUI routes to MasterState
  -> MasterState resolves the waiting supervisor promise
  -> node.execute resumes
```

### Node Signals Error

```text
node calls context.signalError(error)
  -> Supervisor handles node error
  -> ErrorHandler logs and broadcasts EVENT_ERROR_LOGGED
  -> Supervisor enters WAITING_FOR_RECOVERY for recoverable errors
  -> Supervisor emits NODE_ERROR with options
  -> MasterState stores recovery request and opens error UI
  -> User picks recovery action
  -> HandleUI routes action to MasterState
  -> MasterState resolves supervisor recovery promise
  -> Supervisor executes RETRY, SKIP, RECONFIGURE, TERMINATE_BRANCH, or TERMINATE_WORKFLOW
```

### Node Branches

```text
node calls context.signalDone({ data, branches })
  -> Supervisor writes normal output to MemoryBank
  -> Supervisor emits REQUEST_BRANCH for each branch
  -> MasterState checks maxBranchDepth
  -> SupervisorFactory creates child supervisors at depth + 1
  -> Child supervisors emit REGISTER
  -> MasterState broadcasts EVENT_SUPERVISOR_LIST_UPDATE
  -> UI branch selector updates
  -> Supervisors run independently
  -> Each emits TERMINATING when done
  -> Last termination triggers run completion
```

### Internal Checkpoint During Execution

```text
autoSaveInterval fires
  -> MasterState sends INTERNAL_PAUSE to active supervisors
  -> Each supervisor finishes current node
  -> Each emits SAFE_FOR_SAVE
  -> MasterState waits until all are safe
  -> SaveManager saves workflow with execution state
     -> WorkflowMap contributes structure
     -> MasterState contributes supervisor snapshots
     -> MemoryBank contributes memory snapshot
     -> OutputManager contributes current outputs
     -> Persistence writes workflow_{id}_auto_save
  -> MasterState sends INTERNAL_RESUME
  -> Supervisors continue
```

### Run Completion

```text
Supervisor reaches no next node
  -> Supervisor emits TERMINATING
  -> MasterState removes supervisor
  -> If activeSupervisors is empty:
     -> SaveManager/OutputManager finalize run outputs
     -> Persistence saves run outputs
     -> MasterState sets FINISHED
     -> MasterState stops checkpoint timer
     -> MasterState broadcasts EVENT_WORKFLOW_STATE_UPDATE(FINISHED)
  -> UI returns to editor mode and results are available
```

## Dependency Graph

```text
Frontend
  -> BackendBridge
  -> HandleUI
     -> WorkflowMasterState
        -> WorkflowSupervisor
           -> WorkflowMap
           -> MemoryBank
           -> ErrorHandler
           -> OutputManager
        -> SupervisorFactory
           -> ConfigurationManager
        -> ErrorHandler
        -> BackendBridge
     -> SaveManager
        -> WorkflowMap
        -> WorkflowPersistenceManager
        -> WorkflowMasterState
        -> MemoryBank
        -> OutputManager
        -> Validator
        -> ConfigurationManager
     -> WorkflowMap
        -> WorkflowPersistenceManager
        -> NodeFactory
        -> ErrorHandler
     -> Validator
        -> WorkflowMap
        -> NodeFactory
     -> ApiManager
        -> WorkflowPersistenceManager
     -> ConfigurationManager
        -> WorkflowPersistenceManager

NodeFactory
  -> node classes in /nodes/

ErrorHandler
  -> WorkflowPersistenceManager
  -> BackendBridge

MemoryBank
  -> BackendBridge
  -> SaveManager

OutputManager
  -> WorkflowPersistenceManager
  -> SaveManager

BackendBridge
  -> frontend through chrome.runtime.sendMessage
```
