"""C2: one edge compatibility rule for connector choice, Source dropdowns and preflight.

Run from AttackOfTheNodes/:
    ../.venv/bin/python -m pytest tests/test_edge_compatibility.py -v
"""

from types import SimpleNamespace

import pytest

from backend.data_types import describe_value, input_mismatch_message, types_compatible
from backend.event_bus import EventBus
from backend.file_refs import file_reference
from backend.node_factory import NodeFactory
from backend.nodes.file_reader_node import FileReaderNode
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap

FACTORY = NodeFactory()


def _workflow(name):
    workflow_map = WorkflowMap(FACTORY, EventBus())
    workflow_map.create_new(name)
    return workflow_map


def _set(workflow_map, node_id, **overrides):
    config = dict(workflow_map.get_node_data(node_id)["config"])
    config.update(overrides)
    workflow_map.update_node_config(node_id, config)


def _edge_warnings(result, node_id):
    return [w["message"] for w in result["warnings"]
            if w["node_id"] == node_id and w["message"].startswith("Input '")]


# --- The rule ----------------------------------------------------------------


@pytest.mark.parametrize("actual, wanted, ok", [
    ("number", "file", False),
    ("number", "string", False),
    ("string", "file", False),
    ("file", "string", False),
    ("file", "file", True),
    ("string", "string", True),
    ("any", "file", True),
    ("number", "any", True),
    (None, "file", True),
    ("", "string", True),
    ("boolean", "bool", True),
])
def test_types_compatible(actual, wanted, ok):
    assert types_compatible(actual, wanted) is ok


def test_describe_value_names_the_shape():
    assert describe_value(42) == "a number (42)"
    assert describe_value(True) == "true/false (True)"
    assert describe_value(None) == "nothing"
    assert describe_value("hello") == "text ('hello')"
    assert describe_value(file_reference("/tmp/a.txt")) == "a file reference"
    assert describe_value({"a": 1}) == "an object"
    assert describe_value([1, 2]) == "a list of 2"
    assert input_mismatch_message("File", "Upstream payload", "file", 7) == (
        "Input 'File' (Upstream payload) expects a file reference but got a number (7)"
    )


# --- Preflight ---------------------------------------------------------------


