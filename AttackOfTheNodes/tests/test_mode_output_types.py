"""C3: an output type that depends on a node's settings is reported everywhere.

HTTP Request's response is text, or a file reference when "Response as" is
file. The node describes that per config (``describe_output_ports``); the
validator, the editor's auto-wiring and previews, the selector filter and
Vault typing all read it through ``backend.port_types``.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_mode_output_types.py -v
"""

from types import SimpleNamespace

import pytest

from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.port_types import accepts_producers, resolved_metadata, trace_producers
from backend.validator import validate_workflow
from backend.vault_declarations import typed_vault_writes
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


def _http(workflow_map, mode, alias="Fetch"):
    node_id = workflow_map.add_node("http_request_node", alias=alias)
    config = dict(workflow_map.get_node_data(node_id)["config"])
    config.update(url="https://example.com/data", response_mode=mode)
    workflow_map.update_node_config(node_id, config)
    return node_id


def _workflow(name):
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new(name)
    return workflow_map


@pytest.mark.parametrize("mode, expected", [("text", "string"), ("file", "file"), (None, "string")])
def test_http_request_describes_its_response_type_per_mode(mode, expected):
    config = {} if mode is None else {"response_mode": mode}
    ports = FACTORY.node_output_port_metadata({"type": "http_request_node", "config": config})
    assert ports["default"]["data_type"] == expected
    assert ports["default"]["name"] == "Response"


@pytest.mark.parametrize("mode, warns", [("text", True), ("file", False)])
def test_validator_uses_the_mode_type(mode, warns):
    workflow_map = _workflow(f"c3_validate_{mode}")
    start = workflow_map.add_node("start_node")
    fetch = _http(workflow_map, mode)
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(start, "default", fetch, "input")
    workflow_map.connect(fetch, "default", reader, "input")
    config = dict(workflow_map.get_node_data(reader)["config"])
    config["input_source"] = "Upstream payload"
    workflow_map.update_node_config(reader, config)

    mismatches = [w["message"] for w in validate_workflow(workflow_map, FACTORY)["warnings"]
                  if w.get("code") == "type_mismatch"]
    assert mismatches == (["Input 'File' expects file but Fetch sends string"] if warns else [])


@pytest.mark.parametrize("mode, port", [("file", "file_path"), ("text", "content")])
def test_auto_wiring_picks_the_port_for_the_mode(mode, port):
    """Audit case: HTTP in file mode into File Write wired into `content`."""
    from frontend.screens.editor import EditorScreen

    workflow_map = _workflow(f"c3_wire_{mode}")
    fetch = _http(workflow_map, mode)
    writer = workflow_map.add_node("file_output_node")
    fake = SimpleNamespace(
        workflow_map=workflow_map,
        factory=FACTORY,
        _metadata_for_type=lambda node_type: next(
            m for m in FACTORY.get_node_types_metadata() if m["type"] == node_type),
        _upstream_branch_port=lambda source, port: None,
    )
    fake._matching_typed_input_ports = lambda *args: EditorScreen._matching_typed_input_ports(fake, *args)
    chosen = EditorScreen._target_input_port_for_connection(
        fake, fetch, "default", writer, ["content", "file_path"])
    assert chosen == port


@pytest.mark.parametrize("mode, expected", [("file", "file"), ("text", "string")])
def test_preview_tracer_reports_the_mode_type(mode, expected):
    from frontend.node_io_display import trace_transient_producer

    workflow_map = _workflow(f"c3_preview_{mode}")
    fetch = _http(workflow_map, mode)
    sleep = workflow_map.add_node("sleep_node")
    workflow_map.connect(fetch, "default", sleep, "input")
    assert trace_transient_producer(workflow_map, FACTORY, sleep, "default")["data_type"] == expected
    assert trace_producers(workflow_map.get_all_node_data(), FACTORY, sleep, "default") == [(fetch, expected)]


@pytest.mark.parametrize("mode, fits", [("file", True), ("text", False)])
def test_selector_filter_follows_the_mode(mode, fits):
    workflow_map = _workflow(f"c3_selector_{mode}")
    fetch = _http(workflow_map, mode)
    types = [t for _, t in trace_producers(workflow_map.get_all_node_data(), FACTORY, fetch, "default")]
    assert accepts_producers(FACTORY, "file_reader_node", types) is fits


@pytest.mark.parametrize("mode, tag", [("file", "file"), ("text", "string")])
def test_vault_typing_reads_the_resolved_type(mode, tag):
    config = {"response_mode": mode, "vault_write": True, "vault_write_key": "page"}
    metadata = resolved_metadata(FACTORY, "http_request_node", config)
    assert typed_vault_writes("http_request_node", config, metadata) == {"page": tag}


def test_resolved_metadata_without_hook_is_the_static_metadata():
    static = next(m for m in FACTORY.get_node_types_metadata() if m["type"] == "random_number_node")
    resolved = resolved_metadata(FACTORY, "random_number_node", {"mode": "float"})
    assert resolved["output_port_metadata"]["default"]["data_type"] == "number"
    assert resolved["input_port_metadata"] == static["input_port_metadata"]


@pytest.mark.parametrize("mode, expected", [("file", "file"), ("text", "string")])
def test_details_panel_shows_the_mode_type(mode, expected):
    """PR 59 review: the editor's details panel showed Response [any]."""
    import asyncio

    from textual.app import App

    from frontend.screens.editor import EditorScreen

    workflow_map = _workflow(f"c3_details_{mode}")
    start = workflow_map.add_node("start_node")
    fetch = _http(workflow_map, mode)
    workflow_map.connect(start, "default", fetch, "input")
    editor = EditorScreen(FACTORY, workflow_map)

    class EditorApp(App):
        def on_mount(self):
            self.push_screen(editor)

    seen = {}

    async def run():
        async with EditorApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.1)
            node = workflow_map.get_node_data(fetch)
            lines = editor._detail_output_lines(node, editor._metadata_for_type("http_request_node"))
            seen["first"] = str(lines[0])

    asyncio.run(run())
    assert seen["first"] == f"  Response  \\[[#4EC9B0]{expected}[/]]"
