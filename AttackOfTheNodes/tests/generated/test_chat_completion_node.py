"""Focused registration/contract tests for chat_completion_node.

Execution and session behavior are covered by tests/test_chat_completion_node.py
(mocked provider client); this file checks the factory-exposed contract that
check_node.py verifies for every node type.
"""

from __future__ import annotations

import pytest

from backend.llm_provider import DEFAULT_MODEL_ID, supported_model_ids
from backend.nodes.chat_completion_node import CONTEXT_INPUT_PORTS
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
    assert metadata["input_ports"] == ["prompt", *CONTEXT_INPUT_PORTS, "document"]
    assert metadata["output_ports"] == ["default"]


def test_chat_completion_node_port_contract():
    metadata = _metadata()
    prompt = metadata["input_port_metadata"]["prompt"]
    assert prompt["data_type"] == "string"
    assert prompt["required"] is True
    document = metadata["input_port_metadata"]["document"]
    assert document["data_type"] == "string"
    assert document["required"] is False
    context_1 = metadata["input_port_metadata"]["context_1"]
    assert context_1["data_type"] == "string"
    assert context_1["required"] is False
    assert context_1["sources"] == ["upstream", "vault", "configured"]
    output = metadata["output_port_metadata"]["default"]
    assert output["data_type"] == "string"
    assert output["pass_through"] is True


def test_chat_completion_node_model_options_come_from_provider_constant():
    schema = _metadata()["config_schema"]
    assert schema["model"]["options"] == supported_model_ids()
    factory = NodeFactory()
    node = factory.create_node("chat_completion_node", "n1")
    assert node.config["model"] == DEFAULT_MODEL_ID
    assert node.config["context_input_count"] == "0"
    assert node.config["context_8_source"] == "Configured"


def test_chat_completion_node_session_and_routing_fields():
    schema = _metadata()["config_schema"]
    # Session persistence lives in the Payloads tab; the key hides until
    # enabled. Continuation is a prompt-source mode on the Source tab.
    # Hidden until enabled, and suppressed in Continue mode (session reused).
    assert schema["session_key"]["visible_when"] == {
        "use_chat_session": True,
        "prompt_source": ["Upstream payload", "Vault", "Configured"],
    }
    assert schema["session_key"]["tab"] == "Payloads"
    assert schema["use_chat_session"]["tab"] == "Payloads"
    assert "Continue AI session" in schema["prompt_source"]["options"]
    assert schema["continue_session_key"]["tab"] == "Source"
    assert schema["continue_session_key"]["vault_type"] == "ai_session"
    assert schema["continue_session_key"]["visible_when"] == {
        "prompt_source": "Continue AI session"
    }
    assert schema["prompt_vault_key"]["visible_when"] == {"prompt_source": "Vault"}
    assert schema["prompt_vault_key"]["vault_type"] == "string"
    assert schema["prompt"]["visible_when"] == {"prompt_source": "Configured"}
    assert schema["context_input_count"]["options"] == [
        str(index) for index in range(len(CONTEXT_INPUT_PORTS) + 1)
    ]
    assert schema["context_1_source"]["visible_when"] == {
        "context_input_count": [str(index) for index in range(1, 9)]
    }
    assert schema["context_2_vault_key"]["visible_when"] == {
        "context_2_source": "Vault",
        "context_input_count": [str(index) for index in range(2, 9)],
    }
    # Continue mode makes the document required and retitles its section, but
    # keeps the source selectable (no force-to-Configured lock).
    assert schema["document_source"]["required_when"] == {
        "prompt_source": "Continue AI session",
        "context_input_count": "0",
    }
    assert "force_value_when" not in schema["document_source"]
    assert schema["document_source"]["section_when"] == {
        "Required Inputs": {
            "prompt_source": "Continue AI session",
            "context_input_count": "0",
        }
    }
    assert schema["document"]["visible_when"] == {"document_source": "Configured"}
    assert schema["api_key_secret"]["secret"] is True
    # Routing/vault controls are composed from output_port_metadata, not schema
    # fields; the output port declares downstream + vault routing.
    assert schema.get("transient_output") is None
    assert schema.get("vault_write") is None
    default_out = _metadata()["output_port_metadata"]["default"]
    assert "downstream" in default_out["to"]
    assert "vault" in default_out["to"]

    factory = NodeFactory()
    node = factory.create_node("chat_completion_node", "n1")
    # Result is the designated downstream payload (dead-drop off), also
    # duplicated to the vault by default.
    assert node.config["dead_drop_passthrough"] is False
    assert node.config["transient_output"] is True
    assert node.config["vault_write"] is True
