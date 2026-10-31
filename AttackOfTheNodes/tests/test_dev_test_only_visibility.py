"""Dev/test-only nodes and Merge Beacon: what each surface may and may not show.

Owner decisions 2026-10-30. The 16 dev/test-only types leave the normal picker
and every drafter path but stay registered, loadable and runnable. Merge Beacon
stays in the editor and picker and only leaves the drafter.
"""
import asyncio
import json
from copy import deepcopy
from pathlib import Path

import pytest

from backend import authoring, node_catalogue
from backend.node_errors import NodeError
from backend.node_factory import NodeFactory
from backend.node_metadata import (
    DEV_TEST_ONLY, LIGHT_RECORD_TYPES, NODE_METADATA, PENDING_REVIEW, is_dev_test_only,
    record_problems,
)
from backend.nodes.data.node_catalogue_node import NodeCatalogueNode
from backend.palette_selection import (
    ADMITTED, HELPER_PALETTE, HELPERS, ORIGINAL_PALETTE, ORIGINAL_ROLE_IDS, ROLE_TYPES, STAGE_ONE, admission, exact_ids,
    implemented_not_admitted, positive_matches, validate_analysis,
)
from frontend.screens.node_selector import HIDDEN_NODE_TYPES, TABS, NodeSelectorScreen
from tests.test_node_metadata_behavior import engine  # noqa: F401
from tools.draft_trials.admission import configure
from tools.draft_trials.reply_schemas import analysis_schema

ROOT = Path(__file__).resolve().parents[1]
FACTORY = NodeFactory()
SPEC = json.loads((ROOT / 'docs/delivery_tests/specs/draft-a-workflow-v2.json').read_text())
BEACON = 'branch_end_node'
# Deliberately spelled out here: the set is an owner decision, not a derived value.
EXACT_16 = {
    'counter_node', 'echo_node', 'error_node', 'logger_node', 'memory_snapshot_node',
    'no_op_node', 'probe_node', 'repeat_counter_node', 'deep_branch_node',
    'random_branch_node', 'variable_setter_node', 'variable_reader_node', 'embedding_node',
    'image_generation_node', 'chat_completion_node', 'random_number_node',
}
KEEP_VISIBLE = {'sleep_node', BEACON, 'merge_node', 'set_variable_node', 'get_variable_node',
                'wait_until_node', 'branch_node'}


def catalogue_config(**changes):
    return dict(deepcopy(FACTORY._node_registry['node_catalogue_node'].default_config),
                max_chars=node_catalogue.MAX_CHARS_LIMIT, format='JSON', **changes)


# --- the set and the three coverage buckets ---------------------------------------

def test_set_is_exactly_the_owner_list_and_the_factory_exports_it():
    assert DEV_TEST_ONLY == EXACT_16 and len(DEV_TEST_ONLY) == 16
    for kind in FACTORY.get_registered_types():
        assert FACTORY.metadata_for_type(kind)['dev_test_only'] is (kind in EXACT_16)
        assert is_dev_test_only(kind) is (kind in EXACT_16)


def test_coverage_is_a_disjoint_three_way_split():
    registered = set(FACTORY.get_registered_types())
    reviewed = set(NODE_METADATA)
    assert not reviewed & PENDING_REVIEW and not reviewed & DEV_TEST_ONLY
    assert not PENDING_REVIEW & DEV_TEST_ONLY
    assert reviewed | PENDING_REVIEW | DEV_TEST_ONLY == registered
    assert (len(reviewed), len(PENDING_REVIEW), len(DEV_TEST_ONLY)) == (18, 25, 16)


def test_record_shape_and_visibility_stay_independent():
    assert 'sleep_node' in LIGHT_RECORD_TYPES - DEV_TEST_ONLY
    assert 'tombstone_node' in LIGHT_RECORD_TYPES - DEV_TEST_ONLY
    assert 'tombstone_node' in PENDING_REVIEW and 'sleep_node' in PENDING_REVIEW


def test_no_record_may_point_at_a_dev_test_only_type():
    record = deepcopy(NODE_METADATA['context_pack_node'])
    record['use_instead'] = [dict(when='Debug it', node_type='probe_node')]
    assert any('use_instead' in p for p in record_problems('context_pack_node', record))


