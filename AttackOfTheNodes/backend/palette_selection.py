"""Reviewed, bounded discovery for the existing twelve-type admission boundary.

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
ADMITTED = frozenset('start_node end_node branch_end_node branch_node user_text_input_node text_output_node text_transform_node file_reader_node file_output_node conditional_node concat_node json_path_node'.split())
MAX_IDS = 64
CONTRACT_LIMIT = 50000
CONTEXT_LIMIT = 100000
PREFIX = 'Selection snapshot: '

# Reviewed role alternatives: each tuple is one complete composition, not a bag
# of interchangeable words. More complex/unproven roles require an honest stop.
ROLE_TYPES = {
    'start': [('start_node',)], 'finish': [('end_node',)],
    'ask_text': [('user_text_input_node',)],
    'show_text': [('text_output_node',)],
    'show_saved_path': [('text_output_node',), ('json_path_node', 'text_output_node')],
    'read_file': [('file_reader_node',)], 'write_file': [('file_output_node',)],
    'transform_text': [('text_transform_node',)], 'choose_path': [('conditional_node',)],
    'parallel_paths': [('branch_node',)], 'compose_text': [('concat_node',)],
    'extract_json': [('json_path_node',)], 'branch_beacon': [('branch_end_node',)],
    'join': [('merge_node',)], 'persistent_state': [('remember_node',)],
    'vault_state': [('concat_node',)], 'error_route': [('text_output_node',)],
}
# Small support closure, keyed by an explicit role, not service/node families.
SUPPORT = {
    'always': ('start_node', 'end_node'),
    'join': ('merge_node',),
    'vault_state': ('concat_node',),
    'error_route': ('text_output_node',),
}
SYNONYMS = {
    'read_file': ('read', 'file', 'utf-8', 'open file'),
    'write_file': ('save', 'write', 'copy', 'create file'),
    'show_text': ('show', 'display', 'print'),
    'transform_text': ('uppercase', 'lowercase', 'trim', 'strip'),
    'ask_text': ('ask', 'answer', 'prompt'),
    'choose_path': ('if', 'otherwise', 'condition'),
    'parallel_paths': ('parallel', 'simultaneous'),
    'compose_text': ('combine', 'concatenate', 'concat'),
    'extract_json': ('json', 'field'),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def exact_ids(factory, ids):
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
        if kind in HIDDEN_TYPES or meta.get('editor_only'):
            raise NodeError('selection_invalid', f'Hidden type_id: {kind}.')
        if kind not in ADMITTED or not meta.get('node_metadata'):
            raise NodeError('selection_invalid', f'Not admitted: {kind}.')
    return sorted(seen)


def validate_analysis(factory, analysis):
    selection = analysis.get('selection') if isinstance(analysis, dict) else None
    if not isinstance(selection, dict) or set(selection) != {'candidates', 'roles'}:
        raise NodeError('selection_invalid', 'selection needs separate candidates and roles lists.')
    candidates, roles = selection['candidates'], selection['roles']
    if not isinstance(candidates, list) or len(candidates) > MAX_IDS or not isinstance(roles, list) or len(roles) > 32:
        raise NodeError('selection_invalid', 'Selection exceeds candidate/role limits.')
    if candidates:
        exact_ids(factory, [c.get('type_id') if isinstance(c, dict) else None for c in candidates])
    requirements = analysis.get('requirements')
    if not isinstance(requirements, list) or any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in requirements):
        raise NodeError('selection_invalid', 'Requirements need string IDs before candidate selection.')
    req_ids = {r['id'] for r in requirements}
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
    if analysis.get('status') == 'ready' and (not roles or req_ids - {r for row in roles for r in row['requirement_ids']}):
        raise NodeError('selection_invalid', 'Ready selection must cover every requirement with a role.')
    return selection


def positive_matches(factory, query, *, reviewed_only=True):
    """Positive intent only; no not_for or UI-family boundary matching."""
    words = set(re.findall(r'[a-z0-9_]+', query.casefold()))
    hits = []
    for kind, cls in factory._node_registry.items():
        meta = factory.metadata_for_type(kind)
        record = meta.get('node_metadata')
        if reviewed_only and not record:
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
    if not isinstance(request, str) or not request.strip():
        raise NodeError('selection_invalid', 'Freeze the original request before selection.')
    initial = {c['type_id'] for c in selection['candidates']}
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
                if set(composition) <= set(hits) | ids and set(composition) <= ADMITTED:
                    ids.update(composition)
                    break
    unresolved = [r for r in selection['roles'] if not _covered(r['role'], ids)]
    unavailable = sorted(ids - ADMITTED)
    if unresolved or unavailable:
        pending = sorted({k for row in unresolved for alt in ROLE_TYPES.get(row['role'], []) for k in alt
                          if k in factory._node_registry and k not in ADMITTED} | set(unavailable))
        status = 'not_admitted' if pending else 'missing_capability'
        raise NodeError('selection_incomplete', 'Selection stopped: ' + status + '; ' +
                        ', '.join(r['role'] for r in unresolved),
                        details=dict(status=status, missing_roles=unresolved, not_admitted=pending,
                                     expansion_count=len(searches), searches=searches))
    selected = exact_ids(factory, sorted(ids))
    # Refetch once with the expanded identities; no stale draft/check exists yet.
    contracts = await build(factory, dict(config, scope='Exact IDs', type_ids=selected,
                                          detail='Compact', format='Text', max_chars=min(config['max_chars'], CONTRACT_LIMIT)))
    receipt = dict(schema_version=1, selected_type_ids=selected, initial_type_ids=sorted(initial),
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
        if (receipt['contracts_sha256'] != digest(contracts)
                or receipt['contracts_characters'] != len(contracts)
                or sorted(re.findall(r'^node ([a-z0-9_]+) \|', contracts, flags=re.M)) != receipt['selected_type_ids']):
            raise ValueError('snapshot binding')
        return receipt
    except (AttributeError, ValueError, KeyError, TypeError):
        raise NodeError('selection_invalid', 'Missing or stale selected contract snapshot.') from None


def check_draft(factory, draft, text):
    receipt = read_snapshot(text)
    selected = set(exact_ids(factory, receipt['selected_type_ids']))
    if receipt['registry_sha256'] != registry_revision(factory):
        raise NodeError('selection_invalid', 'Registry changed; fetch a fresh selected snapshot.')
    used = {n.get('type') for n in draft.get('nodes', {}).values() if isinstance(n, dict)}
    if used - selected:
        raise NodeError('spec_invalid', 'Draft uses unselected type_ids: ' + ', '.join(sorted(used - selected)))
    return receipt
