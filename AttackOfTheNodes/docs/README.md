# AttackOfTheNodes docs

Start with the [Newcomer Guide](NEWCOMER_GUIDE.md) for purpose, setup,
a first workflow and runtime traps. Then check [Current State](CURRENT_STATE.md)
for the dated baseline, open PRs, verification and owner decisions.

The [Node Contract Plan](NODE_CONTRACT_PLAN.md) owns immediate delivery order;
the [Distributed Build Plan](DISTRIBUTED_BUILD_PLAN.md) and
[Stash proposal](STASH_PROPOSAL.md) preserve the longer-term direction.
VISION and CONTRIBUTING will join this route in docs PR B.

## Choose a task

| If you need to… | Read | Likely code / focused check |
|---|---|---|
| Set up, run or test | [Newcomer Guide](NEWCOMER_GUIDE.md) | `main.py`, full suite below |
| Build or inspect workflows | [Workflow Authoring](WORKFLOW_AUTHORING.md) | `backend/authoring.py`, `tests/test_authoring.py`, `tests/test_authoring_examples.py` |
| Add/change a node | [Node Standards](NODE_STANDARDS.md), then [Node Helper](NODE_HELPER.md) | `backend/nodes/`, helper safety and commands in Node Helper |
| Check node ideas or live capabilities | [Node Catalog](NODE_CATALOG.md), `aotn nodes` / `describe` | Catalog includes proposals; CLI reads registered contracts |
| Fix editor/config UI | [UI Quick Reference](UI_QUICK_REFERENCE.md), [Boundary](BACKEND_FRONTEND_BOUNDARY.md) | `frontend/screens/`, `frontend/widgets/`; debug test filter below |
| Change runtime/routing | [Architecture](ARCHITECTURE.md), [Boundary](BACKEND_FRONTEND_BOUNDARY.md) | `backend/supervisor.py`, `backend/master_state.py`; runtime test filter below |
| Diagnose run-screen state | [Execution Status Contract](EXECUTION_STATUS_CONTRACT.md), [Architecture](ARCHITECTURE.md) | `tests/test_execution_status.py` |
| Change file output/window behavior | [Node Standards](NODE_STANDARDS.md), [File Output decisions](FILE_OUTPUT_BUILD_PLAN.md) | `tests/test_window_manager.py`, `tests/generated/test_file_output_node.py` |
| Continue planned work | [Current State](CURRENT_STATE.md), [Node Contract Plan](NODE_CONTRACT_PLAN.md) | Consult [Project Backlog](PROJECT_BACKLOG.md) before redesigning |
| Trace a decision or recent change | [Session Log](SESSION_LOG.md), [Migration Notes](DOCS_MIGRATION_NOTES.md) | [Older log](archive/SESSION_LOG_HISTORY.md), `archive/` |

## Verification

From `AttackOfTheNodes/`, with a checkout-local `.venv` at the repository root:

```bash
../.venv/bin/python -m pytest -q
../.venv/bin/python -m pytest tests/test_debug_nodes.py -q -k 'node_config or command_input or selection'
../.venv/bin/python -m pytest tests/test_debug_nodes.py -q -k '<runtime_behavior_name>'
../.venv/bin/python -m pytest tests/test_execution_status.py -q
../.venv/bin/python -m pytest tests/test_forwarding.py -q
```

In the owner's separate worktrees, substitute the shared interpreter documented
in [Current State](CURRENT_STATE.md). Run `git diff --check` for documentation.
Choose tests for the changed behavior; a focused command is not the full suite.

## Documentation transition

This router absorbs the task-selection route from [Task Index](TASK_INDEX.md).
Older handoffs and execution prompts are historical, not instructions to redo
completed phases or merge PRs. The taxonomy rename was cancelled:
`primary_family` and frontend `group` remain separate from legacy `category`.
Full consolidation and archival follow in PR B, after preserving unique reasoning.
The [retained audit report](audits/docs_audit_2026_10_17/MASTER_REPORT.md)
records the findings; its supporting artifacts were not retained.
