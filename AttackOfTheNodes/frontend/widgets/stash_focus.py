"""Focus ownership for explicit field Stash actions in row/text editors."""
from frontend import notifications


def stash_field(screen, selector):
    field = screen.query_one(selector)
    if screen.focused is not field or field.disabled or not field.display:
        notifications.notify_info(screen.app, "Stash text can't go into this field")
        return None
    return field
