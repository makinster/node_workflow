"""C5: one number policy for the node editor and the validator.

Owner, 2026-10-15: an unreadable, non-finite or out-of-range number blocks
the save with an inline error (the typed text stays); limits are declared
per field (``min`` / ``max`` / ``min_exclusive``); blank means the default;
the validator applies the same check (``invalid_number``) before a run.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_number_policy.py -v
"""

import asyncio
import os

import pytest

from backend.event_bus import EventBus
from backend.field_types import check_number
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()
CSS = os.path.join(os.path.dirname(__file__), "..", "frontend", "styles.tcss")
FLOAT_0_60 = {"type": "float", "min": 0.0, "max": 60.0}
INT_MIN_1 = {"type": "integer", "min": 1}
ABOVE_0 = {"type": "float", "min": 0, "min_exclusive": True}


# --- The shared check -------------------------------------------------------------


@pytest.mark.parametrize("info, raw, default, expected", [
    (FLOAT_0_60, "2.5", None, (2.5, "")),
    (FLOAT_0_60, 3, None, (3.0, "")),
    (FLOAT_0_60, " 4 ", None, (4.0, "")),
    (FLOAT_0_60, "abc", None, (None, "Enter a number")),
    (FLOAT_0_60, "nan", None, (None, "Enter a finite number")),
    (FLOAT_0_60, "inf", None, (None, "Enter a finite number")),
    (FLOAT_0_60, "-1", None, (None, "Must be at least 0")),
    (FLOAT_0_60, "61", None, (None, "Must be at most 60")),
    (FLOAT_0_60, "", 0.1, (0.1, "")),
    (FLOAT_0_60, None, 0.1, (0.1, "")),
    (FLOAT_0_60, "", None, (None, "Enter a number")),
    (FLOAT_0_60, True, None, (None, "Enter a number")),
    (INT_MIN_1, "3", None, (3, "")),
    (INT_MIN_1, "3.0", None, (3, "")),
    (INT_MIN_1, "3.5", None, (None, "Enter a whole number")),
    (INT_MIN_1, "x", None, (None, "Enter a whole number")),
    (INT_MIN_1, "0", None, (None, "Must be at least 1")),
    (ABOVE_0, "0", None, (None, "Must be more than 0")),
    (ABOVE_0, "0.5", None, (0.5, "")),
    ({"type": "float"}, "-1e9", None, (-1e9, "")),
])
def test_check_number(info, raw, default, expected):
    assert check_number(info, raw, default) == expected


def test_bad_default_is_reported_too():
    assert check_number(INT_MIN_1, "", 0) == (None, "Must be at least 1")


# --- Field limits declared on nodes --------------------------------------------------


def _schema(node_type):
    meta = next(m for m in FACTORY.get_node_types_metadata() if m["type"] == node_type)
    return meta["config_schema"], meta["default_config"]


@pytest.mark.parametrize("node_type, field, bad, problem", [
    ("sleep_node", "duration", "-1", "Must be at least 0"),
    ("http_request_node", "timeout_seconds", "0", "Must be more than 0"),
    ("chat_completion_node", "temperature", "1.5", "Must be at most 1"),
    ("chat_completion_node", "max_tokens", "0", "Must be at least 1"),
    ("repeat_counter_node", "max_visits", "0", "Must be at least 1"),
    ("branch_node", "branch_count", "65", "Must be at most 64"),
])
def test_declared_limits(node_type, field, bad, problem):
    schema, defaults = _schema(node_type)
    assert check_number(schema[field], bad, defaults.get(field)) == (None, problem)
    assert check_number(schema[field], "", defaults.get(field))[1] == "", "default must pass"


def test_every_default_passes_its_own_field():
    for meta in FACTORY.get_node_types_metadata():
        defaults = meta.get("default_config") or {}
        for name, info in (meta.get("config_schema") or {}).items():
            if isinstance(info, dict) and info.get("type") in {"integer", "float", "number"}:
                assert check_number(info, defaults.get(name), None)[1] == "", (meta["type"], name)


# --- Validator -------------------------------------------------------------------------


