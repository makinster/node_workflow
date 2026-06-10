"""Focused tests for the standalone node helper generator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE_ROOT))

from aotn_node_helper.generator import generate_from_spec, load_spec  # noqa: E402


def _project_skeleton(tmp_path: Path) -> Path:
    project_root = tmp_path / "AttackOfTheNodes"
    nodes_root = project_root / "backend" / "nodes"
    nodes_root.mkdir(parents=True)
    (project_root / "tests").mkdir()
    (nodes_root / "__init__.py").write_text(
        '"""Registered node classes."""\n\nALL_NODE_CLASSES = [\n]\n',
        encoding="utf-8",
    )
    return project_root


def _spec_file(tmp_path: Path) -> Path:
    spec_path = tmp_path / "helper_passthrough_node.yaml"
    spec_path.write_text(
        """
node_type: helper_passthrough_node
class_name: HelperPassthroughNode
category: debug
display_name: Helper Passthrough
default_alias: Helper Passthrough
description: Generated helper pass-through node
input_ports: ["input"]
output_ports: ["default"]
output_port_metadata:
  default:
    name: Helper Payload
    description: Payload forwarded by helper test
config_tabs:
  Source:
    source_note:
      type: string
      label: Source note
      default: Helper source
      required: false
  Parameters:
    label:
      type: string
      label: Label
      default: Helper
      required: false
  Payloads:
    payload_note:
      type: string
      label: Payload note
      default: Helper payload
      required: false
ui_hints:
  pass_through: Forwards the previous payload unchanged.
execution_template: pass_through
""".strip(),
        encoding="utf-8",
    )
    return spec_path


def test_node_helper_generates_node_registration_and_focused_test(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)
    spec = load_spec(_spec_file(tmp_path))

    paths = generate_from_spec(spec, project_root=project_root)

    node_text = paths.node_file.read_text(encoding="utf-8")
    registration_text = paths.registration_file.read_text(encoding="utf-8")
    test_text = paths.test_file.read_text(encoding="utf-8")

    assert paths.node_file == project_root / "backend/nodes/debug/helper_passthrough_node.py"
    assert "class HelperPassthroughNode(Node):" in node_text
    assert "node_type: ClassVar[str] = 'helper_passthrough_node'" in node_text
    assert "'name': 'Helper Payload'" in node_text
    assert "'pass_through': 'Forwards the previous payload unchanged.'" in node_text
    assert "'tab': 'Source'" in node_text
    assert "'tab': 'Payloads'" in node_text
    assert "context.signal_done" in node_text

    assert "from .debug.helper_passthrough_node import HelperPassthroughNode" in registration_text
    assert "    HelperPassthroughNode," in registration_text

    assert "pytest.mark.generated_node" in test_text
    assert 'pytest.mark.node_type("helper_passthrough_node")' in test_text
    assert "test_helper_passthrough_node_registration_and_metadata" in test_text


def test_node_helper_refuses_to_overwrite_without_force(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)
    spec = load_spec(_spec_file(tmp_path))

    generate_from_spec(spec, project_root=project_root)

    with pytest.raises(FileExistsError):
        generate_from_spec(spec, project_root=project_root)

    paths = generate_from_spec(spec, project_root=project_root, force=True)
    assert paths.node_file.exists()


def test_node_helper_rejects_invalid_spec_before_writing(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)
    bad_spec = {
        "node_type": "bad_node",
        "category": "not_a_category",
        "display_name": "Bad Node",
    }

    with pytest.raises(ValueError):
        generate_from_spec(bad_spec, project_root=project_root)

    assert not (project_root / "backend/nodes/not_a_category").exists()
