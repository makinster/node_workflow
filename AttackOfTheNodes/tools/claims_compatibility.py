"""Read-only compatibility inventory for authored bundled/delivery specs."""
import json
from pathlib import Path

from backend.authoring import check_workflow_spec


def workflow_specs(value, pointer=''):
    if isinstance(value,dict):
        if value.get('format')=='aotn-workflow/1' and isinstance(value.get('nodes'),dict):
            yield pointer,value
        for key,child in value.items():
            yield from workflow_specs(child,pointer+'/'+key.replace('~','~0').replace('/','~1'))
    elif isinstance(value,list):
        for index,child in enumerate(value):
            yield from workflow_specs(child,pointer+'/'+str(index))


def audit(factory,root):
    specs=[]
    for directory in ('examples','docs/delivery_tests'):
        for path in sorted((Path(root)/directory).rglob('*.json')):
            value=json.loads(path.read_text())
            for pointer,spec in workflow_specs(value):
                result=check_workflow_spec(factory,spec)
                errors=[d for d in result['diagnostics'] if d['code']=='unsupported_standard_flag']
                specs.append(dict(path=path.relative_to(root).as_posix(),pointer=pointer,new_flag_errors=errors))
    return dict(roots=['examples','docs/delivery_tests'],spec_count=len(specs),
                newly_failing_specs=sum(bool(s['new_flag_errors']) for s in specs),specs=specs,
                owner_workflows_scanned=False,
                policy='Reject explicit unsupported flags including false/empty; saved workflow loading is unchanged.')
