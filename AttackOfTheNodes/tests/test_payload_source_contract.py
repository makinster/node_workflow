"""Regression coverage for shared payload source discovery and forwarding."""
import asyncio

from tests.test_debug_nodes import _make_services
from frontend.node_io_display import trace_transient_producer
from frontend.screens.node_config import NodeConfigScreen


def test_writer_forwarding_traces_content_not_first_file_connection():
    _, wm, _, _ = _make_services()
    wm.create_new('forwarded_content')
    file_id = wm.add_node('file_view_node')
    text = wm.add_node('start_node')
    writer = wm.add_node('file_output_node')
    wm.update_node_config(writer, {'dead_drop_passthrough': True})
    wm.connect(file_id, 'default', writer, 'file')
    wm.connect(text, 'default', writer, 'content')
    result = trace_transient_producer(wm, wm._factory, writer, 'default')
    assert result['node_id'] == text
    assert result['data_type'] == 'string'


def test_upstream_preview_uses_immediate_captured_none_not_original_value():
    _, wm, mb, _ = _make_services()
    wm.create_new('preview')
    origin = wm.add_node('start_node')
    manager = wm.add_node('file_view_node')
    consumer = wm.add_node('text_output_node')
    wm.update_node_config(manager, {'dead_drop_passthrough': True})
    wm.connect(origin, 'default', manager, 'file')
    wm.connect(manager, 'default', consumer, 'input')
    mb.store_transient(origin, 'default', 'original value must not leak')
    mb.store_transient(manager, 'default', None)
    screen = NodeConfigScreen(wm._factory, wm, consumer, wm.get_node_data(consumer), memory_bank=mb)
    preview = screen._previous_output_text()
    assert 'original value must not leak' not in preview
    assert 'None' in preview or 'null' in preview


def test_file_input_excludes_known_text_upstream():
    _, wm, _, _ = _make_services()
    wm.create_new('typed')
    source = wm.add_node('start_node')
    manager = wm.add_node('file_view_node')
    wm.connect(source, 'default', manager, 'file')
    screen = NodeConfigScreen(wm._factory, wm, manager, wm.get_node_data(manager))
    schema = screen._metadata_for_type('file_view_node')['config_schema']
    result = screen._prune_unavailable_source_options(schema, {}, {})
    assert 'Upstream payload' not in result['file_source']['options']


def test_merge_home_payload_available_without_closing_sibling():
    _, wm, _, _ = _make_services()
    wm.create_new('home')
    source = wm.add_node('start_node')
    merge = wm.add_node('merge_node')
    wm.connect(source, 'default', merge, 'path_a')
    screen = NodeConfigScreen(wm._factory, wm, merge, wm.get_node_data(merge))
    assert ('Home branch | Input: path_a', 'home:path_a') in screen._merge_carry_forward_options([], set())


def test_object_list_roundtrip_and_removal():
    from textual.app import App
    from frontend.widgets.form_generator import build_form, ObjectListField
    class FormApp(App):
        def compose(self):
            form, self.get_values = build_form({'files': {'type': 'object_list', 'item_schema': {'id': {'type':'string'}, 'path': {'type':'string'}, 'vault_key': {'type':'string'}}}}, {'files':[{'id':'stable', 'path':'/tmp/a', 'vault_key':'a'}]})
            yield form
    async def run():
        app = FormApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert app.get_values()['files'] == [{'id':'stable','path':'/tmp/a','vault_key':'a'}]
            widget = app.query_one(ObjectListField)
            widget.rows[0][1].press()
            await pilot.pause()
            assert app.get_values()['files'] == []
    asyncio.run(run())


def test_manager_object_rows_and_downstream_picker_at_supported_widths():
    from pathlib import Path
    from textual.app import App
    from textual.widgets import Select, TabbedContent
    from frontend.widgets.form_generator import ObjectListField
    async def run(width):
        _, wm, mb, _ = _make_services()
        wm.create_new('manager_rows')
        node = wm.add_node('file_view_node')
        wm.update_node_config(node, {'file_source':'Configured', 'file':'/tmp/primary', 'additional_files':[{'id':'second','path':'/tmp/second','vault_key':'second_file','description':'second'}], 'downstream_file_id':'second'})
        class ConfigApp(App):
            CSS_PATH = str(Path(__file__).parents[1] / 'frontend/styles.tcss')
            def on_mount(self):
                self.push_screen(NodeConfigScreen(wm._factory, wm, node, wm.get_node_data(node), memory_bank=mb))
        app = ConfigApp()
        async with app.run_test(size=(width, 40)) as pilot:
            await pilot.pause()
            screen = app.screen
            picker = screen.query_one('#field-downstream_file_id', Select)
            assert picker.value == 'second'
            rows = screen.query_one(ObjectListField)
            assert screen._get_form_values()['additional_files'][0]['id'] == 'second'
            screen.query_one('#node-config-tabs', TabbedContent).active = 'node-config-tab-parameters'
            rows.query_one(f'#{rows.id}-add').press()
            await pilot.pause()
            assert len(rows.value) == 2
            new_id = rows.value[1]['id']
            assert new_id in {value for _, value in picker._options}
            for row in rows.rows:
                assert row[0].size.height > 0
            assert len(wm.get_node_data(node)['config']['additional_files']) == 1
    for width in (60, 100, 140):
        asyncio.run(run(width))


def test_vault_only_producer_is_not_offered_as_upstream():
    _, wm, _, _ = _make_services()
    wm.create_new('vault_only')
    source = wm.add_node('start_node')
    consumer = wm.add_node('text_output_node')
    wm.update_node_config(source, {'transient_output': False, 'vault_write': True, 'vault_write_key': 'text'})
    wm.connect(source, 'default', consumer, 'input')
    screen = NodeConfigScreen(wm._factory, wm, consumer, wm.get_node_data(consumer))
    schema = screen._metadata_for_type('text_output_node')['config_schema']
    result = screen._prune_unavailable_source_options(schema, {'any': [('text [string]', 'text')]}, {})
    assert 'Upstream payload' not in result['input_source']['options']


def test_user_text_vault_declaration_is_typed_before_execution():
    from frontend.node_io_display import memory_registry
    _, wm, _, _ = _make_services()
    wm.create_new('typed_user_text')
    source = wm.add_node('user_text_input_node')
    wm.update_node_config(source, {'membank_outputs': [{'id': 'answer'}]})
    assert memory_registry(wm)['answer']['data_type'] == 'string'


def test_forwarding_remains_available_when_own_result_is_disabled():
    _, wm, _, _ = _make_services()
    wm.create_new('forwarding')
    origin = wm.add_node('start_node')
    source = wm.add_node('file_view_node')
    consumer = wm.add_node('text_output_node')
    wm.update_node_config(source, {'dead_drop_passthrough': True, 'transient_output': False})
    wm.connect(origin, 'default', source, 'file')
    wm.connect(source, 'default', consumer, 'input')
    screen = NodeConfigScreen(wm._factory, wm, consumer, wm.get_node_data(consumer))
    schema = screen._metadata_for_type('text_output_node')['config_schema']
    result = screen._prune_unavailable_source_options(schema, {}, {})
    assert 'Upstream payload' in result['input_source']['options']
