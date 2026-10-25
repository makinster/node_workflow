"""Read-only merged activity, with disposable libraries and Hermes homes."""
import json
import os
from pathlib import Path

import pytest

from tests.credential_cases import CREDENTIAL_CASES, PADDED_BLOCK_CASES, PUBLIC_FIELD_CASES

from aotn_mcp import activity
from aotn_mcp.tools import validate_arguments
from backend import persistence
from tests.test_mcp import server

RID = 'i_20261023_235019_' + 'a' * 32


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')


def run_record(**changes):
    return dict(run_id='run_1', workflow_id='workflow_1', workflow_name='Backup',
                started_at='2026-10-23T23:49:00Z', ended_at='2026-10-23T23:50:00Z',
                final_state='FINISHED', error_count=0, output_count=1, **changes)


def finding(state='ready'):
    return dict(schema_version=1, request_id=RID, state=state,
                finished_at='2026-10-23T16:51:02-07:00',
                finding='The disk is full.' if state == 'ready' else '',
                failure=None if state == 'ready' else dict(code='auth_failed', message='DO NOT RETURN'),
                evidence='RAW EVIDENCE NEVER RETURNED', limits={'seconds': 90})


def event(kind='event', **changes):
    record = dict(schema_version=1, event_id='e_1', kind=kind, workflow='Backup',
                  run_id='run_1', value='RAW VALUE NEVER RETURNED',
                  created_at='2026-10-23T23:52:00Z', name='backup.check', summary='Backup checked')
    if kind == 'receipt':
        record.update(stage='handed_off', stage_at='2026-10-23T23:53:00Z')
        record.pop('summary')  # Real Notify me receipts do not contain message text.
    record.update(changes)
    return record


def jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b''.join(json.dumps(record).encode() + b'\n' for record in records))


@pytest.fixture
def roots(tmp_path, monkeypatch):
    data, home = tmp_path / 'data', tmp_path / 'hermes'
    monkeypatch.setenv('HERMES_HOME', str(home))
    monkeypatch.setattr(persistence, 'RUN_HISTORY_DIR', data / 'run_history')
    monkeypatch.setattr(persistence, 'SECRETS_DIR', data / 'secrets')
    return data, home / 'aotn'


def test_mixed_activity_since_order_and_projection(roots):
    data, shared = roots
    write(data / 'run_history/run_1.json', run_record())
    write(shared / f'investigations/results/{RID}.json', finding())
    jsonl(shared / 'events.jsonl', [event(), event('receipt')])
    result = activity.get_activity()
    assert [item['type'] for item in result['activity']] == ['event', 'event', 'investigation', 'run']
    assert [item['source'] for item in result['activity']] == [
        'events.jsonl', 'events.jsonl', 'investigation_results', 'run_history']
    assert all(item['time'].endswith('Z') for item in result['activity'])
    assert result['activity'][0]['summary'] == '' and result['activity'][0]['stage'] == 'handed_off'
    assert result['activity'][2]['finding'] == 'The disk is full.'
    assert result['activity'][2]['finished_at'] == '2026-10-23T23:51:02.000000Z'
    assert 'RAW' not in json.dumps(result)
    assert not result['skipped'] and not result['truncated_sources']
    filtered = activity.get_activity('2026-10-24T01:51:02+02:00', 2)
    assert len(filtered['activity']) == 2
    assert len(activity.get_activity('2026-10-23T23:51:02Z')['activity']) == 3  # Inclusive.


def test_fractional_time_ordering(roots):
    _, shared = roots
    jsonl(shared / 'events.jsonl', [event(created_at='2026-10-23T23:52:00Z'),
                                   event(created_at='2026-10-23T23:52:00.1Z')])
    assert [r['time'] for r in activity.get_activity()['activity']] == [
        '2026-10-23T23:52:00.100000Z', '2026-10-23T23:52:00.000000Z']


def test_damaged_lines_and_files_are_counted_without_content_leaks(roots):
    data, shared = roots
    jsonl(shared / 'events.jsonl', [event()])
    with (shared / 'events.jsonl').open('ab') as stream:
        stream.write(b'bad secret content\n\xff\n{}\n{"schema_version":99}\n{"unfinished":')
    write(shared / f'investigations/results/{RID}.json', {'schema_version': 99})
    write(data / 'run_history/run_1.json', ['not a summary'])
    result = activity.get_activity()
    assert len(result['activity']) == 1
    assert result['skipped_by_source'] == {'run_history': 1, 'investigation_results': 1, 'events.jsonl': 5}
    assert result['skipped'] == 7 and 'secret content' not in json.dumps(result)


