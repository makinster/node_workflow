"""Private Linux subreaper broker for the isolated Hermes profile CLI."""
import json
import os
from pathlib import Path
import runpy
import sys
import time

# Explicit sibling path, independent of the selected working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hermes_worker import PROTOCOL, MAX_QUESTION, parse_tools, parse_answer, is_auth_failure

MAX_REQUEST = 512 * 1024


def main():
    result = {'status': 'agent_failed', 'cleanup_confirmed': True}
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        request = json.loads(raw) if len(raw) <= MAX_REQUEST else {}
        if request.get('protocol') != PROTOCOL or sys.platform != 'linux':
            result['status'] = 'unsupported_runtime'
        else:
            question = request['question']
            if not isinstance(question, str) or not question.strip() or '\0' in question:
                raise ValueError
            if len(question) > MAX_QUESTION:
                result['status'] = 'text_too_long'
                print(json.dumps(result))
                return 0
            profile = Path(request['profile'])
            command = Path(request['command'])
            config = profile / 'config.yaml'
            if not profile.is_absolute() or not profile.is_dir() or not config.is_file():
                result['status'] = 'profile_missing'
            elif not command.is_absolute() or not command.is_file() or not os.access(command, os.X_OK):
                result['status'] = 'not_installed'
            else:
                # This env belongs only to this disposable broker and its CLI
                # children. Never mutate the app's/default Hermes environment.
                os.environ['HERMES_HOME'] = str(profile)
                h0_path = Path(__file__).resolve().parents[2] / 'integrations/hermes/_aotn_run.py'
                h0 = runpy.run_path(str(h0_path))

                def collect(argv):
                    remaining = request['expires_at'] - time.monotonic()
                    if remaining <= 0:
                        return None, b'', '', 'deadline', None
                    return h0['collect'](argv, request['folder'], deadline=remaining)

                before = config.stat()
                code, output, diagnostic, reason, _ = collect([str(command), 'tools', 'list', '--platform', 'cli'])
                if reason is not None:
                    result['status'] = {'deadline': 'timed_out', 'signal': 'cancelled',
                                        'overflow': 'permission_denied'}.get(reason, 'agent_failed')
                else:
                    try:
                        if code != 0:
                            raise ValueError
                        parse_tools(output, diagnostic.encode('utf-8'))
                        after = config.stat()
                        if (before.st_ino, before.st_mtime_ns, before.st_size) != (after.st_ino, after.st_mtime_ns, after.st_size):
                            raise ValueError
                    except (ValueError, UnicodeError):
                        result['status'] = 'permission_denied'
                    else:
                        # One attached argv element: Hermes's early --profile
                        # scan and argparse both read it as question text.
                        argv = [str(command), 'chat', '--query=' + question, '-Q', '--source', 'tool',
                                '--max-turns', '1', '--ignore-rules']
                        code, output, diagnostic, reason, _ = collect(argv)
                        if reason is not None:
                            result['status'] = {'deadline': 'timed_out', 'signal': 'cancelled',
                                                'overflow': 'invalid_response'}.get(reason, 'agent_failed')
                        elif code != 0:
                            result['status'] = 'auth_failed' if is_auth_failure(output, diagnostic.encode('utf-8')) else 'agent_failed'
                        else:
                            try:
                                answer = parse_answer(output)
                            except (ValueError, UnicodeError):
                                result['status'] = 'auth_failed' if is_auth_failure(output, diagnostic.encode('utf-8')) else 'invalid_response'
                            else:
                                result.update(status='reply', answer=answer)
    except FileNotFoundError:
        result['status'] = 'profile_missing'
    except BaseException as exc:
        # No raw CLI output, traceback, question, account metadata or secrets.
        if type(exc).__name__ == 'CleanupFailure':
            result = {'status': 'cleanup_failed', 'cleanup_confirmed': False}
    sys.stdout.write(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
