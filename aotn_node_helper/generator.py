"""Generate AttackOfTheNodes node files from a small node spec."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROJECT_ROOT = ROOT / "AttackOfTheNodes"
VALID_FIELD_TYPES = {
    "string",
    "integer",
    "float",
    "number",
    "boolean",
    "select",
    "multiselect",
    "multiline",
    "code",
}
VALID_TEMPLATES = {
    "pass_through",
    "producer",
    "transform_stub",
    "output_sink",
    "async_wait",
    "error_stub",
}
VALID_CATEGORIES = {"flow", "io", "data", "ai", "debug", "utility"}


@dataclass(frozen=True)
class GeneratedPaths:
    node_file: Path
    registration_file: Path
    test_file: Path
    ui_todo_file: Path | None


def load_spec(path: Path) -> dict[str, Any]:
    """Load a JSON or simple YAML node spec."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = _load_yaml(text)
    if not isinstance(data, dict):
        raise ValueError("Spec must be an object at the top level")
    return data


def generate_from_spec(
    spec: dict[str, Any],
    *,
    project_root: Path = DEFAULT_PROJECT_ROOT,
    force: bool = False,
) -> GeneratedPaths:
    """Generate node source, registration, tests, and optional UI notes."""
    normalized = normalize_spec(spec)
    nodes_root = project_root / "backend" / "nodes"
    package_dir = nodes_root / normalized["category"]
    node_file = package_dir / f"{normalized['module_name']}.py"
    registration_file = nodes_root / "__init__.py"
    test_dir = project_root / "tests" / "generated"
    test_file = test_dir / f"test_{normalized['node_type']}.py"
    ui_todo_file = (
        ROOT / "aotn_node_helper" / "generated_notes" / f"{normalized['node_type']}_ui.md"
        if normalized.get("structural_ui")
        else None
    )

    if node_file.exists() and not force:
        raise FileExistsError(f"Node file already exists: {node_file}")

    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "__init__.py").touch()
    test_dir.mkdir(parents=True, exist_ok=True)

    node_file.write_text(render_node_file(normalized), encoding="utf-8")
    update_registration(registration_file, normalized)
    test_file.write_text(render_test_file(normalized), encoding="utf-8")
    if ui_todo_file is not None:
        ui_todo_file.parent.mkdir(parents=True, exist_ok=True)
        ui_todo_file.write_text(render_ui_todo(normalized), encoding="utf-8")

    return GeneratedPaths(node_file, registration_file, test_file, ui_todo_file)


