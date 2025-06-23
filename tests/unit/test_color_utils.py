"""
Unit tests for color utility functions.
"""

import pytest

from fh_pydantic_form.color_utils import robust_color_to_rgba
from fh_pydantic_form.color_utils import get_metric_colors, DEFAULT_METRIC_GREY


class TestGetMetricColors:
    @pytest.mark.parametrize(
        "metric,expected_bg,expected_text",
        [
            (0.0, "#D32F2F", "white"),
            (0.25, "#8B0000", "#fca5a5"),
            (0.75, "#2E7D32", "#86efac"),
            (1.0, "#00C853", "white"),
            ("invalid", DEFAULT_METRIC_GREY, "white"),
            (None, DEFAULT_METRIC_GREY, "white"),
            (-1, DEFAULT_METRIC_GREY, "white"),
            (2.0, DEFAULT_METRIC_GREY, "white"),
        ],
    )
    def test_metric_colors(self, metric, expected_bg, expected_text):
        """Test metric-based color determination."""
        bg, text = get_metric_colors(metric)
        assert bg == expected_bg
        assert text == expected_text


class TestRobustColorToRgba:
    """Test the robust_color_to_rgba function with various color formats."""

    def test_hex_colors(self):
        """Test hex color parsing."""
        # 6-digit hex colors
        assert robust_color_to_rgba("#FF0000", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("#00FF00", 0.8) == "rgba(0, 255, 0, 0.8)"
        assert robust_color_to_rgba("#0000FF", 0.5) == "rgba(0, 0, 255, 0.5)"

        # 3-digit hex colors (should expand)
        assert robust_color_to_rgba("#f00", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("#0f0", 0.7) == "rgba(0, 255, 0, 0.7)"
        assert robust_color_to_rgba("#00f", 0.3) == "rgba(0, 0, 255, 0.3)"

        # Case insensitive
        assert robust_color_to_rgba("#ff0000", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("#FF0000", 1.0) == "rgba(255, 0, 0, 1.0)"

    def test_rgb_colors(self):
        """Test RGB color parsing."""
        assert robust_color_to_rgba("rgb(255, 0, 0)", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("rgb(0, 255, 0)", 0.6) == "rgba(0, 255, 0, 0.6)"
        assert robust_color_to_rgba("rgb(0, 0, 255)", 0.2) == "rgba(0, 0, 255, 0.2)"

        # With spaces
        assert robust_color_to_rgba("rgb(255,0,0)", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("rgb( 255 , 0 , 0 )", 1.0) == "rgba(255, 0, 0, 1.0)"

    def test_rgba_colors(self):
        """Test RGBA color parsing (opacity from color string is ignored, parameter used)."""
        assert (
            robust_color_to_rgba("rgba(255, 0, 0, 0.5)", 1.0) == "rgba(255, 0, 0, 1.0)"
        )
        assert (
            robust_color_to_rgba("rgba(0, 255, 0, 0.8)", 0.3) == "rgba(0, 255, 0, 0.3)"
        )

    def test_hsl_colors(self):
        """Test HSL color parsing."""
        # Red: hsl(0, 100%, 50%)
        assert robust_color_to_rgba("hsl(0, 100%, 50%)", 1.0) == "rgba(255, 0, 0, 1.0)"

        # Green: hsl(120, 100%, 50%)
        assert (
            robust_color_to_rgba("hsl(120, 100%, 50%)", 0.8) == "rgba(0, 255, 0, 0.8)"
        )

        # Blue: hsl(240, 100%, 50%)
        assert (
            robust_color_to_rgba("hsl(240, 100%, 50%)", 0.5) == "rgba(0, 0, 255, 0.5)"
        )

    def test_hsla_colors(self):
        """Test HSLA color parsing (opacity from color string is ignored, parameter used)."""
        assert (
            robust_color_to_rgba("hsla(0, 100%, 50%, 0.5)", 1.0)
            == "rgba(255, 0, 0, 1.0)"
        )
        assert (
            robust_color_to_rgba("hsla(120, 100%, 50%, 0.8)", 0.3)
            == "rgba(0, 255, 0, 0.3)"
        )

    def test_named_colors(self):
        """Test named CSS color parsing."""
        assert robust_color_to_rgba("red", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("green", 0.8) == "rgba(0, 128, 0, 0.8)"
        assert robust_color_to_rgba("blue", 0.5) == "rgba(0, 0, 255, 0.5)"
        assert robust_color_to_rgba("white", 1.0) == "rgba(255, 255, 255, 1.0)"
        assert robust_color_to_rgba("black", 0.7) == "rgba(0, 0, 0, 0.7)"

        # Case insensitive
        assert robust_color_to_rgba("RED", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("Red", 1.0) == "rgba(255, 0, 0, 1.0)"

    def test_tailwind_colors(self):
        """Test Tailwind CSS color parsing."""
        # Basic Tailwind colors
        assert robust_color_to_rgba("red-500", 1.0) == "rgba(239, 68, 68, 1.0)"
        assert robust_color_to_rgba("blue-600", 0.7) == "rgba(37, 99, 235, 0.7)"
        assert robust_color_to_rgba("green-400", 0.5) == "rgba(74, 222, 128, 0.5)"

        # With prefixes
        assert robust_color_to_rgba("text-red-500", 1.0) == "rgba(239, 68, 68, 1.0)"
        assert robust_color_to_rgba("bg-blue-600", 0.8) == "rgba(37, 99, 235, 0.8)"
        assert (
            robust_color_to_rgba("border-green-400", 0.3) == "rgba(74, 222, 128, 0.3)"
        )

        # Extended colors
        assert robust_color_to_rgba("emerald-500", 1.0) == "rgba(16, 185, 129, 1.0)"
        assert robust_color_to_rgba("amber-400", 0.6) == "rgba(251, 191, 36, 0.6)"
        assert robust_color_to_rgba("violet-600", 0.4) == "rgba(124, 58, 237, 0.4)"

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty string
        assert robust_color_to_rgba("", 1.0) == "rgba(128, 128, 128, 1.0)"

        # None (should not happen in practice, but test defensive coding)
        # Note: This would cause an AttributeError in real usage, but we test with empty string

        # Invalid hex
        assert robust_color_to_rgba("#invalid", 1.0) == "rgba(128, 128, 128, 1.0)"
        assert (
            robust_color_to_rgba("#12", 1.0) == "rgba(128, 128, 128, 1.0)"
        )  # Too short
        assert (
            robust_color_to_rgba("#1234567", 1.0) == "rgba(128, 128, 128, 1.0)"
        )  # Too long

        # Invalid RGB
        assert robust_color_to_rgba("rgb()", 1.0) == "rgba(128, 128, 128, 1.0)"
        assert robust_color_to_rgba("rgb(255)", 1.0) == "rgba(128, 128, 128, 1.0)"
        assert robust_color_to_rgba("rgb(255, 0)", 1.0) == "rgba(128, 128, 128, 1.0)"

        # Invalid HSL
        assert robust_color_to_rgba("hsl()", 1.0) == "rgba(128, 128, 128, 1.0)"
        assert robust_color_to_rgba("hsl(0)", 1.0) == "rgba(128, 128, 128, 1.0)"

        # Unknown named color
        assert robust_color_to_rgba("unknown-color", 1.0) == "rgba(128, 128, 128, 1.0)"

        # Invalid Tailwind
        assert robust_color_to_rgba("unknown-500", 1.0) == "rgba(128, 128, 128, 1.0)"
        assert robust_color_to_rgba("red-999", 1.0) == "rgba(128, 128, 128, 1.0)"

    def test_opacity_parameter(self):
        """Test that the opacity parameter is correctly applied."""
        # Test various opacity values
        assert robust_color_to_rgba("red", 0.0) == "rgba(255, 0, 0, 0.0)"
        assert robust_color_to_rgba("red", 0.25) == "rgba(255, 0, 0, 0.25)"
        assert robust_color_to_rgba("red", 0.5) == "rgba(255, 0, 0, 0.5)"
        assert robust_color_to_rgba("red", 0.75) == "rgba(255, 0, 0, 0.75)"
        assert robust_color_to_rgba("red", 1.0) == "rgba(255, 0, 0, 1.0)"

    def test_whitespace_handling(self):
        """Test that whitespace is properly handled."""
        assert robust_color_to_rgba("  red  ", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("\t#FF0000\n", 1.0) == "rgba(255, 0, 0, 1.0)"
        assert robust_color_to_rgba("  rgb(255, 0, 0)  ", 1.0) == "rgba(255, 0, 0, 1.0)"

    @pytest.mark.parametrize(
        "color,expected_rgb",
        [
            # Basic colors
            ("red", (255, 0, 0)),
            ("green", (0, 128, 0)),
            ("blue", (0, 0, 255)),
            # Hex colors
            ("#FF0000", (255, 0, 0)),
            ("#00FF00", (0, 255, 0)),
            ("#0000FF", (0, 0, 255)),
            # Tailwind colors
            ("red-500", (239, 68, 68)),
            ("blue-600", (37, 99, 235)),
            ("green-400", (74, 222, 128)),
        ],
    )
    def test_parametrized_color_parsing(
        self, color: str, expected_rgb: tuple[int, int, int]
    ):
        """Parametrized test for various color formats."""
        r, g, b = expected_rgb
        expected = f"rgba({r}, {g}, {b}, 1.0)"
        assert robust_color_to_rgba(color, 1.0) == expected
