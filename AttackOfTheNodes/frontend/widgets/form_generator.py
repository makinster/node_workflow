"""Schema-to-widget helpers for node and settings forms."""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Callable, Dict, Iterable, List, Tuple

from textual.containers import Vertical
from textual.validation import Integer, Length, Number, Validator
from textual.widgets import (
    Checkbox,
    Input,
    Label,
    Select,
    SelectionList,
    TabbedContent,
    TabPane,
    TextArea,
)

from frontend.widgets.command_input import CommandInput, CommandTextArea


WidgetGetter = Callable[[], Dict[str, Any]]
DEFAULT_GROUP = "Settings"
GroupedSchema = List[Tuple[str, Dict[str, Dict[str, Any]]]]


def build_form(
    config_schema: Dict[str, Dict[str, Any]],
    values: Dict[str, Any] | None = None,
) -> Tuple[Vertical, WidgetGetter]:
    """Build a Textual form container and a getter for current values.

    This is intentionally frontend-only: it translates backend schemas into
    widgets without requiring backend changes for UI convenience.
    """
    values = values or {}
    field_widgets: Dict[str, Any] = {}
    groups = group_config_schema(config_schema)

    if schema_uses_tabs(config_schema):
        tabs = TabbedContent(id="generated-form-tabs", classes="generated-form-tabs")
        for index, (group_name, group_schema) in enumerate(groups):
            children = []
            for field_name, field_schema in group_schema.items():
                children.extend(
                    _field_children(field_name, field_schema, values, field_widgets)
                )
            tabs.compose_add_child(
                TabPane(
                    group_name,
                    Vertical(*children, classes="generated-form-page"),
                    id=f"config-tab-{_slug_id(group_name, index)}",
                )
            )
        container = Vertical(tabs, classes="generated-form generated-form-tabbed")
    else:
        children = []
        for _, group_schema in groups:
            for field_name, field_schema in group_schema.items():
                children.extend(
                    _field_children(field_name, field_schema, values, field_widgets)
                )
        container = Vertical(*children, classes="generated-form")

    def get_values() -> Dict[str, Any]:
        values_by_field: Dict[str, Any] = {}
        for field_name, widget in field_widgets.items():
            field_schema = config_schema.get(field_name, {})
            field_type = str(field_schema.get("type", "string")).lower()
            values_by_field[field_name] = _value_from_widget(widget, field_type)
        return values_by_field

    return container, get_values


def group_config_schema(config_schema: Dict[str, Dict[str, Any]]) -> GroupedSchema:
    """Group schema fields by their optional group key while preserving order."""
    grouped: "OrderedDict[str, Dict[str, Dict[str, Any]]]" = OrderedDict()
    for field_name, field_schema in config_schema.items():
        group_name = str(field_schema.get("group") or DEFAULT_GROUP).strip()
        if not group_name:
            group_name = DEFAULT_GROUP
        grouped.setdefault(group_name, OrderedDict())[field_name] = field_schema
    return list(grouped.items())


def schema_uses_tabs(config_schema: Dict[str, Dict[str, Any]]) -> bool:
    """Return true when a schema has enough groups to justify tabs."""
    return len(group_config_schema(config_schema)) > 1


def _field_children(
    field_name: str,
    field_schema: Dict[str, Any],
    values: Dict[str, Any],
    field_widgets: Dict[str, Any],
) -> list[Any]:
    field_type = str(field_schema.get("type", "string")).lower()
    label = field_schema.get("label", field_name)
    required = " *" if field_schema.get("required") else ""
    description = field_schema.get("description", "")
    current_value = values.get(field_name, field_schema.get("default", ""))

    children = []
    children.append(Label(f"{label}{required}", classes="form-label"))
    if description:
        children.append(Label(str(description), classes="form-description"))

    widget = _widget_for_field(field_name, field_type, field_schema, current_value)
    field_widgets[field_name] = widget
    children.append(widget)
    return children


def _widget_for_field(
    field_name: str,
    field_type: str,
    field_schema: Dict[str, Any],
    value: Any,
):
    placeholder = str(field_schema.get("placeholder", ""))
    if field_schema.get("options") and field_type not in {"multiselect", "boolean"}:
        return Select(
            _select_options(field_schema.get("options", [])),
            value=value if value not in (None, "") else Select.NULL,
            id=f"field-{field_name}",
            allow_blank=False,
        )
    if field_type in {"multiline", "code"}:
        widget = CommandTextArea(
            "" if value is None else str(value),
            id=f"field-{field_name}",
            placeholder=placeholder,
            language=field_schema.get("language") if field_type == "code" else None,
        )
        height = field_schema.get("height")
        if height is not None:
            try:
                widget.styles.height = max(1, int(height))
            except (TypeError, ValueError):
                pass
        return widget
    if field_type == "boolean":
        return Checkbox(value=bool(value), id=f"field-{field_name}")
    if field_type == "select":
        return Select(
            _select_options(field_schema.get("options", [])),
            value=value if value not in (None, "") else Select.NULL,
            id=f"field-{field_name}",
            allow_blank=False,
        )
    if field_type == "multiselect":
        selected_values = _selected_values(value)
        options = [
            (str(option), option, option in selected_values)
            for option in field_schema.get("options", [])
        ]
        return SelectionList(*options, id=f"field-{field_name}")
    input_type = "text"
    if field_type == "integer":
        input_type = "integer"
    elif field_type in {"float", "number"}:
        input_type = "number"
    text_value = "" if value is None else str(value)
    return CommandInput(
        value=text_value,
        placeholder=placeholder,
        type=input_type,
        id=f"field-{field_name}",
        validators=_validators_for_field(field_type, field_schema),
    )


def _select_options(options: Iterable[Any]) -> list[tuple[str, Any]]:
    return [(str(option), option) for option in options]


def _selected_values(value: Any) -> set[Any]:
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return set(value)
    return {value}


def _validators_for_field(
    field_type: str,
    field_schema: Dict[str, Any],
) -> list[Validator]:
    validators: list[Validator] = []
    minimum = field_schema.get("min")
    maximum = field_schema.get("max")
    if field_type == "integer" and (minimum is not None or maximum is not None):
        validators.append(Integer(minimum=minimum, maximum=maximum))
    elif field_type in {"float", "number"} and (
        minimum is not None or maximum is not None
    ):
        validators.append(Number(minimum=minimum, maximum=maximum))

    min_length = field_schema.get("min_length")
    max_length = field_schema.get("max_length")
    if field_type == "string" and (min_length is not None or max_length is not None):
        validators.append(Length(minimum=min_length, maximum=max_length))
    return validators


def _slug_id(value: str, index: int) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return f"{index}-{slug or 'group'}"


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
        return None if widget.value == Select.NULL else widget.value
    if isinstance(widget, SelectionList):
        return list(widget.selected)
    return None
