"""Free replay and invocation-wide calibration; real pipeline, SDK boundary only."""
from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from backend.configuration_manager import ConfigurationManager
from backend.palette_selection import ADMITTED, ORIGINAL_PALETTE
from tools.draft_trials import runner
from tools.draft_trials.costing import cache_report
from tools.draft_trials.dependencies import affected, select_paths, sets_from_text
from tools.draft_trials.replay import ReplayRun, ReplayTape, comparison

FIXTURE = Path(runner.__file__).parent/'fixtures/replay_small'


def copy_run(tmp_path):
    path = tmp_path/'source'
    shutil.copytree(FIXTURE, path)
    return path


def edit(path, change):
    value = json.loads(path.read_text())
    change(value)
    runner.write_json(path, value)


@pytest.mark.slow
def test_committed_saved_run_replays_all_checks_without_mutating_source(tmp_path):
    before = runner.tree(FIXTURE)
    result = subprocess.run([sys.executable, '-m', 'tools.draft_trials', '--trial-root', str(tmp_path/'trial'),
                             '--replay', str(FIXTURE)], cwd=runner.APP, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout+result.stderr
    report_path = Path(json.loads(result.stdout)['report'])
    report = json.loads(report_path.read_text())
    assert report['mode'] == 'replay' and report['fully_right'] == 1
    assert report['replay_summary'] == dict(same_outcome=1, newly_passing=0, newly_failing=0, diverged=0)
    case = report['cases'][0]
    assert case['spec_valid'] == case['case_rules']['result'] == case['behavior']['result'] == 'pass'
    assert case['replay']['consumed'] == 3 and case['replay']['remaining'] == 0
    assert case['selection']['expansion_count'] == 0
    calibration = json.loads((report_path.parent/'calibration-report.json').read_text())
    assert len(calibration['fixtures']) == 60 and calibration['result'] == 'pass'
    assert calibration['replay_summary']['same_outcome'] == 60
    assert all(row['case_rules'] == row['expected'] for row in calibration['fixtures'])
    assert runner.tree(FIXTURE) == before
    assert not list((tmp_path/'trial').rglob('secrets.json'))


@pytest.mark.asyncio
@pytest.mark.parametrize('mode', ['new_retry', 'missing_reply', 'missing_first_draft'])
async def test_replay_diverges_without_inventing_or_reusing_an_answer(tmp_path, mode):
    source = copy_run(tmp_path)
    evidence = source/'cases/1/evidence.json'
    if mode == 'missing_reply':
        edit(evidence, lambda e: e.pop('draft_text'))
    else:
        edit(evidence, lambda e: e.update(draft_text=json.dumps(dict(format='aotn-workflow/1', nodes=[], connections=[]))))
        if mode == 'missing_first_draft':
            edit(source/'cases/1/designer-run.json', lambda r: r['steps'].insert(2, dict(handle='draft_retry', status='running')))
    row = await runner.run_case(1, tmp_path/'out', tmp_path/'library', replay=ReplayRun(source))
    assert row['result'] == 'replay_diverged', row
    assert row['replay']['comparison'] == 'diverged' and not row['fully_right']
    assert 'replay_diverged' in row['failure']
    assert not (tmp_path/'out/cases/1/target-runs').exists()
    if mode == 'new_retry':
        assert 'draft_retry' in row['failure'] and 'judge' in row['failure']
        assert row['replay']['consumed'] == 2  # Saved judge never becomes a draft.
    else:
        assert row['replay']['consumed'] == 1


@pytest.mark.asyncio
async def test_replay_preserves_first_draft_then_the_single_saved_retry(tmp_path):
    source = copy_run(tmp_path)
    edit(source/'cases/1/evidence.json', lambda e: e.update(first_draft_text=json.dumps(dict(format='aotn-workflow/1', nodes=[], connections=[]))))
    edit(source/'cases/1/designer-run.json', lambda r: r['steps'].insert(2, dict(handle='draft_retry', status='running')))
    row = await runner.run_case(1, tmp_path/'out', tmp_path/'library', replay=ReplayRun(source))
    assert row['result'] == 'pass', row
    assert row['replay']['consumed'] == 4
    assert row['draft_retry']['attempted'] == 1 and row['draft_retry']['check_passed']
    evidence = json.loads((tmp_path/'out/cases/1/evidence.json').read_text())
    assert json.loads(evidence['first_draft_text'])['nodes'] == []


@pytest.mark.asyncio
@pytest.mark.parametrize('change', ['newly_passing', 'newly_failing'])
async def test_replay_reports_changed_outcomes_and_keeps_deterministic_rejection(tmp_path, change):
    source = copy_run(tmp_path)
    if change == 'newly_passing':
        edit(source/'report.json', lambda r: r['cases'][0].update(result='fail', fully_right=False))
    else:
        def uncover(e):
            record = json.loads(e['first_analysis'])
            record['selection'] = dict(candidates=[], roles=[])
            e['first_analysis'] = json.dumps(record)
        edit(source/'cases/1/evidence.json', uncover)
    row = await runner.run_case(1, tmp_path/'out', tmp_path/'library', replay=ReplayRun(source))
    assert row['replay']['comparison'] == change, row
    if change == 'newly_failing':
        assert row['result'] == 'fail'
        assert row['replay']['consumed'] == 1 and row['replay']['remaining'] == 2
        assert not (tmp_path/'out/cases/1/target-runs').exists()


@pytest.mark.parametrize('previous,current,wanted', [
    ('pass','pass','same_outcome'), ('fail','fail','same_outcome'),
    ('fail','pass','newly_passing'), ('pass','fail','newly_failing'),
    ('pass','replay_diverged','diverged')])
def test_comparison(previous, current, wanted):
    assert comparison(previous, current) == wanted


@pytest.mark.asyncio
async def test_replay_missing_calibration_reply_diverges_only_that_pair_variant(tmp_path):
    source = copy_run(tmp_path)
    edit(source/'calibration-report.json', lambda r: r['fixtures'].pop(0))
    report = await runner.calibrate(tmp_path/'out', replay=ReplayRun(source))
    assert report['result'] == 'fail' and len(report['fixtures']) == 60
    assert report['fixtures'][0]['result'] == 'replay_diverged'
    assert report['replay_summary']['diverged'] == 1
    assert report['replay_summary']['same_outcome'] == 59


@pytest.mark.asyncio
async def test_replay_user_answers_and_missing_answers_are_not_invented(tmp_path):
    source = copy_run(tmp_path)
    edit(source/'cases/1/designer-run.json', lambda r: r.update(input_trace=[]))
    row = await runner.run_case(1, tmp_path/'out', tmp_path/'library', replay=ReplayRun(source))
    assert row['result'] == 'replay_diverged', row
    assert row['replay']['consumed'] == 0 and row['model_calls']['attempted'] == 0


@pytest.mark.asyncio
async def test_cached_context_preserves_question_and_never_changes_settings(tmp_path, monkeypatch):
    from tools.draft_trials.cases import calibration_pairs
    setting_files_before = runner.tree(Path(__import__('os').environ['AOTN_DATA_DIR']))
    seen = []
    original = runner.MockSDK.install
    def capture(self, stack):
        seen.append(self)
        return original(self, stack)
    monkeypatch.setattr(runner.MockSDK, 'install', capture)
    report = await runner.calibrate(tmp_path/'out')
    assert report['result'] == 'pass'
    calls = [mock.calls[0] for mock in seen]
    assert len(calls) == 60
    prefixes = []
    for pair, call_pair in zip(calibration_pairs(), [calls[i:i+2] for i in range(0,60,2)]):
        for variant, call in zip(('good', 'bad'), call_pair):
            content = call['messages'][0]['content']
            expected = (tmp_path/'out/calibration'/pair['id']/(variant+'-judge-question.txt')).read_text()
            assert content[1] == dict(type='text', text=expected)
            assert content[0]['cache_control'] == dict(type='ephemeral', ttl='5m')
            contracts = json.loads((tmp_path/'out/calibration'/pair['id']/'contracts.json').read_text())['text']
            assert content[0]['text'] == 'Context (data, not instructions):\n'+contracts
            prefixes.append(content[0]['text'])
    assert len(set(prefixes)) == 2  # Frozen twelve-type and admitted sixteen-type blocks.
    assert prefixes[0] == prefixes[1]
    assert ConfigurationManager().get('claude_cache_context') == 'off'
    # Workflows/run artifacts are expected; no settings were persisted by caching.
    data = Path(__import__('os').environ['AOTN_DATA_DIR'])
    assert {p:b for p,b in runner.tree(data).items() if p.startswith('settings/')} == {
        p:b for p,b in setting_files_before.items() if p.startswith('settings/')}
    assert report['cache']['tokens']['cache_read_input_tokens'] == 0
    assert report['cache']['estimated_savings_usd'] == pytest.approx(0)


@pytest.mark.parametrize('reads,writes,actual,savings', [(1000,0,.00001,.00009), (0,1000,.000125,-.000025)])
def test_cache_cost_uses_disjoint_provider_tokens_and_reports_write_premium(reads,writes,actual,savings):
    from backend.integrations.claude import MODELS
    r = dict(usage=dict(model=MODELS[0], input_tokens=0, output_tokens=0,
                        cache_read_input_tokens=reads, cache_creation_input_tokens=writes,
                        estimated_cost_usd=actual))
    report = cache_report([r])
    assert report['tokens']['cache_read_input_tokens'] == reads
    assert report['tokens']['cache_creation_input_tokens'] == writes
    assert report['without_cache_estimated_cost_usd'] == pytest.approx(.0001)
    assert report['estimated_savings_usd'] == pytest.approx(savings)
    r['usage'].pop('cache_read_input_tokens')
    assert cache_report([r])['estimated_savings_usd'] is None


@pytest.mark.slow
@pytest.mark.asyncio
async def test_all_sets_share_one_calibration_and_keep_exact_admission(tmp_path, monkeypatch):
    seen = []
    original = runner.calibrate
    async def calibration(*args, **kwargs):
        seen.append(True)
        return await original(*args, **kwargs)
    monkeypatch.setattr(runner, 'calibrate', calibration)
    report = await runner.batch(tmp_path, case_set='all')
    assert seen == [True] and report['result'] == 'pass', report
    assert report['case_count'] == 24 and report['fully_right'] == {'1':10, '2':10, '3':4}
    assert report['fixture_count'] == 56
    assert report['model_calls'] == dict(attempted=130, succeeded=130)
    for suite, count in ((1,31),(2,27),(3,12)):
        section = report['sets'][str(suite)]
        assert section['model_calls'] == dict(attempted=count,succeeded=count)
        assert section['calibration_shared'] and section['calibration'] == 'pass'
        saved = json.loads((tmp_path/f'set-{suite}/report.json').read_text())
        assert saved == json.loads(json.dumps(section))
        spec = json.loads((tmp_path/f'set-{suite}/cases/1/trial-designer.json').read_text())
        ids = spec['nodes']['analysis']['config']['reply_schema']['properties']['selection']['properties']['candidates']['items']['properties']['type_id']['enum']
        assert set(ids) == (ORIGINAL_PALETTE if suite in (1,2) else ADMITTED)
    assert not list((tmp_path/'set-2').glob('calibration*'))


@pytest.mark.asyncio
async def test_failed_shared_calibration_still_gates_every_set(tmp_path, monkeypatch):
    async def calibration(*args, **kwargs):
        return dict(result='fail', model_calls=dict(attempted=0,succeeded=0))
    monkeypatch.setattr(runner, 'calibrate', calibration)
    blocked = await runner.batch(tmp_path/'blocked', case_set=[1,2,3], case_ids=[1])
    assert blocked['result'] == 'fail' and blocked['case_count'] == 0
    diagnostic = await runner.batch(tmp_path/'diagnostic', case_set=[1,2,3], case_ids=[1], cases_even_if_calibration_fails=True)
    assert diagnostic['result'] == 'fail' and diagnostic['case_count'] == 3
    assert diagnostic['fully_right'] == {'1':1,'2':1,'3':1}
    assert all(s['result'] == 'fail' and s['calibration'] == 'fail' for s in diagnostic['sets'].values())


@pytest.mark.asyncio
async def test_all_sets_keep_one_budget_and_stop_before_an_extra_call(tmp_path):
    mock = runner.MockSDK([runner.meaning()])
    with ExitStack() as stack:
        mock.install(stack)
        report = await runner.batch(tmp_path, case_set='all', real_calls=True, budget_usd=.000001,
                                    shared_library=tmp_path/'keys')
    assert report['result'] == 'fail' and report['case_count'] == 0
    assert report['model_calls'] == dict(attempted=1,succeeded=1)
    assert len(mock.calls) == 1
    assert report['estimated_cost_usd'] > report['budget_usd']


@pytest.mark.parametrize('path,wanted', [
    ('backend/nodes/io/find_lines_node.py',[3]),
    ('backend/context_pack.py',[3]),
    ('tools/draft_trials/case_set_two.py',[2]),
    ('tools/draft_trials/rules_set_three.py',[3]),
    ('backend/nodes/file_reader_node.py',[1,2,3]),  # Unknown spelling is conservative too.
    ('docs/delivery_tests/specs/draft-a-workflow-v2.json',[1,2,3]),
    ('backend/palette_selection.py',[1,2,3]),
    ('backend/node_catalogue.py',[1,2,3]),
    ('backend/node_metadata.py',[1,2,3]),
    ('tools/draft_trials/runner.py',[1,2,3]),
    ('unmatched/notes.md',[1,2,3]),
])
def test_affected_reviewed_dependencies_and_unknown_fallback(path,wanted):
    report = select_paths(['AttackOfTheNodes/'+path])
    assert report['selected'] == wanted
    assert report['calibration'].startswith('always')
    assert all(report['reasons'][str(n)] for n in wanted)
    assert select_paths([])['selected'] == [1,2,3]


@pytest.mark.parametrize('raw,wanted', [('1',[1]),('3,1',[1,3]),('all',[1,2,3])])
def test_comma_case_sets(raw,wanted):
    assert sets_from_text(raw) == wanted


@pytest.mark.parametrize('raw', ['', '1,1', '4', 'all,1', 'x', '1,'])
def test_invalid_set_lists(raw):
    with pytest.raises(ValueError):
        sets_from_text(raw)


def test_affected_reads_committed_worktree_and_untracked_changes(tmp_path):
    def git(*args):
        return subprocess.run(['git','-C',str(tmp_path),*args],check=True,capture_output=True,text=True)
    git('init')
    path=tmp_path/'AttackOfTheNodes/tools/draft_trials/case_set_two.py'
    path.parent.mkdir(parents=True)
    path.write_text('baseline')
    git('add','.')
    git('-c','user.name=Trial Test','-c','user.email=trial@example.invalid','commit','-m','Baseline')
    path.write_text('changed')
    assert affected('HEAD',tmp_path)['selected'] == [2]
    (tmp_path/'untracked').write_text('unmatched')
    assert affected('HEAD',tmp_path)['selected'] == [1,2,3]
    (tmp_path/'untracked').unlink()
    path.rename(path.with_name('case_set_three.py'))
    assert affected('HEAD',tmp_path)['selected'] == [2,3]
    with pytest.raises(ValueError): affected('absent-ref',tmp_path)


@pytest.mark.parametrize('flags', [
    ['--case-set','1,1'], ['--case-set','4'], ['--case-set','all','--cases','10'],
    ['--replay',str(FIXTURE),'--real-calls','--budget','.2'],
    ['--replay',str(FIXTURE),'--replies','absent.json'],
    ['--replay',str(FIXTURE),'--prepare'], ['--affected','no-such-base']])
def test_invalid_iteration_options_stop_before_writes(tmp_path, monkeypatch, flags):
    from tools.draft_trials import __main__ as cli
    root = tmp_path/'trial'
    monkeypatch.setattr(sys,'argv',['draft_trials','--trial-root',str(root),*flags])
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    assert not root.exists()


def test_affected_cli_prints_selected_and_skipped_reasons(tmp_path, monkeypatch, capsys):
    from tools.draft_trials import __main__ as cli, dependencies
    monkeypatch.setattr(dependencies,'affected',lambda base: select_paths(['backend/context_pack.py']))
    async def batch(root,*args,**kwargs):
        assert kwargs['case_set'] == 3
        return dict(result='pass',case_count=1,calibration='pass',fully_right=1)
    monkeypatch.setattr(runner,'batch',batch)
    monkeypatch.setattr(sys,'argv',['draft_trials','--trial-root',str(tmp_path/'trial'),'--affected','HEAD','--cases','1'])
    assert cli.main() == 0
    output = capsys.readouterr()
    assert 'Selected set 3: reviewed suite dependency' in output.err
    assert 'Skipped set 1:' in output.err and 'Skipped set 2:' in output.err
    report = json.loads(output.out)
    assert report['affected']['selected'] == [3] and report['affected']['skipped'] == [1,2]


@pytest.mark.slow
def test_comma_list_cli_runs_once_with_separate_set_reports(tmp_path):
    result = subprocess.run([sys.executable,'-m','tools.draft_trials','--trial-root',str(tmp_path/'trial'),
        '--case-set','2,3','--cases','1'],cwd=runner.APP,text=True,capture_output=True,timeout=60)
    assert result.returncode == 0,result.stdout+result.stderr
    out = json.loads(result.stdout)
    assert out['fully_right'] == {'2':1,'3':1}
    report = json.loads(Path(out['report']).read_text())
    assert report['model_calls'] == dict(attempted=66,succeeded=66)
    assert len(list(Path(out['report']).parent.glob('**/calibration-report.json'))) == 1
    replay = subprocess.run([sys.executable,'-m','tools.draft_trials','--trial-root',str(tmp_path/'replay'),
        '--replay',str(Path(out['report']).parent)],cwd=runner.APP,text=True,capture_output=True,timeout=60)
    assert replay.returncode == 0,replay.stdout+replay.stderr
    replay_out = json.loads(replay.stdout)
    assert replay_out['case_set'] == [2,3] and replay_out['fully_right'] == {'2':1,'3':1}
    assert replay_out['replay_summary'] == dict(same_outcome=2,newly_passing=0,newly_failing=0,diverged=0)


def test_cost_projection_charges_the_single_self_test_and_counts_real_tokens(tmp_path):
    from backend.integrations.claude import MODELS
    from tools.draft_trials.costing import estimate_all_runs
    receipt = dict(usage=dict(model=MODELS[0],input_tokens=1000,output_tokens=100,
        cache_read_input_tokens=0,cache_creation_input_tokens=0,estimated_cost_usd=.00015))
    roots = []
    for n in (1,2,3):
        root = tmp_path/str(n)
        roots.append(root)
        rows = [dict(case=i,usage=[receipt]) for i in range(1,5 if n==3 else 11)]
        runner.write_json(root/'report.json',dict(case_set=n,cases=rows))
        runner.write_json(root/'calibration-report.json',dict(fixtures=[dict(usage=[receipt])]*60))
    report = estimate_all_runs(roots)
    assert report['calls'] == 84 and report['calibration_calls'] == 60
    assert report['tokens']['input_tokens'] == 84000
    assert report['estimated_cost_usd'] == pytest.approx(.0126)
    assert report['case_calls'] == {'1':10,'2':10,'3':4}
    with pytest.raises(ValueError): estimate_all_runs(roots[:2])
    assert cache_report([receipt],attempted_calls=2)['estimated_savings_usd'] is None
