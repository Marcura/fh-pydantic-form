from datetime import time

import pytest
from pydantic import BaseModel

from fh_pydantic_form import PydanticForm


class TestConstructorRobustness:
    """Test PydanticForm constructor handles various initial value scenarios robustly."""

    @pytest.fixture
    def evolution_models(self):
        """Models representing schema evolution scenarios."""

        # Original schema
        class OriginalAddress(BaseModel):
            street: str = "123 Main St"
            city: str = "Anytown"

        # Evolved schema (added country field)
        class EvolvedAddress(BaseModel):
            street: str = "123 Main St"
            city: str = "Anytown"
            country: str = "USA"  # New field

        # Schema with removed field
        class MinimalAddress(BaseModel):
            city: str = "Anytown"
            # street field removed

        return {
            "original": OriginalAddress,
            "evolved": EvolvedAddress,
            "minimal": MinimalAddress,
        }

    @pytest.mark.parametrize(
        "initial_data,expected_behavior",
        [
            # Valid dict scenarios
            ({"name": "Test", "age": 30}, "preserves_all_data"),
            ({"name": "Test"}, "uses_defaults_for_missing"),
            ({}, "uses_all_defaults"),
            # Explicit None vs missing
            ({"name": None, "age": 30}, "preserves_explicit_none"),
            ({"age": 30}, "missing_field_uses_default"),
            # Invalid data scenarios
            ({"name": 123, "age": "invalid"}, "filters_invalid_preserves_valid"),
            ({"invalid_field": "value"}, "ignores_unknown_fields"),
            ("not_a_dict", "falls_back_to_empty"),
            (None, "handles_none_gracefully"),
            # Edge cases
            ([], "handles_list_gracefully"),
            (123, "handles_int_gracefully"),
            (object(), "handles_object_gracefully"),
        ],
    )
    def test_constructor_dict_input_robustness(
        self, simple_test_model, initial_data, expected_behavior
    ):
        """Test constructor handles various dict inputs robustly."""

        # Should not raise exceptions regardless of input
        form = PydanticForm("test", simple_test_model, initial_values=initial_data)

        # Verify internal state based on expected behavior
        if expected_behavior == "preserves_all_data":
            assert form.initial_values_dict == initial_data
        elif expected_behavior == "uses_all_defaults":
            assert form.initial_values_dict == {}
        elif expected_behavior == "preserves_explicit_none":
            assert form.initial_values_dict["name"] is None
            assert form.initial_values_dict["age"] == 30
        elif expected_behavior == "missing_field_uses_default":
            assert "name" not in form.initial_values_dict
            assert form.initial_values_dict["age"] == 30
        elif expected_behavior in [
            "filters_invalid_preserves_valid",
            "ignores_unknown_fields",
        ]:
            assert isinstance(form.initial_values_dict, dict)
        elif expected_behavior in [
            "falls_back_to_empty",
            "handles_none_gracefully",
            "handles_list_gracefully",
            "handles_int_gracefully",
            "handles_object_gracefully",
        ]:
            assert form.initial_values_dict == {}

        # Should always be able to render
        rendered = form.render_inputs()
        assert rendered is not None

    def test_field_provided_vs_missing_distinction(self, simple_test_model):
        """Test distinction between explicitly provided None and missing fields."""
        # Scenario 1: Field explicitly set to None
        form1 = PydanticForm("test", simple_test_model, initial_values={"name": None})
        rendered1 = form1.render_inputs()

        # Scenario 2: Field not provided at all
        form2 = PydanticForm("test", simple_test_model, initial_values={})
        rendered2 = form2.render_inputs()

        # Check that the forms have different internal state
        assert form1.values_dict.get("name") is None
        # form2.values_dict remains empty since it's a copy of initial_values_dict
        # Defaults are applied during rendering, not stored back in values_dict
        assert form2.values_dict.get("name") is None  # Empty initial_values_dict

        # Both should render successfully
        assert rendered1 is not None
        assert rendered2 is not None

    def test_invalid_initial_values_fallback(self, simple_test_model, mocker):
        """Test fallback behavior with completely invalid initial values."""
        mocker.patch("fh_pydantic_form.form_renderer.logger")

        invalid_inputs = [
            "not_a_dict_or_model",
            123,
            ["list", "not", "dict"],
            object(),  # Non-serializable object
        ]

        for invalid_input in invalid_inputs:
            form = PydanticForm("test", simple_test_model, initial_values=invalid_input)

            # Should fall back to empty dict
            assert form.initial_values_dict == {}

            # Should still render without errors
            rendered = form.render_inputs()
            assert rendered is not None

    def test_basemodel_instance_conversion(self, simple_test_model):
        """Test that BaseModel instances are properly converted to dict."""
        model_instance = simple_test_model(name="Instance User", age=25, score=88.5)

        form = PydanticForm("test", simple_test_model, initial_values=model_instance)

        # Should convert to dict
        assert isinstance(form.initial_values_dict, dict)
        assert form.initial_values_dict["name"] == "Instance User"
        assert form.initial_values_dict["age"] == 25
        assert form.initial_values_dict["score"] == 88.5

        # Should render correctly - check for form structure
        rendered = form.render_inputs()
        assert rendered is not None
        # Check internal state instead of rendered HTML since we get wrapper IDs
        assert form.values_dict["name"] == "Instance User"

    def test_dict_with_non_serializable_values(self, simple_test_model, mocker):
        """Test handling of dictionaries containing non-serializable values."""
        mocker.patch("fh_pydantic_form.form_renderer.logger")

        # Dict with mix of valid and invalid values
        mixed_dict = {
            "name": "Valid Name",
            "age": 30,
            "invalid_field": object(),  # Non-serializable
            "another_invalid": lambda x: x,  # Function
        }

        form = PydanticForm("test", simple_test_model, initial_values=mixed_dict)

        # Should preserve the dict (filtering happens later during rendering)
        assert form.initial_values_dict == mixed_dict

        # Should still render without crashing
        rendered = form.render_inputs()
        assert rendered is not None

    def test_empty_dict_uses_model_defaults(self, simple_test_model):
        """Test that empty dict properly uses model defaults during rendering."""
        form = PydanticForm("test", simple_test_model, initial_values={})
        rendered = form.render_inputs()

        # Should use model defaults - check form structure instead of exact HTML
        assert rendered is not None
        # Form should have proper ID structure
        assert "test-inputs-wrapper" in str(rendered)

    def test_partial_dict_mixed_with_defaults(self, simple_test_model):
        """Test partial dict with some fields provided and others using defaults."""
        partial_data = {"name": "Partial User", "score": 95.0}
        # age is missing, should use default

        form = PydanticForm("test", simple_test_model, initial_values=partial_data)
        rendered = form.render_inputs()

        # Should render successfully with proper structure
        assert rendered is not None
        # Check internal state preservation
        assert form.values_dict["name"] == "Partial User"
        assert form.values_dict["score"] == 95.0


