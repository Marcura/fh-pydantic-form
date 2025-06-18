from typing import List, Literal, Optional, Union, get_args, get_origin

import pytest

from fh_pydantic_form.type_helpers import (
    _is_optional_type,
    _get_underlying_type_if_optional,
    _is_literal_type,
    _is_skip_json_schema_field,
)


class TestIsOptionalType:
    """Test the _is_optional_type function."""

    def test_optional_str(self):
        """Test with Optional[str]."""
        assert _is_optional_type(Optional[str]) is True

    def test_union_with_none(self):
        """Test with Union[str, None]."""
        assert _is_optional_type(Union[str, None]) is True

    def test_union_without_none(self):
        """Test with Union[str, int]."""
        assert _is_optional_type(Union[str, int]) is False

    def test_non_optional_str(self):
        """Test with str."""
        assert _is_optional_type(str) is False

    def test_non_optional_int(self):
        """Test with int."""
        assert _is_optional_type(int) is False

    def test_non_optional_list(self):
        """Test with List[str]."""
        assert _is_optional_type(List[str]) is False

    def test_optional_list(self):
        """Test with Optional[List[str]]."""
        assert _is_optional_type(Optional[List[str]]) is True


class TestGetUnderlyingTypeIfOptional:
    """Test the _get_underlying_type_if_optional function."""

    def test_optional_str(self):
        """Test with Optional[str]."""
        assert _get_underlying_type_if_optional(Optional[str]) is str

    def test_union_with_none(self):
        """Test with Union[str, None]."""
        assert _get_underlying_type_if_optional(Union[str, None]) is str

    def test_union_with_none_reversed(self):
        """Test with Union[None, str]."""
        assert _get_underlying_type_if_optional(Union[None, str]) is str

    def test_non_optional_str(self):
        """Test with str."""
        assert _get_underlying_type_if_optional(str) is str

    def test_optional_list(self):
        """Test with Optional[List[str]]."""
        underlying = _get_underlying_type_if_optional(Optional[List[str]])
        assert get_origin(underlying) is list
        assert get_args(underlying)[0] is str


class TestIsLiteralType:
    """Test the _is_literal_type function."""

    def test_literal(self):
        """Test with Literal['a', 'b']."""
        assert _is_literal_type(Literal["a", "b"]) is True

    def test_optional_literal(self):
        """Test with Optional[Literal['a', 'b']]."""
        assert _is_literal_type(Optional[Literal["a", "b"]]) is True

    def test_non_literal_str(self):
        """Test with str."""
        assert _is_literal_type(str) is False

    def test_non_literal_union(self):
        """Test with Union[str, int]."""
        assert _is_literal_type(Union[str, int]) is False


class TestIsSkipJsonSchemaField:
    """Test the _is_skip_json_schema_field function."""

    @pytest.fixture
    def skip_json_schema_annotations(self):
        """Create various SkipJsonSchema annotations for testing."""
        try:
            from pydantic.json_schema import SkipJsonSchema

            return {
                "available": True,
                "direct_str": SkipJsonSchema[str],
                "direct_int": SkipJsonSchema[int],
                "complex_list": SkipJsonSchema[List[str]],
                "optional_skip": SkipJsonSchema[Optional[str]],
            }
        except ImportError:
            # Handle case where pydantic version doesn't have SkipJsonSchema
            return {"available": False}

    def test_skip_json_schema_direct(self, skip_json_schema_annotations):
        """Test direct SkipJsonSchema annotations."""
        if not skip_json_schema_annotations.get("available"):
            pytest.skip("SkipJsonSchema not available in this pydantic version")

        assert (
            _is_skip_json_schema_field(skip_json_schema_annotations["direct_str"])
            is True
        )
        assert (
            _is_skip_json_schema_field(skip_json_schema_annotations["direct_int"])
            is True
        )
        assert (
            _is_skip_json_schema_field(skip_json_schema_annotations["complex_list"])
            is True
        )

    def test_skip_json_schema_with_optional(self, skip_json_schema_annotations):
        """Test SkipJsonSchema with Optional types."""
        if not skip_json_schema_annotations.get("available"):
            pytest.skip("SkipJsonSchema not available in this pydantic version")

        assert (
            _is_skip_json_schema_field(skip_json_schema_annotations["optional_skip"])
            is True
        )

    def test_non_skip_json_schema_types(self):
        """Test that regular types return False."""
        assert _is_skip_json_schema_field(str) is False
        assert _is_skip_json_schema_field(int) is False
        assert _is_skip_json_schema_field(List[str]) is False
        assert _is_skip_json_schema_field(Optional[str]) is False
        assert _is_skip_json_schema_field(Union[str, int]) is False

    def test_skip_json_schema_string_fallback(self):
        """Test string representation fallback detection."""

        # Create a mock type that has SkipJsonSchema in its string representation
        class MockSkipJsonSchemaType:
            def __str__(self):
                return "SkipJsonSchema[str]"

        mock_type = MockSkipJsonSchemaType()
        assert _is_skip_json_schema_field(mock_type) is True

    def test_edge_cases(self):
        """Test edge cases for SkipJsonSchema detection."""
        # None should return False
        assert _is_skip_json_schema_field(None) is False

        # Empty type annotations
        assert _is_skip_json_schema_field(type(None)) is False
