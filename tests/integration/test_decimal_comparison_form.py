import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

from decimal import Decimal
from typing import Optional

import pytest
from pydantic import BaseModel

from fh_pydantic_form import PydanticForm
from fh_pydantic_form.comparison_form import ComparisonForm, simple_diff_metrics


class TestDecimalComparisonForm:
    """Test decimal fields in comparison forms"""

    @pytest.fixture
    def decimal_comparison_model(self):
        """Model for decimal comparison testing"""

        class DecimalComparisonModel(BaseModel):
            base_price: Decimal
            discount: Optional[Decimal] = None
            final_price: Decimal
            margin: Decimal = Decimal("0.20")

        return DecimalComparisonModel

    @pytest.fixture
    def left_decimal_data(self, decimal_comparison_model):
        """Left side data for comparison"""
        return decimal_comparison_model(
            base_price=Decimal("100.00"),
            discount=Decimal("10.00"),
            final_price=Decimal("90.00"),
            margin=Decimal("0.25"),
        )

    @pytest.fixture
    def right_decimal_data(self, decimal_comparison_model):
        """Right side data for comparison"""
        return decimal_comparison_model(
            base_price=Decimal("105.50"),
            discount=Decimal("15.50"),
            final_price=Decimal("90.00"),  # Same final price
            margin=Decimal("0.20"),  # Different margin
        )

    @pytest.fixture
    def decimal_comparison_form(
        self, decimal_comparison_model, left_decimal_data, right_decimal_data
    ):
        """Comparison form with decimal data"""
        left_form = PydanticForm(
            "left_decimal", decimal_comparison_model, initial_values=left_decimal_data
        )
        right_form = PydanticForm(
            "right_decimal", decimal_comparison_model, initial_values=right_decimal_data
        )

        return ComparisonForm(
            name="decimal_comparison",
            left_form=left_form,
            right_form=right_form,
            left_label="Reference Pricing",
            right_label="Proposed Pricing",
        )

    def test_decimal_comparison_form_rendering(self, decimal_comparison_form):
        """Test that comparison form renders decimal fields correctly"""
        rendered = decimal_comparison_form.render_inputs()

        assert rendered is not None
        rendered_str = str(rendered)

        # Should contain decimal values from both sides
        assert "100.00" in rendered_str  # Left base_price
        assert "105.50" in rendered_str  # Right base_price
        assert "10.00" in rendered_str  # Left discount
        assert "15.50" in rendered_str  # Right discount

    def test_decimal_comparison_form_structure(self, decimal_comparison_form):
        """Test the structure of decimal comparison form"""
        rendered = decimal_comparison_form.render_inputs()
        rendered_str = str(rendered)

        # Should have comparison structure
        assert "Reference Pricing" in rendered_str
        assert "Proposed Pricing" in rendered_str

        # Should contain decimal input fields
        assert 'type="number"' in rendered_str
        assert 'step="any"' in rendered_str

    def test_decimal_simple_diff_metrics(
        self, decimal_comparison_model, left_decimal_data, right_decimal_data
    ):
        """Test simple diff metrics with decimal values"""
        metrics = simple_diff_metrics(
            left_data=left_decimal_data,
            right_data=right_decimal_data,
            model_class=decimal_comparison_model,
        )

        # Should have metrics for fields that differ
        assert "base_price" in metrics
        assert "discount" in metrics
        assert "margin" in metrics

        # final_price is the same, so might not have metric or have equality metric
        # Check the specific metric values (0.0 = different, 1.0 = same)
        assert metrics["base_price"]["metric"] == 0.0
        assert metrics["discount"]["metric"] == 0.0
        assert metrics["margin"]["metric"] == 0.0

    def test_decimal_comparison_with_precision_differences(
        self, decimal_comparison_model
    ):
        """Test comparison with decimal precision differences"""
        left_data = decimal_comparison_model(
            base_price=Decimal("100.00"),
            final_price=Decimal("90.00"),
            margin=Decimal("0.25000"),  # High precision
        )

        right_data = decimal_comparison_model(
            base_price=Decimal("100.0"),  # Lower precision, same value
            final_price=Decimal("90.00"),
            margin=Decimal("0.25"),  # Lower precision, same value
        )

        left_form = PydanticForm(
            "left_precision", decimal_comparison_model, initial_values=left_data
        )
        right_form = PydanticForm(
            "right_precision", decimal_comparison_model, initial_values=right_data
        )

        comparison_form = ComparisonForm(
            name="precision_comparison", left_form=left_form, right_form=right_form
        )

        rendered = comparison_form.render_inputs()
        rendered_str = str(rendered)

        # Should preserve precision in display
        assert "100.00" in rendered_str
        assert "100.0" in rendered_str or "100" in rendered_str
        assert "0.25000" in rendered_str
        assert "0.25" in rendered_str

    def test_decimal_comparison_with_none_values(self, decimal_comparison_model):
        """Test comparison with None decimal values"""
        left_data = decimal_comparison_model(
            base_price=Decimal("100.00"),
            discount=None,  # None value
            final_price=Decimal("100.00"),
        )

        right_data = decimal_comparison_model(
            base_price=Decimal("100.00"),
            discount=Decimal("5.00"),  # Has value
            final_price=Decimal("95.00"),
        )

        left_form = PydanticForm(
            "left_none", decimal_comparison_model, initial_values=left_data
        )
        right_form = PydanticForm(
            "right_none", decimal_comparison_model, initial_values=right_data
        )

        comparison_form = ComparisonForm(
            name="none_comparison", left_form=left_form, right_form=right_form
        )

        rendered = comparison_form.render_inputs()

        # Should render without error
        assert rendered is not None

    def test_decimal_comparison_metrics_visualization(
        self, decimal_comparison_model, left_decimal_data, right_decimal_data
    ):
        """Test that decimal comparison shows metrics visualization"""
        # Create metrics based on differences
        metrics = simple_diff_metrics(
            left_data=left_decimal_data,
            right_data=right_decimal_data,
            model_class=decimal_comparison_model,
        )

        left_form = PydanticForm(
            "left_visual", decimal_comparison_model, initial_values=left_decimal_data
        )
        right_form = PydanticForm(
            "right_visual",
            decimal_comparison_model,
            initial_values=right_decimal_data,
            metrics_dict=metrics,
        )

        comparison_form = ComparisonForm(
            name="visual_comparison", left_form=left_form, right_form=right_form
        )

        rendered = comparison_form.render_inputs()
        rendered_str = str(rendered)

        # Should contain visual indicators
        # Look for styling that indicates differences
        assert "border-left" in rendered_str or "background" in rendered_str

    def test_decimal_comparison_with_extreme_values(self, decimal_comparison_model):
        """Test comparison with extreme decimal values"""
        left_data = decimal_comparison_model(
            base_price=Decimal("0.01"),  # Very small
            final_price=Decimal("0.01"),
            margin=Decimal("0.999999999"),  # Very precise
        )

        right_data = decimal_comparison_model(
            base_price=Decimal("999999.99"),  # Very large
            final_price=Decimal("999999.99"),
            margin=Decimal("0.000000001"),  # Very small
        )

        left_form = PydanticForm(
            "left_extreme", decimal_comparison_model, initial_values=left_data
        )
        right_form = PydanticForm(
            "right_extreme", decimal_comparison_model, initial_values=right_data
        )

        comparison_form = ComparisonForm(
            name="extreme_comparison", left_form=left_form, right_form=right_form
        )

        # Should render without error
        rendered = comparison_form.render_inputs()
        assert rendered is not None

        rendered_str = str(rendered)
        # Should contain the extreme values
        assert "0.01" in rendered_str
        assert "999999.99" in rendered_str

    def test_decimal_comparison_form_wrapper(self, decimal_comparison_form):
        """Test decimal comparison form wrapper functionality"""
        wrapped = decimal_comparison_form.form_wrapper(
            decimal_comparison_form.render_inputs()
        )

        assert wrapped is not None
        wrapped_str = str(wrapped)

        # Should contain form wrapper elements
        assert "form" in wrapped_str.lower()

    def test_decimal_comparison_reset_buttons(self, decimal_comparison_form):
        """Test reset buttons work with decimal comparison forms"""
        left_reset = decimal_comparison_form.left_reset_button()
        right_reset = decimal_comparison_form.right_reset_button()

        assert left_reset is not None
        assert right_reset is not None

        # Should contain reset functionality
        left_str = str(left_reset)
        right_str = str(right_reset)

        assert "reset" in left_str.lower()
        assert "reset" in right_str.lower()

    def test_decimal_comparison_refresh_buttons(self, decimal_comparison_form):
        """Test refresh buttons work with decimal comparison forms"""
        left_refresh = decimal_comparison_form.left_refresh_button()
        right_refresh = decimal_comparison_form.right_refresh_button()

        assert left_refresh is not None
        assert right_refresh is not None

        # Should contain refresh functionality
        left_str = str(left_refresh)
        right_str = str(right_refresh)

        assert "refresh" in left_str.lower()
        assert "refresh" in right_str.lower()

    def test_decimal_comparison_field_ordering(self, decimal_comparison_form):
        """Test that decimal fields maintain consistent ordering in comparison"""
        rendered = decimal_comparison_form.render_inputs()
        rendered_str = str(rendered)

        # Fields should appear in model definition order
        base_price_pos = rendered_str.find("base_price")
        discount_pos = rendered_str.find("discount")
        final_price_pos = rendered_str.find("final_price")
        margin_pos = rendered_str.find("margin")

        # Check relative ordering (allowing for multiple occurrences)
        assert base_price_pos < final_price_pos
        assert discount_pos >= 0 and margin_pos >= 0  # Both should be present

    def test_decimal_comparison_custom_labels(
        self, decimal_comparison_model, left_decimal_data, right_decimal_data
    ):
        """Test decimal comparison with custom labels"""
        left_form = PydanticForm(
            "custom_left", decimal_comparison_model, initial_values=left_decimal_data
        )
        right_form = PydanticForm(
            "custom_right", decimal_comparison_model, initial_values=right_decimal_data
        )

        comparison_form = ComparisonForm(
            name="custom_comparison",
            left_form=left_form,
            right_form=right_form,
            left_label="💰 Current Pricing",
            right_label="🎯 Target Pricing",
        )

        rendered = comparison_form.render_inputs()
        rendered_str = str(rendered)

        # Should contain custom labels
        assert "💰 Current Pricing" in rendered_str
        assert "🎯 Target Pricing" in rendered_str
