"""All registered input contracts, real forms, and every compatible writer.

The dated JSON is a reviewed runtime expectation, independent of UI generation.
A changed execute() requires re-audit, rather than silently blessing schema drift.
"""
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import pytest
from textual.app import App
from textual.widgets import Select
from backend.data_types import CANONICAL_TYPES, types_compatible
from backend.event_bus import EventBus
from backend.memory_bank import MemoryBank
from backend.node_factory import NodeFactory
from backend.vault_declarations import vault_output_fields
from backend.workflow_map import WorkflowMap
from frontend.screens.node_config import NodeConfigScreen
from frontend.widgets.form_generator import build_form
from tests.source_menu_fixtures import graph

AUDIT=Path(__file__).parents[1]/'docs/audits/source_menus_2026_10_26/contracts.json'
CONTRACTS=json.loads(AUDIT.read_text())['nodes']
SOURCES={'Upstream payload':'upstream','Vault':'vault','Configured':'configured'}


def check_contract(factory, record):
    cls=factory._node_registry[record['node_type']]
    assert set(cls.input_ports)==set(record['ports']), record['node_type']
    assert hashlib.sha256(inspect.getsource(cls.execute).encode()).hexdigest()==record['runtime_sha256'], 'Runtime changed; re-audit acceptance'
    for port,row in record['ports'].items():
        if row['mode']!='standard':continue
        info=cls.input_port_metadata[port]
        assert set(info['sources'])==set(row['accepted_sources']),(cls.node_type,port,'declared sources')
        schema=cls.config_schema
        offered={SOURCES[value] for value in schema[row['control']]['options'] if value in SOURCES}
        assert offered==set(row['accepted_sources']),(cls.node_type,port,'offered sources')
        assert info['data_type']==row['data_type']
        if 'vault' in row['accepted_sources']:
            field=schema[port+'_vault_key']
            assert field['vault_type']==row['data_type']
            assert field['visible_when'][row['control']]=='Vault'
        if 'configured' in row['accepted_sources']:
            name=info.get('configured_field',port)
            assert schema[name]['visible_when'][row['control']]=='Configured'


def test_registry_is_exhaustive():
    assert {r['node_type'] for r in CONTRACTS}==set(NodeFactory().get_registered_types())


@pytest.mark.parametrize('record',CONTRACTS,ids=lambda r:r['node_type'])
def test_every_registered_runtime_declaration_and_schema(record):
    check_contract(NodeFactory(),record)


def test_consistency_detector_rejects_deliberately_broken_node(monkeypatch):
    factory=NodeFactory();record=next(r for r in CONTRACTS if r['node_type']=='ask_local_model_node')
    cls=factory._node_registry[record['node_type']]
    broken=deepcopy(cls.config_schema)
    broken['context_source']['options'].remove('Vault')
    monkeypatch.setattr(cls,'config_schema',broken)
    with pytest.raises(AssertionError,match='offered sources'):check_contract(factory,record)


class Host(App):
    CSS_PATH=str(Path(__file__).parents[1]/'frontend/styles.tcss')
    def __init__(self,factory,wm,mb,node):super().__init__();self.args=(factory,wm,mb,node)
    def on_mount(self):
        f,wm,mb,node=self.args
        self.push_screen(NodeConfigScreen(f,wm,node,wm.get_node_data(node),memory_bank=mb))


