"""Real source/output routing and explicit terminal-node behavior."""
import pytest
from backend.node_factory import NodeFactory
from backend.supervisor import Supervisor
from backend.vault_declarations import standard_vault_writes
from tests.generated.test_file_view_node import _make_context


@pytest.mark.parametrize('transient', [True, False])
async def test_start_writes_typed_vault_and_independent_transient(transient):
    node = NodeFactory().create_node('start_node', 'start')
    node.config.update(greeting='hello', vault_write=True, vault_write_key='greeting', transient_output=transient,
                       membank_outputs=[{'id':'old_a'}, {'output':'old_b'}])
    context, done, errors, _ = _make_context()
    await node.execute(context)
    assert not errors
    assert done[0]['data'] == ({'default':'hello'} if transient else {})
    assert context.memory_bank.read_persistent_by_type('string') == dict.fromkeys(['greeting','old_a','old_b'], 'hello')


@pytest.mark.parametrize('source,expected', [('Vault','vault value'), ('Upstream payload','upstream value')])
async def test_text_output_reads_only_selected_source_and_publishes(source, expected):
    node = NodeFactory().create_node('text_output_node','out')
    node.config.update(input_source=source,input_vault_key='text',label='Result',template='<{input}>')
    context, done, errors, _ = _make_context(inputs={'input':'upstream value'})
    context.memory_bank.store_persistent('text','vault value',type_tag='string')
    await node.execute(context)
    assert not errors
    assert done[0]['data']['default'] == f'[Result] <{expected}>'
    assert not done[0].get('terminate_branch')
    assert context.memory_bank.read_persistent('output_log') == [f'[Result] <{expected}>']


async def test_missing_vault_does_not_fall_back_to_upstream():
    node = NodeFactory().create_node('text_output_node','out')
    node.config.update(input_source='Vault',input_vault_key='absent')
    context, done, errors, _ = _make_context(inputs={'input':'wrong'})
    await node.execute(context)
    assert not done
    assert 'unavailable' in str(errors[0])
    assert context.memory_bank.read_persistent('output_log') is None


async def test_text_prompt_retained_after_source_resolution():
    node = NodeFactory().create_node('text_output_node','out')
    node.config.update(request_user_input=True)
    context, done, errors, _ = _make_context(inputs={'input':'old'})
    async def answer(prompt):
        assert prompt == 'Enter a value:'
        return 'new'
    context.signal_waiting_for_input = answer
    await node.execute(context)
    assert not errors
    assert done[0]['data']['default'] == '[Output] new'


async def test_text_output_payload_is_captured_before_continuing_connected_path():
    context, done, errors, _ = _make_context()
    node = NodeFactory().create_node('text_output_node','out')
    await node.execute(context)
    supervisor = object.__new__(Supervisor)
    supervisor.current_node_id = 'out'
    supervisor._memory_bank = context.memory_bank
    class ConnectedGraph:
        def find_next_node_id(self, *args, **kwargs):
            return 'next_node'
    supervisor._workflow_map = ConnectedGraph()
    assert supervisor._handle_payload(done[0]) == 'next_node'
    assert context.memory_bank.read_transient('out','default') == '[Output] '


async def test_end_explicitly_terminates():
    node = NodeFactory().create_node('end_node','end')
    context, done, errors, _ = _make_context()
    await node.execute(context)
    assert not errors
    assert done[0]['terminate_branch']


def test_multiple_file_vault_declarations():
    config = {'vault_write':True,'vault_write_key':'primary','additional_files':[
        {'id':'one','path':'one.md','vault_key':'one'}, {'id':'selected','path':'two.md','vault_key':''}]}
    meta = {'output_port_metadata':{'default':{'data_type':'file'}}}
    assert standard_vault_writes('file_view_node',config,meta) == {'primary':'file','one':'file'}


def test_declared_start_vault_is_valid_before_execution():
    from backend.validator import validate_workflow
    from tests.test_debug_nodes import _make_services
    _, wm, _, _ = _make_services()
    wm.create_new('start-vault-output')
    start = wm.add_node('start_node')
    wm.update_node_config(start, {'vault_write':True, 'vault_write_key':'greeting'})
    output = wm.add_node('text_output_node')
    wm.update_node_config(output, {'input_source':'Vault','input_vault_key':'greeting'})
    wm.connect(start, 'default', output, 'input')
    result = validate_workflow(wm,wm._factory)
    assert result['success'], result


def test_additional_file_declaration_is_valid_and_type_checked():
    from backend.validator import validate_workflow
    from tests.test_debug_nodes import _make_services
    _, wm, _, _ = _make_services()
    wm.create_new('additional-file-vault')
    start = wm.add_node('start_node')
    manager = wm.add_node('file_view_node')
    wm.update_node_config(manager, {'additional_files':[{'id':'second','path':'later.md','vault_key':'second'}]})
    output = wm.add_node('file_output_node')
    wm.update_node_config(output, {'file_path_source':'Vault','file_path_vault_key':'second',
                                            'content_source':'Vault','content_vault_key':'second'})
    wm.connect(start,'default',manager,'file')
    wm.connect(manager,'default',output,'file_path')
    result = validate_workflow(wm,wm._factory)
    assert not any('not declared: second' in error['message'] for error in result['errors'])
    assert any('incompatible with string' in warning['message'] for warning in result['warnings'])


def test_blank_vault_selection_is_preflight_error():
    from backend.validator import validate_workflow
    from tests.test_debug_nodes import _make_services
    _, wm, _, _ = _make_services()
    wm.create_new('blank-vault-selection')
    start = wm.add_node('start_node')
    output = wm.add_node('text_output_node')
    wm.update_node_config(output, {'input_source':'Vault','input_vault_key':''})
    wm.connect(start,'default',output,'input')
    result = validate_workflow(wm,wm._factory)
    assert any("Vault source for 'input' requires a key" == entry['message'] for entry in result['errors'])
