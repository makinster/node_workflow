"""Read-only full-validator inventory of bundled graphs, not execution of AI/IO."""
import hashlib
import json
import os
from pathlib import Path

from backend import authoring
from backend.event_bus import EventBus
from backend.node_factory import NodeFactory
from backend.validator import validate_workflow
from backend.workflow_map import WorkflowMap
from tools.claims_compatibility import workflow_specs

ROOT=Path(__file__).parents[1]


class EmptySecrets:
    def has_key(self, key):
        return False


def bundled_validation():
    factory=NodeFactory();rows=[]
    for folder in ['examples','docs/delivery_tests']:
        for path in sorted((ROOT/folder).rglob('*.json')):
            for pointer,spec in workflow_specs(json.loads(path.read_text())):
                wm=WorkflowMap(factory,EventBus());wm.create_new('Validation audit')
                ids={}
                for handle,node in spec['nodes'].items():
                    ids[handle]=wm.add_node(node['type'],alias=node.get('alias',''))
                    config=dict(wm.get_node_data(ids[handle])['config'])
                    config.update(node.get('config') or {})
                    wm.update_node_config(ids[handle],config)
                # Reuse authoring's reference resolver; a spec handle is not a
                # saved node ID (notably Wait Until targets).
                problems=[]
                for handle,node in spec['nodes'].items():
                    config=dict(wm.get_node_data(ids[handle])['config'])
                    for field in authoring.NODE_REFERENCE_FIELDS.get(node['type'],()):
                        if field in config:
                            config[field]=authoring._translated_references(config[field],ids,handle,field,lambda *args,**kw:problems.append(args))
                    wm.update_node_config(ids[handle],config)
                assert not problems,problems
                if spec.get('callable'):wm.set_callable(True)
                for edge in spec['connections']:
                    src,port=edge['from'].rsplit('.',1);dst,slot=edge['to'].rsplit('.',1)
                    wm.connect(ids[src],port,ids[dst],slot)
                result=validate_workflow(wm,factory,secrets_manager=EmptySecrets())
                handles={v:k for k,v in ids.items()}
                rows.append(dict(path=path.relative_to(ROOT).as_posix(),pointer=pointer,
                    errors=[dict(node=handles.get(e.get('node_id'),''),code=e['code'],message=e['message']) for e in result['errors']],
                    warnings=sorted({w['code'] for w in result['warnings']})))
    return rows


def test_bundled_graphs_pass_the_app_checker():
    rows=bundled_validation()
    assert len(rows)==17
    # The packet preserves a rejected historical draft with display labels
    # pasted into port IDs. It is not a valid bundled workflow.
    bad=[r for r in rows if r['errors']]
    assert [(r['path'],r['pointer'],[e['code'] for e in r['errors']]) for r in bad]==[
        ('docs/delivery_tests/draft-a-workflow.json','/trial/draft_spec',['undeclared_port']*4)]
    if os.getenv('AOTN_APP_VALIDATION_REPORT'):
        data=dict(schema_version=1,base_revision='821688d461f17166d78ded5dd3fc182b708b929e',
                  graph_count=len(rows),graphs=rows,secrets='Empty local store: no keys read',
                  scope='All authored graph objects in examples and docs/delivery_tests; existing full validate_workflow, no execution.',
                  sources={p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in ['frontend/app.py','frontend/screens/editor.py','backend/validator.py','tests/test_app_run_validation.py','tests/test_app_run_compatibility.py']})
        Path(os.environ['AOTN_APP_VALIDATION_REPORT']).write_text(json.dumps(data,indent=2)+'\n')