STANDARD=[r for r in CONTRACTS if any(p['mode']=='standard' for p in r['ports'].values())]
@pytest.mark.asyncio
@pytest.mark.parametrize('record',STANDARD,ids=lambda r:r['node_type'])
async def test_actual_ui_sources_and_visible_fields_for_all_standard_ports(record):
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('All sources')
    mb=MemoryBank(EventBus())
    for tag in CANONICAL_TYPES:
        for number in range(12):mb.store_persistent(f'{tag}_{number}',None,type_tag=tag)
    files=wm.add_node('start_node')
    wm.update_node_config(files, {'rows':[dict(id=f'f{n}',name=f'file_{n}',type='file',value='',required=False,to='Vault',vault_key=f'file_{n}') for n in range(12)]})
    node=wm.add_node(record['node_type'])
    for port,row in record['ports'].items():
        # Distinct unknown-type producers: every source is eligible; duplicate
        # source prevention therefore doesn't conceal a contract mismatch.
        writer=wm.add_node('get_variable_node')
        wm.connect(writer,'default',node,port)
    cfg=deepcopy(wm.get_node_data(node)['config'])
    if 'context_input_count' in cfg:cfg['context_input_count']='8'
    wm.update_node_config(node,cfg)
    app=Host(factory,wm,mb,node)
    async with app.run_test(size=(110,38)) as pilot:
        await pilot.pause();screen=app.screen
        for port,row in record['ports'].items():
            if row['mode']!='standard':continue
            selector=screen.query_one('#field-'+row['control'],Select)
            actual={SOURCES[value] for _,value in selector._options if value in SOURCES}
            assert actual==set(row['accepted_sources']),(record['node_type'],port,selector._options)
            if 'vault' in actual:
                selector.value='Vault';await pilot.pause()
                key=screen.query_one(f'#field-{port}_vault_key',Select)
                assert key.display
                expected={f'{tag}_{number}' for tag in CANONICAL_TYPES if types_compatible(tag,row['data_type']) for number in range(12)}
                assert expected <= {value for _,value in key._options}
            if 'configured' in actual:
                selector.value='Configured';await pilot.pause()
                field=factory._node_registry[record['node_type']].input_port_metadata[port].get('configured_field',port)
                assert screen.query_one('#field-'+field).display
                assert not screen.query_one(f'#field-{port}_vault_key').display
            selector.value=cfg.get(row['control'],'Upstream payload');await pilot.pause()


@pytest.mark.parametrize('scenario,kind,key,wanted',[
    ('unknown','file_reader_node','dynamic_value','file'),
    ('collision','check_reply_node','shared_value','string'),
    ('child','text_output_node','child_answer','any')])
def test_regressions_hidden_compatible_writes(scenario,kind,key,wanted):
    f,wm,mb,node=graph(kind,scenario)
    screen=NodeConfigScreen(f,wm,node,wm.get_node_data(node),memory_bank=mb)
    opts=screen._vault_key_options({'key':{'vault_type':wanted}})
    assert key in {v for _,v in opts[wanted]}


@pytest.mark.asyncio
async def test_fanin_checks_every_parent_and_screen_mounts():
    f,wm,mb,node=graph('file_view_node','fanin')
    app=Host(f,wm,mb,node)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert 'Upstream payload' in {v for _,v in app.screen.query_one('#field-file_source',Select)._options}
        assert len(app.screen.query('.incoming-payload-summary'))==2


@pytest.mark.asyncio
async def test_every_standard_secondary_and_dynamic_writer_in_picker():
    factory=NodeFactory();wm=WorkflowMap(factory,EventBus());wm.create_new('Every writer')
    expected={}
    # A valid ordering before the consumer; no node is executed.
    previous=wm.add_node('start_node')
    for record in CONTRACTS:
        kind=record['node_type'];cls=factory._node_registry[kind]
        meta=factory.metadata_for_type(kind)
        ports=vault_output_fields(meta)
        if not ports:continue
        writer=wm.add_node(kind);cfg=deepcopy(wm.get_node_data(writer)['config'])
        for port,(enabled,key_field,_) in ports.items():
            key=f'{kind}_{port}';cfg[enabled]=True;cfg[key_field]=key
            expected[key]=meta['output_port_metadata'][port].get('data_type','any')
        wm.update_node_config(writer,cfg)
        resolved=factory.node_output_port_metadata(wm.get_node_data(writer))
        for port,(_,key_field,_) in ports.items():expected[cfg[key_field]]=resolved[port].get('data_type','any')
        if cls.input_ports:wm.connect(previous,'default',writer,cls.input_ports[0])
        previous=writer
    # Typed Start rows (including a Stash copy) and child result routes.
    start=wm.add_node('start_node')
    wm.update_node_config(start,{'rows':[dict(id='s',name='stashed_text',type='string',value='copied from Stash',required=False,to='Vault',vault_key='stash_copy')]})
    expected['stash_copy']='string'
    child=wm.add_node('subworkflow_node')
    wm.update_node_config(child,{'results':[dict(name='result',to='Both',vault_key='child_result')]})
    expected['child_result']='any'
    for kind,field in [('set_variable_node','variable_name'),('variable_setter_node','variable_name'),('counter_node','counter_name')]:
        writer=wm.add_node(kind);wm.update_node_config(writer,{field:kind+'_dynamic'})
        expected[kind+'_dynamic']='any'
    recall=wm.add_node('recall_node');wm.update_node_config(recall,{'expect':'string','vault_write':True,'vault_write_key':'recalled_text'})
    expected['recalled_text']='string'
    node=wm.add_node('context_pack_node');wm.connect(previous,'default',node,'input')
    # Put all isolated producers on incoming paths to this consumer as well.
    for writer in list(wm.get_all_node_data()):
        if writer!=node and wm.get_node_data(writer)['type']!='start_node':
            if not wm.get_node_data(writer).get('connections',{}).get('outputs'):wm.connect(writer,'default',node,'input')
    mb=MemoryBank(EventBus());mb.store_persistent('run_level_text','ready',type_tag='string');mb.store_persistent('run_level_record',{},type_tag='var')
    expected.update(run_level_text='string',run_level_record='var')
    screen=NodeConfigScreen(factory,wm,node,wm.get_node_data(node),memory_bank=mb)
    options=screen._vault_key_options({tag:{'vault_type':tag} for tag in CANONICAL_TYPES})
    for wanted in CANONICAL_TYPES:
        offered={value for _,value in options[wanted]}
        assert {key for key,tag in expected.items() if types_compatible(tag,wanted)} <= offered,(wanted,offered)
    # Record/list outputs are not text; dynamic any may be text. Never cast it.
    assert 'run_level_record' not in {v for _,v in options['string']}
    assert 'pick_one_node_details' not in {v for _,v in options['string']}
    assert 'ask_local_model_node_details' in {v for _,v in options['var']}
    # Exercise the actual nested Vault Select too, not only its option builder.
    from frontend.widgets.context_items import ContextItems
    app=Host(factory,wm,mb,node)
    async with app.run_test(size=(80,24)) as pilot:
        app.screen.query_one(ContextItems)._open_editor(0)
        await pilot.pause()
        app.screen.query_one('#row-source',Select).value='Vault'
        await pilot.pause()
        offered={value for _,value in app.screen.query_one('#row-key',Select)._options}
        assert set(expected) <= offered


