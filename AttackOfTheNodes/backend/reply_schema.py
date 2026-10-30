"""Closed JSON reply schemas: bounded local validation and API-safe projection.

No reference retrieval. Only local, acyclic JSON-pointer references are allowed.
Length/range/pattern/array constraints remain in the Check reply schema, even
when the API grammar cannot express them. No constraint is silently discarded
from the local check.
"""
from copy import deepcopy
from functools import lru_cache
import json

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from .node_errors import NodeError

MAX_SCHEMA_CHARS = 16000
MAX_DEPTH = 24
LOCAL_CONSTRAINTS = {'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
                     'multipleOf', 'minLength', 'maxLength', 'pattern', 'maxItems', 'uniqueItems'}
KEYWORDS = {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum', 'const',
            'anyOf', 'allOf', '$ref', '$defs', 'definitions', '$schema',
            'title', 'description', 'default', 'minItems', 'format'} | LOCAL_CONSTRAINTS
API_FORMATS = {'date-time', 'time', 'date', 'duration', 'email', 'hostname', 'uri', 'ipv4', 'ipv6', 'uuid'}


def invalid(message):
    return NodeError('shape_invalid', 'Reply schema: ' + message)


def _json(raw):
    from .reply_shape import pairs
    def constant(_):
        raise ValueError('non-finite')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def load(value):
    """None/blank disables this opt-in; a configured schema must be an object."""
    if value is None or isinstance(value, str) and not value.strip():
        return None
    try:
        encoded = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, allow_nan=False)
        if len(encoded) > MAX_SCHEMA_CHARS or len(encoded.encode()) > 64000:
            raise invalid('exceeds 16,000 characters or 64,000 UTF-8 bytes.')
        return deepcopy(_compiled(encoded)[0])
    except (ValueError, UnicodeError, RecursionError, TypeError):
        raise invalid('provide one valid JSON Schema object.') from None


@lru_cache(maxsize=64)
def _compiled(encoded):
    root = _json(encoded)
    if not isinstance(root, dict) or root.get('type') != 'object':
        raise invalid('root type must be object.')
    count = 0
    def visit(schema, trail=(), depth=0):
        nonlocal count
        count += 1
        if count > 1024 or depth > MAX_DEPTH or not isinstance(schema, dict):
            raise invalid('use a bounded, non-recursive object schema.')
        if set(schema) - KEYWORDS:
            raise invalid('unsupported keyword: ' + sorted(set(schema) - KEYWORDS)[0])
        if '$schema' in schema and schema['$schema'] != 'https://json-schema.org/draft/2020-12/schema':
            raise invalid('only Draft 2020-12 schemas are supported.')
        if '$ref' in schema:
            ref = schema['$ref']
            if not isinstance(ref, str) or not ref.startswith('#/') or ref in trail:
                raise invalid('references must be local and non-recursive.')
            target = root
            try:
                for part in ref[2:].split('/'):
                    target = target[part.replace('~1', '/').replace('~0', '~')]
            except (KeyError, TypeError):
                raise invalid('reference target is missing.') from None
            # Ref siblings have intersection semantics; keep them with allOf.
            resolved = visit(target, trail + (ref,), depth + 1)
            siblings = {k: v for k, v in schema.items() if k != '$ref'}
            return dict(allOf=[resolved, visit(siblings, trail, depth + 1)]) if siblings else resolved
        result = deepcopy(schema)
        result.pop('$schema', None)
        for definitions in ('$defs', 'definitions'):
            for child in (schema.get(definitions) or {}).values():
                visit(child, trail, depth + 1)
            result.pop(definitions, None)  # Local refs are expanded before sending.
        kind = schema.get('type')
        if kind == 'object' or 'properties' in schema or isinstance(kind, list) and 'object' in kind:
            if schema.get('additionalProperties', False) is not False:
                raise invalid('every object must have additionalProperties: false.')
            result['additionalProperties'] = False
            result['properties'] = {k: visit(v, trail, depth + 1) for k, v in (schema.get('properties') or {}).items()}
        if kind == 'array' or isinstance(kind, list) and 'array' in kind:
            if 'items' not in schema:
                raise invalid('arrays need an explicit items schema.')
            result['items'] = visit(schema['items'], trail, depth + 1)
        for combinator in ('anyOf', 'allOf'):
            if combinator in schema:
                result[combinator] = [visit(v, trail, depth + 1) for v in schema[combinator]]
        if 'enum' in schema and any(isinstance(v, (list, dict)) for v in schema['enum']):
            raise invalid('enum values must be scalar.')
        if 'const' in schema and isinstance(schema['const'], (list, dict)):
            raise invalid('const values must be scalar.')
        if 'format' in schema and schema['format'] not in FormatChecker.checkers:
            raise invalid('format is not available for local checking.')
        return result
    try:
        Draft202012Validator.check_schema(root)
        normalized = visit(root)
        Draft202012Validator.check_schema(normalized)
    except (SchemaError, ValueError, TypeError, AttributeError):
        raise invalid('schema is malformed.') from None
    return normalized, Draft202012Validator(normalized, format_checker=FormatChecker())


def provider_schema(value):
    """API-compatible projection; original bounds remain in Check reply."""
    schema = load(value)
    if schema is None:
        return None
    def project(node):
        result = deepcopy(node)
        removed = {k: result.pop(k) for k in LOCAL_CONSTRAINTS if k in result}
        if result.get('minItems', 0) not in (0, 1):
            removed['minItems'] = result.pop('minItems')
        if 'format' in result and result['format'] not in API_FORMATS:
            removed['format'] = result.pop('format')
        if removed:
            result['description'] = (str(result.get('description', '')) + ' Checked afterwards: ' + json.dumps(removed, separators=(',', ':'))).strip()
        for key in ('properties',):
            if key in result:
                result[key] = {k: project(v) for k, v in result[key].items()}
        if 'items' in result:
            result['items'] = project(result['items'])
        for key in ('anyOf', 'allOf'):
            if key in result:
                result[key] = [project(v) for v in result[key]]
        return result
    return project(schema)


def check(value, schema):
    normalized = load(schema)
    if normalized is None:
        return
    encoded = json.dumps(normalized, ensure_ascii=False, allow_nan=False)
    validator = _compiled(encoded)[1]
    error = next(validator.iter_errors(value), None)
    if error is not None:
        # Values and arbitrary schema labels may contain credentials. Preserve
        # a bounded machine location and rule only, never the exception body.
        raise NodeError('reply_mismatch', "Reply didn't match its schema (" + error.validator + ').')
