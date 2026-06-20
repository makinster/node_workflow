"""Tests for the per-port I/O contract fields (handoff Track A step 2, §4/§6).

Covers the additive `data_type` / `required` port-metadata fields, their
forward-compatible defaults exposed through NodeFactory, canonicalization of the
deprecated `boolean` spelling, and the class-definition warning for unknown
port types.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_node_contract.py -v
"""

import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.data_types import UnknownDataTypeWarning
from backend.node_base import Node, NodeContext
from backend.node_factory import NodeFactory


def _make_factory():
    return NodeFactory()


def test_factory_fills_default_contract_on_every_port():
    factory = _make_factory()
    metadata = {m["type"]: m for m in factory.get_node_types_metadata()}

    # Every declared port on every node gets the §6 defaults filled in.
    for meta in metadata.values():
        for direction in ("input_port_metadata", "output_port_metadata"):
            for port, info in meta[direction].items():
                assert info["data_type"] == "any" or info["data_type"], (
                    f"{meta['type']} {direction} {port} missing data_type"
                )
                assert "data_type" in info
                assert "required" in info
                assert isinstance(info["required"], bool)

    print("test_factory_fills_default_contract_on_every_port PASSED")


def test_absent_fields_default_to_any_and_optional():
    factory = _make_factory()
    # echo_node declares no port metadata, so every port should default.
    meta = next(
        m for m in factory.get_node_types_metadata() if m["type"] == "echo_node"
    )
    for direction in ("input_port_metadata", "output_port_metadata"):
        for info in meta[direction].values():
            assert info["data_type"] == "any"
            assert info["required"] is False

    print("test_absent_fields_default_to_any_and_optional PASSED")


def test_port_metadata_canonicalizes_and_coerces():
    factory = _make_factory()
    # Drive the helper directly: declared boolean -> bool; required passes through.
    result = factory._port_metadata(
        ["result", "untyped"],
        {
            "result": {"data_type": "boolean", "required": True, "description": "ok"},
            # 'untyped' intentionally omits both fields.
        },
        "output",
    )
    assert result["result"]["data_type"] == "bool"
    assert result["result"]["required"] is True
    assert result["result"]["description"] == "ok"
    assert result["untyped"]["data_type"] == "any"
    assert result["untyped"]["required"] is False

    print("test_port_metadata_canonicalizes_and_coerces PASSED")


def test_declared_contract_survives_through_factory_exposure():
    factory = _make_factory()
    # example_file_instance_node is the unified-spec reference node: its
    # outputs: block declares name + data_type + required + to, and the factory
    # must surface all of it (not just fill defaults).
    meta = next(
        (
            m
            for m in factory.get_node_types_metadata()
            if m["type"] == "example_file_instance_node"
        ),
        None,
    )
    if meta is None:
        pytest.skip("example_file_instance_node not registered in this build")
    out = meta["output_port_metadata"]["default"]
    assert out["name"] == "Open Result"
    assert out["data_type"] == "bool"  # declared in the outputs: block
    assert out["required"] is True
    assert out["to"] == ["downstream", "vault"]
    assert out["pass_through"] is True
    # The inputs: block declares the file_path port as a file reference type.
    inp = meta["input_port_metadata"]["file_path"]
    assert inp["data_type"] == "file"
    assert inp["sources"] == ["upstream", "vault", "configured"]

    print("test_declared_contract_survives_through_factory_exposure PASSED")


def test_unknown_port_data_type_warns_at_class_definition():
    with pytest.warns(UnknownDataTypeWarning, match="bogus_type"):

        class _BadPortNode(Node):
            node_type = "test_bad_port_node"
            display_name = "Bad Port"
            output_ports = ["default"]
            output_port_metadata = {"default": {"data_type": "bogus_type"}}

            async def execute(self, context: NodeContext) -> None:  # pragma: no cover
                pass

    print("test_unknown_port_data_type_warns_at_class_definition PASSED")


def test_canonical_port_data_type_does_not_warn():
    with warnings.catch_warnings():
        warnings.simplefilter("error", UnknownDataTypeWarning)

        class _GoodPortNode(Node):
            node_type = "test_good_port_node"
            display_name = "Good Port"
            input_ports = ["prompt"]
            output_ports = ["default"]
            input_port_metadata = {"prompt": {"data_type": "string", "required": True}}
            # deprecated alias resolves silently
            output_port_metadata = {"default": {"data_type": "boolean"}}

            async def execute(self, context: NodeContext) -> None:  # pragma: no cover
                pass

    print("test_canonical_port_data_type_does_not_warn PASSED")
