"""Mounted-screen contract checks for schema-driven node config UI.

Used by `check_ui.py` and by generated `test_<node_type>_ui.py` smoke tests.
The checks mount `NodeConfigScreen` for one node type and verify:

- every schema field renders a generated widget;
- each widget lands in the top-level tab its schema declares;
- each widget participates in keyboard focus;
- `enabled_when` / `visible_when` rule state matches the mounted defaults;
- `mutually_exclusive_with` declarations reference real boolean fields.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT / "AttackOfTheNodes"

# These schema keys render through dedicated screen sections, not the
# generated form, so they are skipped by widget checks.
NON_FORM_SCHEMA_KEYS = {"membank_outputs", "membank_inputs", "transient_outputs"}
STRUCTURAL_NODE_TYPES = {"branch_node", "merge_node", "branch_end_node"}
TAB_PANE_IDS = {
    "source": "node-config-tab-core",
    "parameters": "node-config-tab-parameters",
    "payloads": "node-config-tab-outputs",
}


def _normalize_tab(tab_name: Any) -> str:
    value = str(tab_name or "parameters").strip().lower()
    if value in {"source", "core"}:
        return "source"
    if value in {"payload", "payloads", "output", "outputs"}:
        return "payloads"
    return "parameters"


def run_ui_check(node_type: str, project_root: Path = PROJECT_ROOT) -> list[str]:
    """Mount the node's config screen and return a list of contract problems."""
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return asyncio.run(collect_ui_problems(node_type))


async def collect_ui_problems(node_type: str) -> list[str]:
    from textual.app import App, ComposeResult
    from textual.widgets import TabPane

    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap
    from frontend.screens.node_config import NodeConfigScreen
    from frontend.widgets.form_generator import evaluate_field_condition

    factory = NodeFactory()
    if not factory.is_valid_node_type(node_type):
        return [f"Unknown node type: {node_type}"]
    if node_type in STRUCTURAL_NODE_TYPES:
        raise ValueError(
            f"{node_type} uses structural config UI; check_ui covers "
            "schema-driven nodes only"
        )

    metadata = next(
        item
        for item in factory.get_node_types_metadata()
        if item["type"] == node_type
    )
    schema: dict[str, dict[str, Any]] = dict(metadata.get("config_schema") or {})
    for key in NON_FORM_SCHEMA_KEYS:
        schema.pop(key, None)
    if node_type == "wait_until_node":
        schema.pop("target_node_ids", None)

    workflow_map = WorkflowMap(factory, EventBus())
    workflow_map.create_new(f"ui_check_{node_type}")
    node_id = workflow_map.add_node(node_type)
    node_data = workflow_map.get_node_data(node_id)
    screen = NodeConfigScreen(factory, workflow_map, node_id, node_data)

    class CheckApp(App):
        def compose(self) -> ComposeResult:
            yield screen

    problems: list[str] = []
    app = CheckApp()
    async with app.run_test() as pilot:
        await pilot.pause()

        widgets: dict[str, Any] = {}
        for field_name, field_schema in schema.items():
            found = list(app.query(f"#field-{field_name}"))
            if not found:
                problems.append(
                    f"{field_name}: no generated widget mounted (#field-{field_name})"
                )
                continue
            widget = found[0]
            widgets[field_name] = widget

            expected_pane = TAB_PANE_IDS[_normalize_tab(field_schema.get("tab"))]
            pane = next(
                (ancestor for ancestor in widget.ancestors if isinstance(ancestor, TabPane)),
                None,
            )
            if pane is None:
                problems.append(f"{field_name}: widget is not inside a config tab")
            elif pane.id != expected_pane:
                problems.append(
                    f"{field_name}: rendered in tab {pane.id!r}, expected {expected_pane!r}"
                )
            if not widget.can_focus:
                problems.append(f"{field_name}: widget is not keyboard focusable")

        values = screen._get_form_values() if screen._get_form_values else {}
        for field_name, field_schema in schema.items():
            widget = widgets.get(field_name)
            if widget is None:
                continue
            enabled_when = field_schema.get("enabled_when")
            if enabled_when is not None:
                expected_disabled = not evaluate_field_condition(enabled_when, values)
                if bool(widget.disabled) != expected_disabled:
                    problems.append(
                        f"{field_name}: enabled_when state mismatch at mount "
                        f"(disabled={widget.disabled}, expected disabled={expected_disabled})"
                    )
            visible_when = field_schema.get("visible_when")
            if visible_when is not None:
                expected_visible = evaluate_field_condition(visible_when, values)
                if bool(widget.display) != expected_visible:
                    problems.append(
                        f"{field_name}: visible_when state mismatch at mount "
                        f"(display={widget.display}, expected display={expected_visible})"
                    )

        for field_name, field_schema in schema.items():
            partners = field_schema.get("mutually_exclusive_with") or []
            for partner in partners:
                partner_schema = schema.get(partner)
                if partner_schema is None:
                    problems.append(
                        f"{field_name}: mutually_exclusive_with references unknown "
                        f"field {partner!r}"
                    )
                elif str(partner_schema.get("type", "string")).lower() != "boolean":
                    problems.append(
                        f"{field_name}: mutually_exclusive_with partner {partner!r} "
                        "is not a boolean field"
                    )

    return problems
