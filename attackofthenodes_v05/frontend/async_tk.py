"""
Asyncio/tkinter integration for AttackOfTheNodes.

Tkinter owns the main thread. This shim gives asyncio tasks short chances to
advance between Tk events by pumping a dedicated event loop with root.after().
"""

import asyncio


class AsyncTkPump:
    """Small coordinator that pumps an asyncio loop from tkinter."""

    def __init__(self, root, interval_ms: int = 50) -> None:
        self.root = root
        self.interval_ms = interval_ms
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self._running = False

    def start(self) -> None:
        """Start periodic asyncio pumping."""
        if self._running:
            return
        self._running = True
        self.root.after(self.interval_ms, self._pump)

    def stop(self) -> None:
        """Stop pumping and close the loop when possible."""
        self._running = False
        if not self.loop.is_closed():
            self.loop.call_soon(self.loop.stop)

    def create_task(self, coroutine):
        """Schedule a coroutine on the managed loop."""
        return self.loop.create_task(coroutine)

    def _pump(self) -> None:
        if not self._running or self.loop.is_closed():
            return
        self.loop.run_until_complete(asyncio.sleep(0))
        self.root.after(self.interval_ms, self._pump)
