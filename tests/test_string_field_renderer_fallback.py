"""
Tests for StringFieldRenderer robustness as a fallback renderer.

StringFieldRenderer is used as fallback when no specific renderer is found,
so it needs to handle ANY type of value gracefully.
"""

import pytest
from bs4 import BeautifulSoup
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import StringFieldRenderer


class TestStringFieldRendererFallback:
    """Test StringFieldRenderer's robustness as a fallback renderer"""

    @pytest.mark.parametrize(
        "value,expected_content,expected_issues",
        [
            # Basic types that should work well
            ("hello", "hello", []),
            ("", "", []),
            ("Line 1\nLine 2", "Line 1\nLine 2", []),
            # Numbers - should convert to strings
            (42, "42", []),
            (3.14159, "3.14159", []),
            (0, "0", []),
            (-5, "-5", []),
            # Boolean values - ISSUE: False becomes empty
            (True, "True", []),
            (False, "", ["false_becomes_empty"]),  # This is a problem!
            # None - reasonable to become empty
            (None, "", []),
            # Collections - should show reasonable representations
            ([1, 2, 3], "[1, 2, 3]", []),
            (["a", "b"], "['a', 'b']", []),
            ([], "[]", []),
            # Dictionaries - MAJOR ISSUE: becomes empty!
            ({"key": "value"}, "", ["dict_becomes_empty"]),  # This is BAD!
            ({}, "", ["dict_becomes_empty"]),
            # Complex objects
            (set([1, 2, 3]), "", ["object_becomes_empty"]),  # Sets become empty too
        ],
    )
    def test_fallback_value_handling(self, value, expected_content, expected_issues):
        """Test that StringFieldRenderer handles various value types as fallback"""
        field_info = FieldInfo(annotation=str)
        renderer = StringFieldRenderer(
            field_name="test_field", field_info=field_info, value=value
        )

        component = renderer.render_input()
        html = (
            component.__html__() if hasattr(component, "__html__") else str(component)
        )

        # Parse HTML to get content
        soup = BeautifulSoup(html, "html.parser")
        textarea = soup.find("textarea")
        assert textarea is not None, f"No textarea found for value {value!r}"

        content = textarea.text
        assert content == expected_content, (
            f"Expected {expected_content!r}, got {content!r} for value {value!r}"
        )

        # Log known issues for documentation
        if expected_issues:
            pytest.skip(f"Known issues with {value!r}: {expected_issues}")

    def test_fallback_row_calculation_robustness(self):
        """Test that row calculation doesn't crash on non-string values"""
        field_info = FieldInfo(annotation=str)

        # These should not crash the renderer
        test_values = [42, True, False, None, [1, 2, 3], {"key": "value"}]

        for value in test_values:
            renderer = StringFieldRenderer(
                field_name="test_field", field_info=field_info, value=value
            )

            # Should not crash
            component = renderer.render_input()
            html = component.__html__()

            soup = BeautifulSoup(html, "html.parser")
            textarea = soup.find("textarea")
            assert textarea is not None
            rows = int(getattr(textarea, "attrs", {}).get("rows", 1))

            # Non-strings should default to 1 row (current behavior)
            assert rows == 1, f"Expected 1 row for {value!r}, got {rows}"

    def test_fallback_with_complex_objects(self):
        """Test behavior with complex objects that might be encountered"""

        class CustomObject:
            def __str__(self):
                return "CustomObject(data=123)"

        test_cases = [
            (CustomObject(), "CustomObject(data=123)"),  # Should use __str__
            (object(), ""),  # Default object() has no useful __str__, becomes empty
        ]

        field_info = FieldInfo(annotation=str)

        for value, expected in test_cases:
            renderer = StringFieldRenderer(
                field_name="test_field", field_info=field_info, value=value
            )

            component = renderer.render_input()
            html = component.__html__()

            soup = BeautifulSoup(html, "html.parser")
            textarea = soup.find("textarea")
            assert textarea is not None
            content = textarea.text

            # For now, document the current behavior
            # In the future, we might want to improve this
            if value is object():
                # Default object() becomes empty due to "or ''" logic
                assert content == ""
            else:
                assert content == expected

    def test_fallback_type_annotation_ignored(self):
        """Test that StringFieldRenderer ignores the type annotation when used as fallback"""
        # When used as fallback, the annotation might be wrong
        field_info = FieldInfo(annotation=int)  # Says int, but we pass string

        renderer = StringFieldRenderer(
            field_name="test_field",
            field_info=field_info,
            value="this is actually a string",
        )

        component = renderer.render_input()
        html = component.__html__()

        soup = BeautifulSoup(html, "html.parser")
        textarea = soup.find("textarea")
        assert textarea is not None
        content = textarea.text

        # Should still work correctly regardless of annotation
        assert content == "this is actually a string"


class TestStringFieldRendererImprovements:
    """Tests for improved StringFieldRenderer that should be more robust"""

    def test_boolean_false_should_not_become_empty(self):
        """False should become 'False', not empty string"""
        field_info = FieldInfo(annotation=str)
        renderer = StringFieldRenderer(
            field_name="test_field", field_info=field_info, value=False
        )

        component = renderer.render_input()
        html = component.__html__()

        soup = BeautifulSoup(html, "html.parser")
        textarea = soup.find("textarea")
        assert textarea is not None
        content = textarea.text

        # This currently fails - False becomes ""
        # After improvement, it should become "False"
        assert content == "False", f"Expected 'False', got {content!r}"

    def test_dict_should_not_become_empty(self):
        """Dictionaries should show a reasonable representation"""
        field_info = FieldInfo(annotation=str)
        test_dict = {"key": "value", "number": 42}

        renderer = StringFieldRenderer(
            field_name="test_field", field_info=field_info, value=test_dict
        )

        component = renderer.render_input()
        html = component.__html__()

        soup = BeautifulSoup(html, "html.parser")
        textarea = soup.find("textarea")
        assert textarea is not None
        content = textarea.text

        # This currently fails - dict becomes ""
        # After improvement, it should show a reasonable representation
        expected = str(test_dict)  # "{'key': 'value', 'number': 42}"
        assert content == expected, f"Expected {expected!r}, got {content!r}"
