"""Reviewed, bounded discovery for the reviewed admission boundaries.

Selection is evidence about coverage, never permission to run a draft. Unknown
compositions stop rather than treating a keyword hit as proof of capability.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from .node_errors import NodeError

# Admission is deliberately independent of metadata presence/catalogue visibility.
# Join Merge (branch_end_node) is an editor join marker, deliberately not drafted.
ORIGINAL_PALETTE = frozenset('start_node end_node branch_node user_text_input_node text_output_node text_transform_node file_reader_node file_output_node conditional_node concat_node json_path_node'.split())
ORIGINAL_ROLE_IDS = frozenset('start finish ask_text show_text show_saved_path read_file write_file transform_text choose_path parallel_paths compose_text extract_json join persistent_state vault_state error_route'.split())
HELPERS = frozenset('find_lines_node read_lines_node check_reply_node context_pack_node'.split())
# Frozen boundary of helper set 3; Merge is added beside it, not into it.
HELPER_PALETTE = ORIGINAL_PALETTE | HELPERS
# Family 2. Stage 1 is Merge; Stage 2 adds Wait Until. Set/Get are not in this milestone.
STAGE_ONE = frozenset({'merge_node'})
STAGE_TWO = frozenset({'wait_until_node'})
STAGE_TWO_ROLES = frozenset({'wait_for_step'})
ADMITTED = HELPER_PALETTE | STAGE_ONE | STAGE_TWO
# These move together: admission changes the role schema, contracts and provider
# cache prefixes. A snapshot from another version is stale, never reused.
ADMISSION_VERSIONS = dict(admission=3, role_schema=3, contracts=3, cache=3, draft_stage=2)
OUTSIDE_STAGE = 'This is outside this admission stage: '
ONE_JOIN = 'Use one split, with its paths or their sub-paths wired to one Merge.'
MAX_IDS = 64
CONTRACT_LIMIT = 50000
CONTEXT_LIMIT = 100000
PREFIX = 'Selection snapshot: '

# Reviewed role alternatives: each tuple is one complete composition, not a bag
# of interchangeable words. More complex/unproven roles require an honest stop.
ROLE_TYPES = {
    'find_in_file': [('find_lines_node',)], 'read_excerpt': [('read_lines_node',)],
    'check_json_reply': [('check_reply_node',)], 'pack_context': [('context_pack_node',)],
    'start': [('start_node',)], 'finish': [('end_node',)],
    'ask_text': [('user_text_input_node',)],
    'show_text': [('text_output_node',)],
    'show_saved_path': [('text_output_node',), ('json_path_node', 'text_output_node')],
    'read_file': [('file_reader_node',)], 'write_file': [('file_output_node',)],
    'transform_text': [('text_transform_node',)], 'choose_path': [('conditional_node',)],
    'parallel_paths': [('branch_node',)], 'compose_text': [('concat_node',)],
    'extract_json': [('json_path_node',)],
    'join': [('merge_node',)], 'wait_for_step': [('wait_until_node',)],
    'persistent_state': [('remember_node',)],
    'vault_state': [('concat_node',)], 'error_route': [('text_output_node',)],
}
# Small support closure, keyed by an explicit role, not service/node families.
SUPPORT = {
    'always': ('start_node', 'end_node'),
    'find_in_file': (), 'read_excerpt': (), 'check_json_reply': (), 'pack_context': (),
    'join': ('merge_node',),
    'wait_for_step': ('wait_until_node',),
    'vault_state': ('concat_node',),
    'error_route': ('text_output_node',),
}
SYNONYMS = {
    'find_in_file': ('find lines', 'matching lines', 'search text'),
    'read_excerpt': ('excerpt', 'lines around', 'line range'),
    'check_json_reply': ('validate json reply', 'required fields', 'check reply'),
    'pack_context': ('context pack', 'labelled facts', 'redacted facts'),
    'read_file': ('read', 'file', 'utf-8', 'open file'),
    'write_file': ('save', 'write', 'copy', 'create file'),
    'show_text': ('show', 'display', 'print'),
    'transform_text': ('uppercase', 'lowercase', 'trim', 'strip'),
    'ask_text': ('ask', 'answer', 'prompt'),
    'choose_path': ('if', 'otherwise', 'condition'),
    'parallel_paths': ('parallel', 'simultaneous'),
    'compose_text': ('combine', 'concatenate', 'concat'),
    'extract_json': ('json', 'field'),
    'join': ('join', 'merge', 'collect results', 'together after'),
    'wait_for_step': ('wait until', 'wait for', 'hold until'),
}


def role_ids(admitted):
    """Role IDs a drafting boundary may name; frozen boundaries keep theirs."""
    return frozenset(ROLE_TYPES) - (frozenset() if STAGE_TWO <= admitted else STAGE_TWO_ROLES)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def admission(config):
    """Optional exact boundary, used to preserve frozen twelve-type trials."""
    ids = config.get('admitted_type_ids', [])
    if not isinstance(ids, list) or any(not isinstance(k, str) for k in ids) or len(ids) != len(set(ids)) or set(ids) - ADMITTED:
        raise NodeError('selection_invalid', 'admitted_type_ids must be distinct admitted identities.')
    return frozenset(ids) if ids else ADMITTED


def exact_ids(factory, ids, *, allowed=ADMITTED):
    from .authoring import HIDDEN_TYPES
    if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_IDS:
        raise NodeError('selection_invalid', f'type_ids must be a list of 1–{MAX_IDS} exact IDs.')
    seen = set()
    for kind in ids:
        if not isinstance(kind, str) or len(kind) > 128 or kind not in factory._node_registry:
            raise NodeError('selection_invalid', f'Unknown type_id: {str(kind)[:128]!r}.')
        if kind in seen:
            raise NodeError('selection_invalid', f'Duplicate type_id: {kind}.')
        seen.add(kind)
        meta = factory.metadata_for_type(kind)
        if kind in HIDDEN_TYPES or meta.get('editor_only') or meta.get('dev_test_only'):
            raise NodeError('selection_invalid', f'Hidden type_id: {kind}.')
        if kind not in allowed or not meta.get('node_metadata'):
            raise NodeError('selection_invalid', f'Not admitted: {kind}.')
    return sorted(seen)


def _merge_repeats(rows, key):
    """Fold repeated rows for one ID into the first, joining requirement IDs.

    A schema cannot forbid repeats; listing a node or role twice is not a
    selection error. Malformed rows pass through for the checks below.
    """
    merged, first = [], {}
    for row in rows:
        ident = row.get(key) if isinstance(row, dict) else None
        if (isinstance(ident, str) and ident in first and isinstance(row.get('requirement_ids'), list)
                and isinstance(first[ident].get('requirement_ids'), list)):
            ids = first[ident]['requirement_ids']
            ids.extend(r for r in row['requirement_ids'] if r not in ids)
            continue
        row = deepcopy(row)
        if isinstance(ident, str):
            first[ident] = row
        merged.append(row)
    return merged


def validate_analysis(factory, analysis):
    selection = analysis.get('selection') if isinstance(analysis, dict) else None
    if not isinstance(selection, dict) or set(selection) != {'candidates', 'roles'}:
        raise NodeError('selection_invalid', 'selection needs separate candidates and roles lists.')
    candidates, roles = selection['candidates'], selection['roles']
    if not isinstance(candidates, list) or len(candidates) > MAX_IDS or not isinstance(roles, list) or len(roles) > 32:
        raise NodeError('selection_invalid', 'Selection exceeds candidate/role limits.')
    candidates, roles = _merge_repeats(candidates, 'type_id'), _merge_repeats(roles, 'role')
    # Only repair an undeclared role when identity gives one unambiguous
    # declared alternative. Start/End are already in the support closure.
    declared = {r.get('role') for r in roles
                if isinstance(r, dict) and isinstance(r.get('role'), str)}
    repaired = []
    for candidate in candidates:
        if isinstance(candidate, dict) and isinstance(candidate.get('role'), str) and candidate['role'] not in declared:
            kind = candidate.get('type_id')
            if kind in ('start_node', 'end_node'):
                continue
            matches = [role for role in declared
                       if any(kind in composition for composition in ROLE_TYPES.get(role, []))]
            if len(matches) == 1:
                candidate['role'] = matches[0]
        repaired.append(candidate)
    candidates = repaired
    selection = dict(candidates=candidates, roles=roles)
    if candidates:
        exact_ids(factory, [c.get('type_id') if isinstance(c, dict) else None for c in candidates])
    requirements = analysis.get('requirements')
    if not isinstance(requirements, list) or any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in requirements):
        raise NodeError('selection_invalid', 'Requirements need string IDs before candidate selection.')
    req_ids = {r['id'] for r in requirements}
    if any(r.get('kind', 'action') not in ('action', 'constraint') for r in requirements):
        raise NodeError('selection_invalid', 'Requirement kind must be action or constraint.')
    action_ids = {r['id'] for r in requirements if r.get('kind', 'action') == 'action'}
    for row in candidates + roles:
        if (not isinstance(row, dict) or not isinstance(row.get('role'), str)
                or not row['role'].strip() or len(row['role']) > 128
                or not isinstance(row.get('reason'), str) or not row['reason'].strip()
                or len(row['reason']) > 512 or not isinstance(row.get('requirement_ids'), list)
                or not row['requirement_ids'] or not all(type(r) is str and r in req_ids for r in row['requirement_ids'])):
            raise NodeError('selection_invalid', 'Each candidate/role needs known requirement_ids, role and short reason.')
    role_names = [r['role'] for r in roles]
    if len(role_names) != len(set(role_names)) or any(c['role'] not in role_names for c in candidates):
        raise NodeError('selection_invalid', 'Candidate roles must name unique declared roles.')
    if analysis.get('status') == 'ready' and (not req_ids or action_ids - {r for row in roles for r in row['requirement_ids']}):
        raise NodeError('selection_invalid', 'Ready selection must cover every action requirement with a role.')
    return selection


def positive_matches(factory, query, *, reviewed_only=True):
    """Positive intent only; no not_for or UI-family boundary matching."""
    words = set(re.findall(r'[a-z0-9_]+', query.casefold()))
    hits = []
    for kind, cls in factory._node_registry.items():
        meta = factory.metadata_for_type(kind)
        record = meta.get('node_metadata')
        if meta.get('dev_test_only') or (reviewed_only and not record):
            continue
        text = ' '.join([kind, cls.display_name, (record or {}).get('purpose', ''),
                         (record or {}).get('use_when', ''), *(meta.get('tags') or [])]).casefold()
        score = sum(w in set(re.findall(r'[a-z0-9_]+', text)) for w in words)
        for role, aliases in SYNONYMS.items():
            if any(a in query.casefold() for a in aliases) and any(kind in alt for alt in ROLE_TYPES[role]):
                score += 3
        if kind in query or cls.display_name.casefold() == query.casefold():
            score += 10
        if score:
            hits.append((score, kind))
    return [kind for _, kind in sorted(hits, key=lambda p: (-p[0], p[1]))]


def implemented_not_admitted(factory, allowed):
    """Classification hints for the drafter: never dev/test-only or editor-only markers."""
    return sorted(kind for kind in set(factory._node_registry) - allowed - {'tombstone_node', 'branch_end_node'}
                  if not factory.metadata_for_type(kind).get('dev_test_only'))


def registry_revision(factory):
    return digest({kind: factory.metadata_for_type(kind) for kind in sorted(factory._node_registry)})


def _covered(role, ids):
    return any(set(composition) <= ids for composition in ROLE_TYPES.get(role, []))


async def snapshot(factory, analysis, request, config, *, clarification=''):
    """One local expansion across all missing roles, then complete refetch or stop.

    The role table is the adequacy proof. Search alone never certifies a new
    operation; unknown roles produce an explicit unproven-composition stop.
    """
    from .node_catalogue import build
    selection = validate_analysis(factory, analysis)
    allowed = admission(config)
    if not isinstance(request, str) or not request.strip():
        raise NodeError('selection_invalid', 'Freeze the original request before selection.')
    initial = {c['type_id'] for c in selection['candidates']}
    if initial:
        exact_ids(factory, sorted(initial), allowed=allowed)
    ids = initial | set(SUPPORT['always'])
    for row in selection['roles']:
        ids.update(SUPPORT.get(row['role'], ()))
    missing = [r for r in selection['roles'] if not _covered(r['role'], ids)]
    searches = []
    if missing:
        query = request + '\n' + '\n'.join(r['role'] + ' ' + r['reason'] for r in missing)
        hits = positive_matches(factory, query)
        searches.append(dict(query=query, results=hits))
        for row in missing:
            # Search is over the full reviewed catalogue; intersect with a
            # reviewed complete alternative, never silently approximate a role.
            for composition in ROLE_TYPES.get(row['role'], []):
                if set(composition) <= set(hits) | ids and set(composition) <= allowed:
                    ids.update(composition)
                    break
    unresolved = [r for r in selection['roles'] if not _covered(r['role'], ids)]
    unavailable = sorted(ids - allowed)
    if unresolved or unavailable:
        pending = sorted({k for row in unresolved for alt in ROLE_TYPES.get(row['role'], []) for k in alt
                          if k in factory._node_registry and k not in allowed} | set(unavailable))
        status = 'not_admitted' if pending else 'missing_capability'
        raise NodeError('selection_incomplete', 'Selection stopped: ' + status + '; ' +
                        ', '.join(r['role'] for r in unresolved),
                        details=dict(status=status, missing_roles=unresolved, not_admitted=pending,
                                     expansion_count=len(searches), searches=searches))
    selected = exact_ids(factory, sorted(ids), allowed=allowed)
    # Refetch once with the expanded identities; no stale draft/check exists yet.
    contracts = await build(factory, dict(config, scope='Exact IDs', type_ids=selected,
                                          detail='Compact', format='Text', max_chars=min(config['max_chars'], CONTRACT_LIMIT)))
    # Frozen trial boundaries cannot select Merge and keep their earlier checks.
    receipt = dict(schema_version=1, admission=ADMISSION_VERSIONS,
                   draft_stage=ADMISSION_VERSIONS['draft_stage'] if STAGE_ONE <= allowed else None,
                   selected_type_ids=selected, initial_type_ids=sorted(initial),
                   registry_sha256=registry_revision(factory), request_sha256=digest(request),
                   analysis_sha256=digest(analysis), clarification_sha256=digest(clarification),
                   roles=deepcopy(selection['roles']),
                   roles_covered=[r['role'] for r in selection['roles']], missing_roles=[],
                   candidate_count=len(selected), expansion_count=len(searches), searches=searches,
                   contracts_sha256=digest(contracts), contracts_characters=len(contracts))
    result = PREFIX + json.dumps(receipt, ensure_ascii=False, separators=(',', ':')) + '\n' + contracts
    limit = min(config['max_chars'], CONTRACT_LIMIT)
    if len(result) > limit or len(result.encode()) > 256 * 1024:
        raise NodeError('catalogue_too_large', 'Complete selected snapshot exceeds the contract budget.',
                        details=dict(characters=len(result), bytes=len(result.encode()), limit=limit, matched_count=len(selected)))
    return result


def read_snapshot(text):
    try:
        header, contracts = text.split('\n', 1)
        if not header.startswith(PREFIX):
            raise ValueError('snapshot header')
        receipt = json.loads(header[len(PREFIX):])
        if (receipt['admission'] != ADMISSION_VERSIONS
                or receipt['contracts_sha256'] != digest(contracts)
                or receipt['contracts_characters'] != len(contracts)
                or sorted(re.findall(r'^node ([a-z0-9_]+) \|', contracts, flags=re.M)) != receipt['selected_type_ids']):
            raise ValueError('snapshot binding')
        return receipt
    except (AttributeError, ValueError, KeyError, TypeError):
        raise NodeError('selection_invalid', 'Missing or stale selected contract snapshot.') from None


def _first_wire(draft, source):
    """The target handle of a draft's own first wire from one output, or None.

    analyze_flow's control rows do not name ports. This reads one wire and walks nothing.
    """
    return next((wire['to'].partition('.')[0] for wire in draft.get('connections', [])
                 if wire.get('from') == source), None)


def draft_stage_problems(flow, draft):
    """Plain refusals of anything beyond the current draft stage.

    The analysis owns the graph facts and admission stage; this only names them.
    The engine runs these shapes: a refusal here says nothing about what it can do.
    """
    kinds = {nid: str(getattr(p['kind'], 'value', p['kind'])) for nid, p in flow['profiles'].items()}
    merges = flow['merges']
    joined = {root for merge in merges.values() for root in merge['group_roots']}
    problems = []
    if flow['back_edges']:
        problems.append('loops are not supported in drafts yet. Remove the connection that goes back to an earlier step.')
    if 'beacon' in kinds.values():
        problems.append('Join Merges are not available in drafts. Wire each path directly to the Merge.')
    for nid, profile in flow['profiles'].items():
        if kinds[nid] == 'wait' and (not profile['targets'] or any(kinds.get(t) == 'fork' for t in profile['targets'])):
            problems.append('Wait Until must name the step it waits for, not a split. Set target_node_ids to that step.')
    for root, group in flow['groups'].items():
        if root not in joined and (merges or any(h['lineage'] for h in group['handoffs'])):
            problems.append('a split inside a path, or beside a Merge, must have its paths join that Merge. ' + ONE_JOIN)
    for mid, merge in merges.items():
        if not merge['group_roots']:
            problems.append('a Merge with no split is not available in drafts. ' + ONE_JOIN)
            continue
        if any(set(other['group_roots']) & set(merge['group_roots']) for oid, other in merges.items() if oid != mid):
            problems.append('a split and its sub-paths may use only one Merge. ' + ONE_JOIN)
        if _first_wire(draft, mid + '.error') is not None:
            problems.append("a route leaving the Merge is not available in drafts. Remove the Merge's error wire.")
        if kinds.get(_first_wire(draft, mid + '.default'), 'finish') == 'finish':
            problems.append("the Merge's collected result must feed a later step before End.")
    if flow['admission_stage'] > ADMISSION_VERSIONS['draft_stage'] and not problems:
        problems.append(ONE_JOIN)
    return [OUTSIDE_STAGE + p for p in dict.fromkeys(problems)]


def check_draft(factory, draft, text, flow=None):
    receipt = read_snapshot(text)
    selected = set(exact_ids(factory, receipt['selected_type_ids']))
    if receipt['registry_sha256'] != registry_revision(factory):
        raise NodeError('selection_invalid', 'Registry changed; fetch a fresh selected snapshot.')
    used = {n.get('type') for n in draft.get('nodes', {}).values() if isinstance(n, dict)}
    if used - selected:
        raise NodeError('spec_invalid', 'Draft uses unselected type_ids: ' + ', '.join(sorted(used - selected)))
    if receipt['draft_stage'] is not None:
        if flow is None:
            raise NodeError('selection_invalid', 'Draft check needs the shared flow analysis.')
        problems = draft_stage_problems(flow, draft)
        if problems:
            raise NodeError('spec_invalid', 'Workflow spec did not pass.\n' + '\n'.join(problems),
                            details=dict(problems=problems))
    return receipt
