"""Check the designer recipe without executing it or contacting inference."""
import json
from pathlib import Path
import socket

import pytest

from backend import authoring, meta_workflow, node_catalogue, persistence
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'docs/delivery_tests/specs/draft-a-workflow.json').read_text())
CASES = json.loads((ROOT / 'docs/delivery_tests/fixtures/draft-a-workflow.json').read_text())
PALETTE = {'start_node', 'end_node', 'branch_end_node', 'branch_node',
           'file_reader_node', 'file_output_node', 'user_text_input_node',
           'text_transform_node', 'text_output_node'}


@pytest.fixture(autouse=True)
def no_execution_or_network(monkeypatch, tmp_path):
    library = tmp_path / 'workflows'
    library.mkdir()
    owner = library / 'owner.json'
    owner.write_text('{"name":"Owner work"}')
    before = owner.read_bytes()
    monkeypatch.setattr(persistence, 'WORKFLOWS_DIR', library)
    def forbidden(*args, **kwargs):
        raise AssertionError('Designer checks must not build/save/execute/connect')
    for name in ['save_workflow', 'write_json_atomic', 'save_json_record']:
        monkeypatch.setattr(persistence, name, forbidden)
    monkeypatch.setattr(authoring, 'build_workflow', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    for cls in NodeFactory()._node_registry.values():
        monkeypatch.setattr(cls, 'execute', forbidden)
    yield
    assert list(library.iterdir()) == [owner]
    assert owner.read_bytes() == before


def test_designer_checks_cleanly_and_never_runs():
    report = authoring.check_workflow_spec(NodeFactory(), SPEC)
    assert report['ok'], report
    assert report['diagnostics'] == []


def reachable(start, target, excluded=()):
    pending, seen = [start], set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen:
            continue
        seen.add(current)
        for e in SPEC['connections']:
            if e['from'].split('.')[0] == current and (e['from'], e['to']) not in excluded:
                pending.append(e['to'].split('.')[0])
    return False


def test_only_matching_check_success_can_reach_writer_and_manual_summary():
    edges = SPEC['connections']
    gate = ('check.default', 'write.content')
    assert reachable('start', 'write')
    assert not reachable('start', 'write', [gate])
    assert not reachable('check', 'show', [gate])
    for source in ['error_message', 'failure', 'scope_summary', 'scope_output']:
        assert not reachable(source, 'write')
        assert reachable(source, 'end')
    # Any preparation/API/check/write error goes to the same stop path.
    for h in SPEC['nodes']:
        if h not in {'end', 'error_message', 'failure'}:
            assert {'from': h + '.error', 'to': 'error_message.input'} in edges
    n = SPEC['nodes']
    assert n['draft']['config']['vault_write_key'] == 'draft_text'
    assert n['check']['config']['input_source'] == 'Upstream payload'
    assert {'from': 'draft.default', 'to': 'check.input'} in edges
    c = n['write']['config']
    assert (c['content_source'], c['content_vault_key']) == ('Vault', 'draft_text')
    assert c['file_path_source'] == 'Configured'
    assert c['file_path'] == '/home/makin/src/agent_channel/draft-workflow-output/draft.json'
    assert c['write_mode'] == 'Create unique'
    assert not c['interpret_newlines'] and not c['open_after_write']
    assert n['path']['config']['path'] == 'path'
    assert {'from': 'write.default', 'to': 'path.input'} in edges
    summary = n['summary']['config']['template']
    assert "aotn build '{input}'" in summary
    assert '{draft_text}' in summary and '{spec_check[problems]}' in summary
    assert n['check']['config']['report_vault_key'] == 'spec_check'
    assert n['end']['config']['record_line'] is False


def test_no_retry_no_execution_capabilities_and_approved_call_limits():
    # Every path is acyclic, including error paths: never a second model attempt.
    visiting, visited = set(), set()
    def visit(h):
        assert h not in visiting, 'retry/cycle introduced'
        if h in visited:
            return
        visiting.add(h)
        for e in SPEC['connections']:
            if e['from'].split('.')[0] == h:
                visit(e['to'].split('.')[0])
        visiting.remove(h)
        visited.add(h)
    visit('start')
    assert visited == set(SPEC['nodes'])
    assert {n['type'] for n in SPEC['nodes'].values()} == {
        'start_node', 'user_text_input_node', 'node_catalogue_node', 'concat_node',
        'ask_local_model_node', 'check_reply_node', 'json_path_node',
        'conditional_node', 'set_variable_node', 'check_workflow_spec_node',
        'file_output_node', 'text_output_node', 'end_node'}
    for handle, timeout, tokens in [('shortlist', 300, 256), ('draft', 600, 1024)]:
        c = SPEC['nodes'][handle]['config']
        assert (c['timeout'], c['max_tokens']) == (timeout, tokens)
        assert c['reply_json'] and not c['thinking']
        assert c['temperature'] == 0.2 and c['num_ctx'] == 8192
    assert SPEC['nodes']['check']['config']['max_spec'] == 8000


@pytest.mark.asyncio
async def test_complete_live_palette_and_prompt_sizes_fit_without_truncation():
    n = SPEC['nodes']; factory = NodeFactory()
    defaults = authoring.describe_node_type(factory, 'node_catalogue_node')['config']
    brief = await node_catalogue.build(factory, dict(defaults, **n['brief']['config']))
    values = {}
    types = set()
    for handle, node in n.items():
        if not handle.startswith('catalogue_'):
            continue
        c = dict(defaults, **node['config'])
        assert c['scope'] == 'Filtered' and c['detail'] == 'Compact'
        assert c['include_debug'] is False
        values[c['vault_write_key']] = await node_catalogue.build(factory, c)
        records = await node_catalogue.build(factory, dict(c, format='JSON'))
        types.update(e['type'] for e in records['entries'])
    assert types == PALETTE
    contracts = n['contracts']['config']['template'].format_map(values)
    assert len(brief) == 7634
    assert len(contracts) == 7996
    assert len(contracts) < 8000  # retain the existing designer Context cap
    for case in CASES:
        state = dict(draft_request=case['request'], draft_shortlist=json.dumps(
            case['shortlist'], ensure_ascii=False, separators=(',', ':')))
        question = n['shortlist_question']['config']['template'].format_map(state)
        draft_question = n['draft_question']['config']['template'].format_map(state)
        # Doubled braces in the stored Concat template become literal JSON.
        assert '{"from":"start.default","to":"show.input"}' in draft_question
        assert '{{' not in draft_question
        assert 'display names are labels, never part of a connection' in draft_question
        for q, context in [(question, brief), (draft_question, contracts)]:
            assert len(q) + len(context) + 100 < 20000


@pytest.mark.asyncio
@pytest.mark.parametrize('case', CASES, ids=lambda c: c['id'])
async def test_approved_draft_samples_keep_their_verdicts(case):
    assert {n['type'] for n in case['draft']['nodes'].values()} <= PALETTE
    text = json.dumps(case['draft'], ensure_ascii=False, indent=2) + '\n'
    if case['expected_ok']:
        parsed, report = await meta_workflow.check(NodeFactory(), text, 8000)
        assert parsed == case['draft']
        assert report['warning_count'] == case['expected_warnings']
        # Concat renders the raw JSON from Vault unchanged inside the owner view.
        summary = SPEC['nodes']['summary']['config']['template'].format_map(
            {'input': '/tmp/saved-draft.json', 'spec_check': report, 'draft_text': text})
        assert summary.endswith(text)
        assert "aotn build '/tmp/saved-draft.json'" in summary
    else:
        with pytest.raises(NodeError) as exc:
            await meta_workflow.check(NodeFactory(), text, 8000)
        assert exc.value.code == 'spec_invalid'
        assert any(p['code'] == 'ignored_fan_out' for p in exc.value.details['problems'])
