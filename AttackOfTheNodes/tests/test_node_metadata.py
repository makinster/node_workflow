"""Node metadata record v1: coverage, schema, projections, catalogue v2, review.

Completeness counts every registered class (debug, hidden, editor-only and
tombstone included), not the catalogue view. A type without a reviewed record
must sit in the migration ledger, and then it has no effect claims at all.
"""
import hashlib
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from backend import authoring, node_catalogue, node_metadata
from backend.node_errors import NodeError
from backend.node_execution_contracts import EXECUTION_CONTRACTS
from backend.node_factory import NodeFactory
from backend.node_metadata import (
    LIGHT_RECORD_TYPES, NODE_METADATA, PENDING_REVIEW, content_sha256, is_read_only,
    record_for, record_problems, selection, selection_problems,
)
from backend.nodes import ALL_NODE_CLASSES

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'backend/node_metadata_review.json').read_text())
V2 = json.loads((ROOT / 'docs/delivery_tests/specs/draft-a-workflow-v2.json').read_text())

# The ledger as opened on 2026-10-29. It may only shrink: a new node type
# needs a reviewed record in the same change, never a ledger entry.
LEDGER_AT_OPENING = frozenset("""
merge_node wait_until_node error_mux_node set_variable_node get_variable_node
variable_setter_node variable_reader_node random_number_node find_lines_node
read_lines_node check_reply_node context_pack_node node_catalogue_node
check_workflow_spec_node remember_node recall_node if_changed_node
disk_space_node file_age_node git_status_node file_view_node window_control_node
http_request_node record_event_node hermes_notify_node hermes_ask_node
hermes_investigate_node hermes_investigation_result_node ask_local_model_node
ask_claude_node chat_completion_node image_generation_node embedding_node
pick_one_node subworkflow_node echo_node logger_node sleep_node counter_node
memory_snapshot_node probe_node error_node random_branch_node deep_branch_node
no_op_node repeat_counter_node tombstone_node
""".split())


def good_record():
    return deepcopy(NODE_METADATA['file_output_node'])


# --- coverage --------------------------------------------------------------------

def test_every_registered_type_has_a_record_or_a_ledger_entry():
    ids = [getattr(cls, 'node_type', '') for cls in ALL_NODE_CLASSES]
    # Before the factory's dictionary could hide them.
    assert all(isinstance(i, str) and i for i in ids), 'empty node_type'
    assert [i for i, n in Counter(ids).items() if n > 1] == []
    registered = set(ids)
    assert set(NodeFactory().get_registered_types()) == registered
    assert not set(NODE_METADATA) & PENDING_REVIEW
    assert set(NODE_METADATA) | PENDING_REVIEW == registered
    assert len(registered) == len(NODE_METADATA) + len(PENDING_REVIEW)


def test_migration_ledger_only_shrinks():
    assert PENDING_REVIEW <= LEDGER_AT_OPENING
    assert LIGHT_RECORD_TYPES <= LEDGER_AT_OPENING | set(NODE_METADATA)


@pytest.mark.parametrize('node_type', sorted(NODE_METADATA))
def test_record_is_valid(node_type):
    assert record_problems(node_type, NODE_METADATA[node_type]) == []
    sel = selection(NODE_METADATA[node_type])
    assert selection_problems(node_type, sel) == []
    # The projections are different schemas: neither passes as the other.
    assert record_problems(node_type, sel) != []
    assert selection_problems(node_type, NODE_METADATA[node_type]) != []


# --- schema rules ------------------------------------------------------------------

def mutate(**changes):
    record = good_record()
    for path, value in changes.items():
        target = record
        *parents, last = path.split('__')
        for key in parents:
            target = target[key]
        if value is KeyError:
            del target[last]
        else:
            target[last] = value
    return record


