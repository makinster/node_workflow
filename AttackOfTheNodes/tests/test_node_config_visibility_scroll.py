"""Production-style regressions for toggle visibility and highlighted scrolling."""

from copy import deepcopy
from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import Checkbox, SelectionList, Select

from frontend.screens.node_config import NodeConfigScreen
from tests.test_debug_nodes import _make_services


def config_app(wm, node, memory):
    class ConfigApp(App):
        CSS_PATH = str(Path(__file__).parent.parent / "frontend" / "styles.tcss")

        async def on_mount(self):
            await self.push_screen(NodeConfigScreen(
                wm._factory, wm, node, wm.get_node_data(node), memory_bank=memory))

    return ConfigApp()


@pytest.mark.parametrize("width", [60, 100, 140])
async def test_vault_toggle_hides_list_and_preserves_selections(width):
    _, wm, memory, _ = _make_services()
    wm.create_new("visibility")
    writer = wm.add_node("user_text_input_node")
    wm.update_node_config(writer, {"membank_outputs": [{"id": "notes", "description": "Notes"}]})
    node = wm.add_node("text_output_node")
    before = deepcopy(wm.get_node_data(node))
    app = config_app(wm, node, memory)
    async with app.run_test(size=(width, 24)) as pilot:
        await pilot.pause()
        screen = app.screen
        toggle = screen.query_one("#membank-reads", Checkbox)
        choices = screen.query_one("#membank-inputs", SelectionList)
        assert not toggle.value
        assert not choices.display
        assert choices not in screen._keyboard_focus_widgets()
        app.set_focus(toggle)
        await pilot.press("enter")
        await pilot.pause()
        assert choices.display and not choices.disabled
        choices.select("notes")
        await pilot.press("enter")
        await pilot.pause()
        assert not choices.display
        assert choices.selected == ["notes"]
        await pilot.press("enter")
        await pilot.pause()
        assert choices.display and choices.selected == ["notes"]
        screen.action_cancel()
        await pilot.pause()
        assert wm.get_node_data(node) == before


@pytest.mark.parametrize("width", [60, 100, 140])
async def test_llm_initial_focus_and_scroll_follow_highlight_only(width):
    _, wm, memory, _ = _make_services()
    wm.create_new("scroll")
    memory.store_persistent("notes", "text", type_tag="string")
    node = wm.add_node("chat_completion_node")
    app = config_app(wm, node, memory)
    async with app.run_test(size=(width, 24)) as pilot:
        await pilot.pause(0.15)
        screen = app.screen
        scroll = screen._scroll_container()
        assert app.focused.id == "alias-input"
        assert scroll.scroll_y == 0
        assert app.focused.region.y >= scroll.content_region.y
        # Late programmatic events from non-highlighted fields must not scroll.
        count = screen.query_one("#field-context_input_count", Select)
        count.value = "3"
        await pilot.pause()
        assert app.focused.id == "alias-input"
        assert scroll.scroll_y == 0
        # No scrolling if the next row (including its margin) already fits.
        next_row = screen._keyboard_focus_widgets()[1]
        next_fits = scroll.content_region.contains_region(next_row.region.grow(next_row.styles.margin))
        await pilot.press("down")
        await pilot.pause()
        if next_fits:
            assert scroll.scroll_y == 0
        # Navigation scrolls enough to expose the highlighted row, not its neighbour.
        for _ in range(18):
            await pilot.press("down")
            await pilot.pause()
            focused = app.focused
            if screen._is_descendant_of(focused, scroll):
                assert focused.region.y < scroll.content_region.bottom
                assert focused.region.bottom > scroll.content_region.y
        # A newly selected tab starts at its first field.
        await pilot.press("2")
        await pilot.pause()
        assert app.focused is screen._keyboard_focus_widgets()[0]
        active_scroll = screen._scroll_container()
        assert app.focused.region.y < active_scroll.content_region.bottom
        assert app.focused.region.bottom > active_scroll.content_region.y


async def test_payload_toggle_hides_dependent_rows_and_retains_values():
    _, wm, memory, _ = _make_services()
    wm.create_new("routing_visibility")
    node = wm.add_node("chat_completion_node")
    app = config_app(wm, node, memory)
    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        screen = app.screen
        key = screen.query_one("#vault-output-key-default")
        key.value = "saved_result"
        disabled = screen.query_one("#vault-output-disabled-default", Checkbox)
        disabled.value = True
        await pilot.pause()
        assert not screen.query_one("#vault-key-row-default").display
        assert not screen.query_one("#vault-desc-row-default").display
        assert key not in screen._keyboard_focus_widgets()
        disabled.value = False
        await pilot.pause()
        assert screen.query_one("#vault-key-row-default").display
        assert key.value == "saved_result"
        forwarding = screen.query_one("#dead-drop-passthrough", Checkbox)
        forwarding.value = True
        await pilot.pause()
        assert not screen.query_one("#downstream-name-row-default").display
        assert not screen.query_one("#downstream-desc-row-default").display
        forwarding.value = False
        await pilot.pause()
        assert screen.query_one("#downstream-name-row-default").display


