"""Versioned admission for frozen trials; uses the shared catalogue boundary."""
import re
from backend.palette_selection import ADMITTED, HELPER_PALETTE, ORIGINAL_PALETTE, ORIGINAL_ROLE_IDS, ROLE_TYPES, STAGE_ONE
from .reply_schemas import install
BASELINE_ROLES = ORIGINAL_ROLE_IDS
# What each suite's drafter may use. Earlier suites keep their exact boundary.
SUITE_SCOPE = {1: ORIGINAL_PALETTE, 2: ORIGINAL_PALETTE, 3: HELPER_PALETTE, 4: ADMITTED}
# Stored verbatim in the v2 spec; frozen suites never see words about Merge.
JOIN_ANALYSIS = (' When parallel paths must all finish before one later step uses their results together, '
                 'declare both parallel_paths and join; join adds Merge, which collects them. '
                 'A shared End only finishes paths; it never waits for or combines them.')
JOIN_DRAFT = (' To use parallel results together: one branch_node, each path wired to its own merge_node input '
              '(reader_a.default to join.path_a, reader_b.default to join.path_b), then join.default to the next step. '
              'Merge passes on one record keyed by input name, so that step reads {{input[path_a]}} and {{input[path_b]}}. '
              'Drafts allow one split and one Merge: no split inside a path, no two paths into one Merge input, '
              'no Merge without a split, no path ending before the Merge. '
              'A shared End only finishes each path; it never waits for or combines them.')


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
        if not STAGE_ONE <= admitted:
            value = value.replace(JOIN_ANALYSIS, '').replace(JOIN_DRAFT, '')
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