def test_random_number_into_file_reader_upstream_warns():
    workflow_map = _workflow("c2_random_to_reader")
    start = workflow_map.add_node("start_node")
    number = workflow_map.add_node("random_number_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(start, "default", number, "input")
    workflow_map.connect(number, "default", reader, "input")
    _set(workflow_map, reader, input_source="Upstream payload")

    result = validate_workflow(workflow_map, FACTORY)
    assert result["success"] is True, result["errors"]
    assert _edge_warnings(result, reader) == [
        "Input 'File' expects file but Random Number sends number"
    ]


def test_inactive_upstream_edge_does_not_warn():
    workflow_map = _workflow("c2_configured_reader")
    number = workflow_map.add_node("random_number_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(number, "default", reader, "input")
    _set(workflow_map, reader, input_source="Configured", file_path="/tmp/x.txt")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == []


def test_pass_through_chain_is_traced_to_the_producer():
    workflow_map = _workflow("c2_sleep_chain")
    number = workflow_map.add_node("random_number_node", alias="Dice")
    sleep = workflow_map.add_node("sleep_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(number, "default", sleep, "input")
    workflow_map.connect(sleep, "default", reader, "input")
    _set(workflow_map, reader, input_source="Upstream payload")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == [
        "Input 'File' expects file but Dice sends number"
    ]


def test_any_paths_keep_working():
    workflow_map = _workflow("c2_any_path")
    number = workflow_map.add_node("random_number_node")
    # C4: No-Op now forwards (number would flow through); Echo computes its
    # own untyped output, which is what this test needs.
    no_op = workflow_map.add_node("echo_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(number, "default", no_op, "input")
    workflow_map.connect(no_op, "default", reader, "input")
    _set(workflow_map, reader, input_source="Upstream payload")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == []


def test_matching_file_edge_does_not_warn():
    workflow_map = _workflow("c2_file_to_reader")
    writer = workflow_map.add_node("file_output_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(writer, "default", reader, "input")
    _set(workflow_map, writer, content_source="Configured", content="x",
         file_path="/tmp/out.txt", pass_through=False)
    _set(workflow_map, reader, input_source="Upstream payload")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == []


def test_number_into_text_port_warns():
    workflow_map = _workflow("c2_number_to_content")
    number = workflow_map.add_node("random_number_node")
    writer = workflow_map.add_node("file_output_node")
    workflow_map.connect(number, "default", writer, "content")
    _set(workflow_map, writer, content_source="Upstream payload", file_path="/tmp/out.txt")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), writer) == [
        "Input 'Content' expects string but Random Number sends number"
    ]


# --- Runtime -----------------------------------------------------------------


async def test_file_reader_runtime_error_names_port_and_shapes():
    node = FileReaderNode("reader", {"input_source": "Upstream payload"})
    done, errors = [], []
    context = SimpleNamespace(run_session=None, inputs={"input": 42},
                              signal_done=done.append, signal_error=errors.append)
    await node.execute(context)
    assert not done
    assert str(errors[0]) == (
        "File Reader: Input 'File' (Upstream payload) expects a file reference "
        "but got a number (42)."
    )


async def test_file_write_runtime_error_names_content_shape(tmp_path):
    node = FACTORY.create_node("file_output_node", "writer")
    node.config.update(content_source="Upstream payload", file_path=str(tmp_path / "o.txt"))
    done, errors = [], []
    context = SimpleNamespace(run_session=None, inputs={"content": 3.5},
                              memory_bank=None, signal_done=done.append,
                              signal_error=errors.append)
    await node.execute(context)
    assert not done
    assert str(errors[0]) == (
        "Input 'Content' (Upstream payload) expects text but got a number (3.5). "
        "Use File Reader to copy file contents."
    )


# --- One rule, three consumers ------------------------------------------------


def test_frontend_uses_the_backend_helpers():
    import backend.port_types as port_types
    import frontend.node_io_display as display

    assert display.is_pass_through_node is port_types.is_pass_through_node
    assert display.metadata_for_type is port_types.metadata_for_type


def test_connector_choice_matches_only_compatible_typed_ports():
    from frontend.screens.editor import EditorScreen

    workflow_map = _workflow("c2_connector_choice")
    number = workflow_map.add_node("random_number_node")
    reader_writer = workflow_map.add_node("file_output_node")
    fake = SimpleNamespace(
        workflow_map=workflow_map,
        factory=FACTORY,
        _metadata_for_type=lambda node_type: next(
            m for m in FACTORY.get_node_types_metadata() if m["type"] == node_type),
    )
    ports = ["content", "file_path"]
    assert EditorScreen._matching_typed_input_ports(fake, number, "default", reader_writer, ports) == []
    writer = workflow_map.add_node("file_output_node")
    assert EditorScreen._matching_typed_input_ports(
        fake, writer, "default", reader_writer, ports) == ["file_path"]


def test_validation_details_labels_the_warning():
    from frontend.screens.error_details import ErrorDetailsScreen

    screen = ErrorDetailsScreen({"validation": {"errors": [], "warnings": []}})
    assert screen._validation_type({
        "code": "type_mismatch",
        "message": "Input 'File' expects file but Dice sends number"}) == "Type mismatch"


@pytest.mark.parametrize("number_first", [True, False])
def test_every_producer_into_a_shared_pass_through_is_checked(number_first):
    """PR 56 review: Sleep forwards whichever source arrived, so all count."""
    workflow_map = _workflow(f"c2_shared_sleep_{number_first}")
    writer = workflow_map.add_node("file_output_node", alias="Save")
    number = workflow_map.add_node("random_number_node", alias="Dice")
    sleep = workflow_map.add_node("sleep_node")
    reader = workflow_map.add_node("file_reader_node")
    _set(workflow_map, writer, content_source="Configured", content="x", file_path="/tmp/out.txt")
    sources = [number, writer] if number_first else [writer, number]
    for source in sources:
        workflow_map.connect(source, "default", sleep, "input")
    workflow_map.connect(sleep, "default", reader, "input")
    _set(workflow_map, reader, input_source="Upstream payload")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == [
        "Input 'File' expects file but Dice sends number"
    ]


def test_trace_producers_lists_each_source_once_and_ends_on_cycles():
    from backend.port_types import trace_producers

    workflow_map = _workflow("c2_trace_cycle")
    number = workflow_map.add_node("random_number_node")
    first = workflow_map.add_node("sleep_node")
    second = workflow_map.add_node("sleep_node")
    workflow_map.connect(number, "default", first, "input")
    workflow_map.connect(second, "default", first, "input")
    workflow_map.connect(first, "default", second, "input")
    nodes = workflow_map.get_all_node_data()
    assert trace_producers(nodes, FACTORY, second, "default") == [(number, "number")]


# --- Branch paths and the Source dropdown (PR 56 follow-up) -------------------


def test_branch_path_forwards_its_input_type():
    workflow_map = _workflow("c2_branch_forward")
    number = workflow_map.add_node("random_number_node", alias="Dice")
    branch = workflow_map.add_node("branch_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(number, "default", branch, "input")
    workflow_map.connect(branch, "path_a", reader, "input")
    _set(workflow_map, reader, input_source="Upstream payload")

    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == [
        "Input 'File' expects file but Dice sends number"
    ]


@pytest.mark.parametrize("writer_type, warns", [
    ("file_output_node", False),
    ("random_number_node", True),
])
def test_vault_seeded_branch_path_takes_the_writer_type(writer_type, warns):
    workflow_map = _workflow(f"c2_branch_seed_{writer_type}")
    writer = workflow_map.add_node(writer_type, alias="Writer")
    branch = workflow_map.add_node("branch_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(writer, "default", branch, "input")
    workflow_map.connect(branch, "path_a", reader, "input")
    _set(workflow_map, writer, vault_write=True, vault_write_key="seed",
         content_source="Configured", content="x", file_path="/tmp/out.txt")
    _set(workflow_map, branch, branch_payload_sources={"path_a": "vault:seed"})
    _set(workflow_map, reader, input_source="Upstream payload")

    expected = ["Input 'File' expects file but Writer sends number"] if warns else []
    assert _edge_warnings(validate_workflow(workflow_map, FACTORY), reader) == expected


def _upstream_offered(workflow_map, node_id):
    """Whether File Reader's File source offers Upstream payload."""
    import asyncio

    from textual.app import App
    from textual.widgets import Select

    from backend.memory_bank import MemoryBank
    from frontend.screens.node_config import NodeConfigScreen

    screen = NodeConfigScreen(FACTORY, workflow_map, node_id,
                              workflow_map.get_node_data(node_id),
                              memory_bank=MemoryBank(EventBus()))
    seen = {}

    class ConfigApp(App):
        def on_mount(self):
            self.push_screen(screen)

    async def body():
        async with ConfigApp().run_test(size=(110, 40)) as pilot:
            await pilot.pause(0.1)
            select = screen.query_one("#field-input_source", Select)
            seen["options"] = {value for _label, value in select._options}

    asyncio.run(body())
    return "Upstream payload" in seen["options"]


@pytest.mark.parametrize("number_first", [True, False])
def test_dropdown_offers_upstream_when_any_producer_fits(number_first):
    workflow_map = _workflow(f"c2_dropdown_mixed_{number_first}")
    writer = workflow_map.add_node("file_output_node")
    number = workflow_map.add_node("random_number_node")
    sleep = workflow_map.add_node("sleep_node")
    reader = workflow_map.add_node("file_reader_node")
    for source in ([number, writer] if number_first else [writer, number]):
        workflow_map.connect(source, "default", sleep, "input")
    workflow_map.connect(sleep, "default", reader, "input")

    assert _upstream_offered(workflow_map, reader) is True


def test_dropdown_hides_upstream_when_no_producer_fits():
    workflow_map = _workflow("c2_dropdown_number_only")
    number = workflow_map.add_node("random_number_node")
    sleep = workflow_map.add_node("sleep_node")
    reader = workflow_map.add_node("file_reader_node")
    workflow_map.connect(number, "default", sleep, "input")
    workflow_map.connect(sleep, "default", reader, "input")

    assert _upstream_offered(workflow_map, reader) is False
