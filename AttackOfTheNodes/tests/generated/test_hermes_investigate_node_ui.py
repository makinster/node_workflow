"""Generated config-UI smoke test for hermes_investigate_node.

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


pytestmark = [pytest.mark.generated_node, pytest.mark.node_type("hermes_investigate_node")]


def test_hermes_investigate_node_config_ui_contract():
    problems = run_ui_check("hermes_investigate_node")
    assert problems == [], "\n".join(problems)
