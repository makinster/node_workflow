"""
Base node interfaces for AttackOfTheNodes v0.5.

Concrete nodes inherit from Node, declare class-level metadata, and implement
async execute(context). The supervisor supplies NodeContext during execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
)

from .field_types import validate_config_schema


if TYPE_CHECKING:
    from .memory_bank import MemoryBank


@dataclass
class NodeContext:
    """
    Execution context passed to a node's execute method.

    The supervisor populates inputs before calling execute() by reading each
    input port's connected upstream output from the memory bank's transient
    store. Nodes read inputs through this dict instead of resolving graph
    connections themselves.
    """

    node_id: str
    branch_id: str
    run_id: str
    inputs: Dict[str, Any]
    memory_bank: "MemoryBank"
    signal_done: Callable[[Dict[str, Any]], None]
    signal_error: Callable[[Exception], None]
    signal_waiting_for_input: Callable[[str], Awaitable[str]]
    wait_for_nodes: Callable[[List[str], Optional[float]], Awaitable[None]]
    wait_for_merge: Callable[
        [str, str, str, Dict[str, Any], Optional[float]],
        Awaitable[Dict[str, Any]],
    ]


class Node(ABC):
    """Abstract base class for all workflow nodes."""

    node_type: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    default_alias: ClassVar[str] = ""
    description: ClassVar[str] = ""
    category: ClassVar[str] = ""

    input_ports: ClassVar[List[str]] = []
    output_ports: ClassVar[List[str]] = ["default"]

    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    # Optional metadata
    icon_name: ClassVar[str] = ""
    tags: ClassVar[List[str]] = []
    color_hint: ClassVar[str] = ""
    examples: ClassVar[List[Dict[str, Any]]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.default_alias:
            cls.default_alias = cls.display_name
        if cls.config_schema:
            errors = validate_config_schema(cls.config_schema)
            if errors:
                raise ValueError(
                    f"Invalid config_schema in {cls.__name__}: {errors}"
                )

    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None) -> None:
        self.node_id = node_id
        self.config = dict(config) if config is not None else dict(self.default_config)

    @abstractmethod
    async def execute(self, context: NodeContext) -> None:
        """Run this node's logic and signal through the provided context."""
        raise NotImplementedError

    def validate_config(self) -> List[str]:
        """Return human-readable config validation errors."""
        errors: List[str] = []
        for field_name, field_info in self.config_schema.items():
            if field_info.get("required", False) and field_name not in self.config:
                errors.append(f"Missing required field: {field_name}")
        return errors

    def get_input_ports(self) -> List[str]:
        """Return this node type's input port names."""
        return list(self.input_ports)

    def get_output_ports(self) -> List[str]:
        """Return this node type's output port names."""
        return list(self.output_ports)