@pytest.mark.parametrize('record,fragment', [
    (mutate(schema_version=True), 'schema_version'),
    (mutate(schema_version=2), 'schema_version'),
    (mutate(extra='x'), 'unknown keys'),
    (mutate(side_effects=KeyError), 'missing side_effects'),
    (mutate(needs=KeyError), 'missing needs'),
    (mutate(purpose='x' * 121), 'over the 120 limit'),
    (mutate(purpose=' leading'), 'leading or trailing'),
    (mutate(use_when='two\nlines'), 'single line'),
    (mutate(not_for='Café'), 'NFC'),
    (mutate(purpose=''), 'must not be empty'),
    (mutate(purpose=7), 'must be text'),
    (mutate(side_effects__possible=['controls_windows', 'writes_files']), 'canonical order'),
    (mutate(side_effects__possible=['writes_files', 'writes_files']), 'duplicate'),
    (mutate(side_effects__possible=['deletes_everything']), 'unknown values'),
    (mutate(side_effects__delegated=1), 'true or false'),
    (mutate(side_effects__delegated=True, side_effects__note=KeyError), 'required when delegated'),
    (mutate(needs__optional=['external_program'], needs__note=KeyError), 'needs.note'),
    (mutate(needs__unresolved=True, needs__optional=[], needs__note=KeyError), 'needs.note'),
    (mutate(needs__optional=['local_files']), 'both required and optional'),
    (mutate(cost_class='free'), 'cost_class'),
    (mutate(cost_class='variable'), 'cost_note'),
    (mutate(time_class='waits', time_note=KeyError), 'time_note'),
    (mutate(time_class='soon'), 'time_class'),
    (mutate(learnable_from=[]), 'learnable_from'),
    (mutate(learnable_from=['recording', 'example']), 'canonical order'),
    (mutate(execution_contract=KeyError), 'missing execution_contract'),
    (mutate(execution_contract__output_payload='x' * 513), 'over the 512 limit'),
    (mutate(execution_contract__extra='x'), 'unknown keys'),
])
def test_validator_rejects_with_a_named_problem(record, fragment):
    problems = record_problems('file_output_node', record)
    assert any(fragment in p for p in problems), problems


def test_text_limits_are_inclusive_and_no_clipping():
    record = mutate(purpose='p' * 120, use_when='u' * 200, not_for='n' * 200,
                    learnable_from=['example', 'recording'])
    assert record_problems('file_output_node', record) == []
    assert record['purpose'] == 'p' * 120


def test_whole_record_byte_ceiling():
    record = mutate(execution_contract__output_payload='é' * 512,
                    execution_contract__notes='é' * 512, purpose='é' * 120)
    record['side_effects']['note'] = 'é' * 240
    record['needs']['note'] = 'é' * 240
    record['use_when'] = 'é' * 200
    record['not_for'] = 'é' * 200
    record['time_note'] = 'é' * 160
    record['cost_note'] = 'é' * 160
    problems = record_problems('file_output_node', record)
    assert problems and 'byte' in problems[-1]


def test_light_records_for_debug_and_tombstone():
    light = {'schema_version': 1, 'purpose': 'Mark a deleted node; it errors if run.',
             'side_effects': {'possible': [], 'delegated': False},
             'needs': {'required': [], 'optional': [], 'unresolved': False}}
    assert record_problems('tombstone_node', light) == []
    assert selection_problems('tombstone_node', selection(light)) == []
    assert record_problems('tombstone_node', {**light, 'use_when': 'x'})  # light means light
    assert record_problems('end_node', light)  # user-facing nodes need the full record


# --- read-only is derived, never assumed ----------------------------------------------

def test_missing_data_is_never_read_only():
    factory = NodeFactory()
    assert is_read_only(None) is False
    for node_type in PENDING_REVIEW:
        assert record_for(node_type) is None
        assert factory.metadata_for_type(node_type)['node_metadata'] is None
    assert is_read_only(NODE_METADATA['conditional_node'])
    assert not is_read_only(NODE_METADATA['file_output_node'])
    assert not is_read_only(mutate(side_effects__possible=[], side_effects__delegated=True))


# --- ownership and projections ---------------------------------------------------------

@pytest.mark.parametrize('node_type', sorted(NODE_METADATA))
def test_factory_describe_and_legacy_projections_agree(node_type):
    factory = NodeFactory()
    record = NODE_METADATA[node_type]
    meta = factory.metadata_for_type(node_type)
    assert meta['node_metadata'] == record
    assert meta['execution_contract'] == record['execution_contract'] == EXECUTION_CONTRACTS[node_type]
    cls = factory._node_registry[node_type]
    assert meta['description'] == record['purpose'] == cls.description
    described = authoring.describe_node_type(factory, node_type)
    assert described['node_metadata'] == record
    assert described['execution_contract'] == record['execution_contract']
    assert described['description'] == record['purpose']


