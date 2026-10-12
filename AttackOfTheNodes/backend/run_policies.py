"""
Run policies for AttackOfTheNodes (decision D1).

Whoever starts a run decides how that run gets recovery choices and user
input. A run started with no policy keeps the attended behavior: the engine
publishes ``RECOVERY_OPTIONS_AVAILABLE`` / ``USER_INPUT_NEEDED`` and waits for
a client (the TUI) to answer through ``MasterState``. A run started with a
``RecoveryPolicy`` and/or ``InputProvider`` asks those objects instead, so the
same node can ask whichever client launched the run (CLI, API, AI).

The step 1 ``unattended`` value is the first ``RecoveryPolicy``:
``TerminatePolicy`` paired with ``NoInputProvider``.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


RETRY = "RETRY"
SKIP = "SKIP"
TERMINATE_BRANCH = "TERMINATE_BRANCH"
TERMINATE_WORKFLOW = "TERMINATE_WORKFLOW"
RECOVERY_ACTIONS: Tuple[str, ...] = (RETRY, SKIP, TERMINATE_BRANCH, TERMINATE_WORKFLOW)

# Unattended policy value -> recovery action taken without waiting for a client.
UNATTENDED_ACTIONS = {
    "terminate_branch": TERMINATE_BRANCH,
    "terminate_workflow": TERMINATE_WORKFLOW,
}


class UnattendedInputError(RuntimeError):
    """A node asked for user input in a run that has no one to answer."""


@dataclass(frozen=True)
class RecoveryRequest:
    """A node error waiting for a recovery decision. JSON-friendly fields only."""

    run_id: str
    branch_id: str
    node_id: Optional[str]
    error: Dict[str, Any]
    options: List[str] = field(default_factory=lambda: list(RECOVERY_ACTIONS))

    @property
    def message(self) -> str:
        return str(self.error.get("message") or "")


@dataclass(frozen=True)
class InputRequest:
    """A node asking for one line of user input."""

    run_id: str
    branch_id: str
    node_id: Optional[str]
    prompt: str


class RecoveryPolicy(ABC):
    """Decides what happens when a node errors in a run.

    ``pause_at_breakpoints`` is False for policies that run without someone
    able to resume the run; breakpoints are then skipped.
    """

    pause_at_breakpoints: bool = False

    @abstractmethod
    async def decide(self, request: RecoveryRequest) -> str:
        """Return one of ``request.options``."""


class InputProvider(ABC):
    """Supplies answers to user-input requests in a run."""

    @abstractmethod
    async def provide(self, request: InputRequest) -> str:
        """Return the answer, or raise to fail the requesting node."""


class TerminatePolicy(RecoveryPolicy):
    """Unattended policy: end the failing branch or the whole workflow."""

    def __init__(self, mode: str) -> None:
        if mode not in UNATTENDED_ACTIONS:
            raise ValueError(f"Unknown unattended policy: {mode!r}")
        self.mode = mode

    async def decide(self, request: RecoveryRequest) -> str:
        return UNATTENDED_ACTIONS[self.mode]

    def __repr__(self) -> str:
        return f"TerminatePolicy({self.mode!r})"


class NoInputProvider(InputProvider):
    """Unattended input: every request fails its node."""

    async def provide(self, request: InputRequest) -> str:
        raise UnattendedInputError(
            f"Input required but run is unattended (prompt: {request.prompt!r})"
        )


def unattended_policies(mode: str) -> Tuple[RecoveryPolicy, InputProvider]:
    """The policy pair the step 1 ``unattended=`` value stands for."""
    return TerminatePolicy(mode), NoInputProvider()
