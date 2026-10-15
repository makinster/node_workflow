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
    no_op = workflow_map.add_node("no_op_node")
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
    assert screen._validation_type(
        "Input 'File' expects file but Dice sends number") == "Type mismatch"
