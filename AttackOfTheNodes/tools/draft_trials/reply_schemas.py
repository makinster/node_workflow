"""Generate closed v2 reply schemas from the live admission/role vocabulary.

Run with --write from the app directory to refresh the checked-in v2 spec.
The workflow-spec step stays on reply_json: dynamic handles and heterogeneous
node configs cannot use additionalProperties:false without changing its format.
"""
import json
from pathlib import Path

from backend.palette_selection import ADMITTED, ROLE_TYPES, MAX_IDS


def obj(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def text(**constraints):
    return dict(type='string', **constraints)


def array(items, **constraints):
    return dict(type='array', items=items, **constraints)


def analysis_schema(admitted=ADMITTED):
    role = text(enum=sorted(ROLE_TYPES))
    req_ids = array(text(minLength=1), minItems=1)
    reason = text(minLength=1, maxLength=512)
    role_row = dict(role=role, requirement_ids=req_ids, reason=reason)
    # Property order is generation order: reasoning first, the decision last.
    return obj(dict(
        requirements=array(obj(dict(id=text(minLength=1), action=text(minLength=1),
            source=text(minLength=1), destination=text(minLength=1),
            order=dict(anyOf=[dict(type='integer'), text(minLength=1)]), acceptance=text(minLength=1)))),
        questions=text(), assumptions=array(text()), reason=text(),
        selection=obj(dict(candidates=array(obj(dict(type_id=text(enum=sorted(admitted)), **role_row)), maxItems=MAX_IDS),
                           roles=array(obj(role_row), maxItems=32))),
        status=text(enum=['ready', 'clarify', 'outside_scope', 'needs_new_node'])))


def judge_schema():
    # A verdict written before its evidence anchors the review; keep it last.
    # Remarks precede problems so non-blocking notes have their own place.
    return obj(dict(
        coverage=array(obj(dict(requirement_id=text(minLength=1), evidence=text(minLength=1), met=dict(type='boolean')))),
        remarks=array(text()), problems=array(text()), summary=text(),
        verdict=text(enum=['pass', 'fail', 'unsure'])))


def install(spec, admitted=ADMITTED):
    for ai, gate in [('analysis', 'analysis_shape'), ('resolve', 'resolved_shape'), ('judge', 'judge_shape')]:
        schema = judge_schema() if ai == 'judge' else analysis_schema(admitted)
        spec['nodes'][ai]['config']['reply_schema'] = schema
        spec['nodes'][gate]['config']['reply_schema'] = schema
    return spec


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', required=True)
    parser.parse_args()
    path = Path(__file__).parents[2]/'docs/delivery_tests/specs/draft-a-workflow-v2.json'
    path.write_text(json.dumps(install(json.loads(path.read_text())), indent=2, ensure_ascii=False)+'\n')
