"""
Unit tests for MetricsRendererMixin and metrics decoration logic.
"""

import pytest

from fh_pydantic_form.field_renderers import MetricsRendererMixin
from fh_pydantic_form.type_helpers import DecorationScope


@pytest.fixture
def mock_renderer(mocker):
    """Fixture: Returns a dummy renderer instance with MetricsRendererMixin."""

    class DummyRenderer(MetricsRendererMixin):
        pass

    return DummyRenderer()


@pytest.fixture
def sample_metric_entries():
    """Fixture: Provides sample metric entries for testing."""
    return [
        {"metric": 0.0},
        {"metric": 0.3},
        {"metric": 0.7},
        {"metric": 1.0},
        {"color": "#FF0000"},
        {"metric": 0.5, "comment": "Halfway"},
        {"comment": "Only comment"},
        {},
        None,
    ]


@pytest.fixture
def mock_ft_element(mocker):
    """Fixture: Returns a mock FastHTML element with attrs and children."""

    def _make(tag="div"):
        elem = mocker.Mock()
        elem.tag = tag
        elem.attrs = {}
        elem.children = []
        return elem

    return _make


@pytest.mark.unit
class TestMetricsRendererMixin:
    def test_metric_border_color_various(self, mock_renderer, sample_metric_entries):
        """Test _metric_border_color returns expected color for various metric entries."""
        for entry in sample_metric_entries:
            color = mock_renderer._metric_border_color(entry)
            # Should return a string or None
            assert color is None or isinstance(color, str)

    @pytest.mark.parametrize(
        "metric_entry,expected_color",
        [
            ({"metric": 0.0}, "rgba(211, 47, 47"),  # Instead of "#D32F2F"
            ({"metric": 0.3}, "rgba(139, 0, 0"),  # Instead of "#8B0000"
            ({"metric": 0.7}, "rgba(46, 125, 50"),  # Instead of "#2E7D32"
            ({"metric": 1.0}, "rgba(0, 200, 83"),  # Instead of "#00C853"
            ({"color": "#FF0000"}, "rgba(255, 0, 0, 0.8)"),
        ],
    )
    def test_metric_border_color_specific(
        self, mock_renderer, metric_entry, expected_color
    ):
        """Test _metric_border_color returns correct color for known cases."""
        color = mock_renderer._metric_border_color(metric_entry)
        assert expected_color in color  # Now checking partial match

    def test_decorate_label_with_bullet(self, mock_renderer, mock_ft_element):
        """Test _decorate_label attaches a badge to the label element."""
        label = mock_ft_element("label")
        metric_entry = {"metric": 0.8}
        result = mock_renderer._decorate_label(label, metric_entry)
        # Should still be the same object
        assert result is label
        # Should have a badge in children
        assert any(
            "badge" in str(child).lower() or "span" in str(child).lower()
            for child in label.children
        )

    @pytest.mark.parametrize(
        "scope", [DecorationScope.BORDER, DecorationScope.BULLET, DecorationScope.BOTH]
    )
    def test_decorate_metrics_scopes(self, mock_renderer, mock_ft_element, scope):
        """Test _decorate_metrics applies correct decorations for each scope."""
        elem = mock_ft_element("div")
        metric_entry = {"metric": 0.9, "comment": "Good"}
        result = mock_renderer._decorate_metrics(elem, metric_entry, scope=scope)
        # For BULLET or BOTH scope, element gets wrapped
        if scope in {DecorationScope.BULLET, DecorationScope.BOTH}:
            # Result should be a wrapper containing the original element
            assert result is not elem  # It's wrapped
            assert "relative inline-flex items-center" in str(result)
        else:
            # For BORDER only, element is modified in-place
            assert result is elem
        # Check for tooltip/comment
        if "comment" in metric_entry:
            assert "uk-tooltip" in elem.attrs or "title" in elem.attrs
        # Check for border style if BORDER or BOTH
        if scope in {DecorationScope.BORDER, DecorationScope.BOTH}:
            assert "border-left" in elem.attrs.get("style", "")
        # Check for badge if BULLET or BOTH
        if scope in {DecorationScope.BULLET, DecorationScope.BOTH}:
            # Badge should be in children or wrapped
            pass  # Already tested in test_decorate_label_with_bullet

    def test_attach_metric_badge_inline(self, mock_renderer, mock_ft_element):
        """Test _attach_metric_badge appends badge to inline elements."""
        elem = mock_ft_element("span")
        badge = mock_ft_element("span")
        mock_renderer._attach_metric_badge(elem, badge)
        assert badge in elem.children

    def test_attach_metric_badge_block(self, mock_renderer, mock_ft_element):
        """Test _attach_metric_badge wraps block elements."""
        elem = mock_ft_element("div")
        badge = mock_ft_element("span")
        result = mock_renderer._attach_metric_badge(elem, badge)
        # Should return a new wrapper (not the original elem)
        assert result is not elem

    def test_highlight_input_fields_applies_style(self, mock_renderer, mock_ft_element):
        """Test _highlight_input_fields applies highlight CSS to form controls."""
        input_elem = mock_ft_element("input")
        parent = mock_ft_element("div")
        parent.children.append(input_elem)
        metric_entry = {"metric": 0.6}
        mock_renderer._highlight_input_fields(parent, metric_entry)
        # Should apply style to input_elem
        assert "border" in input_elem.attrs.get("style", "")

    def test_highlight_input_fields_no_metric(self, mock_renderer, mock_ft_element):
        """Test _highlight_input_fields does nothing if no metric."""
        elem = mock_ft_element("input")
        mock_renderer._highlight_input_fields(elem, None)
        # Should not modify style
        assert elem.attrs.get("style", "") == ""
