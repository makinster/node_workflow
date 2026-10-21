"""Execution screen: the run on the workflow map (EX, owner samples 2026-10-19).

The left pane is the editor's map, built by the editor's own row code, with
each card's second line showing how that node is doing. The right pane shows
the highlighted node: its status, what it got, what it sent, what it wrote
to the Vault and, for a Subworkflow node, the call. The highlight follows the
running node until W/S move it; F follows again. A/D switch the nearest
branch above the highlight. A node waiting for a recovery choice opens the
error panel at the top of the right pane; V hides and shows it, and Go to
node highlights the failed node. X stops the run.
"""

from __future__ import annotations

from time import monotonic
from typing import Any, Dict, List, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from frontend import colors, notifications
from frontend.io_contract import TYPE_COLOR
from frontend.keymap import EXECUTION, bindings_for, screen_hint_for
from frontend.keymap_runtime import KeymapScreenMixin
from frontend.node_io_display import node_display_name
from frontend.output_records import normalize_outputs
from frontend.screens.error_details import ErrorDetailsScreen
from frontend.screens.output_viewer import OutputViewerScreen
from frontend.error_mux_ui import friendly_error_name
from frontend.screens.vault_log import VaultLogScreen, kind_of, shorten, value_text
from frontend.widgets.node_list import NodeList
from frontend.widgets.status_bar import StatusBar

from frontend.colors import ERROR as RED, MUTED as DIM, RUNNING as CYAN, SUCCESS as GREEN, WARNING as YELLOW  # noqa: E402
NARROW_WIDTH = 80
_MISSING = object()

STATUS_TEXT = {
    "running": ("▶ running", CYAN),
    "waiting": ("⏸ waiting for you", YELLOW),
    "done": ("✓ done", GREEN),
    "errored": ("✗ error", RED),
    "recovered": ("↺ recovered", YELLOW),
    "skipped": ("skipped", DIM),
    "stopped": ("stopped", DIM),
}


def seconds_text(seconds: Optional[float]) -> str:
    if not seconds:
        return ""
    return f"{seconds:.2f}s" if seconds < 10 else f"{seconds:.1f}s"