def test_helper_spec_descriptions_match_the_purpose():
    import sys
    sys.path.insert(0, str(ROOT.parent))
    from aotn_node_helper.generator import load_spec
    checked = set()
    for path in (ROOT.parent / 'aotn_node_helper/specs').iterdir():
        spec = load_spec(path)
        if spec['node_type'] in NODE_METADATA:
            assert spec['description'] == NODE_METADATA[spec['node_type']]['purpose'], path.name
            checked.add(spec['node_type'])
    assert checked  # the specs that exist for migrated types


def test_copies_are_independent():
    factory = NodeFactory()
    before = deepcopy(NODE_METADATA)
    record_for('start_node')['purpose'] = 'changed'
    rows = factory.get_node_types_metadata()
    next(r for r in rows if r['type'] == 'start_node')['node_metadata']['needs']['required'].append('x')
    authoring.describe_node_type(factory, 'end_node')['node_metadata']['purpose'] = 'changed'
    node_metadata.execution_contracts()['end_node']['notes'] = 'changed'
    assert NODE_METADATA == before
    assert set(EXECUTION_CONTRACTS) == set(NODE_METADATA)


def test_records_hold_no_identity_or_port_copies():
    for record in NODE_METADATA.values():
        assert not {'type', 'node_type', 'display_name', 'inputs', 'outputs', 'ports',
                    'group', 'tags', 'config_schema'} & set(record)


# --- catalogue v2 ----------------------------------------------------------------------

def catalogue_config(**changes):
    factory = NodeFactory()
    return factory, dict(deepcopy(factory.metadata_for_type('node_catalogue_node')['default_config']),
                         **changes)


@pytest.mark.asyncio
async def test_brief_json_keeps_old_fields_and_adds_the_selection_projection():
    factory, cfg = catalogue_config(detail='Brief', format='JSON')
    record = await node_catalogue.build(factory, cfg)
    assert (record['schema_version'], record['node_metadata_version'],
            record['metadata_projection']) == (2, 1, 'selection')
    entries = {e['type']: e for e in record['entries']}
    for node_type, entry in entries.items():
        expected = NODE_METADATA.get(node_type)
        assert entry['node_metadata'] == (selection(expected) if expected else None)
        assert isinstance(entry['description'], str) and isinstance(entry['inputs'], list)
    picked = entries['branch_node']['node_metadata']
    assert 'never add an unrequested split' in picked['not_for']
    # Brief omits explanatory notes and the wiring contract.
    assert 'note' not in entries['file_output_node']['node_metadata']['side_effects']
    assert 'execution_contract' not in entries['file_output_node']['node_metadata']


@pytest.mark.asyncio
@pytest.mark.parametrize('detail', ['Compact', 'Detailed'])
async def test_full_projection_carries_the_contract_once(detail):
    factory, cfg = catalogue_config(scope='Filtered', search='file_output_node', detail=detail,
                                    format='JSON')
    record = await node_catalogue.build(factory, cfg)
    assert record['metadata_projection'] == 'full'
    entry = record['entries'][0]
    assert entry['node_metadata'] == NODE_METADATA['file_output_node']
    assert 'execution_contract' not in entry
    text = await node_catalogue.build(factory, dict(cfg, format='Text'))
    assert text.startswith(f'Node catalogue v2 · node record v1 · {detail} (full)')
    payload = NODE_METADATA['file_output_node']['execution_contract']['output_payload']
    assert text.count(payload) == 1
    assert text.count(NODE_METADATA['file_output_node']['purpose']) == 1
    for line in ('Use when: ', 'Not for: ', 'Effects: possibly writes files; runs external commands; controls windows.',
                 'Effects note: ', 'Needs note: ', 'Time note: '):
        assert line in text


@pytest.mark.asyncio
async def test_brief_text_is_purpose_first_and_marks_pending_types():
    factory, cfg = catalogue_config(detail='Brief')
    text = await node_catalogue.build(factory, cfg)
    assert text.startswith('Node catalogue v2 · node record v1 · Brief (selection)')
    assert node_catalogue.PORT_LEGEND in text
    start = text.index('branch_node|Parallel Branch|' + NODE_METADATA['branch_node']['purpose'] + '|')
    block = text[start:text.index('\n', text.index('Cost:', start))]
    assert '\n  Use when: ' in block and '\n  Not for: ' in block
    assert '\n  Effects: Read-only. Needs: nothing beyond the engine.' in block
    assert 'Effects note' not in text and 'Time note' not in text
    pending = [t for t in PENDING_REVIEW if f'\n{t}|' in text]
    assert pending, 'catalogue lists some pending types'
    for node_type in pending:
        line_end = text.index('\n', text.index(f'\n{node_type}|') + 1)
        assert text[line_end + 1:].startswith('  ' + node_catalogue.PENDING_LINE)
    assert text.count(node_catalogue.PENDING_LINE) == len(pending)


