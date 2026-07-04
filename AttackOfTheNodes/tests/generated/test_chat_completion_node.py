"""Focused registration/contract tests for chat_completion_node.

Execution and session behavior are covered by tests/test_chat_completion_node.py
(mocked provider client); this file checks the factory-exposed contract that
check_node.py verifies for every node type.
"""

from __future__ import annotations

import pytest

from backend.llm_provider import DEFAULT_MODEL_ID, supported_model_ids
from backend.node_factory import NodeFactory


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("chat_completion_node")]


def _metadata():
    factory = NodeFactory()
    return next(
        item
        for item in factory.get_node_types_metadata()
        if item["type"] == "chat_completion_node"
    )


def test_chat_completion_node_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("chat_completion_node")
    metadata = _metadata()
    assert metadata["display_name"] == "Chat Completion"
    assert metadata["input_ports"] == ["prompt", "document"]
    assert metadata["output_ports"] == ["default"]


def test_chat_completion_node_port_contract():
    metadata = _metadata()
    prompt = metadata["input_port_metadata"]["prompt"]
    assert prompt["data_type"] == "string"
    assert prompt["required"] is True
    document = metadata["input_port_metadata"]["document"]
    assert document["data_type"] == "string"
    assert document["required"] is False
    output = metadata["output_port_metadata"]["default"]
    assert output["data_type"] == "string"
    assert output["pass_through"] is True


def test_chat_completion_node_model_options_come_from_provider_constant():
    schema = _metadata()["config_schema"]
    assert schema["model"]["options"] == supported_model_ids()
    factory = NodeFactory()
    node = factory.create_node("chat_completion_node", "n1")
    assert node.config["model"] == DEFAULT_MODEL_ID


def test_chat_completion_node_session_and_routing_fields():
    schema = _metadata()["config_schema"]
    assert schema["session_key"]["enabled_when"] == {"use_chat_session": True}
    assert schema["continue_session_key"]["vault_type"] == "ai_session"
    assert schema["api_key_secret"]["secret"] is True
    assert "dead_drop_passthrough" in schema["transient_output"]["mutually_exclusive_with"]
    assert "transient_output" in schema["dead_drop_passthrough"]["mutually_exclusive_with"]

    factory = NodeFactory()
    node = factory.create_node("chat_completion_node", "n1")
    assert node.config["dead_drop_passthrough"] is True
    assert node.config["transient_output"] is False
    assert node.config["vault_write"] is True
