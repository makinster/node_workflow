"""Immutable, in-memory facts supplied to one node visit; no persistence access."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RunErrorSummary:
    time: str
    node_name: str
    code: str
    handled: bool
    message: str


@dataclass(frozen=True)
class RunSnapshot:
    started_at: str
    errors: tuple[RunErrorSummary, ...] = ()
    older_errors: int = 0
