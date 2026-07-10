"""Schema-to-widget helpers for node and settings forms."""

from __future__ import annotations

from collections import OrderedDict
import re
from typing import Any, Callable, Dict, Iterable, List, Tuple

from textual.containers import Horizontal, Vertical
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
FIELD_RULE_KEYS = {
    "enabled_when",
    "visible_when",
    "mutually_exclusive_with",
    "required_when",
    "section_when",
    "force_value_when",
}


def build_form(
    config_schema: Dict[str, Dict[str, Any]],
    values: Dict[str, Any] | None = None,
    secret_keys: Iterable[str] | None = None,
    vault_keys_by_type: Dict[str, List[Tuple[str, str]]] | None = None,
) -> Tuple[Vertical, WidgetGetter]:
    """Build a Textual form container and a getter for current values.

    This is intentionally frontend-only: it translates backend schemas into
    widgets without requiring backend changes for UI convenience.

    ``vault_keys_by_type`` maps a canonical vault type tag to selectable
    ``(label, key)`` options; string fields declaring ``vault_type`` render as
    a dropdown over the matching keys (same pattern as ``secret`` fields over
    ``secret_keys``).
    """
    values = values or {}
    secret_key_options = _secret_key_options(secret_keys)
    field_widgets: Dict[str, Any] = {}
    groups = group_config_schema(config_schema)

    if schema_uses_tabs(config_schema):
        tabs = TabbedContent(id="generated-form-tabs", classes="generated-form-tabs")
        for index, (group_name, group_schema) in enumerate(groups):
            children = []
            current_section: str | None = None
            for field_name, field_schema in group_schema.items():
                current_section = _append_section_label(
                    children, field_name, field_schema, current_section
                )
                children.extend(
                    _field_children(
                        field_name,
                        field_schema,
                        values,
                        field_widgets,
                        secret_key_options,
                        vault_keys_by_type,
                    )
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
        current_section = None
        for _, group_schema in groups:
            for field_name, field_schema in group_schema.items():
                current_section = _append_section_label(
                    children, field_name, field_schema, current_section
                )
                children.extend(
                    _field_children(
                        field_name,
                        field_schema,
                        values,
                        field_widgets,
                        secret_key_options,
                        vault_keys_by_type,
                    )
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


def humanize_field_name(field_name: str) -> str:
    """Titleize a snake_case field name as a sentence-case label.

    Used as a fallback when a schema field omits an explicit ``label`` so the
    generated form shows ``Request user input`` rather than the raw
    ``request_user_input`` identifier.
    """
    words = str(field_name).replace("_", " ").split()
    if not words:
        return str(field_name)
    text = " ".join(words)
    return text[:1].upper() + text[1:]


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


def _is_inline_field(field_type: str, field_schema: Dict[str, Any]) -> bool:
    """Return True for fields whose label shares a row with the widget.

    Single-line inputs and every dropdown (plain select, secret-key, vault-key)
    render inline; only tall widgets (multiline/code editors, multi-select
    lists) and self-labeled checkboxes get a label line of their own.
    """
    return field_type not in {"multiline", "code", "boolean", "multiselect"}


def _append_section_label(
    children: list[Any],
    field_name: str,
    field_schema: Dict[str, Any],
    current_section: str | None,
) -> str | None:
    """Insert a section header when a field starts a new declared section.

    The label id is derived from the field that opens the section run so a
    ``section_when`` rule on that field can retitle the header dynamically.
    """
    section = str(field_schema.get("section") or "").strip()
    if section and section != current_section:
        children.append(
            Label(
                section,
                classes="form-label nav-section form-section-label",
                id=f"form-section-{field_name}",
            )
        )
        return section
    return current_section if not section else section


def _field_children(
    field_name: str,
    field_schema: Dict[str, Any],
    values: Dict[str, Any],
    field_widgets: Dict[str, Any],
    secret_key_options: list[tuple[str, str]] | None = None,
    vault_keys_by_type: Dict[str, List[Tuple[str, str]]] | None = None,
) -> list[Any]:
    field_type = str(field_schema.get("type", "string")).lower()
    label = field_schema.get("label") or humanize_field_name(field_name)
    required = " *" if field_schema.get("required") else ""
    description = field_schema.get("description", "")
    current_value = values.get(field_name, field_schema.get("default", ""))

    children: list[Any] = []
    if field_type == "boolean":
        # Checkboxes carry their own label so the control reads as one row;
        # a declared description rides on the same row.
        widget = Checkbox(
            f"{label}{required}",
            value=bool(current_value),
            id=f"field-{field_name}",
        )
        field_widgets[field_name] = widget
        if description:
            children.append(
                Horizontal(
                    widget,
                    Label(
                        str(description),
                        classes="form-description form-description-inline",
                        id=f"field-desc-{field_name}",
                    ),
                    classes="form-inline-row",
                    id=f"field-row-{field_name}",
                )
            )
        else:
            children.append(widget)
        return children

    widget = _widget_for_field(
        field_name,
        field_type,
        field_schema,
        current_value,
        secret_key_options,
        vault_keys_by_type,
    )
    field_widgets[field_name] = widget

    # The header line carries the label and, inline after it, the description.
    header_items: list[Any] = [
        Label(
            f"{label}{required}:",
            classes="form-label-inline",
            id=f"field-label-{field_name}",
        )
    ]
    if description:
        header_items.append(
            Label(
                str(description),
                classes="form-description form-description-inline",
                id=f"field-desc-{field_name}",
            )
        )

    if isinstance(widget, Select) or not _is_inline_field(field_type, field_schema):
        # Dropdowns and tall widgets sit on their own line under the header so
        # their left edges align instead of being offset by label width.
        children.append(
            Horizontal(
                *header_items,
                classes="form-header-row",
                id=f"field-row-{field_name}",
            )
        )
        children.append(widget)
    else:
        # Single-line inputs share the row: label, description, input.
        children.append(
            Horizontal(
                *header_items,
                widget,
                classes="form-inline-row",
                id=f"field-row-{field_name}",
            )
        )
    return children


def _widget_for_field(
    field_name: str,
    field_type: str,
    field_schema: Dict[str, Any],
    value: Any,
    secret_key_options: list[tuple[str, str]] | None = None,
    vault_keys_by_type: Dict[str, List[Tuple[str, str]]] | None = None,
):
    placeholder = str(field_schema.get("placeholder", ""))
    if field_schema.get("secret") and secret_key_options is not None:
        options = list(secret_key_options)
        current_value = "" if value is None else str(value)
        option_values = {option_value for _, option_value in options}
        if current_value and current_value not in option_values:
            options.append((f"{current_value} (not stored)", current_value))
        return Select(
            options,
            value=current_value if current_value else Select.NULL,
            id=f"field-{field_name}",
            allow_blank=True,
        )
    vault_type = field_schema.get("vault_type")
    if vault_type and vault_keys_by_type is not None:
        options = list(vault_keys_by_type.get(str(vault_type), []))
        current_value = "" if value is None else str(value)
        option_values = {option_value for _, option_value in options}
        if current_value and current_value not in option_values:
            options.append((f"{current_value} (not declared)", current_value))
        return Select(
            options,
            value=current_value if current_value else Select.NULL,
            id=f"field-{field_name}",
            allow_blank=True,
        )
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
            (label, option_value, option_value in selected_values)
            for label, option_value in _select_options(field_schema.get("options", []))
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
    """Normalize schema options to (label, value) pairs.

    Supported entry shapes: plain scalars (label == value), label/value
    mappings, and 2-item sequences. Backends read the stable value; the label
    is display-only.
    """
    normalized: list[tuple[str, Any]] = []
    for option in options:
        if isinstance(option, dict):
            option_value = option.get("value")
            label = option.get("label", option_value)
            normalized.append((str(label), option_value))
        elif isinstance(option, (tuple, list)) and len(option) == 2:
            normalized.append((str(option[0]), option[1]))
        else:
            normalized.append((str(option), option))
    return normalized


def _secret_key_options(secret_keys: Iterable[str] | None) -> list[tuple[str, str]] | None:
    """Return Select-compatible options for stored secret key names."""
    if secret_keys is None:
        return None
    keys = sorted({str(key).strip() for key in secret_keys if str(key).strip()})
    return [(key, key) for key in keys]


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


def schema_has_field_rules(config_schema: Dict[str, Dict[str, Any]]) -> bool:
    """Return true when any field declares a dynamic-form rule key."""
    return any(
        key in field_schema
        for field_schema in config_schema.values()
        for key in FIELD_RULE_KEYS
    )


def evaluate_field_condition(condition: Any, values: Dict[str, Any]) -> bool:
    """Evaluate an enabled_when/visible_when condition against form values.

    A condition is a mapping of field name to expected value. All entries must
    match (AND). An expected value may be a list, which matches when the
    current value equals any listed entry (OR within one field).
    """
    if not isinstance(condition, dict) or not condition:
        return True
    for field_name, expected in condition.items():
        current = values.get(field_name)
        if isinstance(expected, list):
            if current not in expected:
                return False
        elif current != expected:
            return False
    return True


def mutual_exclusion_targets(
    field_name: str,
    config_schema: Dict[str, Dict[str, Any]],
) -> list[str]:
    """Return fields to uncheck when the named boolean field becomes true.

    Declarations are symmetric: if either side lists the other, both exclude
    each other.
    """
    targets: list[str] = []
    declared = config_schema.get(field_name, {}).get("mutually_exclusive_with") or []
    for other in declared:
        if other != field_name and other not in targets:
            targets.append(str(other))
    for other_name, other_schema in config_schema.items():
        partners = other_schema.get("mutually_exclusive_with") or []
        if other_name != field_name and field_name in partners and other_name not in targets:
            targets.append(other_name)
    return targets


def apply_field_rules(
    root: Any,
    config_schema: Dict[str, Dict[str, Any]],
    values: Dict[str, Any],
) -> None:
    """Apply dynamic-form rules to mounted generated widgets.

    `root` is any Textual DOM node with `.query` (screen or container). Fields
    are located by their generated `field-<name>` ids so rules work across
    config tabs that were built by separate `build_form` calls.

    Supported per-field rule keys: `enabled_when` (grey), `visible_when`
    (hide), `required_when` (add the `*` marker live), `section_when` (retitle
    the field's section header), and `force_value_when` (lock a select to a
    value while a condition holds). All conditions share the mapping shape
    evaluated by `evaluate_field_condition`.
    """
    for field_name, field_schema in config_schema.items():
        enabled_when = field_schema.get("enabled_when")
        visible_when = field_schema.get("visible_when")
        required_when = field_schema.get("required_when")
        section_when = field_schema.get("section_when")
        force_value_when = field_schema.get("force_value_when")
        if not any(
            (enabled_when, visible_when, required_when, section_when, force_value_when)
        ):
            continue
        widgets = list(root.query(f"#field-{field_name}"))
        widget = widgets[0] if widgets else None

        if enabled_when is not None and widget is not None:
            widget.disabled = not evaluate_field_condition(enabled_when, values)
        if visible_when is not None and widget is not None:
            visible = evaluate_field_condition(visible_when, values)
            widget.display = visible
            for extra_id in (
                f"field-label-{field_name}",
                f"field-desc-{field_name}",
                f"field-row-{field_name}",
            ):
                for extra in root.query(f"#{extra_id}"):
                    extra.display = visible
        if required_when is not None:
            required = bool(field_schema.get("required")) or evaluate_field_condition(
                required_when, values
            )
            _set_label_required(root, field_name, field_schema, required)
        if section_when:
            title = None
            for candidate, condition in section_when.items():
                if evaluate_field_condition(condition, values):
                    title = candidate
                    break
            default_title = str(field_schema.get("section") or "")
            for header in root.query(f"#form-section-{field_name}"):
                header.update(title or default_title)
        if force_value_when and isinstance(widget, Select):
            forced = None
            for value, condition in force_value_when.items():
                if evaluate_field_condition(condition, values):
                    forced = value
                    break
            if forced is not None:
                if widget.value != forced:
                    widget.value = forced
                widget.disabled = True
            elif enabled_when is None:
                widget.disabled = False


def _set_label_required(
    root: Any,
    field_name: str,
    field_schema: Dict[str, Any],
    required: bool,
) -> None:
    """Refresh a field's rendered label / checkbox text to reflect required."""
    base = field_schema.get("label") or humanize_field_name(field_name)
    suffix = " *" if required else ""
    for label in root.query(f"#field-label-{field_name}"):
        inline = "form-label-inline" in getattr(label, "classes", set())
        label.update(f"{base}{suffix}:" if inline else f"{base}{suffix}")
    if str(field_schema.get("type", "")).lower() == "boolean":
        for checkbox in root.query(f"#field-{field_name}"):
            if isinstance(checkbox, Checkbox):
                checkbox.label = f"{base}{suffix}"


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
