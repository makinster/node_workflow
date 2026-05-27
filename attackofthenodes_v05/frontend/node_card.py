"""
Node card drawing helpers for the tkinter editor.

The Phase 3 editor renders workflow nodes as stacked cards on a Canvas.
"""

from typing import Any, Callable, Dict, Optional, Tuple


CARD_WIDTH = 360
CARD_HEIGHT = 78
CARD_RADIUS = 4


def draw_node_card(
    canvas,
    node_id: str,
    node_data: Dict[str, Any],
    x: int,
    y: int,
    status: str = "idle",
    on_click: Optional[Callable[[str], None]] = None,
    on_delete: Optional[Callable[[str], None]] = None,
) -> Tuple[int, int, int, int]:
    """Draw a node card and return its bounding box."""
    colors = {
        "idle": "#f8fafc",
        "running": "#fef3c7",
        "done": "#dcfce7",
        "error": "#fee2e2",
        "waiting": "#e0f2fe",
        "warning": "#fef9c3",
    }
    border_colors = {
        "idle": "#94a3b8",
        "running": "#d97706",
        "done": "#16a34a",
        "error": "#dc2626",
        "waiting": "#0284c7",
        "warning": "#ca8a04",
    }
    fill = colors.get(status, colors["idle"])
    outline = border_colors.get(status, border_colors["idle"])

    x2 = x + CARD_WIDTH
    y2 = y + CARD_HEIGHT
    rect = canvas.create_rectangle(
        x,
        y,
        x2,
        y2,
        fill=fill,
        outline=outline,
        width=2,
    )

    alias = node_data.get("alias") or node_data.get("type", node_id)
    node_type = node_data.get("type", "unknown")
    text_items = []
    text_items.append(canvas.create_text(
        x + 14,
        y + 18,
        anchor="w",
        text=alias,
        fill="#0f172a",
        font=("Segoe UI", 11, "bold"),
    ))
    if node_data.get("bookmarked"):
        text_items.append(canvas.create_text(
            x2 - 24,
            y + 58,
            text="*",
            fill="#ca8a04",
            font=("Segoe UI", 16, "bold"),
        ))
    text_items.append(canvas.create_text(
        x + 14,
        y + 42,
        anchor="w",
        text=node_type,
        fill="#475569",
        font=("Segoe UI", 9),
    ))
    text_items.append(canvas.create_text(
        x + 14,
        y + 61,
        anchor="w",
        text=node_id,
        fill="#64748b",
        font=("Consolas", 8),
    ))

    delete_items = []
    if on_delete is not None:
        button_x1 = x2 - 78
        button_y1 = y + 12
        button_x2 = x2 - 14
        button_y2 = y + 38
        delete_rect = canvas.create_rectangle(
            button_x1,
            button_y1,
            button_x2,
            button_y2,
            fill="#fee2e2",
            outline="#ef4444",
            width=1,
        )
        delete_text = canvas.create_text(
            (button_x1 + button_x2) // 2,
            (button_y1 + button_y2) // 2,
            text="Delete",
            fill="#991b1b",
            font=("Segoe UI", 8, "bold"),
        )
        delete_items = [delete_rect, delete_text]
        for item in delete_items:
            canvas.tag_bind(
                item, "<Button-1>", lambda _event, nid=node_id: on_delete(nid)
            )

    if on_click is not None:
        clickable_items = [rect] + text_items
        canvas.tag_bind(rect, "<Button-1>", lambda _event, nid=node_id: on_click(nid))
        for item_id in clickable_items:
            canvas.tag_bind(
                item_id, "<Button-1>", lambda _event, nid=node_id: on_click(nid)
            )

    return x, y, x2, y2
