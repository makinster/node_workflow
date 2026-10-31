"""Bounded authoring contracts from the live registry; no node execution."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json

from .authoring import HIDDEN_TYPES, INPUT_ARRIVAL_NOTE, describe_node_type, list_node_types
from .node_errors import NodeError
from .node_metadata import (
    COST_PHRASES, RECORD_SCHEMA_VERSION, effects_text, needs_text, note_lines, selection,
)
from .port_types import port_metadata, resolved_metadata
from .flow_behaviors import flow_provenance, flow_brief

#: Catalogue schema 2 carries node metadata record v1; each versions separately.
SCHEMA_VERSION = 2
MAX_BYTES = 256 * 1024
MAX_CHARS_LIMIT = 200_000
PENDING_LINE = 'Unreviewed: effects/needs unknown; not Read-only.'
SOURCE_IDS = {'Upstream payload': 'upstream', 'Vault': 'vault', 'Configured': 'configured'}
COMPACT_KEYS = ('type', 'required', 'options', 'min', 'max', 'secret', 'path_hint')
DETAILS = ('Brief', 'Compact', 'Detailed')
_MISSING = object()


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def is_debug(meta):
    """The selector's Debug section is a group to users; legacy classes agree."""
    return (str(meta.get('group') or '').casefold() == 'debug'
            or str(meta.get('selector_section') or '').casefold() == 'debug')


def _field(info, default=_MISSING):
    result = {k: deepcopy(info[k]) for k in COMPACT_KEYS if k in info and info[k] is not False}
    if default is not _MISSING:
        result['default'] = deepcopy(default)
        result.pop('required', None)
    if 'options' in result:
        result['options'] = [o[1] if isinstance(o, (list, tuple)) and len(o) == 2 else o for o in result['options']]
    if isinstance(info.get('item_schema'), dict):
        result['item_schema'] = {k: _field(v) for k, v in info['item_schema'].items()}
    return result


def brief_entry(factory, row):
    """Shortlist row: purpose-first selection facts; no types, sources or config.

    The old fields keep their meaning (description is the purpose alias);
    node_metadata is the selection projection, or None while pending review.
    """
    description = describe_node_type(factory, row['type'])
    record = factory.metadata_for_type(row['type']).get('node_metadata')
    result = dict(entry_kind='node', type=row['type'], display_name=row['name'],
                description=' '.join(row['description'].splitlines()),
                inputs=[p['name'] for p in description['inputs']],
                outputs=[p['name'] for p in description['outputs']],
                node_metadata=selection(record) if record else None)
    if record and record.get("flow_behavior"):
        result["flow_summary"] = flow_brief(record["flow_behavior"])
    return result


def entry(factory, row, detail):
    """Ports have stable ids/names: future Bundle contract rows can use the same shape."""
    kind = row['type']
    if detail == 'Brief':
        return brief_entry(factory, row)
    meta = factory.metadata_for_type(kind)
    description = describe_node_type(factory, kind)
    config = description['config']
    node = dict(type=kind, config=config)
    schema = meta.get('config_schema') or {}
    inputs = []
    for port in description['inputs']:
        info = port_metadata(factory, node, port['port'], 'input')
        sources = info.get('sources')
        if sources is None:
            sources = [SOURCE_IDS[s] for s in port['source_options'] if s in SOURCE_IDS] or ['upstream']
        item = dict(id=port['port'], name=port['name'], data_type=port['data_type'],
                    required=port['required'], sources=list(sources))
        if port['source_field']:
            item['source_field'] = port['source_field']
        if 'configured' in sources:
            item['configured_field'] = info.get('configured_field', port['port'])
        inputs.append(item)
    resolved = resolved_metadata(factory, kind, config)
    outputs = []
    for port in description['outputs']:
        info = (resolved.get('output_port_metadata') or {}).get(port['port']) or {}
        item = dict(id=port['port'], name=port['name'], data_type=port['data_type'],
                    required=bool(info.get('required')), to=list(info.get('to') or ['downstream']))
        if port['port'] == 'error':
            item.update(to=['error'], required=False)
        if info.get('pass_through'):
            item['forward_input_optional'] = True
        outputs.append(item)
    result = dict(entry_kind='node', type=kind, display_name=row['name'],
                  description=' '.join(row['description'].splitlines()),
                  family=row['family'], group=row['group'] or None,
                  tags=list(meta.get('tags') or []), inputs=inputs, outputs=outputs,
                  config_fields={k: _field(v, config[k]) if k in config else _field(v)
                                 for k, v in schema.items()},
                  errors=[e['code'] for e in description['errors']])
    if description['custom_keys']:
        result['custom_keys'] = list(description['custom_keys'])
    if description['node_reference_fields']:
        result['node_reference_fields'] = description['node_reference_fields']
    # The full record carries execution_contract once; never a second copy.
    result['node_metadata'] = deepcopy(meta.get('node_metadata'))
    if meta.get('standard_key_docs'):
        result['standard_key_docs'] = deepcopy(meta['standard_key_docs'])
    configured = {
        p['id']: f"{p['source_field']}=Configured: use {p['configured_field']}; {p['id']} trigger only; no type check."
        for p in inputs if 'configured_field' in p and p.get('source_field')
    }
    if configured:
        result['configured_inputs'] = configured
    if detail == 'Detailed':
        result.update(config_fields=deepcopy(schema), defaults=deepcopy(config),
                      errors=description['errors'], custom_keys=description['custom_keys'],
                      unchecked_keys=description['unchecked_keys'],
                      standard_keys=description['standard_keys'],
                      vault_reads=description['vault_reads'], vault_writes=description['vault_writes'],
                      ui_hints=deepcopy(meta.get('ui_hints') or {}))
    return result


