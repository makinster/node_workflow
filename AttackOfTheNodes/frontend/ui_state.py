"""Small shared state objects for the Textual frontend."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TuiState:
    """Frontend-only state that mirrors backend ids without owning backend data."""

    selected_node_id: Optional[str] = None
    selected_supervisor_id: Optional[str] = None
    node_statuses: Dict[str, str] = field(default_factory=dict)
    active_panel: str = "nodes"
