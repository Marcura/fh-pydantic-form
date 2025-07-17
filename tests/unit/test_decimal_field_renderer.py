import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

import decimal
from decimal import Decimal

import pytest
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import DecimalFieldRenderer
from fh_pydantic_form.ui_style import SpacingTheme


class TestDecimalFieldRenderer:
    """Unit tests for DecimalFieldRenderer"""

    @pytest.fixture
    def decimal_field_info(self):
        """Create a FieldInfo for decimal fields"""
        return FieldInfo(annotation=decimal.Decimal)

    @pytest.fixture
    def optional_decimal_field_info(self):
        """Create a FieldInfo for optional decimal fields"""
        return FieldInfo(annotation=decimal.Decimal, default=None)

    def test_decimal_renderer_initialization(self, decimal_field_info):
        """Test basic renderer initialization"""
        renderer = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("99.99"),
            prefix="test_",
        )

        assert renderer.field_name == "test_price"
        assert renderer.original_field_name == "price"
        assert renderer.value == Decimal("99.99")
        assert renderer.disabled is False

    @pytest.mark.parametrize(
        "value,expected_display",
        [
            (Decimal("123.45"), "123.45"),
            (Decimal("0"), "0"),
            (Decimal("-99.99"), "-99.99"),
            (Decimal("1000000.123456"), "1000000.123456"),
            (Decimal("0.0000000001"), "0.0000000001"),
            (None, ""),
            ("123.45", "123.45"),  # String input
            (123.45, "123.45"),  # Float input
        ],
    )
    def test_decimal_value_display(self, decimal_field_info, value, expected_display):
        """Test decimal values are displayed correctly"""
        renderer = DecimalFieldRenderer(
            field_name="amount",
            field_info=decimal_field_info,
            value=value,
            prefix="test_",
        )

        input_element = renderer.render_input()

        # Check that the value attribute is set correctly
        assert input_element.attrs.get("value") == expected_display

    def test_decimal_renderer_html_structure(self, decimal_field_info):
        """Test the rendered HTML structure"""
        renderer = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("49.99"),
            prefix="form_",
        )

        input_element = renderer.render_input()

        # Verify input attributes
        assert input_element.attrs.get("type") == "number"
        assert input_element.attrs.get("step") == "any"
        assert input_element.attrs.get("id") == "form_price"
        assert input_element.attrs.get("name") == "form_price"
        assert "w-full" in input_element.attrs.get(
            "cls", ""
        ) or "w-full" in input_element.attrs.get("class", "")

    def test_decimal_renderer_disabled_state(self, decimal_field_info):
        """Test disabled state rendering"""
        renderer = DecimalFieldRenderer(
            field_name="amount",
            field_info=decimal_field_info,
            value=Decimal("100.00"),
            disabled=True,
        )

        input_element = renderer.render_input()

        # Should have disabled attribute
        assert input_element.attrs.get("disabled") is True

    def test_decimal_renderer_required_optional(
        self, decimal_field_info, optional_decimal_field_info
    ):
        """Test required vs optional decimal fields"""
        # Required field
        required_renderer = DecimalFieldRenderer(
            field_name="required_amount", field_info=decimal_field_info, value=None
        )

        required_input = required_renderer.render_input()
        assert required_input.attrs.get("required") is True
        assert "Optional" not in required_input.attrs.get("placeholder", "")

        # Optional field
        optional_renderer = DecimalFieldRenderer(
            field_name="optional_amount",
            field_info=optional_decimal_field_info,
            value=None,
        )

        optional_input = optional_renderer.render_input()
        assert optional_input.attrs.get("required") is not True
        assert "optional" in optional_input.attrs.get("placeholder", "").lower()

    def test_decimal_renderer_spacing_themes(self, decimal_field_info):
        """Test renderer with different spacing themes"""
        for spacing in [SpacingTheme.NORMAL, SpacingTheme.COMPACT]:
            renderer = DecimalFieldRenderer(
                field_name="amount",
                field_info=decimal_field_info,
                value=Decimal("50.00"),
                spacing=spacing,
            )

            # Should render without error
            input_element = renderer.render_input()
            assert input_element is not None
            assert input_element.attrs.get("type") == "number"

    def test_decimal_renderer_with_prefix(self, decimal_field_info):
        """Test renderer with field prefix"""
        renderer = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("199.99"),
            prefix="product_form_",
        )

        input_element = renderer.render_input()

        assert input_element.attrs.get("id") == "product_form_price"
        assert input_element.attrs.get("name") == "product_form_price"

    def test_decimal_renderer_label_rendering(self, decimal_field_info):
        """Test label rendering for decimal fields"""
        renderer = DecimalFieldRenderer(
            field_name="unit_price",
            field_info=decimal_field_info,
            value=Decimal("25.50"),
            label_color="emerald",
        )

        label_element = renderer.render_label()

        # Should contain the formatted field name
        assert "Unit Price" in str(label_element)
        assert label_element.attrs.get("for") == "unit_price"

    def test_decimal_renderer_complete_render(self, decimal_field_info):
        """Test complete field rendering (label + input)"""
        renderer = DecimalFieldRenderer(
            field_name="total_amount",
            field_info=decimal_field_info,
            value=Decimal("999.99"),
        )

        complete_field = renderer.render()

        # Should contain both label and input
        assert complete_field is not None
        field_str = str(complete_field)
        assert "Total Amount" in field_str
        assert "999.99" in field_str

    def test_decimal_renderer_high_precision(self, decimal_field_info):
        """Test handling of high precision decimal values"""
        high_precision_value = Decimal("3.14159265358979323846")

        renderer = DecimalFieldRenderer(
            field_name="pi", field_info=decimal_field_info, value=high_precision_value
        )

        input_element = renderer.render_input()

        # Should preserve full precision in display
        assert input_element.attrs.get("value") == str(high_precision_value)

    def test_decimal_renderer_negative_values(self, decimal_field_info):
        """Test handling of negative decimal values"""
        negative_value = Decimal("-1234.56")

        renderer = DecimalFieldRenderer(
            field_name="balance", field_info=decimal_field_info, value=negative_value
        )

        input_element = renderer.render_input()

        assert input_element.attrs.get("value") == "-1234.56"

    def test_decimal_renderer_zero_values(self, decimal_field_info):
        """Test handling of zero decimal values"""
        zero_values = [Decimal("0"), Decimal("0.0"), Decimal("0.00")]

        for zero_val in zero_values:
            renderer = DecimalFieldRenderer(
                field_name="amount", field_info=decimal_field_info, value=zero_val
            )

            input_element = renderer.render_input()

            # All should display as "0"
            assert input_element.attrs.get("value") == "0"

    def test_decimal_renderer_field_path(self, decimal_field_info):
        """Test renderer with field path for nested structures"""
        renderer = DecimalFieldRenderer(
            field_name="price",
            field_info=decimal_field_info,
            value=Decimal("89.99"),
            field_path=["product", "pricing", "price"],
        )

        # Should initialize without error
        assert renderer.field_path == ["product", "pricing", "price"]

        input_element = renderer.render_input()
        assert input_element is not None
