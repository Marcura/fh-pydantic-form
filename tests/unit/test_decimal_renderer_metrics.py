import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

import decimal
from decimal import Decimal
from typing import cast, Dict, Any

import pytest
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import DecimalFieldRenderer
from fh_pydantic_form.type_helpers import MetricEntry


class TestDecimalRendererMetrics:
    """Test DecimalFieldRenderer with metrics support"""

    @pytest.fixture
    def decimal_field_info(self):
        """Create a FieldInfo for decimal fields"""
        return FieldInfo(annotation=decimal.Decimal)

    @pytest.fixture
    def sample_metric_entry(self):
        """Sample metric entry for testing"""
        return {
            "metric": 0.85,
            "color": "green",
            "comment": "Good value within expected range",
        }

    @pytest.fixture
    def high_score_metric(self):
        """High score metric entry"""
        return {"metric": 0.95, "color": "blue", "comment": "Excellent precision"}

    @pytest.fixture
    def low_score_metric(self):
        """Low score metric entry"""
        return {"metric": 0.25, "color": "red", "comment": "Value needs attention"}

    def test_decimal_renderer_with_metric_entry(
        self, decimal_field_info, sample_metric_entry
    ):
        """Test decimal renderer with explicit metric entry"""
        renderer = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("99.99"),
            metric_entry=sample_metric_entry,
        )

        assert renderer.metric_entry == sample_metric_entry

        # Should render without error
        complete_field = renderer.render()
        assert complete_field is not None

    def test_decimal_renderer_with_metrics_dict(self, decimal_field_info):
        """Test decimal renderer with metrics dict auto-lookup"""
        metrics_dict = {
            "product.price": {
                "metric": 0.78,
                "color": "yellow",
                "comment": "Moderate pricing",
            }
        }

        renderer = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("149.99"),
            field_path=["product", "price"],
            metrics_dict=metrics_dict,
        )

        # Should auto-resolve metric entry
        assert renderer.metric_entry is not None
        assert renderer.metric_entry["metric"] == 0.78
        assert renderer.metric_entry["color"] == "yellow"

    def test_decimal_renderer_metric_border_decoration(
        self, decimal_field_info, high_score_metric
    ):
        """Test that metric entries add border decoration"""
        renderer = DecimalFieldRenderer(
            field_name="amount",
            field_info=decimal_field_info,
            value=Decimal("500.00"),
            metric_entry=high_score_metric,
        )

        complete_field = renderer.render()
        field_str = str(complete_field)

        # Should contain border styling
        assert "border-left" in field_str
        assert "padding-left" in field_str

    def test_decimal_renderer_metric_badge(
        self, decimal_field_info, sample_metric_entry
    ):
        """Test that metric entries add score badges"""
        renderer = DecimalFieldRenderer(
            field_name="cost",
            field_info=decimal_field_info,
            value=Decimal("75.50"),
            metric_entry=sample_metric_entry,
        )

        complete_field = renderer.render()
        field_str = str(complete_field)

        # Should contain metric score
        assert "0.85" in field_str

    def test_decimal_renderer_metric_tooltip(
        self, decimal_field_info, sample_metric_entry
    ):
        """Test that metric entries add tooltips"""
        renderer = DecimalFieldRenderer(
            field_name="margin",
            field_info=decimal_field_info,
            value=Decimal("0.25"),
            metric_entry=sample_metric_entry,
        )

        complete_field = renderer.render()
        field_str = str(complete_field)

        # Should contain tooltip attributes
        assert "uk-tooltip" in field_str or "title" in field_str
        assert sample_metric_entry["comment"] in field_str

    def test_decimal_renderer_multiple_metric_decorations(self, decimal_field_info):
        """Test decimal renderer with multiple metric decoration types"""
        metric_entry: MetricEntry = {
            "metric": 0.92,
            "color": "rgba(0, 255, 0, 0.8)",
            "comment": "Excellent value with high confidence",
        }

        renderer = DecimalFieldRenderer(
            field_name="quality_score",
            field_info=decimal_field_info,
            value=Decimal("98.75"),
            metric_entry=metric_entry,
        )

        complete_field = renderer.render()
        field_str = str(complete_field)

        # Should contain multiple decorations
        assert "0.92" in field_str  # Badge
        assert "border-left" in field_str  # Border
        assert metric_entry["comment"] in field_str  # Tooltip

    def test_decimal_renderer_metric_path_resolution(self, decimal_field_info):
        """Test metric path resolution for nested decimal fields"""
        metrics_dict = {
            "order.items[0].price": {
                "metric": 0.88,
                "color": "green",
                "comment": "Good item pricing",
            },
            "order.items[1].price": {
                "metric": 0.45,
                "color": "orange",
                "comment": "Review item pricing",
            },
        }

        # Test first item
        renderer1 = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("25.99"),
            field_path=["order", "items", "0", "price"],
            metrics_dict=metrics_dict,
        )

        assert renderer1.metric_entry is not None
        assert renderer1.metric_entry["metric"] == 0.88

        # Test second item
        renderer2 = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("125.99"),
            field_path=["order", "items", "1", "price"],
            metrics_dict=metrics_dict,
        )

        assert renderer2.metric_entry is not None
        assert renderer2.metric_entry["metric"] == 0.45

    def test_decimal_renderer_no_metrics(self, decimal_field_info):
        """Test decimal renderer without any metrics"""
        renderer = DecimalFieldRenderer(
            field_name="basic_amount",
            field_info=decimal_field_info,
            value=Decimal("100.00"),
        )

        assert renderer.metric_entry is None

        # Should still render normally
        complete_field = renderer.render()
        assert complete_field is not None

    def test_decimal_renderer_metric_color_variants(self, decimal_field_info):
        """Test decimal renderer with various metric color formats"""
        color_variants = [
            {"metric": 0.9, "color": "green", "comment": "Named color"},
            {"metric": 0.8, "color": "#00FF00", "comment": "Hex color"},
            {"metric": 0.7, "color": "rgb(0, 255, 0)", "comment": "RGB color"},
            {"metric": 0.6, "color": "rgba(0, 255, 0, 0.8)", "comment": "RGBA color"},
            {"metric": 0.5, "color": "hsl(120, 100%, 50%)", "comment": "HSL color"},
        ]

        for i, metric_entry in enumerate(color_variants):
            renderer = DecimalFieldRenderer(
                field_name=f"test_field_{i}",
                field_info=decimal_field_info,
                value=Decimal(f"{i * 10}.00"),
                metric_entry=metric_entry,
            )

            # Should render without error regardless of color format
            complete_field = renderer.render()
            assert complete_field is not None

    def test_decimal_renderer_metric_score_types(self, decimal_field_info):
        """Test decimal renderer with various metric score types"""
        score_variants = [
            {"metric": 0.85, "comment": "Float score"},
            {"metric": 85, "comment": "Integer score"},
            {"metric": "HIGH", "comment": "String score"},
            {"metric": "A+", "comment": "Grade score"},
        ]

        for i, metric_entry_data in enumerate(score_variants):
            metric_entry = metric_entry_data
            renderer = DecimalFieldRenderer(
                field_name=f"score_field_{i}",
                field_info=decimal_field_info,
                value=Decimal(f"{i * 25}.50"),
                metric_entry=metric_entry,
            )

            # Should render without error regardless of score type
            complete_field = renderer.render()
            assert complete_field is not None

            field_str = str(complete_field)
            assert str(cast(Dict[str, Any], metric_entry)["metric"]) in field_str

    def test_decimal_renderer_metric_edge_cases(self, decimal_field_info):
        """Test decimal renderer with metric edge cases"""
        edge_cases = [
            {"metric": 0.0, "comment": "Zero score"},
            {"metric": 1.0, "comment": "Perfect score"},
            {"metric": -0.5, "comment": "Negative score"},
            {"comment": "Comment only, no score"},
            {"metric": 0.5, "color": ""},  # Empty color
            {},  # Empty metric entry
        ]

        for i, metric_entry in enumerate(edge_cases):
            renderer = DecimalFieldRenderer(
                field_name=f"edge_field_{i}",
                field_info=decimal_field_info,
                value=Decimal("50.00"),
                metric_entry=metric_entry if metric_entry else None,
            )

            # Should handle edge cases gracefully
            complete_field = renderer.render()
            assert complete_field is not None

    def test_decimal_renderer_metrics_with_disabled_field(
        self, decimal_field_info, sample_metric_entry
    ):
        """Test metrics work with disabled decimal fields"""
        renderer = DecimalFieldRenderer(
            field_name="disabled_price",
            field_info=decimal_field_info,
            value=Decimal("200.00"),
            disabled=True,
            metric_entry=sample_metric_entry,
        )

        complete_field = renderer.render()
        field_str = str(complete_field)

        # Should have both disabled and metrics
        assert "disabled" in field_str
        assert "0.85" in field_str  # Metric score
        assert sample_metric_entry["comment"] in field_str

    def test_decimal_renderer_metrics_with_optional_field(self, sample_metric_entry):
        """Test metrics work with optional decimal fields"""
        optional_field_info = FieldInfo(annotation=decimal.Decimal)

        renderer = DecimalFieldRenderer(
            field_name="optional_amount",
            field_info=optional_field_info,
            value=None,
            metric_entry=sample_metric_entry,
        )

        complete_field = renderer.render()
        field_str = str(complete_field)

        # Should have metrics even with None value
        assert "0.85" in field_str
        assert sample_metric_entry["comment"] in field_str
        assert "Optional" in field_str  # Optional field indicator
