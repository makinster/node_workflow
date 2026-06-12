"""Tests for dynamic-form rule keys: enabled_when, visible_when, mutual exclusion."""

from __future__ import annotations

import asyncio

from frontend.widgets.form_generator import (
    evaluate_field_condition,
    mutual_exclusion_targets,
    schema_has_field_rules,
)


# ---------------------------------------------------------------------------
# Pure rule helpers
# ---------------------------------------------------------------------------

def test_evaluate_field_condition_matches_scalar_and_list():
    values = {"file_source": "Configured", "vault_write": True}
    assert evaluate_field_condition({"file_source": "Configured"}, values)
    assert not evaluate_field_condition({"file_source": "Vault"}, values)
    assert evaluate_field_condition({"file_source": ["Vault", "Configured"]}, values)
    assert evaluate_field_condition(
        {"file_source": "Configured", "vault_write": True}, values
    )
    assert not evaluate_field_condition(
        {"file_source": "Configured", "vault_write": False}, values
    )
    assert evaluate_field_condition({}, values)
    assert evaluate_field_condition(None, values)


def test_schema_has_field_rules_detects_rule_keys():
    assert not schema_has_field_rules({"plain": {"type": "string"}})
    assert schema_has_field_rules(
        {"gated": {"type": "string", "enabled_when": {"mode": "Configured"}}}
    )
    assert schema_has_field_rules(
        {"hidden": {"type": "string", "visible_when": {"mode": "On"}}}
    )
    assert schema_has_field_rules(
        {"a": {"type": "boolean", "mutually_exclusive_with": ["b"]}}
    )


def test_mutual_exclusion_targets_are_symmetric():
    schema = {
        "transient_output": {
            "type": "boolean",
            "mutually_exclusive_with": ["dead_drop_passthrough"],
        },
        "dead_drop_passthrough": {"type": "boolean"},
        "vault_write": {"type": "boolean"},
    }
    assert mutual_exclusion_targets("transient_output", schema) == [
        "dead_drop_passthrough"
    ]
    # Declared on only one side, but resolved from both directions.
    assert mutual_exclusion_targets("dead_drop_passthrough", schema) == [
        "transient_output"
    ]
    assert mutual_exclusion_targets("vault_write", schema) == []


# ---------------------------------------------------------------------------
# Mounted NodeConfigScreen integration
# ---------------------------------------------------------------------------

RULE_SCHEMA = {
    "file_source": {
        "type": "select",
        "label": "File path source",
        "options": ["Upstream payload", "Vault", "Configured"],
        "tab": "Source",
    },
    "file_vault_key": {
        "type": "string",
        "label": "File path Vault key",
        "tab": "Source",
        "enabled_when": {"file_source": "Vault"},
    },
    "file_path": {
        "type": "string",
        "label": "File path",
        "tab": "Parameters",
        "enabled_when": {"file_source": "Configured"},
    },
    "transient_output": {
        "type": "boolean",
        "label": "Send result to next node",
        "tab": "Payloads",
        "mutually_exclusive_with": ["dead_drop_passthrough"],
    },
    "dead_drop_passthrough": {
        "type": "boolean",
        "label": "Forward incoming payload unchanged",
        "tab": "Payloads",
    },
    "vault_write_key": {
        "type": "string",
        "label": "Vault key",
        "tab": "Payloads",
        "visible_when": {"transient_output": True},
    },
}


def _make_rule_screen():
    from backend.event_bus import EventBus
    from backend.node_factory import NodeFactory
    from backend.workflow_map import WorkflowMap
    from frontend.screens.node_config import NodeConfigScreen

    factory = NodeFactory()
    wm = WorkflowMap(factory, EventBus())
    wm.create_new("form_rules_test")
    node_id = wm.add_node("echo_node")
    wm.update_node_config(
        node_id,
        {
            "file_source": "Configured",
            "file_vault_key": "",
            "file_path": "",
            "transient_output": False,
            "dead_drop_passthrough": True,
            "vault_write_key": "",
        },
    )
    node_data = wm.get_node_data(node_id)

    class RuleConfigScreen(NodeConfigScreen):
        def _metadata_for_type(self, node_type: str):
            metadata = super()._metadata_for_type(node_type)
            if metadata is None:
                return None
            metadata = dict(metadata)
            metadata["config_schema"] = RULE_SCHEMA
            return metadata

    return RuleConfigScreen(factory, wm, node_id, node_data)


def test_node_config_applies_rules_on_mount_and_change():
    asyncio.run(_test_node_config_applies_rules_on_mount_and_change())


async def _test_node_config_applies_rules_on_mount_and_change():
    from textual.app import App, ComposeResult
    from textual.widgets import Checkbox, Select

    from frontend.widgets.command_input import CommandInput

    screen = _make_rule_screen()

    class RuleApp(App):
        def compose(self) -> ComposeResult:
            yield screen

    app = RuleApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        # Initial state: source is Configured, so the vault key is disabled
        # and the Parameters path field is enabled.
        assert app.query_one("#field-file_vault_key", CommandInput).disabled
        assert not app.query_one("#field-file_path", CommandInput).disabled
        # transient_output is False, so the visible_when vault key is hidden.
        assert not app.query_one("#field-vault_write_key", CommandInput).display
        assert not app.query_one("#field-label-vault_write_key").display

        # Switch source to Vault: vault key enables, path field greys out.
        app.query_one("#field-file_source", Select).value = "Vault"
        await pilot.pause()
        assert not app.query_one("#field-file_vault_key", CommandInput).disabled
        assert app.query_one("#field-file_path", CommandInput).disabled

        # Check transient output: dead-drop unchecks (mutual exclusion) and
        # the visible_when vault key field appears.
        app.query_one("#field-transient_output", Checkbox).value = True
        await pilot.pause()
        assert not app.query_one("#field-dead_drop_passthrough", Checkbox).value
        assert app.query_one("#field-vault_write_key", CommandInput).display
        assert app.query_one("#field-label-vault_write_key").display

        # Re-check dead-drop: transient unchecks from the other direction.
        app.query_one("#field-dead_drop_passthrough", Checkbox).value = True
        await pilot.pause()
        assert not app.query_one("#field-transient_output", Checkbox).value
    print("test_node_config_applies_rules_on_mount_and_change PASSED")
