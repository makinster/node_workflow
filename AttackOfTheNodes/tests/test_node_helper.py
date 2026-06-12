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
primary_family: Complex
tags: ["Utility"]
icon_name: repeat
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
    assert "primary_family: ClassVar[str] = 'Complex'" in node_text
    assert "tags: ClassVar[List[str]] = ['Utility']" in node_text
    assert "icon_name: ClassVar[str] = 'repeat'" in node_text
    # color_hint defaults from the family map when not declared.
    assert "color_hint: ClassVar[str] = 'violet'" in node_text
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


def _standard_model_spec() -> dict:
    return {
        "node_type": "helper_standard_node",
        "class_name": "HelperStandardNode",
        "category": "debug",
        "primary_family": "Inputs",
        "tags": ["File I/O"],
        "display_name": "Helper Standard",
        "description": "Standard input/output model example",
        "input_ports": ["input"],
        "output_ports": ["default"],
        "input_sources": {
            "file_path": {
                "label": "File path",
                "sources": ["upstream", "vault", "configured"],
                "default": "configured",
                "parameter": {
                    "type": "string",
                    "label": "File path",
                    "placeholder": "/path/to/file",
                },
            },
        },
        "output_routing": {
            "default": "transient",
            "vault": {"mode": "optional", "label": "Save error to Vault"},
        },
        "execution_template": "transform_stub",
    }


def test_node_helper_expands_input_sources_and_output_routing(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)

    paths = generate_from_spec(_standard_model_spec(), project_root=project_root)
    node_text = paths.node_file.read_text(encoding="utf-8")

    # Source selector with mapped option labels and Source tab placement.
    assert "'file_path_source'" in node_text
    assert "'Upstream payload', 'Vault', 'Configured'" in node_text
    assert "'file_path_source': 'Configured'" in node_text  # default_config
    # Vault key gated on the Vault source.
    assert "'file_path_vault_key'" in node_text
    assert "'enabled_when': {'file_path_source': 'Vault'}" in node_text
    # Configured parameter gated on the Configured source, in Parameters tab.
    assert "'enabled_when': {'file_path_source': 'Configured'}" in node_text
    # Output routing pair is mutually exclusive both ways.
    assert "'transient_output'" in node_text
    assert "'mutually_exclusive_with': ['dead_drop_passthrough']" in node_text
    assert "'mutually_exclusive_with': ['transient_output']" in node_text
    # Optional vault write defaults off with a gated key field.
    assert "'vault_write': False" in node_text
    assert "'enabled_when': {'vault_write': True}" in node_text
    # Standard-model specs get a generated config-UI smoke test.
    assert paths.ui_test_file is not None
    ui_test_text = paths.ui_test_file.read_text(encoding="utf-8")
    assert "run_ui_check" in ui_test_text
    assert 'run_ui_check("helper_standard_node")' in ui_test_text


def test_node_helper_required_unless_transient_vault_mode(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)
    spec = _standard_model_spec()
    spec["output_routing"]["vault"] = {"mode": "required_unless_transient"}
    spec["output_routing"]["default"] = "dead_drop"

    paths = generate_from_spec(spec, project_root=project_root)
    node_text = paths.node_file.read_text(encoding="utf-8")

    # Vault write locked on until transient output is checked.
    assert "'vault_write': True" in node_text
    assert "'enabled_when': {'transient_output': True}" in node_text
    assert "'dead_drop_passthrough': True" in node_text
    assert "'transient_output': False" in node_text


def test_node_helper_validates_standard_sections(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)

    spec = _standard_model_spec()
    spec["input_sources"]["file_path"]["sources"] = ["configured"]
    with pytest.raises(ValueError, match="at least two sources"):
        generate_from_spec(spec, project_root=project_root)

    spec = _standard_model_spec()
    spec["input_sources"]["file_path"]["sources"] = ["upstream", "teleport"]
    with pytest.raises(ValueError, match="unknown sources"):
        generate_from_spec(spec, project_root=project_root)

    spec = _standard_model_spec()
    del spec["input_sources"]["file_path"]["parameter"]
    with pytest.raises(ValueError, match="must declare a parameter"):
        generate_from_spec(spec, project_root=project_root)

    spec = _standard_model_spec()
    spec["output_routing"]["vault"] = {"mode": "sometimes"}
    with pytest.raises(ValueError, match="vault.mode"):
        generate_from_spec(spec, project_root=project_root)

    # Standard fields must not collide with hand-written config fields.
    spec = _standard_model_spec()
    spec["config_tabs"] = {
        "Payloads": {"transient_output": {"type": "boolean", "label": "Clash"}}
    }
    with pytest.raises(ValueError, match="collides"):
        generate_from_spec(spec, project_root=project_root)


def test_node_helper_requires_phase_17_identity(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)

    spec = _standard_model_spec()
    del spec["primary_family"]
    with pytest.raises(ValueError, match="primary_family is required"):
        generate_from_spec(spec, project_root=project_root)

    spec = _standard_model_spec()
    spec["primary_family"] = "Gadgets"
    with pytest.raises(ValueError, match="primary_family must be one of"):
        generate_from_spec(spec, project_root=project_root)

    spec = _standard_model_spec()
    spec["tags"] = ["File I/O", "Time Travel"]
    with pytest.raises(ValueError, match="unknown entries"):
        generate_from_spec(spec, project_root=project_root)


def test_node_helper_validates_rule_keys(tmp_path: Path):
    project_root = _project_skeleton(tmp_path)

    base = {
        "node_type": "helper_rules_node",
        "class_name": "HelperRulesNode",
        "category": "debug",
        "primary_family": "Complex",
        "display_name": "Helper Rules",
        "description": "Rule validation example",
        "input_ports": ["input"],
        "output_ports": ["default"],
        "execution_template": "pass_through",
    }

    spec = dict(base)
    spec["config_tabs"] = {
        "Parameters": {
            "gated": {
                "type": "string",
                "label": "Gated",
                "enabled_when": {"missing_field": "On"},
            }
        }
    }
    with pytest.raises(ValueError, match="references unknown field"):
        generate_from_spec(spec, project_root=project_root)

    spec = dict(base)
    spec["config_tabs"] = {
        "Payloads": {
            "not_boolean": {
                "type": "string",
                "label": "Not boolean",
                "mutually_exclusive_with": ["other"],
            },
            "other": {"type": "boolean", "label": "Other"},
        }
    }
    with pytest.raises(ValueError, match="requires a boolean field"):
        generate_from_spec(spec, project_root=project_root)
