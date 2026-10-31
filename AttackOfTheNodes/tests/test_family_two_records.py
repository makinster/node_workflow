"""Final flow record/schema/provenance exports; Stage 1 admits Merge alone."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from backend import authoring, meta_workflow, node_catalogue
from backend.flow_behaviors import FLOW_RECORD_TYPES, FLOW_POLICY, flow_provenance, flow_template
from backend.node_factory import NodeFactory
from backend.node_metadata import (NODE_METADATA, PENDING_REVIEW, DEV_TEST_ONLY,
    canonical_json, content_sha256, record_problems)
from backend.node_errors import NodeError
from backend.palette_selection import ADMITTED
from tests.test_flow_behaviors import reference

F=NodeFactory()


def spec():
    return dict(format=authoring.FORMAT,name='Flow export',nodes={
        'start':{'type':'start_node'},'split':{'type':'branch_node'},
        'a':{'type':'text_transform_node','config':{'operation':'uppercase'}},
        'b':{'type':'text_transform_node','config':{'operation':'lowercase'}},
        'join':{'type':'merge_node'},'end':{'type':'end_node'}},connections=[
        {'from':a,'to':b} for a,b in [('start.default','split.input'),('split.path_a','a.input'),
        ('split.path_b','b.input'),('a.default','join.path_a'),('b.default','join.path_b'),('join.default','end.input')]])


def test_final_membership_preserves_state_nodes_beacon_and_admission():
    assert {'merge_node','wait_until_node'}<=set(NODE_METADATA)
    assert len(NODE_METADATA)==18 and len(PENDING_REVIEW)==25 and len(DEV_TEST_ONLY)==16
    for kind in ['set_variable_node','get_variable_node']:
        assert kind in PENDING_REVIEW and kind not in DEV_TEST_ONLY
    assert 'branch_end_node' not in DEV_TEST_ONLY and 'branch_end_node' not in ADMITTED
    assert 'merge_node' in ADMITTED and 'wait_until_node' not in ADMITTED


@pytest.mark.parametrize('kind',sorted(FLOW_RECORD_TYPES))
def test_flow_templates_are_exported_validated_hashed_and_bounded(kind):
    record=F.metadata_for_type(kind)['node_metadata']
    assert record['flow_behavior']==flow_template(kind)
    assert not record_problems(kind,record)
    assert len(canonical_json(record).encode())<=4096
    changed=deepcopy(record);changed['flow_behavior']['pass_number']=2
    assert record_problems(kind,changed) and content_sha256(record)!=content_sha256(changed)
    changed=deepcopy(record);changed['flow_behavior']['pass_number']=True
    assert record_problems(kind,changed)
    changed=deepcopy(record);changed['flow_behavior']['basis']='guessed'
    assert record_problems(kind,changed)
    assert authoring.describe_node_type(F,kind)['node_metadata']['flow_behavior']==record['flow_behavior']


@pytest.mark.asyncio
@pytest.mark.parametrize('detail',['Brief','Compact','Detailed'])
async def test_catalogue_exports_complete_flow_under_existing_caps(detail):
    c=F.create_config_template('node_catalogue_node')
    c.update(scope='Filtered',search='wait',detail=detail,format='JSON')
    # A catalogue view is not drafter admission; exact unadmitted selection stays rejected.
    result=await node_catalogue.build(F,c)
    assert result['flow_provenance']==flow_provenance() and result['complete']
    assert {'merge_node','wait_until_node'}<={row['type'] for row in result['entries']}
    for row in result['entries']:
        if row['type'] not in {'merge_node','wait_until_node'}:continue
        if detail=='Brief': assert row['flow_summary']
        else: assert row['node_metadata']['flow_behavior']['kind'] in {'join','wait'}
    assert len(json.dumps(result,ensure_ascii=False).encode())<256*1024
    c['max_chars']=512
    with pytest.raises(NodeError) as error:
        await node_catalogue.build(F,c)
    assert error.value.code=='catalogue_too_large'


def test_check_exports_stable_handle_flow_data_with_provenance():
    checked=authoring.check_workflow_spec(F,spec())
    assert checked['ok'],checked['diagnostics']
    flow=checked['flow_analysis'];merge=flow['merges']['join']
    assert flow['schema_version']==1 and flow['policy']==FLOW_POLICY
    assert flow['provenance']==flow_provenance()
    assert merge['group_roots']==['split']
    assert list(merge['slots'])==['path_a','path_b']
    assert merge['slots']['path_a']['producers'][0]['source_id']=='a'
    assert merge['slots']['path_a']['cardinality']=='one'
    assert 'fewest nested splits' in merge['summary'] and 'shallowest depth' not in merge['summary']
    serialized=json.dumps(flow)
    assert not any(nid in serialized for nid in checked['nodes'].values())


@pytest.mark.asyncio
async def test_check_node_flow_report_is_complete_or_size_error(monkeypatch):
    c=F.create_config_template('check_workflow_spec_node')
    parsed,report=await meta_workflow.check(F,json.dumps(spec()),64000)
    assert parsed==spec() and report['flow_analysis']['merges']['join']['slots']['path_a']['cardinality']=='one'
    assert len(json.dumps(report,ensure_ascii=False,separators=(',',':')))<=meta_workflow.FLOW_REPORT_CHARS
    monkeypatch.setattr(meta_workflow,'FLOW_REPORT_CHARS',200)
    with pytest.raises(NodeError) as error:await meta_workflow.check(F,json.dumps(spec()),64000)
    assert error.value.code=='spec_too_large'


def test_provenance_covers_engine_policy_and_analysis_source():
    p=flow_provenance()
    assert p['schema_version']==1 and len(p['policy_sha256'])==len(p['source_sha256'])==64
    assert set(p['runtime_sources'])=={'master_state.py','supervisor.py','run_context.py','wait_registry.py','node_base.py','node_errors.py'}
