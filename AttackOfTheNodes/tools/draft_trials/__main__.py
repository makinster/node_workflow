"""Explicit fresh root required; mock mode is the default."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial-root',type=Path,required=True)
    parser.add_argument('--real-calls',action='store_true',help='Step 2 only, after separate owner approval and key setup')
    parser.add_argument('--prepare',action='store_true',help='Create a fresh empty trial library for owner key setup, then stop')
    parser.add_argument('--calibrate-only',action='store_true')
    parser.add_argument('--cases',default='1,2,3,4,5,6,7,8,9,10')
    parser.add_argument('--scenario',choices=['ready','judge_fail','error','unhelpful'],default='ready')
    parser.add_argument('--replies',type=Path,help='Mock-only JSON object of case id -> ordered SDK replies')
    args=parser.parse_args()
    root=args.trial_root
    if not root.is_absolute() or root.is_symlink():parser.error('--trial-root must be an absolute, non-symlink path')
    # Reject symlink ancestors too; a data directory is not a sandbox.
    if any(p.is_symlink() for p in root.parents):parser.error('symlink in trial-root ancestry')
    root=root.resolve();marker=root/'prepared.json'
    if root.exists():
        if not args.real_calls or not marker.is_file() or set(p.name for p in root.iterdir())-{'prepared.json','library'}:parser.error('trial root must be fresh (or untouched --prepare root for Step 2)')
    else:
        root.mkdir(parents=True);(root/'library').mkdir()
    if args.real_calls and args.replies:parser.error('--replies is mock-only')
    try:
        ids=[int(v) for v in args.cases.split(',')]
        if len(set(ids))!=len(ids) or any(n not in range(1,11) for n in ids):raise ValueError()
    except ValueError:parser.error('--cases must contain distinct ids from 1 through 10')
    os.environ['AOTN_DATA_DIR']=str(root/'library')
    from .runner import batch,write_json
    if args.prepare:
        write_json(marker,dict(version=1,library=str(root/'library'),note='Step 2 requires separate owner approval. Owner adds key through app. Harness never copies Secrets.'))
        print(json.dumps({'prepared':str(root)}));return 0
    try:report=asyncio.run(batch(root,ids,args.real_calls,args.calibrate_only,args.scenario,args.replies))
    except Exception as exc:
        # Errors are artifacts, never a success because a handled workflow exited 0.
        write_json(root/'report.json',{'result':'fail','failure':type(exc).__name__+': '+str(exc)})
        print(json.dumps({'result':'fail','report':str(root/'report.json')}));return 1
    print(json.dumps({'result':report['result'],'cases':report['case_count'],'report':str(root/'report.json')}))
    return 0 if report['result']=='pass' else 1

if __name__=='__main__':sys.exit(main())
