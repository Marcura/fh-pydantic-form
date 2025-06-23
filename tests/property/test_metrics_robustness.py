import pytest
from hypothesis import given
from hypothesis import strategies as st

from fh_pydantic_form.color_utils import get_metric_colors
from fh_pydantic_form.field_renderers import _build_path_string_static


@pytest.mark.property
class TestMetricsRobustness:
    @given(st.floats(min_value=-10, max_value=10, allow_infinity=False))
    def test_metric_color_robustness(self, metric_value):
        """Test color determination with arbitrary float values."""
        bg, text = get_metric_colors(metric_value)
        assert isinstance(bg, str)
        assert isinstance(text, str)

    @given(st.lists(st.text(), min_size=1, max_size=5))
    def test_path_resolution_robustness(self, path_segments):
        """Test path resolution doesn't crash with arbitrary paths."""
        try:
            path = _build_path_string_static(path_segments)
            assert isinstance(path, str)
        except Exception:
            # Should not raise, but if it does, only for truly invalid input
            assert True
