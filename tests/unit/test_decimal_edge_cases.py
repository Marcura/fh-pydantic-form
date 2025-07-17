import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

import decimal
from decimal import Decimal
from typing import List

import pytest
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm
from fh_pydantic_form.field_renderers import DecimalFieldRenderer


class TestDecimalEdgeCases:
    """Test decimal edge cases and boundary conditions"""

    @pytest.fixture
    def decimal_edge_model(self):
        """Model for testing decimal edge cases"""

        class DecimalEdgeModel(BaseModel):
            tiny_value: Decimal
            huge_value: Decimal
            precise_value: Decimal
            negative_value: Decimal
            zero_value: Decimal

        return DecimalEdgeModel

    @pytest.fixture
    def decimal_edge_form(self, decimal_edge_model):
        """Form for testing decimal edge cases"""
        return PydanticForm("edge_test", decimal_edge_model)

    @pytest.mark.parametrize(
        "edge_value",
        [
            Decimal("0.0000000001"),  # Very small positive
            Decimal("-0.0000000001"),  # Very small negative
            Decimal("999999999999.99"),  # Very large positive
            Decimal("-999999999999.99"),  # Very large negative
            Decimal("3.14159265358979323846"),  # High precision pi
            Decimal("2.71828182845904523536"),  # High precision e
            Decimal("1.41421356237309504880"),  # High precision sqrt(2)
            Decimal("0"),  # Zero
            Decimal("0.0"),  # Zero with decimal
            Decimal("0.00"),  # Zero with currency precision
            Decimal("1"),  # One
            Decimal("-1"),  # Negative one
        ],
    )
    def test_decimal_edge_values_rendering(self, edge_value):
        """Test decimal renderer with edge case values"""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)
        renderer = DecimalFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=edge_value,
            prefix="test_",
        )

        input_element = renderer.render_input()

        # Should render without error
        assert input_element is not None
        # The value should be formatted without scientific notation
        expected_value = format(edge_value, "f") if edge_value != 0 else "0"
        assert input_element.attrs.get("value") == expected_value

    def test_decimal_precision_preservation(self, decimal_edge_form):
        """Test that decimal precision is maintained through form lifecycle"""
        high_precision_value = Decimal(
            "3.14159265358979323846264338327950288419716939937510"
        )

        # Set initial value
        decimal_edge_form.values_dict = {"precise_value": high_precision_value}

        # Render form
        rendered = decimal_edge_form.render_inputs()
        assert rendered is not None

        # Simulate form submission with high precision
        form_data = {
            "edge_test_tiny_value": "0.0000000001",
            "edge_test_huge_value": "999999999999.99",
            "edge_test_precise_value": str(high_precision_value),
            "edge_test_negative_value": "-1234.56789",
            "edge_test_zero_value": "0",
        }

        parsed = decimal_edge_form.parse(form_data)

        # Should preserve precision as string (Pydantic will convert)
        assert parsed["precise_value"] == str(high_precision_value)

    def test_decimal_vs_float_precision(self):
        """Test that decimals don't lose precision like floats"""
        # This value loses precision when converted to float
        precise_decimal = Decimal("0.1") + Decimal("0.2")
        float_result = 0.1 + 0.2

        # Decimal should be exactly 0.3
        assert precise_decimal == Decimal("0.3")

        # Float should not be exactly 0.3
        assert float_result != 0.3

        # Test in renderer
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)
        renderer = DecimalFieldRenderer(
            field_name="precise", field_info=field_info, value=precise_decimal
        )

        input_element = renderer.render_input()
        assert input_element.attrs.get("value") == "0.3"

    def test_decimal_scientific_notation_handling(self):
        """Test handling of scientific notation in decimals"""
        scientific_values = [
            Decimal("1.23e-4"),  # 0.000123
            Decimal("4.56e10"),  # 45600000000
            Decimal("7.89e-10"),  # 0.0000000789
            Decimal("1.23e+5"),  # 123000
        ]

        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)

        for value in scientific_values:
            renderer = DecimalFieldRenderer(
                field_name="scientific", field_info=field_info, value=value
            )

            input_element = renderer.render_input()

            # Should render without error
            assert input_element is not None
            # Value should be formatted without scientific notation
            expected_value = format(value, "f") if value != 0 else "0"
            assert input_element.attrs.get("value") == expected_value

    def test_decimal_boundary_conditions(self):
        """Test decimal boundary conditions"""
        boundary_values = [
            # Maximum positive value (implementation dependent)
            Decimal("9" * 28),
            # Maximum negative value
            Decimal("-" + "9" * 28),
            # Smallest positive value
            Decimal("1e-28"),
            # Smallest negative value
            Decimal("-1e-28"),
        ]

        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)

        for value in boundary_values:
            try:
                renderer = DecimalFieldRenderer(
                    field_name="boundary", field_info=field_info, value=value
                )

                input_element = renderer.render_input()
                assert input_element is not None
            except (decimal.InvalidOperation, decimal.Overflow):
                # Some boundary values might exceed decimal limits
                # This is expected behavior
                pass

    def test_decimal_special_values_handling(self):
        """Test handling of special decimal values"""
        # Test with None
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)
        renderer = DecimalFieldRenderer(
            field_name="special", field_info=field_info, value=None
        )

        input_element = renderer.render_input()
        assert input_element.attrs.get("value") == ""

    def test_decimal_string_conversion_edge_cases(self):
        """Test edge cases in string to decimal conversion"""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)

        # Test with string input
        string_value = "123.456789"
        renderer = DecimalFieldRenderer(
            field_name="string_test", field_info=field_info, value=string_value
        )

        input_element = renderer.render_input()
        assert input_element.attrs.get("value") == "123.456789"

    def test_decimal_list_edge_cases(self):
        """Test edge cases with lists of decimals"""

        class DecimalListModel(BaseModel):
            amounts: List[Decimal] = Field(default_factory=list)

        form = PydanticForm("list_test", DecimalListModel)

        # Test with various decimal values in list
        form_data = {
            "list_test_amounts_0": "0.0000000001",
            "list_test_amounts_1": "999999999999.99",
            "list_test_amounts_2": "3.14159265358979323846",
            "list_test_amounts_3": "-1234.56789",
            "list_test_amounts_4": "0",
        }

        parsed = form.parse(form_data)

        assert len(parsed["amounts"]) == 5
        assert parsed["amounts"][0] == "0.0000000001"
        assert parsed["amounts"][1] == "999999999999.99"
        assert parsed["amounts"][2] == "3.14159265358979323846"
        assert parsed["amounts"][3] == "-1234.56789"
        assert parsed["amounts"][4] == "0"

    def test_decimal_context_precision(self):
        """Test decimal context and precision handling"""
        # Test with different decimal contexts
        original_context = decimal.getcontext()

        try:
            # Set high precision context
            decimal.getcontext().prec = 50

            high_precision_value = Decimal("1") / Decimal("3")

            from pydantic.fields import FieldInfo

            field_info = FieldInfo(annotation=Decimal)
            renderer = DecimalFieldRenderer(
                field_name="context_test",
                field_info=field_info,
                value=high_precision_value,
            )

            input_element = renderer.render_input()

            # Should render with the context precision
            assert input_element is not None
            assert (
                len(input_element.attrs.get("value", "")) > 10
            )  # Should be a long decimal

        finally:
            # Restore original context
            decimal.setcontext(original_context)

    def test_decimal_locale_independence(self):
        """Test that decimal handling is locale-independent"""
        # Decimals should always use . as decimal separator regardless of locale
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)

        value = Decimal("1234.56")
        renderer = DecimalFieldRenderer(
            field_name="locale_test", field_info=field_info, value=value
        )

        input_element = renderer.render_input()

        # Should always use . as decimal separator
        assert "1234.56" in input_element.attrs.get("value", "")
        assert "1234,56" not in input_element.attrs.get("value", "")  # Not comma

    def test_decimal_rounding_behavior(self):
        """Test decimal rounding behavior"""
        # Test that decimal values are not unexpectedly rounded
        unrounded_value = Decimal("1.23456789012345678901234567890")

        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)
        renderer = DecimalFieldRenderer(
            field_name="rounding_test", field_info=field_info, value=unrounded_value
        )

        input_element = renderer.render_input()

        # Should preserve the full value without rounding
        assert input_element.attrs.get("value") == str(unrounded_value)

    def test_decimal_memory_efficiency(self):
        """Test that decimal handling is memory efficient"""
        # Create many decimal renderers to test memory usage
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)

        renderers = []
        for i in range(1000):
            renderer = DecimalFieldRenderer(
                field_name=f"test_{i}",
                field_info=field_info,
                value=Decimal(f"{i}.{i:02d}"),
            )
            renderers.append(renderer)

        # Should create successfully without memory issues
        assert len(renderers) == 1000

        # All should render
        for renderer in renderers[:10]:  # Test first 10
            input_element = renderer.render_input()
            assert input_element is not None

    def test_decimal_thread_safety(self):
        """Test decimal operations are thread-safe"""
        import threading
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=Decimal)
        results = []

        def create_renderer(value):
            renderer = DecimalFieldRenderer(
                field_name="thread_test",
                field_info=field_info,
                value=Decimal(str(value)),
            )
            input_element = renderer.render_input()
            results.append(input_element.attrs.get("value"))

        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_renderer, args=(i * 1.5,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Should have all results
        assert len(results) == 10
        # All should be valid decimal strings
        for result in results:
            assert result is not None
            assert "." in result or result == "0"
