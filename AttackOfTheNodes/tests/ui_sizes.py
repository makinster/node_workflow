"""Full layout coverage; the common size remains in the quick suite."""
import pytest

LAYOUT_WIDTHS = [pytest.param(60, marks=pytest.mark.slow), 100,
                 pytest.param(140, marks=pytest.mark.slow)]
LAYOUT_SIZES = [(80, 24), pytest.param((120, 40), marks=pytest.mark.slow)]