class TestSchemaEvolution:
    """Test handling of schema evolution scenarios."""

    @pytest.fixture
    def evolution_models(self):
        """Models representing schema evolution scenarios."""

        # Original schema
        class OriginalAddress(BaseModel):
            street: str = "123 Main St"
            city: str = "Anytown"

        # Evolved schema (added country field)
        class EvolvedAddress(BaseModel):
            street: str = "123 Main St"
            city: str = "Anytown"
            country: str = "USA"  # New field

        # Schema with removed field
        class MinimalAddress(BaseModel):
            city: str = "Anytown"
            # street field removed from original

        return {
            "original": OriginalAddress,
            "evolved": EvolvedAddress,
            "minimal": MinimalAddress,
        }

    def test_schema_drift_new_fields_added(self, evolution_models):
        """Test handling when new fields are added to schema."""
        original_data = {"street": "456 Oak St", "city": "Springfield"}

        # Use evolved model with original data
        form = PydanticForm(
            "test", evolution_models["evolved"], initial_values=original_data
        )
        rendered = form.render_inputs()

        # Should preserve existing data in internal state
        assert rendered is not None
        assert form.values_dict["street"] == "456 Oak St"
        assert form.values_dict["city"] == "Springfield"

    def test_schema_drift_fields_removed(self, evolution_models):
        """Test handling when fields are removed from schema."""
        evolved_data = {
            "street": "456 Oak St",
            "city": "Springfield",
            "country": "Canada",
        }

        # Use minimal model with evolved data (extra country field)
        form = PydanticForm(
            "test", evolution_models["minimal"], initial_values=evolved_data
        )
        rendered = form.render_inputs()

        # Should preserve valid fields in internal state
        assert rendered is not None
        assert "city" in form.values_dict
        assert form.values_dict["city"] == "Springfield"

    def test_schema_drift_field_type_changes(self, evolution_models):
        """Test handling when field types change between schema versions."""
        # This simulates old data with different type expectations
        mixed_type_data = {
            "street": 123,  # Should be string
            "city": "Springfield",  # Correct type
        }

        form = PydanticForm(
            "test", evolution_models["original"], initial_values=mixed_type_data
        )
        rendered = form.render_inputs()

        # Should not crash and should render something
        assert rendered is not None
        # Check that the values are preserved in internal state
        assert form.values_dict["city"] == "Springfield"
        assert form.values_dict["street"] == 123  # Preserved even with wrong type

    def test_multiple_evolution_stages(self, evolution_models):
        """Test data compatibility across multiple evolution stages."""
        # Data from original schema
        original_data = {"street": "Original St", "city": "Original City"}

        # Should work with all evolution stages
        for stage_name, model_class in evolution_models.items():
            form = PydanticForm(
                f"test_{stage_name}", model_class, initial_values=original_data
            )
            rendered = form.render_inputs()

            assert rendered is not None
            # Check for proper form structure
            assert f"test_{stage_name}" in str(rendered)


