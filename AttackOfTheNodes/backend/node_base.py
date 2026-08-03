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

from .data_types import validate_type
from .field_types import validate_config_schema


if TYPE_CHECKING:
    from .memory_bank import MemoryBank
    from .run_session import RunSession
    from .secrets_manager import SecretsManager


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
    run_session: Optional["RunSession"] = None
    secrets_manager: Optional["SecretsManager"] = None
    # Publish a JSON-serializable event to the run's EventBus. Wired by the
    # supervisor (which stamps run_id/branch_id/node_id); None outside a run.
    publish_event: Optional[Callable[[str, Dict[str, Any]], None]] = None

    def emit_event(self, event_name: str, payload: Dict[str, Any]) -> bool:
        """Publish an event if a bus is wired in; return whether it was sent."""
        if self.publish_event is None:
            return False
        self.publish_event(event_name, payload)
        return True

    def get_secret(self, key: str) -> Optional[str]:
        """Return the secret value for key, or None if the manager is not wired in."""
        if self.secrets_manager is None:
            return None
        return self.secrets_manager.get_secret(key)


class Node(ABC):
    """Abstract base class for all workflow nodes."""

    node_type: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    default_alias: ClassVar[str] = ""
    description: ClassVar[str] = ""
    category: ClassVar[str] = ""
    primary_family: ClassVar[str] = ""

    input_ports: ClassVar[List[str]] = []
    output_ports: ClassVar[List[str]] = ["default"]
    # Per-port I/O contract metadata. Each entry may carry `name`, `description`,
    # `data_type` (from backend.data_types; absent ⇒ `any`), and `required`
    # (absent ⇒ optional/False). NodeFactory fills the defaults on exposure;
    # see NODE_STANDARDIZATION_HANDOFF.md §4/§6.
    input_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {}
    output_port_metadata: ClassVar[Dict[str, Dict[str, Any]]] = {}

    default_config: ClassVar[Dict[str, Any]] = {}
    config_schema: ClassVar[Dict[str, Dict[str, Any]]] = {}

    # Optional metadata
    icon_name: ClassVar[str] = ""
    tags: ClassVar[List[str]] = []
    color_hint: ClassVar[str] = ""
    examples: ClassVar[List[Dict[str, Any]]] = []

    # Frontend-only navigation metadata (Phase 17). The backend exposes these
    # through NodeFactory but never branches on them. Nodes sharing a group
    # appear behind one Group Picker entry; selector_section names the header
    # an entry renders under. Group members must share one selector_section.
    group: ClassVar[Optional[str]] = None
    selector_section: ClassVar[Optional[str]] = None

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
        cls._validate_port_data_types()

    @classmethod
    def _validate_port_data_types(cls) -> None:
        """Warn when a declared port `data_type` is outside the canonical set.

        Unknown types warn (via backend.data_types.validate_type) rather than
        raise — the vocabulary is a soft semantic convention, and absent types
        default to `any` at exposure time. This is the helper-facing validation
        surface promised by the canonical data-type module.
        """
        for direction, metadata in (
            ("input", cls.input_port_metadata),
            ("output", cls.output_port_metadata),
        ):
            for port, info in metadata.items():
                if not isinstance(info, dict):
                    continue
                declared = info.get("data_type")
                if declared:
                    validate_type(declared, source=f"{cls.node_type or cls.__name__} {direction} port '{port}'")

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
