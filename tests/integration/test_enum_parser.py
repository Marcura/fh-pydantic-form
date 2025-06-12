from enum import Enum
from typing import List, Optional

import pytest
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from fh_pydantic_form.form_parser import (
    _identify_list_fields,
    _parse_enum_field,
    _parse_list_fields,
    _parse_non_list_fields,
)


class StatusEnum(Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"


class PriorityEnum(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class SimpleEnumModel(BaseModel):
    """Simple model with enum fields for parser testing."""

    status: StatusEnum
    priority: Optional[PriorityEnum] = None


class ComplexEnumModel(BaseModel):
    """Complex model with various enum field types for parser testing."""

    # Required enum fields
    status: StatusEnum = StatusEnum.NEW
    priority: PriorityEnum = PriorityEnum.MEDIUM

    # Optional enum fields
    optional_status: Optional[StatusEnum] = None

    # Mixed field types
    name: str = "Test"
    is_active: bool = True

    # Lists with enums
    status_history: List[StatusEnum] = Field(default_factory=list)
    priority_options: List[PriorityEnum] = Field(default_factory=list)


@pytest.mark.integration
class TestEnumFieldParsing:
    """Integration tests for enum field parsing from form data."""

    def test_parse_required_enum_field_valid_value(self):
        """Test parsing required enum field with valid value."""
        field_info = FieldInfo(annotation=StatusEnum)
        result = _parse_enum_field(
            "prefix_status", {"prefix_status": "PROCESSING"}, field_info
        )

        assert result == "PROCESSING"

    def test_parse_required_enum_field_missing(self):
        """Test parsing required enum field when missing from form data."""
        field_info = FieldInfo(annotation=StatusEnum)
        result = _parse_enum_field("prefix_status", {}, field_info)

        assert result is None

    def test_parse_optional_enum_field_valid_value(self):
        """Test parsing optional enum field with valid value."""
        field_info = FieldInfo(annotation=Optional[StatusEnum])
        result = _parse_enum_field(
            "prefix_status", {"prefix_status": "COMPLETED"}, field_info
        )

        assert result == "COMPLETED"

    def test_parse_optional_enum_field_empty_string(self):
        """Test parsing optional enum field with empty string (should become None)."""
        field_info = FieldInfo(annotation=Optional[StatusEnum])
        result = _parse_enum_field("prefix_status", {"prefix_status": ""}, field_info)

        assert result is None

    def test_parse_optional_enum_field_none_display_value(self):
        """Test parsing optional enum field with '-- None --' value."""
        field_info = FieldInfo(annotation=Optional[StatusEnum])
        result = _parse_enum_field(
            "prefix_status", {"prefix_status": "-- None --"}, field_info
        )

        assert result is None

    def test_parse_enum_field_invalid_value_passthrough(self):
        """Test that invalid enum values are passed through for later validation."""
        field_info = FieldInfo(annotation=StatusEnum)
        result = _parse_enum_field(
            "prefix_status", {"prefix_status": "INVALID_STATUS"}, field_info
        )

        # Should pass through invalid value for Pydantic to handle
        assert result == "INVALID_STATUS"

    def test_parse_integer_enum_field(self):
        """Test parsing enum field with integer values."""
        field_info = FieldInfo(annotation=PriorityEnum)
        result = _parse_enum_field(
            "prefix_priority", {"prefix_priority": "2"}, field_info
        )

        assert str(result) == "2"  # Passed as string for Pydantic conversion

    @pytest.mark.parametrize(
        "input_value, expected",
        [
            ("NEW", "NEW"),
            ("PROCESSING", "PROCESSING"),
            ("COMPLETED", "COMPLETED"),
            ("", None),  # For optional fields
            ("-- None --", None),  # For optional fields
            ("INVALID", "INVALID"),  # Invalid values passed through
        ],
    )
    def test_parametrized_enum_parsing(self, input_value, expected):
        """Test enum parsing with various input values."""
        field_info = FieldInfo(annotation=Optional[StatusEnum])
        result = _parse_enum_field(
            "prefix_status", {"prefix_status": input_value}, field_info
        )

        assert result == expected


@pytest.mark.integration
class TestEnumModelParsing:
    """Integration tests for parsing complete models with enum fields."""

    def test_parse_simple_enum_model_all_fields(self):
        """Test parsing simple enum model with all fields provided."""
        list_field_defs = _identify_list_fields(SimpleEnumModel)

        form_data = {
            "prefix_status": "PROCESSING",
            "prefix_priority": "3",  # HIGH priority (integer enum)
        }

        result = _parse_non_list_fields(
            form_data, SimpleEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": "PROCESSING",
            "priority": "3",  # String for Pydantic conversion
        }
        # Compare string representations to handle int vs string values
        assert str(result.get("status")) == str(expected["status"])
        assert str(result.get("priority")) == str(expected["priority"])

    def test_parse_simple_enum_model_optional_missing(self):
        """Test parsing simple enum model with optional field missing."""
        list_field_defs = _identify_list_fields(SimpleEnumModel)

        form_data = {
            "prefix_status": "NEW",
            # priority field missing
        }

        result = _parse_non_list_fields(
            form_data, SimpleEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": "NEW",
            "priority": None,  # Optional field defaults to None when missing
        }
        assert result == expected

    def test_parse_simple_enum_model_optional_empty(self):
        """Test parsing simple enum model with optional field as empty string."""
        list_field_defs = _identify_list_fields(SimpleEnumModel)

        form_data = {
            "prefix_status": "COMPLETED",
            "prefix_priority": "",  # Empty string for optional enum
        }

        result = _parse_non_list_fields(
            form_data, SimpleEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": "COMPLETED",
            "priority": None,  # Empty string converted to None for optional enum
        }
        assert result == expected

    def test_parse_complex_enum_model_mixed_fields(self):
        """Test parsing complex model with mixed enum and non-enum fields."""
        list_field_defs = _identify_list_fields(ComplexEnumModel)

        form_data = {
            "prefix_status": "PROCESSING",
            "prefix_priority": "1",  # LOW priority
            "prefix_optional_status": "",  # Empty optional enum
            "prefix_name": "Updated Name",
            "prefix_is_active": "on",  # Boolean field
        }

        result = _parse_non_list_fields(
            form_data, ComplexEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": "PROCESSING",
            "priority": "1",
            "optional_status": None,  # Empty string → None
            "name": "Updated Name",
            "is_active": True,  # Boolean parsing
        }
        # Compare string representations for enum values to handle int vs string
        assert str(result.get("status")) == str(expected["status"])
        assert str(result.get("priority")) == str(expected["priority"])
        assert result.get("optional_status") == expected["optional_status"]
        assert result.get("name") == expected["name"]
        assert result.get("is_active") == expected["is_active"]

    def test_parse_enum_list_fields(self):
        """Test parsing list fields containing enum values."""
        list_field_defs = _identify_list_fields(ComplexEnumModel)

        form_data = {
            # Simple enum list
            "prefix_status_history_0": "NEW",
            "prefix_status_history_1": "PROCESSING",
            "prefix_status_history_2": "COMPLETED",
            # Integer enum list
            "prefix_priority_options_0": "1",  # LOW
            "prefix_priority_options_1": "3",  # HIGH
        }

        result = _parse_list_fields(form_data, list_field_defs, base_prefix="prefix_")

        expected = {
            "status_history": ["NEW", "PROCESSING", "COMPLETED"],
            "priority_options": ["1", "3"],
        }
        # Compare string representations for enum values
        assert [str(x) for x in result.get("status_history", [])] == [
            str(x) for x in expected["status_history"]
        ]
        assert [str(x) for x in result.get("priority_options", [])] == [
            str(x) for x in expected["priority_options"]
        ]

    def test_parse_enum_list_with_new_indices(self):
        """Test parsing enum list fields with new_* indices."""
        list_field_defs = _identify_list_fields(ComplexEnumModel)

        form_data = {
            "prefix_status_history_0": "NEW",
            "prefix_status_history_new_12345": "PROCESSING",
            "prefix_status_history_1": "COMPLETED",
        }

        result = _parse_list_fields(form_data, list_field_defs, base_prefix="prefix_")

        # Should maintain order based on appearance in form_data
        expected = {
            "status_history": ["NEW", "PROCESSING", "COMPLETED"],
        }
        # Filter out any undefined fields that might be added
        filtered_result = {k: v for k, v in result.items() if k in expected}
        assert filtered_result == expected

    def test_parse_invalid_enum_values_in_lists(self):
        """Test that invalid enum values in lists are passed through."""
        list_field_defs = _identify_list_fields(ComplexEnumModel)

        form_data = {
            "prefix_status_history_0": "VALID_STATUS",
            "prefix_status_history_1": "INVALID_STATUS",  # Invalid value
            "prefix_priority_options_0": "99",  # Invalid priority value
        }

        result = _parse_list_fields(form_data, list_field_defs, base_prefix="prefix_")

        expected = {
            "status_history": [
                "VALID_STATUS",
                "INVALID_STATUS",
            ],  # Invalid passed through
            "priority_options": ["99"],  # Invalid passed through
        }
        # Compare string representations
        assert [str(x) for x in result.get("status_history", [])] == [
            str(x) for x in expected["status_history"]
        ]
        assert [str(x) for x in result.get("priority_options", [])] == [
            str(x) for x in expected["priority_options"]
        ]


@pytest.mark.integration
class TestEnumParserEdgeCases:
    """Integration tests for edge cases in enum parsing."""

    def test_parse_empty_form_data(self):
        """Test parsing with completely empty form data."""
        list_field_defs = _identify_list_fields(SimpleEnumModel)

        result = _parse_non_list_fields(
            {}, SimpleEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": None,  # Required field missing → None
            "priority": None,  # Optional field missing → None
        }
        assert result == expected

    def test_parse_with_extra_fields(self):
        """Test parsing ignores extra fields not in model."""
        list_field_defs = _identify_list_fields(SimpleEnumModel)

        form_data = {
            "prefix_status": "NEW",
            "prefix_priority": "2",
            "prefix_extra_field": "ignored",  # Not in model
            "other_prefix_field": "also_ignored",  # Different prefix
        }

        result = _parse_non_list_fields(
            form_data, SimpleEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": "NEW",
            "priority": "2",
            # Extra fields should be ignored
        }
        # Compare string representations for enum values
        assert str(result.get("status")) == str(expected["status"])
        assert str(result.get("priority")) == str(expected["priority"])

    def test_parse_with_mixed_case_enum_values(self):
        """Test parsing with mixed case enum values (should pass through)."""
        list_field_defs = _identify_list_fields(SimpleEnumModel)

        form_data = {
            "prefix_status": "processing",  # Lowercase (invalid but passed through)
            "prefix_priority": "HIGH",  # Wrong type but passed through
        }

        result = _parse_non_list_fields(
            form_data, SimpleEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "status": "processing",  # Invalid case passed through
            "priority": "HIGH",  # Wrong type passed through
        }
        assert result == expected

    def test_parse_enum_with_special_characters(self):
        """Test parsing enum values containing special characters."""

        class SpecialEnum(Enum):
            DASH_VALUE = "DASH-VALUE"
            UNDERSCORE_VALUE = "UNDERSCORE_VALUE"
            SPACE_VALUE = "SPACE VALUE"

        class SpecialEnumModel(BaseModel):
            special: SpecialEnum

        list_field_defs = _identify_list_fields(SpecialEnumModel)

        form_data = {
            "prefix_special": "DASH-VALUE",
        }

        result = _parse_non_list_fields(
            form_data, SpecialEnumModel, list_field_defs, base_prefix="prefix_"
        )

        expected = {
            "special": "DASH-VALUE",
        }
        assert result == expected

    @pytest.mark.parametrize(
        "form_field_name, enum_value",
        [
            ("status", "NEW"),
            ("priority", "1"),
            ("optional_status", "PROCESSING"),
        ],
    )
    def test_parametrized_field_parsing(self, form_field_name, enum_value):
        """Test parsing various enum fields with parametrized inputs."""
        list_field_defs = _identify_list_fields(ComplexEnumModel)

        form_data = {f"prefix_{form_field_name}": enum_value}

        result = _parse_non_list_fields(
            form_data, ComplexEnumModel, list_field_defs, base_prefix="prefix_"
        )

        # Should contain the parsed field with the expected value
        assert form_field_name in result
        assert str(result[form_field_name]) == str(enum_value)


@pytest.mark.integration
class TestEnumParsingWithFormRenderer:
    """Integration tests using the full form renderer parse method."""

    def test_enum_form_renderer_parse_valid_data(self, enum_form_renderer):
        """Test parsing valid enum data through form renderer."""
        form_data = {
            "enum_test_status": "PROCESSING",
            "enum_test_priority": "MEDIUM",  # MEDIUM priority
            "enum_test_priority_int": 2,
        }

        result = enum_form_renderer.parse(form_data)

        expected = {
            "status": "PROCESSING",
            "priority": "MEDIUM",
            "priority_int": 2,
        }
        assert result == expected

    def test_enum_form_renderer_parse_optional_none(self, enum_form_renderer):
        """Test parsing enum form with optional field as None."""
        form_data = {
            "enum_test_status": "NEW",
            "enum_test_priority": "",  # Empty string for None
            "enum_test_priority_int": None,
        }

        result = enum_form_renderer.parse(form_data)

        expected = {
            "status": "NEW",
            "priority": None,
            "priority_int": None,
        }
        assert result == expected

    def test_complex_enum_form_renderer_parse(self, complex_enum_form_renderer):
        """Test parsing complex enum form with mixed field types."""
        form_data = {
            "complex_enum_test_status": "COMPLETED",
            "complex_enum_test_shipping_method": "OVERNIGHT",
            "complex_enum_test_priority": "3",  # HIGH
            "complex_enum_test_name": "Updated Order",
            "complex_enum_test_order_id": "67890",
            "complex_enum_test_status_history_0": "NEW",
            "complex_enum_test_status_history_1": "PROCESSING",
            "complex_enum_test_available_priorities_0": "1",  # LOW
            "complex_enum_test_available_priorities_1": "2",  # MEDIUM
        }

        result = complex_enum_form_renderer.parse(form_data)

        # Check non-list fields
        assert result["status"] == "COMPLETED"
        assert result["shipping_method"] == "OVERNIGHT"
        assert result["priority"] == "3"
        assert result["name"] == "Updated Order"
        assert result["order_id"] == "67890"

        # Check list fields
        assert result["status_history"] == ["NEW", "PROCESSING"]
        assert result["available_priorities"] == ["1", "2"]
