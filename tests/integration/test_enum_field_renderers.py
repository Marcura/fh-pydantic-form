from enum import Enum, IntEnum
from typing import Optional

import pytest
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import EnumFieldRenderer
from tests import to_html


class StatusEnum(Enum):
    OPTION_A = "A"
    OPTION_B = "B"
    OPTION_C = "C"


class PriorityEnum(IntEnum):
    FIRST = 1
    SECOND = 2
    THIRD = 3


@pytest.mark.integration
class TestEnumFieldRenderer:
    """Integration tests for EnumFieldRenderer HTML output."""

    def test_enum_renderer_basic_html_structure(self):
        """Test that enum renderer generates basic select HTML structure."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=StatusEnum.OPTION_A,
        )

        html_output = str(renderer.render_input())

        # Check for select element (works with both raw HTML and component representations)
        assert "select" in html_output.lower()
        assert "test_field" in html_output

    def test_enum_renderer_all_options_present(self):
        """Test that all enum options are rendered as select options."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
        )

        html_output = str(renderer.render_input())

        # Check that all enum values are present as options
        assert "'value': 'A'" in html_output or 'value="A"' in html_output
        assert "'value': 'B'" in html_output or 'value="B"' in html_output
        assert "'value': 'C'" in html_output or 'value="C"' in html_output

        # Check display names (formatted from enum names)
        assert "Option A" in html_output
        assert "Option B" in html_output
        assert "Option C" in html_output

    def test_enum_renderer_selected_value(self):
        """Test that the selected enum value is marked as selected."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=StatusEnum.OPTION_B,  # Select the second option
        )

        html_output = str(renderer.render_input())

        # Check that the correct option is selected
        assert (
            ("'selected': True" in html_output and "'value': 'B'" in html_output)
            or 'value="B" selected' in html_output
            or 'selected value="B"' in html_output
        )

    def test_enum_renderer_string_value_selection(self):
        """Test that string values are correctly matched for selection."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value="B",  # Pass string value instead of enum
        )

        html_output = str(renderer.render_input())

        # Should still select the correct option
        assert (
            ("'selected': True" in html_output and "'value': 'B'" in html_output)
            or 'value="B" selected' in html_output
            or 'selected value="B"' in html_output
        )

    def test_optional_enum_renderer_none_option(self):
        """Test that optional enum fields include a None option."""
        field_info = FieldInfo(annotation=Optional[StatusEnum])  # type: ignore[arg-type]
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
        )

        html_output = str(renderer.render_input())

        # Check for None option
        assert "-- None --" in html_output

    def test_optional_enum_renderer_none_selected(self):
        """Test that None value is correctly selected in optional enum."""
        field_info = FieldInfo(annotation=Optional[StatusEnum])  # type: ignore[arg-type]
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=None,
        )

        html_output = str(renderer.render_input())

        # Check that None option is selected - looking for the empty value option to be selected
        assert (
            'value=""' in html_output and "selected" in html_output
        ) or "-- None --" in html_output

    def test_enum_renderer_disabled_state(self):
        """Test that disabled state is properly applied to enum renderer."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            disabled=True,
        )

        html_output = str(renderer.render_input())

        # Check for disabled attribute
        assert "disabled" in html_output

    def test_enum_renderer_required_attribute(self):
        """Test that required attribute is set for non-optional enum without default."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
        )

        html_output = str(renderer.render_input())

        # Should be required since it's not optional and has no default
        # The required attribute is set on the uk-select component
        assert 'required="True"' in html_output or "required" in html_output

    def test_enum_renderer_not_required_with_default(self):
        """Test that required attribute is not set when enum has default."""
        field_info = FieldInfo(annotation=StatusEnum, default=StatusEnum.OPTION_A)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
        )

        html_output = str(renderer.render_input())

        # Should not be required since it has a default
        # The required attribute should not be present in the HTML output
        assert 'required="True"' not in html_output and "required" not in html_output

    def test_enum_renderer_with_prefix(self):
        """Test that field name prefix is correctly applied."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            prefix="form_prefix_",
        )

        html_output = str(renderer.render_input())

        # Check that prefix is applied to field name
        assert "form_prefix_test_field" in html_output

    def test_integer_enum_renderer(self):
        """Test that enums with integer values are rendered correctly."""
        field_info = FieldInfo(annotation=PriorityEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=PriorityEnum.SECOND,
        )

        html_output = str(renderer.render_input())

        # Check that integer values are used
        assert "'value': '1'" in html_output or 'value="1"' in html_output
        assert "'value': '2'" in html_output or 'value="2"' in html_output
        assert "'value': '3'" in html_output or 'value="3"' in html_output

        # Check that second option is selected
        assert (
            ("'selected': True" in html_output and "'value': '2'" in html_output)
            or 'value="2" selected' in html_output
            or 'selected value="2"' in html_output
        )

        # Check display names
        assert "First" in html_output
        assert "Second" in html_output
        assert "Third" in html_output

    def test_enum_renderer_placeholder_text(self):
        """Test that placeholder text is generated for enum fields."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="status_field",
            field_info=field_info,
        )

        html_output = str(renderer.render_input())

        # Check for placeholder-related text (may be in various attributes)
        expected_placeholder = "Select Status Field"
        # The exact implementation might put this in different places
        placeholder_found = (
            expected_placeholder in html_output or "status field" in html_output.lower()
        )
        assert placeholder_found

    def test_enum_renderer_spacing_classes(self):
        """Test that spacing classes are correctly applied."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            spacing="compact",
        )

        html_output = str(renderer.render_input())

        # Should contain some form of width/spacing classes
        assert "w-full" in html_output

    @pytest.mark.parametrize(
        "enum_value, expected_selected",
        [
            (StatusEnum.OPTION_A, "A"),
            (StatusEnum.OPTION_B, "B"),
            (StatusEnum.OPTION_C, "C"),
        ],
    )
    def test_parametrized_enum_selection(self, enum_value, expected_selected):
        """Test enum selection with parametrized values."""
        field_info = FieldInfo(annotation=StatusEnum)
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value=enum_value,
        )

        html_output = str(renderer.render_input())

        # Check that the expected value is selected
        assert (
            (
                "'selected': True" in html_output
                and f"'value': '{expected_selected}'" in html_output
            )
            or f'value="{expected_selected}" selected' in html_output
            or f'selected value="{expected_selected}"' in html_output
        )


@pytest.mark.integration
class TestEnumFieldRendererIntegration:
    """Integration tests for enum renderer with form components."""

    def test_enum_renderer_in_form_context(self, enum_form_renderer):
        """Test enum renderer within a complete form context."""
        import monsterui.all as mui

        form_html = to_html(mui.Form(enum_form_renderer.render_inputs()))

        # Should contain enum select elements
        assert "select" in form_html.lower()
        assert "status" in form_html.lower()
        assert "priority" in form_html.lower()

    def test_complex_enum_renderer_integration(self, complex_enum_form_renderer):
        """Test complex enum renderer with multiple enum fields."""
        import monsterui.all as mui

        form_html = to_html(mui.Form(complex_enum_form_renderer.render_inputs()))

        # Should contain multiple enum selects (count select occurrences)
        select_count = form_html.lower().count("<select")
        assert select_count >= 3  # At least status, shipping_method, priority

        # Check for specific enum options
        assert "PROCESSING" in form_html  # From status enum
        assert "EXPRESS" in form_html  # From shipping method enum
        assert "HIGH" in form_html  # From priority enum

    def test_enum_renderer_error_handling(self):
        """Test enum renderer handles missing enum gracefully."""
        # Create renderer with no enum class (edge case)
        field_info = FieldInfo(annotation=str)  # Wrong annotation type
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
        )

        html_output = str(renderer.render_input())

        # Should handle gracefully, possibly showing an error alert
        assert "alert" in html_output.lower() or "error" in html_output.lower()

    def test_enum_renderer_with_description_tooltip(self):
        """Test that enum field descriptions become tooltips."""
        field_info = FieldInfo(
            annotation=StatusEnum, description="Select the current status"
        )
        renderer = EnumFieldRenderer(
            field_name="test_field",
            field_info=field_info,
        )

        # Render the complete field (including label with tooltip)
        all_elements = str(repr(renderer.render()))

        # Should contain tooltip with description
        assert "Select the current status" in all_elements
        assert "uk_tooltip" in all_elements or "tooltip" in all_elements.lower()