def test_fanin_availability_does_not_depend_on_first_parent():
    f,wm,mb,node=graph('file_view_node','fanin')
    screen=NodeConfigScreen(f,wm,node,wm.get_node_data(node),memory_bank=mb)
    schema=f.metadata_for_type('file_view_node')['config_schema']
    offered=screen._prune_unavailable_source_options(schema,{}, {})['file_source']['options']
    assert 'Upstream payload' in offered


@pytest.mark.asyncio
async def test_custom_source_menus_match_runtime_and_reveal_their_fields():
    from backend.nodes.flow.subworkflow_node import INPUT_SOURCES
    from frontend.widgets.subworkflow_rows import SubworkflowInputEditor
    from frontend.widgets.context_items import ContextItemEditor
    from backend.context_pack import SOURCES as ROW_SOURCES
    from frontend.widgets.contract_rows import ContractRowEditor, FROM, RESULT
    from backend.contracts import RESULT_SOURCES
    # Production custom editors cover the sources that aren't <port>_source.
    editors=[
        (ContextItemEditor({},[],[('text [string]','text')]), '#row-source', set(ROW_SOURCES),
         [('Vault','#row-key-holder'),('Configured text','#row-text-holder'),('Upstream payload','#row-upstream')]),
        (SubworkflowInputEditor(dict(name='question',type='string',required=False,value=''),None),
         '#row-source', set(INPUT_SOURCES)|{'default'},
         [('Vault','#row-vault-key-row'),('Configured','#row-value-row'),('Stash','#row-stash-row')]),
        (ContractRowEditor(RESULT,dict(id='r',name='result',type='string',required=False),[]),
         '#row-to', set(RESULT_SOURCES),[]),
    ]
    for editor,selector_id,expected,fields in editors:
        class EditorHost(App):
            CSS_PATH=Host.CSS_PATH
            def on_mount(self):self.push_screen(editor)
        app=EditorHost()
        async with app.run_test() as pilot:
            await pilot.pause();selector=editor.query_one(selector_id,Select)
            assert {value for _,value in selector._options}==expected
            for source,field in fields:
                selector.value=source;await pilot.pause()
                assert editor.query_one(field).display
    factory=NodeFactory()
    for kind,field,expected in [
        ('http_request_node','body_source',{'config','input'}),
        ('conditional_node','left_value_source',{'input','variable'}),
        ('set_variable_node','value_source',{'input','literal'}),
    ]:
        class FormHost(App):
            CSS_PATH=Host.CSS_PATH
            def compose(self):
                cls=factory._node_registry[kind]
                form,self.get_values=build_form(cls.config_schema,cls.default_config)
                yield form
        app=FormHost()
        async with app.run_test() as pilot:
            await pilot.pause()
            assert {v for _,v in app.query_one('#field-'+field,Select)._options}==expected
