"""Source-backed metadata claims; fake HTTP and isolated local queues/stores only."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import json
import urllib.error

import pytest

from backend import hermes_folder, saved_values
from backend.node_metadata import NODE_METADATA, PENDING_REVIEW, is_read_only
from backend.run_session import RunSession
from tests.test_meta_nodes import runner

TYPES = ('http_request_node', 'hermes_notify_node', 'if_changed_node')


@pytest.fixture(autouse=True)
def no_real_transports(monkeypatch):
    import socket
    import subprocess
    def forbidden(*args, **kwargs):
        raise AssertionError('External transport is forbidden in metadata claims')
    monkeypatch.setattr(socket.socket, 'connect', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    monkeypatch.setattr('urllib.request.urlopen', forbidden)


def http_reply(body, content_type='text/plain'):
    response = BytesIO(body)
    response.headers = {'Content-Type': content_type}
    return response


@pytest.mark.asyncio
@pytest.mark.parametrize('value,body,content_type', [
    ('Hello', b'Hello', 'text/plain; charset=utf-8'),
    ({'answer': False}, b'{"answer": false}', 'application/json'),
    (b'\x00\xff', b'\x00\xff', 'application/octet-stream'),
    (None, b'', None),
])
async def test_http_post_sends_input_and_optional_bearer(value, body, content_type, monkeypatch):
    calls = []
    def response(request, timeout):
        calls.append((request, timeout))
        return http_reply(b'caf\xe9', 'text/plain; charset=latin-1')
    monkeypatch.setattr('urllib.request.urlopen', response)
    node, ctx, _, done, errors = runner('http_request_node', dict(
        url='https://example.invalid/collect', method='POST', body_source='input',
        auth_token_secret='service-token'), value)
    ctx.secrets_manager = SimpleNamespace(get_secret=lambda key: 'mock-bearer' if key == 'service-token' else None)
    await node.execute(ctx)
    request, timeout = calls[0]
    assert request.full_url == 'https://example.invalid/collect'
    assert request.get_method() == 'POST' and request.data == body
    assert request.get_header('Content-type') == content_type
    assert request.get_header('Authorization') == 'Bearer mock-bearer'
    assert timeout == 10
    assert not errors and done == [{'data': {'default': 'café'}}]


@pytest.mark.asyncio
@pytest.mark.parametrize('method,expected', [('GET', None), ('POST', b'configured body')])
async def test_http_configured_body_and_get_no_body(method, expected, monkeypatch):
    def response(request, timeout):
        assert request.data == expected
        return http_reply(b'\xff')
    monkeypatch.setattr('urllib.request.urlopen', response)
    node, ctx, _, done, errors = runner('http_request_node', dict(
        url='https://example.invalid/', method=method, body='configured body'), 'ignored wire')
    await node.execute(ctx)
    assert not errors and done == [{'data': {'default': '\ufffd'}}]


@pytest.mark.asyncio
@pytest.mark.parametrize('keep,succeeded,survives', [(False, True, False), (True, True, True), (False, False, True)])
async def test_http_file_response_lifetime(keep, succeeded, survives, tmp_path, monkeypatch):
    monkeypatch.setattr('urllib.request.urlopen', lambda *args, **kwargs: http_reply(b'\x00\xffraw', 'application/octet-stream'))
    node, ctx, _, done, errors = runner('http_request_node', dict(
        url='https://example.invalid/', response_mode='file', keep_response_file=keep))
    ctx.run_session = RunSession('http-claim', files_root=tmp_path)
    try:
        await node.execute(ctx)
        assert not errors
        ref = done[0]['data']['default']
        assert set(ref) == {'type', 'ref_key', 'path', 'lifetime'} and ref['type'] == 'file'
        path = Path(ref['path'])
        assert path.read_bytes() == b'\x00\xffraw'
        assert ctx.run_session.file_lifetime(ref) == ('kept' if keep else 'run')
    finally:
        ctx.run_session.close_all(delete_run_files=succeeded)
    assert path.exists() is survives


@pytest.mark.asyncio
@pytest.mark.parametrize('failure,code', [
    (TimeoutError('late'), 'timeout'),
    (urllib.error.URLError(TimeoutError('late')), 'timeout'),
    (urllib.error.URLError('offline'), 'network'),
    (urllib.error.HTTPError('https://example.invalid/', 403, 'Denied', {}, BytesIO(b'no'*3000)), 'http_status'),
])
async def test_http_coded_transport_errors(failure, code, monkeypatch):
    def response(*args, **kwargs):
        raise failure
    monkeypatch.setattr('urllib.request.urlopen', response)
    node, ctx, _, done, errors = runner('http_request_node', dict(url='https://example.invalid/'))
    await node.execute(ctx)
    assert not done and len(errors) == 1 and errors[0].code == code
    if code == 'http_status':
        assert errors[0].details == dict(status=403, url='https://example.invalid/', response_body=('no'*3000)[:4096])


@pytest.mark.asyncio
async def test_http_missing_url_or_file_run_never_calls_transport():
    for config, expected in [({}, 'missing_url'), (dict(url='https://example.invalid/', response_mode='file'), None)]:
        node, ctx, _, done, errors = runner('http_request_node', config)
        await node.execute(ctx)
        assert not done and len(errors) == 1
        if expected:
            assert errors[0].code == expected
        else:
            assert 'needs a run' in str(errors[0])


@pytest.mark.asyncio
async def test_notify_queues_receipt_but_forwards_wire_even_with_vault_source(tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    wire = {'wire': False}
    node, ctx, memory, done, errors = runner('hermes_notify_node', dict(
        input_source='Vault', input_vault_key='message_input', vault_write=True,
        vault_write_key='receipt'), wire)
    memory.store_persistent('message_input', 'queued text')
    await node.execute(ctx)
    receipt = memory.read_persistent('receipt')
    assert not errors and done == [{'data': {'default': wire}}]
    assert receipt['status'] == 'queued' and receipt['message'] == 'queued text'
    outbox = [json.loads(line) for line in (tmp_path/'aotn'/hermes_folder.OUTBOX).read_text().splitlines()]
    assert len(outbox) == 1 and outbox[0]['receipt_id'] == receipt['receipt_id']
    events = [json.loads(line) for line in (tmp_path/'aotn'/hermes_folder.EVENTS).read_text().splitlines()]
    assert [event['stage'] for event in events] == ['queued']  # not delivered


@pytest.mark.asyncio
@pytest.mark.parametrize('mode,expected', [('forward', 'original'), ('receipt', 'queued'), ('silent', None)])
async def test_notify_output_contract(mode, expected, tmp_path, monkeypatch):
    monkeypatch.setenv('HERMES_HOME', str(tmp_path))
    node, ctx, _, done, errors = runner('hermes_notify_node', dict(
        dead_drop_passthrough=mode == 'forward', transient_output=mode == 'receipt', message='message'), 'original')
    await node.execute(ctx)
    assert not errors
    data = done[0]['data']
    if mode == 'forward':
        assert data == {'default': expected}
    elif mode == 'silent':
        assert data == {}
    else:
        assert set(data) == {'default'}
        assert set(data['default']) == {'receipt_id', 'status', 'message'}
        assert data['default']['status'] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize('carry', [False, True])
async def test_notify_queue_failure_is_not_delivery(carry, monkeypatch):
    def unwritable(**kwargs):
        raise OSError('unwritable queue')
    monkeypatch.setattr(hermes_folder, 'queue_message', unwritable)
    node, ctx, _, done, errors = runner('hermes_notify_node', dict(
        dead_drop_passthrough=False, transient_output=True,
        if_not_queued='Carry on' if carry else 'Stop with an error'), 'message')
    await node.execute(ctx)
    if carry:
        assert not errors and done[0]['data']['default']['status'] == 'not queued'
    else:
        assert not done and errors[0].code == 'outbox_unwritable' and errors[0].retryable


@pytest.mark.asyncio
@pytest.mark.parametrize('loosely,changed', [(False, True), (True, False)])
async def test_if_changed_saves_across_runs_and_compares_before_routing(loosely, changed):
    for index, value in enumerate(['Hello world', ' HELLO\tWORLD ']):
        node, ctx, _, done, errors = runner('if_changed_node', dict(
            name='LAST', compare='Loosely' if loosely else 'Exactly'), value)
        ctx.workflow_name = 'Change claims'
        ctx.run_id = f'run-{index}'
        await node.execute(ctx)
        port = 'changed' if index and changed else 'no_change'
        assert not errors and done == [{'data': {port: value}, 'output_port': port, 'next_node_id': None}]
        stored = saved_values.SavedValues().get(saved_values.workflow_place('Change claims'), ' last ')
        assert stored['value'] == value


@pytest.mark.asyncio
@pytest.mark.parametrize('first_time', ['Changed', 'No change'])
async def test_if_changed_first_use_and_suppression_still_save(first_time):
    value = {'n': 0, 'flag': False}
    node, ctx, _, done, errors = runner('if_changed_node', dict(
        name='state', keep_for='All workflows', first_time=first_time, transient_output=False), value)
    await node.execute(ctx)
    port = 'changed' if first_time == 'Changed' else 'no_change'
    assert not errors and done == [{'data': {}, 'output_port': port, 'next_node_id': None}]
    assert saved_values.SavedValues().get(saved_values.all_place(), 'STATE')['value'] == value


@pytest.mark.asyncio
@pytest.mark.parametrize('code', ['store_unwritable', 'store_unreadable', 'too_big'])
@pytest.mark.parametrize('carry', [False, True])
async def test_if_changed_store_failure_route(code, carry, monkeypatch):
    def fail(*args, **kwargs):
        raise saved_values.SavedValuesError('cannot save', code)
    monkeypatch.setattr(saved_values.SavedValues, 'check_and_save', fail)
    node, ctx, _, done, errors = runner('if_changed_node', dict(
        name='state', if_not_saved='Carry on' if carry else 'Stop with an error'), 'value')
    await node.execute(ctx)
    if carry:
        assert not errors and done[0]['output_port'] == 'no_change' and done[0]['data'] == {'no_change': 'value'}
    else:
        assert not done and errors[0].code == code
        assert errors[0].retryable is (code in saved_values.RETRYABLE)


@pytest.mark.asyncio
@pytest.mark.parametrize('carry', [False, True])
async def test_if_changed_blank_name_follows_save_failure_policy(carry):
    node, ctx, _, done, errors = runner('if_changed_node', dict(
        name='', if_not_saved='Carry on' if carry else 'Stop with an error'), 'value')
    await node.execute(ctx)
    if carry:
        assert not errors and done[0]['output_port'] == 'no_change'
    else:
        assert not done and errors[0].code == 'node_error'
    assert saved_values.SavedValues().list_values() == []


@pytest.mark.asyncio
@pytest.mark.parametrize('source', ['Upstream payload', 'Vault'])
async def test_if_changed_missing_input_is_not_hidden_by_carry_on(source):
    node, ctx, _, done, errors = runner('if_changed_node', dict(
        name='state', input_source=source, input_vault_key='missing', if_not_saved='Carry on'))
    ctx.inputs = {}
    await node.execute(ctx)
    assert not done and len(errors) == 1 and isinstance(errors[0], ValueError)
    assert saved_values.SavedValues().list_values() == []


def test_reviewed_effects_do_not_admit_nodes_to_drafts():
    from backend.palette_selection import ADMITTED, ROLE_TYPES
    assert not set(TYPES) & ADMITTED
    assert not any(set(choice) & set(TYPES) for choices in ROLE_TYPES.values() for choice in choices)
    for kind in TYPES:
        assert kind in NODE_METADATA and kind not in PENDING_REVIEW
        assert not is_read_only(NODE_METADATA[kind])
