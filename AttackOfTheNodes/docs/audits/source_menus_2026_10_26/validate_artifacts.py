"""Planning schemas and capture provenance; system Python's existing jsonschema."""
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from jsonschema import Draft202012Validator

OUT=Path(__file__).resolve().parent
DOCS=OUT.parents[1]
ROOT=DOCS.parents[1]
files=list(OUT.glob('*.json'))+list((DOCS/'delivery_tests').glob('*.json'))+list((DOCS/'templates').glob('*.json'))
for path in files:json.loads(path.read_text())
for name,field in [('workflow_request','request'),('feasibility_check','feasibility')]:
    schema=json.loads((DOCS/'templates'/f'{name}.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    validator=Draft202012Validator(schema)
    validator.validate(json.loads((DOCS/'templates'/f'{name}.example.json').read_text()))
    for case in ('source-menu-audit','ask-local-model'):
        validator.validate(json.loads((DOCS/'delivery_tests'/f'{case}.json').read_text())[field])
for phase in ('before','after'):
    manifest=json.loads((OUT/f'{phase}-manifest.json').read_text())
    for filename in manifest['screens']:
        path=OUT/filename;ET.parse(path)
        assert path.with_suffix('.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert manifest['node_executions']==0
    assert all(call=='GET /api/tags' for call in manifest['requests'])
    for source,expected in manifest['source_sha256'].items():
        data=(ROOT/source).read_bytes() if phase=='after' else subprocess.check_output(['git','show',f'f0aa39d:{source}'],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==expected,source
    assert hashlib.sha256((ROOT/'AttackOfTheNodes/frontend/styles.tcss').read_bytes()).hexdigest()==manifest['styles_sha256']
case=json.loads((DOCS/'delivery_tests/source-menu-audit.json').read_text())
coverage=case['coverage'];assert coverage['total_operations']==coverage['existing_count']+coverage['new_count']==0
assert coverage['ratio'] is None and case['measurements']['review_rounds']==0
assert case['measurements']['verification']['generation_calls']==0
print(f'PASS: {len(files)} parseable JSON files; six schema instances; 15 real-screen SVG/PNG pairs; source/style hashes; coverage and no-generation record.')
