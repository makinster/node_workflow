"""Mounted-screen contract checks for schema-driven node config UI.

Used by `check_ui.py` and by generated `test_<node_type>_ui.py` smoke tests.
The checks mount `NodeConfigScreen` for one node type and verify:

- every schema field renders a generated widget;
- each widget lands in the top-level tab its schema declares;
- each widget participates in keyboard focus;
- dynamic rule declarations reference real fields;
- `enabled_when` / `visible_when` / `force_value_when` / `section_when`
  rule state matches the mounted defaults;
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
    from textual.widgets import Select, TabPane

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
            force_value_when = field_schema.get("force_value_when") or {}
            if force_value_when:
                if not isinstance(widget, Select):
                    problems.append(f"{field_name}: force_value_when requires Select widget")
                else:
                    forced = None
                    for candidate, condition in force_value_when.items():
                        if evaluate_field_condition(condition, values):
                            forced = candidate
                            break
                    if forced is not None:
                        if widget.value != forced:
                            problems.append(
                                f"{field_name}: force_value_when value mismatch at mount "
                                f"(value={widget.value!r}, expected {forced!r})"
                            )
                        if not widget.disabled:
                            problems.append(
                                f"{field_name}: force_value_when should disable select at mount"
                            )
            section_when = field_schema.get("section_when") or {}
            if section_when:
                expected_title = None
                for candidate, condition in section_when.items():
                    if evaluate_field_condition(condition, values):
                        expected_title = candidate
                        break
                if expected_title is not None:
                    headers = list(app.query(f"#form-section-{field_name}"))
                    if headers and str(headers[0].content) != str(expected_title):
                        problems.append(
                            f"{field_name}: section_when title mismatch at mount "
                            f"(title={headers[0].content!r}, expected {expected_title!r})"
                        )

        for field_name, field_schema in schema.items():
            for rule_key in ("enabled_when", "visible_when", "required_when"):
                condition = field_schema.get(rule_key)
                if condition is None:
                    continue
                if not isinstance(condition, dict) or not condition:
                    problems.append(f"{field_name}: {rule_key} must be a non-empty object")
                    continue
                for referenced in condition:
                    if referenced not in schema:
                        problems.append(
                            f"{field_name}: {rule_key} references unknown field {referenced!r}"
                        )
            for rule_key in ("section_when", "force_value_when"):
                mapping = field_schema.get(rule_key)
                if mapping is None:
                    continue
                if not isinstance(mapping, dict) or not mapping:
                    problems.append(f"{field_name}: {rule_key} must be a non-empty object")
                    continue
                if rule_key == "force_value_when" and str(
                    field_schema.get("type", "string")
                ).lower() != "select":
                    problems.append(f"{field_name}: force_value_when requires a select field")
                for condition in mapping.values():
                    if not isinstance(condition, dict) or not condition:
                        problems.append(
                            f"{field_name}: {rule_key} conditions must be non-empty objects"
                        )
                        continue
                    for referenced in condition:
                        if referenced not in schema:
                            problems.append(
                                f"{field_name}: {rule_key} references unknown field "
                                f"{referenced!r}"
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
