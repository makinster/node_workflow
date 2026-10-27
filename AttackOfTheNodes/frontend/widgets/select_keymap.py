"""Textual 8.2 Select compatibility, with one native registered key source.

Some hosts/terminal focus paths leave focus on the expanded Select instead of
its overlay. Both native owners use the same profile; only the focused owner
is enabled. No raw-key handler or second shortcut map is installed.
"""

from textual.widgets import Select
from textual.widgets._select import SelectOverlay

from frontend.keymap import SELECT_OVERLAY, bindings_for
from frontend.keymap_runtime import available, context_for


def install_select_keymap() -> None:
    if getattr(SelectOverlay, "_registered_command_keymap", False):
        return
    additions = bindings_for(SELECT_OVERLAY)
    keys = {binding.key for binding in additions}

    def install(owner, *, keep_native=False):
        owner.KEYMAP = SELECT_OVERLAY
        # Select retains its native Enter -> show_overlay for the closed state.
        # Overlay-native keys are replaced by the registered priority routes.
        owner.BINDINGS = [binding for binding in owner.BINDINGS
                          if keep_native or (binding.key if hasattr(binding, "key") else binding[0]) not in keys] + additions
        owner._merged_bindings = owner._merge_bindings()
        original_check = owner.check_action

        def check_action(self, action, parameters):
            commands = [command for command in SELECT_OVERLAY.commands
                        if command.action_signature == (action, parameters)]
            if commands:
                if isinstance(self, Select) and not self.expanded:
                    return False
                if not all(available(command, SELECT_OVERLAY.scope, context_for(self)) for command in commands):
                    return False
            return original_check(self, action, parameters)

        owner.check_action = check_action

    # These are action delegates, not key handlers. The focused Select can
    # operate its overlay without forcing focus or duplicating dispatch.
    def cursor_up(self):
        self.query_one(SelectOverlay).action_cursor_up()

    def cursor_down(self):
        self.query_one(SelectOverlay).action_cursor_down()

    def select(self):
        self.query_one(SelectOverlay).action_select()

    def dismiss(self):
        self.query_one(SelectOverlay).action_dismiss()

    def stash_insert(self):
        # Expanded overlays own dispatch. Keep P on the same field's screen;
        # never fall through to a suspended form's remembered Stash target.
        action = getattr(self.screen, "action_stash_insert", None)
        if action is not None:
            action()
        else:
            from frontend import notifications
            notifications.notify_info(self.app, "Stash text can't go into this field")

    Select.action_stash_insert = stash_insert
    SelectOverlay.action_stash_insert = stash_insert
    Select.action_cursor_up = cursor_up
    Select.action_cursor_down = cursor_down
    Select.action_select = select
    Select.action_dismiss = dismiss
    install(Select, keep_native=True)
    install(SelectOverlay)
    SelectOverlay._registered_command_keymap = True
