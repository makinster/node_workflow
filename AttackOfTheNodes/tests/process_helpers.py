"""Disposable subprocess launchers; production argv/env cannot shorten cleanup."""
import sys

# Mirrors the installed runpy protocol, shortening only tests' cleanup reserve.
SHORT_CLEANUP = '''import runpy,sys
original=runpy.run_path
def loaded(path,*args,**kwargs):
 namespace=original(path,*args,**kwargs)
 if str(path).endswith('_aotn_run.py'):
  namespace['collect'].__globals__.update(GRACE=.2,CLEANUP_WAIT=.05)
 return namespace
runpy.run_path=loaded
'''


def short_broker(path):
    code = SHORT_CLEANUP + "module=original(sys.argv[1]);sys.exit(module['main']())\n"
    return [sys.executable, '-I', '-S', '-u', '-c', code, str(path)]