class ExecutionScreen(KeymapScreenMixin, Screen):
    """Live workflow execution view."""

    KEYMAP = EXECUTION
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, workflow_map, memory_bank, master_state, call=None) -> None:
        super().__init__()
        self.workflow_map = workflow_map
        self.memory_bank = memory_bank
        self.master_state = master_state
        # 4c-2: a running subworkflow call (``frontend.child_runs.ChildRun``)
        # shown the same way; None for the root run.
        self.call = call
        # The editor builds the map rows; an editor screen that is never shown
        # keeps the path shown at each branch node (A/D) as the editor would.
        from frontend.screens.editor import EditorScreen

        self._map = EditorScreen(workflow_map._factory, workflow_map)
        self.follow = True
        self._selected: Optional[tuple] = None
        self._recoveries: List[Dict[str, Any]] = []
        self._panel_hidden = False
        self._started: Optional[float] = None
        self._ended: Optional[float] = None

    # -- layout ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Static("", id="execution-title")
        with Horizontal(id="execution-columns"):
            with Vertical(id="execution-panel", classes="panel"):
                yield Label("Run", classes="panel-title")
                yield NodeList()
            with Vertical(id="execution-side", classes="panel"):
                with Vertical(id="execution-error"):
                    yield Static("", id="execution-error-text")
                    with Horizontal(classes="button-row"):
                        yield Button("Retry", id="recover-RETRY", variant="primary", compact=True)
                        yield Button("Skip", id="recover-SKIP", compact=True)
                        yield Button("Stop branch", id="recover-TERMINATE_BRANCH", compact=True)
                    with Horizontal(classes="button-row"):
                        yield Button("Go to node", id="recover-goto", compact=True)
                        yield Button("Stop run", id="recover-TERMINATE_WORKFLOW", compact=True)
                        yield Button("Details", id="recover-details", compact=True)
                yield Static("", id="execution-details")
                yield Label("Output", classes="panel-title")
                yield Static("", id="execution-output", markup=False)
        yield StatusBar(screen_hint_for(self.KEYMAP, keymap=getattr(self.app, "_keymap", None)))

    def on_mount(self) -> None:
        self.query_one("#execution-error").display = False
        self.refresh_from_backend()
        self.query_one(NodeList).focus()

    def on_screen_resume(self) -> None:
        if self.is_mounted:
            self.refresh_from_backend()

    def on_resize(self, event) -> None:
        self.set_class(event.size.width < NARROW_WIDTH, "narrow")

    # -- refresh -------------------------------------------------------------------

    @property
    def _source(self) -> Any:
        """Where run status comes from: the call's record, or the app."""
        return self.call if self.call is not None else self.app

    @property
    def _run_id(self) -> Optional[str]:
        return self.call.run_id if self.call is not None else self.master_state.current_run_id

    def _root_master(self) -> Any:
        return getattr(self.app, "master_state", None) or self.master_state

    def refresh_from_backend(self) -> None:
        app = self._source
        state = str(getattr(app, "workflow_state", "IDLE"))
        if state in {"RUNNING", "PAUSED", "WAITING_FOR_INPUT"}:
            self._started = self._started or monotonic()
            self._ended = None
        elif self._started is not None and self._ended is None:
            self._ended = monotonic()
        self._drop_stale_recoveries(state)
        statuses = dict(getattr(app, "node_statuses", {}) or {})
        timings = dict(getattr(app, "node_timings", {}) or {})
        rows = self._map._build_visible_rows()
        node_list = self.query_one(NodeList)
        node_list.refresh_rows(rows, statuses, timings, run_status=self._status_lines(statuses, timings))
        self._place_highlight(node_list)
        self._refresh_title(state)
        self._refresh_details()
        self._refresh_error_panel()
        self._refresh_output()

    def _execution_state(self):
        return getattr(self._source, "execution_state", None)

    def _branches(self) -> Dict[str, Dict[str, Any]]:
        state = self._execution_state()
        return dict(state.branches) if state is not None else {}

    def _branch_numbers(self) -> Dict[str, Optional[int]]:
        """Branch 1, 2... in start order for the paths that split off; the
        main path (depth 0) has no number."""
        numbers: Dict[str, Optional[int]] = {}
        count = 0
        for branch_id, branch in self._branches().items():
            if int(branch.get("depth") or 0) == 0:
                numbers[branch_id] = None
            else:
                count += 1
                numbers[branch_id] = count
        return numbers

    def _visits_for(self, node_id: str) -> List[tuple]:
        """``(branch_number, visit_index, visit)`` for every visit of a node;
        the branch number is None on the main path."""
        numbers = self._branch_numbers()
        found = []
        for branch_id, branch in self._branches().items():
            for index, visit in sorted((branch.get("visits") or {}).items()):
                if visit.get("node_id") == node_id:
                    found.append((numbers.get(branch_id), index, visit))
        return found

    def _step_of(self, node_id: str) -> Optional[int]:
        """The node's step number: its distance from Start, as on the map."""
        start = self.workflow_map.find_start_node_id()
        if not start:
            return None
        nodes = self.workflow_map.get_all_node_data()
        depth, frontier = {start: 0}, [start]
        while frontier:
            following = []
            for current in frontier:
                for conn in (nodes.get(current) or {}).get("connections", {}).get("outputs", []):
                    target = conn.get("target_node_id")
                    if target in nodes and target not in depth:
                        depth[target] = depth[current] + 1
                        following.append(target)
            frontier = following
        return depth.get(node_id)

    def _status_lines(self, statuses: Dict[str, str], timings: Dict[str, float]) -> Dict[str, str]:
        lines: Dict[str, str] = {}
        reasons = dict(getattr(self._source, "node_skip_reasons", {}) or {})
        for node_id, status in statuses.items():
            label, _ = STATUS_TEXT.get(status, ("not started", DIM))
            if status in {"skipped", "recovered"} and reasons.get(node_id):
                label = f"{label}: {str(reasons[node_id]).replace('_', ' ')}"
            visits = self._visits_for(node_id)
            if status == "errored":
                label = "✗ " + friendly_error_name(self._error_for(node_id).get("code") or "node_error")
            if status == "running" and any(self._waits(call) for call in self._calls_at(node_id)):
                label, status = STATUS_TEXT["waiting"][0], "waiting"
            if status not in {"running", "waiting"}:
                timing = seconds_text(timings.get(node_id))
                label = f"{label}  {timing}" if timing else label
            tries = max((len(visit.get("attempts") or {}) for _, _, visit in visits), default=0)
            if len(visits) > 1:
                label += f"  · {len(visits)} runs"
            elif tries > 1:
                label += f"  · {tries} tries"
            lines[node_id] = label
        return lines

    # -- highlight and follow --------------------------------------------------------

    def _row_key(self, row: Optional[Dict[str, Any]]) -> Optional[tuple]:
        if not row:
            return None
        if row["kind"] == "node":
            return ("node", row["node_id"])
        if row["kind"] == "branch_select":
            # The live path selector and its Saved paths row share a branch node.
            return ("branch", row["branch_node_id"], row["active_port"] if row.get("saved_paths") else "live")
        if row["kind"] == "merge_beacon_select":
            return ("beacon", row["beacon_node_id"])
        return None

    def _live_node(self) -> Optional[str]:
        """The node to follow: one waiting for a choice, then for input, then running."""
        if self._recoveries:
            return str(self._recoveries[0].get("node_id") or "") or None
        branches = list(self._branches().values())
        for wanted in ("WAITING_FOR_INPUT", "AWAITING_RECOVERY", "RUNNING"):
            for branch in branches:
                if branch.get("state") == wanted and branch.get("current_node_id"):
                    return str(branch["current_node_id"])
        return None

    def _place_highlight(self, node_list: NodeList) -> None:
        index = None
        if self.follow:
            live = self._live_node()
            if live is not None:
                index = node_list.index_for_node_id(live)
                # Following shows the followed node's path; A/D and W/S stop following.
                if index is None:
                    self._show_path_to(live)
                    source = self._source
                    node_list.refresh_rows(self._map._build_visible_rows(), dict(source.node_statuses or {}),
                                           dict(source.node_timings or {}),
                                           run_status=self._status_lines(dict(source.node_statuses or {}),
                                                                         dict(source.node_timings or {})))
                    index = node_list.index_for_node_id(live)
        if index is None and self._selected is not None:
            for position, row in enumerate(node_list._rows):
                if self._row_key(row) == self._selected:
                    index = position
                    break
        if index is None:
            index = node_list.index if node_list.index is not None else 0
            if not node_list.is_selectable_index(index):
                index = node_list.next_selectable_index(index, 1) or 0
        if node_list.index != index:
            node_list.index = index
        node_list.normalize_highlight()
        self._selected = self._row_key(node_list.row_for_index(index))

    def _move(self, delta: int) -> None:
        node_list = self.query_one(NodeList)
        current = node_list.index if node_list.index is not None else 0
        target = node_list.next_selectable_index(current, delta)
        if target is None:
            return
        self.follow = False
        node_list.index = target
        node_list.normalize_highlight()
        node_list.scroll_visible(animate=False)
        self._selected = self._row_key(node_list.row_for_index(target))
        self._refresh_details()
        self._refresh_hint()

    def on_list_view_highlighted(self, _event) -> None:
        """Remember a highlight set by a click (or by refresh) so the next
        refresh keeps it; only W/S and A/D stop following."""
        node_list = self.query_one(NodeList)
        key = self._row_key(node_list.row_for_index(node_list.index))
        if key is not None and key != self._selected:
            self._selected = key
            self._refresh_details()

    def action_cursor_up(self) -> None:
        self._move(-1)

    def action_cursor_down(self) -> None:
        self._move(1)

    def action_follow(self) -> None:
        self.follow = True
        self.refresh_from_backend()
        notifications.notify_info(self.app, "Following the run")

    def action_branch(self, delta: int) -> None:
        """Switch the path shown at the nearest branch at or above the highlight."""
        node_list = self.query_one(NodeList)
        rows = node_list._rows
        if not rows:
            return
        index = node_list.index if node_list.index is not None else 0
        for position in range(min(index, len(rows) - 1), -1, -1):
            row = rows[position]
            if row.get("kind") == "branch_select" and len(row.get("output_ports") or []) > 1:
                ports = list(row["output_ports"])
                active = self._map.active_branch_ports.get(row["branch_node_id"], row["active_port"])
                position_in = ports.index(active) if active in ports else 0
                self._map.active_branch_ports[row["branch_node_id"]] = ports[(position_in + int(delta)) % len(ports)]
                self.follow = False
                self._selected = self._row_key(row)
                self.refresh_from_backend()
                return

    # -- title, details, output ------------------------------------------------------

    def _refresh_title(self, state: str) -> None:
        words = {"RUNNING": ("▶ running", CYAN), "PAUSED": ("⏸ paused", YELLOW),
                 "WAITING_FOR_INPUT": ("⏸ waiting for you", YELLOW), "FINISHED": ("✓ finished", GREEN),
                 "ERROR": ("✗ failed", RED), "IDLE": ("stopped", DIM)}
        if state == "RUNNING" and self._call_below_waits():
            state = "WAITING_FOR_INPUT"  # a subworkflow this run called waits for you
        word, colour = words.get(state, (state.lower(), DIM))
        if self.call is not None:
            title = self._breadcrumbs(max(20, (self.size.width or 100) - 40))
            title.append("   ")
        else:
            title = Text(f"{self.workflow_map.workflow_name}   ")
        if self._recoveries:
            if self._panel_hidden:
                count = len(self._recoveries)
                title.append(f"⚠ {count} error{'s' if count > 1 else ''} waiting · v to choose",
                             style=f"bold {YELLOW}")
            else:
                title.append("⚠ needs you", style=f"bold {YELLOW}")
        else:
            title.append(word, style=f"bold {colour}")
        branches = [b for b in self._branches().values() if int(b.get("depth") or 0) > 0]
        if branches:
            running = sum(1 for b in branches if b.get("state") in {"RUNNING", "WAITING_FOR_INPUT", "PAUSED",
                                                                  "AWAITING_RECOVERY"})
            title.append(f"   {len(branches)} branches · {running} running · {len(branches) - running} done")
        if self._started is not None:
            elapsed = (self._ended or monotonic()) - self._started
            title.append(f"   {int(elapsed) // 60}:{int(elapsed) % 60:02d}")
        self.query_one("#execution-title", Static).update(title)

    def _error_for(self, node_id: str) -> Dict[str, Any]:
        for payload in self._recoveries:
            if payload.get("node_id") == node_id:
                return dict(payload.get("error") or {}, code=payload.get("code"))
        run_id = self.master_state.current_run_id
        errors = self.master_state.error_handler.get_errors_for_run(run_id) if run_id else []
        for error in reversed(errors or []):
            if error.get("node_id") == node_id:
                return error
        return {}

    def _value_line(self, label: str, value: Any) -> Text:
        line = Text("  ")
        if label:
            line.append(label, style=colors.PAYLOAD)
            line.append("  ")
        line.append(f"[{kind_of(value)}]", style=TYPE_COLOR)
        line.append(f"  {shorten(value_text(value), 46)}", style=colors.VALUE)
        return line

    def _refresh_details(self) -> None:
        node_list = self.query_one(NodeList)
        row = node_list.row_for_index(node_list.index)
        text = Text()
        if row and row["kind"] == "branch_select":
            branch_node = self.workflow_map.get_node_data(row["branch_node_id"]) or {}
            text.append(f"{row.get('active_label') or row['active_port']}\n", style="bold")
            text.append(f"One of {len(row.get('output_ports') or [])} paths from "
                        f"{node_display_name(row['branch_node_id'], branch_node)}. a/d shows another.\n",
                        style=DIM)
        elif row and row["kind"] == "node":
            text = self._node_details(row)
        self.query_one("#execution-details", Static).update(text)

    def _node_details(self, row: Dict[str, Any]) -> Text:
        node_id = row["node_id"]
        node = self.workflow_map.get_node_data(node_id) or {}
        status = (getattr(self._source, "node_statuses", {}) or {}).get(node_id, "idle")
        visits = self._visits_for(node_id)
        branch = f" · Branch {visits[-1][0]}" if visits and visits[-1][0] else ""
        text = Text(node_display_name(node_id, node), style=f"bold {colors.NAME}")
        text.append(f" · step {row.get('depth', '-')}{branch}\n", style="bold")
        label, colour = STATUS_TEXT.get(status, ("not started yet", DIM))
        timing = seconds_text((getattr(self._source, "node_timings", {}) or {}).get(node_id))
        call_waits = status == "running" and any(self._waits(call) for call in self._calls_at(node_id))
        if call_waits:
            pass  # the call details lead with "Greeter is waiting for you"
        elif status == "errored":
            error = self._error_for(node_id)
            text.append(f"✗ {friendly_error_name(error.get('code') or 'node_error')}"
                        f"{('  ' + timing) if timing else ''}\n", style=colour)
            text.append(f"  {error.get('message') or ''}\n")
        else:
            text.append(f"{label[0].upper()}{label[1:]}{('  ' + timing) if timing else ''}\n", style=colour)
        attempts = [attempt for _, _, visit in visits
                    for _, attempt in sorted((visit.get("attempts") or {}).items())]
        if len(attempts) > 1:
            text.append("\nTries\n", style="bold")
            for count, attempt in enumerate(attempts, start=1):
                state = attempt.get("status", "")
                mark, tone = STATUS_TEXT.get(state, (state, DIM))
                text.append(f"  {count}  {mark}  {seconds_text(attempt.get('seconds'))}\n", style=tone)
        if node.get("type") == "subworkflow_node":
            text.append_text(self._call_details(node_id, node, status))
        text.append("\nReceived from the previous node\n", style="bold")
        self._append_values(text, self._inputs_of(node))
        text.append("Sent to the next node\n", style="bold")
        self._append_values(text, self._outputs_of(node_id))
        text.append("Saved to the Vault\n", style="bold")
        writes = [w for w in self.memory_bank.writes() if w.get("node_id") == node_id]
        for write in writes[-4:]:
            text.append(f"  {write.get('key')} = {shorten(value_text(write.get('value')), 36)}  ")
            text.append(f"[{write.get('type') or kind_of(write.get('value'))}]\n", style=TYPE_COLOR)
        if not writes:
            text.append("  nothing\n", style=DIM)
        return text

    def _append_values(self, text: Text, values: List[tuple]) -> None:
        if not values:
            text.append("  nothing yet\n", style=DIM)
        for name, value in values:
            text.append_text(self._value_line(name, value))
            text.append("\n")

    def _inputs_of(self, node: Dict[str, Any]) -> List[tuple]:
        found = []
        for conn in (node.get("connections") or {}).get("inputs", []):
            value = self.memory_bank.read_transient(conn.get("source_node_id"), conn.get("source_port", "default"),
                                                    default=_MISSING)
            if value is not _MISSING:
                found.append(("", value))
        return found

    def _outputs_of(self, node_id: str) -> List[tuple]:
        found = []
        for port in self.workflow_map.output_ports(node_id) or ["default"]:
            value = self.memory_bank.read_transient(node_id, port, default=_MISSING)
            if value is not _MISSING:
                found.append(("" if port == "default" else port, value))
        return found

    # -- subworkflow calls (4c-2, owner samples 2026-10-20) ---------------------------

    def _calls_at(self, node_id: str) -> list:
        """The live calls this run's node ``node_id`` started."""
        calls = getattr(self.app, "child_runs", None)
        return calls.at(self._run_id, node_id) if calls is not None and self._run_id else []

    def _child_master(self, call) -> Any:
        tree = getattr(self._root_master(), "call_tree", None)
        for child in (tree.live_masters() if tree is not None else []):
            if child.current_run_id == call.run_id:
                return child
        return None

    def _now_at(self, call) -> List[str]:
        child = self._child_master(call)
        if child is None:
            return []
        names = []
        for branch in call.execution_state.branches.values():
            node_id = branch.get("current_node_id")
            if node_id and branch.get("state") not in {"TERMINATED", "IDLE", "ERROR"}:
                name = node_display_name(node_id, child.workflow_map.get_node_data(node_id) or {})
                if name not in names:
                    names.append(name)
        return names

    def _call_details(self, node_id: str, node: Dict[str, Any], status: str) -> Text:
        from frontend import subworkflow_info

        text = Text()
        calls = self._calls_at(node_id)
        child = subworkflow_info.describe(str((node.get("config") or {}).get("workflow_id") or ""))
        name = (calls[0].call_path[-1] if calls and calls[0].call_path else (child or {}).get("name")) or "?"
        if calls:
            calls.sort(key=lambda call: not self._waits(call))
            where = ", ".join(self._now_at(calls[0]))
            waiting = self._waiting_inside(calls[0])
            if waiting is calls[0]:
                text.append(f"⏸ {name} is waiting for you" + (f" at {where}" if where else "") + "\n",
                            style=YELLOW)
            elif waiting is not None:
                inner = waiting.call_path[-1] if waiting.call_path else "a subworkflow"
                at = ", ".join(self._now_at(waiting))
                text.append(f"⏸ {name} is waiting for you (in {inner}" + (f", at {at}" if at else "") + ")\n",
                            style=YELLOW)
            text.append(f"\nRuns {name} [sub]\n", style="bold")
            if where:
                text.append(f"  now at: {where}\n")
            text.append("  e/enter  open it\n", style=DIM)
        elif status in {"done", "errored", "stopped", "recovered"}:
            text.append(f"\nRan {name} [sub]\n", style="bold")
            text.append("  finished\n" if status == "done" else "  ended\n")
        else:
            text.append(f"\nRuns {name} [sub]\n", style="bold")
        return text

    def _waiting_inside(self, call):
        calls = getattr(self.app, "child_runs", None)
        return calls.waiting_inside(call) if calls is not None else (call if call.waiting else None)

    def _waits(self, call) -> bool:
        """The call, or one it made (at any depth), waits for you."""
        return self._waiting_inside(call) is not None

    def _call_below_waits(self) -> bool:
        """A call made from this view's run (at any depth) waits for you;
        followed by run ids, so parallel calls with the same names stay apart."""
        calls = getattr(self.app, "child_runs", None)
        if calls is None or not self._run_id:
            return False
        return any(self._waits(call) for call in calls.children_of(self._run_id))

    def _highlighted_call(self):
        node_list = self.query_one(NodeList)
        row = node_list.row_for_index(node_list.index)
        if not row or row.get("kind") != "node":
            return None, None
        node = self.workflow_map.get_node_data(row["node_id"]) or {}
        if node.get("type") != "subworkflow_node":
            return None, None
        calls = self._calls_at(row["node_id"])
        calls.sort(key=lambda call: not self._waits(call))  # one that needs you first
        return row["node_id"], (calls[0] if calls else None)

    def action_open_call(self) -> None:
        """Enter: open the highlighted node's running subworkflow."""
        node_id, call = self._highlighted_call()
        if node_id is None:
            return
        child = self._child_master(call) if call is not None else None
        if child is None:
            notifications.notify_info(self.app, "That subworkflow isn't running")
            return
        self.app.push_screen(ExecutionScreen(child.workflow_map, child.memory_bank, child, call=call))

    def action_open_or_errors(self) -> None:
        """E: open a running subworkflow on its card, otherwise show the errors."""
        node_id, call = self._highlighted_call()
        if call is not None and self._child_master(call) is not None:
            self.action_open_call()
        else:
            self.action_errors()

    def on_list_view_selected(self, event) -> None:
        """Enter on the map opens a running call (the binding is not a
        priority one, so a focused error-panel button still gets its Enter)."""
        event.stop()
        self.action_open_call()

    def _breadcrumbs(self, width: int) -> Text:
        """Fetch report › Greet › Greeter, shortened to fit: the first name,
        "…", then as many of the last names as fit (owner, 2026-10-20)."""
        path = list(self.call.call_path) if self.call is not None else [self.workflow_map.workflow_name]

        def build(kept: int) -> Text:
            names = path if kept >= len(path) - 1 else [path[0], "…"] + path[-kept:]
            out = Text()
            for index, name in enumerate(names):
                if index:
                    out.append(" › ", style=DIM)
                out.append(str(name), style="bold" if index == len(names) - 1 else DIM)
            if len(names) < len(path):
                out.append(f"   (level {(len(path) - 1) // 2})", style=DIM)
            return out

        for kept in range(len(path) - 1, 0, -1):
            text = build(kept)
            if text.cell_len <= width:
                return text
        # Still too long: shorten the first and last names themselves.
        def clip(name: str, room: int) -> str:
            return name if len(name) <= room else name[:max(1, room - 1)] + "…"

        level = f"   (level {(len(path) - 1) // 2})" if len(path) > 2 else ""
        room = max(4, width - len(level) - (len(" › … › ") if len(path) > 2 else len(" › ")))
        first, last = str(path[0]), str(path[-1])
        last = clip(last, max(room // 2, room - len(first)))
        first = clip(first, max(1, room - len(last)))
        out = Text(first, style=DIM)
        if len(path) > 2:
            out.append(" › … › ", style=DIM)
        elif len(path) == 2:
            out.append(" › ", style=DIM)
        out.append(last, style="bold")
        out.append(level, style=DIM)
        return out

    def _refresh_output(self) -> None:
        outputs = self._current_outputs()
        lines = [str(record.get("value", "")) for record in normalize_outputs(outputs)[-4:]] if outputs else []
        self.query_one("#execution-output", Static).update("\n".join(lines) or "-")

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

    # -- the error panel -----------------------------------------------------------------

    def add_recovery(self, payload: Dict[str, Any]) -> None:
        """A node needs a recovery choice: show it in the panel (EX)."""
        self._recoveries.append(dict(payload))
        self._panel_hidden = False
        if self.is_mounted:
            self.refresh_from_backend()

    def _drop_stale_recoveries(self, state: str) -> None:
        """A finished run, or a stopped branch, no longer waits for a choice."""
        if not self._recoveries:
            return
        if self._ended is not None and state in {"FINISHED", "ERROR", "IDLE"}:
            self._recoveries.clear()
            return
        branches = self._branches()
        self._recoveries = [p for p in self._recoveries
                            if (branches.get(str(p.get("branch_id") or "")) or {}).get("state") != "TERMINATED"]

    @property
    def pending_recoveries(self) -> List[Dict[str, Any]]:
        return list(self._recoveries)

    def _refresh_error_panel(self) -> None:
        panel = self.query_one("#execution-error")
        panel.display = bool(self._recoveries) and not self._panel_hidden
        if self._recoveries:
            payload = self._recoveries[0]
            node_id = str(payload.get("node_id") or "")
            name = node_display_name(node_id, self.workflow_map.get_node_data(node_id) or {})
            visits = self._visits_for(node_id)
            text = Text()
            more = f"  (1 of {len(self._recoveries)})" if len(self._recoveries) > 1 else ""
            branch = f" · Branch {visits[-1][0]}" if visits and visits[-1][0] else ""
            text.append(f"✗ {name} failed{branch}{more}\n", style=f"bold {RED}")
            text.append(f"{payload.get('error_message') or payload.get('code') or 'Error'}\n")
            text.append("This branch waits for your choice.", style=DIM)
            self.query_one("#execution-error-text", Static).update(text)
        self._refresh_hint()

    def _refresh_hint(self) -> None:
        self.query_one(StatusBar).set_bindings_text(screen_hint_for(
            self.KEYMAP,
            keymap=getattr(self.app, "_keymap", None),
            error_panel_hidden=self._panel_hidden if self._recoveries else None,
            open_call=self._highlighted_call()[1] is not None,
            back_to=self._parent_name(),
        ))

    def _parent_name(self) -> Optional[str]:
        """The workflow Esc goes back to from a call (the one that called it)."""
        if self.call is None:
            return None
        path = self.call.call_path
        return path[-3] if len(path) >= 3 else (path[0] if path else "the workflow")

    def action_error_panel(self) -> None:
        if not self._recoveries:
            return
        self._panel_hidden = not self._panel_hidden
        self.refresh_from_backend()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = str(event.button.id or "")
        if not button_id.startswith("recover-") or not self._recoveries:
            return
        event.stop()
        payload = self._recoveries[0]
        choice = button_id.removeprefix("recover-")
        if choice == "goto":
            self.go_to_node(str(payload.get("node_id") or ""))
            return
        if choice == "details":
            self.app.push_screen(ErrorDetailsScreen(dict(payload, options=[])))
            return
        if choice == "TERMINATE_WORKFLOW":
            self._recoveries.clear()
        else:
            self._recoveries.pop(0)
        self._panel_hidden = False
        self.master_state.submit_recovery_action(str(payload.get("branch_id") or ""), choice)
        self.refresh_from_backend()

    def go_to_node(self, node_id: str) -> None:
        """Hide the panel and highlight ``node_id``, showing its path if needed."""
        self._panel_hidden = True
        self.follow = False
        node_list = self.query_one(NodeList)
        self.refresh_from_backend()
        if node_list.index_for_node_id(node_id) is None:
            self._show_path_to(node_id)
            self.refresh_from_backend()
        index = node_list.index_for_node_id(node_id)
        if index is not None:
            node_list.index = index
            node_list.normalize_highlight()
            node_list.scroll_visible(animate=False)
            self._selected = ("node", node_id)
        self._refresh_details()

    def _show_path_to(self, node_id: str) -> None:
        """Pick, at each branch node, the path that leads to ``node_id``."""
        # One route from Start (the shortest), so a loop's back edge cannot
        # overwrite a choice made earlier on the same route.
        nodes = self.workflow_map.get_all_node_data()
        start = self.workflow_map.find_start_node_id()
        came_from: Dict[str, tuple] = {}
        frontier, seen = [start], {start}
        while frontier and node_id not in seen:
            following = []
            for current in frontier:
                for conn in (nodes.get(current) or {}).get("connections", {}).get("outputs", []):
                    target = conn.get("target_node_id")
                    if target in nodes and target not in seen:
                        seen.add(target)
                        came_from[target] = (current, conn.get("source_port"))
                        following.append(target)
            frontier = following
        current = node_id
        while current in came_from:
            source, port = came_from[current]
            if len(self._map._output_ports_for_node(nodes.get(source) or {})) > 1:
                self._map.active_branch_ports[source] = port
            current = source

    # -- commands ------------------------------------------------------------------------

    def action_pause_resume(self) -> None:
        state = getattr(self.app, "workflow_state", "IDLE")
        root = self._root_master()
        if state in {"RUNNING", "WAITING_FOR_INPUT"}:
            root.pause()
        elif state == "PAUSED":
            root.resume()

    def action_stop(self) -> None:
        self._root_master().stop()
        self._recoveries.clear()
        self.app.workflow_state = "IDLE"
        notifications.workflow_stopped(self.app)
        self.refresh_from_backend()

    def action_memory(self) -> None:
        self.app.push_screen(VaultLogScreen(self.memory_bank.writes(), self.source_label))

    def source_label(self, write: Dict[str, Any]) -> str:
        """``S3B2 Save note``: the map step, the branch number and the node."""
        node_id = write.get("node_id")
        if not node_id:
            return "-"
        step = self._step_of(str(node_id))
        branch = self._branch_numbers().get(write.get("branch_id"))
        name = node_display_name(str(node_id), self.workflow_map.get_node_data(str(node_id)) or {})
        prefix = (f"S{step}" if step is not None else "") + (f"B{branch}" if branch else "")
        return f"{prefix} {name}".strip()

    def action_output(self) -> None:
        self.app.push_screen(OutputViewerScreen(self._current_outputs()))

    def action_errors(self) -> None:
        errors = []
        run_id = self.master_state.current_run_id
        if run_id:
            errors = self.master_state.error_handler.get_errors_for_run(run_id)
        if not errors:
            notifications.no_run_errors(self.app)
            return
        self.app.push_screen(ErrorDetailsScreen({"error": errors[-1], "options": []}))

    def action_back_to_editor(self) -> None:
        if self.call is not None:
            # Inside a call, Esc goes back one level and never stops anything.
            self.app.pop_screen()
            return
        self.app.show_editor_screen()
