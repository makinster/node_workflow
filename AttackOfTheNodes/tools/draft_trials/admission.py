"""Versioned admission for frozen trials; uses the shared catalogue boundary."""
import re
from backend.palette_selection import ADMITTED, ORIGINAL_PALETTE, ORIGINAL_ROLE_IDS, ROLE_TYPES
from .reply_schemas import install
BASELINE_ROLES = ORIGINAL_ROLE_IDS

def configure(spec, admitted=ADMITTED):
    admitted = frozenset(admitted)
    if not admitted or admitted - ADMITTED:
        raise ValueError('invalid trial admission')
    roles = sorted(BASELINE_ROLES if admitted == ORIGINAL_PALETTE else ROLE_TYPES)
    for handle in ('analysis_question', 'resolve_question', 'draft_question', 'retry_question'):
        if handle not in spec['nodes']:
            continue
        config = spec['nodes'][handle]['config']
        value = config['template']
        value = re.sub('Palette: [^.]+\\.', 'Palette: ' + ', '.join(sorted(admitted)) + '.', value)
        value = re.sub('Allowed role IDs: [^.]+\\.', 'Allowed role IDs: ' + ', '.join(roles) + '.', value)
        value = value.replace('in the admitted twelve', 'in the admitted palette')
        value = re.sub('approved \\d+-type palette: [^.]+\\.', 'approved ' + str(len(admitted)) + '-type palette: ' + ', '.join(sorted(admitted)) + '.', value)
        value = re.sub('Allowed types: [^.]+\\.', 'Allowed types: ' + ', '.join(sorted(admitted)) + '.', value)
        config['template'] = value
    for node in spec['nodes'].values():
        if node['type'] == 'node_catalogue_node' and node['config'].get('scope') in ('Exact IDs', 'Selected analysis'):
            node['config']['admitted_type_ids'] = sorted(admitted)
            if node['config'].get('detail') == 'Brief':
                node['config']['type_ids'] = sorted(admitted)
    install(spec, admitted)
    if admitted == ORIGINAL_PALETTE:
        for gate in ('analysis', 'resolve', 'analysis_shape', 'resolved_shape'):
            schema = spec['nodes'][gate]['config']['reply_schema']
            sel = schema['properties']['selection']['properties']
            for key in ('candidates', 'roles'):
                sel[key]['items']['properties']['role']['enum'] = roles
    return spec
