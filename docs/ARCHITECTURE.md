# AttackOfTheNodes Architecture

AttackOfTheNodes is a node-based workflow engine with a live frontend control surface. The guiding metaphor is a factory floor with a control room: backend services execute and coordinate node pipelines, while the frontend renders, edits, and observes them.

## Big Picture

A workflow is a recipe made of connected nodes. When a run starts, a `WorkflowSupervisor` walks from the start node through the graph. If a node forks execution, `WorkflowMasterState` spawns one supervisor per branch. Supervisors share a per-run `MemoryBank`, collect durable outputs through `OutputManager`, and report lifecycle events back to `WorkflowMasterState`.

The execution pipeline is:

1. Load workflow structure.
2. Validate reachable nodes and connections.
3. Start root supervisor at the start node.
4. Execute nodes sequentially along a path.
5. Write transient data to `MemoryBank`.
6. Spawn branch supervisors when requested.
7. Pause for human input or recovery decisions when needed.
8. Finalize outputs and run state when all supervisors terminate.

## Backend Components

### `WorkflowPersistenceManager`

The persistence manager is intentionally dumb. It wraps IndexedDB through Dexie.js and exposes six conceptual tables:

- `workflows`: serialized workflow blueprints.
- `settings`: global key/value configuration.
- `apiKeys`: encrypted API credentials.
- `runHistory`: summaries of past runs.
- `runOutputs`: collected output data from completed runs.
- `runErrors`: structured error logs per run.

Workflow nodes are stored as plain JSON objects. Conversion to live runtime `Map` objects happens above this layer.

Workflow saves use two keys:

- `workflow_{id}`: manual save.
- `workflow_{id}_auto_save`: internal checkpoint written during a run.

On startup, session recovery should check for an auto-save first, restore from it, and delete it afterward.

### `ConfigurationManager`

The settings board. It loads settings once, caches them in memory, and serves future reads from cache. `DEFAULT_SETTINGS` acts as both defaults and schema; only known setting keys can be set.

Important settings:

- `maxBranchDepth`: hard ceiling for nested branch spawning.
- `nodeTimeoutMs`: per-node execution timeout.
- `autoSaveInterval`: internal checkpoint cadence.

### `WorkflowMap`

The live blueprint manager. It caches workflows as `Map<workflowId, WorkflowCacheEntry>`.

Each cache entry contains:

- `nodes: Map<nodeId, NodeDataObject>`
- `isDirty: boolean`
- `modifiedNodeIds: Set`
- `isSubworkflow: boolean`

Each node data object contains identity, type, alias, config, input/output connections, position, bookmark state, and subworkflow marker.

Primary responsibilities:

- Traversal: start-node discovery, adjacent-node lookup, and BFS windowing for the UI.
- Node CRUD: add nodes from `NodeFactory` templates, delete nodes, and clean neighbor connections.
- Dirty tracking: mutations set dirty state, saves clear it.
- Loose node handling: disconnected nodes are retained and persisted, but ignored during execution unless reachable.

### `NodeFactory`

The parts catalog. It imports node classes from `/nodes/index.js` and builds a registry of node type to class, metadata, config schema, and form schema.

Primary operations:

- `createNodeInstance(nodeId, nodeType, config)`
- `createNodeConfigTemplate(nodeType)`
- `getNodeTypesMetadata()`
- `getNodeConfigFormSchema(nodeType)`

If a node does not define an explicit form schema, the form schema can be inferred from its JSON schema.

### Node Classes

Each node lives under `/nodes/` and extends `NodeBase`. A node is intentionally graph-ignorant: it receives inputs, reads its config, and signals through context.

Each node defines:

- `static nodeMetadata`
- `static configSchema`
- `async execute(inputs, context)`

The execution context includes signal methods, shared services, runtime identity, and helpers:

```javascript
context = {
  signalDone({ data, nextNodeId, branches }),
  signalError(error),
  signalProgress(data),
  signalWaitingForInput(promptContext),
  signalLongRunning(estimatedMs, checkpoint),
  memoryBank,
  apiManager,
  callApi(apiId, params),
  createSupervisor(ctx),
  getNodeConfig(),
  currentNodeId,
  branchId,
  runId
};
```

Branching is requested through `signalDone`:

```javascript
context.signalDone({
  data: { decision: "yes" },
  branches: [
    { outputSocketName: "yes_path", startNodeId: "node_a", initialData: {} },
    { outputSocketName: "no_path", startNodeId: "node_b", initialData: {} }
  ]
});
```

