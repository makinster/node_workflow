"""Benchmark scripts live outside tests/ and are never collected (D6)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BENCHMARKS = PROJECT_ROOT / "benchmarks"


def test_benchmark_scripts_exist():
    scripts = sorted(path.name for path in BENCHMARKS.glob("bench_*.py"))
    assert "bench_linear_run.py" in scripts
    assert "bench_wait_registry.py" in scripts


def test_benchmarks_do_not_import_the_frontend():
    for script in BENCHMARKS.glob("*.py"):
        text = script.read_text(encoding="utf-8")
        assert "frontend" not in text, script.name
        assert "textual" not in text.lower(), script.name


def test_plain_pytest_collects_nothing_from_benchmarks():
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider",
         str(BENCHMARKS)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    # Exit code 5 is pytest's "no tests were collected".
    assert result.returncode == 5, result.stdout + result.stderr
