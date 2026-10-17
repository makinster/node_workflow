"""C6: Random Number's ignored Payload field is gone; Chat Completion validates fresh.

- The helper generator's ``producer`` template added a "Payload" (``value``)
  field to every producer; Random Number computes its output and ignored it.
  Specs can now say ``payload_field: false``; Random Number does.
- Owner, 2026-10-17: Chat Completion's Vault output is off by default (it was
  on with an empty key, so a freshly added node failed Validate).

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_c6_payload_and_chat_defaults.py -v
"""

import asyncio
from types import SimpleNamespace

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


def _meta(node_type):
    return next(m for m in FACTORY.get_node_types_metadata() if m["type"] == node_type)


# --- Random Number ----------------------------------------------------------------------


def test_random_number_has_no_payload_control():
    meta = _meta("random_number_node")
    assert "value" not in meta["config_schema"]
    assert "value" not in meta["default_config"]
    # The rest of its contract is unchanged.
    assert meta["output_port_metadata"]["default"]["data_type"] == "number"
    assert set(meta["config_schema"]) == {"mode", "min_value", "max_value", "seed"}


def test_saved_value_key_is_kept_and_ignored():
    """A workflow saved before C6 keeps its stored `value`; nothing reads it."""
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("c6_saved")
    node_id = workflow_map.add_node("random_number_node")
    data = workflow_map.get_workflow_data_for_save()
    data["nodes"][node_id]["config"]["value"] = "old payload"
    workflow_map.load_data(data)
    assert workflow_map.get_node_data(node_id)["config"]["value"] == "old payload"
    result = validate_workflow(workflow_map, FACTORY)
    assert [i for i in result["errors"] + result["warnings"]
            if i["node_id"] == node_id and i["code"] != "unreachable"] == []

    node = FACTORY.create_node("random_number_node", node_id, workflow_map.get_node_data(node_id)["config"])
    node.config.update(seed="7", min_value=1, max_value=1)
    done = []
    context = SimpleNamespace(inputs={}, memory_bank=MemoryBank(EventBus()), signal_done=done.append,
                              signal_error=done.append)
    asyncio.run(node.execute(context))
    assert done[0]["data"]["default"] == 1


def test_node_editor_keeps_a_saved_value_key():
    from textual.app import App

    from frontend.screens.node_config import NodeConfigScreen

    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("c6_editor")
    node_id = workflow_map.add_node("random_number_node")
    config = dict(workflow_map.get_node_data(node_id)["config"])
    config["value"] = "old payload"
    workflow_map.update_node_config(node_id, config)
    screen = NodeConfigScreen(FACTORY, workflow_map, node_id, workflow_map.get_node_data(node_id),
                              memory_bank=MemoryBank(EventBus()))
    seen = {}

    class ConfigApp(App):
        def on_mount(self):
            self.push_screen(screen)

    async def run():
        async with ConfigApp().run_test(size=(110, 40)) as pilot:
            await pilot.pause(0.1)
            assert not list(screen.query("#field-value"))
            seen["result"] = screen._save_result()

    asyncio.run(run())
    assert seen["result"]["config"]["value"] == "old payload"


def test_generator_payload_field_option():
    from aotn_node_helper.generator import normalize_spec

    base = {
        "node_type": "demo_producer_node", "category": "data", "primary_family": "Utility",
        "display_name": "Demo Producer", "description": "Demo", "input_ports": ["input"],
        "output_ports": ["default"], "execution_template": "producer",
        "group": "Data Transform", "selector_section": "Transform",
    }
    assert "value" in normalize_spec(dict(base))["default_config"]
    without = normalize_spec({**base, "payload_field": False})
    assert "value" not in without["default_config"]
    assert "value" not in without["config_schema"]


# --- Chat Completion --------------------------------------------------------------------


def test_fresh_chat_completion_has_vault_output_off():
    assert _meta("chat_completion_node")["default_config"]["vault_write"] is False


def test_fresh_chat_completion_only_needs_its_secret():
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new("c6_chat")
    start = workflow_map.add_node("start_node")
    chat = workflow_map.add_node("chat_completion_node")
    workflow_map.connect(start, "default", chat, "prompt")
    codes = [e["code"] for e in validate_workflow(workflow_map, FACTORY)["errors"] if e["node_id"] == chat]
    assert codes == ["secret_not_configured"]


def test_chat_vault_output_still_works_when_turned_on():
    from backend.vault_declarations import typed_vault_writes

    config = dict(_meta("chat_completion_node")["default_config"])
    config.update(vault_write=True, vault_write_key="reply")
    assert typed_vault_writes("chat_completion_node", config,
                              _meta("chat_completion_node")) == {"reply": "string"}
