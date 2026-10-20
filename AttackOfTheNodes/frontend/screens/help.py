"""Help modal."""


from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from frontend.keymap import EDITOR, EXECUTION, HELP, bindings_for, help_for

from frontend.widgets.command_screen_mixin import CommandScreenMixin


HELP_TEXT = {
    "node_config": [
        "Config",
        "  W/S or ↑/↓  Move through fields",
        "  A/D or ←/→  Switch tabs",
        "  E or Enter  Edit / choose",
        "  P           Insert from Stash into the field",
        "  Ctrl+S      Save",
        "  Ctrl+Enter  Save multiline text",
        "  Esc         Leave field or cancel",
        "  Ctrl+Q      Revert field edit",
    ],
    "node_selector": [
        "Selector",
        "  W/S or ↑/↓  Move through nodes",
        "  A/D         Switch tabs",
        "  E or Enter  Add / open group",
        "  /           Filter",
        "  Esc         Cancel",
    ],
    "workflow_library": [
        "Workflow Library",
        "  Open and create             Manage",
        "    E    open                   R    rename",
        "    N    new                    X    delete",
        "    D    duplicate              I    import",
        "    C    copy to subworkflows   O    export",
        "",
        "  Move",
        "    1/2  switch tab             Esc  close",
        "    W/S  up / down",
    ],
    "stash": [
        "Stash",
        "  1 / 2                 Paste or drop / Entries",
        "  Paste, drop or Enter  Add (paths become files, else text)",
        "  T                     Keep a refused paste as text; on Entries, filter",
        "  W/S or ↑/↓            Move",
        "  / or E                Search / rename on Entries",
        "  R / X                 Rename / delete",
        "  Esc                   Close",
    ],
    "settings": [
        "Options",
        "  W/S or ↑/↓  Move through settings",
        "  E or Enter  Edit / toggle",
        "  Ctrl+S      Save",
        "  Esc         Cancel",
    ],
    "general": [
        "General",
        "  Ctrl+S  Save workflow",
        "  Ctrl+R  Run workflow",
        "  Ctrl+N  New workflow",
        "  Ctrl+O  File",
        "  Ctrl+E  Options",
        "  H or ?  Help",
        "  Ctrl+C  Copy selected text",
        "  Ctrl+Q  Quit from editor",
    ],
}


PROFILE_HELP = {"editor": EDITOR, "execution": EXECUTION}


class HelpScreen(CommandScreenMixin, ModalScreen):
    """Keyboard reference and short TUI usage guide."""

    KEYMAP = HELP
    BINDINGS = bindings_for(KEYMAP)

    def __init__(self, context: str = "general") -> None:
        super().__init__()
        self.context = context if context in HELP_TEXT or context in PROFILE_HELP else "general"

    def compose(self) -> ComposeResult:
        # The text scrolls so Close stays on screen in short terminals.
        with Vertical(id="modal-card", classes="help-modal"):
            yield Label("Help", classes="modal-title")
            with VerticalScroll(id="help-scroll"):
                yield Static(
                    "\n".join(self._help_lines()),
                    id="help-text",
                    markup=False,
                )
            yield Button("Close", id="close-help", variant="default")

    def _help_lines(self) -> list[str]:
        profile = PROFILE_HELP.get(self.context)
        if profile is not None:
            return help_for(profile, keymap=getattr(self.app, "_keymap", None))
        return HELP_TEXT[self.context]

    def action_cursor_up(self) -> None:
        self.query_one("#help-scroll", VerticalScroll).scroll_relative(y=-3, animate=False)

    def action_cursor_down(self) -> None:
        self.query_one("#help-scroll", VerticalScroll).scroll_relative(y=3, animate=False)

    def on_mount(self) -> None:
        self._focus_first()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-help":
            self.action_close()

    def action_close(self) -> None:
        self.dismiss(None)