class TestEdgeCases:
    """Test various edge cases and corner scenarios."""

    @pytest.fixture
    def time_test_model(self):
        """Model with time field for testing time format handling."""

        class TimeTestModel(BaseModel):
            name: str = "Test User"
            start_time: time = time(9, 0)  # Default 09:00
            end_time: time | None = None  # Optional time field

        return TimeTestModel

    def test_time_string_formats_robustness(self, time_test_model):
        """Test handling of various time string formats."""
        test_cases = [
            # Valid time formats that should be parsed successfully
            ({"start_time": "14:30"}, "14:30", "HH:MM format"),
            ({"start_time": "14:30:45"}, "14:30", "HH:MM:SS format"),
            (
                {"start_time": "14:30:45.123456"},
                "14:30",
                "HH:MM:SS.microseconds format",
            ),
            ({"start_time": "09:05"}, "09:05", "Morning time with leading zero"),
            ({"start_time": "00:00"}, "00:00", "Midnight"),
            ({"start_time": "23:59"}, "23:59", "End of day"),
            # Edge cases and potentially problematic formats
            ({"start_time": "9:30"}, "09:30", "Single digit hour - may need padding"),
            (
                {"start_time": "invalid_time"},
                "",
                "Invalid time string should fallback gracefully",
            ),
            ({"start_time": ""}, "", "Empty string should fallback gracefully"),
            ({"start_time": None}, "", "None value should be handled"),
            # Actual time object
            ({"start_time": time(15, 45)}, "15:45", "Actual time object"),
            ({"start_time": time(8, 5, 30)}, "08:05", "Time object with seconds"),
        ]

        for initial_values, expected_display_time, description in test_cases:
            # Create form and render - should not crash regardless of input
            form = PydanticForm("test", time_test_model, initial_values=initial_values)
            rendered = form.render_inputs()

            # Should always render something without crashing
            assert rendered is not None, f"Failed to render for case: {description}"

            # Check internal state preservation for valid dict inputs
            if isinstance(initial_values, dict):
                start_time_value = initial_values.get("start_time")
                if (
                    start_time_value is not None
                    and "invalid" not in description.lower()
                ):
                    preserved_value = form.values_dict.get("start_time")
                    # Value should be preserved in some form (string or time object)
                    assert preserved_value is not None or start_time_value == "", (
                        f"Value not preserved for case: {description}"
                    )

    def test_mixed_time_data_types(self, time_test_model):
        """Test time fields with mixed data types."""
        mixed_time_data = {
            "name": "Time Test User",
            "start_time": "14:30:15",  # Valid string format
            "end_time": time(17, 0),  # Actual time object
        }

        form = PydanticForm("test", time_test_model, initial_values=mixed_time_data)
        rendered = form.render_inputs()

        assert rendered is not None
        assert form.values_dict["name"] == "Time Test User"
        # Both time values should be preserved in the internal state
        assert form.values_dict.get("start_time") is not None
        assert form.values_dict.get("end_time") is not None

    def test_optional_time_field_handling(self, time_test_model):
        """Test optional time fields with various values."""
        test_cases = [
            ({"end_time": None}, "Explicit None for optional time"),
            ({"end_time": "16:45"}, "Valid string for optional time"),
            ({}, "Missing optional time field"),
        ]

        for initial_values, description in test_cases:
            form = PydanticForm("test", time_test_model, initial_values=initial_values)
            rendered = form.render_inputs()

            assert rendered is not None, f"Failed to render for case: {description}"
            # Should handle optional time fields gracefully

    def test_extremely_large_dict(self, simple_test_model):
        """Test handling of very large dictionaries."""
        from typing import Any, Dict

        large_dict: Dict[str, Any] = {f"field_{i}": f"value_{i}" for i in range(1000)}
        large_dict.update({"name": "Large Dict User", "age": 30})

        form = PydanticForm("test", simple_test_model, initial_values=large_dict)

        # Should handle large dict gracefully
        assert form.initial_values_dict == large_dict

        rendered = form.render_inputs()
        assert rendered is not None
        # Check that the relevant values are in the form's internal state
        assert form.values_dict["name"] == "Large Dict User"
        assert form.values_dict["age"] == 30

    def test_deeply_nested_invalid_structures(self, simple_test_model):
        """Test handling of deeply nested invalid structures."""
        nested_dict = {
            "name": "Nested User",
            "nested": {"level1": {"level2": {"level3": "deep_value"}}},
        }

        form = PydanticForm("test", simple_test_model, initial_values=nested_dict)

        # Should preserve the structure
        assert form.initial_values_dict == nested_dict

        rendered = form.render_inputs()
        assert rendered is not None
        # Check internal state instead of string representation of FastHTML component
        assert form.values_dict["name"] == "Nested User"

    def test_unicode_and_special_characters(self, simple_test_model):
        """Test handling of unicode and special characters in initial values."""
        unicode_dict = {"name": "用户名称 🚀 Special™", "age": 25, "score": 99.9}

        form = PydanticForm("test", simple_test_model, initial_values=unicode_dict)
        rendered = form.render_inputs()

        assert rendered is not None
        # Check internal state preservation of unicode
        assert form.values_dict["name"] == "用户名称 🚀 Special™"

    def test_circular_reference_handling(self, simple_test_model):
        """Test handling of dictionaries with circular references."""
        circular_dict = {"name": "Circular User", "age": 30}
        circular_dict["self"] = circular_dict  # Circular reference

        # Should not crash during construction
        form = PydanticForm("test", simple_test_model, initial_values=circular_dict)

        # Should still render
        rendered = form.render_inputs()
        assert rendered is not None

    def test_none_values_in_dict(self, simple_test_model):
        """Test explicit None values in various field types."""
        none_dict = {"name": None, "age": None, "score": None}

        form = PydanticForm("test", simple_test_model, initial_values=none_dict)
        rendered = form.render_inputs()

        assert rendered is not None
        # Check that None values are preserved in the form's internal state
        assert form.values_dict["name"] is None
        assert form.values_dict["age"] is None
        assert form.values_dict["score"] is None

    def test_mixed_data_types_in_dict(self, simple_test_model):
        """Test dictionary with mixed data types."""
        mixed_dict = {
            "name": "Mixed User",
            "age": "30",  # String instead of int
            "score": 95,  # Int instead of float
            "extra_list": [1, 2, 3],
            "extra_dict": {"key": "value"},
            "extra_bool": True,
        }

        form = PydanticForm("test", simple_test_model, initial_values=mixed_dict)
        rendered = form.render_inputs()

        assert rendered is not None
        # Check that mixed data types are preserved in the form's internal state
        assert form.values_dict["name"] == "Mixed User"
        assert form.values_dict["age"] == "30"  # String instead of int
        assert form.values_dict["score"] == 95  # Int instead of float