@pytest.mark.asyncio
async def test_search_uses_positive_intent_never_not_for():
    factory, cfg = catalogue_config(scope='Filtered', format='JSON')
    found = await node_catalogue.build(factory, dict(cfg, search='simultaneous'))
    assert [e['type'] for e in found['entries']] == ['branch_node']  # from use_when
    assert 'Find-and-replace' in NODE_METADATA['text_transform_node']['not_for']
    with pytest.raises(NodeError) as error:
        await node_catalogue.build(factory, dict(cfg, search='find-and-replace'))
    assert error.value.code == 'catalogue_empty'


@pytest.mark.asyncio
@pytest.mark.parametrize('cap,ok', [(511, False), (512, True), (200000, True), (200001, False)])
async def test_configurable_cap_range(cap, ok):
    factory, cfg = catalogue_config(scope='Filtered', search='start_node', detail='Brief', max_chars=cap)
    if ok:
        try:
            assert 'start_node|' in await node_catalogue.build(factory, cfg)
        except NodeError as error:  # an accepted cap may still be too small
            assert error.code == 'catalogue_too_large' and cap == 512
    else:
        with pytest.raises(NodeError) as error:
            await node_catalogue.build(factory, cfg)
        assert error.value.code == 'invalid_config'
    schema = factory.metadata_for_type('node_catalogue_node')['config_schema']['max_chars']
    assert (schema['min'], schema['max']) == (512, node_catalogue.MAX_CHARS_LIMIT)


@pytest.mark.asyncio
async def test_byte_ceiling_reports_which_limit_failed(monkeypatch):
    factory, cfg = catalogue_config(scope='Filtered', search='start_node', detail='Brief')
    monkeypatch.setattr(node_catalogue, 'MAX_BYTES', 100)
    with pytest.raises(NodeError) as error:
        await node_catalogue.build(factory, cfg)
    details = error.value.details
    assert details['failed'] == 'bytes' and details['byte_limit'] == 100 and details['bytes'] > 100


@pytest.mark.asyncio
@pytest.mark.parametrize('detail', ['Brief', 'Compact'])
@pytest.mark.parametrize('fmt', ['Text', 'JSON'])
async def test_synthetic_200_entry_inventory_is_complete_or_a_size_error(monkeypatch, detail, fmt):
    """Cap behaviour only; real future node sizes are not predicted here."""
    real = node_catalogue.list_node_types
    rows = [row for row in real(NodeFactory()) if row['type'] in NODE_METADATA]
    synthetic = [dict(rows[i % len(rows)], name=f"{rows[i % len(rows)]['name']} {i}") for i in range(200)]
    monkeypatch.setattr(node_catalogue, 'list_node_types', lambda factory: synthetic)
    factory, cfg = catalogue_config(detail=detail, format=fmt, max_chars=node_catalogue.MAX_CHARS_LIMIT)
    try:
        value = await node_catalogue.build(factory, cfg)
    except NodeError as error:
        assert error.code == 'catalogue_too_large'
        assert error.details['matched_count'] == 200
        assert error.details['failed'] in ('characters', 'bytes')
    else:
        if fmt == 'JSON':
            assert value['complete'] and value['matched_count'] == len(value['entries']) == 200
        else:
            assert value.count('\n' if detail == 'Brief' else '\nnode ') >= 200


# --- Draft a workflow v2: frozen queries and budgets ------------------------------------

V2_INVENTORY = {
    'catalogue_start': ['start_node'],
    'catalogue_ends': ['end_node', 'branch_end_node'],
    'catalogue_output': ['text_output_node'],
    'catalogue_input': ['user_text_input_node'],
    'catalogue_reader': ['file_reader_node'],
    'catalogue_writer': ['file_output_node'],
    'catalogue_transform': ['text_transform_node'],
    'catalogue_parallel': ['branch_node'],
    'catalogue_conditional': ['conditional_node'],
    'catalogue_concat': ['concat_node'],
    'catalogue_json_path': ['json_path_node'],
}


