"""
Node factory for AttackOfTheNodes v0.5.

Maintains a registry from node type strings to Node subclasses. Creates node
instances and exposes metadata for UI and validation.
"""

import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional, Type

from .node_errors import ERROR_PORT, definitions_with_default
from .data_types import coerce_type
from .config_migrations import normalize_node_config
from .node_base import Node
from .node_capabilities import supported_standard_flags
from .node_metadata import record_for, standard_key_docs
from .nodes import ALL_NODE_CLASSES


logger = logging.getLogger(__name__)


class NodeFactory:
    """Registry and factory for all node types."""

    def __init__(self) -> None:
        self._node_registry: Dict[str, Type[Node]] = {}
        self._metadata_by_type: Optional[Dict[str, Dict[str, Any]]] = None
        self._register_node_types()

    def _register_node_types(self) -> None:
        """Register every node class listed by the nodes package."""
        for node_class in ALL_NODE_CLASSES:
            node_type = getattr(node_class, "node_type", "")
            if not node_type:
                logger.warning(
                    "Node class %s has no node_type; skipping registration",
                    node_class.__name__,
                )
                continue
            self._node_registry[node_type] = node_class

    def create_node(
        self,
        node_type: str,
        node_id: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Node]:
        """Instantiate a node by type."""
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            logger.error("Unknown node type: %s", node_type)
            return None
        return node_class(node_id, normalize_node_config(node_type, config) if config is not None else None)

    def create_config_template(self, node_type: str) -> Optional[Dict[str, Any]]:
        """Return a fresh default config copy for a node type."""
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            return None
        return deepcopy(node_class.default_config)

    def output_ports_for(
        self, node_type: str, config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Output ports a node of ``node_type`` has with ``config``.

        Unknown types have none. Metadata ``output_ports`` stays the type's
        full list; this is the one place that narrows or extends it per node.
        """
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            return []
        return [str(port) for port in node_class.resolve_output_ports(dict(config or {}))]

    def input_ports_for(
        self, node_type: str, config: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Input ports a node of ``node_type`` has with ``config``."""
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            return []
        return [str(port) for port in node_class.resolve_input_ports(dict(config or {}))]

    def node_input_ports(self, node_data: Optional[Dict[str, Any]]) -> List[str]:
        """Input ports of a saved node, resolved from its config."""
        node_data = node_data or {}
        return self.input_ports_for(
            str(node_data.get("type") or ""), node_data.get("config") or {}
        )

    def declared_input_ports(self, node_type: str) -> List[str]:
        """The type's fixed class list (metadata ``input_ports``)."""
        node_class = self._node_registry.get(node_type)
        return [str(port) for port in node_class.input_ports] if node_class else []

    def declared_output_ports(self, node_type: str) -> List[str]:
        """The type's fixed class list (metadata ``output_ports``)."""
        node_class = self._node_registry.get(node_type)
        return [str(port) for port in node_class.output_ports] if node_class else []

    def node_output_ports(self, node_data: Optional[Dict[str, Any]]) -> List[str]:
        """Output ports of a saved node (``{"type": ..., "config": ...}``)."""
        node_data = node_data or {}
        return self.output_ports_for(
            str(node_data.get("type") or ""), node_data.get("config") or {}
        )

    def node_output_port_metadata(
        self, node_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Normalized metadata for each port ``node_output_ports`` returns."""
        node_data = node_data or {}
        node_class = self._node_registry.get(str(node_data.get("type") or ""))
        if node_class is None:
            return {}
        config = dict(node_data.get("config") or {})
        ports = [str(port) for port in node_class.resolve_output_ports(config)]
        declared = dict(node_class.output_port_metadata)
        for port, extra in node_class.describe_output_ports(config).items():
            declared[port] = {**dict(declared.get(port) or {}), **dict(extra or {})}
        return self._port_metadata(ports, declared, "output")

    def spawns_branches(self, node_type: str) -> bool:
        """Whether nodes of ``node_type`` start branch supervisors."""
        node_class = self._node_registry.get(node_type)
        return bool(node_class is not None and node_class.spawns_branches)

    def get_default_alias(self, node_type: str) -> Optional[str]:
        """Return the default user-facing alias for a node type."""
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            return None
        return node_class.default_alias or node_class.display_name or node_type

    def metadata_for_type(self, node_type: str) -> Optional[Dict[str, Any]]:
        """One type's metadata, built once and shared; callers must not modify it.

        Types are fixed once the factory exists, so the editor can look up a
        type per row and per key press without rebuilding the metadata of
        every type each time (UX3). ``get_node_types_metadata`` still returns
        fresh copies.
        """
        if self._metadata_by_type is None:
            self._metadata_by_type = {
                item["type"]: item for item in self.get_node_types_metadata()
            }
        return self._metadata_by_type.get(node_type)

    def get_node_types_metadata(self) -> List[Dict[str, Any]]:
        """Return UI-ready metadata for every registered node type."""
        metadata: List[Dict[str, Any]] = []
        for node_type, node_class in self._node_registry.items():
            primary_family = self._metadata_string(
                getattr(node_class, "primary_family", "")
            )
            legacy_category = self._metadata_string(getattr(node_class, "category", ""))
            category = primary_family or legacy_category
            # Record v1 (backend/node_metadata.py) is the one authored source;
            # description and execution_contract are derived aliases of it.
            # A pending type has no record: None, never an empty Read-only one.
            record = record_for(node_type)
            metadata.append(
                {
                    "type": node_type,
                    "display_name": node_class.display_name,
                    "default_alias": node_class.default_alias,
                    "description": record["purpose"] if record else node_class.description,
                    "node_metadata": record,
                    "standard_key_docs": standard_key_docs(node_class.default_config),
                    "execution_contract": deepcopy((record or {}).get("execution_contract") or {}),
                    "category": category,
                    "primary_family": category,
                    "legacy_category": legacy_category,
                    "tags": self._metadata_tags(getattr(node_class, "tags", [])),
                    "icon_name": self._metadata_string(
                        getattr(node_class, "icon_name", "")
                    ),
                    "color_hint": self._metadata_string(
                        getattr(node_class, "color_hint", "")
                    ),
                    "group": self._metadata_string(
                        getattr(node_class, "group", None)
                    )
                    or None,
                    "selector_section": self._metadata_string(
                        getattr(node_class, "selector_section", None)
                    )
                    or None,
                    "input_ports": list(node_class.input_ports),
                    "output_ports": list(node_class.output_ports),
                    "input_port_metadata": self._port_metadata(
                        node_class.input_ports,
                        node_class.input_port_metadata,
                        "input",
                    ),
                    "output_port_metadata": self._port_metadata(
                        node_class.output_ports,
                        node_class.output_port_metadata,
                        "output",
                    ),
                    "config_schema": dict(node_class.config_schema),
                    "default_config": dict(node_class.default_config),
                    "ui_hints": dict(getattr(node_class, "ui_hints", {})),
                    "editor_only": bool(getattr(node_class, "editor_only", False)),
                    "terminates_branch": bool(node_class.terminates_branch),
                    "spawns_branches": bool(node_class.spawns_branches),
                    # D7: declared codes plus the default generic code, which
                    # is listed first so no error is ever unmatched.
                    "errors": definitions_with_default(
                        getattr(node_class, "error_definitions", [])
                    ),
                    "error_port": ERROR_PORT,
                    "custom_config_keys": dict(getattr(node_class, "custom_config_keys", {})),
                }
            )
        for item in metadata:
            item['standard_flags'] = sorted(supported_standard_flags(item))
        return sorted(metadata, key=lambda item: item["display_name"])

    def _metadata_string(self, value: Any) -> str:
        """Return a plain string for metadata values, including str enums."""
        if value is None:
            return ""
        enum_value = getattr(value, "value", None)
        if enum_value is not None:
            value = enum_value
        return str(value)

    def _metadata_tags(self, value: Any) -> List[str]:
        """Return subcategory tags as a list of plain strings."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        return [self._metadata_string(item) for item in value if item]

    def _port_metadata(
        self,
        ports: List[str],
        configured: Dict[str, Dict[str, Any]],
        direction: str,
    ) -> Dict[str, Dict[str, Any]]:
        """Return the per-port I/O contract for every declared port.

        Fills the forward-compatible defaults from docs/archive/NODE_STANDARDIZATION_HANDOFF.md
        §6: absent `data_type` ⇒ `any` (the explicit permissive type), absent
        `required` ⇒ optional (`False`). Declared types are canonicalized
        through backend.data_types so the deprecated `boolean` spelling resolves
        to `bool`.
        """
        result: Dict[str, Dict[str, Any]] = {}
        for port in ports:
            entry = dict(configured.get(port, {}))
            if not entry.get("name"):
                if port == "default":
                    entry["name"] = "Output" if direction == "output" else "Input"
                elif port == "input":
                    entry["name"] = "Input"
                else:
                    entry["name"] = port.replace("_", " ").title()
            entry.setdefault("description", "")
            entry["data_type"] = coerce_type(entry.get("data_type"))
            entry["required"] = bool(entry.get("required", False))
            result[port] = entry
        return result

    def is_valid_node_type(self, node_type: str) -> bool:
        """Return True when node_type is registered."""
        return node_type in self._node_registry

    def get_registered_types(self) -> List[str]:
        """Return registered node type identifiers."""
        return list(self._node_registry.keys())
