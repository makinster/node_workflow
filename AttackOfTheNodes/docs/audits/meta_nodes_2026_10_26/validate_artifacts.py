"""Check screenshots against current production sources, without running nodes."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
OUT=Path(__file__).resolve().parent
APP=OUT.parents[2]
manifest=json.loads((OUT/'manifest.json').read_text())
assert not manifest['design_only']
for name,expected in manifest['source_sha256'].items():
    assert hashlib.sha256((APP/name).read_bytes()).hexdigest()==expected,name
for record in manifest['screens']:
    svg=OUT/record['file'];ET.parse(svg)
    png=svg.with_suffix('.png')
    assert png.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    assert record['library_unchanged'] and record['config_preserved']
assert {tuple(r['size']) for r in manifest['screens']} >= {(80,24),(120,40)}
for name in ['workflow_library_writes','workflow_executions','generation_calls','network_calls']:
    assert manifest[name]==0
contracts=json.loads((OUT/'built-node-contracts.json').read_text())
assert contracts['registered_in_product'] and not contracts['design_only']
for p in OUT.glob('*.json'):json.loads(p.read_text())
print(f"{len(manifest['screens'])} SVG/PNG pairs, production hashes, no-write manifest and audit JSON: PASS")
