"""Tests for Headless Plan H4: form generator schema keys.

Covers label/value select options (backend reads stable machine values) and
the schema keys not already exercised by test_form_rules.py or the generic
hint tests in test_debug_nodes.py.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_form_generator.py -v
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# _select_options normalization (pure function)
# ---------------------------------------------------------------------------


def test_select_options_normalizes_all_entry_shapes():
    from frontend.widgets.form_generator import _select_options

    options = [
        "plain",
        {"label": "Fast mode", "value": "fast"},
        ("Safe mode", "safe"),
        ["Verbose mode", "verbose"],
        {"value": "unlabeled"},
        7,
    ]
    assert _select_options(options) == [
        ("plain", "plain"),
        ("Fast mode", "fast"),
        ("Safe mode", "safe"),
        ("Verbose mode", "verbose"),
        ("unlabeled", "unlabeled"),
        ("7", 7),
    ]
    print("test_select_options_normalizes_all_entry_shapes PASSED")


# ---------------------------------------------------------------------------
# Mounted widget behavior
# ---------------------------------------------------------------------------


def _mount_form(schema, values):
    """Mount a generated form and return (app context manager factory)."""
    from textual.app import App, ComposeResult

    from frontend.widgets.form_generator import build_form

    holder = {}

    class FormApp(App):
        def compose(self) -> ComposeResult:
            form, getter = build_form(schema, values)
            holder["getter"] = getter
            yield form

    return FormApp(), holder


def test_select_label_value_round_trips_machine_value():
    asyncio.run(_test_select_label_value_round_trips_machine_value())


async def _test_select_label_value_round_trips_machine_value():
    from textual.widgets import Select

    schema = {
        "mode": {
            "type": "select",
            "label": "Mode",
            "options": [
                {"label": "Fast mode", "value": "fast"},
                {"label": "Safe mode", "value": "safe"},
            ],
        },
    }
    app, holder = _mount_form(schema, {"mode": "safe"})
    async with app.run_test():
        select = app.query_one("#field-mode", Select)
        # Stored machine value selected; display label differs from value
        assert select.value == "safe"
        labels = [str(label) for label, _ in select._options]
        assert "Safe mode" in labels and "fast" not in labels
        # Backend reads the machine value, not the display label
        assert holder["getter"]()["mode"] == "safe"

        select.value = "fast"
        assert holder["getter"]()["mode"] == "fast"
    print("test_select_label_value_round_trips_machine_value PASSED")


def test_select_plain_string_options_unchanged():
    asyncio.run(_test_select_plain_string_options_unchanged())


async def _test_select_plain_string_options_unchanged():
    from textual.widgets import Select

    schema = {
        "mode": {"type": "select", "label": "Mode", "options": ["short", "long"]},
    }
    app, holder = _mount_form(schema, {"mode": "long"})
    async with app.run_test():
        select = app.query_one("#field-mode", Select)
        assert select.value == "long"
        assert holder["getter"]()["mode"] == "long"
    print("test_select_plain_string_options_unchanged PASSED")


def test_string_field_with_options_uses_label_value_pairs():
    asyncio.run(_test_string_field_with_options_uses_label_value_pairs())


async def _test_string_field_with_options_uses_label_value_pairs():
    """Non-select field types with options also render a Select with pairs."""
    from textual.widgets import Select

    schema = {
        "model": {
            "type": "string",
            "label": "Model",
            "options": [
                {"label": "GPT-4 (recommended)", "value": "gpt-4"},
                {"label": "Claude 3", "value": "claude-3"},
            ],
        },
    }
    app, holder = _mount_form(schema, {"model": "claude-3"})
    async with app.run_test():
        select = app.query_one("#field-model", Select)
        assert select.value == "claude-3"
        assert holder["getter"]()["model"] == "claude-3"
    print("test_string_field_with_options_uses_label_value_pairs PASSED")


def test_multiselect_label_value_round_trips_machine_values():
    asyncio.run(_test_multiselect_label_value_round_trips_machine_values())


async def _test_multiselect_label_value_round_trips_machine_values():
    from textual.widgets import SelectionList

    schema = {
        "features": {
            "type": "multiselect",
            "label": "Features",
            "options": [
                {"label": "Fast mode", "value": "fast"},
                {"label": "Safe mode", "value": "safe"},
                {"label": "Verbose logging", "value": "verbose"},
            ],
        },
    }
    app, holder = _mount_form(schema, {"features": ["fast", "verbose"]})
    async with app.run_test():
        selection = app.query_one("#field-features", SelectionList)
        assert set(selection.selected) == {"fast", "verbose"}
        assert set(holder["getter"]()["features"]) == {"fast", "verbose"}
    print("test_multiselect_label_value_round_trips_machine_values PASSED")


# ---------------------------------------------------------------------------
# Schema key matrix: keys not covered by other suites
# ---------------------------------------------------------------------------


def test_label_required_and_description_render():
    asyncio.run(_test_label_required_and_description_render())


async def _test_label_required_and_description_render():
    from textual.widgets import Label

    schema = {
        "name": {
            "type": "string",
            "label": "Display name",
            "required": True,
            "description": "Shown in the editor list",
        },
    }
    app, _ = _mount_form(schema, {})
    async with app.run_test():
        label = app.query_one("#field-label-name", Label)
        assert str(label.render()).startswith("Display name *")
        description = app.query_one("#field-desc-name", Label)
        assert str(description.render()) == "Shown in the editor list"
    print("test_label_required_and_description_render PASSED")


def test_default_used_when_value_absent():
    asyncio.run(_test_default_used_when_value_absent())


async def _test_default_used_when_value_absent():
    from textual.widgets import Input

    schema = {
        "retries": {"type": "integer", "label": "Retries", "default": 3},
    }
    app, holder = _mount_form(schema, {})
    async with app.run_test():
        assert app.query_one("#field-retries", Input).value == "3"
        assert holder["getter"]()["retries"] == 3
    print("test_default_used_when_value_absent PASSED")


def test_boolean_field_renders_checkbox_and_round_trips():
    asyncio.run(_test_boolean_field_renders_checkbox_and_round_trips())


async def _test_boolean_field_renders_checkbox_and_round_trips():
    from textual.widgets import Checkbox

    schema = {"enabled": {"type": "boolean", "label": "Enabled"}}
    app, holder = _mount_form(schema, {"enabled": True})
    async with app.run_test():
        checkbox = app.query_one("#field-enabled", Checkbox)
        assert checkbox.value is True
        checkbox.value = False
        assert holder["getter"]()["enabled"] is False
    print("test_boolean_field_renders_checkbox_and_round_trips PASSED")


def test_integer_min_max_attach_integer_validator():
    asyncio.run(_test_integer_min_max_attach_integer_validator())


async def _test_integer_min_max_attach_integer_validator():
    from textual.validation import Integer
    from textual.widgets import Input

    schema = {
        "count": {"type": "integer", "label": "Count", "min": 1, "max": 10},
    }
    app, _ = _mount_form(schema, {"count": 5})
    async with app.run_test():
        field = app.query_one("#field-count", Input)
        integer_validators = [v for v in field.validators if isinstance(v, Integer)]
        assert integer_validators, "Integer validator not attached"
        assert integer_validators[0].minimum == 1
        assert integer_validators[0].maximum == 10
    print("test_integer_min_max_attach_integer_validator PASSED")


def test_string_length_limits_attach_length_validator():
    asyncio.run(_test_string_length_limits_attach_length_validator())


async def _test_string_length_limits_attach_length_validator():
    from textual.validation import Length
    from textual.widgets import Input

    schema = {
        "alias": {
            "type": "string",
            "label": "Alias",
            "min_length": 1,
            "max_length": 32,
        },
    }
    app, _ = _mount_form(schema, {"alias": "x"})
    async with app.run_test():
        field = app.query_one("#field-alias", Input)
        length_validators = [v for v in field.validators if isinstance(v, Length)]
        assert length_validators, "Length validator not attached"
        assert length_validators[0].minimum == 1
        assert length_validators[0].maximum == 32
    print("test_string_length_limits_attach_length_validator PASSED")


def test_code_field_sets_language():
    asyncio.run(_test_code_field_sets_language())


async def _test_code_field_sets_language():
    from frontend.widgets.command_input import CommandTextArea

    schema = {
        "script": {"type": "code", "label": "Script", "language": "python"},
    }
    app, _ = _mount_form(schema, {"script": "print('hi')"})
    async with app.run_test():
        area = app.query_one("#field-script", CommandTextArea)
        assert area.language == "python"
        assert area.text == "print('hi')"
    print("test_code_field_sets_language PASSED")


def test_numeric_coercion_on_invalid_input_defaults_to_zero():
    asyncio.run(_test_numeric_coercion_on_invalid_input_defaults_to_zero())


async def _test_numeric_coercion_on_invalid_input_defaults_to_zero():
    from textual.widgets import Input

    schema = {
        "count": {"type": "integer", "label": "Count"},
        "ratio": {"type": "float", "label": "Ratio"},
    }
    app, holder = _mount_form(schema, {"count": 2, "ratio": 0.5})
    async with app.run_test():
        app.query_one("#field-count", Input).value = ""
        app.query_one("#field-ratio", Input).value = ""
        values = holder["getter"]()
        assert values["count"] == 0
        assert values["ratio"] == 0.0
    print("test_numeric_coercion_on_invalid_input_defaults_to_zero PASSED")
