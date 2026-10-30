"""Read saved replies only; missing evidence is divergence, never a canned answer."""
from copy import deepcopy
import json
from pathlib import Path

STAGES = {'analysis': 'first_analysis', 'resolve': 'resolved_analysis',
          'draft': 'draft_text', 'draft_retry': 'draft_text', 'judge': 'judge_text'}
COMPARISONS = ('same_outcome', 'newly_passing', 'newly_failing', 'diverged')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def relocate(value, old_root, new_root):
    """Only relocate this case's fixture root, including paths inside raw JSON."""
    if isinstance(value, str):
        return value.replace(old_root, str(new_root))
    if isinstance(value, list):
        return [relocate(v, old_root, new_root) for v in value]
    if isinstance(value, dict):
        return {k: relocate(v, old_root, new_root) for k, v in value.items()}
    return value


def comparison(previous, current):
    if current == 'replay_diverged':
        return 'diverged'
    was, now = previous == 'pass', current == 'pass'
    return 'same_outcome' if was == now else 'newly_passing' if now else 'newly_failing'


def counts(rows):
    return {key: sum(r.get('replay', {}).get('comparison') == key for r in rows) for key in COMPARISONS}


class ReplayTape:
    def __init__(self, entries, *, source, previous='not_run', unavailable=None):
        self.entries = deepcopy(entries)
        self.source = str(source)
        self.previous = previous
        self.index = 0
        self.stage = None
        self.failure = None
        self.unavailable = unavailable
        self.answers = None

    def observe(self, stage):
        self.stage = stage

    def pop(self):
        entry = self.entries[self.index] if self.index < len(self.entries) else None
        if entry is None or entry['stage'] != self.stage or entry.get('reply') is None:
            wanted = entry['stage'] if entry else 'no further saved reply'
            self.failure = (f'replay_diverged: current call {self.stage}; saved {wanted}. '
                            + (self.unavailable or 'No reply was invented.'))
            raise ValueError(self.failure)
        self.index += 1
        return entry['reply']

    def report(self, result):
        return dict(source=self.source, previous_result=self.previous, current_result=result,
                    comparison=comparison(self.previous, result), available=len(self.entries),
                    consumed=self.index, remaining=len(self.entries)-self.index, divergence=self.failure)


class ReplayRun:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.report = read(self.root/'report.json')
        if not isinstance(self.report, dict):
            raise ValueError('Replay needs a saved run report object.')
        self.sections = self.report.get('sets') or {str(self.report.get('case_set', 1)): self.report}
        if not isinstance(self.sections, dict) or not self.sections or any(str(k) not in ('1', '2', '3') for k in self.sections):
            raise ValueError('Replay report has no recognized case sets.')
        try:
            calibration = read(self.root/'calibration-report.json')
            self.judges = {(r['fixture'], r['variant']): r for r in calibration['fixtures']}
        except (OSError, ValueError, KeyError, TypeError):
            self.judges = {}

    @property
    def sets(self):
        return sorted(int(n) for n in self.sections)

    def case_ids(self, case_set):
        return [r['case'] for r in self.sections.get(str(case_set), {}).get('cases', [])]

    def case(self, case_set, number, new_root):
        section = self.sections.get(str(case_set), {})
        baseline = next((r for r in section.get('cases', []) if r['case'] == number), {})
        directory = self.root/(f'set-{case_set}' if self.report.get('sets') else '')/'cases'/str(number)
        entries, unavailable = [], None
        answers = None
        try:
            evidence = read(directory/'evidence.json')
            run = read(directory/'designer-run.json')
            frozen = read(directory/'frozen-case.json')
            old_root = frozen['root']
            if not isinstance(old_root, str) or not old_root:
                raise ValueError('Missing original fixture root')
            if isinstance(run.get('input_trace'), list):
                answers = [(relocate(row['prompt'], old_root, new_root), relocate(row['answer'], old_root, new_root))
                           for row in run['input_trace'] if row.get('answer') is not None]
            try:
                spec = read(directory/'trial-designer.json')
                ai = {h for h, n in spec['nodes'].items() if n['type'] == 'ask_claude_node'}
            except FileNotFoundError:
                ai = set(STAGES)
            order = [s['handle'] for s in run['steps'] if s['status'] == 'running' and s['handle'] in ai]
            for stage in order:
                key = STAGES.get(stage)
                if stage == 'draft' and 'draft_retry' in order:
                    key = 'first_draft_text'  # The final draft overwrites draft_text.
                raw = evidence.get(key)
                # Refused/capped/missing replies have no published text: never synthesize them.
                if not isinstance(raw, str):
                    raw = json.dumps(raw, ensure_ascii=False) if isinstance(raw, (dict, list)) else None
                entries.append(dict(stage=stage, reply=relocate(raw, old_root, new_root)))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            unavailable = 'Saved case evidence unavailable: ' + type(exc).__name__
        tape = ReplayTape(entries, source=directory, previous=baseline.get('result', 'not_run'), unavailable=unavailable)
        tape.answers = answers
        return tape

    def judge(self, pair, variant):
        row = self.judges.get((pair, variant), {})
        raw = row.get('judge_reply')
        # Keep invalid saved answers literal, but never pretend that a bounded
        # prefix or an omission notice is a complete original answer.
        if isinstance(raw, dict):
            raw = json.dumps(raw, ensure_ascii=False)
        elif isinstance(raw, str):
            try:
                json.loads(raw)
            except ValueError:
                if len(raw) >= 4000 or not raw or raw.startswith('[reply omitted:'):
                    raw = None
        return ReplayTape([dict(stage='judge', reply=raw if isinstance(raw, str) else None)],
                          source=self.root/'calibration'/pair/variant,
                          previous=row.get('result', 'not_run'))
