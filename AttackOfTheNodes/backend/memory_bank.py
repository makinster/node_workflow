"""
Memory bank for AttackOfTheNodes v0.5.

Holds runtime data for one workflow run. The persistent store is the named
variable space; the transient store is the wire between connected node ports.

MEMORY_UPDATE carries only a lightweight delta describing what changed
(e.g. {"change": "set", "key": ...}); it is a signal, not a snapshot.
Subscribers that need the current contents pull get_state() on demand. This
keeps each persistent write O(1) instead of deep-copying both stores per write,
which grew O(n^2) over the course of a run.
"""

from contextvars import ContextVar
from copy import deepcopy
from time import monotonic
from typing import Any, Dict, List, Optional

from .event_bus import EventBus
from .events import MEMORY_UPDATE


_TRANSIENT_SEPARATOR = "__"

#: The node step writing to the Vault right now (EX, 2026-10-19). Each
#: supervisor runs in its own task and sets this at every step, so a write
#: records which node, branch and visit made it; nodes need no changes.
current_writer: ContextVar[Optional[Dict[str, Any]]] = ContextVar("aotn_vault_writer", default=None)

#: Keys the engine keeps for itself; the Vault log leaves them out.
INTERNAL_KEYS = frozenset({"output_log"})


class MemoryBank:
    """Run-scoped storage with persistent and transient halves."""

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._persistent: Dict[str, Any] = {}
        self._persistent_type_tags: Dict[str, Optional[str]] = {}
        self._transient: Dict[str, Any] = {}
        self._writes: List[Dict[str, Any]] = []
        self._started = monotonic()

    def store_persistent(self, key: str, value: Any, type_tag: Optional[str] = None) -> None:
        """Write a named variable and publish a memory update."""
        self._persistent[key] = value
        self._persistent_type_tags[key] = type_tag
        if key not in INTERNAL_KEYS:
            writer = current_writer.get() or {}
            self._writes.append({
                "seconds": monotonic() - self._started,
                "key": key,
                "type": type_tag,
                "value": _snapshot(value),
                "node_id": writer.get("node_id"),
                "branch_id": writer.get("branch_id"),
                "visit": writer.get("visit"),
            })
        self._event_bus.publish(MEMORY_UPDATE, {"change": "set", "key": key})

    def writes(self) -> List[Dict[str, Any]]:
        """Every Vault write this run, oldest first: when (seconds since the
        run began), key, type, the value as written, and which node step
        wrote it (``node_id``, ``branch_id``, ``visit``; None outside a node)."""
        return list(self._writes)

    def read_persistent(self, key: str, default: Any = None) -> Any:
        """Read a named variable."""
        return self._persistent.get(key, default)

    def read_persistent_by_type(self, type_tag: str) -> Dict[str, Any]:
        """Return all persistent entries whose stored type_tag matches."""
        return {
            k: v
            for k, v in self._persistent.items()
            if self._persistent_type_tags.get(k) == type_tag
        }

    def store_transient(self, node_id: str, port_name: str, value: Any) -> None:
        """Write a node output value for one output port."""
        key = f"{node_id}{_TRANSIENT_SEPARATOR}{port_name}"
        self._transient[key] = value

    def read_transient(self, node_id: str, port_name: str, default: Any = None) -> Any:
        """Read a node output value previously written to a port."""
        key = f"{node_id}{_TRANSIENT_SEPARATOR}{port_name}"
        return self._transient.get(key, default)

    def get_state(self) -> Dict[str, Any]:
        """Return a snapshot of both stores."""
        return {
            "persistent": dict(self._persistent),
            "persistent_type_tags": dict(self._persistent_type_tags),
            "transient": dict(self._transient),
        }

    def clear(self) -> None:
        """Clear both stores at the start of a run."""
        self._persistent.clear()
        self._persistent_type_tags.clear()
        self._transient.clear()
        self._writes.clear()
        self._started = monotonic()
        self._event_bus.publish(MEMORY_UPDATE, {"change": "clear"})

    def load_state(self, state: Dict[str, Any]) -> None:
        """Restore both stores from a serialized snapshot."""
        self._persistent = dict(state.get("persistent", {}))
        self._persistent_type_tags = dict(state.get("persistent_type_tags", {}))
        self._transient = dict(state.get("transient", {}))
        self._event_bus.publish(MEMORY_UPDATE, {"change": "load"})


def _snapshot(value: Any) -> Any:
    """The value as it was written; a later change to it must not rewrite history."""
    try:
        return deepcopy(value)
    except Exception:
        return value
