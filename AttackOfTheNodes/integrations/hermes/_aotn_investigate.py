#!/usr/bin/env python3
"""Installed deterministic entry; app code comes from the selected live checkout."""
import argparse
import os
from pathlib import Path
import sys


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project-root',required=True,type=Path)
    parser.add_argument('--data-dir',required=True,type=Path)
    parser.add_argument('--folder',required=True,type=Path)
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    os.environ['AOTN_DATA_DIR']=str(args.data_dir)
    sys.path.insert(0,str(args.project_root/'AttackOfTheNodes'))
    try:
        from backend.hermes_folder import NAME_PATTERN, MESSAGE_LIMIT, cut
        from backend.integrations.hermes_investigate import tick
        from backend.secrets_manager import SecretsManager
        if not NAME_PATTERN.fullmatch(args.name):
            raise ValueError
        # Final transport boundary: include print's LF, headers and notes in
        # the same UTF-16 budget as the C1 drain.
        print(cut(tick(args.folder,args.name,manager=SecretsManager()), MESSAGE_LIMIT-1))
    except Exception:
        print('Investigation inbox needs checking.')
    return 0


if __name__=='__main__':
    sys.exit(main())