def normalize_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a raw spec dict."""
    node_type = _required_identifier(spec, "node_type")
    category = str(spec.get("category") or "debug").strip().lower()
    if category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {sorted(VALID_CATEGORIES)}")
    template = str(spec.get("execution_template") or "pass_through").strip()
    if template not in VALID_TEMPLATES:
        raise ValueError(f"execution_template must be one of {sorted(VALID_TEMPLATES)}")

    input_ports = _string_list(spec.get("input_ports", ["input"]), "input_ports")
    output_ports = _string_list(spec.get("output_ports", ["default"]), "output_ports")
    config_fields = _config_fields_from_spec(spec)
    if not isinstance(config_fields, dict):
        raise ValueError("config_fields/config must be an object")

    config_schema: dict[str, dict[str, Any]] = {}
    default_config: dict[str, Any] = {}
    for field_name, raw_field in config_fields.items():
        if not isinstance(raw_field, dict):
            raise ValueError(f"Config field {field_name!r} must be an object")
        field_type = str(raw_field.get("type", "string")).lower()
        if field_type not in VALID_FIELD_TYPES:
            raise ValueError(f"Config field {field_name!r} has invalid type {field_type!r}")
        schema = {
            key: value
            for key, value in raw_field.items()
            if key != "default" and value is not None
        }
        schema.setdefault("type", field_type)
        config_schema[str(field_name)] = schema
        if "default" in raw_field:
            default_config[str(field_name)] = raw_field["default"]

    if template == "producer" and "value" not in default_config:
        default_config["value"] = spec.get("default_payload", "")
        config_schema.setdefault(
            "value",
            {"type": "string", "label": "Payload", "required": False},
        )
    if template == "async_wait" and "duration" not in default_config:
        default_config["duration"] = 0.0
        config_schema.setdefault(
            "duration",
            {
                "type": "float",
                "label": "Duration seconds",
                "required": False,
                "min": 0.0,
            },
        )

    class_name = str(spec.get("class_name") or _pascal_case(node_type)).strip()
    if not re.fullmatch(r"[A-Z][A-Za-z0-9]*", class_name):
        raise ValueError("class_name must be a valid PascalCase Python class name")

    module_name = str(spec.get("module_name") or node_type).strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", module_name):
        raise ValueError("module_name must be a valid snake_case Python module name")

    return {
        "node_type": node_type,
        "class_name": class_name,
        "module_name": module_name,
        "category": category,
        "category_constant": category.upper(),
        "display_name": str(spec.get("display_name") or _title_case(node_type)),
        "default_alias": str(spec.get("default_alias") or spec.get("display_name") or _title_case(node_type)),
        "description": str(spec.get("description") or ""),
        "input_ports": input_ports,
        "output_ports": output_ports,
        "input_port_metadata": _port_metadata(spec.get("input_port_metadata", {}), input_ports),
        "output_port_metadata": _port_metadata(spec.get("output_port_metadata", {}), output_ports),
        "default_config": default_config,
        "config_schema": config_schema,
        "ui_hints": spec.get("ui_hints", {}) or {},
        "execution_template": template,
        "structural_ui": bool(spec.get("structural_ui", False)),
    }


def render_node_file(spec: dict[str, Any]) -> str:
    imports = ["from typing import Any, ClassVar, Dict, List"]
    if spec["execution_template"] == "async_wait":
        imports.insert(0, "import asyncio")
    body = _execute_body(spec)
    return f'''"""{spec["display_name"]} node generated by aotn_node_helper."""

{chr(10).join(imports)}

from ...node_base import Node, NodeContext
from ...node_category import NodeCategory


class {spec["class_name"]}(Node):
    """{spec["description"] or spec["display_name"]}."""

    node_type: ClassVar[str] = {spec["node_type"]!r}
    display_name: ClassVar[str] = {spec["display_name"]!r}
    default_alias: ClassVar[str] = {spec["default_alias"]!r}
    description: ClassVar[str] = {spec["description"]!r}
    category: ClassVar[str] = NodeCategory.{spec["category_constant"]}
    input_ports: ClassVar[List[str]] = {_pretty(spec["input_ports"])}
    output_ports: ClassVar[List[str]] = {_pretty(spec["output_ports"])}
    input_port_metadata: ClassVar[Dict[str, Dict[str, str]]] = {_pretty(spec["input_port_metadata"])}
    output_port_metadata: ClassVar[Dict[str, Dict[str, str]]] = {_pretty(spec["output_port_metadata"])}
    default_config: ClassVar[Dict[str, Any]] = {_pretty(spec["default_config"])}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {_pretty(spec["config_schema"])}
    ui_hints: ClassVar[Dict[str, Any]] = {_pretty(spec["ui_hints"])}

    async def execute(self, context: NodeContext) -> None:
{body}
'''


def render_test_file(spec: dict[str, Any]) -> str:
    return f'''"""Focused tests for generated node {spec["node_type"]}."""

from __future__ import annotations

import pytest

from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.node_base import NodeContext


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("{spec["node_type"]}")]


def test_{spec["node_type"]}_registration_and_metadata():
    factory = NodeFactory()
    assert factory.is_valid_node_type("{spec["node_type"]}")
    metadata = next(item for item in factory.get_node_types_metadata() if item["type"] == "{spec["node_type"]}")
    assert metadata["display_name"] == {spec["display_name"]!r}
    assert metadata["default_alias"] == {spec["default_alias"]!r}
    assert metadata["input_ports"] == {_pretty(spec["input_ports"])}
    assert metadata["output_ports"] == {_pretty(spec["output_ports"])}


@pytest.mark.asyncio
async def test_{spec["node_type"]}_execute_template_smoke():
    factory = NodeFactory()
    node = factory.create_node("{spec["node_type"]}", "generated")
    memory = MemoryBank(EventBus())
    done = []
    errors = []
    context = NodeContext(
        node_id="generated",
        branch_id="branch",
        run_id="run",
        inputs={{"input": "seed"}},
        memory_bank=memory,
        signal_done=done.append,
        signal_error=errors.append,
        signal_waiting_for_input=lambda prompt: None,
        wait_for_nodes=lambda targets, timeout: None,
        wait_for_merge=lambda node_id, branch_id, port, inputs, timeout: None,
    )
    await node.execute(context)
{_render_generated_test_assertions(spec)}
'''


def _render_generated_test_assertions(spec: dict[str, Any]) -> str:
    if spec["execution_template"] == "error_stub":
        return '''    assert errors
    assert not done'''
    return '''    assert not errors
    assert done'''


def render_ui_todo(spec: dict[str, Any]) -> str:
    return f"""# Config UI Follow-Up: {spec['display_name']}

