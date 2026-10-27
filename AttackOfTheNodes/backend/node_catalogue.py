"""Bounded authoring contracts from the live registry; no node execution."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json

from .authoring import HIDDEN_TYPES, describe_node_type, list_node_types
from .node_errors import NodeError
from .port_types import port_metadata, resolved_metadata

MAX_BYTES = 256 * 1024
SOURCE_IDS = {'Upstream payload': 'upstream', 'Vault': 'vault', 'Configured': 'configured'}
COMPACT_KEYS = ('type', 'required', 'options', 'min', 'max', 'secret', 'path_hint')
DETAILS = ('Brief', 'Compact', 'Detailed')


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def is_debug(meta):
    """The selector's Debug section is a group to users; legacy classes agree."""
    return (str(meta.get('group') or '').casefold() == 'debug'
            or str(meta.get('selector_section') or '').casefold() == 'debug')


def _field(info):
    result = {k: deepcopy(info[k]) for k in COMPACT_KEYS if k in info and info[k] is not False}
    if 'options' in result:
        result['options'] = [o[1] if isinstance(o, (list, tuple)) and len(o) == 2 else o for o in result['options']]
    if isinstance(info.get('item_schema'), dict):
        result['item_schema'] = {k: _field(v) for k, v in info['item_schema'].items()}
    return result


def brief_entry(factory, row):
    """Shortlist row: names and one-liners only, no types, sources or config."""
    description = describe_node_type(factory, row['type'])
    return dict(entry_kind='node', type=row['type'], display_name=row['name'],
                description=' '.join(row['description'].splitlines()),
                inputs=[p['name'] for p in description['inputs']],
                outputs=[p['name'] for p in description['outputs']])


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
                  config_fields={k: _field(v) for k, v in schema.items()},
                  errors=[e['code'] for e in description['errors']])
    if description['custom_keys']:
        result['custom_keys'] = list(description['custom_keys'])
    if description['node_reference_fields']:
        result['node_reference_fields'] = description['node_reference_fields']
    if detail == 'Detailed':
        result.update(config_fields=deepcopy(schema), defaults=deepcopy(config),
                      errors=description['errors'], custom_keys=description['custom_keys'],
                      unchecked_keys=description['unchecked_keys'],
                      standard_keys=description['standard_keys'],
                      vault_reads=description['vault_reads'], vault_writes=description['vault_writes'],
                      ui_hints=deepcopy(meta.get('ui_hints') or {}))
    return result


def brief_text(record):
    lines = ['Node catalogue v1 · Brief: type | name | purpose | in -> out',
             'For shortlisting. Ask again with Detailed, filtered to the chosen types, before drafting.', '']
    for item in record['entries']:
        lines.append(f"{item['type']} | {item['display_name']} | {item['description']} | "
                     f"{', '.join(item['inputs']) or '-'} -> {', '.join(item['outputs']) or '-'}")
    return '\n'.join(lines) + '\n'


def text_output(record):
    if record['detail'] == 'Brief':
        return brief_text(record)
    lines = ['Node catalogue v1 · ports resolved with defaults',
             'Complete matching entries. Compact fields omit defaults/full constraints; use Detailed.', '']
    for item in record['entries']:
        lines.extend([f"{item['entry_kind']} {item['type']} | {item['display_name']} | {item['group'] or 'Ungrouped'}",
                      item['description'],
                      'Family: ' + item['family'] + ' · Tags: ' + ', '.join(item['tags']),
                      'In: ' + ('; '.join(f"{p['id']}/{p['name']} [{p['data_type']}] {'required' if p['required'] else 'optional'} ({'/'.join(p['sources'])})" for p in item['inputs']) or 'none'),
                      'Out: ' + '; '.join(f"{p['id']}/{p['name']} [{p['data_type']}] {'required' if p['required'] else 'optional'} ({'/'.join(p['to'])})" for p in item['outputs']),
                      'Config: ' + compact_json(item['config_fields']),
                      'Errors: ' + compact_json(item['errors'])])
        for key in ('custom_keys', 'node_reference_fields', 'defaults', 'unchecked_keys',
                    'standard_keys', 'vault_reads', 'vault_writes', 'ui_hints'):
            if key in item:
                lines.append(key + ': ' + compact_json(item[key]))
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def validate_config(config):
    if (config.get('scope') not in ('All nodes', 'Filtered')
            or config.get('detail') not in DETAILS
            or config.get('format') not in ('Text', 'JSON')
            or type(config.get('include_debug')) is not bool
            or type(config.get('max_chars')) is not int
            or not 512 <= config['max_chars'] <= 64000
            or any(not isinstance(config.get(k), str) or len(config[k]) > 256
                   for k in ('group_filter', 'tag_filter', 'search'))):
        raise NodeError('invalid_config', 'Check catalogue filters, format and size limit.')


async def build(factory, config):
    validate_config(config)
    entries = []
    for row in list_node_types(factory):
        meta = factory.metadata_for_type(row['type'])
        if row['type'] in HIDDEN_TYPES or meta.get('editor_only'):
            continue
        if is_debug(meta) and not config['include_debug']:
            continue
        if config['scope'] == 'Filtered':
            group, tag = config['group_filter'], config['tag_filter']
            if group and group != 'Any group' and row['group'] != group:
                continue
            if tag and tag.casefold() not in [t.casefold() for t in meta.get('tags') or []]:
                continue
            haystack = ' '.join([row['type'], row['name'], row['description'], *(meta.get('tags') or [])]).casefold()
            if not all(word in haystack for word in config['search'].casefold().split()):
                continue
        await asyncio.sleep(0)
        entries.append(entry(factory, row, config['detail']))
    if not entries:
        raise NodeError('catalogue_empty', 'No nodes match. Broaden the filters.')
    record = dict(schema_version=1, ports_basis='defaults', detail=config['detail'],
                  include_debug=config['include_debug'], matched_count=len(entries),
                  complete=True, entries=entries)
    value = record if config['format'] == 'JSON' else text_output(record)
    serialized = compact_json(record) if config['format'] == 'JSON' else value
    if len(serialized) > config['max_chars'] or len(serialized.encode('utf-8')) > MAX_BYTES:
        raise NodeError('catalogue_too_large', 'Catalogue is too large. Narrow the filters or raise the cap.',
                        details=dict(characters=len(serialized), limit=config['max_chars'], matched_count=len(entries)))
    await asyncio.sleep(0)
    return value
