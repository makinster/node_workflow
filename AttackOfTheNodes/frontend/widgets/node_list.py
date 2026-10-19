"""Node list widget for editor and execution screens."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.widgets import Label, ListItem, ListView

from .node_card import (
    BranchSelectCard,
    GapArrowCard,
    MergeBeaconSelectCard,
    NodeCard,
)


class NodeList(ListView):
    """A selectable vertical list of workflow nodes."""

    def __init__(self) -> None:
        super().__init__(id="node-list")
        self._rows: list[Dict[str, Any]] = []
        self._run_status: Optional[Dict[str, str]] = None

    def refresh_nodes(
        self,
        nodes: Dict[str, Dict[str, Any]],
        statuses: Optional[Dict[str, str]] = None,
        timings: Optional[Dict[str, float]] = None,
        reasons: Optional[Dict[str, str]] = None,
    ) -> None:
        """Update execution cards; rebuild only when node IDs/order change."""
        statuses = statuses or {}
        timings = timings or {}
        reasons = reasons or {}
        # Execution events change status/timing far more often than graph shape.
        # Keep mounted cards stable so highlights and scroll survive updates.
        cards = list(self.query(NodeCard))
        if cards and [card.node_id for card in cards] == list(nodes):
            for card in cards:
                card.node_data = nodes[card.node_id]
                card.status = statuses.get(card.node_id, "idle")
                card.status_detail = reasons.get(card.node_id, "")
                card.timing_seconds = timings.get(card.node_id)
                card.refresh_card()
            return
        self.clear()
        self._rows = [
            {"kind": "node", "node_id": node_id, "node": node_data}
            for node_id, node_data in nodes.items()
        ]
        for node_id, node_data in nodes.items():
            card = NodeCard(
                node_id,
                node_data,
                statuses.get(node_id, "idle"),
                timings.get(node_id),
                show_id=False,  # owner, 2026-10-14: names, not IDs, on cards
            )
            if reasons.get(node_id):
                card.status_detail = reasons[node_id]
                card.refresh_card()
            self.append(ListItem(card))
        if not nodes:
            self.append(ListItem(Label("No nodes. Press I to add a node.")))

    def refresh_rows(
        self,
        rows: list[Dict[str, Any]],
        statuses: Optional[Dict[str, str]] = None,
        timings: Optional[Dict[str, float]] = None,
        flagged_node_ids: Optional[set] = None,
        run_status: Optional[Dict[str, str]] = None,
    ) -> None:
        """Replace the list contents with node and branch selector rows.

        ``run_status`` (EX) puts each node's run status on its card's second
        line; with it, a refresh whose rows are unchanged updates the cards in
        place, so the highlight and scroll survive every run event."""
        statuses = statuses or {}
        timings = timings or {}
        flagged_node_ids = flagged_node_ids or set()
        self._run_status = run_status
        if run_status is not None and self._same_rows(rows):
            self.update_run_status(statuses, run_status)
            return
        self.clear()
        self._rows = []
        for index, row in enumerate(rows):
            next_kind = (
                rows[index + 1]["kind"]
                if index + 1 < len(rows)
                else None
            )
            self._append_row(row, statuses, timings, flagged_node_ids)
            if row["kind"] == "node" and next_kind == "node":
                next_row = rows[index + 1]
                next_node = next_row.get("node") or {}
                branch_port = (
                    row.get("node", {}).get("_editor_branch_port")
                    or next_node.get("_editor_branch_port")
                )
                branch_color_key = (
                    row.get("node", {}).get("_editor_branch_color_key")
                    or next_node.get("_editor_branch_color_key")
                )
                output_marker = row.get("node", {}).get("_editor_gap_marker")
                gap_row = {
                    "kind": "gap_arrow",
                    "after_node_id": row["node_id"],
                    "branch_port": branch_port,
                    "branch_color_key": branch_color_key,
                    "output_marker": output_marker,
                }
                self._rows.append(gap_row)
                self.append(
                    ListItem(
                        GapArrowCard(
                            branch_port=branch_port,
                            branch_color_key=branch_color_key,
                            output_marker=output_marker,
                        )
                    )
                )
        if not rows:
            self.append(ListItem(Label("No nodes. Press I to add a node.")))
        self.normalize_highlight()
        self.call_after_refresh(self.normalize_highlight)

    def _append_row(
        self,
        row: Dict[str, Any],
        statuses: Dict[str, str],
        timings: Dict[str, float],
        flagged_node_ids: Optional[set] = None,
    ) -> None:
        """Append one selectable row and keep `_rows` aligned to ListView items."""
        self._rows.append(row)
        if row["kind"] == "node":
            node_id = row["node_id"]
            card = NodeCard(
                node_id,
                row["node"],
                statuses.get(node_id, "idle"),
                timings.get(node_id),
                show_status=False,
                show_id=False,
                show_identity=True,
                has_warning=node_id in (flagged_node_ids or set()),
            )
            run_status = getattr(self, "_run_status", None)
            if run_status is not None:
                card.run_status_text = run_status.get(node_id, "not started")
        elif row["kind"] == "branch_select":
            card = BranchSelectCard(
                row["branch_node_id"],
                row["active_port"],
                row.get("active_label"),
                row.get("depth"),
                row.get("active_color_key"),
            )
        else:
            card = MergeBeaconSelectCard(
                row["beacon_node_id"],
                row.get("active_label"),
                row.get("depth"),
                row.get("active_port"),
                row.get("active_color_key"),
            )
        self.append(ListItem(card))

    def _row_key(self, row: Dict[str, Any]) -> tuple:
        return (row.get("kind"), row.get("node_id"), row.get("branch_node_id"),
                row.get("active_port"), row.get("beacon_node_id"))

    def _same_rows(self, rows: list[Dict[str, Any]]) -> bool:
        current = [self._row_key(row) for row in self._rows if row.get("kind") != "gap_arrow"]
        return bool(current) and current == [self._row_key(row) for row in rows]

    def update_run_status(self, statuses: Dict[str, str], run_status: Dict[str, str]) -> None:
        """Refresh each card's status line in place (EX)."""
        for card in self.query(NodeCard):
            card.status = statuses.get(card.node_id, "idle")
            text = run_status.get(card.node_id, "not started")
            if card.run_status_text != text:
                card.run_status_text = text
                card.refresh_card()

    def node_id_for_index(self, index: int | None) -> Optional[str]:
        """Return the node id matching a ListView index."""
        row = self.row_for_index(index)
        if not row or row["kind"] != "node":
            return None
        return row["node_id"]

    def row_for_index(self, index: int | None) -> Optional[Dict[str, Any]]:
        """Return the row descriptor matching a ListView index."""
        if index is None or index < 0 or index >= len(self._rows):
            return None
        return self._rows[index]

    def is_selectable_index(self, index: int | None) -> bool:
        """Return true when index points at a selectable workflow row."""
        row = self.row_for_index(index)
        return bool(row and row.get("kind") != "gap_arrow")

    def next_selectable_index(self, current: int, delta: int) -> Optional[int]:
        """Return the next selectable index, skipping disabled gap arrows."""
        if not self._rows:
            return None
        if delta == 0:
            return current if self.is_selectable_index(current) else None
        step = 1 if delta >= 0 else -1
        index = current
        while True:
            index = max(0, min(len(self._rows) - 1, index + step))
            if self.is_selectable_index(index):
                return index
            if index == 0 or index == len(self._rows) - 1:
                return current if self.is_selectable_index(current) else None

    def index_for_node_id(self, node_id: str) -> Optional[int]:
        """Return the first row index for a node id."""
        for index, row in enumerate(self._rows):
            if row["kind"] == "node" and row["node_id"] == node_id:
                return index
        return None

    def index_for_branch_select(
        self, branch_node_id: str, active_port: str
    ) -> Optional[int]:
        """Return the row index for a branch selector row."""
        for index, row in enumerate(self._rows):
            if (
                row["kind"] == "branch_select"
                and row.get("branch_node_id") == branch_node_id
                and row.get("active_port") == active_port
            ):
                return index
        return None

    def index_for_merge_beacon_select(self, beacon_node_id: str) -> Optional[int]:
        """Return the row index for a merge-beacon selector row."""
        for index, row in enumerate(self._rows):
            if (
                row["kind"] == "merge_beacon_select"
                and row.get("beacon_node_id") == beacon_node_id
            ):
                return index
        return None

    def normalize_highlight(self) -> None:
        """Ensure only the current ListView index renders as highlighted."""
        for index, item in enumerate(self.children):
            if isinstance(item, ListItem):
                is_highlighted = index == self.index
                item.highlighted = is_highlighted
                item.styles.background = "#101418"
                for card in item.children:
                    if not isinstance(
                        card,
                        (NodeCard, BranchSelectCard, MergeBeaconSelectCard),
                    ):
                        continue
                    was_selected = card.has_class("selected")
                    card.set_class(is_highlighted, "selected")
                    if was_selected != is_highlighted:
                        card.refresh_card()

    def watch_index(self, old_index: int | None, new_index: int | None) -> None:
        """Keep child-card selection in sync with Textual's ListView cursor."""
        if new_index is not None and not self.is_selectable_index(new_index):
            selectable = self.next_selectable_index(new_index, 1)
            if selectable is None:
                selectable = self.next_selectable_index(new_index, -1)
            if selectable is not None:
                self.index = selectable
                return
        super().watch_index(old_index, new_index)
        self.normalize_highlight()
