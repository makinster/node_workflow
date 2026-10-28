"""Explicit fresh root required; mock mode is the default."""

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys

from .containment import (
    ContainmentError,
    checked_root,
    preparation_record,
    validate_prepared,
    validate_tree,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-root", type=Path, required=True)
    parser.add_argument(
        "--real-calls",
        action="store_true",
        help="Step 2 only, after separate owner approval and key setup",
    )
    parser.add_argument(
        "--prepare",
        action="store_true",
        help="Create a fresh empty trial library for owner key setup, then stop",
    )
    parser.add_argument("--calibrate-only", action="store_true")
    parser.add_argument("--cases", default="1,2,3,4,5,6,7,8,9,10")
    parser.add_argument(
        "--scenario",
        choices=["ready", "judge_fail", "error", "unhelpful"],
        default="ready",
    )
    parser.add_argument(
        "--replies",
        type=Path,
        help="Mock-only JSON object of case id -> ordered SDK replies",
    )
    args = parser.parse_args()
    if args.real_calls and args.replies:
        parser.error("--replies is mock-only")
    try:
        ids = [int(value) for value in args.cases.split(",")]
        if len(set(ids)) != len(ids) or any(
            number not in range(1, 11) for number in ids
        ):
            raise ValueError()
    except ValueError:
        parser.error("--cases must contain distinct ids from 1 through 10")

    # All validation precedes mkdir, marker writes, env changes and runner import.
    try:
        root = checked_root(args.trial_root)
        if root.exists():
            validate_tree(root)
            if args.prepare:
                raise ContainmentError("--prepare requires a fresh trial root")
            if not args.real_calls:
                raise ContainmentError("trial root must be fresh")
            validate_prepared(root)
        if args.real_calls and args.prepare:
            raise ContainmentError("--real-calls and --prepare cannot be combined")
    except (ContainmentError, OSError) as exc:
        parser.error(str(exc))

    if not root.exists():
        root.mkdir(parents=True)
        (root / "library").mkdir()
    if args.prepare:
        # Exclusive creation cannot follow an existing marker link or overwrite.
        with (root / "prepared.json").open("x", encoding="utf-8") as marker:
            json.dump(preparation_record(root), marker, indent=2)
            marker.write("\n")
        print(json.dumps({"prepared": str(root)}))
        return 0

    os.environ["AOTN_DATA_DIR"] = str(root / "library")
    from .runner import batch, write_json

    try:
        report = asyncio.run(
            batch(
                root,
                ids,
                args.real_calls,
                args.calibrate_only,
                args.scenario,
                args.replies,
            )
        )
    except Exception as exc:
        # A handled engine failure with exit 0 is not trial success.
        write_json(
            root / "report.json",
            {"result": "fail", "failure": type(exc).__name__ + ": " + str(exc)},
        )
        print(json.dumps({"result": "fail", "report": str(root / "report.json")}))
        return 1
    print(
        json.dumps(
            {
                "result": report["result"],
                "cases": report["case_count"],
                "report": str(root / "report.json"),
            }
        )
    )
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
