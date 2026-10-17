# AttackOfTheNodes

A Python workflow engine and Textual terminal UI for building, running,
pausing, branching and inspecting node-based workflows. Nodes are the
machines; the backend runs the factory floor and the UI is its control room.

Read [the docs router](AttackOfTheNodes/docs/README.md), then the
[newcomer guide](AttackOfTheNodes/docs/NEWCOMER_GUIDE.md), then
[the checked current state](AttackOfTheNodes/docs/CURRENT_STATE.md).
The dedicated VISION document follows in docs PR B; until then the guide
links to the distributed direction and Stash design.

[Node Contract Plan](AttackOfTheNodes/docs/NODE_CONTRACT_PLAN.md) owns the
immediate work order. Use `aotn nodes` / `aotn describe` for live node facts.
Read [the boundary contract](AttackOfTheNodes/docs/BACKEND_FRONTEND_BOUNDARY.md)
before backend changes motivated by the UI.

Work in one checkout; preserve unrelated edits and owner workflows. The owner
merges PRs. Process and environment notes are in the newcomer guide until
CONTRIBUTING is introduced in docs PR B. Old execution prompts are history.