# --- normal picker ------------------------------------------------------------------

def run_selector(body):
    from textual.app import App
    screen = NodeSelectorScreen(FACTORY)

    class SelectorApp(App):
        CSS_PATH = str(ROOT / 'frontend/styles.tcss')

        def on_mount(self):
            self.push_screen(screen)

    async def run():
        async with SelectorApp().run_test(size=(120, 40)) as pilot:
            await pilot.pause(0.1)
            await body(pilot, screen)

    asyncio.run(run())


def listed(screen):
    seen = set()
    for tab in TABS:
        screen._set_active_tab(tab)
        for entry in screen._entries:
            if entry['kind'] == 'node':
                seen.add(entry['node']['type'])
            elif entry['kind'] == 'group':
                seen.update(member['type'] for member in entry['members'])
    return seen


def test_picker_browsing_groups_and_search_hide_them_only():
    async def body(pilot, screen):
        browsing = listed(screen)
        assert not browsing & DEV_TEST_ONLY
        assert KEEP_VISIBLE <= browsing
        assert browsing == set(FACTORY.get_registered_types()) - DEV_TEST_ONLY - HIDDEN_NODE_TYPES
        for tab in TABS:
            screen._set_active_tab(tab)
            for kind in sorted(DEV_TEST_ONLY):
                screen._apply_filter(kind)
                assert kind not in {e['node']['type'] for e in screen._entries if e['kind'] == 'node'}
            screen._apply_filter('')
            for entry in screen._entries:
                if entry['kind'] != 'group':
                    continue
                assert not {m['type'] for m in entry['members']} & DEV_TEST_ONLY
                screen._enter_quick_list(entry)
                assert not set(screen._quick_list_members) & DEV_TEST_ONLY
                screen._exit_quick_list()
    run_selector(body)


# --- every drafter path, even with include_debug ---------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize('detail', ['Brief', 'Compact'])
@pytest.mark.parametrize('include_debug', [False, True])
async def test_catalogue_never_lists_them(detail, include_debug):
    record = await node_catalogue.build(FACTORY, catalogue_config(detail=detail, include_debug=include_debug))
    kinds = {e['type'] for e in record['entries']}
    assert not kinds & DEV_TEST_ONLY
    assert ('sleep_node' in kinds) is include_debug  # Sleep keeps its Debug opt-in.
    assert BEACON in kinds  # An ordinary catalogue view is not drafter admission.


@pytest.mark.asyncio
@pytest.mark.parametrize('kind', sorted(EXACT_16))
async def test_filtered_search_and_exact_ids_refuse_each(kind):
    with pytest.raises(NodeError, match='Broaden'):
        await node_catalogue.build(FACTORY, catalogue_config(scope='Filtered', search=kind, include_debug=True))
    with pytest.raises(NodeError, match='Hidden type_id'):
        exact_ids(FACTORY, [kind])
    with pytest.raises(NodeError, match='Hidden type_id'):
        exact_ids(FACTORY, [kind], allowed=frozenset(EXACT_16))
    with pytest.raises(NodeError, match='Hidden type_id'):
        await node_catalogue.build(FACTORY, catalogue_config(scope='Exact IDs', type_ids=[kind], include_debug=True))
    with pytest.raises(NodeError, match='distinct admitted'):
        admission(dict(admitted_type_ids=[kind]))
    assert kind not in positive_matches(FACTORY, kind, reviewed_only=False)
    assert kind not in implemented_not_admitted(FACTORY, ADMITTED)


def test_drafter_lists_stay_free_of_them_with_one_shared_flag():
    source = (ROOT / 'backend/palette_selection.py').read_text() + (ROOT / 'backend/node_catalogue.py').read_text() \
        + (ROOT / 'frontend/screens/node_selector.py').read_text()
    # One list, one flag: these surfaces read the factory's bool, not a copy.
    assert not [kind for kind in EXACT_16 if kind in source]
    assert not EXACT_16 & ADMITTED
    assert not {k for roles in ROLE_TYPES.values() for alt in roles for k in alt} & EXACT_16
    text = json.dumps(SPEC)
    for kind in sorted(EXACT_16):
        assert kind not in text


# --- still registered, loadable, showable and runnable ------------------------------