PORT_LEGEND = 'Connections use port ids only; quoted names are labels.'
LOOKALIKE_LEGEND = 'Use instead links name alternatives; they do not grant admission.'


def port_label(port, *, brief=False):
    name = compact_json(port['name'])
    return f"{port['id']} {name}" if brief else f"{port['id']} ({name})"


def config_text(fields):
    """Lossless short Text notation; JSON keeps its structured field records."""
    rows = []
    for name, info in fields.items():
        rest = {k: v for k, v in info.items() if k not in ('type', 'default')}
        row = name + ':' + str(info.get('type', 'any'))
        if 'default' in info:
            row += '=' + compact_json(info['default'])
        if rest:
            row += ' ' + compact_json(rest)
        rows.append(row)
    return ';'.join(rows)


def header(record):
    return (f"Node catalogue v{record['schema_version']} · node record v{record['node_metadata_version']}"
            f" · {record['detail']} ({record['metadata_projection']})")


def intent_lines(meta, *, notes):
    """Choosing facts; Compact/Detailed add the explanatory notes for wiring."""
    if meta is None:
        return [PENDING_LINE]
    lines = [f"Use when: {meta['use_when']}"] if 'use_when' in meta else []
    if 'not_for' in meta:
        lines.append(f"Not for: {meta['not_for']}")
    for link in meta.get('use_instead', []):
        from .palette_selection import ADMITTED
        status = ' (not admitted)' if link['node_type'] not in ADMITTED else ''
        lines.append(f"Use instead: {link['when']}: {link['node_type']}{status}.")
    lines.append(f"Effects: {effects_text(meta)}. Needs: {needs_text(meta)}.")
    if 'cost_class' in meta:
        lines.append(f"Cost: {COST_PHRASES[meta['cost_class']]}. Time: {meta['time_class']}.")
    return lines + (note_lines(meta) if notes else [])


def brief_text(record, factory):
    lines = [header(record) + ': type|name|purpose|in -> out, then choosing facts',
             PORT_LEGEND, LOOKALIKE_LEGEND, '']
    family = None
    for item in sorted(record['entries'], key=lambda e: (factory.metadata_for_type(e['type']).get('primary_family', ''), e['type'])):
        item_family = factory.metadata_for_type(item['type']).get('primary_family', '')
        if item_family != family:
            family = item_family
            lines.append('Family: ' + (family or 'Ungrouped'))
        # Brief JSON deliberately retains its original names-only arrays.
        # Resolve ids only for Text; never add/change JSON contract fields.
        description = describe_node_type(factory, item['type'])
        def ports(direction):
            return ', '.join(port_label(dict(id=p['port'], name=p['name']), brief=True)
                             for p in description[direction]) or '-'
        lines.append(f"{item['type']}|{item['display_name']}|{item['description']}|"
                     f"{ports('inputs')} -> {ports('outputs')}")
        lines.extend('  ' + line for line in intent_lines(item['node_metadata'], notes=False))
        if item.get('flow_summary'): lines.append('  Flow: ' + item['flow_summary'])
    return '\n'.join(lines) + '\n'


