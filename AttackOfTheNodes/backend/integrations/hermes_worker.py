"""Isolated standard-library-only compatibility gate. Never imports Hermes.

The installed 0.14 runtime cannot guarantee a tool-free, read-only, single-call
AIAgent: imports discover plugins; its conversation loop has extra retry paths.
There is deliberately no approved adapter for it. New versions do not opt in
by version number alone: adding an adapter requires a separate source audit and
containment tests. Refusal occurs before auth, memory loading or inference.
"""
import json
from pathlib import Path
import re
import sys

PROTOCOL = 'aotn-hermes-worker/1'
POLICY = {'tools': [], 'memory': 'read-only', 'memory_writeback': False,
          'plugins': False, 'hooks': False, 'mcp': False, 'context_files': False,
          'fallback_models': [], 'max_turns': 1, 'automatic_retries': 0}
MAX_REQUEST = 128 * 1024


def main():
    status = 'unsupported_runtime'
    try:
        raw = sys.stdin.buffer.read(MAX_REQUEST + 1)
        request = json.loads(raw) if len(raw) <= MAX_REQUEST else None
        if (not isinstance(request, dict) or request.get('protocol') != PROTOCOL
                or request.get('policy') != POLICY):
            status = 'unsupported_runtime'
        else:
            root = Path(request['installation'])
            version_file = root / 'hermes_cli/__init__.py'
            if not version_file.is_file():
                status = 'not_installed'
            else:
                # Read the literal without executing __init__, sitecustomize,
                # plugin discovery, provider resolution or credential code.
                with version_file.open('rb') as stream:
                    source = stream.read(64 * 1024)
                match = re.search(rb'^__version__\s*=\s*[\'"]([^\'"\r\n]+)', source, re.M)
                # No installed release has an audited compatible adapter.
                # Unknown/modified versions also remain refused, not trusted.
                if match is not None:
                    status = 'unsupported_runtime'
    except (OSError, ValueError, KeyError, TypeError):
        status = 'unsupported_runtime'
    print(json.dumps({'protocol': PROTOCOL, 'status': status}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
