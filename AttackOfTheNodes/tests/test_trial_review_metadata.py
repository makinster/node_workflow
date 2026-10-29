"""Shared authoring explanations used by the drafter and judge."""
import pytest
from backend import authoring, node_catalogue
from backend.node_factory import NodeFactory


@pytest.mark.asyncio
async def test_every_transient_option_has_shared_behavior_docs():
    factory = NodeFactory()
    cfg = factory.metadata_for_type('node_catalogue_node')['default_config']
    result = await node_catalogue.build(factory, dict(cfg, format='JSON', max_chars=200000))
    entries = {e['type']: e for e in result['entries']}
    for meta in factory.get_node_types_metadata():
        docs = meta['standard_key_docs']
        if 'transient_output' not in meta['default_config']:
            assert docs == {}
            continue
        expected = docs['transient_output']
        assert 'true passes the output on to the next node; false sends no output on' in expected
        assert ('Default: ' + str(meta['default_config']['transient_output']).lower()) in expected
        assert authoring.describe_node_type(factory, meta['type'])['standard_key_docs'] == docs
        if meta['type'] in entries:
            assert entries[meta['type']]['standard_key_docs'] == docs
    text = await node_catalogue.build(factory, dict(cfg, scope='Filtered', search='file_reader_node'))
    assert 'Standard config: transient_output:' in text
    assert 'false sends no output on' in text


def test_start_distinguishes_passing_input_from_showing_text():
    meta = NodeFactory().metadata_for_type('start_node')['node_metadata']
    assert 'to the next node as its input' in meta['purpose']
    assert 'Start itself shows nothing' in meta['not_for']
    assert 'never displayed' not in str(meta)


def test_judge_focuses_on_requested_inputs():
    import json
    from tools.draft_trials.runner import SPEC
    prompt = json.loads(SPEC.read_text())['nodes']['judge_question']['config']['template']
    assert 'ordinary inputs the request describes' in prompt
    assert 'edge cases the request never raised' in prompt
