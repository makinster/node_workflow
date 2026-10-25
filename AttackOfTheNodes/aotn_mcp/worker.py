"""One tool call per interpreter: isolates backend singletons and blocking nodes."""
import asyncio
import json
import logging
import os
import sys


def dispatch(name, args):
    # The launcher sets AOTN_DATA_DIR before this process imports any backend.
    from backend import persistence, saved_values
    from backend.contracts import call_contract

    saved_values.RUN_FROM = 'MCP'  # shown with each saved value (C2)

    if name == 'get_activity':
        from .activity import get_activity
        return {'result': get_activity(**args)}
    if name == 'get_run_status':
        history = persistence.RUN_HISTORY_DIR.resolve()
        if not (history / (args['run_id'] + '.json')).resolve().is_relative_to(history):
            raise ValueError('run summary resolves outside run history')
        record = persistence.load_json_record(persistence.RUN_HISTORY_DIR, args['run_id'])
        if record is None:
            raise ValueError('run not found in history')
        if not isinstance(record, dict):
            raise ValueError('invalid run-history summary')
        return {'result': {'run': record}}
    if name == 'get_recent_events':
        from backend.event_bus import EventBus
        from backend.run_history import RunHistory
        history = persistence.RUN_HISTORY_DIR.resolve()
        if any(not path.resolve().is_relative_to(history) for path in history.glob('*.json')):
            raise ValueError('run summary resolves outside run history')
        return {'result': {'runs': RunHistory(EventBus()).list_runs()[:args.get('limit', 10)]}}

    library = persistence.WORKFLOWS_DIR.resolve()
    if any(not path.resolve().is_relative_to(library) for path in library.glob('*.json')):
        raise ValueError('saved workflow resolves outside the configured library')
    catalog = persistence.list_workflows()
    by_id = {item['id']: item for item in catalog}

    def saved(identifier):
        if identifier not in by_id:
            return None
        path = library / (identifier + '.json')
        if not path.resolve().is_relative_to(library):
            raise ValueError('saved workflow resolves outside the configured library')
        return persistence.load_workflow(identifier)

    if name == 'list_workflows':
        return {'result': {'workflows': [
            {'id': item['id'], **call_contract(saved(item['id']), saved)} for item in catalog
        ]}}

    reference = args['name_or_id'].strip()
    matches = [by_id[reference]] if reference in by_id else [
        item for item in catalog if item['name'].casefold() == reference.casefold()]
    if len(matches) > 1:
        standard = [item for item in matches if not item.get('callable')]
        if len(standard) == 1:
            matches = standard
    if len(matches) != 1:
        raise ValueError('saved workflow not found or name ambiguous; use a saved ID')
    data = saved(matches[0]['id'])
    contract = call_contract(data, saved)
    if contract['asks']:
        raise ValueError('unattended workflow may ask for input (C25): ' + ', '.join(contract['asks']))
    return {'result': asyncio.run(run(data, args.get('inputs', {}))), 'run': True}


async def run(data, supplied):
    from backend.contracts import ContractInputError, ContractError, parse_text, resolve_inputs, start_rows
    from backend.run_service import RunService, WorkflowValidationError
    from backend.run_policies import unattended_policies
    from backend.stash_manager import StashManager, input_value, stash_ref_name

    service = RunService.create()
    try:
        service.workflow_map.load_data(data)  # Saved catalog only; no file-path resolution.
        start = service.workflow_map.find_start_node_id()
        rows = start_rows((service.workflow_map.get_node_data(start) or {}).get('config') or {})
        types = {row['name']: row['type'] for row in rows}
        inputs = dict(supplied)
        for name, value in supplied.items():
            entry_name = stash_ref_name(value)
            if entry_name is not None:
                entry = StashManager().get_by_name(entry_name) if entry_name else None
                if entry is None:
                    raise ContractInputError([], {name: f'no Stash entry "{entry_name}"'}, [])
                raw = input_value(entry)
                try:
                    inputs[name] = parse_text(types[name], raw) if name in types else raw
                except ContractError as exc:
                    raise ContractInputError([], {name: str(exc)}, []) from exc
        resolve_inputs(rows, inputs, strict=bool(data.get('callable')))
        recovery, provider = unattended_policies('terminate_workflow')
        await service.start(inputs=inputs, recovery_policy=recovery, input_provider=provider)
        return (await service.wait()).to_dict()
    except (ContractInputError, WorkflowValidationError, RuntimeError) as exc:
        return {'run_id': None, 'final_state': 'NOT_STARTED',
                'exit_code': 5 if isinstance(exc, ContractInputError) else 3,
                'outputs': [], 'values': {}, 'errors': [{'message': str(exc)}]}
    finally:
        service.close()


def main():
    # Keep a private report FD; even incidental print()/native stdout goes to
    # stderr, never into the worker report or the parent's MCP protocol stream.
    reply = os.fdopen(os.dup(1), 'w', encoding='utf-8')
    sys.stdout.flush()
    os.dup2(2, 1)
    logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
    try:
        request = json.load(sys.stdin)
        payload = dispatch(request['name'], request['arguments'])
    except Exception as exc:
        logging.exception('MCP tool worker failed')
        payload = {'error': str(exc)}
    with reply:
        json.dump(payload, reply, ensure_ascii=True, allow_nan=False)
        reply.write('\n')


if __name__ == '__main__':
    main()
