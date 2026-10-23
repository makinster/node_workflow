"""Private subreaper broker; shared H0 process ownership, no provider imports."""
import json
from pathlib import Path
import runpy
import sys
import time

PROTOCOL = 'aotn-hermes-worker/1'
MAX_REQUEST = 128 * 1024


def worker_command(installation):
    root = Path(installation)
    python = root / 'venv/bin/python'
    if not python.is_file() or not (root / 'hermes_cli/__init__.py').is_file():
        raise FileNotFoundError
    return [str(python), '-I', '-S', '-u', str(Path(__file__).with_name('hermes_worker.py'))]


def main():
    result = {'status': 'agent_failed', 'cleanup_confirmed': True}
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        request = json.loads(raw) if len(raw) <= MAX_REQUEST else {}
        if request.get('protocol') != PROTOCOL or sys.platform != 'linux':
            result['status'] = 'unsupported_runtime'
        else:
            h0_path = Path(__file__).resolve().parents[2] / 'integrations/hermes/_aotn_run.py'
            h0 = runpy.run_path(str(h0_path))
            remaining = request['expires_at'] - time.monotonic()
            if remaining <= 0:
                result['status'] = 'timed_out'
            else:
                argv = worker_command(request['installation'])
                code, output, _, reason, _ = h0['collect'](
                    argv, request['folder'], deadline=remaining, input_bytes=raw)
                if reason == 'deadline':
                    result['status'] = 'timed_out'
                elif reason == 'signal':
                    result['status'] = 'cancelled'
                elif reason == 'overflow':
                    result['status'] = 'invalid_response'
                elif code != 0:
                    result['status'] = 'agent_failed'
                else:
                    try:
                        data = json.loads(output)
                    except (ValueError, RecursionError):
                        data = None
                    result = {'status': 'reply', 'reply': data, 'cleanup_confirmed': True}
    except FileNotFoundError:
        result['status'] = 'not_installed'
    except BaseException as exc:
        # CleanupFailure is defined in the loaded H0 module; do not stringify
        # worker/OS errors or raw stderr into diagnostics or protocol output.
        if type(exc).__name__ == 'CleanupFailure':
            result = {'status': 'cleanup_failed', 'cleanup_confirmed': False}
        else:
            result['status'] = 'agent_failed'
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
