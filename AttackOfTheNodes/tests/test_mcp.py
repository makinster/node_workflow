"""C4 acceptance tests: launch the shipped server and speak actual MCP stdio."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time

import pytest

APP = Path(__file__).resolve().parents[1]
MAIN = APP / 'main.py'


def build(data, name='Number echo', *, kind='number', node=None, callable_=True):
    spec = {'format': 'aotn-workflow/1', 'name': name, 'callable': callable_,
            'nodes': {'start': {'type': 'start_node', 'config': {'rows': [
                {'name': 'value', 'type': kind, 'required': True, 'to': 'Downstream'}]}},
                      'end': {'type': 'end_node', 'config': {'record_line': False,
                              'return_end': callable_, 'results': [
                                  {'name': 'answer', 'type': kind, 'required': True,
                                   'source': 'Incoming payload'}]}}},
            'connections': [{'from': 'start.default', 'to': 'end.input'}]}
    if node:
        spec['nodes']['middle'] = node
        spec['connections'] = [{'from': 'start.default', 'to': 'middle.input'},
                               {'from': 'middle.default', 'to': 'end.input'}]
    path = data.parent / f'{name}.json'
    path.write_text(json.dumps(spec))
    result = subprocess.run([sys.executable, str(MAIN), 'build', str(path), '--data-dir', str(data)],
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    for workflow in (data / 'workflows').glob('*.json'):
        if json.loads(workflow.read_text())['name'] == name:
            return workflow.stem
    raise AssertionError('build did not save the workflow')


class Client:
    def __init__(self, process, log):
        self.process, self.log, self.sequence = process, log, 0

    def send(self, value):
        self.process.stdin.write((json.dumps(value) + '\n').encode())
        self.process.stdin.flush()

    def receive(self, timeout=12):
        assert select.select([self.process.stdout], [], [], timeout)[0], 'MCP response timed out'
        line = self.process.stdout.readline()
        if not line:
            self.log.seek(0)
            raise AssertionError(self.log.read().decode(errors='replace'))
        message = json.loads(line)
        assert message['jsonrpc'] == '2.0'
        return message

    def request(self, method, params=None):
        self.sequence += 1
        self.send({'jsonrpc': '2.0', 'id': self.sequence, 'method': method, 'params': params or {}})
        response = self.receive()
        assert response['id'] == self.sequence
        return response

    def initialize(self, version='2025-11-25'):
        reply = self.request('initialize', {'protocolVersion': version, 'capabilities': {},
                                          'clientInfo': {'name': 'test-client', 'version': '1'}})
        self.send({'jsonrpc': '2.0', 'method': 'notifications/initialized'})
        return reply['result']

    def call(self, name, arguments=None):
        return self.request('tools/call', {'name': name, 'arguments': arguments or {}})['result']


@contextmanager
def server(data, timeout=5, *, initialize=True, env=None):
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen([sys.executable, str(MAIN), 'mcp', '--data-dir', str(data),
                                    '--call-timeout', str(timeout)],
                                   cwd=data.parent, env=env, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=log, bufsize=0)
        client = Client(process, log)
        try:
            if initialize:
                client.initialize()
            yield client
        finally:
            if process.stdin and not process.stdin.closed:
                process.stdin.close()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            process.stdout.close()


@pytest.fixture
def library(tmp_path):
    data = tmp_path / 'data with spaces'
    identifier = build(data)
    return data, identifier


@pytest.mark.parametrize('version', ['2025-11-25', '2025-06-18', '2024-11-05', 'future-version'])
def test_initialize_tools_and_ping(tmp_path, version):
    with server(tmp_path / 'data', initialize=False) as client:
        assert client.request('tools/list')['error']['code'] == -32000
        initialized = client.initialize(version)
        assert initialized['protocolVersion'] == (version if version != 'future-version' else '2025-11-25')
        assert initialized['capabilities'] == {'tools': {'listChanged': False}}
        tools = client.request('tools/list')['result']['tools']
        assert {tool['name'] for tool in tools} == {'list_workflows', 'run_workflow', 'get_run_status', 'get_recent_events'}
        for tool in tools:
            assert tool['inputSchema']['type'] == 'object'
            assert tool['inputSchema']['additionalProperties'] is False
            if version != '2024-11-05':
                assert tool['outputSchema']['type'] == 'object'
        assert client.request('ping')['result'] == {}


def test_all_four_tools_and_history_refresh(library):
    data, identifier = library
    with server(data) as client:
        listed = client.call('list_workflows')['structuredContent']['workflows']
        assert len(listed) == 1
        workflow = listed[0]
        assert (workflow['id'], workflow['name'], workflow['callable']) == (identifier, 'Number echo', True)
        assert workflow['inputs'][0]['type'] == 'number'
        assert workflow['results'][0]['name'] == 'answer' and workflow['asks'] == []
        assert client.call('get_recent_events')['structuredContent']['runs'] == []
        first = client.call('run_workflow', {'name_or_id': 'Number echo', 'inputs': {'value': 42}})
        assert not first['isError']
        report = first['structuredContent']
        assert report['exit_code'] == 0 and report['final_state'] == 'FINISHED'
        assert report['values'] == {'answer': 42} and report['outputs'] == []
        assert json.loads(first['content'][0]['text']) == report
        history = client.call('get_run_status', {'run_id': report['run_id']})['structuredContent']['run']
        assert history['run_id'] == report['run_id'] and history['final_state'] == 'FINISHED'
        second = client.call('run_workflow', {'name_or_id': identifier, 'inputs': {'value': 0}})
        assert second['structuredContent']['values']['answer'] == 0
        recent = client.call('get_recent_events', {'limit': 1})['structuredContent']['runs']
        assert len(recent) == 1 and recent[0]['run_id'] == second['structuredContent']['run_id']


@pytest.mark.parametrize('kind,value', [('bool', False), ('var', {'nested': [1, False, None]}), ('string', '')])
def test_native_typed_contract_values(tmp_path, kind, value):
    data = tmp_path / 'data'
    build(data, kind=kind)
    with server(data) as client:
        result = client.call('run_workflow', {'name_or_id': 'Number echo', 'inputs': {'value': value}})
        assert not result['isError'], result
        assert result['structuredContent']['values'] == {'answer': value}


def test_stash_input_and_missing_entry(library):
    data, identifier = library
    stash = data / 'stash/entries.json'
    stash.parent.mkdir()
    stash.write_text(json.dumps({'format': 'aotn-stash/1', 'entries': [
        {'id': 'stash_test', 'name': 'The number', 'type': 'string', 'value': '12.5'}]}))
    with server(data) as client:
        result = client.call('run_workflow', {'name_or_id': identifier, 'inputs': {'value': '@stash:The number'}})
        assert result['structuredContent']['values'] == {'answer': 12.5}
        failed = client.call('run_workflow', {'name_or_id': identifier, 'inputs': {'value': '@stash:missing'}})
        assert failed['isError'] and failed['structuredContent']['exit_code'] == 5
        assert failed['structuredContent']['run_id'] is None


@pytest.mark.parametrize('inputs', [{}, {'value': '42'}, {'value': True}, {'value': 1, 'unknown': 2}])
def test_contract_input_errors_do_not_start(library, inputs):
    data, identifier = library
    with server(data) as client:
        result = client.call('run_workflow', {'name_or_id': identifier, 'inputs': inputs})
        assert result['isError'] and result['structuredContent']['exit_code'] == 5
        assert result['structuredContent']['run_id'] is None
        assert client.call('get_recent_events')['structuredContent']['runs'] == []


@pytest.mark.parametrize('name,args', [
    ('run_workflow', {'inputs': {}}), ('run_workflow', {'name_or_id': 'x', 'inputs': []}),
    ('run_workflow', {'name_or_id': 'x', 'path': '/tmp/anything'}),
    ('get_run_status', {'run_id': '../../escape'}), ('get_run_status', {'run_id': 'unknown'}),
    ('get_recent_events', {'limit': 0}), ('get_recent_events', {'limit': 101}),
    ('get_recent_events', {'limit': True}), ('list_workflows', {'extra': True}),
])
def test_bad_tool_input_is_error_and_server_survives(tmp_path, name, args):
    with server(tmp_path / 'data') as client:
        assert client.call(name, args)['isError']
        assert client.request('ping')['result'] == {}


def test_no_arbitrary_workflow_file_access(library):
    data, _ = library
    outside = data.parent / 'outside.json'
    outside.write_text(next((data / 'workflows').glob('*.json')).read_text())
    with server(data) as client:
        for reference in (str(outside), '../../outside', '../../outside.json'):
            assert client.call('run_workflow', {'name_or_id': reference})['isError']
        assert client.call('get_recent_events')['structuredContent']['runs'] == []


@pytest.mark.parametrize('node', [
    {'type': 'user_text_input_node'},
    {'type': 'text_output_node', 'config': {'request_user_input': True}},
])
def test_c25_rejects_prompt_before_run(tmp_path, node):
    data = tmp_path / 'data'
    build(data, kind='string', node=node)
    with server(data) as client:
        result = client.call('run_workflow', {'name_or_id': 'Number echo', 'inputs': {'value': 'hi'}})
        assert result['isError'] and 'C25' in result['content'][0]['text']
        assert client.call('get_recent_events')['structuredContent']['runs'] == []


def test_timeout_kills_worker_then_server_can_run_another_tool(tmp_path):
    data = tmp_path / 'data'
    build(data, node={'type': 'sleep_node', 'config': {'duration': 30}})
    with server(data, timeout=0.5) as client:
        started = time.monotonic()
        result = client.call('run_workflow', {'name_or_id': 'Number echo', 'inputs': {'value': 1}})
        assert result['isError'] and 'timed out' in result['content'][0]['text']
        assert time.monotonic() - started < 4
        assert client.call('list_workflows')['structuredContent']['workflows']


@pytest.mark.parametrize('suffix', ['', 'workflows', 'workflows/nested'])
def test_repository_workflow_library_refused_without_writes(suffix):
    result = subprocess.run([sys.executable, str(MAIN), 'mcp', '--data-dir', str(APP / suffix)],
                            input=b'', capture_output=True, timeout=5)
    assert result.returncode != 0 and result.stdout == b''
    assert b'repository workflows' in result.stderr


def test_parse_errors_unknown_method_and_notifications(tmp_path):
    with server(tmp_path / 'data') as client:
        client.process.stdin.write(b'not json\n')
        client.process.stdin.flush()
        assert client.receive()['error']['code'] == -32700
        assert client.request('not/a/method')['error']['code'] == -32601
        assert client.request('tools/call', {'name': 'unknown'})['error']['code'] == -32602
        client.send({'jsonrpc': '2.0', 'method': 'ignored/notification'})
        client.send({'jsonrpc': '2.0', 'method': 'notifications/cancelled', 'params': {'requestId': []}})
        assert client.request('ping')['result'] == {}


def test_failed_run_and_output_never_pollute_protocol(tmp_path):
    data = tmp_path / 'data'
    build(data, kind='string', callable_=False, node={'type': 'text_output_node', 'config': {
        'template': '{input}', 'request_user_input': False, 'input_source': 'Upstream payload'}})
    build(data, name='Failure', node={'type': 'error_node', 'config': {
        'error_mode': 'fail', 'message': 'diagnostic {"jsonrpc":"not protocol"}'}})
    with server(data) as client:
        result = client.call('run_workflow', {'name_or_id': 'Number echo',
                                            'inputs': {'value': 'line one\n{"jsonrpc":"data only"}'}})
        assert not result['isError']
        assert 'data only' in json.dumps(result['structuredContent']['outputs'])
        failed = client.call('run_workflow', {'name_or_id': 'Failure', 'inputs': {'value': 2}})
        assert failed['isError'] and failed['structuredContent']['exit_code'] != 0
        assert failed['structuredContent']['run_id']
        assert client.request('ping')['result'] == {}


def test_nested_c25_is_discovered_before_start(tmp_path):
    data = tmp_path / 'data'
    child_id = build(data, name='Prompting child', kind='string', node={'type': 'user_text_input_node'})
    build(data, name='Parent', kind='string', node={'type': 'subworkflow_node', 'config': {
        'workflow_id': child_id, 'inputs': [{'name': 'value', 'source': 'Upstream payload'}]}})
    with server(data) as client:
        contracts = client.call('list_workflows')['structuredContent']['workflows']
        assert next(item for item in contracts if item['name'] == 'Parent')['asks']
        assert client.call('run_workflow', {'name_or_id': 'Parent', 'inputs': {'value': 'hello'}})['isError']
        assert client.call('get_recent_events')['structuredContent']['runs'] == []


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux process observation')
@pytest.mark.parametrize('stop', ['cancel', 'eof', 'term'])
def test_cancellation_eof_and_signal_reap_active_worker(tmp_path, stop):
    data = tmp_path / 'data'
    build(data, node={'type': 'sleep_node', 'config': {'duration': 30}})
    with server(data) as client:
        client.send({'jsonrpc': '2.0', 'id': 'active-run', 'method': 'tools/call',
                     'params': {'name': 'run_workflow', 'arguments': {
                         'name_or_id': 'Number echo', 'inputs': {'value': 1}}}})
        children = Path(f'/proc/{client.process.pid}/task/{client.process.pid}/children')
        until = time.monotonic() + 3
        while not children.read_text().strip():
            assert time.monotonic() < until
            time.sleep(0.01)
        worker = int(children.read_text().split()[0])
        if stop == 'cancel':
            client.send({'jsonrpc': '2.0', 'method': 'notifications/cancelled',
                         'params': {'requestId': 'active-run'}})
        elif stop == 'eof':
            client.process.stdin.close()
        else:
            client.process.terminate()
        until = time.monotonic() + 4
        while Path(f'/proc/{worker}').exists():
            assert time.monotonic() < until, 'worker was not reaped'
            time.sleep(0.01)
        if stop == 'cancel':
            assert client.request('ping')['result'] == {}
        else:
            assert client.process.wait(timeout=3) == 0


def test_data_dir_environment_override_and_module_entry(tmp_path):
    data = tmp_path / 'data'
    env = {**os.environ, 'AOTN_DATA_DIR': str(APP)}
    with server(data, env=env) as client:
        assert client.call('list_workflows')['structuredContent'] == {'workflows': []}
    messages = [
        {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {
            'protocolVersion': '2025-11-25', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}}},
        {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
        {'jsonrpc': '2.0', 'id': 2, 'method': 'ping'},
    ]
    result = subprocess.run([sys.executable, '-m', 'aotn_mcp'], cwd=APP,
                            env={**os.environ, 'AOTN_DATA_DIR': str(data)},
                            input=''.join(json.dumps(m) + '\n' for m in messages),
                            capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert [json.loads(line)['id'] for line in result.stdout.splitlines()] == [1, 2]


def test_symlink_workflow_file_cannot_read_outside_library(library):
    data, _ = library
    outside = data.parent / 'outside.json'
    outside.write_text('{"name":"outside secret"}')
    (data / 'workflows/link.json').symlink_to(outside)
    with server(data) as client:
        result = client.call('list_workflows')
        assert result['isError'] and 'outside secret' not in json.dumps(result)


@pytest.mark.parametrize('timeout', ['0', '-1', 'nan', 'inf'])
def test_invalid_timeout_rejected(tmp_path, timeout):
    result = subprocess.run([sys.executable, str(MAIN), 'mcp', '--data-dir', str(tmp_path / 'data'),
                             '--call-timeout', timeout], input=b'', capture_output=True, timeout=5)
    assert result.returncode != 0 and result.stdout == b''


def test_file_contract_and_stash_file_reference(tmp_path):
    data = tmp_path / 'data'
    build(data, kind='file')
    target = tmp_path / 'example with spaces.txt'
    target.write_text('workflow input file')
    file_ref = {'type': 'file', 'path': str(target), 'ref_key': 'file:' + str(target)}
    stash = data / 'stash/entries.json'
    stash.parent.mkdir()
    stash.write_text(json.dumps({'format': 'aotn-stash/1', 'entries': [
        {'id': 'stash_file', 'name': 'Input file', 'type': 'file', 'value': file_ref}]}))
    with server(data) as client:
        for supplied in (str(target), file_ref, '@stash:Input file'):
            result = client.call('run_workflow', {'name_or_id': 'Number echo', 'inputs': {'value': supplied}})
            assert not result['isError'], result
            assert result['structuredContent']['values']['answer'] == file_ref


def test_repo_guard_matches_backend_whitespace_normalization():
    result = subprocess.run([sys.executable, str(MAIN), 'mcp', '--data-dir', str(APP) + ' '],
                            input=b'', capture_output=True, timeout=5)
    assert result.returncode != 0 and result.stdout == b''
    assert b'repository workflows' in result.stderr


def test_same_name_ordinary_and_callable_workflows_use_cli_precedence(tmp_path):
    data = tmp_path / 'data'
    build(data, callable_=True)
    build(data, callable_=False)
    ordinary = next(p.stem for p in (data / 'workflows').glob('*.json') if not json.loads(p.read_text()).get('callable'))
    with server(data) as client:
        result = client.call('run_workflow', {'name_or_id': 'Number echo', 'inputs': {'value': 5}})
        assert not result['isError'], result
        assert result['structuredContent']['workflow_id'] == ordinary
        assert result['structuredContent']['values'] == {}


def test_library_elsewhere_inside_checkout_is_allowed():
    with tempfile.TemporaryDirectory(prefix='.mcp-test-library-', dir=APP.parent) as scratch:
        with server(Path(scratch)) as client:
            assert client.call('list_workflows')['structuredContent'] == {'workflows': []}


def test_history_symlink_cannot_read_outside_history(tmp_path):
    data = tmp_path / 'data'
    history = data / 'run_history'
    history.mkdir(parents=True)
    outside = tmp_path / 'outside.json'
    outside.write_text('{"hidden":"not a run"}')
    (history / 'run_link.json').symlink_to(outside)
    with server(data) as client:
        for name, args in [('get_run_status', {'run_id': 'run_link'}), ('get_recent_events', {})]:
            result = client.call(name, args)
            assert result['isError'] and 'not a run' not in json.dumps(result)