def test_read_only_and_missing_sources_create_nothing(roots, tmp_path):
    assert activity.get_activity()['activity'] == []
    assert list(tmp_path.iterdir()) == []
    data, shared = roots
    write(data / 'run_history/run_1.json', run_record())
    jsonl(shared / 'events.jsonl', [event()])
    (shared / 'events.jsonl').chmod(0o640)
    def snapshot():
        return {str(p): (p.stat().st_mode, p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else None)
                for p in tmp_path.rglob('*')}
    before = snapshot()
    assert len(activity.get_activity()['activity']) == 2
    assert snapshot() == before


def test_redaction_and_failed_results(roots):
    data, shared = roots
    secret = 'known-unlabelled-secret'
    write(data / 'secrets/secrets.json', {'private': secret})
    record = finding('failed')
    write(shared / f'investigations/results/{RID}.json', record)
    jsonl(shared / 'events.jsonl', [event(summary=f'{secret} api_key=sk-test password="hidden" Bearer fake-token')])
    result = activity.get_activity()
    text = json.dumps(result)
    assert all(value not in text for value in (secret, 'sk-test', 'hidden', 'fake-token', 'DO NOT RETURN'))
    assert '[redacted]' in text
    assert result['activity'][1]['failure'] == 'auth_failed'
    assert result['activity'][1]['finding'] == ''


def test_finding_cap_and_unicode(roots):
    _, shared = roots
    record = finding()
    record['finding'] = '🌍\u2028\u0085' * 1000
    write(shared / f'investigations/results/{RID}.json', record)
    item = activity.get_activity()['activity'][0]
    assert len(item['finding']) == activity.FINDING_CHARS and item['finding_truncated']
    assert len(activity.get_activity()['activity']) == 1


def test_finding_truncation_counts_redacted_text(roots):
    data, shared = roots
    write(data / 'secrets/secrets.json', {'private': 'abc'})
    record = finding()
    record['finding'] = 'abc' * 600
    write(shared / f'investigations/results/{RID}.json', record)
    item = activity.get_activity()['activity'][0]
    assert item['finding_truncated'] and len(item['finding']) == activity.FINDING_CHARS
    assert 'abc' not in item['finding']


def test_events_use_lf_only_and_invalid_json_is_counted(roots):
    _, shared = roots
    jsonl(shared / 'events.jsonl', [event(summary='one\u2028two\u0085three')])
    with (shared / 'events.jsonl').open('ab') as stream:
        stream.write(b'{"schema_version":1,"schema_version":1}\n')
        stream.write(b'{"value":NaN}\n')
        stream.write(b'{"value":1e999}\n')
        stream.write(json.dumps(event(created_at='2026-10-23T00:00:00')).encode() + b'\n')
    result = activity.get_activity()
    assert len(result['activity']) == 1
    assert result['activity'][0]['summary'] == 'one\u2028two\u0085three'
    assert result['skipped'] == 4


def test_default_hermes_home_and_invalid_result_text(roots, tmp_path, monkeypatch):
    monkeypatch.delenv('HERMES_HOME')
    monkeypatch.setenv('HOME', str(tmp_path))
    shared = tmp_path / '.hermes/aotn'
    jsonl(shared / 'events.jsonl', [event()])
    record = finding()
    record['finding'] = '\ud800'
    write(shared / f'investigations/results/{RID}.json', record)
    result = activity.get_activity()
    assert len(result['activity']) == 1 and result['skipped_by_source']['investigation_results'] == 1


def test_event_line_and_byte_caps_keep_latest_complete_lines(roots, monkeypatch):
    _, shared = roots
    rows = [event(created_at=f'2026-10-23T23:52:0{n}Z') for n in range(6)]
    jsonl(shared / 'events.jsonl', rows)
    monkeypatch.setattr(activity, 'EVENT_LINES', 2)
    result = activity.get_activity(limit=10)
    assert len(result['activity']) == 2 and result['activity'][0]['time'].endswith('05.000000Z')
    assert result['truncated_sources'] == ['events.jsonl']
    monkeypatch.setattr(activity, 'SOURCE_BYTES', len(json.dumps(rows[-1]).encode()) + 3)
    result = activity.get_activity()
    assert len(result['activity']) == 1 and result['skipped'] == 0
    assert result['truncated_sources'] == ['events.jsonl']


