"""Versioned admission for frozen trials; uses the shared catalogue boundary."""
import re
from backend.palette_selection import ADMITTED, HELPER_PALETTE, ORIGINAL_PALETTE, ORIGINAL_ROLE_IDS, STAGE_ONE, role_ids
from .reply_schemas import install
BASELINE_ROLES = ORIGINAL_ROLE_IDS
# What each suite's drafter may use. Earlier suites keep their exact boundary.
SUITE_SCOPE = {1: ORIGINAL_PALETTE, 2: ORIGINAL_PALETTE, 3: HELPER_PALETTE, 4: ADMITTED}
# Stored verbatim in the v2 spec; frozen suites never see words about Merge or Wait Until.
JOIN_ANALYSIS = (' When parallel paths must all finish before one later step uses their results together, '
                 'declare both parallel_paths and join; join adds Merge, which collects them. '
                 'A path that splits again, and either-or results, still use that one join. '
                 'When one path must hold until a step on another path has finished, also declare wait_for_step; it adds Wait Until. '
                 'Merge carries the results forward and joined paths finish once, so do not require a Vault slot or a separate End or completion record for each path unless the request asks for one. '
                 'A shared End only finishes paths; it never waits for or combines them.')
JOIN_DRAFT = (' To use parallel results together: one branch_node, each path wired to its own merge_node input '
              '(reader_a.default to join.path_a, reader_b.default to join.path_b), then join.default to the next step. '
              'For more than two paths set branch_count on the branch_node: 3 gives path_a, path_b and path_c, and so on up to 64. '
              'Merge has inputs path_a to path_e unless input_slots raises it. '
              'Merge passes on one record keyed by input name, so that step reads {{input[path_a]}} and {{input[path_b]}}. '
              'A path may split again, and its children join the same Merge: gather.default to inner.input, inner.path_a to upper.input, '
              'upper.default to join.path_b, lower.default to join.path_c; the inner branch_node needs no Merge input. '
              'Either-or routes may share one input: choose.true to yes.input, choose.false to no.input, yes.default and no.default both to join.path_b; '
              'that input holds the one that ran, and every route must reach the Merge. '
              'Concurrent paths in one input give a list in path order, read as {{input[path_b][0]}}; prefer separate inputs. '
              'To hold one path until a step on another finishes, put wait_until_node first on the waiting path with target_node_ids set to '
              'the handle of that step, ["read"], never the branch_node; it passes on its own input, not that step\'s value. '
              'A text_output_node passes on its text with its label in front, so one feeding a Merge needs "label": "". '
              'A split and its sub-paths use only one Merge. No loops. A Merge needs a split, and join.default must feed a step before End. '
              'A path may end on its own only if it supplies nothing the request needs. '
              'A shared End only finishes each path; it never waits for or combines them.')


def configure(spec, admitted=ADMITTED):
    admitted = frozenset(admitted)
    if not admitted or admitted - ADMITTED:
        raise ValueError('invalid trial admission')
    roles = sorted(BASELINE_ROLES if admitted == ORIGINAL_PALETTE else role_ids(admitted))
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
