"""Schema-to-widget helpers for node and settings forms."""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Tuple

from textual.containers import Vertical
from textual.widgets import Checkbox, Input, Label, Select, SelectionList, TextArea


WidgetGetter = Callable[[], Dict[str, Any]]


def build_form(
    config_schema: Dict[str, Dict[str, Any]],
    values: Dict[str, Any] | None = None,
) -> Tuple[Vertical, WidgetGetter]:
    """Build a Textual form container and a getter for current values.

    This is intentionally frontend-only: it translates backend schemas into
    widgets without requiring backend changes for UI convenience.
    """
    values = values or {}
    children = []
    field_widgets: Dict[str, Any] = {}

    for field_name, field_schema in config_schema.items():
        field_type = str(field_schema.get("type", "string")).lower()
        label = field_schema.get("label", field_name)
        required = " *" if field_schema.get("required") else ""
        description = field_schema.get("description", "")
        current_value = values.get(field_name, field_schema.get("default", ""))

        children.append(Label(f"{label}{required}", classes="form-label"))
        if description:
            children.append(Label(str(description), classes="form-description"))

        widget = _widget_for_field(field_name, field_type, field_schema, current_value)
        field_widgets[field_name] = widget
        children.append(widget)

    container = Vertical(*children, classes="generated-form")

    def get_values() -> Dict[str, Any]:
        values_by_field: Dict[str, Any] = {}
        for field_name, widget in field_widgets.items():
            field_schema = config_schema.get(field_name, {})
            field_type = str(field_schema.get("type", "string")).lower()
            values_by_field[field_name] = _value_from_widget(widget, field_type)
        return values_by_field

    return container, get_values


def _widget_for_field(
    field_name: str,
    field_type: str,
    field_schema: Dict[str, Any],
    value: Any,
):
    if field_schema.get("options") and field_type not in {"multiselect", "boolean"}:
        return Select(
            _select_options(field_schema.get("options", [])),
            value=value if value not in (None, "") else Select.BLANK,
            id=f"field-{field_name}",
        )
    if field_type in {"multiline", "code"}:
        return TextArea(str(value or ""), id=f"field-{field_name}")
    if field_type == "boolean":
        return Checkbox(value=bool(value), id=f"field-{field_name}")
    if field_type == "select":
        return Select(
            _select_options(field_schema.get("options", [])),
            value=value if value not in (None, "") else Select.BLANK,
            id=f"field-{field_name}",
        )
    if field_type == "multiselect":
        options = [(str(option), option) for option in field_schema.get("options", [])]
        return SelectionList(*options, id=f"field-{field_name}")
    input_type = "text"
    if field_type == "integer":
        input_type = "integer"
    elif field_type in {"float", "number"}:
        input_type = "number"
    return Input(value=str(value or ""), type=input_type, id=f"field-{field_name}")


def _select_options(options: Iterable[Any]) -> list[tuple[str, Any]]:
    return [(str(option), option) for option in options]


def _value_from_widget(widget, field_type: str) -> Any:
    if isinstance(widget, Input):
        if field_type == "integer":
            try:
                return int(widget.value)
            except ValueError:
                return 0
        if field_type in {"float", "number"}:
            try:
                return float(widget.value)
            except ValueError:
                return 0.0
        return widget.value
    if isinstance(widget, TextArea):
        return widget.text
    if isinstance(widget, Checkbox):
        return widget.value
    if isinstance(widget, Select):
        return None if widget.value == Select.BLANK else widget.value
    if isinstance(widget, SelectionList):
        return list(widget.selected)
    return None
