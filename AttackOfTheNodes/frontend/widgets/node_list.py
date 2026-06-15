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

    def refresh_nodes(
        self,
        nodes: Dict[str, Dict[str, Any]],
        statuses: Optional[Dict[str, str]] = None,
        timings: Optional[Dict[str, float]] = None,
    ) -> None:
        """Replace the list contents with current workflow nodes."""
        statuses = statuses or {}
        timings = timings or {}
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
            )
            self.append(ListItem(card))
        if not nodes:
            self.append(ListItem(Label("No nodes. Press I to add a node.")))

    def refresh_rows(
        self,
        rows: list[Dict[str, Any]],
        statuses: Optional[Dict[str, str]] = None,
        timings: Optional[Dict[str, float]] = None,
    ) -> None:
        """Replace the list contents with node and branch selector rows."""
        statuses = statuses or {}
        timings = timings or {}
        self.clear()
        self._rows = []
        for index, row in enumerate(rows):
            next_kind = (
                rows[index + 1]["kind"]
                if index + 1 < len(rows)
                else None
            )
            self._append_row(row, statuses, timings)
            if row["kind"] == "node" and next_kind == "node":
                next_row = rows[index + 1]
                next_node = next_row.get("node") or {}
                branch_port = (
                    row.get("node", {}).get("_editor_branch_port")
                    or next_node.get("_editor_branch_port")
                )
                output_marker = row.get("node", {}).get("_editor_gap_marker")
                gap_row = {
                    "kind": "gap_arrow",
                    "after_node_id": row["node_id"],
                    "branch_port": branch_port,
                    "output_marker": output_marker,
                }
                self._rows.append(gap_row)
                self.append(
                    ListItem(
                        GapArrowCard(
                            branch_port=branch_port,
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
            )
        elif row["kind"] == "branch_select":
            card = BranchSelectCard(
                row["branch_node_id"],
                row["active_port"],
                row.get("active_label"),
                row.get("depth"),
            )
        else:
            card = MergeBeaconSelectCard(
                row["beacon_node_id"],
                row.get("active_label"),
                row.get("depth"),
                row.get("active_port"),
            )
        self.append(ListItem(card))

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
        super().watch_index(old_index, new_index)
        self.normalize_highlight()
