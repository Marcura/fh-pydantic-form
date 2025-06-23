from enum import Enum
from typing import Optional

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from fh_pydantic_form.defaults import default_for_annotation
from fh_pydantic_form.field_renderers import EnumFieldRenderer
from fh_pydantic_form.form_parser import _parse_enum_field
from fh_pydantic_form.type_helpers import _is_enum_type


# Test enum with various value types for property testing
class PropertyTestEnum(Enum):
    STRING_VAL = "string_value"
    INT_VAL = 42
    FLOAT_VAL = 3.14
    TUPLE_VAL = ("tuple", "value")
    BOOL_VAL = True


class PropertyTestModel(BaseModel):
    enum_field: PropertyTestEnum
    optional_enum_field: Optional[PropertyTestEnum] = None


@pytest.mark.property
class TestEnumRobustnessProperties:
    """Property-based tests for enum handling robustness."""

    @given(st.text())
    def test_enum_parser_handles_arbitrary_strings(self, arbitrary_string):
        """Test that enum parser doesn't crash on arbitrary string inputs."""
        field_info = FieldInfo(annotation=PropertyTestEnum)

        # Should not raise exception, even with invalid values
        try:
            result = _parse_enum_field(
                "test_field", {"test_field": arbitrary_string}, field_info
            )
            # Result should be the input string (passed through for validation)
            assert result == arbitrary_string
        except Exception as e:
            # If there's an exception, it should be a specific type we expect
            # (Not a general crash)
            assert isinstance(e, (ValueError, TypeError, AttributeError))

    @given(st.text())
    def test_optional_enum_parser_handles_arbitrary_strings(self, arbitrary_string):
        """Test that optional enum parser handles arbitrary strings correctly."""
        field_info = FieldInfo(annotation=Optional[PropertyTestEnum])

        try:
            result = _parse_enum_field(
                "test_field", {"test_field": arbitrary_string}, field_info
            )

            # Empty string and "-- None --" should become None
            if arbitrary_string in ("", "-- None --"):
                assert result is None
            else:
                assert result == arbitrary_string
        except Exception as e:
            assert isinstance(e, (ValueError, TypeError, AttributeError))

    @given(st.text(min_size=1, max_size=50))
    def test_enum_renderer_handles_arbitrary_field_names(self, field_name):
        """Test that enum renderer doesn't crash with arbitrary field names."""
        # Filter out field names that would be invalid HTML attributes
        if not field_name.replace("_", "").replace("-", "").isalnum():
            return

        field_info = FieldInfo(annotation=PropertyTestEnum)

        try:
            renderer = EnumFieldRenderer(
                field_name=field_name,
                field_info=field_info,
                value=PropertyTestEnum.STRING_VAL,
            )

            html_output = str(renderer.render_input())

            # Should produce some HTML output
            assert isinstance(html_output, str)
            assert len(html_output) > 0

            # Should contain the field name somewhere
            assert field_name in html_output

        except Exception as e:
            # Allow specific expected exceptions
            assert isinstance(e, (ValueError, TypeError, AttributeError))

    @given(st.text(max_size=100))
    def test_enum_renderer_handles_arbitrary_prefixes(self, prefix):
        """Test enum renderer with arbitrary prefix values."""
        # Skip problematic prefixes that would break HTML
        if any(char in prefix for char in "<>\"'&"):
            return

        field_info = FieldInfo(annotation=PropertyTestEnum)

        try:
            renderer = EnumFieldRenderer(
                field_name="test_field",
                field_info=field_info,
                prefix=prefix,
                value=PropertyTestEnum.INT_VAL,
            )

            html_output = str(renderer.render_input())
            assert isinstance(html_output, str)

            # If prefix is valid, it should appear in the output
            if prefix and prefix.replace("_", "").replace("-", "").isalnum():
                expected_name = f"{prefix}test_field"
                assert expected_name in html_output

        except Exception as e:
            assert isinstance(e, (ValueError, TypeError, AttributeError))

    @given(st.sampled_from([member.value for member in PropertyTestEnum]))
    def test_enum_renderer_handles_all_enum_values(self, enum_value):
        """Test that enum renderer handles all possible enum values correctly."""
        field_info = FieldInfo(annotation=PropertyTestEnum)

        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=enum_value,
        )

        html_output = str(renderer.render_input())

        # Should contain the string representation of the value
        assert str(enum_value) in html_output

        # Should mark the correct option as selected
        assert "selected" in html_output

    @given(st.booleans())
    def test_enum_renderer_disabled_state_robustness(self, disabled_state):
        """Test enum renderer disabled state with property-based input."""
        field_info = FieldInfo(annotation=PropertyTestEnum)

        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            disabled=disabled_state,
        )

        html_output = str(renderer.render_input())

        if disabled_state:
            assert "disabled" in html_output

        # Should always produce valid HTML regardless of disabled state
        assert "select" in html_output.lower()

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=20), st.text(max_size=50), max_size=10
        )
    )
    def test_enum_parser_ignores_unrelated_form_data(self, form_data):
        """Test that enum parser only processes its own field from form data."""
        # Add our specific field to the form data
        form_data["test_enum_field"] = "STRING_VAL"

        field_info = FieldInfo(annotation=PropertyTestEnum)

        result = _parse_enum_field("test_enum_field", form_data, field_info)

        # Should only return our field's value
        assert result == "STRING_VAL"

    @given(
        st.lists(
            st.sampled_from([member.value for member in PropertyTestEnum]),
            min_size=0,
            max_size=5,
        )
    )
    def test_enum_default_annotation_consistency(self, enum_values):
        """Test that default_for_annotation is consistent for enum types."""
        # This tests the deterministic nature of enum defaults
        result1 = default_for_annotation(PropertyTestEnum)
        result2 = default_for_annotation(PropertyTestEnum)

        # Should always return the same default
        assert result1 == result2

        # Should return the first enum member's value
        first_member_value = list(PropertyTestEnum)[0].value
        assert result1 == first_member_value

    @given(st.text(min_size=1))
    def test_enum_type_detection_robustness(self, arbitrary_annotation):
        """Test that _is_enum_type doesn't crash on arbitrary inputs."""
        try:
            result = _is_enum_type(arbitrary_annotation)
            # Should return a boolean
            assert isinstance(result, bool)
            # For string inputs, should return False
            assert result is False
        except Exception as e:
            # Allow specific type-related exceptions
            assert isinstance(e, (TypeError, AttributeError))


