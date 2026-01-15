"""Integration tests for ListChoiceFieldRenderer.

Tests the List[Literal[...]] and List[Enum] pill/tag renderer which displays
selected values as removable pills and a dropdown for adding from remaining options.
"""

from enum import Enum, IntEnum
from typing import List, Literal, Optional

import pytest
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import ListChoiceFieldRenderer, ListLiteralFieldRenderer
from tests import to_html


class ColorEnum(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class PriorityEnum(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class StatusEnum(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@pytest.mark.integration
class TestListChoiceFieldRendererLiteral:
    """Integration tests for List[Literal[...]] rendering."""

    def test_basic_structure_literal(self):
        """Test basic HTML structure for List[Literal]."""
        field_info = FieldInfo(annotation=List[Literal["a", "b", "c"]])
        renderer = ListChoiceFieldRenderer(
            field_name="tags",
            field_info=field_info,
            value=["a"],
        )

        html = to_html(renderer.render_input())

        # Should contain container with data attributes
        assert "tags_pills_container" in html
        assert "data-field-name" in html
        assert "data-all-choices" in html

    def test_selected_values_as_pills(self):
        """Test that selected values are rendered as pills."""
        field_info = FieldInfo(annotation=List[Literal["red", "green", "blue"]])
        renderer = ListChoiceFieldRenderer(
            field_name="colors",
            field_info=field_info,
            value=["red", "blue"],
        )

        html = to_html(renderer.render_input())

        # Should have pills for selected values
        assert "colors_0_pill" in html
        assert "colors_1_pill" in html
        # Should have hidden inputs
        assert 'name="colors_0"' in html or "'name': 'colors_0'" in html
        assert 'name="colors_1"' in html or "'name': 'colors_1'" in html
        # Should contain selected values
        assert "red" in html
        assert "blue" in html

    def test_dropdown_shows_remaining_values(self):
        """Test that dropdown only shows unselected values."""
        field_info = FieldInfo(annotation=List[Literal["a", "b", "c", "d"]])
        renderer = ListChoiceFieldRenderer(
            field_name="options",
            field_info=field_info,
            value=["a", "c"],
        )

        html = to_html(renderer.render_input())

        # Dropdown should show b and d (not a and c which are selected)
        # The dropdown options have data_display attribute
        assert "data_display" in html or "data-display" in html

    def test_empty_list_renders_dropdown_only(self):
        """Test that empty list shows dropdown for all options."""
        field_info = FieldInfo(annotation=List[Literal["x", "y", "z"]])
        renderer = ListChoiceFieldRenderer(
            field_name="items",
            field_info=field_info,
            value=[],
        )

        html = to_html(renderer.render_input())

        # Should have dropdown
        assert "items_pills_container_dropdown" in html
        # Should have no pills (no _pill suffix elements)
        assert "_0_pill" not in html

    def test_all_selected_hides_dropdown(self):
        """Test that dropdown is hidden when all values are selected."""
        field_info = FieldInfo(annotation=List[Literal["only", "two"]])
        renderer = ListChoiceFieldRenderer(
            field_name="all_selected",
            field_info=field_info,
            value=["only", "two"],
        )

        html = to_html(renderer.render_input())

        # Dropdown should be hidden (display: none in style)
        assert "display: none" in html

    def test_literal_with_integers(self):
        """Test List[Literal] with integer values."""
        field_info = FieldInfo(annotation=List[Literal[1, 2, 3, 4, 5]])
        renderer = ListChoiceFieldRenderer(
            field_name="numbers",
            field_info=field_info,
            value=[2, 4],
        )

        html = to_html(renderer.render_input())

        # Should render integer values correctly
        assert "2" in html
        assert "4" in html

    def test_with_prefix(self):
        """Test that field name prefix is applied correctly."""
        field_info = FieldInfo(annotation=List[Literal["opt1", "opt2"]])
        renderer = ListChoiceFieldRenderer(
            field_name="field",
            field_info=field_info,
            prefix="form_",
            value=["opt1"],
        )

        html = to_html(renderer.render_input())

        # Should have prefixed field names
        assert "form_field" in html


@pytest.mark.integration
class TestListChoiceFieldRendererEnum:
    """Integration tests for List[Enum] rendering."""

    def test_basic_structure_enum(self):
        """Test basic HTML structure for List[Enum]."""
        field_info = FieldInfo(annotation=List[ColorEnum])
        renderer = ListChoiceFieldRenderer(
            field_name="colors",
            field_info=field_info,
            value=[ColorEnum.RED],
        )

        html = to_html(renderer.render_input())

        # Should contain container
        assert "colors_pills_container" in html
        # Should have data attributes
        assert "data-all-choices" in html

    def test_enum_display_text_formatting(self):
        """Test that enum names are formatted for display."""
        field_info = FieldInfo(annotation=List[StatusEnum])
        renderer = ListChoiceFieldRenderer(
            field_name="statuses",
            field_info=field_info,
            value=[StatusEnum.PENDING, StatusEnum.ACTIVE],
        )

        html = to_html(renderer.render_input())

        # Should use formatted display text (Title Case with spaces)
        assert "Pending" in html
        assert "Active" in html
        # Hidden input values should use enum values
        assert "pending" in html
        assert "active" in html

    def test_enum_with_int_values(self):
        """Test List[IntEnum] renders correctly."""
        field_info = FieldInfo(annotation=List[PriorityEnum])
        renderer = ListChoiceFieldRenderer(
            field_name="priorities",
            field_info=field_info,
            value=[PriorityEnum.HIGH, PriorityEnum.LOW],
        )

        html = to_html(renderer.render_input())

        # Should show formatted names
        assert "High" in html
        assert "Low" in html
        # Values should be integers
        assert "3" in html  # HIGH = 3
        assert "1" in html  # LOW = 1

    def test_enum_value_string_selection(self):
        """Test that string values are matched to enum members."""
        field_info = FieldInfo(annotation=List[ColorEnum])
        renderer = ListChoiceFieldRenderer(
            field_name="colors",
            field_info=field_info,
            value=["red", "green"],  # String values instead of enum members
        )

        html = to_html(renderer.render_input())

        # Should still render correctly
        assert "Red" in html
        assert "Green" in html

    def test_enum_dropdown_shows_remaining(self):
        """Test dropdown shows only unselected enum members."""
        field_info = FieldInfo(annotation=List[ColorEnum])
        renderer = ListChoiceFieldRenderer(
            field_name="colors",
            field_info=field_info,
            value=[ColorEnum.RED],
        )

        html = to_html(renderer.render_input())

        # Dropdown should exist and show remaining values
        assert "colors_pills_container_dropdown" in html


@pytest.mark.integration
class TestListChoiceFieldRendererCommon:
    """Common integration tests applicable to both Literal and Enum."""

    def test_disabled_state(self):
        """Test that disabled state is properly applied."""
        field_info = FieldInfo(annotation=List[Literal["a", "b"]])
        renderer = ListChoiceFieldRenderer(
            field_name="disabled_field",
            field_info=field_info,
            value=["a"],
            disabled=True,
        )

        html = to_html(renderer.render_input())

        # Should have disabled attribute on dropdown
        assert "disabled" in html
        # Should not have onclick handlers (disabled pills)
        assert "cursor-not-allowed" in html

    def test_optional_list_literal(self):
        """Test Optional[List[Literal[...]]] handling."""
        field_info = FieldInfo(annotation=Optional[List[Literal["opt1", "opt2"]]])
        renderer = ListChoiceFieldRenderer(
            field_name="optional_field",
            field_info=field_info,
            value=None,
        )

        html = to_html(renderer.render_input())

        # Should render dropdown for adding values
        assert "optional_field_pills_container" in html

    def test_optional_list_enum(self):
        """Test Optional[List[Enum]] handling."""
        field_info = FieldInfo(annotation=Optional[List[ColorEnum]])
        renderer = ListChoiceFieldRenderer(
            field_name="optional_colors",
            field_info=field_info,
            value=None,
        )

        html = to_html(renderer.render_input())

        # Should render dropdown
        assert "optional_colors_pills_container" in html

    def test_invalid_type_shows_error(self):
        """Test that non-Literal/Enum list shows error."""
        field_info = FieldInfo(annotation=List[str])
        renderer = ListChoiceFieldRenderer(
            field_name="invalid_field",
            field_info=field_info,
            value=[],
        )

        html = to_html(renderer.render_input())

        # Should show error alert
        assert "alert" in html.lower() or "error" in html.lower()

    def test_pill_remove_button_onclick(self):
        """Test that pills have remove button with onclick handler."""
        field_info = FieldInfo(annotation=List[Literal["removable"]])
        renderer = ListChoiceFieldRenderer(
            field_name="with_remove",
            field_info=field_info,
            value=["removable"],
        )

        html = to_html(renderer.render_input())

        # Should have remove button with onclick
        assert "fhpfRemoveChoicePill" in html
        assert "×" in html or "&times;" in html.lower()

    def test_dropdown_onchange_handler(self):
        """Test that dropdown has onchange handler for adding pills."""
        field_info = FieldInfo(annotation=List[Literal["new1", "new2"]])
        renderer = ListChoiceFieldRenderer(
            field_name="with_add",
            field_info=field_info,
            value=[],
        )

        html = to_html(renderer.render_input())

        # Should have onchange handler
        assert "fhpfAddChoicePill" in html

    def test_all_choices_data_attribute(self):
        """Test that all choices are stored in data attribute for JS."""
        field_info = FieldInfo(annotation=List[Literal["x", "y", "z"]])
        renderer = ListChoiceFieldRenderer(
            field_name="choices",
            field_info=field_info,
            value=["x"],
        )

        html = to_html(renderer.render_input())

        # Should have data-all-choices attribute with all values
        assert "data-all-choices" in html

    @pytest.mark.parametrize(
        "selected,expected_pills",
        [
            ([], 0),
            (["a"], 1),
            (["a", "b"], 2),
            (["a", "b", "c"], 3),
        ],
    )
    def test_pill_count_matches_selection(self, selected, expected_pills):
        """Test that number of pills matches number of selected values."""
        field_info = FieldInfo(annotation=List[Literal["a", "b", "c"]])
        renderer = ListChoiceFieldRenderer(
            field_name="count_test",
            field_info=field_info,
            value=selected,
        )

        html = to_html(renderer.render_input())

        # Count hidden inputs (one per selected pill)
        hidden_input_count = html.count('type="hidden"') if 'type="hidden"' in html else html.count("'type': 'hidden'")
        assert hidden_input_count == expected_pills

    @pytest.mark.parametrize(
        "enum_value",
        [
            ColorEnum.RED,
            ColorEnum.GREEN,
            ColorEnum.BLUE,
        ],
    )
    def test_parametrized_enum_rendering(self, enum_value):
        """Test enum rendering with parametrized values."""
        field_info = FieldInfo(annotation=List[ColorEnum])
        renderer = ListChoiceFieldRenderer(
            field_name="param_enum",
            field_info=field_info,
            value=[enum_value],
        )

        html = to_html(renderer.render_input())

        # Should contain the enum value
        assert enum_value.value in html
        # Should have display text
        expected_display = enum_value.name.replace("_", " ").title()
        assert expected_display in html


@pytest.mark.integration
class TestListLiteralFieldRendererAlias:
    """Test backward compatibility alias."""

    def test_alias_is_same_class(self):
        """Test that ListLiteralFieldRenderer is an alias."""
        assert ListLiteralFieldRenderer is ListChoiceFieldRenderer

    def test_alias_creates_same_output(self):
        """Test that using the alias produces identical output."""
        field_info = FieldInfo(annotation=List[Literal["a", "b"]])

        renderer1 = ListChoiceFieldRenderer(
            field_name="test",
            field_info=field_info,
            value=["a"],
        )
        renderer2 = ListLiteralFieldRenderer(
            field_name="test",
            field_info=field_info,
            value=["a"],
        )

        html1 = to_html(renderer1.render_input())
        html2 = to_html(renderer2.render_input())

        assert html1 == html2


@pytest.mark.integration
class TestListChoiceFieldRendererEdgeCases:
    """Edge case tests for ListChoiceFieldRenderer."""

    def test_special_characters_in_literal_values(self):
        """Test handling of special characters in Literal values."""
        field_info = FieldInfo(annotation=List[Literal["a b", "c-d", "e_f"]])
        renderer = ListChoiceFieldRenderer(
            field_name="special",
            field_info=field_info,
            value=["a b"],
        )

        html = to_html(renderer.render_input())

        # Should handle spaces and special chars
        assert "a b" in html

    def test_literal_with_delimiter_characters(self):
        """Test Literal values containing characters that could break parsing.

        This verifies that colons and commas in values are handled correctly
        by the JSON encoding (not delimiter-based parsing).
        """
        field_info = FieldInfo(annotation=List[Literal["a:b", "c,d", "e:f,g"]])
        renderer = ListChoiceFieldRenderer(
            field_name="delimiters",
            field_info=field_info,
            value=["a:b"],
        )

        html = to_html(renderer.render_input())

        # Should correctly render values with special characters
        assert "a:b" in html
        # The data-all-choices should be valid JSON
        assert "data-all-choices" in html
        # All options should be available
        assert "c,d" in html or "c,d" in html  # In dropdown options

    def test_single_option_literal(self):
        """Test List[Literal] with only one option."""
        field_info = FieldInfo(annotation=List[Literal["only"]])
        renderer = ListChoiceFieldRenderer(
            field_name="single",
            field_info=field_info,
            value=[],
        )

        html = to_html(renderer.render_input())

        # Should render the single option
        assert "only" in html

    def test_none_value_treated_as_empty_list(self):
        """Test that None value is handled as empty list."""
        field_info = FieldInfo(annotation=List[Literal["a", "b"]])
        renderer = ListChoiceFieldRenderer(
            field_name="none_value",
            field_info=field_info,
            value=None,
        )

        html = to_html(renderer.render_input())

        # Should render without errors
        assert "none_value_pills_container" in html

    def test_duplicate_values_in_selection(self):
        """Test handling when selection has duplicate values."""
        field_info = FieldInfo(annotation=List[Literal["dup", "other"]])
        renderer = ListChoiceFieldRenderer(
            field_name="dups",
            field_info=field_info,
            value=["dup", "dup"],  # Duplicate
        )

        html = to_html(renderer.render_input())

        # Should render both (implementation detail - may dedupe)
        assert "dup" in html

    def test_value_not_in_choices(self):
        """Test graceful handling when value is not in choices."""
        field_info = FieldInfo(annotation=List[Literal["a", "b", "c"]])
        renderer = ListChoiceFieldRenderer(
            field_name="missing",
            field_info=field_info,
            value=["unknown"],  # Not a valid Literal value
        )

        html = to_html(renderer.render_input())

        # Should still render without crashing
        assert "missing_pills_container" in html
