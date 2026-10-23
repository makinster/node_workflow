"""Strict, stdlib-only parsers for the profile CLI. Never imports Hermes."""
import re

PROTOCOL = 'aotn-hermes-cli/2'
POLICY = {'isolation': 'profile', 'tools': [], 'memory': 'off',
          'context_files': False, 'max_turns': 1}
MAX_QUESTION = 20_000
MAX_ANSWER = 256 * 1024
# Inventory verified against the owner's CLI. New/changed output needs review,
# never silently accepts a truncated listing or a newly introduced toolset.
TOOLSETS = frozenset('web browser terminal file code_execution vision video image_gen '
    'video_gen x_search moa tts skills todo memory session_search clarify delegation '
    'cronjob messaging homeassistant spotify yuanbao computer_use'.split())
SGR = re.compile(r'\x1b\[[0-9;]*m')
SESSION = re.compile(r'(?:session_id|Session|Session ID):\s*[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}')


def text(raw):
    value = SGR.sub('', raw.decode('utf-8'))
    if any(ord(char) < 32 and char not in '\n\r\t' or ord(char) == 127 for char in value):
        raise ValueError('control character')
    return value.replace('\r\n', '\n')


def parse_tools(output, diagnostic=b''):
    lines = [line for line in text(output + b'\n' + diagnostic).splitlines() if line.strip()]
    if not lines or lines.pop(0) != 'Built-in toolsets (cli):':
        raise ValueError('unknown listing')
    seen = set()
    for line in lines:
        row = re.fullmatch(r'  ✗ disabled  ([a-z][a-z0-9_]*)  \S.*', line)
        if row is None or row[1] not in TOOLSETS or row[1] in seen:
            raise ValueError('unclassified toolset')
        seen.add(row[1])
    if seen != TOOLSETS:
        raise ValueError('incomplete listing')


def parse_answer(output):
    # The collector bounds the whole CLI stream to 1 MiB. The answer cap
    # applies after removing its final newline/session metadata.
    if len(output) > 1024 * 1024:
        raise ValueError('CLI output too long')
    # CLI framing is LF-delimited. Unicode separators inside the finding
    # are data, as in the C1 shared-folder records, not framing to rewrite.
    lines = text(output).strip(' \t\r\n').split('\n')
    # -Q writes session_id to stderr today. Recognise the bounded metadata
    # line at stdout's edges too; never return a session receipt as an answer.
    while lines and SESSION.fullmatch(lines[-1].strip()):
        lines.pop()
    while lines and SESSION.fullmatch(lines[0].strip()):
        lines.pop(0)
    answer = '\n'.join(lines).strip(' \t\r\n')
    # An embedded receipt in any recognised form is never answer text.
    if (not answer or len(answer.encode('utf-8')) > MAX_ANSWER
            or any(SESSION.fullmatch(line.strip()) or re.match(r'\s*(?:session_id|Session ID):', line) for line in answer.splitlines())
            or answer.startswith(('Error:', 'Traceback (most recent call last):', 'Built-in toolsets ('))):
        raise ValueError('no answer')
    return answer


def is_auth_failure(output, diagnostic):
    # Only called on a failed/empty/error-shaped reply, never on successful
    # answer prose (which may itself discuss authentication).
    value = (output + b'\n' + diagnostic).decode('utf-8', errors='replace')
    return bool(re.search(r'\b(?:401|403|unauthorized|unauthenticated|authentication|oauth)\b'
        r'|(?:sign|log)\s*in|\blogin\b|credentials?|token.{0,40}expir|invalid.{0,20}api.?key', value, re.I))