def test_oversized_event_line_does_not_hide_valid_following_line(roots, monkeypatch):
    _, shared = roots
    jsonl(shared / 'events.jsonl', [event(summary='x' * 2000), event()])
    monkeypatch.setattr(activity, 'EVENT_LINE_BYTES', 1000)
    result = activity.get_activity()
    assert len(result['activity']) == 1 and result['skipped_by_source']['events.jsonl'] == 1


def test_record_and_directory_caps(roots, monkeypatch):
    data, shared = roots
    write(data / 'run_history/run_1.json', run_record())
    path = shared / f'investigations/results/{RID}.json'
    write(path, finding())
    monkeypatch.setattr(activity, 'RECORD_BYTES', 10)
    assert activity.get_activity()['skipped'] == 2
    monkeypatch.setattr(activity, 'RECORD_BYTES', 256 * 1024)
    monkeypatch.setattr(activity, 'DIRECTORY_ENTRIES', 0)
    result = activity.get_activity()
    assert result['activity'] == []
    assert result['truncated_sources'] == ['investigation_results', 'run_history']
    monkeypatch.setattr(activity, 'DIRECTORY_ENTRIES', 2000)
    monkeypatch.setattr(activity, 'SOURCE_BYTES', 1)
    result = activity.get_activity()
    assert result['activity'] == [] and len(result['truncated_sources']) == 2


@pytest.mark.parametrize('kind', ['file_symlink', 'directory_symlink', 'fifo'])
def test_unsafe_sources_are_not_followed_or_opened_for_writing(roots, tmp_path, kind):
    _, shared = roots
    shared.mkdir(parents=True)
    outside = tmp_path / 'outside'
    outside.mkdir()
    jsonl(outside / 'events.jsonl', [event(summary='OUTSIDE CONTENT')])
    if kind == 'file_symlink':
        (shared / 'events.jsonl').symlink_to(outside / 'events.jsonl')
    elif kind == 'directory_symlink':
        shared.rmdir()
        shared.symlink_to(outside, target_is_directory=True)
    else:
        os.mkfifo(shared / 'events.jsonl')
    result = activity.get_activity()
    assert result['activity'] == [] and result['skipped'] > 0
    assert 'OUTSIDE CONTENT' not in json.dumps(result)


def test_damaged_secrets_fail_closed_without_logging_contents(roots, caplog):
    data, _ = roots
    path = data / 'secrets/secrets.json'
    path.parent.mkdir(parents=True)
    path.write_text('private credential garbage')
    with pytest.raises(ValueError, match='activity secrets could not be read safely'):
        activity.get_activity()
    assert not caplog.text


@pytest.mark.parametrize('since', ['today', '2026-10-23', '2026-10-23T00:00:00', 'not-a-time'])
def test_since_requires_explicit_time_zone(roots, since):
    with pytest.raises(ValueError, match='since must be an ISO'):
        activity.get_activity(since)


@pytest.mark.parametrize('args', [{'limit': True}, {'limit': 0}, {'limit': 101}, {'path': '/tmp'}, {'since': 1}])
def test_tool_arguments_do_not_accept_paths_or_invalid_types(args):
    with pytest.raises(ValueError):
        validate_arguments('get_activity', args)


def test_stdio_activity_and_legacy_history_are_independent(tmp_path):
    data, home = tmp_path / 'data', tmp_path / 'hermes'
    write(data / 'run_history/run_1.json', run_record())
    write(home / f'aotn/investigations/results/{RID}.json', finding())
    jsonl(home / 'aotn/events.jsonl', [event()])
    with server(data, env={**os.environ, 'HERMES_HOME': str(home)}) as client:
        response = client.call('get_activity', {'since': '2026-10-23T00:00:00Z', 'limit': 3})
        assert not response['isError']
        result = response['structuredContent']
        assert json.loads(response['content'][0]['text']) == result
        assert [item['type'] for item in result['activity']] == ['event', 'investigation', 'run']
        legacy = client.call('get_recent_events')['structuredContent']
        assert legacy == {'runs': [run_record()]}
        assert client.call('get_activity', {'since': 'not-a-time'})['isError']


