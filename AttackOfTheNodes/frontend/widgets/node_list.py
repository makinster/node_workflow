"""Node list widget for editor and execution screens."""

from __future__ import annotations

from typing import Any, Dict, Optional

from textual.widgets import Label, ListItem, ListView

from .node_card import BranchSelectCard, MergeBeaconSelectCard, NodeCard


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
        self._rows = list(rows)
        for row in self._rows:
            if row["kind"] == "node":
                node_id = row["node_id"]
                card = NodeCard(
                    node_id,
                    row["node"],
                    statuses.get(node_id, "idle"),
                    timings.get(node_id),
                    show_status=False,
                    show_id=False,
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
                )
            self.append(ListItem(card))
        if not rows:
            self.append(ListItem(Label("No nodes. Press I to add a node.")))
        self.normalize_highlight()

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
                item.highlighted = index == self.index
