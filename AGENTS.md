# AttackOfTheNodes

A Python workflow engine and Textual terminal UI for building, running,
pausing, branching and inspecting node-based workflows. Nodes are the
machines; the backend runs the factory floor and the UI is its control room.

Read [the docs router](AttackOfTheNodes/docs/README.md), then the
[newcomer guide](AttackOfTheNodes/docs/NEWCOMER_GUIDE.md),
[Vision](AttackOfTheNodes/docs/VISION.md), and
[the checked current state](AttackOfTheNodes/docs/CURRENT_STATE.md).
[Node Contract Plan](AttackOfTheNodes/docs/NODE_CONTRACT_PLAN.md) owns the
immediate work order. Use `aotn nodes` / `aotn describe` for live node facts.
Read [the boundary contract](AttackOfTheNodes/docs/BACKEND_FRONTEND_BOUNDARY.md)
before backend changes motivated by the UI.

Work in your own checkout or worktree; never edit another worker's.
Preserve unrelated edits and owner workflows. The owner merges, or explicitly
asks a reviewer to merge. Read [Contributing](AttackOfTheNodes/docs/CONTRIBUTING.md)
for process and environment. Historical prompts are not live authorization.

## Rules that bite

- Nodes are graph-ignorant; use prepared inputs and NodeContext callbacks.
- WorkflowMap owns live graph shape, mutations and dirty state.
- EventBus is the only inter-component signal channel; service calls remain explicit.
- Tombstones intentionally preserve deleted nodes for repair/restore; do not clean them away.
- MasterState/App are session singletons; register subscriptions once per session.
- An ordinary output follows its first connection; extra wires do not spawn branches.
- A branch-spawning node ends its own path after requesting children.
- Publish outputs before marking the saved node ID completed; waiters may wake immediately.
- Vault and transient data are shared within a run; transient keys are not branch-isolated.
- See [Architecture](AttackOfTheNodes/docs/ARCHITECTURE.md) for guarantees and limits.