@pytest.mark.asyncio
async def test_v2_queries_return_their_frozen_inventory_and_full_records():
    from tools.draft_trials import runner
    text, inventory = await runner.contract_inventory()
    assert inventory == V2_INVENTORY
    for node_type in {kind for kinds in V2_INVENTORY.values() for kind in kinds}:
        record = NODE_METADATA[node_type]
        assert record['execution_contract']['output_payload'] in text
        assert record['not_for'] in text
    assert text.count('node record v1 · Compact (full)') == len(V2_INVENTORY)
    assert node_catalogue.PENDING_LINE not in text


@pytest.mark.asyncio
async def test_v2_caps_and_assembled_prompts_keep_20_percent_headroom():
    from tools.draft_trials import runner
    nodes = V2['nodes']
    assert nodes['brief']['config']['max_chars'] == 50000
    for handle in V2_INVENTORY:
        assert nodes[handle]['config']['max_chars'] == 16000
    for handle in ('analysis', 'resolve', 'draft', 'judge'):
        assert nodes[handle]['config']['context_limit'] == 100000
    factory, cfg = catalogue_config()
    brief = await node_catalogue.build(factory, {**cfg, **nodes['brief']['config']})
    contracts, _ = await runner.contract_inventory()
    assert len(brief) <= 0.8 * 50000
    assert len(contracts) <= 0.8 * 50000
    # Largest Questions the frozen reply limits allow, plus their Context.
    request = 'r' * 500
    filled = dict(draft_request=request, clarification_answer='a' * 500,
                  frozen_requirements='f' * 4000, draft_text='d' * 8000, spec_check='s' * 8000)
    analysis = nodes['analysis_question']['config']['template'].format_map(filled)
    draft = nodes['draft_question']['config']['template'].format_map(filled)
    judge = nodes['judge_question']['config']['template'].format_map(filled)
    assert len(analysis) + len(brief) <= 0.8 * 100000
    for question in (draft, judge):
        assert len(question) + len(contracts) <= 0.8 * 100000
        assert len((question + contracts).encode('utf-8')) <= 0.8 * 100000 * 4


# --- review manifest ---------------------------------------------------------------------

def sha_lf(path):
    return hashlib.sha256((ROOT / path).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def test_review_manifest_shape():
    assert MANIFEST['manifest_version'] == 1 and MANIFEST['node_metadata_version'] == 1
    assert set(MANIFEST['reviews']) == set(NODE_METADATA)
    for node_type, entry in MANIFEST['reviews'].items():
        assert set(entry) == {'sources', 'tests', 'content_sha256', 'author', 'verifier',
                              'reviewed', 'source_revision'}, node_type
        assert 1 <= len(entry['sources']) <= 32 and 1 <= len(entry['tests']) <= 32
        assert entry['author'] != entry['verifier']
        assert all(0 < len(entry[k]) <= 80 for k in ('author', 'verifier'))
        assert re.fullmatch(r'\d{4}-\d{2}-\d{2}', entry['reviewed'])
        assert re.fullmatch(r'[0-9a-f]{40}', entry['source_revision'])
        for path in list(entry['sources']) + entry['tests']:
            assert len(path) <= 240 and not path.startswith('/') and '..' not in path
            assert '\\' not in path and ':' not in path.split('::')[0]


@pytest.mark.parametrize('node_type', sorted(NODE_METADATA))
def test_review_attestation_is_current(node_type):
    """A changed source, helper or record text needs a fresh review.

    Re-read the listed code, re-check the record and its tests, then record
    the new digests with the reviewer; updating a digest alone is no review.
    """
    entry = MANIFEST['reviews'][node_type]
    assert entry['content_sha256'] == content_sha256(NODE_METADATA[node_type]), (
        f'{node_type}: record text changed since review')
    for path, digest in entry['sources'].items():
        assert (ROOT / path).is_file(), path
        assert sha_lf(path) == digest, f'{node_type}: {path} changed since review'
    for test_id in entry['tests']:
        path, name = test_id.split('::')
        source = (ROOT / path).read_text()
        assert re.search(rf'^(async )?def {re.escape(name)}\(', source, re.M), test_id
