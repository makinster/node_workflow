"""H0 acceptance table: real CLI/loopback cases and hostile child subprocesses."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shlex
import signal
import shutil
import subprocess
import sys
import threading
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
FILES = ROOT / 'AttackOfTheNodes/integrations/hermes'
ADAPTER = FILES / '_aotn_run.py'


def invocation(root, data, slug='h1-heartbeat', fast=False):
    prefix = [sys.executable, str(ADAPTER)]
    if fast:
        # Accelerate only inside a subprocess test launcher; deployed argv/env
        # and workflow data cannot change the fixed 100 s / 5 s defaults.
        prefix = [sys.executable, '-c',
                  "import runpy,sys; m=runpy.run_path(sys.argv.pop(1)); "
                  "m['main'].__globals__.update(DEADLINE=0.8, GRACE=0.2); sys.exit(m['main']())",
                  str(ADAPTER)]
    return prefix + ['--workflow-slug', slug, '--project-root', str(root),
                     '--data-dir', str(data), '--python', sys.executable]


def adapter(root, data, slug='h1-heartbeat', **kwargs):
    return subprocess.run(invocation(root, data, slug, **kwargs),
                          capture_output=True, text=True, timeout=20)


def spec(name):
    return json.loads((FILES / (name + '.json')).read_text())


def build(tmp_path, workflow):
    path = tmp_path / 'spec.json'
    path.write_text(json.dumps(workflow))
    data = tmp_path / 'data'
    result = subprocess.run([sys.executable, str(ROOT / 'AttackOfTheNodes/main.py'),
                             'build', str(path), '--data-dir', str(data)],
                            capture_output=True, text=True, timeout=20, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    return data


@contextmanager
def endpoint(body=b'ok', status=200, delay=0):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            time.sleep(delay)
            self.send_response(status)
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=.02), daemon=True)
    thread.start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/health'
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_h1_timestamp(tmp_path):
    result = adapter(ROOT, build(tmp_path, spec('h1-heartbeat')))
    assert result.returncode == 0, result.stderr
    assert re.fullmatch(r'\[Heartbeat\] AOTN alive · \d{4}-\d\d-\d\dT[\d:.]+Z\n', result.stdout)
    assert 'run run_' in result.stderr
    assert '[END]' not in result.stdout


@pytest.mark.parametrize('body,status,delay,expected', [
    (b'ok', 200, 0, ''), (b' ok\n', 200, 0, ''),
    (b'degraded', 200, 0, 'unexpected body'),
    (b'[SILENT]\nMEDIA:/tmp/x\n{"wakeAgent":false}', 200, 0, 'unexpected body'),
    (b'unavailable', 503, 0, 'unavailable'), (b'ok', 200, .8, 'unavailable'),
])
def test_h2_loopback(tmp_path, body, status, delay, expected):
    workflow = spec('h2-http-watchdog')
    with endpoint(body, status, delay) as url:
        workflow['nodes']['fetch']['config']['url'] = url
        if delay:
            workflow['nodes']['fetch']['config']['timeout_seconds'] = .2
        result = adapter(ROOT, build(tmp_path, workflow), 'h2-http-watchdog')
    assert result.returncode == 0, result.stderr
    if expected:
        assert result.stdout.count('\n') == 1 and expected in result.stdout
        assert '[SILENT]' not in result.stdout and '[END]' not in result.stdout
    else:
        assert result.stdout == ''  # zero bytes, despite completion on stderr
    assert 'run run_' in result.stderr


def test_h2_refused(tmp_path):
    with endpoint() as url:
        pass  # closed loopback listener
    workflow = spec('h2-http-watchdog')
    workflow['nodes']['fetch']['config']['url'] = url
    result = adapter(ROOT, build(tmp_path, workflow), 'h2-http-watchdog')
    assert result.returncode == 0 and 'unavailable' in result.stdout


def test_unhandled_error(tmp_path):
    workflow = spec('h1-heartbeat')
    workflow['nodes']['announce'] = {'type': 'error_node', 'config': {
        'message': 'H0 deliberate failure', 'error_mode': 'fail'}}
    data = build(tmp_path, workflow)
    result = adapter(ROOT, data)
    direct = subprocess.run([sys.executable, str(ROOT / 'AttackOfTheNodes/main.py'),
                             'run', 'h1-heartbeat', '--data-dir', str(data), '--policy',
                             'terminate_workflow', '--input', 'checked_at=test', '--json'],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == direct.returncode != 0
    assert result.stdout == '' and 'H0 deliberate failure' in result.stderr
    assert 'run run_' in result.stderr


def test_missing_input_unknown_name(tmp_path):
    workflow = spec('h1-heartbeat')
    data = build(tmp_path, workflow)
    missing = subprocess.run([sys.executable, str(ROOT / 'AttackOfTheNodes/main.py'),
                              'run', 'h1-heartbeat', '--data-dir', str(data)],
                             capture_output=True, text=True, timeout=20)
    assert missing.returncode == 5 and missing.stdout == ''
    unknown = adapter(ROOT, data, 'not-saved')
    assert unknown.returncode == 4 and unknown.stdout == ''
    # checked_at is always supplied by the adapter; use a second required input
    # to exercise its exit-5 pre-start path as well as CLI missing timestamp.
    workflow['nodes']['start']['config']['rows'].append(
        {'name': 'another', 'type': 'string', 'required': True, 'to': 'Downstream'})
    other = tmp_path / 'other'
    other.mkdir()
    missing = adapter(ROOT, build(other, workflow))
    assert missing.returncode == 5 and missing.stdout == ''
    assert 'run unavailable' in missing.stderr


def report(outputs=None, values=None, code=0):
    return {'run_id': 'run_test', 'final_state': 'FINISHED', 'exit_code': code,
            'outputs': outputs or [], 'values': values or {}}


def fake_root(tmp_path, program):
    root = tmp_path / 'root with spaces'
    (root / 'AttackOfTheNodes').mkdir(parents=True)
    (root / 'AttackOfTheNodes/main.py').write_text(program)
    return root


def program(value, code=0, diagnostic='completion summary\n'):
    return (f'import sys\nsys.stderr.write({diagnostic!r})\n'
            f'sys.stdout.write({json.dumps(value)!r})\nsys.exit({code})\n')


def test_empty_and_rendered_report(tmp_path):
    root = fake_root(tmp_path, program(report()))
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 0 and result.stdout == ''
    assert result.stderr == 'completion summary\n'
    value = report([{'value': [1, 2]}, {'a': True}, 'plain', 3], {'one': {'value': 7}, 'two': [1]})
    (root / 'AttackOfTheNodes/main.py').write_text(program(value))
    result = adapter(root, tmp_path / 'data')
    assert result.stdout == '[1, 2]\n| {"a": true}\nplain\n3\none = {"value": 7}\ntwo = [1]\n'


@pytest.mark.parametrize('code', [1, 2, 3, 4, 5, 64, 130])
def test_natural_exits(tmp_path, code):
    root = fake_root(tmp_path, program(report(['do not send'], code=code), code))
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == code and result.stdout == ''
    assert 'run run_test' in result.stderr


@pytest.mark.parametrize('raw', ['not json', '{}', '[]', '{"exit_code":false}',
                                 json.dumps(report(code=1)),
                                 json.dumps({**report(), 'outputs': {}}), ''])
def test_malformed_report(tmp_path, raw):
    root = fake_root(tmp_path, f'print({raw!r})')
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 70 and result.stdout == ''
    assert 'adapter failure' in result.stderr


def alive(pid):
    path = Path(f'/proc/{pid}/stat')
    return path.exists() and path.read_text().split(') ', 1)[1][0] != 'Z'


def wait_file(path):
    until = time.monotonic() + 10
    while not path.exists() or not path.read_text():
        assert time.monotonic() < until, path
        time.sleep(0.02)
    return int(path.read_text())


def test_oversized_report_reaped_and_unlocks(tmp_path):
    pidfile = tmp_path / 'pid'
    root = fake_root(tmp_path, 'import os,sys,time,signal\n'
                     f'open({str(pidfile)!r},"w").write(str(os.getpid()))\n'
                     'signal.signal(signal.SIGINT, signal.SIG_IGN)\n'
                     "sys.stdout.write('x' * (1024*1024+1)); sys.stdout.flush()\ntime.sleep(60)\n")
    result = adapter(root, tmp_path / 'data', fast=True)
    assert result.returncode == 70 and result.stdout == ''
    assert not alive(wait_file(pidfile))
    (root / 'AttackOfTheNodes/main.py').write_text(program(report()))
    assert adapter(root, tmp_path / 'data').returncode == 0


def test_long_emoji_stream_caps(tmp_path):
    root = fake_root(tmp_path, program(report(['😀' * 4000]), diagnostic='😀' * 40000))
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 0
    for stream in (result.stdout, result.stderr):
        assert len(stream.encode('utf-16-le')) // 2 <= 3500
        assert '�' not in stream
        assert stream.endswith('| …truncated; see run run_test')


def test_directives_both_streams(tmp_path):
    text = 'ordinary\n[SILENT] [silent] [SiLeNt] [ſilent] [sılent]\nMEDIA:/tmp/file\n  {"wakeAgent":false}'
    root = fake_root(tmp_path, program(report([text]), diagnostic=text))
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 0
    for stream in (result.stdout, result.stderr):
        assert '[SILENT]' not in stream.upper() and 'MEDIA:' not in stream
        assert stream.startswith('ordinary\n')
        assert '\n|   {"wakeAgent":false}' in stream
    (root / 'AttackOfTheNodes/main.py').write_text(program(report(code=2), 2, text))
    failed = adapter(root, tmp_path / 'data')
    assert failed.returncode == 2 and failed.stdout == ''
    assert '[SILENT]' not in failed.stderr.upper() and 'MEDIA:' not in failed.stderr
    assert '\n|   {"wakeAgent":false}' in failed.stderr


def sleeper(tmp_path, ignore=False):
    pidfile, signalfile = tmp_path / 'pid', tmp_path / 'got-int'
    source = ('import os,signal,time,sys\n'
              f'def stop(*_):\n open({str(signalfile)!r}, "w").write("SIGINT")\n'
              + (' return\n' if ignore else ' sys.exit(130)\n')
              + 'signal.signal(signal.SIGINT, stop)\n'
              + f'open({str(pidfile)!r}, "w").write(str(os.getpid()))\ntime.sleep(60)\n')
    return fake_root(tmp_path, source), pidfile, signalfile


@pytest.mark.parametrize('ignore', [False, True])
def test_deadline(tmp_path, ignore):
    root, pidfile, signalfile = sleeper(tmp_path, ignore)
    result = adapter(root, tmp_path / 'data', fast=True)
    assert result.returncode == 124 and result.stdout == ''
    assert signalfile.read_text() == 'SIGINT' and not alive(wait_file(pidfile))


@pytest.mark.parametrize('sig,code', [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
@pytest.mark.parametrize('ignore', [False, True])
def test_external_stop(tmp_path, sig, code, ignore):
    root, pidfile, signalfile = sleeper(tmp_path, ignore)
    process = subprocess.Popen(invocation(root, tmp_path / 'data', fast=True),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pid = wait_file(pidfile)
    process.send_signal(sig)
    out, err = process.communicate(timeout=10)
    assert process.returncode == code and out == '', err
    assert signalfile.read_text() == 'SIGINT' and not alive(pid)


def test_overlap_per_slug_and_cleanup_lock(tmp_path):
    root, pidfile, _ = sleeper(tmp_path, ignore=True)
    data = tmp_path / 'data'
    first = subprocess.Popen(invocation(root, data), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    wait_file(pidfile)
    other = None
    try:
        result = adapter(root, data)
        assert result.returncode == 75 and result.stdout == ''
        other = subprocess.Popen(invocation(root, data, 'different'), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.2)
        assert other.poll() is None  # separate slug started, not rejected
        other.send_signal(signal.SIGTERM)
        first.send_signal(signal.SIGTERM)
        assert adapter(root, data).returncode == 75  # still held during grace
        other.communicate(timeout=10)
        first.communicate(timeout=10)
        assert other.returncode == first.returncode == 143
        (root / 'AttackOfTheNodes/main.py').write_text(program(report()))
        assert adapter(root, data).returncode == 0
    finally:
        for process in (first, other):
            if process is not None and process.poll() is None:
                process.send_signal(signal.SIGTERM)
                process.communicate(timeout=10)


def test_child_signal_exit_convention(tmp_path):
    root = fake_root(tmp_path, 'import os,signal; os.kill(os.getpid(), signal.SIGTERM)')
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 143 and result.stdout == ''


def test_child_argv_cwd_stdin(tmp_path):
    observed = tmp_path / 'observed.json'
    root = fake_root(tmp_path, 'import os,sys,json\n'
                     f'open({str(observed)!r},"w").write(json.dumps([sys.argv,os.getcwd(),sys.stdin.read()]))\n'
                     + f'print({json.dumps(report())!r})\n')
    data = tmp_path / 'isolated data'
    assert adapter(root, data).returncode == 0
    argv, cwd, stdin = json.loads(observed.read_text())
    assert cwd == str(root) and stdin == ''
    assert argv[1:7] == ['run', 'h1-heartbeat', '--policy', 'terminate_workflow', '--data-dir', str(data)]
    assert argv[7] == '--input' and argv[8].startswith('checked_at=') and argv[8].endswith('Z')
    assert argv[9:] == ['--json']


@pytest.mark.parametrize('name', ['aotn-.sh', 'aotn-Foo.sh', 'aotn-foo.py', 'foo.sh', 'aotn-x;touch bad.sh'])
def test_bad_wrapper_filename(name):
    result = subprocess.run(['bash', '-c', 'source "$1"; aotn_cron_run "$2"', 'test',
                             str(FILES / '_aotn_common.sh'), name], capture_output=True, text=True)
    assert result.returncode == 70 and result.stdout == ''


def test_wrapper_rejects_arguments():
    result = subprocess.run(['bash', '-c', 'source "$1"; aotn_cron_run aotn-h1-heartbeat.sh extra',
                             'test', str(FILES / '_aotn_common.sh')], capture_output=True, text=True)
    assert result.returncode == 70


def test_fixed_limits_and_spec_fidelity():
    import runpy
    module = runpy.run_path(str(ADAPTER))
    assert (module['DEADLINE'], module['GRACE']) == (100, 5)
    draft = (ROOT / 'AttackOfTheNodes/docs/integrations/HERMES_H0_DRAFT.md').read_text()
    for block in re.findall(r'```json\n(.*?)\n```', draft, re.S):
        expected = json.loads(block)
        assert spec(expected['name']) == expected
        for node in expected['nodes'].values():
            if node['type'] == 'end_node':
                assert node['config']['record_line'] is False


def test_wrapper_filename_selects_exact_slug():
    # Stub only Bash's final exec; exercise the real function and its argv
    # without touching the deployment data directory or Hermes installation.
    result = subprocess.run(['bash', '-c',
                             'source "$1"; exec() { printf "%s\\n" "$@"; }; '
                             'aotn_cron_run "/some folder/aotn-h2-http-watchdog.sh"',
                             'test', str(FILES / '_aotn_common.sh')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        '/home/makin/src/node_workflow/.venv/bin/python', str(ADAPTER),
        '--workflow-slug', 'h2-http-watchdog', '--project-root', '/home/makin/src/aotn-live',
        '--data-dir', '/home/makin/.local/share/aotn-cron',
        '--python', '/home/makin/src/node_workflow/.venv/bin/python']


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux descendant containment')
@pytest.mark.parametrize('stop', ['deadline', 'term'])
@pytest.mark.parametrize('detach', [False, True])
def test_deadline_cleans_lingering_descendant(tmp_path, stop, detach):
    child_pid = tmp_path / 'descendant'
    script = ('import os,signal,time\n' + ('os.setsid()\n' if detach else '') +
              'signal.signal(signal.SIGINT, signal.SIG_IGN)\n'
              f'open({str(child_pid)!r}, "w").write(str(os.getpid()))\ntime.sleep(60)')
    root = fake_root(tmp_path, 'import subprocess,sys\n'
                     f'subprocess.Popen([sys.executable, "-c", {script!r}])\n')
    process = subprocess.Popen(invocation(root, tmp_path / 'data', fast=True),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    pid = wait_file(child_pid)
    try:
        if stop == 'term':
            process.send_signal(signal.SIGTERM)
        out, err = process.communicate(timeout=10)
        assert process.returncode == (124 if stop == 'deadline' else 143), err
        assert out == b''
        # Reaping is part of the contract, not merely sending SIGKILL.
        assert not Path(f'/proc/{pid}').exists()
        (root / 'AttackOfTheNodes/main.py').write_text(program(report()))
        assert adapter(root, tmp_path / 'data').returncode == 0
    finally:
        if alive(pid):
            os.kill(pid, signal.SIGKILL)
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=10)


@pytest.fixture
def deployed_entries(tmp_path):
    home = tmp_path / 'Hermes home with spaces'
    scripts = home / 'scripts'
    scripts.mkdir(parents=True)
    observed = tmp_path / 'started.json'
    root = fake_root(tmp_path, 'import sys,json\n'
                     f'open({str(observed)!r}, "w").write(json.dumps(sys.argv))\n'
                     + f'print({json.dumps(report(["adapter reached"]))!r})\n')
    data = tmp_path / 'cron data with spaces'
    for path in FILES.iterdir():
        if path.suffix in ('.py', '.sh'):
            shutil.copy2(path, scripts / path.name)
    # Installation-specific absolute paths only; execute the production Bash
    # function, exec, Python adapter and controlled child without mocking them.
    common = scripts / '_aotn_common.sh'
    source = common.read_text()
    for name, value in [('root', root), ('python', sys.executable), ('data', data)]:
        source = re.sub(rf'^    local {name}=.*$',
                        lambda _: f'    local {name}={shlex.quote(str(value))}',
                        source, flags=re.M)
    common.write_text(source)
    return scripts, {**os.environ, 'HERMES_HOME': str(home)}, observed


@pytest.mark.parametrize('slug', ['h1-heartbeat', 'h2-http-watchdog'])
@pytest.mark.parametrize('extra', [False, True])
def test_shipped_entry_subprocess(deployed_entries, slug, extra):
    scripts, env, observed = deployed_entries
    argv = ['bash', str(scripts / f'aotn-{slug}.sh')]
    result = subprocess.run(argv + (['unexpected argument'] if extra else []),
                            env=env, cwd=scripts.parent, capture_output=True,
                            text=True, timeout=10)
    if extra:
        assert result.returncode == 70, result.stderr
        assert 'no arguments' in result.stderr
        assert result.stdout == '' and not observed.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert result.stdout == 'adapter reached\n'
        assert json.loads(observed.read_text())[1:3] == ['run', slug]


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux descendant containment')
@pytest.mark.parametrize('kill_fault', ['denied', 'ignored'])
def test_unconfirmed_cleanup_marks_stale_and_blocks_next_tick(tmp_path, kill_fault):
    pidfile = tmp_path / 'escaped'
    child = ('import os,signal,time\nos.setsid()\n'
             'signal.signal(signal.SIGINT, signal.SIG_IGN)\n'
             f'open({str(pidfile)!r}, "w").write(str(os.getpid()))\ntime.sleep(60)')
    root = fake_root(tmp_path, 'import subprocess,sys\n'
                     f'subprocess.Popen([sys.executable, "-c", {child!r}])\n')
    data = tmp_path / 'data'
    # Inject an OS permission failure, not a replacement cleanup function.
    # Child processes and the complete adapter path remain real subprocesses.
    fault = 'raise PermissionError(1, "kill denied")' if kill_fault == 'denied' else 'return'
    launcher = ("import runpy,sys; m=runpy.run_path(sys.argv.pop(1)); "
                "m['main'].__globals__.update(DEADLINE=0.8, GRACE=0.2); "
                f"exec({'def denied(*args):' + chr(10) + ' ' + fault!r}); "
                "m['os'].kill=denied; sys.exit(m['main']())")
    argv = [sys.executable, '-c', launcher, str(ADAPTER)] + invocation(root, data)[2:]
    pid = None
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        pid = wait_file(pidfile)
        assert result.returncode == 70 and result.stdout == '', result.stderr
        assert 'cleanup' in result.stderr and 'stale' in result.stderr
        if kill_fault == 'ignored':
            assert 'timed out' in result.stderr
        assert len(result.stderr.encode('utf-16-le')) // 2 <= 3500
        marker = data / '.hermes-locks/h1-heartbeat.lock'
        assert 'stale' in marker.read_text()
        started = tmp_path / 'next started'
        (root / 'AttackOfTheNodes/main.py').write_text(
            f'open({str(started)!r}, "w").write("started")\n' + program(report()))
        blocked = adapter(root, data)
        assert blocked.returncode == 75 and blocked.stdout == ''
        assert 'stale' in blocked.stderr and not started.exists()
    finally:
        if pid is None and pidfile.exists():
            pid = int(pidfile.read_text())
        if pid is not None and alive(pid):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux descendant containment')
def test_natural_exit_reaps_detached_descendant_with_closed_pipes(tmp_path):
    pidfile = tmp_path / 'escaped'
    child = ('import os,time\nos.setsid()\n'
             f'open({str(pidfile)!r}, "w").write(str(os.getpid()))\ntime.sleep(60)')
    source = ('import subprocess,sys,time,pathlib\n'
              f'subprocess.Popen([sys.executable,"-c",{child!r}], '
              'stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n'
              f'while not pathlib.Path({str(pidfile)!r}).exists(): time.sleep(0.01)\n'
              + program(report(['normal output'])))
    root = fake_root(tmp_path, source)
    pid = None
    try:
        result = adapter(root, tmp_path / 'data')
        pid = wait_file(pidfile)
        assert result.returncode == 0 and result.stdout == 'normal output\n', result.stderr
        assert not Path(f'/proc/{pid}').exists()
    finally:
        if pid is None and pidfile.exists():
            pid = int(pidfile.read_text())
        if pid is not None and alive(pid):
            os.kill(pid, signal.SIGKILL)


@pytest.mark.parametrize('data_suffix', ['', 'workflows', 'workflows/nested'])
def test_refuse_repository_data(tmp_path, data_suffix):
    root = fake_root(tmp_path, program(report()))
    data = root / 'AttackOfTheNodes' / data_suffix
    result = adapter(root, data)
    assert result.returncode == 70 and result.stdout == ''
    assert not (root / 'AttackOfTheNodes/workflows').exists()


def test_signal_with_valid_report_keeps_run_id(tmp_path):
    pidfile = tmp_path / 'pid'
    source = ('import os,signal,time,sys,json\n'
              f'def stop(*_):\n print({json.dumps(report(code=130))!r}); sys.exit(130)\n'
              'signal.signal(signal.SIGINT, stop)\n'
              f'open({str(pidfile)!r}, "w").write(str(os.getpid()))\ntime.sleep(60)')
    root = fake_root(tmp_path, source)
    process = subprocess.Popen(invocation(root, tmp_path / 'data', fast=True),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    wait_file(pidfile)
    process.send_signal(signal.SIGTERM)
    out, err = process.communicate(timeout=10)
    assert process.returncode == 143 and out == ''
    assert 'run run_test' in err and 'run unavailable' not in err


@pytest.mark.parametrize('separator', ['\r', '\r\n', '\u2028', '\x0b'])
def test_json_directive_alternative_line_endings(tmp_path, separator):
    root = fake_root(tmp_path, program(report(['plain' + separator + '{"wakeAgent":false}'])))
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 0
    assert result.stdout.splitlines()[-1] == '| {"wakeAgent":false}'


def test_adapter_usage_is_adapter_failure():
    result = subprocess.run([sys.executable, str(ADAPTER)], capture_output=True, text=True)
    assert result.returncode == 70 and result.stdout == ''
    assert 'adapter failure' in result.stderr


def test_unbounded_run_id_rejected(tmp_path):
    root = fake_root(tmp_path, program({**report(), 'run_id': 'x' * 4000}))
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 70 and result.stdout == ''


def test_concurrent_pipe_floods(tmp_path):
    value = json.dumps(report(['x' * 200000]))
    root = fake_root(tmp_path, 'import sys,threading\n'
                     "t=threading.Thread(target=lambda: sys.stderr.write('diagnostic' * 30000))\n"
                     't.start()\n' + f'sys.stdout.write({value!r}); sys.stdout.flush(); t.join()\n')
    result = adapter(root, tmp_path / 'data')
    assert result.returncode == 0
    assert 'see run run_test' in result.stdout and 'truncated' in result.stderr
    assert len(result.stderr.encode('utf-16-le')) // 2 <= 3500


# -- install.sh: copies, not symlinks (Hermes v0.14 rejects symlinks out of scripts/) -------------

INSTALL = Path(__file__).resolve().parent.parent / 'integrations' / 'hermes' / 'install.sh'
INSTALLED = ('_aotn_common.sh', '_aotn_run.py', 'aotn-h1-heartbeat.sh', 'aotn-h2-http-watchdog.sh',
             '_aotn_drain.py', 'aotn-drain-home.sh')


def run_install(home, *args):
    return subprocess.run(['bash', str(INSTALL), *args], capture_output=True, text=True,
                          env=dict(os.environ, HERMES_HOME=str(home)))


def test_install_copies_files_with_entry_scripts_executable(tmp_path):
    home = tmp_path / 'hermes home'
    first = run_install(home)
    scripts = home / 'scripts'
    assert first.returncode == 0, first.stderr
    for name in INSTALLED:
        target = scripts / name
        assert target.is_file() and not target.is_symlink()
        assert target.read_bytes() == (INSTALL.parent / name).read_bytes()
        assert bool(target.stat().st_mode & 0o111) == name.startswith('aotn-')
    again = run_install(home)
    assert again.returncode == 0 and again.stdout.count('up to date') == len(INSTALLED)


def test_install_check_reports_drift_without_changing_anything(tmp_path):
    home = tmp_path / 'home'
    assert run_install(home, '--check').returncode == 1  # missing
    run_install(home)
    assert run_install(home, '--check').returncode == 0
    edited = home / 'scripts' / '_aotn_run.py'
    edited.write_text('# changed\n')
    check = run_install(home, '--check')
    assert check.returncode == 1 and 'differs' in check.stdout and edited.read_text() == '# changed\n'


def test_install_refuses_symlinks_and_bad_arguments(tmp_path):
    home = tmp_path / 'home'
    (home / 'scripts').mkdir(parents=True)
    (home / 'scripts' / '_aotn_run.py').symlink_to(INSTALL.parent / '_aotn_run.py')
    assert run_install(home).returncode == 70
    assert run_install(home, '--force').returncode == 64