This generated node requested structural UI. The helper did not patch
`NodeConfigScreen` automatically.

- Node type: `{spec['node_type']}`
- Suggested first step: keep ordinary fields in `config_schema`.
- Add custom frontend UI only for topology-derived behavior.
- Preserve command navigation: W/S movement, E interaction, focusable previews,
  and scroll-to-first-control behavior.
"""


def update_registration(registration_file: Path, spec: dict[str, Any]) -> None:
    text = registration_file.read_text(encoding="utf-8") if registration_file.exists() else ""
    import_line = f"from .{spec['category']}.{spec['module_name']} import {spec['class_name']}"
    if import_line not in text:
        marker = "\n\nALL_NODE_CLASSES = ["
        if marker in text:
            text = text.replace(marker, f"\n{import_line}{marker}", 1)
        else:
            text = f"{text.rstrip()}\n{import_line}\n\nALL_NODE_CLASSES = [\n]\n"
    class_entry = f"    {spec['class_name']},"
    if class_entry not in text:
        text = text.replace("ALL_NODE_CLASSES = [", f"ALL_NODE_CLASSES = [\n{class_entry}", 1)
    registration_file.write_text(text, encoding="utf-8")


def _execute_body(spec: dict[str, Any]) -> str:
    template = spec["execution_template"]
    output_port = spec["output_ports"][0] if spec["output_ports"] else "default"
    if template == "pass_through":
        return f'        context.signal_done({{"data": {{{output_port!r}: context.inputs.get("input", "")}}}})'
    if template == "producer":
        return f'        context.signal_done({{"data": {{{output_port!r}: self.config.get("value", "")}}}})'
    if template == "transform_stub":
        return f'''        value = context.inputs.get("input", "")
        context.signal_done({{"data": {{{output_port!r}: value}}}})'''
    if template == "output_sink":
        return '''        value = context.inputs.get("input", "")
        log = list(context.memory_bank.read_persistent("output_log", default=[]))
        log.append(str(value))
        context.memory_bank.store_persistent("output_log", log)
        context.signal_done({"data": {"default": value}, "next_node_id": None})'''
    if template == "async_wait":
        return f'''        duration = float(self.config.get("duration", 0.0) or 0.0)
        await asyncio.sleep(max(0.0, duration))
        context.signal_done({{"data": {{{output_port!r}: context.inputs.get("input", "")}}}})'''
    if template == "error_stub":
        return f'        context.signal_error(RuntimeError("{spec["display_name"]} generated error stub"))'
    raise ValueError(f"Unhandled execution template: {template}")


def _load_yaml(text: str) -> dict[str, Any]:
    """Load YAML with PyYAML when available, otherwise a tiny safe subset."""
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text)
        return {} if data is None else data
    except ModuleNotFoundError:
        return _load_simple_yaml(text)


def _load_simple_yaml(text: str) -> dict[str, Any]:
    """Parse the helper's simple YAML subset via indentation."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    pending: list[tuple[int, str, dict[str, Any]]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        container = stack[-1][1]
        if line.startswith("- "):
            if not isinstance(container, list):
                raise ValueError("YAML list item found outside a list")
            item_text = line[2:].strip()
            if ":" in item_text and not item_text.startswith(("'", '"')):
                key, value = item_text.split(":", 1)
                item: dict[str, Any] = {key.strip(): _parse_scalar(value.strip())}
                container.append(item)
                stack.append((indent, item))
            else:
                container.append(_parse_scalar(item_text))
            continue
        if ":" not in line:
            raise ValueError(f"Invalid YAML line: {raw_line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            container[key] = _parse_scalar(value)
            continue
        next_container: dict[str, Any] | list[Any] = {}
        container[key] = next_container
        pending.append((indent, key, container))
        stack.append((indent, next_container))
        # Convert empty mapping to list lazily when the next significant line is
        # an indented list item.
        following = _next_significant_line(text.splitlines(), raw_line)
        if following and following[0] > indent and following[1].startswith("- "):
            container[key] = []
            stack[-1] = (indent, container[key])
    return root


def _next_significant_line(lines: list[str], current: str) -> tuple[int, str] | None:
    try:
        start = lines.index(current) + 1
    except ValueError:
        return None
    for raw in lines[start:]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        return len(raw) - len(raw.lstrip(" ")), raw.strip()
    return None


def _parse_scalar(value: str) -> Any:
    if value == "":
        return ""
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    if value in {"null", "None", "~"}:
        return None
    if value.startswith("[") or value.startswith("{") or value.startswith(("'", '"')):
        return ast.literal_eval(value)
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _required_identifier(spec: dict[str, Any], key: str) -> str:
    value = str(spec.get(key) or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]*", value):
        raise ValueError(f"{key} must be a valid snake_case identifier")
    return value


def _string_list(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{name} must be a non-empty list")
    result = [str(item).strip() for item in value if str(item).strip()]
    if len(result) != len(value):
        raise ValueError(f"{name} contains an empty value")
    return result


def _config_fields_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    if "config_tabs" not in spec:
        return spec.get("config_fields", spec.get("config", {})) or {}
    tabs = spec.get("config_tabs") or {}
    if not isinstance(tabs, dict):
        raise ValueError("config_tabs must be an object")
    fields: dict[str, Any] = {}
    for tab_name, tab_fields in tabs.items():
        if not isinstance(tab_fields, dict):
            raise ValueError(f"config_tabs.{tab_name} must be an object")
        for field_name, raw_field in tab_fields.items():
            if field_name in fields:
                raise ValueError(f"Config field {field_name!r} appears in more than one tab")
            if not isinstance(raw_field, dict):
                raise ValueError(f"Config field {field_name!r} must be an object")
            field = dict(raw_field)
            field.setdefault("tab", tab_name)
            fields[str(field_name)] = field
    return fields


def _port_metadata(raw: Any, ports: list[str]) -> dict[str, dict[str, str]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Port metadata must be an object")
    result: dict[str, dict[str, str]] = {}
    for port, value in raw.items():
        if port not in ports:
            raise ValueError(f"Metadata references undeclared port {port!r}")
        if not isinstance(value, dict):
            raise ValueError(f"Metadata for port {port!r} must be an object")
        result[str(port)] = {
            "name": str(value.get("name") or ""),
            "description": str(value.get("description") or ""),
        }
    return result


def _pascal_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.split("_") if part)


def _title_case(value: str) -> str:
    suffix = "_node"
    if value.endswith(suffix):
        value = value[: -len(suffix)]
    return " ".join(part.capitalize() for part in value.split("_") if part)


def _pretty(value: Any) -> str:
    return repr(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate an AttackOfTheNodes node")
    parser.add_argument("spec", type=Path, help="Path to a JSON/YAML node spec")
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument("--force", action="store_true", help="Overwrite an existing generated node file")
    args = parser.parse_args(argv)
    paths = generate_from_spec(load_spec(args.spec), project_root=args.project_root, force=args.force)
    print(f"Generated node: {paths.node_file}")
    print(f"Updated registration: {paths.registration_file}")
    print(f"Generated focused tests: {paths.test_file}")
    if paths.ui_todo_file:
        print(f"Generated UI follow-up notes: {paths.ui_todo_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