def text_output(record, factory):
    if record['detail'] == 'Brief':
        return brief_text(record, factory)
    lines = [header(record) + (': default ports; field:type=default; required=no default.'
                               if record['detail'] == 'Compact' else ': default ports; full schema and defaults.'),
             PORT_LEGEND, LOOKALIKE_LEGEND, record['input_routing'], 'All nodes may raise node_error.', '']
    for item in record['entries']:
        lines.extend([f"{item['entry_kind']} {item['type']} | {item['display_name']} | {item['group'] or 'Ungrouped'}",
                      item['description'], *intent_lines(item['node_metadata'], notes=True),
                      'Family: ' + item['family'] + ' · Tags: ' + ', '.join(item['tags']),
                      'In: ' + ('; '.join(f"{port_label(p)} [{p['data_type']}] {'required' if p['required'] else 'optional'} ({'/'.join(p['sources'])})" for p in item['inputs']) or 'none'),
                      'Out: ' + '; '.join(f"{port_label(p)} [{p['data_type']}] {'required' if p['required'] else 'optional'} ({'/'.join(p['to'])})" for p in item['outputs']),
                      'Config: ' + (config_text(item['config_fields']) if record['detail'] == 'Compact'
                                                  else compact_json(item['config_fields'])),
                      *(['Errors: ' + compact_json([e for e in item['errors'] if e != 'node_error'])]
                        if record['detail'] != 'Compact' or any(e != 'node_error' for e in item['errors']) else [])])
        if (item['node_metadata'] or {}).get('flow_behavior'):
            lines.append('Flow: ' + compact_json(item['node_metadata']['flow_behavior']))
        for key, value in ((item['node_metadata'] or {}).get('execution_contract') or {}).items():
            lines.append(('Output payload: ' if key == 'output_payload' else 'Behavior: ') + value)
        for key, value in item.get('standard_key_docs', {}).items():
            lines.append('Standard config: ' + key + ': ' + value)
        if item.get('configured_inputs'):
            lines.append('Configured: ' + ' '.join(item['configured_inputs'].values()))
        for key in ('custom_keys', 'node_reference_fields', 'defaults', 'unchecked_keys',
                    'standard_keys', 'vault_reads', 'vault_writes', 'ui_hints'):
            if key in item:
                lines.append(key + ': ' + compact_json(item[key]))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def validate_config(config):
    if (config.get('scope') not in ('All nodes', 'Filtered', 'Exact IDs')
            or config.get('detail') not in DETAILS
            or config.get('format') not in ('Text', 'JSON')
            or type(config.get('include_debug')) is not bool
            or type(config.get('max_chars')) is not int
            or not 512 <= config['max_chars'] <= MAX_CHARS_LIMIT
            or any(not isinstance(config.get(k), str) or len(config[k]) > 256
                   for k in ('group_filter', 'tag_filter', 'search'))):
        raise NodeError('invalid_config', 'Check catalogue filters, format and size limit.')


async def build(factory, config):
    validate_config(config)
    entries = []
    selected = None
    if config['scope'] == 'Exact IDs':
        from .palette_selection import exact_ids, admission
        selected = exact_ids(factory, config.get('type_ids'), allowed=admission(config))
    for row in sorted(list_node_types(factory), key=lambda r: r['type']) if selected else list_node_types(factory):
        if selected is not None and row['type'] not in selected:
            continue
        meta = factory.metadata_for_type(row['type'])
        # include_debug does not reach dev/test-only types; they are never drafted.
        if row['type'] in HIDDEN_TYPES or meta.get('editor_only') or meta.get('dev_test_only'):
            continue
        if selected is None and is_debug(meta) and not config['include_debug']:
            continue
        if config['scope'] == 'Filtered':
            group, tag = config['group_filter'], config['tag_filter']
            if group and group != 'Any group' and row['group'] != group:
                continue
            if tag and tag.casefold() not in [t.casefold() for t in meta.get('tags') or []]:
                continue
            # Positive intent only: not_for names wrong uses and never matches.
            use_when = (meta.get('node_metadata') or {}).get('use_when', '')
            haystack = ' '.join([row['type'], row['name'], row['description'], use_when,
                                 *(meta.get('tags') or [])]).casefold()
            if not all(word in haystack for word in config['search'].casefold().split()):
                continue
        await asyncio.sleep(0)
        entries.append(entry(factory, row, config['detail']))
    if selected is not None and [e['type'] for e in entries] != selected:
        raise NodeError('selection_invalid', 'Selected catalogue IDs are unavailable or duplicated; no partial contracts returned.')
    if not entries:
        raise NodeError('catalogue_empty', 'No nodes match. Broaden the filters.')
    record = dict(schema_version=SCHEMA_VERSION, node_metadata_version=RECORD_SCHEMA_VERSION,
                  metadata_projection='selection' if config['detail'] == 'Brief' else 'full',
                  ports_basis='defaults', detail=config['detail'],
                  include_debug=config['include_debug'], matched_count=len(entries),
                  complete=True, entries=entries, flow_provenance=flow_provenance())
    if selected is not None:
        record['selected_type_ids'] = selected
    if config['detail'] != 'Brief':
        record['input_routing'] = INPUT_ARRIVAL_NOTE
    value = record if config['format'] == 'JSON' else text_output(record, factory)
    if config['format'] == 'Text':
        value += 'Flow provenance: ' + compact_json(record['flow_provenance']) + '\n'
    serialized = compact_json(record) if config['format'] == 'JSON' else value
    characters, size = len(serialized), len(serialized.encode('utf-8'))
    if characters > config['max_chars'] or size > MAX_BYTES:
        raise NodeError('catalogue_too_large', 'Catalogue is too large. Narrow the filters or raise the cap.',
                        details=dict(characters=characters, limit=config['max_chars'], bytes=size,
                                     byte_limit=MAX_BYTES, matched_count=len(entries),
                                     failed='characters' if characters > config['max_chars'] else 'bytes'))
    await asyncio.sleep(0)
    return value