def _single(node_type, **config):
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new(f"c5_{node_type}")
    start = workflow_map.add_node("start_node")
    node = workflow_map.add_node(node_type)
    workflow_map.connect(start, "default", node, "input")
    merged = dict(workflow_map.get_node_data(node)["config"])
    merged.update(config)
    workflow_map.update_node_config(node, merged)
    return workflow_map, node


def _number_errors(workflow_map):
    return [e for e in validate_workflow(workflow_map, FACTORY)["errors"] if e["code"] == "invalid_number"]


def test_validator_blocks_a_saved_bad_number():
    workflow_map, node = _single("sleep_node", duration="definitely not a number")
    result = validate_workflow(workflow_map, FACTORY)
    assert result["success"] is False
    assert _number_errors(workflow_map) == [{
        "node_id": node, "port": "duration", "code": "invalid_number",
        "message": "Duration (seconds): Enter a number (saved value 'definitely not a number')",
    }]


def test_validator_blocks_out_of_range_and_accepts_valid():
    workflow_map, _ = _single("sleep_node", duration=-1)
    assert [e["message"] for e in _number_errors(workflow_map)] == [
        "Duration (seconds): Must be at least 0 (saved value -1)"]
    workflow_map, _ = _single("sleep_node", duration=2)
    assert _number_errors(workflow_map) == []


def test_validator_skips_hidden_number_fields():
    workflow_map, _ = _single("text_transform_node", operation="uppercase", wrap_width=-5)
    assert _number_errors(workflow_map) == []
    workflow_map, _ = _single("text_transform_node", operation="markdown format", wrap_width=-5)
    assert len(_number_errors(workflow_map)) == 1


def test_validator_treats_a_missing_value_as_the_default():
    workflow_map, node = _single("sleep_node")
    config = dict(workflow_map.get_node_data(node)["config"])
    config.pop("duration", None)
    workflow_map.update_node_config(node, config)
    assert _number_errors(workflow_map) == []


# --- Node editor -------------------------------------------------------------------------


def _editor(node_type, body):
    from textual.app import App

    from backend.memory_bank import MemoryBank
    from frontend.screens.node_config import NodeConfigScreen

    workflow_map, node = _single(node_type)
    screen = NodeConfigScreen(FACTORY, workflow_map, node, workflow_map.get_node_data(node),
                              memory_bank=MemoryBank(EventBus()))

    class ConfigApp(App):
        CSS_PATH = CSS

        def on_mount(self):
            self.push_screen(screen)

    async def run():
        async with ConfigApp().run_test(size=(110, 40)) as pilot:
            await pilot.pause(0.1)
            await body(pilot, screen)

    asyncio.run(run())


def _field(screen, name):
    from textual.widgets import Input

    return screen.query_one(f"#field-{name}", Input)


def _error_text(screen, name):
    errors = list(screen.query(f"#field-error-{name}"))
    return str(errors[0].render()) if errors else None


def test_editor_blocks_save_keeps_text_and_shows_the_problem():
    async def body(pilot, screen):
        _field(screen, "duration").value = "abc"
        assert screen._save_result() is None
        await pilot.pause(0.05)
        assert _field(screen, "duration").value == "abc"
        assert _error_text(screen, "duration") == "Enter a number"
        assert screen.focused is _field(screen, "duration")

        _field(screen, "duration").value = "-2"
        assert screen._save_result() is None
        await pilot.pause(0.05)
        assert _error_text(screen, "duration") == "Must be at least 0"

        _field(screen, "duration").value = "2"
        result = screen._save_result()
        await pilot.pause(0.05)
        assert result is not None and result["config"]["duration"] == 2.0
        assert _error_text(screen, "duration") is None

    _editor("sleep_node", body)


def test_editor_blank_saves_the_default():
    async def body(pilot, screen):
        _field(screen, "max_visits").value = ""
        result = screen._save_result()
        assert result is not None
        # The default is not stored as an override; reopening shows 3.
        assert result["config"].get("max_visits", 3) == 3

    _editor("repeat_counter_node", body)
