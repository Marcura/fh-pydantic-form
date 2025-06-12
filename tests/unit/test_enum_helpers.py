from enum import Enum
from typing import List, Optional, Union

import pytest

from fh_pydantic_form.type_helpers import (
    _get_underlying_type_if_optional,
    _is_enum_type,
    _is_optional_type,
)


class StatusEnumType(Enum):
    """Test enum for type detection tests."""

    OPTION_A = "A"
    OPTION_B = "B"
    OPTION_C = "C"


class PriorityEnumType(Enum):
    """Test enum with integer values."""

    FIRST = 1
    SECOND = 2
    THIRD = 3


class TestIsEnumType:
    """Test the _is_enum_type function."""

    def test_enum_type_detection(self):
        """Test that Enum types are correctly detected."""
        assert _is_enum_type(StatusEnumType) is True

    def test_optional_enum_type_detection(self):
        """Test that Optional[Enum] types are correctly detected."""
        assert _is_enum_type(Optional[StatusEnumType]) is True

    def test_union_with_enum_and_none(self):
        """Test that Union[Enum, None] is detected as enum type."""
        assert _is_enum_type(Union[StatusEnumType, None]) is True

    def test_union_with_enum_and_none_reversed(self):
        """Test that Union[None, Enum] is detected as enum type."""
        assert _is_enum_type(Union[None, StatusEnumType]) is True

    def test_non_enum_types_not_detected(self):
        """Test that non-enum types are not detected as enum types."""
        assert _is_enum_type(str) is False
        assert _is_enum_type(int) is False
        assert _is_enum_type(bool) is False
        assert _is_enum_type(list) is False

    def test_non_enum_optional_types_not_detected(self):
        """Test that Optional[non-enum] types are not detected as enum types."""
        assert _is_enum_type(Optional[str]) is False
        assert _is_enum_type(Optional[int]) is False

    def test_union_without_enum_not_detected(self):
        """Test that Union types without enums are not detected."""
        assert _is_enum_type(Union[str, int]) is False

    def test_list_of_enum_not_detected_as_enum_type(self):
        """Test that List[Enum] is not detected as an enum type itself."""
        assert _is_enum_type(List[StatusEnumType]) is False

    def test_int_enum_detection(self):
        """Test that integer-valued enums are detected."""
        assert _is_enum_type(PriorityEnumType) is True
        assert _is_enum_type(Optional[PriorityEnumType]) is True


class TestEnumTypeIntegration:
    """Test enum type helpers integration with other type functions."""

    def test_optional_enum_underlying_type_extraction(self):
        """Test that underlying enum type is correctly extracted from Optional."""
        underlying = _get_underlying_type_if_optional(Optional[StatusEnumType])
        assert underlying is StatusEnumType
        assert _is_enum_type(underlying) is True

    def test_union_enum_none_underlying_type_extraction(self):
        """Test extraction from Union[Enum, None]."""
        underlying = _get_underlying_type_if_optional(Union[StatusEnumType, None])
        assert underlying is StatusEnumType
        assert _is_enum_type(underlying) is True

    def test_optional_enum_is_optional(self):
        """Test that Optional[Enum] is correctly identified as optional."""
        assert _is_optional_type(Optional[StatusEnumType]) is True

    def test_required_enum_not_optional(self):
        """Test that required Enum is not identified as optional."""
        assert _is_optional_type(StatusEnumType) is False

    def test_enum_with_complex_values(self):
        """Test enum detection with complex enum values."""

        class ComplexEnum(Enum):
            TUPLE_VAL = ("complex", "tuple")
            DICT_VAL = {"key": "value"}
            INT_VAL = 42

        assert _is_enum_type(ComplexEnum) is True
        assert _is_enum_type(Optional[ComplexEnum]) is True


class TestEnumTypeEdgeCases:
    """Test edge cases for enum type detection."""

    def test_none_type_not_enum(self):
        """Test that None type is not detected as enum."""
        assert _is_enum_type(type(None)) is False

    def test_empty_enum_detection(self):
        """Test detection of enum with no members."""

        class EmptyEnum(Enum):
            pass

        assert _is_enum_type(EmptyEnum) is True

    def test_subclass_of_enum_detection(self):
        """Test that subclasses of Enum are detected."""
        from enum import Enum

        # Use functional API to avoid Python 3.12 inheritance restrictions
        CustomEnum = Enum(
            "CustomEnum",
            [
                ("OPTION_A", "A"),
                ("OPTION_B", "B"),
                ("OPTION_C", "C"),
                ("OPTION_D", "D"),
            ],
        )

        assert _is_enum_type(CustomEnum) is True

    @pytest.mark.parametrize("enum_class", [StatusEnumType, PriorityEnumType])
    def test_parametrized_enum_detection(self, enum_class):
        """Test enum detection with parametrized enum classes."""
        assert _is_enum_type(enum_class) is True
        assert _is_enum_type(Optional[enum_class]) is True

    def test_enum_annotation_as_string_not_detected(self):
        """Test that string annotations are not detected (would need eval)."""
        # This tests the current behavior - string annotations aren't resolved
        assert _is_enum_type("StatusEnumType") is False
        assert _is_enum_type("Optional[StatusEnumType]") is False
