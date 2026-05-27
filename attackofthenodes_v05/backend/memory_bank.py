"""
Memory bank for AttackOfTheNodes v0.5.

Holds runtime data for one workflow run. The persistent store is the named
variable space; the transient store is the wire between connected node ports.
"""

from typing import Any, Dict

from .event_bus import EventBus
from .events import MEMORY_UPDATE


_TRANSIENT_SEPARATOR = "__"


class MemoryBank:
    """Run-scoped storage with persistent and transient halves."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._persistent: Dict[str, Any] = {}
        self._transient: Dict[str, Any] = {}

    def store_persistent(self, key: str, value: Any) -> None:
        """Write a named variable and publish a memory update."""
        self._persistent[key] = value
        self._event_bus.publish(MEMORY_UPDATE, self.get_state())

    def read_persistent(self, key: str, default: Any = None) -> Any:
        """Read a named variable."""
        return self._persistent.get(key, default)

    def store_transient(self, node_id: str, port_name: str, value: Any) -> None:
        """Write a node output value for one output port."""
        key = f"{node_id}{_TRANSIENT_SEPARATOR}{port_name}"
        self._transient[key] = value

    def read_transient(self, node_id: str, port_name: str, default: Any = None) -> Any:
        """Read a node output value previously written to a port."""
        key = f"{node_id}{_TRANSIENT_SEPARATOR}{port_name}"
        return self._transient.get(key, default)

    def get_state(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of both stores."""
        return {
            "persistent": dict(self._persistent),
            "transient": dict(self._transient),
        }

    def clear(self) -> None:
        """Clear both stores at the start of a run."""
        self._persistent.clear()
        self._transient.clear()
        self._event_bus.publish(MEMORY_UPDATE, self.get_state())

    def load_state(self, state: Dict[str, Dict[str, Any]]) -> None:
        """Restore both stores from a serialized snapshot."""
        self._persistent = dict(state.get("persistent", {}))
        self._transient = dict(state.get("transient", {}))
        self._event_bus.publish(MEMORY_UPDATE, self.get_state())
