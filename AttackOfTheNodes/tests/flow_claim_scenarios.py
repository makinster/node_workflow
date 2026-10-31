"""Flow record evidence matrix: real-engine assertions, never fake join callbacks."""
from itertools import product

SCENARIOS=[]

def add(claim, function, module='test_merge_arrival_runtime', **params):
    SCENARIOS.append(dict(id=f'{claim}:{function}:{params}', claim=claim,
                          module='tests.'+module, function=function, params=params))

add('M1','test_two_real_files_collect_in_slot_order_after_reversed_arrival')
add('M1','test_shared_producer_and_shared_beacon_do_not_reread_another_invocations_value')
for value in [None,False,0,'',[],{}]:
    add('M2','test_present_falsy_values_are_collected_and_missing_is_omitted',value=value)
    add('M9','test_merge_outside_a_split_passes_through_the_actual_value',value=value)
add('M2','test_merge_slots_use_numeric_order_after_z')
for left,right,missing in [(None,False,False),([1],[2],False),(0,'',False),('only',None,True)]:
    add('M3','test_concurrent_same_slot_is_always_a_list_in_path_order',left=left,right=right,missing=missing)
for greeting,wanted in [('yes','Y'),('no','N')]:
    add('M3','test_exclusive_routes_rejoin_one_scalar_slot_and_ignore_inactive_stale_values',greeting=greeting,wanted=wanted)
for beacons,host,a_first in product([False,True],['A','C','D'],[False,True]):
    add('M4','test_inherited_A_and_B_handoff_to_C_D_collect_and_continue_on_shallow_A',beacons=beacons,host=host,a_first=a_first)
for first in ['A','B','simultaneous']:
    add('M5','test_equal_depth_uses_first_arrival_and_simultaneous_delivery_continues_once',first=first)
add('M6','test_a_wait_on_merge_wakes_only_after_the_continuing_arrival_publishes')
add('M6','test_a_duplicate_receipt_after_continuation_cannot_continue_again')
for before_wait in [False,True]:
    add('M7','test_a_failed_member_fails_merge_once_and_releases_peers',before_wait=before_wait)
    add('M7','test_whole_workflow_abort_records_the_merge_failure_once',before_wait=before_wait)
for function in ['test_a_plain_end_settles_an_independent_side_path_without_a_value',
                 'test_stop_during_join_is_quiet_and_leaves_no_partial_output',
                 'test_an_error_route_that_recovers_and_arrives_is_not_a_terminal_member_failure',
                 'test_terminal_failure_marks_merge_even_when_no_member_ever_arrives']:
    add('M7',function)
add('M8','test_new_run_cannot_receive_a_previous_runs_arrivals_or_callbacks')
add('M9','test_merge_outside_a_split_preserves_a_control_only_delivery_as_missing')
add('B1','test_depth_refusal_is_an_error_at_the_branch_and_launches_no_children')
for count in [6,8]:
    add('B1','test_sequential_splits_open_new_groups_and_restore_opening_depth',module='test_merge_plan_integration',count=count,limit=5)
add('B1','test_real_nesting_beyond_default_depth_still_refuses_the_whole_batch',module='test_merge_plan_integration')
for fails in [False,True]:
    add('G1','test_independent_side_end_or_failure_is_excluded_from_merge',module='test_merge_plan_integration',fails=fails)
for function in ['test_merge_after_merge_without_a_new_split_is_refused_before_start',
                 'test_inner_join_cannot_feed_outer_join_before_start',
                 'test_two_joins_on_separate_paths_of_one_split_are_refused']:
    add('G1',function,module='test_merge_plan_integration')
for value in [None,False,0,'',[],{'value':[1,2]}]:
    for form in ['list','comma','newline','empty']:
        add('W1','own_input_and_targets',module='flow_engine_scenarios',value=value,form=form)
add('W2','sticky_completion_and_fresh_run',module='flow_engine_scenarios')
add('W2','timeout_and_stop',module='flow_engine_scenarios')
add('M8','independent_services',module='flow_engine_scenarios')

add('W1','own_input_and_targets',module='flow_engine_scenarios',value=None,form='newline',present=False)
add('W2','test_failed_merge_releases_wait_until_without_completion')

add('M1','test_manager_reader_writer_parallel_merge_and_end_branch',module='test_payload_plan_integration',shown_slot='path_a',expected='first\n')
add('W2','test_wait_until_fails_when_its_target_errors_and_its_branch_is_terminated',module='test_wait_until_reachability')

# Owner decision 7: refusal at the same direct startup entry point as App Run.
for kind,greeting in [('escape','yes'),('escape','no'),('omitted','yes'),('omitted','no'),('impossible','yes'),('missing','yes')]:
    add('G2','test_app_style_start_refuses_flow_error_without_a_run',module='test_flow_startup_refusals',kind=kind,greeting=greeting)
add('G2','test_escaping_child_is_a_typed_subworkflow_error',module='test_flow_startup_refusals')

# Shared checker repairs: automatic coordinator plans, no injected barriers.
for function in ['test_self_wait_with_disconnected_loop_refuses_normal_startup',
                 'test_valid_wait_still_runs_with_disconnected_loop',
                 'test_connected_slot_with_missing_value_is_not_statically_refused']:
    add('G2',function,module='test_family_two_checker_fixes')
for kind in ['text_output_node','concat_node']:
    add('M1','test_valid_direct_merge_templates_run',module='test_family_two_checker_fixes',kind=kind)
for fails in [False,True]:
    add('G1','test_success_and_recovery_rejoin_with_valid_health_and_real_run',module='test_family_two_checker_fixes',fails=fails)
add('B1','test_limit_boundary_real_run_and_live_service_validation',module='test_family_two_checker_fixes')
add('B1','test_sequential_merges_reset_depth_in_analysis_and_runtime',module='test_family_two_checker_fixes')