@pytest.mark.property
class TestEnumFormDataRobustness:
    """Property-based tests for enum form data handling."""

    @given(
        st.dictionaries(
            st.text(min_size=1, max_size=30).filter(lambda x: x.isalnum() or "_" in x),
            st.text(max_size=100),
            max_size=20,
        )
    )
    def test_form_parsing_with_arbitrary_data(self, form_data):
        """Test that form parsing handles arbitrary form data gracefully."""
        from fh_pydantic_form.form_parser import (
            _identify_list_fields,
            _parse_non_list_fields,
        )

        # Add valid enum data to ensure we have something to parse
        form_data["test_enum_field"] = "STRING_VAL"

        list_field_defs = _identify_list_fields(PropertyTestModel)

        try:
            result = _parse_non_list_fields(
                form_data, PropertyTestModel, list_field_defs, base_prefix="test_"
            )

            # Should return a dictionary
            assert isinstance(result, dict)

            # If our field was parsed, it should be in the result
            if "enum_field" in result:
                assert result["enum_field"] == "STRING_VAL"

        except Exception as e:
            # Allow specific parsing exceptions
            assert isinstance(e, (ValueError, TypeError, KeyError))

    @given(st.integers(min_value=0, max_value=1000))
    def test_enum_list_parsing_with_various_indices(self, index_value):
        """Test enum list parsing with various index values."""
        from fh_pydantic_form.form_parser import _parse_list_item_key

        class ListEnumModel(BaseModel):
            enum_list: list[PropertyTestEnum]

        list_field_defs = {
            "enum_list": {
                "item_type": PropertyTestEnum,
                "is_model_type": False,
                "field_info": None,
            }
        }

        # Test with regular numeric index
        key = f"test_enum_list_{index_value}"
        result = _parse_list_item_key(key, list_field_defs, base_prefix="test_")

        if result:
            field_name, idx_str, subfield, is_simple_list = result
            assert field_name == "enum_list"
            assert idx_str == str(index_value)
            assert subfield is None
            assert is_simple_list is True

    @given(
        st.text(min_size=1, max_size=20).filter(lambda x: x.replace("_", "").isalnum())
    )
    def test_enum_field_name_variations(self, field_name):
        """Test enum handling with various field name patterns."""
        # Create a dynamic model with the given field name
        try:
            # Test that field info creation doesn't crash
            field_info = FieldInfo(annotation=PropertyTestEnum)

            # Test that renderer creation doesn't crash
            renderer = EnumFieldRenderer(
                field_name=field_name,
                field_info=field_info,
            )

            # Should produce some output
            html_output = str(renderer.render_input())
            assert isinstance(html_output, str)
            assert len(html_output) > 0

        except Exception as e:
            # Allow specific expected exceptions
            assert isinstance(e, (ValueError, TypeError, AttributeError))