@pytest.mark.parametrize('label', [
    'password', 'passwd', 'secret', 'token', 'api_key', 'apikey', 'api key',
    'authorization', 'bearer', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
])
def test_review_activity_credentials_redacted_before_worker_exit(tmp_path, label):
    import subprocess
    import sys
    from tests.test_mcp import APP
    data, home = tmp_path/'data', tmp_path/'hermes'
    values = ['private-colon-value', 'private-equals-value', 'private-json-value', 'known-store-value']
    text = f'{label.upper()}: {values[0]} {label.lower()}={values[1]} '
    text += json.dumps({label.swapcase(): values[2]}) + ' ' + values[3]
    write(data/'secrets/secrets.json', {'credential': values[3]})
    record = finding(); record['finding'] = text
    write(home/f'aotn/investigations/results/{RID}.json', record)
    jsonl(home/'aotn/events.jsonl', [event(summary=text)])
    result = subprocess.run([sys.executable, '-m', 'aotn_mcp.worker'], cwd=APP,
        env={**os.environ, 'AOTN_DATA_DIR': str(data), 'HERMES_HOME': str(home)},
        input=json.dumps({'name': 'get_activity', 'arguments': {}}),
        text=True, capture_output=True, timeout=10)
    assert result.returncode == 0 and not result.stderr
    assert all(value not in result.stdout for value in values)
    records = json.loads(result.stdout)['result']['activity']
    assert {r['type'] for r in records} == {'event', 'investigation'}
    for item in records:
        safe = item['summary'] if item['type'] == 'event' else item['finding']
        assert safe.count('[redacted]') >= 4


@pytest.mark.parametrize('complete', [True, False])
def test_review_activity_private_key_blocks_case_insensitive(roots, complete):
    _, shared = roots
    text = '-----bEgIn RSA pRiVaTe KeY-----\nprivate-key-material\n'
    if complete:
        text += '-----eNd RSA pRiVaTe KeY-----'
    record = finding(); record['finding'] = text
    write(shared/f'investigations/results/{RID}.json', record)
    jsonl(shared/'events.jsonl', [event(summary=text)])
    result = activity.get_activity()
    assert len(result['activity']) == 2
    assert 'private-key-material' not in json.dumps(result)
    assert all('[redacted private key]' in (r.get('summary') or r.get('finding')) for r in result['activity'])


def test_review_activity_protocol_redacts_labels_before_capping(tmp_path):
    data, home = tmp_path/'data', tmp_path/'hermes'
    text = 'AWS_ACCESS_KEY_ID=FAKEACCESSKEY123 AWS_SECRET_ACCESS_KEY=FAKESECRETKEY456 api key: FAKEAPIKEY789 '
    text += 'Authorization: Bearer FAKEBEARER012 ' + 'x'*2500
    record = finding(); record['finding'] = text
    write(home/f'aotn/investigations/results/{RID}.json', record)
    jsonl(home/'aotn/events.jsonl', [event(summary=text)])
    with server(data, env={**os.environ, 'HERMES_HOME': str(home)}) as client:
        response = client.call('get_activity')
    assert not response['isError']
    serialized = json.dumps(response)
    assert all(secret not in serialized for secret in (
        'FAKEACCESSKEY123', 'FAKESECRETKEY456', 'FAKEAPIKEY789', 'FAKEBEARER012'))
    assert json.loads(response['content'][0]['text']) == response['structuredContent']
    assert response['structuredContent']['activity'][1]['finding_truncated']


def test_review_oversized_unfinished_tail_counts_damage(roots):
    _, shared = roots
    path = shared/'events.jsonl';path.parent.mkdir(parents=True)
    path.write_bytes(b'{"unfinished":"' + b'x'*(activity.SOURCE_BYTES+1))
    result = activity.get_activity()
    assert result['activity'] == []
    assert result['skipped'] == result['skipped_by_source']['events.jsonl'] == 1
    assert result['truncated_sources'] == ['events.jsonl']


def test_review_known_value_cannot_obscure_credential_label(roots):
    data, shared = roots
    write(data/'secrets/secrets.json', {'credential': 'password'})
    jsonl(shared/'events.jsonl', [event(summary='password=unregistered-credential')])
    result = activity.get_activity()
    assert 'unregistered-credential' not in json.dumps(result)


