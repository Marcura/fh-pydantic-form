from typing import List, Literal, Optional, Union, get_args, get_origin

from fh_pydantic_form.type_helpers import (
    _is_optional_type,
    _get_underlying_type_if_optional,
    _is_literal_type,
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