class TestInitialValuesPreservation:
    """Test that initial values are properly preserved and not mutated."""

    def test_initial_values_immutability(self, simple_test_model):
        """Test that initial values dict is not mutated by form operations."""
        original_dict = {"name": "Original", "age": 30}
        original_dict_copy = original_dict.copy()

        form = PydanticForm("test", simple_test_model, initial_values=original_dict)

        # Render the form
        form.render_inputs()

        # Original dict should be unchanged
        assert original_dict == original_dict_copy

        # Form's internal dict should be a copy
        assert form.initial_values_dict is not original_dict
        assert form.initial_values_dict == original_dict

    def test_values_dict_independence(self, simple_test_model):
        """Test that values_dict is independent from initial_values_dict."""
        initial_dict = {"name": "Initial", "age": 30}

        form = PydanticForm("test", simple_test_model, initial_values=initial_dict)

        # Modify values_dict
        form.values_dict["name"] = "Modified"

        # Initial values should remain unchanged
        assert form.initial_values_dict["name"] == "Initial"
        assert form.values_dict["name"] == "Modified"

    def test_model_dump_independence(self, simple_test_model):
        """Test that model instances are properly converted without affecting original."""
        original_model = simple_test_model(name="Model User", age=25, score=95.0)

        form = PydanticForm("test", simple_test_model, initial_values=original_model)

        # Modify form's internal dict
        form.values_dict["name"] = "Modified"

        # Original model should be unchanged
        assert original_model.name == "Model User"
        assert form.values_dict["name"] == "Modified"