def test_review_quoted_json_credential_is_fully_redacted(roots):
    _, shared = roots
    text = json.dumps({'secret': 'first-part " second-part \\ tail-part'})
    jsonl(shared/'events.jsonl', [event(summary=text)])
    summary = activity.get_activity()['activity'][0]['summary']
    assert '[redacted]' in summary
    assert all(part not in summary for part in ('first-part', 'second-part', 'tail-part'))


def test_oversized_complete_window_fragment_is_not_damage(roots):
    _, shared = roots
    path = shared/'events.jsonl';path.parent.mkdir(parents=True)
    path.write_bytes(b'x'*(activity.SOURCE_BYTES+1) + b'\n')
    result = activity.get_activity()
    assert result['activity'] == [] and result['skipped'] == 0
    assert result['truncated_sources'] == ['events.jsonl']


@pytest.mark.parametrize('text,credentials', CREDENTIAL_CASES)
def test_redaction_recheck_activity_blocks_and_urls_before_worker_exit(tmp_path, text, credentials):
    import subprocess
    import sys
    from tests.test_mcp import APP
    data, home = tmp_path/'data', tmp_path/'hermes'
    record = finding();record['finding'] = text
    write(home/f'aotn/investigations/results/{RID}.json', record)
    jsonl(home/'aotn/events.jsonl', [event(summary=text)])
    worker = subprocess.run([sys.executable, '-m', 'aotn_mcp.worker'], cwd=APP,
        env={**os.environ, 'AOTN_DATA_DIR': str(data), 'HERMES_HOME': str(home)},
        input=json.dumps({'name':'get_activity', 'arguments':{}}),
        text=True, capture_output=True, timeout=10)
    assert worker.returncode == 0 and not worker.stderr
    assert all(credential not in worker.stdout for credential in credentials)
    records = json.loads(worker.stdout)['result']['activity']
    assert {item['type'] for item in records} == {'event', 'investigation'}
    for item in records:
        safe = item.get('summary', item.get('finding'))
        assert '[redacted' in safe and 'status: OK' in safe


def test_redaction_recheck_mcp_protocol_blocks_and_uppercase_url(tmp_path):
    data, home = tmp_path/'data', tmp_path/'hermes'
    text = 'password: |\n  FAKEBLOCKFIRST\n  FAKEBLOCKSECOND\nstatus: OK\nHTTPS://user:FAKEUPPERURLPASS@example.invalid/'
    record = finding();record['finding'] = text
    write(home/f'aotn/investigations/results/{RID}.json', record)
    jsonl(home/'aotn/events.jsonl', [event(summary=text)])
    with server(data, env={**os.environ, 'HERMES_HOME': str(home)}) as client:
        response = client.call('get_activity')
    assert not response['isError']
    assert all(secret not in json.dumps(response) for secret in (
        'FAKEBLOCKFIRST','FAKEBLOCKSECOND','FAKEUPPERURLPASS'))
    assert json.loads(response['content'][0]['text']) == response['structuredContent']


@pytest.mark.parametrize('text,expected', PADDED_BLOCK_CASES + [(text, text) for text in PUBLIC_FIELD_CASES])
def test_padding_and_whole_field_recheck_activity_worker(tmp_path, text, expected):
    import subprocess
    import sys
    from tests.test_mcp import APP
    data, home = tmp_path/'data', tmp_path/'hermes'
    record = finding(); record['finding'] = text
    write(home/f'aotn/investigations/results/{RID}.json', record)
    jsonl(home/'aotn/events.jsonl', [event(summary=text)])
    worker = subprocess.run([sys.executable, '-m', 'aotn_mcp.worker'], cwd=APP,
        env={**os.environ, 'AOTN_DATA_DIR': str(data), 'HERMES_HOME': str(home)},
        input=json.dumps({'name': 'get_activity', 'arguments': {}}),
        text=True, capture_output=True, timeout=10)
    assert worker.returncode == 0 and not worker.stderr
    records = json.loads(worker.stdout)['result']['activity']
    assert {item['type'] for item in records} == {'event', 'investigation'}
    assert [item.get('summary', item.get('finding')) for item in records] == [expected]*2
