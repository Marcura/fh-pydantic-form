import pytest
from fh_pydantic_form.list_path import walk_path
from tests.conftest import ComplexTestSchema, AddressTestModel


@pytest.mark.unit
class TestWalkPath:
    """Unit tests for walk_path function."""

    @pytest.mark.parametrize(
        "segments, expected_item_type",
        [
            (["tags"], str),
            (["other_addresses"], AddressTestModel),
            # Note: nested paths like ["main_address", "tags"] would need the AddressTestModel to have a tags field
        ],
    )
    def test_walk_path_valid_simple_cases(self, segments, expected_item_type):
        """Test walk_path with valid simple paths."""
        field_info, html_parts, item_type = walk_path(ComplexTestSchema, segments)

        assert item_type == expected_item_type
        assert html_parts[-1] == segments[-1]  # last part is list name
        assert len(html_parts) == len(segments)

    def test_walk_path_empty_segments(self):
        """Test walk_path with empty segments raises ValueError."""
        with pytest.raises(ValueError, match="Empty path provided"):
            walk_path(ComplexTestSchema, [])

    def test_walk_path_nonexistent_field(self):
        """Test walk_path with non-existent field raises ValueError."""
        with pytest.raises(ValueError, match="Field 'nonexistent' not found"):
            walk_path(ComplexTestSchema, ["nonexistent"])

    def test_walk_path_non_list_final_field(self):
        """Test walk_path with final field that's not a list raises ValueError."""
        with pytest.raises(ValueError, match="Final field 'name' is not a list type"):
            walk_path(ComplexTestSchema, ["name"])

    def test_walk_path_html_parts_structure(self):
        """Test that html_parts are constructed correctly."""
        field_info, html_parts, item_type = walk_path(ComplexTestSchema, ["tags"])

        assert html_parts == ["tags"]
        assert isinstance(field_info, type(ComplexTestSchema.model_fields["tags"]))

    def test_walk_path_with_model_list(self):
        """Test walk_path with a list of BaseModel items."""
        field_info, html_parts, item_type = walk_path(
            ComplexTestSchema, ["other_addresses"]
        )

        assert item_type == AddressTestModel
        assert html_parts == ["other_addresses"]
        assert hasattr(item_type, "model_fields")  # Verify it's a BaseModel

    @pytest.mark.parametrize(
        "bad_segments, error_pattern",
        [
            (["tags", "invalid"], "Expected index after list field 'tags'"),
            (["other_addresses", "not_a_number"], "Expected index after list field"),
            (["main_address", "nonexistent"], "Field 'nonexistent' not found"),
        ],
    )
    def test_walk_path_invalid_segments(self, bad_segments, error_pattern):
        """Test walk_path with various invalid segment patterns."""
        with pytest.raises(ValueError, match=error_pattern):
            walk_path(ComplexTestSchema, bad_segments)
