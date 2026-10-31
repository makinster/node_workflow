"""Reviewed set-dependency index v1. Unknown impact always expands to all sets.

Node sources come from reviewed manifests and case used-type/alternative tags.
Metadata, retrieval, serving, shared routing and harness changes select all.
The universal calibration core always runs, even for a single affected family.
"""
import json
from pathlib import Path
import subprocess

from .cases import case_record, good_draft

ALL = (1, 2, 3, 4)
# Normal-run cases per suite.
CASE_COUNTS = {1: 10, 2: 10, 3: 4, 4: 5}
APP = Path(__file__).resolve().parents[2]
# These files own only the corresponding versioned suite/oracle. Shared cases.py
# supplies common graph helpers and dispatch, so it is deliberately not narrow.
SET_PATHS = {
    'tools/draft_trials/case_set_two.py': 2,
    'tools/draft_trials/case_set_three.py': 3,
    'tools/draft_trials/rules_set_three.py': 3,
    'tests/test_case_set_two.py': 2,
    'tools/draft_trials/case_set_four.py': 4,
    'tools/draft_trials/rules_family_two.py': 4,
    'tools/draft_trials/family_two.py': 4,
    'tools/draft_trials/family_two_engine.py': 4,
    'tools/draft_trials/family_two_controls.py': 4,
    'tests/test_family_two_trials.py': 4,
}
SHARED_PREFIXES = ('docs/delivery_tests/specs/', 'backend/node_metadata',
                   'backend/palette_selection', 'backend/node_catalogue',
                   'backend/integrations/', 'backend/supervisor', 'backend/master_state',
                   'backend/saved_values', 'backend/vault_declarations', 'backend/node_factory')


def sets_from_text(raw):
    if raw == 'all':
        return list(ALL)
    try:
        values = [int(v) for v in raw.split(',')]
    except (ValueError, AttributeError):
        raise ValueError('--case-set must be all or a comma list of 1,2,3,4') from None
    if not values or len(set(values)) != len(values) or any(v not in ALL for v in values):
        raise ValueError('--case-set must contain distinct sets from 1,2,3,4')
    return sorted(values)


def dependency_index():
    reviews = json.loads((APP/'backend/node_metadata_review.json').read_text())['reviews']
    paths = {}
    for suite in ALL:
        for number in range(1, CASE_COUNTS[suite]+1):
            case = case_record(number, '/dependency-index', suite)
            tags = case.get('dependencies', {})
            types = set(tags.get('used_types', [])) | set(tags.get('candidate_alternatives', []))
            if case.get('expected_status', 'ready') == 'ready':
                types.update(n['type'] for n in good_draft(number, '/dependency-index', suite)['nodes'].values())
            for path in tags.get('helper_paths', []):
                paths.setdefault(path, set()).add(suite)
            for kind in types:
                for path in reviews.get(kind, {}).get('sources', {}):
                    paths.setdefault(path, set()).add(suite)
    return paths


def select_paths(paths):
    index = dependency_index()
    selected = set()
    reasons = {str(n): [] for n in ALL}
    paths = sorted(set(paths))
    for raw in paths:
        path = raw.removeprefix('AttackOfTheNodes/')
        shared = path.startswith(SHARED_PREFIXES)
        matches = set(ALL) if shared else {SET_PATHS[path]} if path in SET_PATHS else index.get(path)
        why = 'shared pipeline/metadata/serving' if shared else 'reviewed suite dependency' if matches else 'unmatched; conservative full selection'
        matches = matches or set(ALL)
        selected.update(matches)
        for n in matches:
            reasons[str(n)].append(dict(path=raw, reason=why))
    if not paths:
        selected.update(ALL)
        for n in ALL:
            reasons[str(n)].append(dict(path=None, reason='no changed paths; conservative full selection'))
    return dict(index_version=1, changed_paths=paths, selected=sorted(selected),
                skipped=[n for n in ALL if n not in selected], reasons=reasons,
                skipped_reason='No changed path in this set’s reviewed dependency index.',
                calibration='always: full universal calibration core')


def affected(base, repo=None):
    repo = Path(repo or APP.parent)
    if not base or base.startswith('-'):
        raise ValueError('--affected needs a git commit/ref')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.PIPE).decode()
    try:
        commit = git('rev-parse', '--verify', base+'^{commit}').strip()
        paths = git('diff', '--no-renames', '--name-only', '-z', commit, '--').split('\0')
        paths += git('ls-files', '--others', '--exclude-standard', '-z').split('\0')
    except subprocess.CalledProcessError:
        raise ValueError('--affected could not resolve/read git base ref') from None
    result = select_paths([p for p in paths if p])
    result['base'] = base
    result['base_sha'] = commit
    return result