async def test_legacy_vault_write_fields_hidden_until_enabled():
    _, wm, memory, _ = _make_services()
    wm.create_new("legacy_write_visibility")
    node = wm.add_node("logger_node")
    app = config_app(wm, node, memory)
    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        screen = app.screen
        count = screen.query_one("#membank-output-count")
        label = screen.query_one("#membank-output-count-label")
        rows = screen.query_one("#membank-output-rows")
        assert not count.display and not label.display and not rows.display
        screen.query_one("#membank-writes", Checkbox).value = True
        await pilot.pause()
        assert count.display and label.display and rows.display
        assert screen.query("#membank-output-id-0")
        screen.query_one("#membank-output-id-0").text = "edited_key"
        screen.query_one("#membank-writes", Checkbox).value = False
        await pilot.pause()
        assert not count.display and not label.display and not rows.display
        screen.query_one("#membank-writes", Checkbox).value = True
        await pilot.pause()
        assert screen.query_one("#membank-output-id-0").text == "edited_key"


@pytest.mark.parametrize("node_type, controller, enabled, disabled, field", [
    ("text_output_node", "request_user_input", True, False, "prompt"),
    ("set_variable_node", "value_source", "literal", "input", "value"),
    ("conditional_node", "left_value_source", "variable", "input", "variable_name"),
    ("http_request_node", "method", "POST", "GET", "body"),
])
async def test_audited_dependencies_hide_labels_and_retain_edits(
    node_type, controller, enabled, disabled, field,
):
    _, wm, memory, _ = _make_services()
    wm.create_new("audited_dependencies")
    node = wm.add_node(node_type)
    original = deepcopy(wm.get_node_data(node))
    app = config_app(wm, node, memory)
    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        await pilot.press("2")
        await pilot.pause()
        screen = app.screen
        control = screen.query_one(f"#field-{controller}")
        target = screen.query_one(f"#field-{field}")
        assert not target.display
        assert not screen.query_one(f"#field-label-{field}").display
        control.value = enabled
        await pilot.pause()
        assert target.display
        assert screen.query_one(f"#field-label-{field}").display
        if hasattr(target, "text"):
            target.text = "retain edited value"
        else:
            target.value = "retain edited value"
        control.value = disabled
        await pilot.pause()
        assert not target.display and target not in screen._keyboard_focus_widgets()
        control.value = enabled
        await pilot.pause()
        assert screen._widget_text_value(target) == "retain edited value"
        # Getter preserves the hidden value, so saving unrelated fields cannot erase it.
        control.value = disabled
        await pilot.pause()
        assert screen._get_form_values()[field] == "retain edited value"
        screen.action_cancel()
        await pilot.pause()
        assert wm.get_node_data(node) == original


@pytest.mark.parametrize("node_type", ["set_variable_node", "variable_setter_node"])
async def test_unavailable_legacy_write_checkbox_is_hidden(node_type):
    _, wm, memory, _ = _make_services()
    wm.create_new("unavailable_write")
    node = wm.add_node(node_type)
    app = config_app(wm, node, memory)
    async with app.run_test(size=(100, 24)) as pilot:
        await pilot.pause()
        screen = app.screen
        writes = screen.query_one("#membank-writes", Checkbox)
        assert writes.disabled and not writes.display
        passthrough = screen.query_one("#field-pass_through", Checkbox)
        passthrough.value = False
        await pilot.pause()
        assert writes.display and not writes.disabled
        passthrough.value = True
        await pilot.pause()
        assert not writes.display


@pytest.mark.parametrize("width", [60, 100, 140])
async def test_short_payload_tab_scroll_stays_on_current_highlight(width):
    _, wm, memory, _ = _make_services()
    wm.create_new("short_payload_scroll")
    node = wm.add_node("image_generation_node")
    app = config_app(wm, node, memory)
    async with app.run_test(size=(width, 24)) as pilot:
        await pilot.pause()
        await pilot.press("3")
        await pilot.pause()
        screen = app.screen
        scroll = screen._scroll_container()
        # Its long config compresses Payloads to a short viewport at this height.
        for _ in range(5):
            screen.action_cursor_down()
            await pilot.pause(.03)
        for _ in range(5):
            screen.action_cursor_up()
            await pilot.pause(.03)
            focused = app.focused
            if screen._is_descendant_of(focused, scroll):
                assert focused.region.y < scroll.content_region.bottom
                assert focused.region.bottom > scroll.content_region.y
        focus = app.focused
        position = scroll.scroll_y
        await pilot.pause(.3)
        assert app.focused is focus
        assert scroll.scroll_y == position
        # A stale reveal request for another control must not move this view.
        last_field = screen.query_one("#membank-writes")
        screen._scroll_config_widget_into_view(last_field)
        await pilot.pause()
        assert scroll.scroll_y == position
