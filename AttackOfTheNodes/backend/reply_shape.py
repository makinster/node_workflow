"""Strict, bounded JSON shape checks; no inference or repair."""
import asyncio
import json
import math
import re

from .node_errors import NodeError

TYPES = {'string': 'Text', 'number': 'Number', 'boolean': 'Yes or no',
         'list': 'List', 'object': 'Record', 'null': 'Empty'}
NAME_PATTERN = r'[A-Za-z_][A-Za-z0-9_-]{0,63}'
HINT = 'Checks that a reply has the fields below. If not, it takes the error path.'


def field_problem(rows):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 32:
        return 'Use 1 to 32 fields.'
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            return 'Check the expected fields.'
        name = row.get('name')
        if not isinstance(name, str) or not re.fullmatch(NAME_PATTERN, name):
            return 'Use a short field name: letters, numbers, _ or -.'
        if name in seen:
            return 'Use a different name for each field.'
        seen.add(name)
        if not isinstance(row.get('kind'), str) or row['kind'] not in TYPES or type(row.get('required')) is not bool:
            return 'Choose a type and whether the field is required.'
    return ''


def mismatch():
    return NodeError('reply_mismatch', "Reply didn't match.")


def pairs(items):
    record = {}
    for key, value in items:
        if key in record:
            raise ValueError('duplicate key')
        record[key] = value
    return record


def check_record(result, rows, extra=False):
    """Shared decoded-record shape gate; nested protocol rules belong to clients."""
    problem = field_problem(rows)
    if problem:
        raise NodeError('shape_invalid', problem)
    if not isinstance(result, dict):
        raise mismatch()
    expected = {row['name'] for row in rows}
    if not extra and set(result) - expected:
        raise mismatch()
    for row in rows:
        name, kind = row['name'], row['kind']
        if name not in result:
            if row['required']:
                raise mismatch()
            continue
        value = result[name]
        valid = {'string': type(value) is str, 'number': type(value) in (int, float),
                 'boolean': type(value) is bool, 'list': type(value) is list,
                 'object': type(value) is dict, 'null': value is None}[kind]
        if not valid:
            raise mismatch()
    return result


async def check(text, rows, limit=16000, extra=False):
    problem = field_problem(rows)
    if problem:
        raise NodeError('shape_invalid', problem)
    if (type(limit) is not int or not 1 <= limit <= 64000 or
            not isinstance(text, str) or len(text) > limit):
        raise mismatch()
    try:
        if len(text.encode('utf-8')) > 256000:
            raise mismatch()
        # Bound nesting *before* json.loads; braces inside strings don't count.
        depth, quoted, escape = 0, False, False
        for index, char in enumerate(text):
            if index % 4096 == 0:
                await asyncio.sleep(0)
            if quoted:
                if escape:
                    escape = False
                elif char == '\\':
                    escape = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in '[{':
                depth += 1
                if depth > 8:
                    raise mismatch()
            elif char in ']}':
                depth -= 1
        def constant(_):
            raise ValueError('not finite')
        result = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
        def valid_decoded(value):
            if isinstance(value, str):
                value.encode('utf-8')  # Escaped lone surrogates survive json.loads.
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError('not finite')
            if isinstance(value, dict):
                for key, item in value.items():
                    key.encode('utf-8')
                    valid_decoded(item)
            elif isinstance(value, list):
                for item in value:
                    valid_decoded(item)
        valid_decoded(result)
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise mismatch() from None
    check_record(result, rows, extra)
    await asyncio.sleep(0)
    return result
