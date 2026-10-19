"""Typed command definitions; no screens, application services or dispatch loop.

IDs describe operations and remain stable when keys or Python actions change.
Only migrated profiles belong here; legacy screens keep their existing bindings
until their migration. Textual's native dispatcher remains authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from textual.actions import parse
from textual.binding import Binding
from textual.keys import key_to_character


class Scope(Enum):
    SCREEN = "screen"
    APPLICATION = "application"
    WIDGET = "widget"


class Policy(Enum):
    NAV = "navigation"
    TEXT = "text"
    SELECT = "select"


@dataclass(frozen=True)
class Command:
    id: str
    keys: tuple[str, ...]
    action: str
    description: str
    policies: frozenset[Policy] = frozenset({Policy.NAV})
    priority: bool = False
    # Compact hints are a subset of the same declared keys, never another map.
    hint: str | None = None
    navigation: Literal["up", "down", "left", "right", "activate"] | None = None
    auto_edit_only: bool = False
    row_fallback: bool = False

    @property
    def action_signature(self) -> tuple[str, tuple[object, ...]]:
        namespace, name, parameters = parse(self.action)
        if namespace:
            raise ValueError(f"{self.id}: actions must belong to their profile owner")
        return name, parameters


@dataclass(frozen=True)
class Profile:
    id: str
    commands: tuple[Command, ...]
    scope: Scope = Scope.SCREEN
    cancel_action: str | None = None

    def __post_init__(self) -> None:
        ids: set[str] = set()
        keys: dict[str, frozenset[Policy]] = {}
        policies: dict[tuple[str, tuple[object, ...]], frozenset[Policy]] = {}
        for command in self.commands:
            if not command.id or command.id in ids:
                raise ValueError(f"{self.id}: duplicate/empty command ID {command.id!r}")
            ids.add(command.id)
            if not isinstance(command.policies, frozenset) or not command.policies or not command.policies <= frozenset(Policy):
                raise ValueError(f"{command.id}: a nonempty frozen policy set is required")
            if not command.description or not command.keys:
                raise ValueError(f"{command.id}: description and keys are required")
            signature = command.action_signature
            if signature in policies and policies[signature] != command.policies:
                raise ValueError(f"{command.id}: one action cannot have conflicting policies")
            policies[signature] = command.policies
            for key in command.keys:
                if not key or key.strip() != key or "," in key or bool(keys.get(key, frozenset()) & command.policies):
                    raise ValueError(f"{command.id}: invalid or duplicate key {key!r}")
                keys[key] = keys.get(key, frozenset()) | command.policies


# Reused semantic IDs; each profile compiles its own native bindings.
NAVIGATION = (
    Command("ui.focus.up", ("w", "up"), "cursor_up", "Up", priority=True, navigation='up'),
    Command("ui.focus.down", ("s", "down"), "cursor_down", "Down", priority=True, navigation='down'),
    Command("ui.focus.left", ("a", "left"), "cursor_left", "Left", priority=True, navigation='left'),
    Command("ui.focus.right", ("d", "right"), "cursor_right", "Right", priority=True, navigation='right'),
    Command("ui.activate", ("e", "enter"), "activate_focused", "Activate", priority=True, navigation='activate'),
)

CONFIRM = Profile("confirm", (
    Command("confirm.accept", ("y",), "confirm_yes", "Yes", hint="confirm"),
    Command("confirm.reject", ("n", "escape"), "confirm_no", "No", hint="cancel"),
    Command("confirm.cancel", ("ctrl+q",), "confirm_no", "Cancel", priority=True),
    *NAVIGATION,
))

NAV = frozenset({Policy.NAV})
NAV_TEXT = frozenset({Policy.NAV, Policy.TEXT})
NAV_TEXT_SELECT = frozenset({Policy.NAV, Policy.TEXT, Policy.SELECT})

APP = Profile('app', (
    Command('app.save_workflow', ('ctrl+s',), 'save_workflow', 'Save', policies=NAV, priority=False),
    Command('app.run_workflow', ('ctrl+r',), 'run_workflow', 'Run', policies=NAV, priority=False),
    Command('app.new_workflow', ('ctrl+n',), 'new_workflow', 'New', policies=NAV, priority=False),
    Command('app.workflow_library', ('ctrl+o',), 'workflow_library', 'Open', policies=NAV, priority=False),
    Command('app.settings', ('ctrl+e',), 'settings', 'Settings', policies=NAV, priority=False),
    Command('app.help', ('h', '?'), 'help', 'Help', policies=NAV, priority=False),
    Command('app.back', ('q',), 'back', 'Back', policies=NAV, priority=False),
    Command('app.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Back', policies=NAV_TEXT, priority=True),
), scope=Scope.APPLICATION, cancel_action='back')

BRANCH_KEEP_SELECTOR = Profile('branch_keep_selector', (
    Command('branch_keep_selector.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('branch_keep_selector.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('branch_keep_selector.cursor_up', ('up', 'w'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('branch_keep_selector.cursor_down', ('down', 's'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('branch_keep_selector.choose', ('enter',), 'choose', 'Choose', policies=NAV, priority=False, navigation='activate'),
    Command('branch_keep_selector.choose.e', ('e',), 'toggle', 'Choose', policies=NAV, priority=True, navigation='activate'),
    Command('branch_keep_selector.toggle', ('space',), 'toggle', 'Toggle', policies=NAV, priority=True),
), cancel_action='cancel')

BRANCH_SELECTOR = Profile('branch_selector', (
    Command('branch_selector.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('branch_selector.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('branch_selector.cursor_up', ('up', 'w'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('branch_selector.cursor_down', ('down', 's'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('branch_selector.choose', ('enter', 'd'), 'choose', 'Choose', policies=NAV, priority=False, navigation='activate'),
    Command('branch_selector.choose.e', ('e',), 'choose', 'Choose', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

EDITOR = Profile('editor', (
    Command('editor.focus_next', ('tab',), 'focus_next', 'Next panel', policies=NAV, priority=False),
    Command('editor.focus_previous', ('shift+tab',), 'focus_previous', 'Previous panel', policies=NAV, priority=False),
    Command('editor.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('editor.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('editor.cycle_branch_prev', ('left', 'a'), 'cycle_branch_prev', 'Previous branch', policies=NAV, priority=True),
    Command('editor.cycle_branch_next', ('right', 'd'), 'cycle_branch_next', 'Next branch', policies=NAV, priority=True),
    Command('editor.edit_selected', ('enter',), 'edit_selected', 'Edit', policies=NAV, priority=False, navigation='activate'),
    Command('editor.edit_selected.e', ('e',), 'edit_selected', 'Edit', policies=NAV, priority=True, navigation='activate'),
    Command('editor.cycle_incomplete_branch_prev', ('ctrl+a', 'ctrl+left'), 'cycle_incomplete_branch_prev', 'Previous incomplete branch', policies=NAV, priority=True),
    Command('editor.cycle_incomplete_branch_next', ('ctrl+d', 'ctrl+right'), 'cycle_incomplete_branch_next', 'Next incomplete branch', policies=NAV, priority=True),
    Command('editor.insert_node', ('i',), 'insert_node', 'Insert node', policies=NAV, priority=True),
    Command('editor.validate_workflow', ('v',), 'validate_workflow', 'Validate', policies=NAV, priority=True),
    Command('editor.toggle_breakpoint', ('b',), 'toggle_breakpoint', 'Breakpoint', policies=NAV, priority=True),
    Command('editor.clear_breakpoints', ('ctrl+b',), 'clear_breakpoints', 'Clear breakpoints', policies=NAV, priority=True),
    Command('editor.undo_delete', ('z',), 'undo_delete', 'Undo delete', policies=NAV, priority=True),
    Command('editor.delete_selected', ('backspace', 'x'), 'delete_selected', 'Delete', policies=NAV, priority=True),
    Command('editor.workflow_library', ('f',), 'workflow_library', 'File', policies=NAV, priority=True),
    Command('editor.stash', ('p',), 'stash', 'Stash', policies=NAV, priority=True),
    Command('editor.options', ('o',), 'options', 'Options', policies=NAV, priority=True),
    Command('editor.help', ('h', '?'), 'help', 'Help', policies=NAV, priority=True),
    Command('editor.save_workflow', ('ctrl+s',), 'save_workflow', 'Save', policies=NAV, priority=True),
))

ERROR_DETAILS = Profile('error_details', (
    Command('error_details.close', ('escape', 'q'), 'close', 'Close', policies=NAV, priority=False),
    Command('error_details.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Close', policies=NAV_TEXT, priority=True),
    Command('error_details.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('error_details.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('error_details.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('error_details.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('error_details.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='close')

EXECUTION = Profile('execution', (
    Command('execution.pause_resume', ('p',), 'pause_resume', 'Pause/resume', policies=NAV, priority=False),
    Command('execution.stop', ('s', 'S'), 'stop', 'Stop', policies=NAV, priority=False),
    Command('execution.memory', ('m',), 'memory', 'Memory', policies=NAV, priority=False),
    Command('execution.output', ('o',), 'output', 'Output', policies=NAV, priority=False),
    Command('execution.errors', ('e',), 'errors', 'Errors', policies=NAV, priority=False),
    Command('execution.back_to_editor', ('escape',), 'back_to_editor', 'Editor', policies=NAV, priority=False),
    Command('execution.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Editor', policies=NAV_TEXT, priority=True),
), cancel_action='back_to_editor')

GROUP_PICKER = Profile('group_picker', (
    Command('group_picker.cancel', ('escape',), 'cancel', 'Back', policies=NAV, priority=False),
    Command('group_picker.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Back', policies=NAV_TEXT, priority=True),
    Command('group_picker.cursor_up', ('up', 'w'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('group_picker.cursor_down', ('down', 's'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('group_picker.choose', ('enter',), 'choose', 'Add', policies=NAV, priority=False, navigation='activate'),
    Command('group_picker.choose.e', ('e',), 'choose', 'Add', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

HELP = Profile('help', (
    Command('help.close', ('escape', 'q'), 'close', 'Close', policies=NAV, priority=False),
    Command('help.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Close', policies=NAV_TEXT, priority=True),
    Command('help.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('help.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('help.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('help.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('help.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='close')

MERGE_BEACON_SELECTOR = Profile('merge_beacon_selector', (
    Command('merge_beacon_selector.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('merge_beacon_selector.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('merge_beacon_selector.cursor_up', ('up', 'w'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('merge_beacon_selector.cursor_down', ('down', 's'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('merge_beacon_selector.choose', ('enter',), 'choose', 'Choose', policies=NAV, priority=False, navigation='activate'),
    Command('merge_beacon_selector.choose.e', ('e',), 'choose', 'Choose', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

NODE_CONFIG = Profile('node_config', (
    Command('node_config.cancel', ('escape',), 'cancel', 'Close', policies=NAV, priority=False),
    Command('node_config.save_and_stay', ('ctrl+s', 'ctrl+enter'), 'save_and_stay', 'Save', policies=NAV_TEXT_SELECT, priority=True),
    Command('node_config.jump_config_tab.1', ('1',), 'jump_config_tab(1)', 'Tab 1', policies=NAV, priority=True),
    Command('node_config.jump_config_tab.2', ('2',), 'jump_config_tab(2)', 'Tab 2', policies=NAV, priority=True),
    Command('node_config.jump_config_tab.3', ('3',), 'jump_config_tab(3)', 'Tab 3', policies=NAV, priority=True),
    Command('node_config.jump_config_tab.4', ('4',), 'jump_config_tab(4)', 'Tab 4', policies=NAV, priority=True),
    Command('node_config.jump_config_tab.5', ('5',), 'jump_config_tab(5)', 'Tab 5', policies=NAV, priority=True),
    Command('node_config.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('node_config.stash_insert', ('p',), 'stash_insert', 'Insert from Stash', policies=NAV, priority=True),
    Command('node_config.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('node_config.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('node_config.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('node_config.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('node_config.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

NODE_SELECTOR = Profile('node_selector', (
    Command('node_selector.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('node_selector.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('node_selector.focus_filter', ('/',), 'focus_filter', 'Filter', policies=NAV, priority=False),
    Command('node_selector.focus_node_list', ('tab',), 'focus_node_list', 'List', policies=NAV, priority=True),
    Command('node_selector.jump_tab.1', ('1',), 'jump_tab(1)', 'Tab 1', policies=NAV, priority=True),
    Command('node_selector.jump_tab.2', ('2',), 'jump_tab(2)', 'Tab 2', policies=NAV, priority=True),
    Command('node_selector.jump_tab.3', ('3',), 'jump_tab(3)', 'Tab 3', policies=NAV, priority=True),
    Command('node_selector.jump_tab.4', ('4',), 'jump_tab(4)', 'Tab 4', policies=NAV, priority=True),
    Command('node_selector.jump_tab.5', ('5',), 'jump_tab(5)', 'Tab 5', policies=NAV, priority=True),
    Command('node_selector.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('node_selector.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('node_selector.cursor_up', ('up', 'w'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('node_selector.cursor_down', ('down', 's'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('node_selector.choose', ('enter',), 'choose', 'Add', policies=NAV, priority=False, navigation='activate'),
    Command('node_selector.choose.e', ('e',), 'choose', 'Add', policies=NAV, priority=True, navigation='activate'),
    Command('node_selector.toggle_fitting', ('t',), 'toggle_fitting', 'Fitting only', policies=NAV, priority=True),
), cancel_action='cancel')

RECOVERY_BRANCH_UNPICK = Profile('recovery_branch_unpick', (
    Command('recovery_branch_unpick.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('recovery_branch_unpick.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
), cancel_action='cancel')

SETTINGS = Profile('settings', (
    Command('settings.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('settings.save', ('ctrl+s',), 'save', 'Save', policies=NAV_TEXT, priority=False),
    Command('settings.settings_tab_general', ('1',), 'jump_settings_tab(1)', 'General', policies=NAV, priority=True),
    Command('settings.settings_tab_secrets', ('2',), 'jump_settings_tab(2)', 'Secrets', policies=NAV, priority=True),
    Command('settings.delete_secret', ('x',), 'delete_secret', 'Delete secret', policies=NAV, priority=True),
    Command('settings.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('settings.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('settings.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('settings.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('settings.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('settings.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

STASH = Profile('stash', (
    Command('stash.close', ('escape', 'q'), 'close', 'Close', policies=NAV, priority=False),
    Command('stash.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Close', policies=NAV_TEXT, priority=True),
    Command('stash.show_tab.add', ('1',), "show_tab('add')", 'Paste / drop', policies=NAV, priority=True),
    Command('stash.show_tab.entries', ('2',), "show_tab('entries')", 'Entries', policies=NAV, priority=True),
    Command('stash.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=False, navigation='up'),
    Command('stash.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=False, navigation='down'),
    Command('stash.search', ('slash',), 'search', 'Search', policies=NAV, priority=False),
    Command('stash.toggle', ('t',), 'toggle', 'Filter / keep as text', policies=NAV, priority=False),
    Command('stash.rename', ('r',), 'rename', 'Rename', policies=NAV, priority=False),
    Command('stash.delete', ('x',), 'delete', 'Delete', policies=NAV, priority=False),
    Command('stash.edit', ('e',), 'edit', 'Edit', policies=NAV, priority=False, navigation='activate'),
), cancel_action='close')

UNSAVED_CHANGES = Profile('unsaved_changes', (
    Command('unsaved_changes.stay', ('escape',), 'stay', 'Stay', policies=NAV, priority=False),
    Command('unsaved_changes.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Stay', policies=NAV_TEXT, priority=True),
    Command('unsaved_changes.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('unsaved_changes.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('unsaved_changes.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('unsaved_changes.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('unsaved_changes.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='stay')

USER_INPUT = Profile('user_input', (
    Command('user_input.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('user_input.submit', ('ctrl+enter',), 'submit', 'Submit', policies=NAV_TEXT, priority=False),
    Command('user_input.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('user_input.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('user_input.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('user_input.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('user_input.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('user_input.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

WORKFLOW_LIBRARY = Profile('workflow_library', (
    Command('workflow_library.cancel', ('escape', 'q'), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('workflow_library.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('workflow_library.cursor_up', ('up', 'w'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('workflow_library.cursor_down', ('down', 's'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('workflow_library.load_selected', ('enter',), 'load_selected', 'Load', policies=NAV, priority=False, navigation='activate'),
    Command('workflow_library.choose', ('e',), 'choose', 'Load', policies=NAV, priority=True, navigation='activate'),
    Command('workflow_library.new_workflow', ('n',), 'new_workflow', 'New', policies=NAV, priority=False),
    Command('workflow_library.rename_selected', ('r',), 'rename_selected', 'Rename', policies=NAV, priority=False),
    Command('workflow_library.duplicate_selected', ('d',), 'duplicate_selected', 'Duplicate', policies=NAV, priority=False),
    Command('workflow_library.import_workflow', ('i',), 'import_workflow', 'Import', policies=NAV, priority=False),
    Command('workflow_library.export_selected', ('o',), 'export_selected', 'Export', policies=NAV, priority=False),
    Command('workflow_library.delete_selected', ('x',), 'delete_selected', 'Delete', policies=NAV, priority=False),
    Command('workflow_library.show_tab.workflows', ('1',), "show_tab('workflows')", 'Workflows', policies=NAV, priority=True),
    Command('workflow_library.show_tab.sub', ('2',), "show_tab('sub')", 'Subworkflows', policies=NAV, priority=True),
    Command('workflow_library.copy_to_subworkflows', ('c',), 'copy_to_subworkflows', 'Copy to subworkflows', policies=NAV, priority=False),
), cancel_action='cancel')

NAME_PROMPT = Profile('name_prompt', (
    Command('name_prompt.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('name_prompt.submit', ('ctrl+enter',), 'submit', 'Confirm', policies=NAV_TEXT, priority=False),
    Command('name_prompt.submit.ctrl.s', ('ctrl+s',), 'submit', 'Confirm', policies=NAV_TEXT, priority=True),
    Command('name_prompt.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('name_prompt.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('name_prompt.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('name_prompt.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('name_prompt.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('name_prompt.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

CONTRACT_ROW_EDITOR = Profile('contract_row_editor', (
    Command('contract_row_editor.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('contract_row_editor.submit', ('ctrl+enter',), 'submit', 'Confirm', policies=NAV_TEXT, priority=False),
    Command('contract_row_editor.submit.ctrl.s', ('ctrl+s',), 'submit', 'Confirm', policies=NAV_TEXT, priority=True),
    Command('contract_row_editor.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('contract_row_editor.stash_insert', ('p',), 'stash_insert', 'Insert from Stash', policies=NAV, priority=True),
    Command('contract_row_editor.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('contract_row_editor.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('contract_row_editor.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('contract_row_editor.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('contract_row_editor.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

PATH_PROMPT = Profile('path_prompt', (
    Command('path_prompt.cancel', ('escape',), 'cancel', 'Cancel', policies=NAV, priority=False),
    Command('path_prompt.submit', ('ctrl+enter',), 'submit', 'Submit', policies=NAV_TEXT, priority=False),
    Command('path_prompt.browse', ('b',), 'browse', 'Browse', policies=NAV, priority=True),
    Command('path_prompt.tab_out', ('tab',), 'tab_out', 'Next', policies=NAV, priority=True),
    Command('path_prompt.revert_or_cancel', ('ctrl+q',), 'revert_or_cancel', 'Cancel', policies=NAV_TEXT, priority=True),
    Command('path_prompt.cursor_up', ('w', 'up'), 'cursor_up', 'Up', policies=NAV, priority=True, navigation='up'),
    Command('path_prompt.cursor_down', ('s', 'down'), 'cursor_down', 'Down', policies=NAV, priority=True, navigation='down'),
    Command('path_prompt.cursor_left', ('a', 'left'), 'cursor_left', 'Left', policies=NAV, priority=True, navigation='left'),
    Command('path_prompt.cursor_right', ('d', 'right'), 'cursor_right', 'Right', policies=NAV, priority=True, navigation='right'),
    Command('path_prompt.activate_focused', ('e', 'enter'), 'activate_focused', 'Activate', policies=NAV, priority=True, navigation='activate'),
), cancel_action='cancel')

# Widget policies are part of the same registry. Native editing (caret,
# deletion, selection and clipboard) remains owned by Textual.
TEXT = frozenset({Policy.TEXT})
SELECT = frozenset({Policy.SELECT})

NAV_CARET = (
    Command("text.caret_left", ("a",), "caret_left", "Position caret left",
            priority=True, navigation="left", row_fallback=True),
    Command("text.caret_right", ("d",), "caret_right", "Position caret right",
            priority=True, navigation="right", row_fallback=True),
)

TEXT_INPUT = Profile("text_input", (
    Command("text.begin_edit", ("e",), "begin_edit", "Edit", priority=True, navigation='activate'),
    Command("text_input.enter_edit", ("enter",), "enter_edit", "Edit", priority=True, navigation='activate'),
    Command("text.finish_escape", ("escape",), "finish_edit", "Finish edit", policies=TEXT, priority=True),
    Command("text.revert", ("ctrl+q",), "revert_edit", "Revert edit", policies=TEXT, priority=True),
    Command("text_input.finish_tab", ("tab", "shift+tab"), "finish_edit", "Finish edit", policies=TEXT, priority=True),
    Command("text_input.finish_enter", ("enter",), "finish_enter", "Finish edit", policies=TEXT, priority=True),
    Command("text.nav_up", ("w", "up"), "screen_up", "Up", priority=True, navigation='up'),
    Command("text.nav_down", ("s", "down"), "screen_down", "Down", priority=True, navigation='down'),
    Command("text.tab_previous", ("shift+tab",), "previous_field", "Previous field", priority=True),
    Command("text.tab_next", ("tab",), "next_field", "Next field", priority=True),
    Command("text_input.auto_up", ("w",), "auto_up", "Previous field", policies=TEXT, priority=True, auto_edit_only=True),
    Command("text_input.auto_down", ("s",), "auto_down", "Next field", policies=TEXT, priority=True, auto_edit_only=True),
    *NAV_CARET,
), scope=Scope.WIDGET)

TEXT_AREA = Profile("text_area", (
    TEXT_INPUT.commands[0], TEXT_INPUT.commands[1],
    TEXT_INPUT.commands[2], TEXT_INPUT.commands[3],
    Command("text_area.finish", ("ctrl+enter",), "finish_edit", "Finish edit", policies=TEXT, priority=True),
    Command("text_area.nav_up", ("w", "up"), "screen_up", "Up", priority=True, navigation='up'),
    Command("text_area.nav_down", ("s", "down"), "screen_down", "Down", priority=True, navigation='down'),
    *NAV_CARET,
), scope=Scope.WIDGET)

NAME_INPUT = Profile("name_input", (
    *(command for command in TEXT_INPUT.commands
      if command.id not in {"text_input.enter_edit", "text_input.finish_enter"}),
    Command("name_input.submit", ("enter",), "submit_name", "Confirm", policies=NAV_TEXT, priority=True),
), scope=Scope.WIDGET)

STASH_PASTE = Profile("stash_paste", (
    *(command for command in TEXT_AREA.commands if command.id != "text_input.enter_edit"),
    Command("stash_paste.submit", ("enter",), "submit_paste", "Add", policies=NAV_TEXT, priority=True),
), scope=Scope.WIDGET)

STASH_SEARCH = Profile("stash_search", (
    *(command for command in TEXT_INPUT.commands
      if command.id not in {"text.finish_escape", "text_input.finish_enter"}),
    Command("stash_search.finish", ("enter", "escape"), "finish_search", "Finish search", policies=TEXT, priority=True),
), scope=Scope.WIDGET)

SELECT_OVERLAY = Profile("select_overlay", (
    Command("select.up", ("w", "up"), "cursor_up", "Up", policies=SELECT, priority=True, navigation='up'),
    Command("select.down", ("s", "down"), "cursor_down", "Down", policies=SELECT, priority=True, navigation='down'),
    Command("select.choose", ("e", "enter"), "select", "Select", policies=SELECT, priority=True),
    Command("select.dismiss", ("ctrl+q", "escape"), "dismiss", "Dismiss menu", policies=SELECT, priority=True),
), scope=Scope.WIDGET)

WIDGET_PROFILES = (TEXT_INPUT, TEXT_AREA, NAME_INPUT, STASH_PASTE, STASH_SEARCH, SELECT_OVERLAY)


PROFILES = (CONFIRM, APP, BRANCH_KEEP_SELECTOR, BRANCH_SELECTOR, EDITOR, ERROR_DETAILS, EXECUTION, GROUP_PICKER, HELP, MERGE_BEACON_SELECTOR, NODE_CONFIG, NODE_SELECTOR, RECOVERY_BRANCH_UNPICK, SETTINGS, STASH, UNSAVED_CHANGES, USER_INPUT, WORKFLOW_LIBRARY, NAME_PROMPT, PATH_PROMPT, CONTRACT_ROW_EDITOR,)


def priority_for(command: Command, key: str) -> bool:
    """NAV printable commands must run before a nonediting field eats them."""
    character = key_to_character(key)
    return command.priority or (Policy.NAV in command.policies and bool(character and character.isprintable()))


def bindings_for(profile: Profile) -> list[Binding]:
    """Compile at class definition time, before Textual merges the MRO bindings."""
    return [
        Binding(
            key, command.action, command.description,
            id=command.id, priority=priority_for(command, key),
        )
        for command in profile.commands
        for key in command.keys
    ]


def display_key(key: str) -> str:
    """Consistent spelling for app hints; the input remains a native key name."""
    return {"escape": "Esc", "enter": "Enter", "up": "↑", "down": "↓",
            "left": "←", "right": "→"}.get(key, key.upper())


def hint_for(profile: Profile) -> str:
    """Initial compact display consumer; full contextual Help follows in PR 3."""
    return "  ".join(
        f"{' / '.join(display_key(key) for key in command.keys)} {command.hint}"
        for command in profile.commands if command.hint is not None
    )
