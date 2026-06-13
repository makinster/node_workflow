"""Tests for validator secret-key checks."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from backend.event_bus import EventBus
from backend.node_base import Node, NodeContext
from backend.node_factory import NodeFactory
from backend.secrets_manager import SecretsManager
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap


# ---------------------------------------------------------------------------
# Minimal node fixtures with secret schema fields
# ---------------------------------------------------------------------------


class _SecretOptionalNode(Node):
    """Node with an optional secret-ref field."""

    node_type = "_test_secret_optional"
    display_name = "Secret Optional"
    category = "test"
    input_ports = ["input"]
    output_ports = ["default"]
    config_schema = {
        "api_key": {
            "type": "string",
            "secret": True,
            "required": False,
            "label": "API Key",
        }
    }
    default_config = {"api_key": ""}

    async def execute(self, context: NodeContext) -> None:  # pragma: no cover
        context.signal_done({})


class _SecretRequiredNode(Node):
    """Node with a required secret-ref field."""

    node_type = "_test_secret_required"
    display_name = "Secret Required"
    category = "test"
    input_ports = ["input"]
    output_ports = ["default"]
    config_schema = {
        "api_key": {
            "type": "string",
            "secret": True,
            "required": True,
            "label": "API Key",
        }
    }
    default_config = {"api_key": ""}

    async def execute(self, context: NodeContext) -> None:  # pragma: no cover
        context.signal_done({})


class _PlainNode(Node):
    """Node with no secret fields."""

    node_type = "_test_plain"
    display_name = "Plain"
    category = "test"
    input_ports = ["input"]
    output_ports = ["default"]
    config_schema = {}
    default_config = {}

    async def execute(self, context: NodeContext) -> None:  # pragma: no cover
        context.signal_done({})


class _MultiSecretNode(Node):
    """Node with two independent secret-ref fields."""

    node_type = "_test_multi_secret"
    display_name = "Multi Secret"
    category = "test"
    input_ports = ["input"]
    output_ports = ["default"]
    config_schema = {
        "key_a": {"type": "string", "secret": True, "required": True, "label": "Key A"},
        "key_b": {"type": "string", "secret": True, "required": False, "label": "Key B"},
    }
    default_config = {"key_a": "", "key_b": ""}

    async def execute(self, context: NodeContext) -> None:  # pragma: no cover
        context.signal_done({})


_TEST_NODE_CLASSES = [
    _SecretOptionalNode,
    _SecretRequiredNode,
    _PlainNode,
    _MultiSecretNode,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wm(*extra_node_classes):
    bus = EventBus()
    factory = NodeFactory()
    for cls in (*_TEST_NODE_CLASSES, *extra_node_classes):
        factory._node_registry[cls.node_type] = cls
    return WorkflowMap(factory, bus), factory


def _wm_with_secret_node(node_type: str, api_key: str = ""):
    """start → secret_node (linear, no end node required for config checks)."""
    wm, factory = _make_wm()
    wm.create_new("test")
    start_id = wm.add_node("start_node")
    node_id = wm.add_node(node_type)
    wm.connect(start_id, "default", node_id, "input")
    wm.update_node_config(node_id, {"api_key": api_key})
    return wm, factory


def _sm_with_keys(tmp_path: Path, keys: list) -> SecretsManager:
    sm = SecretsManager(storage_dir=tmp_path)
    for k in keys:
        sm.set_secret(k, "dummy")
    return sm


# ---------------------------------------------------------------------------
# Required field, empty key → error
# ---------------------------------------------------------------------------


def test_required_secret_key_empty_is_error():
    wm, factory = _wm_with_secret_node("_test_secret_required", api_key="")
    result = validate_workflow(wm, factory)
    messages = [e["message"] for e in result["errors"]]
    assert any("api_key" in m and "required" in m for m in messages)
    assert result["success"] is False


def test_required_secret_key_empty_no_manager_still_errors():
    """Error fires regardless of whether a SecretsManager is wired in."""
    wm, factory = _wm_with_secret_node("_test_secret_required", api_key="")
    result = validate_workflow(wm, factory, secrets_manager=None)
    assert any("api_key" in e["message"] for e in result["errors"])


def test_optional_secret_key_empty_is_not_an_error():
    wm, factory = _wm_with_secret_node("_test_secret_optional", api_key="")
    result = validate_workflow(wm, factory)
    error_messages = [e["message"] for e in result["errors"]]
    assert not any("api_key" in m for m in error_messages)


# ---------------------------------------------------------------------------
# Key name present but not in store → warning
# ---------------------------------------------------------------------------


def test_configured_key_missing_from_store_is_warning(tmp_path):
    wm, factory = _wm_with_secret_node("_test_secret_optional", api_key="openai_key")
    sm = _sm_with_keys(tmp_path, [])
    result = validate_workflow(wm, factory, secrets_manager=sm)
    assert result["success"] is True  # warning, not error
    warn_messages = [w["message"] for w in result["warnings"]]
    assert any("openai_key" in m for m in warn_messages)


def test_configured_key_present_in_store_no_warning(tmp_path):
    wm, factory = _wm_with_secret_node("_test_secret_optional", api_key="openai_key")
    sm = _sm_with_keys(tmp_path, ["openai_key"])
    result = validate_workflow(wm, factory, secrets_manager=sm)
    warn_messages = [w["message"] for w in result["warnings"]]
    assert not any("openai_key" in m for m in warn_messages)


def test_no_manager_suppresses_missing_key_warning():
    """Without a SecretsManager, a missing-key warning is not emitted."""
    wm, factory = _wm_with_secret_node("_test_secret_optional", api_key="openai_key")
    result = validate_workflow(wm, factory, secrets_manager=None)
    warn_messages = [w["message"] for w in result["warnings"]]
    assert not any("openai_key" in m for m in warn_messages)


def test_required_field_configured_and_key_present_is_clean(tmp_path):
    wm, factory = _wm_with_secret_node("_test_secret_required", api_key="my_key")
    sm = _sm_with_keys(tmp_path, ["my_key"])
    result = validate_workflow(wm, factory, secrets_manager=sm)
    assert result["success"] is True
    assert not result["errors"]
    secret_warns = [w for w in result["warnings"] if "my_key" in w["message"]]
    assert not secret_warns


def test_required_field_configured_but_key_missing_from_store_is_warning(tmp_path):
    """Key name in config but absent from store → warning, not error."""
    wm, factory = _wm_with_secret_node("_test_secret_required", api_key="missing_key")
    sm = _sm_with_keys(tmp_path, [])
    result = validate_workflow(wm, factory, secrets_manager=sm)
    error_msgs = [e["message"] for e in result["errors"]]
    assert not any("missing_key" in m for m in error_msgs)
    warn_msgs = [w["message"] for w in result["warnings"]]
    assert any("missing_key" in m for m in warn_msgs)


# ---------------------------------------------------------------------------
# Non-secret nodes are unaffected
# ---------------------------------------------------------------------------


def test_plain_node_not_checked_for_secrets():
    wm, factory = _make_wm()
    wm.create_new("test")
    start_id = wm.add_node("start_node")
    node_id = wm.add_node("_test_plain")
    wm.connect(start_id, "default", node_id, "input")
    result = validate_workflow(wm, factory)
    assert result["success"] is True
    assert not result["errors"]


# ---------------------------------------------------------------------------
# Multiple secret fields checked independently
# ---------------------------------------------------------------------------


def test_multiple_secret_fields_each_checked_independently(tmp_path):
    wm, factory = _make_wm()
    wm.create_new("test")
    start_id = wm.add_node("start_node")
    node_id = wm.add_node("_test_multi_secret")
    wm.connect(start_id, "default", node_id, "input")
    wm.update_node_config(node_id, {"key_a": "", "key_b": "configured_b"})

    sm = _sm_with_keys(tmp_path, [])  # both absent from store

    result = validate_workflow(wm, factory, secrets_manager=sm)
    # key_a empty + required → error
    error_msgs = [e["message"] for e in result["errors"]]
    assert any("key_a" in m for m in error_msgs)
    # key_b configured but absent → warning
    warn_msgs = [w["message"] for w in result["warnings"]]
    assert any("configured_b" in m for m in warn_msgs)


def test_multiple_secret_fields_all_present_no_complaints(tmp_path):
    wm, factory = _make_wm()
    wm.create_new("test")
    start_id = wm.add_node("start_node")
    node_id = wm.add_node("_test_multi_secret")
    wm.connect(start_id, "default", node_id, "input")
    wm.update_node_config(node_id, {"key_a": "stored_a", "key_b": "stored_b"})

    sm = _sm_with_keys(tmp_path, ["stored_a", "stored_b"])

    result = validate_workflow(wm, factory, secrets_manager=sm)
    assert result["success"] is True
    secret_warns = [w for w in result["warnings"] if "stored_" in w["message"]]
    assert not secret_warns
