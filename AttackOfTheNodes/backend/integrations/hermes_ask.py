"""Ask Hermes service: bounded subprocesses, private records and safe receipts.

Uses the public CLI with an independent profile, not Hermes Python internals.
Every question gets a strict tools preflight and the same total cleanup deadline.
"""
import asyncio
from datetime import datetime, timezone
import hashlib
try:
    import fcntl
except ImportError:  # Native Windows is deliberately unsupported.
    fcntl = None
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import uuid

from .. import persistence, hermes_folder
from ..file_refs import file_reference
from ..node_errors import NodeError
from .hermes_worker import POLICY, PROTOCOL

MAX_QUESTION = 20_000
MAX_ANSWER = 256 * 1024
MAX_RECORD = 4 * 1024 * 1024
FINAL_RESERVE = 64 * 1024
MAX_BROKER = 2 * 1024 * 1024
USAGE_EVENT = 'AGENT_USAGE_UPDATE'
MESSAGES = {
    'not_installed': 'Hermes is not installed',
    'profile_missing': 'Set up the aotn Hermes profile first',
    'unsupported_runtime': 'Ask Hermes needs a native Linux runtime.',
    'auth_failed': 'Sign in to Hermes (aotn profile)',
    'folder_missing': 'Choose an existing folder.',
    'not_allowed': 'This folder is not allowed in Options.',
    'text_too_long': 'The question is too long.',
    'timed_out': 'Stopped after the time limit.',
    'turn_limit': 'Stopped after the turn limit.',
    'permission_denied': 'This Hermes profile has tools turned on.',
    'agent_failed': 'Hermes could not finish.',
    'invalid_response': 'No complete answer was returned.',
    'record_failed': 'The run record could not be saved.',
    'cleanup_failed': 'The agent did not stop cleanly.',
}


def failure(code, details=None):
    return NodeError(code, MESSAGES[code], retryable=False, details=details or {})


def setting(context, name, default):
    return context.get_setting(name) if context.get_setting is not None else default


def private_dir(path):
    # Never follow a link while creating an audit/ownership directory.
    if path.is_symlink():
        raise OSError
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    if not path.is_dir() or path.is_symlink():
        raise OSError
    path.chmod(0o700)
    return path


