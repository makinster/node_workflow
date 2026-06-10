"""CLI entrypoint for generating a node from a spec."""

from __future__ import annotations

try:
    from .generator import main
except ImportError:
    from generator import main


if __name__ == "__main__":
    raise SystemExit(main())
