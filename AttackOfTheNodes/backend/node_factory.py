"""
Node factory for AttackOfTheNodes v0.5.

Maintains a registry from node type strings to Node subclasses. Creates node
instances and exposes metadata for UI and validation.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from .node_base import Node
from .nodes import ALL_NODE_CLASSES


logger = logging.getLogger(__name__)


class NodeFactory:
    """Registry and factory for all node types."""

    def __init__(self) -> None:
        self._node_registry: Dict[str, Type[Node]] = {}
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
        return node_class(node_id, config)

    def create_config_template(self, node_type: str) -> Optional[Dict[str, Any]]:
        """Return a fresh default config copy for a node type."""
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            return None
        return dict(node_class.default_config)

    def get_default_alias(self, node_type: str) -> Optional[str]:
        """Return the default user-facing alias for a node type."""
        node_class = self._node_registry.get(node_type)
        if node_class is None:
            return None
        return node_class.default_alias or node_class.display_name or node_type

    def get_node_types_metadata(self) -> List[Dict[str, Any]]:
        """Return UI-ready metadata for every registered node type."""
        metadata: List[Dict[str, Any]] = []
        for node_type, node_class in self._node_registry.items():
            primary_family = self._metadata_string(
                getattr(node_class, "primary_family", "")
            )
            legacy_category = self._metadata_string(getattr(node_class, "category", ""))
            category = primary_family or legacy_category
            metadata.append(
                {
                    "type": node_type,
                    "display_name": node_class.display_name,
                    "default_alias": node_class.default_alias,
                    "description": node_class.description,
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
                }
            )
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
        configured: Dict[str, Dict[str, str]],
        direction: str,
    ) -> Dict[str, Dict[str, str]]:
        """Return semantic metadata for every declared port."""
        result: Dict[str, Dict[str, str]] = {}
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
            result[port] = entry
        return result

    def is_valid_node_type(self, node_type: str) -> bool:
        """Return True when node_type is registered."""
        return node_type in self._node_registry

    def get_registered_types(self) -> List[str]:
        """Return registered node type identifiers."""
        return list(self._node_registry.keys())
