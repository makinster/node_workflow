"""Review harness: merge Python sources in memory; never alter application files.
Run from AttackOfTheNodes with ../.venv/bin/python docs/audits/file_output_2026_10_06/check_integration.py.
This tests a source overlay, not a checked-out or installed integration build.
"""
import importlib.abc, importlib.util, json, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
APP = ROOT / 'AttackOfTheNodes'
REF = 'origin/claude/file-output-pywin32-32tnv9'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)
def blob(ref, path):
    p = subprocess.run(['git', 'show', f'{ref}:{path}'], cwd=ROOT, capture_output=True)
    return p.stdout if p.returncode == 0 else None
base = git('merge-base', 'HEAD', REF).decode().strip()
changed = git('diff', '--name-only', base, REF).decode().splitlines()
sources = {}
conflicts = []
class Overlay(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in sources:
            source, filename, package = sources[fullname]
            spec = importlib.util.spec_from_loader(fullname, self, origin=str(filename), is_package=package)
            spec.has_location = True
            if package: spec.submodule_search_locations = [str(filename.parent)]
            return spec
    def create_module(self, spec): return None
    def exec_module(self, module):
        source, filename, _ = sources[module.__name__]
        exec(compile(source, str(filename), 'exec'), module.__dict__)
with tempfile.TemporaryDirectory(prefix='aotn-file-output-review-') as scratch:
    scratch = Path(scratch)
    (scratch/'frontend').symlink_to(APP/'frontend', target_is_directory=True)
    test_paths = []
    for path in changed:
        if not path.endswith('.py') or not path.startswith('AttackOfTheNodes/'): continue
        remote = blob(REF, path)
        if remote is None: continue
        original = blob(base, path)
        local = ROOT / path
        source = remote
        if original is not None and local.exists():
            for name, contents in [('local', local.read_bytes()), ('base', original), ('remote', remote)]:
                (scratch/name).write_bytes(contents)
            result = subprocess.run(['git', 'merge-file', '-p', str(scratch/'local'), str(scratch/'base'), str(scratch/'remote')], capture_output=True)
            if result.returncode: conflicts.append(path); continue
            source = result.stdout
        relative = Path(path).relative_to('AttackOfTheNodes')
        if relative.parts[0] == 'tests':
            target = scratch / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source)
            test_paths.append(str(target))
        elif relative.parts[0] in ('backend', 'frontend'):
            package = relative.name == '__init__.py'
            mod = '.'.join(relative.with_suffix('').parts[:-1] if package else relative.with_suffix('').parts)
            sources[mod] = (source, local, package)
    print('BASE', base, 'FEATURE', git('rev-parse', REF).decode().strip(), flush=True)
    print('PYTHON_MERGE_CONFLICTS', conflicts, flush=True)
    if conflicts: raise SystemExit(2)
    sys.path[:0] = [str(APP), str(ROOT)]
    sys.meta_path.insert(0, Overlay())
    # Feature tests + existing pending Wait Until regressions, on combined sources.
    import pytest
    code = pytest.main(['-q', '-c', str(APP/'pytest.ini'), '--import-mode=importlib', *test_paths,
        str(APP/'tests/test_wait_until_ui.py'), str(APP/'tests/test_wait_until_vault.py')])
    print('OVERLAY_TEST_EXIT', code, flush=True)
    # Deterministic reproduction: ambiguous window discovery must not select a random HWND.
    from backend.window_manager import WindowsWindowManager
    manager = WindowsWindowManager.__new__(WindowsWindowManager)
    manager._snapshot_windows = lambda: {101, 202}
    manager._match_by_title = lambda *args: None
    print('AMBIGUOUS_WINDOW_RESULT', manager._discover_window('/tmp/wanted.txt', set()), flush=True)
    # Production-CSS screen mounts and actual shared controls for the incoming nodes.
    sys.path.insert(0, str(APP/'docs/audits/node_config_2026_10_06'))
    from capture import Harness, NodeFactory, NodeConfigScreen, setup, Secrets, tabs_snapshot
    import asyncio
    async def mounts():
        factory = NodeFactory(); result = {'registry_count':len(factory.get_node_types_metadata()), 'screens':[]}
        for typ in ['file_output_node','file_view_node','window_control_node']:
            for width in (60,100,140):
                wm,nid,mem = setup(factory,typ)
                screen=NodeConfigScreen(factory,wm,nid,wm.get_node_data(nid),mem,Secrets())
                async with Harness(screen,[]).run_test(size=(width,24)) as pilot:
                    await pilot.pause(.05)
                    result['screens'].append({'type':typ,'width':width,'tabs':await tabs_snapshot(screen,pilot)})
        (Path(__file__).parent/'mounted.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
        print('PRODUCTION_CSS_MOUNTS',len(result['screens']),'REGISTRY_COUNT',result['registry_count'],flush=True)
    asyncio.run(mounts())
    raise SystemExit(int(code))
