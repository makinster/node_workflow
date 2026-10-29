"""Check-only workflow adapter and atomic run-output publication. No library writer."""
from __future__ import annotations

import asyncio
import json
import math

from . import authoring
from .hermes_investigations import redact
from .node_errors import NodeError

SPEC_SOURCES = ('Upstream payload', 'Vault', 'Configured')
MAX_BYTES = 256 * 1024
MAX_NODES = 128
MAX_CONNECTIONS = 256
MAX_DEPTH = 64
PROBLEM_LIMIT = 100
PROBLEM_CHARS = 8000


def validate_outputs(config, *, report=False):
    if config.get('dead_drop_passthrough', False) is not False:
        raise NodeError('invalid_config', 'This node always outputs its result; input forwarding is unavailable.')
    keys = []
    for flag, key in [('vault_write', 'vault_write_key')] + ([('report_vault_write', 'report_vault_key')] if report else []):
        if type(config.get(flag, False)) is not bool:
            raise NodeError('invalid_config', 'Check the Vault output options.')
        if config.get(flag):
            value = config.get(key)
            if not isinstance(value, str) or not value.strip() or value.strip() in keys:
                raise NodeError('invalid_config', 'Enter a different Vault key for each enabled output.')
            keys.append(value.strip())
    if type(config.get('transient_output', True)) is not bool:
        raise NodeError('invalid_config', 'Check the downstream output option.')


def publish(config, context, value, tag, report=None):
    # Validation and cancellation points precede all writes. No await separates
    # these in-memory writes from completion, and no library API is involved.
    if report is not None and config.get('report_vault_write'):
        context.memory_bank.store_persistent(config['report_vault_key'].strip(), report, type_tag='var')
    if config.get('vault_write'):
        context.memory_bank.store_persistent(config['vault_write_key'].strip(), value, type_tag=tag)
    context.signal_done({'data': {'default': value} if config.get('transient_output', True) else {}})


def spec_source(config, context):
    source = config.get('input_source')
    if source == 'Upstream payload':
        return context.inputs.get('input')
    if source == 'Vault':
        key = config.get('input_vault_key')
        if not isinstance(key, str) or not key.strip():
            raise NodeError('invalid_config', 'Choose a Spec Vault key.')
        return context.memory_bank.read_persistent(key)
    if source == 'Configured':
        return config.get('input')
    raise NodeError('invalid_config', 'Choose Upstream, Vault or Configured for the Spec.')


def _depth(text):
    depth = 0
    quoted = escaped = False
    for char in text:
        if quoted:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in '[{':
            depth += 1
            if depth > MAX_DEPTH:
                raise NodeError('spec_too_large', 'Spec nesting exceeds 64 levels.')
        elif char in ']}':
            depth -= 1


def _json_value(value):
    """Reject invalid Unicode/non-finite decoded leaves before validation/output."""
    if isinstance(value, str):
        value.encode('utf-8')
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError('non-finite number')
    elif isinstance(value, dict):
        for k, v in value.items():
            _json_value(k)
            _json_value(v)
    elif isinstance(value, list):
        for v in value:
            _json_value(v)


def _nonfinite(_):
    raise ValueError('non-finite JSON constant')


class _Pairs(list):
    """An object's (key, value) pairs in source order, before dict collapse."""


def _objects(value, path, duplicates):
    """Build dicts from parsed pairs, noting every repeated key's path."""
    if isinstance(value, _Pairs):
        result = {}
        for key, item in value:
            where = f'{path}.{key}' if path else key
            if key in result:
                duplicates.append(where)
            result[key] = _objects(item, where, duplicates)
        return result
    if isinstance(value, list):
        return [_objects(item, f'{path}[{n}]', duplicates) for n, item in enumerate(value)]
    return value


def _duplicate_diagnostics(paths):
    rows = []
    for path in paths:
        parts = path.split('.')
        node = parts[1] if len(parts) > 1 and parts[0] == 'nodes' else None
        rows.append(dict(node=node, field=path, code='duplicate_key', level='error'))
    return rows


SAFE_MESSAGES = {
    'spec_invalid': 'This spec field has an invalid shape or value.',
    'bad_handle': 'Use a lowercase handle starting with a letter (letters, digits and underscore).',
    'unknown_node_type': 'Choose an available node type from the catalogue.',
    'unknown_config_key': 'Unknown config field; see this node’s catalogue entry.',
    'invalid_number': 'Enter a finite number in this field’s allowed range.',
    'unknown_reference': 'Reference must name a node handle in this spec.',
    'unknown_port': 'Connection names a port unavailable with this node configuration.',
    'duplicate_connection': 'This connection is listed more than once.',
    'duplicate_key': 'This JSON key appears more than once; keep only one.',
    'file_not_found': 'The configured file was not found at check time.',
    'unreachable': 'Node is not reachable from Start.',
    'no_start_node': 'The workflow needs a Start node.',
    'multiple_start_nodes': 'The workflow has more than one Start node.',
    'ignored_fan_out': 'An output has several destinations; use a branching node.',
}


