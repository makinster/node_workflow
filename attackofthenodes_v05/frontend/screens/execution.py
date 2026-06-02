"""Execution screen for live workflow runs."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.screen import Screen
from textual.widgets import Header, Label, RichLog, Static
from rich.text import Text

from frontend.screens.error_details import ErrorDetailsScreen
from frontend.screens.memory_viewer import MemoryViewerScreen
from frontend.screens.output_viewer import OutputViewerScreen
from frontend.output_records import format_output_record, normalize_outputs
from frontend.widgets.node_list import NodeList
from frontend.widgets.status_bar import StatusBar


class ExecutionScreen(Screen):
    """Live workflow execution view."""

    BINDINGS = [
        ("p", "pause_resume", "Pause/resume"),
        ("s", "stop", "Stop"),
        ("S", "stop", "Stop"),
        ("m", "memory", "Memory"),
        ("o", "output", "Output"),
        ("e", "errors", "Errors"),
        ("escape", "back_to_editor", "Editor"),
        Binding("ctrl+q", "back_to_editor", "Editor", priority=True),
    ]

    def __init__(self, workflow_map, memory_bank, master_state) -> None:
        super().__init__()
        self.workflow_map = workflow_map
        self.memory_bank = memory_bank
        self.master_state = master_state

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical(id="execution-root"):
            yield Label("", id="execution-title")
            with Horizontal(id="execution-columns"):
                with Vertical(id="execution-panel", classes="panel"):
                    yield Label("Execution", classes="panel-title")
                    yield NodeList()
                    yield Static("", id="branch-summary")
                with Vertical(id="memory-output-panel", classes="panel"):
                    yield Label("Memory / Output", classes="panel-title")
                    yield Static("", id="memory-summary")
                    yield Label("Recent Output", classes="panel-title")
                    yield RichLog(
                        id="recent-output",
                        highlight=True,
                        markup=False,
                        wrap=True,
                    )
            yield StatusBar("P pause/resume  S stop  M memory  O output  E errors  ESC stop + editor")

    def on_mount(self) -> None:
        self.refresh_from_backend()

    def on_key(self, event: Key) -> None:
        if event.key.lower() == "s":
            event.stop()
            self.action_stop()

    def refresh_from_backend(self) -> None:
        app = self.app
        state = getattr(app, "workflow_state", "IDLE")
        run_id = self.master_state.current_run_id or "-"
        self.query_one("#execution-title", Label).update(
            f"Workflow: {self.workflow_map.workflow_name} [{state} / {run_id}]"
        )
        self.query_one(NodeList).refresh_nodes(
            self.workflow_map.get_all_node_data(),
            getattr(app, "node_statuses", {}),
            getattr(app, "node_timings", {}),
        )
        self.query_one("#branch-summary", Static).update(self._format_branches())
        self.query_one("#memory-summary", Static).update(self._format_memory())
        self._refresh_output_log()

    def action_pause_resume(self) -> None:
        state = getattr(self.app, "workflow_state", "IDLE")
        if state == "RUNNING":
            self.master_state.pause()
        elif state == "PAUSED":
            self.master_state.resume()

    def action_stop(self) -> None:
        self.master_state.stop()
        self.app.workflow_state = "IDLE"
        self.app.notify("Workflow stopped")
        self.refresh_from_backend()

    def action_memory(self) -> None:
        self.app.push_screen(MemoryViewerScreen(self.memory_bank))

    def action_output(self) -> None:
        self.app.push_screen(OutputViewerScreen(self._current_outputs()))

    def action_errors(self) -> None:
        errors = []
        run_id = self.master_state.current_run_id
        if run_id:
            errors = self.master_state.error_handler.get_errors_for_run(run_id)
        if not errors:
            self.app.notify("No errors for this run")
            return
        self.app.push_screen(ErrorDetailsScreen({"error": errors[-1], "options": []}))

    def action_back_to_editor(self) -> None:
        self.app.show_editor_screen()

    def _format_branches(self) -> str:
        supervisors = getattr(self.app, "supervisors", {})
        if not supervisors:
            return "Branches:\n  -"
        lines = ["Branches:"]
        for branch_id, data in supervisors.items():
            state = data.get("state", "-")
            current = data.get("current_node_id") or "-"
            depth = data.get("depth", 0)
            lines.append(f"  {branch_id} depth {depth}: {state} on {current}")
        return "\n".join(lines)

    def _format_memory(self) -> str:
        state = self.memory_bank.get_state()
        persistent = state.get("persistent", {})
        transient = state.get("transient", {})
        lines = ["Memory:"]
        if not persistent and not transient:
            lines.append("  -")
            return "\n".join(lines)
        for key, value in persistent.items():
            lines.append(f"  {key}: {value}")
        if transient:
            lines.append(f"  transient ports: {len(transient)}")
        return "\n".join(lines)

    def _refresh_output_log(self) -> None:
        outputs = self._current_outputs()
        output_log = self.query_one("#recent-output", RichLog)
        output_log.clear()
        if not outputs:
            output_log.write("-")
            return
        records = normalize_outputs(outputs)
        for record in records[-12:]:
            output_log.write(Text(format_output_record(record)))

    def _current_outputs(self) -> list:
        memory_outputs = self.memory_bank.read_persistent("output_log", default=[])
        outputs = list(memory_outputs or [])
        if outputs:
            return outputs
        outputs = list(getattr(self.master_state, "run_outputs", []) or [])
        run_id = self.master_state.current_run_id
        if not outputs and run_id:
            outputs = self.master_state.output_manager.get_outputs_for_run(run_id)
        return outputs
