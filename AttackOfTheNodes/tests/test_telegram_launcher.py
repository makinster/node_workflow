"""Telegram launchers: real entry/adapter subprocesses; disposable data only."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

import pytest

from tests.test_hermes_adapter import (ADAPTER, FILES, ROOT, build, fake_root, invocation,
                                 program, report, run_install, spec, wait_file)

TEMPLATE = FILES / 'aotn-run-template.sh'


def launch(root, data, slug='h1-heartbeat', timeout=15):
    return subprocess.run(invocation(root, data, slug) + ['--telegram-launcher'],
                          capture_output=True, text=True, timeout=timeout)


def test_entry_filename_and_fixed_paths(tmp_path):
    entry = tmp_path / 'aotn-run-c1-notify-test.sh'
    shutil.copyfile(TEMPLATE, entry)
    (tmp_path / '_aotn_run.py').write_text('import json,sys; print(json.dumps(sys.argv[1:]))')
    result = subprocess.run(['bash', str(entry)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [
        '--telegram-launcher', '--workflow-slug', 'c1-notify-test',
        '--project-root', '/home/makin/src/aotn-live',
        '--data-dir', '/home/makin/.local/share/aotn-cron',
        '--python', '/home/makin/src/node_workflow/.venv/bin/python']


@pytest.mark.parametrize('name,args,reason', [
    ('aotn-run-heartbeat.sh', ['other'], 'arguments are not supported'),
    ('aotn-run-heartbeat.sh', ['--workflow-slug', 'other'], 'arguments are not supported'),
    ('aotn-run-.sh', [], 'name this script'),
    ('aotn-run-Foo.sh', [], 'name this script'),
    ('aotn-run-../bad.sh', [], 'name this script'),
    ('aotn-run-<slug>.sh', [], 'name this script'),
])
def test_entry_refuses_arguments_and_invalid_names(tmp_path, name, args, reason):
    # Include a slash in the pathname without ever accepting it as a slug.
    entry = tmp_path / name
    entry.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, entry)
    result = subprocess.run(['bash', str(entry), *args], capture_output=True, text=True, timeout=10)
    assert result.returncode == 64
    assert result.stdout.startswith("Couldn't run ") and reason in result.stdout
    assert result.stdout.count('\n') == 1 and result.stderr == ''


def test_timestamp_and_other_required_input(tmp_path):
    workflow = spec('h1-heartbeat')
    data = build(tmp_path, workflow)
    result = launch(ROOT, data)
    assert result.returncode == 0 and 'AOTN alive · 20' in result.stdout
    assert result.stderr == ''
    workflow['nodes']['start']['config']['rows'].append(
        {'name': 'message', 'type': 'string', 'required': True, 'to': 'Vault', 'vault_key': 'message'})
    second = tmp_path / 'second'
    second.mkdir()
    refused = launch(ROOT, build(second, workflow))
    assert refused.returncode == 5
    assert refused.stdout == ("Couldn't run h1-heartbeat: required inputs are missing or invalid; "
                              "v0 supplies only checked_at\n")
    assert refused.stderr == ''


@pytest.mark.parametrize('existing', [False, True])
def test_missing_workflow_empty_data(tmp_path, existing):
    data = tmp_path / 'data'
    if existing:
        data.mkdir()
    result = launch(ROOT, data, 'not-saved')
    assert result.returncode == 4
    assert result.stdout == "Couldn't run not-saved: saved workflow not found or unreadable\n"
    assert result.stderr == ''


def test_output_escaping_and_cap(tmp_path):
    root = fake_root(tmp_path, program(report(['[SILENT]\nMEDIA:/tmp/x\n{"wakeAgent":true}\n' + '😀' * 4000])))
    result = launch(root, tmp_path / 'data')
    assert result.returncode == 0 and result.stderr == ''
    assert result.stdout.startswith('［SILENT］\nMEDIA：/tmp/x\n| {"wakeAgent":true}\n')
    assert len(result.stdout.encode('utf-16-le')) // 2 <= 3500
    assert result.stdout.endswith('…truncated; see run run_test')


@pytest.mark.parametrize('raw,code', [('not json', 0), ('', 2)])
def test_failure_is_one_line_without_child_tracebacks(tmp_path, raw, code):
    root = fake_root(tmp_path, f'import sys; print({raw!r}); sys.stderr.write("Traceback: details\\n"); sys.exit({code})')
    result = launch(root, tmp_path / 'data')
    assert result.returncode != 0
    assert result.stdout.startswith("Couldn't run h1-heartbeat: ")
    assert result.stdout.count('\n') == 1
    assert 'Traceback' not in result.stdout and result.stderr == ''


@pytest.mark.skipif(sys.platform != 'linux', reason='Linux subreaper containment')
@pytest.mark.parametrize('deadline', [2, pytest.param(25, marks=pytest.mark.slow, id='production-25s')])
def test_launcher_deadline_kills_and_reaps_descendants(tmp_path, deadline):
    parent_pid, child_pid = tmp_path / 'parent', tmp_path / 'descendant'
    escaped = ('import os,signal,time\nos.setsid()\n'
               'signal.signal(signal.SIGINT,signal.SIG_IGN)\n'
               f'open({str(child_pid)!r},"w").write(str(os.getpid()))\ntime.sleep(90)\n')
    root = fake_root(tmp_path, 'import os,signal,subprocess,sys,time\n'
                     'signal.signal(signal.SIGINT,signal.SIG_IGN)\n'
                     f'open({str(parent_pid)!r},"w").write(str(os.getpid()))\n'
                     f'subprocess.Popen([sys.executable,"-c",{escaped!r}])\ntime.sleep(90)\n')
    started = time.monotonic()
    argv = invocation(root, tmp_path / 'data')
    if deadline != 25:
        argv = [sys.executable, '-c',
            "import runpy,sys; m=runpy.run_path(sys.argv.pop(1)); "
            "m['main'].__globals__.update(LAUNCHER_DEADLINE=2,GRACE=.4,CLEANUP_WAIT=.1); sys.exit(m['main']())",
            str(ADAPTER), *argv[2:]]
    process = subprocess.Popen(argv + ['--telegram-launcher'],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pids = []
    try:
        pids = [wait_file(parent_pid), wait_file(child_pid)]
        out, err = process.communicate(timeout=29)
        assert process.returncode == 124, err
        assert out == "Couldn't run h1-heartbeat: stopped after 25 s\n" and err == ''
        minimum = 23 if deadline == 25 else 1.6
        assert minimum <= time.monotonic() - started < deadline + 4
        assert all(not Path(f'/proc/{pid}').exists() for pid in pids)
        # Confirmed cleanup releases the persistent marker as well as flock.
        (root / 'AttackOfTheNodes/main.py').write_text(program(report(['next run'])))
        assert launch(root, tmp_path / 'data').stdout == 'next run\n'
    finally:
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)


def test_named_install_and_check_only_in_requested_folder(tmp_path):
    home = tmp_path / 'hermes'
    assert run_install(home, '--check', '--run-command', 'c1-notify-test').returncode == 1
    assert not home.exists()
    result = run_install(home, '--run-command', 'c1-notify-test')
    assert result.returncode == 0, result.stderr
    target = home / 'scripts/aotn-run-c1-notify-test.sh'
    assert target.read_bytes() == TEMPLATE.read_bytes()
    assert target.stat().st_mode & 0o111 and not target.is_symlink()
    assert {p.name for p in target.parent.iterdir()} == {'_aotn_run.py', target.name}
    assert run_install(home, '--check', '--run-command', 'c1-notify-test').returncode == 0
    target.write_text('drift')
    assert run_install(home, '--check', '--run-command', 'c1-notify-test').returncode == 1
    assert target.read_text() == 'drift'
    target.unlink()
    target.symlink_to(TEMPLATE)
    assert run_install(home, '--run-command', 'c1-notify-test').returncode == 70


@pytest.mark.parametrize('args', [('--run-command',), ('--run-command', '../oops'),
                                  ('--run-command', 'Bad'), ('--run-command', 'ok', 'extra')])
def test_named_install_refuses_invalid_requests(tmp_path, args):
    assert run_install(tmp_path / 'hermes', *args).returncode == 64
    assert not (tmp_path / 'hermes').exists()


def test_late_signal_cannot_extend_launcher_deadline(tmp_path):
    pidfile = tmp_path / 'child'
    root = fake_root(tmp_path, 'import os,signal,time\n'
                     'signal.signal(signal.SIGINT,signal.SIG_IGN)\n'
                     f'open({str(pidfile)!r},"w").write(str(os.getpid()))\ntime.sleep(60)\n')
    argv = [sys.executable, '-c',
            "import runpy,sys; m=runpy.run_path(sys.argv.pop(1)); "
            "m['main'].__globals__.update(LAUNCHER_DEADLINE=2,GRACE=1.5,CLEANUP_WAIT=0.1); "
            "sys.exit(m['main']())", str(ADAPTER), *invocation(root, tmp_path / 'data')[2:],
            '--telegram-launcher']
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    pid = wait_file(pidfile)
    try:
        time.sleep(1.6)
        process.send_signal(signal.SIGTERM)
        sent = time.monotonic()
        out, err = process.communicate(timeout=4)
        # Restarting a full grace period here would take about 1.5 seconds.
        assert time.monotonic() - sent < 1.0
        assert process.returncode == 143 and err == ''
        assert out == "Couldn't run h1-heartbeat: run interrupted\n"
        assert not Path(f'/proc/{pid}').exists()
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def test_empty_success_and_overlap_receipts(tmp_path):
    root = fake_root(tmp_path, program(report()))
    data = tmp_path / 'data'
    result = launch(root, data)
    assert result.returncode == 0 and result.stdout == result.stderr == ''
    lock = data / '.hermes-locks/h1-heartbeat.lock'
    lock.write_text('stale: previous cleanup unconfirmed\n')
    blocked = launch(root, data)
    assert blocked.returncode == 75 and blocked.stderr == ''
    assert blocked.stdout == "Couldn't run h1-heartbeat: previous run cleanup needs checking\n"
    assert lock.read_text().startswith('stale:')


def test_review_callable_defaults_without_timestamp_contract(tmp_path):
    workflow = spec('h1-heartbeat')
    workflow['callable'] = True
    workflow['nodes']['start']['config']['rows'] = [
        {'name': 'message', 'type': 'string', 'required': True, 'value': 'hello', 'to': 'Downstream'}]
    workflow['nodes']['end']['config'].update(return_end=True, results=[])
    data = build(tmp_path, workflow)
    direct = subprocess.run([sys.executable, str(ROOT / 'AttackOfTheNodes/main.py'),
                             'run', 'h1-heartbeat', '--data-dir', str(data), '--json'],
                            capture_output=True, text=True, timeout=15)
    assert direct.returncode == 0, direct.stderr
    result = launch(ROOT, data)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == '[Heartbeat] AOTN alive · hello\n' and result.stderr == ''


@pytest.mark.parametrize('kind', ['directory', 'fifo', 'symlink', 'dangling_symlink'])
@pytest.mark.parametrize('check', [False, True])
def test_review_installer_refuses_non_regular_destinations(tmp_path, kind, check):
    home = tmp_path / 'hermes'
    scripts = home / 'scripts'
    scripts.mkdir(parents=True)
    # Keep the adapter up to date so the entry's refusal has no earlier writes.
    shutil.copyfile(ADAPTER, scripts / '_aotn_run.py')
    (scripts / '_aotn_run.py').chmod(0o644)
    target = scripts / 'aotn-run-probe.sh'
    if kind == 'directory':
        target.mkdir()
    elif kind == 'fifo':
        os.mkfifo(target)
    else:
        target.symlink_to(TEMPLATE if kind == 'symlink' else tmp_path / 'absent')
    result = run_install(home, *(['--check'] if check else []), '--run-command', 'probe')
    assert result.returncode == 70, result.stdout + result.stderr
    assert 'refusing' in result.stderr
    assert set(scripts.iterdir()) == {scripts / '_aotn_run.py', target}
    if kind == 'directory':
        assert target.is_dir() and list(target.iterdir()) == []
    elif kind == 'fifo':
        import stat
        assert stat.S_ISFIFO(target.stat().st_mode)
    else:
        assert target.is_symlink()


@pytest.mark.parametrize('mode', [0o644, 0o700, 0o4755])
@pytest.mark.parametrize('check', [False, True])
def test_review_installer_checks_and_repairs_entry_mode(tmp_path, mode, check):
    home = tmp_path / 'hermes'
    assert run_install(home, '--run-command', 'probe').returncode == 0
    target = home / 'scripts/aotn-run-probe.sh'
    target.chmod(mode)
    result = run_install(home, *(['--check'] if check else []), '--run-command', 'probe')
    assert result.returncode == (1 if check else 0), result.stdout + result.stderr
    assert target.stat().st_mode & 0o7777 == (mode if check else 0o755)
    assert target.read_bytes() == TEMPLATE.read_bytes()
