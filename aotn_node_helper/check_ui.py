"""Mount one node's config screen and check its schema-driven UI contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT / "AttackOfTheNodes"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check tab placement, focusability, and dynamic-form rules "
        "for one node's generated config UI"
    )
    parser.add_argument("node_type", help="Node type to check")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT))
    try:
        from aotn_node_helper.ui_checks import run_ui_check
    except ImportError:
        from ui_checks import run_ui_check

    try:
        problems = run_ui_check(args.node_type, project_root=args.project_root)
    except ValueError as error:
        print(f"check_ui: {error}")
        return 2

    if problems:
        print(f"check_ui: {len(problems)} problem(s) for {args.node_type}:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print(f"check_ui: {args.node_type} config UI contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
