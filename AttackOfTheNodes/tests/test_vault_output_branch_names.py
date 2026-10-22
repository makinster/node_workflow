"""Only downstream paths receive branch-name controls on Parameters."""
import pytest
from textual.app import App
from textual.widgets import TabbedContent

from backend.event_bus import EventBus
from backend.node_base import Node
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen


class WithDetails(Node):
    node_type = 'test_vault_details'
    display_name = 'With details'
    input_ports = []
    output_ports = ['default', 'details']
    output_port_metadata = {
        'default': {'name': 'Answer', 'data_type': 'string', 'to': ['downstream', 'vault']},
        'details': {'name': 'Pick details', 'data_type': 'var', 'to': ['vault']},
    }
    ui_hints = {'standard_output': True}

    async def execute(self, context):
        pass


def configured(node_type):
    factory = NodeFactory()
    factory._node_registry[WithDetails.node_type] = WithDetails
    workflow = WorkflowMap(factory, EventBus())
    workflow.create_new('Routing controls')
    node_id = workflow.add_node(node_type)
    return NodeConfigScreen(factory, workflow, node_id, workflow.get_node_data(node_id))


@pytest.mark.asyncio
async def test_vault_only_output_does_not_create_branch_names():
    class Host(App):
        CSS_PATH = '../frontend/styles.tcss'

        def on_mount(self):
            self.push_screen(configured(WithDetails.node_type))

    async with Host().run_test(size=(80, 24)) as pilot:
        screen = pilot.app.screen
        screen.query_one('#node-config-tabs', TabbedContent).active = 'node-config-tab-parameters'
        await pilot.pause()
        assert not screen.query('#field-default_label')
        assert not screen.query('#field-details_label')


def test_actual_branches_keep_branch_name_fields():
    screen = configured('branch_node')
    metadata = screen._metadata_for_type('branch_node')
    schema = screen._schema_with_generated_branch_labels(metadata, metadata['config_schema'])
    assert 'path_a_label' in schema and 'path_b_label' in schema