class Record:
    def __init__(self, context, timeout, folder):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', context.run_id):
            raise OSError
        self.context = context
        self.invocation_id = 'ask_' + uuid.uuid4().hex
        root = persistence.RUN_OUTPUTS_DIR
        root.mkdir(parents=True, exist_ok=True)
        if root.is_symlink():
            raise OSError
        markers = private_dir(root / '.ask-hermes-workers')
        # Active invocations hold flock; a released but retained marker means
        # an earlier owner crashed or could not confirm descendant cleanup.
        for path in markers.iterdir():
            try:
                fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
            except FileNotFoundError:
                continue
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    continue
                if path.exists():
                    raise failure('cleanup_failed')
            finally:
                os.close(fd)
        directory = private_dir(private_dir(root / context.run_id) / 'agents')
        self.path = directory / (self.invocation_id + '.jsonl')
        self.marker = markers / (self.invocation_id + '.lock')
        self.owner = os.open(self.marker, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        self.stream = None
        try:
            fcntl.flock(self.owner, fcntl.LOCK_EX)
            os.write(self.owner, json.dumps({'owner_pid': os.getpid(), 'invocation_id': self.invocation_id}).encode())
            os.fsync(self.owner)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            self.stream = os.fdopen(fd, 'wb')
        except BaseException:
            self.close(True)
            raise

    def start(self, timeout, folder):
        self.write({'event': 'started', 'run_id': self.context.run_id,
                        'node_id': self.context.node_id, 'branch_id': self.context.branch_id,
                        'invocation_id': self.invocation_id, 'folder': redact(self.context, str(folder)),
                        'limits': {'seconds': timeout, 'turns': 1, 'budget_usd': None},
                        'policy': POLICY})
        self.receipt('started', None)

    def write(self, event, final=False):
        data = (json.dumps({'schema': 'aotn-agent-run/1', 'at': datetime.now(timezone.utc).isoformat(), **event}, ensure_ascii=False,
                           allow_nan=False) + '\n').encode()
        limit = MAX_RECORD + FINAL_RESERVE if final else MAX_RECORD
        if len(data) > (FINAL_RESERVE if final else MAX_RECORD) or self.stream.tell() + len(data) > limit:
            raise OSError
        self.stream.write(data)
        self.stream.flush()
        os.fsync(self.stream.fileno())

    def receipt(self, status, usage):
        cost = (usage or {}).get('estimated_cost_usd')
        note = 'Cost not reported' if cost is None else f'USD {cost:g} estimated'
        # Never put question, answer, stderr, identity/profile or credentials
        # into the shared folder's receipt.
        hermes_folder.record_event(origin=hermes_folder.origin_of(self.context),
            name='agent.ask_hermes.' + status,
            summary=f'Ask Hermes: {status}; {note}', value=None,
            repeat_key=self.invocation_id + '/' + status, repeat_minutes=0)

    def close(self, confirmed):
        try:
            if self.stream is not None:
                self.stream.close()
            if confirmed:
                self.marker.unlink(missing_ok=True)
        finally:
            os.close(self.owner)


def redact(context, value):
    manager = context.secrets_manager
    if manager is None:
        return value
    for key in manager.list_keys():
        secret = manager.get_secret(key)
        if secret:
            value = value.replace(secret, '[redacted]')
    return value


def broker_command():
    return [sys.executable, '-I', '-S', '-u', str(Path(__file__).with_name('hermes_process.py'))]


def worker_env():
    # CLI resolves auth only from its selected profile; strip unrelated keys,
    # sticky HERMES_HOME, Python paths and agent overrides from the app env.
    return {key: value for key, value in os.environ.items()
            if key in {'HOME', 'PATH', 'LANG', 'LC_ALL', 'TMPDIR'}} | {
                'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}


async def exchange(process, request):
    # ASCII JSON preserves every valid question up to MAX_QUESTION, even
    # when its UTF-16 escapes are larger than its eventual UTF-8 argv.
    process.stdin.write(json.dumps(request, ensure_ascii=True).encode('ascii'))
    try:
        await process.stdin.drain()
    except (BrokenPipeError, ConnectionResetError):
        pass
    process.stdin.close()
    output = bytearray()
    while True:
        chunk = await process.stdout.read(8192)
        if not chunk:
            break
        if len(output) + len(chunk) > MAX_BROKER:
            raise failure('invalid_response')
        output.extend(chunk)
    await process.wait()
    try:
        data = json.loads(output)
    except (ValueError, RecursionError):
        raise failure('invalid_response') from None
    if not isinstance(data, dict) or type(data.get('cleanup_confirmed')) is not bool:
        raise failure('invalid_response')
    return data


def signal_group(process, sig):
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


async def stop(process, io, expires):
    signal_group(process, signal.SIGTERM)
    try:
        # The broker caps late-stop cleanup at its original deadline. One
        # extra second is transport/reaping, never extra model runtime.
        return await asyncio.wait_for(asyncio.shield(io), min(5, max(0, expires-time.monotonic())) + 1)
    except (asyncio.TimeoutError, NodeError, OSError):
        signal_group(process, signal.SIGKILL)
        await process.wait()
        if not io.done():
            io.cancel()
        await asyncio.gather(io, return_exceptions=True)
        return {'status': 'cleanup_failed', 'cleanup_confirmed': False}


async def settle(task):
    # Repeated Stop requests must not interrupt the broker's reaping budget.
    while True:
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            if task.done():
                return task.result()


def parse_reply(data):
    status = data.get('status')
    if status != 'reply':
        raise failure(status if isinstance(status, str) and status in MESSAGES else 'agent_failed')
    answer = data.get('answer')
    if not isinstance(answer, str) or not answer.strip() or len(answer.encode('utf-8')) > MAX_ANSWER:
        raise failure('invalid_response')
    # -Q is answer-only, not a token/cost/turn telemetry protocol. Do not
    # manufacture measurements from the configured one-turn limit.
    usage = {key: None for key in ('input_tokens', 'output_tokens', 'cache_tokens',
                                   'estimated_cost_usd', 'provider', 'model')}
    usage['cost_status'] = 'not_reported'
    return answer, usage


async def ask(context, question, folder, timeout):
    started = time.monotonic()
    expires = started + timeout
    if sys.platform != 'linux' or fcntl is None:
        raise failure('unsupported_runtime')
    record = None
    confirmed = True
    status, usage, answer = 'agent_failed', {}, None
    problem = None
    cancelled = False
    try:
        record = Record(context, timeout, folder)
        try:
            record.start(timeout, folder)
        except OSError:
            raise failure("record_failed") from None
        if setting(context, 'hermes_allow_no_budget', False) is not True:
            raise NodeError('node_error', 'Allow Ask Hermes without a dollar cap in Options first.', retryable=False)
        profile_value = setting(context, 'hermes_profile_home', '~/.hermes/profiles/aotn')
        command_value = setting(context, 'hermes_command', '~/.local/bin/hermes')
        if not isinstance(profile_value, str) or not profile_value.strip():
            raise failure('profile_missing')
        if not isinstance(command_value, str) or not command_value.strip():
            raise failure('not_installed')
        profile = str(Path(profile_value).expanduser().resolve())
        command = str(Path(command_value).expanduser().resolve())
        request = {'protocol': PROTOCOL, 'policy': POLICY, 'question': question,
                   'folder': str(folder), 'profile': profile, 'command': command, 'expires_at': expires}
        if time.monotonic() >= expires:
            raise failure('timed_out')
        spawn = asyncio.create_task(asyncio.create_subprocess_exec(*broker_command(), cwd=str(folder),
                    stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL, start_new_session=True, env=worker_env()))
        process = None
        io = None
        try:
            process = await asyncio.shield(spawn)
            confirmed = False
            io = asyncio.create_task(exchange(process, request))
            data = await asyncio.wait_for(asyncio.shield(io), max(.01, expires-time.monotonic()) + 1)
            confirmed = data['cleanup_confirmed']
            if not confirmed:
                raise failure('cleanup_failed')
            answer, usage = parse_reply(data)
            answer = redact(context, answer)
            status = 'completed'
        except asyncio.CancelledError:
            try:
                process = await settle(spawn)
            except OSError:
                cancelled = True
                status = 'cancelled'
                raise asyncio.CancelledError from None
            if io is None:
                io = asyncio.create_task(exchange(process, request))
            data = await settle(asyncio.create_task(stop(process, io, expires)))
            confirmed = data.get('cleanup_confirmed') is True
            try:
                _, usage = parse_reply(data)
            except NodeError:
                pass
            cancelled = True
            status = 'cancelled' if confirmed else 'cleanup_failed'
        except (asyncio.TimeoutError, NodeError, OSError) as exc:
            if process is not None and not confirmed:
                if io is None:
                    io = asyncio.create_task(exchange(process, request))
                data = await settle(asyncio.create_task(stop(process, io, expires)))
                confirmed = data.get('cleanup_confirmed') is True
            if not confirmed:
                raise failure('cleanup_failed') from None
            if isinstance(exc, asyncio.TimeoutError):
                raise failure('timed_out') from None
            raise
    except asyncio.CancelledError:
        cancelled = True
        status = 'cancelled' if confirmed else 'cleanup_failed'
    except NodeError as exc:
        problem = exc
        status = exc.code
    except (OSError, ValueError, TypeError):
        problem = failure('record_failed' if record is None else 'agent_failed')
        status = problem.code
    finally:
        if record is not None:
            # Stop can race a completed reply; sanitize identity fields on
            # every terminal path, including cancellation.
            usage = {key: redact(context, value) if isinstance(value, str) else value
                     for key, value in usage.items()}
            details = {'invocation_id': record.invocation_id, 'node_id': context.node_id,
                'branch_id': context.branch_id, 'run_id': context.run_id, 'status': status,
                'seconds': round(time.monotonic()-started, 3), 'turns': None,
                'tools': [], 'usage': usage or {'estimated_cost_usd': None, 'cost_status': 'not_reported'},
                'record': file_reference(str(record.path)), 'cleanup_confirmed': confirmed,
                'account_source': 'hermes-profile',
                'limits': {'seconds': timeout, 'turns': 1, 'budget_usd': None},
                'partial': status != 'completed',
                'answer_bytes': len(answer.encode('utf-8')) if answer else None,
                'answer_sha256': hashlib.sha256(answer.encode('utf-8')).hexdigest() if answer else None}
            try:
                if answer is not None and status == 'completed':
                    record.write({'event': 'answer', 'answer': answer})
                record.write({'event': 'finished', **details}, final=True)
                record.receipt(status, usage)
            except (OSError, ValueError):
                details['status'] = 'record_failed'
                problem = failure('record_failed', details)
                try:
                    record.write({'event': 'record_failed', **details}, final=True)
                except OSError:
                    pass
            finally:
                try:
                    record.close(confirmed)
                except OSError:
                    details['status'] = 'record_failed'
                    problem = failure('record_failed', details)
            context.emit_event(USAGE_EVENT, details)
    if cancelled:
        raise asyncio.CancelledError
    if problem is not None:
        if record is not None:
            problem.details = details
        raise problem
    return answer, details