Current node types:

- `DataInputNode`
- `DataOutputNode`
- `LogicBranchNode`
- `UserInputNode`
- `TransformNode`
- `MergeNode` deferred until cross-supervisor coordination is implemented.

### `MemoryBank`

The shared whiteboard for one run. It has two stores:

- Persistent store: named variables shared by all supervisors for the whole run.
- Transient store: point-to-point data passing keyed like `sourceNodeId_portName`.

Persistent memory changes broadcast `EVENT_MEMORY_UPDATE` so the frontend memory viewer can update live. Both stores are cleared on run start and are blank between runs.

### `OutputManager`

The collection bin for durable workflow outputs. It accumulates `OutputItem` objects in memory by `runId`, then `finalizeRunOutputs` batch-saves them through persistence and clears the in-memory store.

`MemoryBank` is ephemeral working memory. `OutputManager` is permanent run output history.

### `WorkflowSupervisor`

The line worker. It executes one path through the graph and owns branch-local state.

Created with:

- `runId`
- `branchId`
- `depth`
- `startNodeId`
- `parentInfo`
- `initialContextData`
- Injected services: `WorkflowMap`, `MemoryBank`, `MasterState`, `OutputManager`, and `ErrorHandler`.

Run loop:

1. Check terminate and pause flags.
2. Fetch executable node instance from `WorkflowMap`.
3. Prepare inputs from transient memory or branch initial data.
4. Start heartbeat timeout.
5. Await `node.execute(inputs, context)` and its signal result.
6. Clear heartbeat.
7. Write outputs to transient memory and output manager when relevant.
8. Request branches from `MasterState` when signaled.
9. Advance to explicit `nextNodeId` or default output connection.
10. Terminate when no next node exists.

For user input, the supervisor transitions to `WAITING_FOR_USER_INPUT`, stores a resolver, and waits for `MasterState` to route the frontend answer back.

For recoverable errors, the supervisor logs, packages recovery options, waits for a human decision, and applies `RETRY`, `SKIP`, `RECONFIGURE`, `TERMINATE_BRANCH`, or `TERMINATE_WORKFLOW`.

Supervisors must support `getSerializableState` and `restoreFromState` for session recovery.

### `WorkflowMasterState`

The floor manager. It does not execute nodes; it coordinates supervisors.

Starting a run:

1. Generate `runId`.
2. Clear `MemoryBank` and `OutputManager`.
3. Find the workflow start node.
4. Create root supervisor through `SupervisorFactory`.
5. Register supervisor metadata in `activeSupervisors`.
6. Start the supervisor.
7. Start checkpoint timer.
8. Broadcast `EVENT_WORKFLOW_STATE_UPDATE`.

Supervisor event routing handles:

- `REGISTER`
- `STATE_UPDATE`
- `REQUEST_BRANCH`
- `TERMINATING`
- `SAFE_FOR_SAVE`
- `NODE_ERROR`

Run completion occurs when `activeSupervisors` is empty. Master state then finalizes outputs, updates state to `FINISHED`, stops the save timer, and broadcasts final state.

Checkpointing pauses supervisors at safe points, waits for `SAFE_FOR_SAVE` from all active supervisors, serializes execution state, writes `_auto_save`, and resumes supervisors.

### `SaveManager`

The archivist. It assembles complete save objects.

Save flow:

1. Get structure from `WorkflowMap.getWorkflowDataForSave`.
2. Include supervisor snapshots and memory snapshots when saving execution state.
3. Stamp version and timestamp.
4. Write to `workflow_{id}` or `workflow_{id}_auto_save`.
5. Clear dirty state in `WorkflowMap`.

Load flow:

1. Fetch raw persisted data.
2. Load workflow cache and convert nodes object back to `Map`.
3. Restore memory and supervisors when execution state exists.
4. Update last active workflow setting.

Subworkflow preparation validates, marks workflow and nodes as subworkflow-safe, and saves.

### `Validator`

The inspector. It performs a DFS from the start node and checks:

- Node type exists in `NodeFactory`.
- Node config satisfies JSON schema.
- Connection sources and targets exist.

After traversal, any unvisited node is unreachable and reported as a warning. The return shape is:

```javascript
{
  success: true,
  errors: [],
  warnings: []
}
```

Each error or warning should include `nodeId` so the UI can highlight the affected node.

### `ErrorHandler`

Central structured error logging. Errors include:

