"""
Event definitions for the AttackOfTheNodes event bus.

Event names are strings for simple publish/subscribe dispatch. State values
are enums so typos in state transitions are easier to catch.
"""

from enum import Enum


WORKFLOW_STATE_UPDATE = "WORKFLOW_STATE_UPDATE"
WORKFLOW_DIRTY = "WORKFLOW_DIRTY"

SUPERVISOR_REGISTER = "SUPERVISOR_REGISTER"
SUPERVISOR_TERMINATING = "SUPERVISOR_TERMINATING"
SUPERVISOR_STATE_UPDATE = "SUPERVISOR_STATE_UPDATE"
SUPERVISOR_REQUEST_BRANCH = "SUPERVISOR_REQUEST_BRANCH"
SUPERVISOR_ERROR = "SUPERVISOR_ERROR"
BREAKPOINT_HIT = "BREAKPOINT_HIT"
NODE_TIMING_UPDATE = "NODE_TIMING_UPDATE"
RECOVERY_OPTIONS_AVAILABLE = "RECOVERY_OPTIONS_AVAILABLE"
TERMINATE_WORKFLOW_REQUESTED = "TERMINATE_WORKFLOW_REQUESTED"

USER_INPUT_NEEDED = "USER_INPUT_NEEDED"
# A node asks any listening frontend to display a file (FO3). JSON payload:
# run_id / branch_id / node_id (stamped by the supervisor), path, ref_key,
# render ("markdown" | "plain"). Headless runs have no subscriber and the
# event is inert by design.
FILE_VIEW_REQUESTED = "FILE_VIEW_REQUESTED"
ERROR_OCCURRED = "ERROR_OCCURRED"
ERROR_LOGGED = "ERROR_LOGGED"
ERRORS_CLEARED = "ERRORS_CLEARED"

MEMORY_UPDATE = "MEMORY_UPDATE"
OUTPUT_UPDATE = "OUTPUT_UPDATE"
RUN_HISTORY_UPDATED = "RUN_HISTORY_UPDATED"


class WorkflowState(str, Enum):
    """Overall workflow run state, owned by MasterState."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class SupervisorState(str, Enum):
    """State of an individual supervisor walking one branch."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    AWAITING_RECOVERY = "AWAITING_RECOVERY"
    ERROR = "ERROR"
    TERMINATED = "TERMINATED"
