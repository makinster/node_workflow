"""
Event bus for AttackOfTheNodes v0.5.

Callbacks fire synchronously in the publisher's thread. This keeps Phase 1
simple and mirrors the future backend-to-frontend event boundary.
"""

import logging
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


logger = logging.getLogger(__name__)


class EventBus:
    """Small publish-subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Register a callback for an event name."""
        self._subscribers[event_name].append(callback)

    def unsubscribe(self, event_name: str, callback: Callable[[Any], None]) -> None:
        """Remove a previously registered callback."""
        if callback in self._subscribers[event_name]:
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, event_data: Any = None) -> None:
        """Publish event_data to all subscribers for event_name."""
        for callback in list(self._subscribers[event_name]):
            try:
                callback(event_data)
            except Exception:
                logger.exception("Error in event callback for %s", event_name)

    def clear_subscribers(self, event_name: Optional[str] = None) -> None:
        """Remove subscribers for one event, or for all events."""
        if event_name is not None:
            self._subscribers[event_name].clear()
        else:
            self._subscribers.clear()