@pytest.mark.parametrize('kind', sorted(EXACT_16))
def test_not_hidden_from_loading_or_authoring(kind):
    assert kind not in authoring.HIDDEN_TYPES
    assert kind in {row['type'] for row in authoring.list_node_types(FACTORY)}
    assert authoring.describe_node_type(FACTORY, kind)['type'] == kind


def test_old_style_spec_with_dev_nodes_still_builds():
    spec = dict(format='aotn-workflow/1', name='Old debugging workflow',
                nodes=dict(start=dict(type='start_node'), echo=dict(type='echo_node'),
                           logger=dict(type='logger_node'), end=dict(type='end_node')),
                connections=[{'from': 'start.default', 'to': 'echo.input'},
                             {'from': 'echo.default', 'to': 'logger.input'},
                             {'from': 'logger.default', 'to': 'end.input'}])
    assert authoring.check_workflow_spec(FACTORY, spec)['ok'] is True


@pytest.mark.asyncio
async def test_saved_workflow_with_a_dev_node_loads_and_runs(engine):  # noqa: F811
    from backend.run_policies import TerminatePolicy
    wm = engine.workflow_map
    wm.create_new('Old debugging workflow')
    start, echo, end = wm.add_node('start_node'), wm.add_node('echo_node'), wm.add_node('end_node')
    wm.connect(start, 'default', echo, 'input')
    wm.connect(echo, 'default', end, 'input')
    assert wm.get_node_data(echo)['type'] == 'echo_node'
    await engine.start(recovery_policy=TerminatePolicy('terminate_workflow'))
    result = await engine.wait()
    assert result.errors == [] and result.final_state == 'FINISHED'


# --- Merge Beacon leaves the drafter only ------------------------------------------------

def test_beacon_is_out_of_admission_roles_schemas_and_prompts():
    assert BEACON not in ORIGINAL_PALETTE and BEACON not in ADMITTED
    assert ADMITTED == ORIGINAL_PALETTE | HELPERS | STAGE_ONE and len(ADMITTED) == 16
    assert 'branch_beacon' not in ROLE_TYPES and 'branch_beacon' not in ORIGINAL_ROLE_IDS
    assert not {k for roles in ROLE_TYPES.values() for alt in roles for k in alt} & {BEACON}
    schema = json.dumps(analysis_schema())
    assert BEACON not in schema and 'branch_beacon' not in schema
    for admitted in (ORIGINAL_PALETTE, HELPER_PALETTE, ADMITTED):
        text = json.dumps(configure(deepcopy(SPEC), admitted))
        assert BEACON not in text and 'branch_beacon' not in text
    assert BEACON not in implemented_not_admitted(FACTORY, ADMITTED)
    assert BEACON not in json.dumps(SPEC) and 'branch_beacon' not in json.dumps(SPEC)


def test_a_beacon_candidate_or_role_is_refused():
    with pytest.raises(NodeError, match='Not admitted'):
        exact_ids(FACTORY, [BEACON])
    with pytest.raises(NodeError, match='Not admitted'):
        validate_analysis(FACTORY, dict(status='ready', requirements=[dict(id='r1')], selection=dict(
            candidates=[dict(type_id=BEACON, role='join', requirement_ids=['r1'], reason='x')],
            roles=[dict(role='join', requirement_ids=['r1'], reason='x')])))


def test_beacon_stays_a_normal_reviewed_runnable_node():
    meta = FACTORY.metadata_for_type(BEACON)
    assert meta['dev_test_only'] is False and meta['node_metadata']
    assert BEACON not in authoring.HIDDEN_TYPES and BEACON in NODE_METADATA


def test_set_and_get_variable_stay_unadmitted_but_not_dev_only():
    for kind in ('set_variable_node', 'get_variable_node'):
        assert kind not in ADMITTED and kind not in DEV_TEST_ONLY and kind in PENDING_REVIEW
        assert kind in implemented_not_admitted(FACTORY, ADMITTED)
        with pytest.raises(NodeError, match='Not admitted'):
            exact_ids(FACTORY, [kind])


def test_catalogue_node_config_offers_only_admitted_boundaries():
    options = NodeCatalogueNode.config_schema['admitted_type_ids']['options']
    assert options == sorted(ADMITTED)
