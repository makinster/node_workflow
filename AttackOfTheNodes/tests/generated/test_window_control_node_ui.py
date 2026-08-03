"""Generated config-UI smoke test for window_control_node.

Mounts NodeConfigScreen and checks tab placement, focusability, and
dynamic-form rule state through aotn_node_helper.ui_checks.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE_ROOT))

from aotn_node_helper.ui_checks import run_ui_check  # noqa: E402


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("window_control_node")]


def test_window_control_node_config_ui_contract():
    problems = run_ui_check("window_control_node")
    assert problems == [], "\n".join(problems)
