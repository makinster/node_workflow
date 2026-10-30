"""Reusable, contained trial roots; mock mode is the default."""

import argparse
import asyncio
import json
import math
import os
from pathlib import Path
import sys

from . import JUDGE_MODELS, JUDGE_EFFORTS
from .containment import (
    ContainmentError,
    checked_root,
    create_run,
    preparation_record,
    validate_prepared,
    validate_tree,
)


def positive_number(raw):
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive finite number") from exc
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be a positive finite number")
    return value


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
    parser.add_argument(
        "--budget",
        type=positive_number,
        metavar="USD",
        help="Required estimate limit with --real-calls; no default",
    )
    parser.add_argument(
        "--time-limit",
        type=positive_number,
        default=600,
        metavar="SECONDS",
        help="Stop before the next call after this time (default 600)",
    )
    parser.add_argument("--calibrate-only", action="store_true")
    parser.add_argument(
        "--cases-even-if-calibration-fails", action="store_true",
        help="Run selected cases after failed calibration; overall result remains fail",
    )
    parser.add_argument("--judge-model", choices=JUDGE_MODELS, default=JUDGE_MODELS[0])
    parser.add_argument("--judge-effort", choices=JUDGE_EFFORTS, default=JUDGE_EFFORTS[0])
    parser.add_argument("--case-set", default=None, help='1,2,3, a comma list, or all (default 1; replay infers saved sets)')
    parser.add_argument('--replay', type=Path, help='Mock-only replay of a saved run directory')
    parser.add_argument('--affected', metavar='GIT_BASE', help='Select sets from changed paths; unknown impact selects all')
    parser.add_argument("--cases", default=None)
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
    if args.real_calls and args.budget is None:
        parser.error("--budget USD is required with --real-calls")
    if args.real_calls and args.replies:
        parser.error("--replies is mock-only")
    if args.replay and (args.real_calls or args.replies or args.prepare or args.scenario != 'ready'):
        parser.error('--replay is mock-only; cannot combine with --real-calls, --replies, --prepare or --scenario')
    replay = None
    selection = None
    try:
        from .dependencies import affected, sets_from_text
        if args.replay:
            from .replay import ReplayRun
            source = checked_root(args.replay.expanduser())
            validate_tree(source)
            replay = ReplayRun(source)
        sets = sets_from_text(args.case_set) if args.case_set else replay.sets if replay else [1]
        if args.affected:
            selection = affected(args.affected)
            # Explicit choices add coverage; they never exclude an affected set.
            sets = sorted(set(selection['selected']) | (set(sets) if args.case_set else set()))
            selection['selected'] = sets
            selection['skipped'] = [n for n in (1, 2, 3) if n not in sets]
            for n in sets:
                if not selection['reasons'][str(n)]:
                    selection['reasons'][str(n)].append(dict(path=None, reason='explicit --case-set'))
        args.case_set = sets[0] if len(sets) == 1 else sets
        count = min(4 if n == 3 else 10 for n in sets)
        ids = [int(value) for value in args.cases.split(',')] if args.cases else None
        if ids is not None and (len(set(ids)) != len(ids) or any(n not in range(1,count+1) for n in ids)):
            raise ValueError(f'--cases must contain distinct ids from 1 through {count} for every selected set')
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    # All validation precedes mkdir, marker writes, env changes and runner import.
    try:
        root = checked_root(args.trial_root)
        if replay is not None and root.is_relative_to(replay.root):
            raise ContainmentError('Replay output must not be inside the saved source run')
        if root.exists():
            validate_tree(root)
            if args.prepare:
                raise ContainmentError("--prepare requires a fresh trial root")
            validate_prepared(root)
        elif args.real_calls:
            raise ContainmentError("--real-calls requires a prepared trial root")
        if args.real_calls and args.prepare:
            raise ContainmentError("--real-calls and --prepare cannot be combined")
    except (ContainmentError, OSError) as exc:
        parser.error(str(exc))

    if not root.exists():
        root.mkdir(parents=True)
        (root / "library").mkdir()
        (root / "runs").mkdir()
        # Exclusive creation cannot follow an existing marker link or overwrite.
        with (root / "prepared.json").open("x", encoding="utf-8") as marker:
            json.dump(preparation_record(root), marker, indent=2)
            marker.write("\n")
    if args.prepare:
        print(json.dumps({"prepared": str(root)}))
        return 0

    run_root = create_run(root)
    (run_root / "library").mkdir()
    os.environ["AOTN_DATA_DIR"] = str(run_root / "library")
    from .runner import batch, write_json

    if selection:
        for n in sets:
            reasons = ', '.join(dict.fromkeys(r['reason'] for r in selection['reasons'][str(n)]))
            print(f'Selected set {n}: {reasons}', file=sys.stderr)
        for n in selection['skipped']:
            print(f'Skipped set {n}: {selection["skipped_reason"]}', file=sys.stderr)

    try:
        report = asyncio.run(
            batch(
                run_root,
                ids,
                args.real_calls,
                args.calibrate_only,
                args.scenario,
                args.replies,
                budget_usd=args.budget,
                time_limit=args.time_limit,
                shared_library=root / "library",
                judge_model=args.judge_model,
                judge_effort=args.judge_effort,
                cases_even_if_calibration_fails=args.cases_even_if_calibration_fails,
                case_set=args.case_set,
                **({'replay': replay} if replay is not None else {}),
            )
        )
    except Exception as exc:
        # A handled engine failure with exit 0 is not trial success.
        write_json(
            run_root / "report.json",
            {
                "result": "fail",
                "case_set": args.case_set,
                "failure": type(exc).__name__ + ": " + str(exc),
                "judge_model": args.judge_model,
                "judge_effort": args.judge_effort,
                "budget_usd": args.budget,
                "time_limit_seconds": args.time_limit,
            },
        )
        print(json.dumps({"result": "fail", "report": str(run_root / "report.json")}))
        return 1
    if selection:
        report['affected'] = selection
        write_json(run_root/'report.json', report)
    print(
        json.dumps(
            {
                "result": report["result"],
                "cases": report["case_count"],
                "case_set": args.case_set,
                "fully_right": report.get("fully_right"),
                "calibration": report["calibration"],
                "cases_even_if_calibration_fails": report.get('cases_even_if_calibration_fails', args.cases_even_if_calibration_fails),
                **({'replay_summary': report['replay_summary']} if replay else {}),
                **({'affected': selection} if selection else {}),
                "report": str(run_root / "report.json"),
            }
        )
    )
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