@pytest.mark.property
class TestEnumEdgeCases:
    """Property-based tests for enum edge cases and boundary conditions."""

    def test_empty_enum_handling(self):
        """Test handling of empty enum (no members)."""

        class EmptyEnum(Enum):
            pass

        # Should not crash when getting default
        result = default_for_annotation(EmptyEnum)
        assert result is None

        # Should be detected as enum type
        assert _is_enum_type(EmptyEnum) is True

    @given(st.integers())
    def test_enum_with_integer_values_consistency(self, int_value):
        """Test that enum handling is consistent with integer-valued enums."""

        class IntEnum(Enum):
            TEST_VALUE = int_value

        # Should be detected as enum
        assert _is_enum_type(IntEnum) is True

        # Default should be the integer value
        default = default_for_annotation(IntEnum)
        assert default == int_value

    @given(st.floats(allow_nan=False, allow_infinity=False))
    def test_enum_with_float_values_consistency(self, float_value):
        """Test that enum handling works with float-valued enums."""

        class FloatEnum(Enum):
            TEST_VALUE = float_value

        # Should be detected as enum
        assert _is_enum_type(FloatEnum) is True

        # Default should be the float value
        default = default_for_annotation(FloatEnum)
        assert default == float_value

    @given(st.tuples(st.text(max_size=10), st.integers(min_value=0, max_value=100)))
    def test_enum_with_complex_values(self, complex_value):
        """Test enum handling with complex tuple values."""

        class ComplexEnum(Enum):
            TEST_VALUE = complex_value

        # Should be detected as enum
        assert _is_enum_type(ComplexEnum) is True

        # Default should be the complex value
        default = default_for_annotation(ComplexEnum)
        assert default == complex_value

    def test_enum_inheritance_robustness(self):
        """Test that enum inheritance is handled correctly."""

        class BaseEnum(Enum):
            BASE_VALUE = "base"

        # Use functional API to avoid Python 3.12 inheritance restrictions
        ExtendedEnum = Enum(
            "ExtendedEnum",
            [("BASE_VALUE", "base"), ("EXTENDED_VALUE", "extended")],
        )

        # Both should be detected as enums
        assert _is_enum_type(BaseEnum) is True
        assert _is_enum_type(ExtendedEnum) is True

        # Defaults should work for both
        base_default = default_for_annotation(BaseEnum)
        extended_default = default_for_annotation(ExtendedEnum)

        assert base_default is not None
        assert extended_default is not None
