"""Run focused checks for one generated node type."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = ROOT / "AttackOfTheNodes"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run focused generated-node checks")
    parser.add_argument("node_type", help="Node type to test")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args(argv)

    commands = [
        [sys.executable, "-m", "compileall", "-q", "."],
        [
            sys.executable,
            "-m",
            "pytest",
            f"tests/generated/test_{args.node_type}.py",
            "-v",
        ],
    ]
    for command in commands:
        print("+", " ".join(command))
        result = subprocess.run(command, cwd=args.project_root, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
