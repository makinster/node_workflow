"""Real-node source audit fixtures. Never execute a network/agent node."""
from backend.node_factory import NodeFactory
from backend.workflow_map import WorkflowMap
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank


def graph(kind='file_reader_node', scenario='unknown'):
    factory = NodeFactory()
    bus = EventBus()
    wm = WorkflowMap(factory, bus)
    wm.create_new('Source menu audit')
    mb = MemoryBank(bus)
    def add(kind, **changes):
        node = wm.add_node(kind)
        wm.update_node_config(node, {**wm.get_node_data(node)['config'], **changes})
        return node
    start = add('start_node')
    if scenario == 'unknown':
        writer = add('set_variable_node', variable_name='dynamic_value')
    elif scenario == 'collision':
        writer = add('context_pack_node', vault_write=True, vault_write_key='shared_value')
        other = add('pick_one_node', details_vault_write=True, details_vault_key='shared_value')
        wm.connect(start, 'default', other, 'input')
    elif scenario == 'child':
        writer = add('subworkflow_node', results=[dict(id='result', name='answer', to='Vault', vault_key='child_answer')])
    elif scenario == 'fanin':
        writer = add('file_view_node')
    else:
        raise ValueError(scenario)
    writer_port = factory.node_input_ports(wm.get_node_data(writer))[0]
    wm.connect(start, 'default', writer, writer_port)
    consumer = add(kind)
    port = 'file' if kind == 'file_view_node' else 'input'
    if scenario == 'fanin':
        wm.connect(start, 'default', consumer, port)  # incompatible first parent
    wm.connect(writer, 'default', consumer, port)
    mb.store_persistent('run_text', 'hello', type_tag='string')
    return factory, wm, mb, consumer