- Unique ID.
- Timestamp.
- Category such as `NETWORK`, `VALIDATION`, `NODE_LOGIC`, or `UNKNOWN`.
- Stack trace.
- Context metadata including node, run, and supervisor.

Errors are persisted per run, cached in memory, and broadcast with `EVENT_ERROR_LOGGED`.

### `ApiManager`

Handles encrypted external API credentials and runtime API dispatch. Encryption uses Web Crypto with PBKDF2-derived keys and AES-GCM. Decrypted credentials are cached only for the session.

`callApi(apiId, params)` is the node-facing dispatch point. `getApiKeysStatus()` exposes configured/not-configured status without leaking values.

### `HandleUI`

The backend facade. It maps frontend `REQ_*` and `CMD_*` messages to backend operations.

Examples:

- `handleSaveWorkflow` delegates to `SaveManager`.
- `handleGetInitialState` assembles workflow, config, API key status, and optional last session.
- `handleSelectExecutionBranch` locates the supervisor current node and asks the frontend to focus it.
- `handleRecoveryAction` routes a recovery choice back to `MasterState`.

`_delegateCall` wraps service calls in uniform error handling through `ErrorHandler`.

## Frontend Components

### Layout

The UI has a persistent top toolbar, a left work area, a right controls panel, and a modal layer. It has two modes:

- `editor`: edit workflow structure and node config.
- `execution`: watch active supervisors and interact with live run state.

Mode is derived from workflow run state.

### `TopToolbar`

Always visible. Contains workflow settings/name, run/stop, results, options, dirty indicator, and error count badge.

### `EditorPanel`

The blueprint view. It renders a scrollable windowed slice of nearby nodes via `requestNodeWindow(centerNodeId, windowSize)`. The UI anchor is `editorCenterNodeId`.

### `ExecutionPanel`

The live view. It uses the same windowing approach but highlights the selected supervisor's active node and follows it as execution advances.

### `ControlsPanel`

Editor mode:

- Validate button and validation status.
- Jump To controls for start, branches, bookmarks, and outputs.

Execution mode:

- Pause/resume.
- Execution status.
- Pending inputs.
- Supervisor selector.
- Selected supervisor info.
- Errors, memory, and outputs shortcuts.

### `NodeCard`

Displays node alias/type, node type tag, status, edit action, and delete action. The active execution node is highlighted in execution mode.

### Modal System

`ModalContainer` reads `modalStack`; opening pushes and closing pops. Supported modals:

- `WorkflowSettingsModal`
- `NodeSelectorModal`
- `NodeConfigModal`
- `DeleteNodeModal`
- `UserInputModal`
- `BranchViewerModal`
- `MemoryViewerModal`
- `OutputViewerModal`
- `ResultsModal`
- `ErrorDetailsModal`
- `ApiKeyManagerModal`
- `OptionsModal`

### `BackendBridge`

The single frontend/backend communication channel. It sends typed message objects and resolves request promises. It also routes backend `EVENT_*` messages into UI store actions.

### `UIController`

The Zustand source of truth for frontend state:

- `mode`
- `workflowRunState`
- `currentWorkflowId`
- `currentWorkflowName`
- `isDirty`
- `modalStack`
- `activeSupervisors`
- `selectedSupervisorId`
- `pendingInputCount`
- `errorCount`
- `validationStatus`
- `editorCenterNodeId`
- `jumpToFilter`
- `jumpToList`

## User Flow

1. App initializes `BackendBridge`.
2. Frontend requests initial state.
3. Backend loads last workflow/config.
4. Editor fetches node window around the start node.
5. User edits nodes, config, and saves.
6. User validates.
7. User starts execution.
8. Master state creates root supervisor.
9. Execution panel follows selected supervisor.
10. User responds to input prompts or recovery decisions when needed.
11. Branches spawn additional supervisors.
12. Run finishes when all supervisors terminate.
13. Outputs are finalized and results become available.

## Implementation Invariants

- Frontend code should communicate with backend only through `BackendBridge`.
- Runtime node execution should not require nodes to know graph topology.
- Persistence should remain schema-light and avoid interpreting workflow meaning.
- `WorkflowMap` owns live workflow shape and dirty state.
- `SaveManager` is the only component that should assemble complete save payloads.
- Session recovery should prefer `_auto_save`, then delete it after restoration.
- Loose nodes round-trip through saves.
- `MergeNode` should remain deferred until branch recombination semantics are explicit.
