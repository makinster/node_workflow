"""Contained family oracle: actual local execute, independent expected fixtures.

No provider code or effects are admitted here. Graph validity/source typing use
shared authoring services. This probe is a contract stub, not a second engine;
target_fixtures separately proves delivery with the real engine.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from backend.authoring import check_workflow_spec
from backend.node_factory import NodeFactory
from .cases import fixture_variants
from .rules import NeedsReview, RuleFailure, effective_nodes, safe_path, allows_display_framing, display_outputs_match
from backend.palette_selection import ADMITTED

# Sequential local nodes execute directly. Parallel scheduling needs the real
# coordinator; file writes are forbidden by these read-only case outcomes.
LOCAL_EXECUTABLE = frozenset('start_node end_node branch_end_node user_text_input_node text_output_node text_transform_node file_reader_node conditional_node concat_node json_path_node find_lines_node read_lines_node check_reply_node context_pack_node'.split())

def safety(spec, case):
    from collections import defaultdict
    if spec.get('format') != 'aotn-workflow/1' or spec.get('callable') or len(spec.get('nodes', {})) > 32:
        raise RuleFailure('unsupported helper graph')
    nodes = effective_nodes(spec)
    out = defaultdict(list)
    for edge in spec['connections']:
        out[edge['from']].append(edge['to'])
    if any((len(v) != 1 for v in out.values())):
        raise RuleFailure('ordinary fan-out')
    unsupported = []
    for n in nodes.values():
        t, c = (n['type'], n['config'])
        if t not in ADMITTED:
            raise RuleFailure('outside admitted palette')
        if t not in LOCAL_EXECUTABLE:
            unsupported.append(t + ' needs execution review beyond this local probe.')
        if t == 'file_output_node':
            raise RuleFailure('Unrequested filesystem write in a read-only helper case.')
        if any((c.get(k) for k in ('membank_inputs', 'transient_outputs', 'node_errors', 'breakpoint', 'return_end'))):
            unsupported.append('Legacy routing/recovery or return modes need engine review.')
        if t == 'file_reader_node' and c['input_source'] != 'Configured':
            # Its configured path is inactive. Do not reject a valid wire or
            # Vault file reference by inspecting that unused field. The probe
            # does not yet map dynamic file identities into its temporary root.
            unsupported.append('Dynamic File Reader references need mapped-path review.')
        elif t in ('find_lines_node', 'read_lines_node', 'file_reader_node'):
            field = 'file_path' if t == 'file_reader_node' else 'file'
            if not case['reads'] or safe_path(c[field], case['root']) != Path(case['root']) / case['reads']:
                raise RuleFailure('wrong file or file outside trial library')
        if t == 'context_pack_node' and (c['include_run'] or c['include_errors']):
            raise RuleFailure('unrequested run/error context')
        if t == 'user_text_input_node' and case['id'] not in (2, 4):
            raise RuleFailure('extra runtime prompt')
    if unsupported:
        raise NeedsReview(' '.join(dict.fromkeys(unsupported)))
    return (nodes, out)

async def probe(spec, case, variant):
    from backend.node_base import NodeContext
    from backend.memory_bank import MemoryBank
    from backend.event_bus import EventBus
    from backend.run_snapshot import RunSnapshot
    nodes, out = safety(spec, case)
    factory = NodeFactory()

    class Inputs(dict):
        used = False

        def get(self, key, *args):
            if key == 'input':
                self.used = True
            return super().get(key, *args)

        def __getitem__(self, key):
            if key == 'input':
                self.used = True
            return super().__getitem__(key)

    class Memory(MemoryBank):

        def read_persistent(self, key, default=None):
            read_keys.add(key)
            return super().read_persistent(key, default)
        def store_persistent(self, key, value, type_tag=None):
            written_keys.add(key)
            return super().store_persistent(key,value,type_tag)
    read_keys = set()
    written_keys = set()
    vault_lineage = {}
    memory = Memory(EventBus())
    starts = [h for h, n in nodes.items() if n['type'] == 'start_node']
    if len(starts) != 1:
        raise RuleFailure('one Start required')
    answers = iter(variant['answers'])
    prompts = []
    outputs = []
    visits = []
    visited = []
    errors = []
    ends = []

    class NoSecrets:

        def list_keys(self):
            return []

        def get_secret(self, key):
            raise AssertionError('unexpected Secrets lookup')
    with TemporaryDirectory(prefix='helper-oracle-') as folder:
        root = Path(folder)
        for name, body in variant['files'].items():
            (root / name).write_text(body)
        h = starts[0]
        absent = object()
        payload = absent
        lineage = ()
        routes = ()
        for _ in range(64):
            if h in visited:
                raise RuleFailure('cycle')
            visited.append(h)
            visits.append(dict(handle=h, routes=routes, data_lineage=()))
            n = nodes[h]
            c = dict(n['config'])
            for key in ('file', 'file_path'):
                if c.get(key):
                    c[key] = str(root / Path(c[key]).name)
            node = factory.create_node(n['type'], h, c)
            done = []
            failed = []

            async def answer(prompt):
                prompts.append(prompt)
                try:
                    return next(answers)
                except StopIteration:
                    raise RuleFailure('extra runtime prompt') from None
            incoming = Inputs({} if payload is absent else {'input': payload})
            read_keys.clear()
            written_keys.clear()
            ctx = NodeContext(node_id=h, branch_id='local', run_id='fixed', workflow_name='Family probe', inputs=incoming, memory_bank=memory, signal_done=done.append, signal_error=failed.append, signal_waiting_for_input=answer, wait_for_nodes=lambda *_: None, wait_for_merge=lambda *_: None, secrets_manager=NoSecrets(), run_snapshot=RunSnapshot('2026-10-25T00:00:00+00:00'), get_setting=lambda key: str(root) if key == 'system_node_folders' else None)
            try:
                await asyncio.wait_for(node.execute(ctx), 2)
            except (RuleFailure, NeedsReview):
                raise
            except TimeoutError:
                raise NeedsReview('Local execution exceeded the probe time limit.') from None
            except Exception as exc:
                # The supervisor converts raised node exceptions into the same
                # error route as signal_error; the local probe must do so too.
                failed.append(exc)
            used = set(lineage if incoming.used else ())
            for key in read_keys:
                used.update(vault_lineage.get(key, ()))
            visits[-1]['data_lineage'] = tuple(sorted(used))
            lineage = tuple(sorted(used | {h}))
            for key in written_keys:
                vault_lineage[key] = lineage
            if n['type'] == 'end_node':
                ends.append(h)
                break
            if failed:
                if len(failed) != 1:
                    raise RuleFailure('multiple errors')
                exc = failed[0]
                errors.append(getattr(exc, 'code', 'node_error'))
                port = 'error'
                payload = dict(version=1, code=getattr(exc, 'code', 'node_error'), message=str(exc), details=getattr(exc, 'details', {}))
            else:
                if len(done) != 1:
                    raise RuleFailure('node did not complete')
                port = done[0].get('output_port', 'default')
                payload = done[0].get('data', {}).get(port, absent)
                transient = memory.get_state()['transient']
                if h + '__' + port in transient:
                    payload = transient[h + '__' + port]
            if n['type'] == 'text_output_node':
                from backend.output_entry import text_output_prefix
                outputs.append(dict(handle=h, body=str(payload).removeprefix(text_output_prefix(c['label'])), expression=('literal', payload) if '{input' not in c['template'] else ('computed', h)))
            if n['type'] == 'conditional_node' and not failed:
                routes += (dict(fork=h, port=port),)
            targets = out.get(h + '.' + port, [])
            if not targets:
                if failed:
                    break
                raise RuleFailure('path ends before End')
            h = targets[0].split('.')[0]
        else:
            raise RuleFailure('step limit')
        if list(answers):
            raise RuleFailure('missing prompt')
        return dict(outputs=outputs, writes=[], prompts=prompts, visited=visited, visits=visits, error=bool(errors), error_codes=errors, ends=ends)

def evaluate(spec, case, variant):
    # A bounded worker isolates asyncio.run from an orchestrator event loop.
    with ThreadPoolExecutor(max_workers=1) as worker:
        try:
            return worker.submit(lambda: asyncio.run(probe(spec, case, variant))).result(timeout=10)
        except TimeoutError:
            raise NeedsReview('The bounded composition probe exceeded its time limit.') from None

def check_rules(spec, case):
    rows = []

    def record(name, ok, evidence):
        rows.append(dict(id=f"3.{case['id']}.{name}", result='pass' if ok else 'fail', evidence=evidence))
    try:
        report = check_workflow_spec(NodeFactory(), spec)
        record('structure', report['ok'] and (not report['diagnostics']), report['diagnostics'])
        safety(spec, case)
        record('safety', True, 'Local read-only types; configured file paths confined to fixture directory')
        evaluated = []
        for variant in fixture_variants(case['id'], 3):
            result = evaluate(spec, case, variant)
            evaluated.append(result)
            record('semantics.' + variant['name'], display_outputs_match(result['outputs'], variant['outputs'], allows_display_framing(case)) and result['error_codes'] == variant['handled_errors'] and bool(result['ends']), result)
        from .structure_rules import check_required_structure
        shape = check_required_structure(spec, case['required_structure'], evaluated,
                                         allow_additional_conditionals=True)
        record('required_structure', shape['result'] == 'pass', shape)
    except NeedsReview as exc:
        rows.append(dict(id=f"3.{case['id']}.composition", result='needs_review', evidence=str(exc)))
    except (RuleFailure, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        record('evaluation', False, str(exc))
    result = ('fail' if not rows or any(r['result'] == 'fail' for r in rows) else
              'needs_review' if any(r['result'] == 'needs_review' for r in rows) else 'pass')
    return dict(result=result, rules=rows)
