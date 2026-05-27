"""Central UI state for AttackOfTheNodes."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


UI_STATE_CHANGED = "UI_STATE_CHANGED"


@dataclass
class UIState:
    """Central UI state shared by the app and panels."""

    mode: str = "editor"
    workflow_run_state: str = "IDLE"
    current_workflow_id: Optional[str] = None
    current_workflow_name: str = ""
    is_dirty: bool = False
    active_supervisors: List[Dict[str, str]] = field(default_factory=list)
    selected_supervisor_id: Optional[str] = None
    editor_center_node_id: Optional[str] = None
    validation_status: Optional[Dict[str, object]] = None
    node_statuses: Dict[str, str] = field(default_factory=dict)
    supervisor_nodes: Dict[str, Optional[str]] = field(default_factory=dict)
    modal_stack: List[str] = field(default_factory=list)
    _event_bus: Any = field(default=None, repr=False, compare=False)

    def attach_event_bus(self, event_bus) -> None:
        """Attach the event bus used to announce state changes."""
        self._event_bus = event_bus

    def set_workflow_identity(self, workflow_id: Optional[str], name: str) -> None:
        self.current_workflow_id = workflow_id
        self.current_workflow_name = name
        self._publish_changed("workflow_identity")

    def set_dirty(self, is_dirty: bool) -> None:
        self.is_dirty = is_dirty
        self._publish_changed("dirty")

    def set_run_state(self, state: str) -> None:
        self.workflow_run_state = state
        self.mode = "editor" if state in ("IDLE", "FINISHED") else "execution"
        self._publish_changed("run_state")

    def set_validation_status(self, result: Optional[Dict[str, object]]) -> None:
        self.validation_status = result
        self._publish_changed("validation")

    def push_modal(self, modal_name: str) -> None:
        self.modal_stack.append(modal_name)
        self._publish_changed("modal_stack")

    def pop_modal(self, modal_name: Optional[str] = None) -> None:
        if modal_name and modal_name in self.modal_stack:
            self.modal_stack.remove(modal_name)
        elif self.modal_stack:
            self.modal_stack.pop()
        self._publish_changed("modal_stack")

    def _publish_changed(self, reason: str) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(UI_STATE_CHANGED, {"reason": reason, "state": self})
