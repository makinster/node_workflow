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

    def get_node_types_metadata(self) -> List[Dict[str, Any]]:
        """Return UI-ready metadata for every registered node type."""
        metadata: List[Dict[str, Any]] = []
        for node_type, node_class in self._node_registry.items():
            metadata.append(
                {
                    "type": node_type,
                    "display_name": node_class.display_name,
                    "description": node_class.description,
                    "input_ports": list(node_class.input_ports),
                    "output_ports": list(node_class.output_ports),
                    "config_schema": dict(node_class.config_schema),
                    "default_config": dict(node_class.default_config),
                    "ui_hints": dict(getattr(node_class, "ui_hints", {})),
                }
            )
        return sorted(metadata, key=lambda item: item["display_name"])

    def is_valid_node_type(self, node_type: str) -> bool:
        """Return True when node_type is registered."""
        return node_type in self._node_registry

    def get_registered_types(self) -> List[str]:
        """Return registered node type identifiers."""
        return list(self._node_registry.keys())