def _safe(value, manager, limit):
    if value is None:
        return None
    safe = redact(str(value), manager, encoded=True)
    return ''.join(c if ord(c) >= 32 and ord(c) != 127 else ' ' for c in safe)[:limit]


def problem_report(diagnostics, manager=None, *, invalid=False):
    """No raw spec values in messages. Locations are redacted before capping."""
    problems = []
    total = len(diagnostics)

    def body():
        omitted = total - len(problems)
        title = 'Workflow spec did not pass.' if invalid else 'Workflow spec checked.'
        rows = [' · '.join(str(p[k] or '—') for k in ('node', 'field', 'message')) for p in problems]
        message = title + ('\n' + '\n'.join(rows) if rows else '')
        if omitted:
            message += f'\n{omitted} more problem(s) omitted.'
        details = dict(problems=problems, omitted_count=omitted)
        return message, details

    for diagnostic in diagnostics[:PROBLEM_LIMIT]:
        code = str(diagnostic.get('code') or 'validation')
        # Core CLI messages can quote arbitrary config values. Preserve verdict,
        # structured location and code; render safe guidance for node persistence.
        message = SAFE_MESSAGES.get(code, 'Check this node’s configuration: ' + code.replace('_', ' ') + '.')
        row = dict(node=_safe(diagnostic.get('node'), manager, 80),
                   field=_safe(diagnostic.get('field'), manager, 200),
                   code=_safe(code, manager, 80), severity=diagnostic.get('level', 'error'),
                   message=_safe(message, manager, 500))
        problems.append(row)
        rendered, details = body()
        encoded = json.dumps(dict(message=rendered, details=details), ensure_ascii=False)
        if len(encoded) > PROBLEM_CHARS - 128 or len(encoded.encode('utf-8')) > 32000:
            problems.pop()
            break
    return body()


async def check(factory, text, limit, manager=None, *, fail_on_unreachable=False, fail_on_disabled_output=False):
    if type(fail_on_unreachable) is not bool:
        raise NodeError('invalid_config', 'Choose a boolean fail_on_unreachable option.')
    if type(fail_on_disabled_output) is not bool:
        raise NodeError('invalid_config', 'Choose a boolean fail_on_disabled_output option.')
    if type(limit) is not int or not 1 <= limit <= 64000:
        raise NodeError('invalid_config', 'Choose a spec size limit from 1 to 64,000 characters.')
    if not isinstance(text, str):
        raise NodeError('invalid_json', 'Provide the Spec as JSON text.')
    if len(text) > limit:
        raise NodeError('spec_too_large', 'Spec exceeds its character limit.')
    try:
        if len(text.encode('utf-8')) > MAX_BYTES:
            raise NodeError('spec_too_large', 'Spec exceeds its byte limit.')
        _depth(text)
        duplicates = []
        parsed = _objects(json.loads(text, parse_constant=_nonfinite, object_pairs_hook=_Pairs),
                          '', duplicates)
        _json_value(parsed)
    except (ValueError, UnicodeError, RecursionError):
        raise NodeError('invalid_json', 'Spec is not valid JSON text.') from None
    if duplicates:
        # A repeated key would silently keep only its last value; never approve that draft.
        message, details = problem_report(_duplicate_diagnostics(duplicates), manager, invalid=True)
        raise NodeError('invalid_json', message, details=details)
    if isinstance(parsed, dict):
        if isinstance(parsed.get('nodes'), dict) and len(parsed['nodes']) > MAX_NODES:
            raise NodeError('spec_too_large', 'Spec has more than 128 nodes.')
        if isinstance(parsed.get('connections'), list) and len(parsed['connections']) > MAX_CONNECTIONS:
            raise NodeError('spec_too_large', 'Spec has more than 256 connections.')
    await asyncio.sleep(0)
    checked = authoring.check_workflow_spec(factory, parsed)
    await asyncio.sleep(0)  # Stop must win before any publication.
    rejected_codes = set()
    if fail_on_unreachable:
        rejected_codes.add('unreachable')
    if fail_on_disabled_output:
        rejected_codes.add('disabled_output_connection')
    rejected = not checked['ok'] or any(d.get('code') in rejected_codes for d in checked['diagnostics'])
    message, details = problem_report(checked['diagnostics'], manager, invalid=rejected)
    if rejected:
        raise NodeError('spec_invalid', message, details=details)
    return parsed, dict(schema_version=1, ok=True, node_count=len(parsed['nodes']),
                        connection_count=len(parsed.get('connections', [])),
                        warning_count=sum(d['level'] == 'warning' for d in checked['diagnostics']),
                        **details)
