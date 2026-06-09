"""Async try/catch helper for the data, error = await try_catch(coro()) pattern."""

from typing import Any, Coroutine, Optional, Tuple, TypeVar

T = TypeVar("T")


async def try_catch(coro: Coroutine[Any, Any, T]) -> Tuple[Optional[T], Optional[Exception]]:
    """Await *coro* and return (result, None) on success or (None, exc) on failure."""
    try:
        return await coro, None
    except Exception as exc:
        return None, exc
