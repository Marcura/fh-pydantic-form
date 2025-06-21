#!/usr/bin/env python3
"""
Test script to verify excluded fields default injection functionality
"""

from typing import List, Optional

import pytest
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm


class ExampleModel(BaseModel):
    """Example model with various default types"""

    visible_field: str = "user input"
    excluded_with_default: str = "default_value"
    excluded_with_factory: List[str] = Field(default_factory=lambda: ["item1", "item2"])
    excluded_required: str  # No default - should cause validation error if not provided
    excluded_optional: Optional[str] = None


def test_excluded_fields_default_injection():
    """Test that excluded fields get default values injected during parsing"""
    # Create form with some excluded fields
    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
        ],
    )

    # Simulate form data with only visible field
    form_data = {"test_form_visible_field": "user provided value"}

    # Parse the form data
    parsed_data = form_renderer.parse(form_data)

    # Verify defaults were injected for excluded fields
    assert "excluded_with_default" in parsed_data
    assert parsed_data["excluded_with_default"] == "default_value"

    assert "excluded_with_factory" in parsed_data
    assert parsed_data["excluded_with_factory"] == ["item1", "item2"]

    assert "excluded_optional" in parsed_data
    assert parsed_data["excluded_optional"] is None

    # Verify visible field was parsed correctly
    assert parsed_data["visible_field"] == "user provided value"

    # Note: excluded_required is NOT in exclude_fields, so it will be processed normally
    # and set to None since it's not in the form data


def test_excluded_fields_validation_success():
    """Test that validation succeeds when excluded fields have defaults"""
    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
        ],
    )

    # Simulate form data with visible and required fields
    form_data = {
        "test_form_visible_field": "user provided value",
        "test_form_excluded_required": "provided_value",
    }

    # Parse and validate
    parsed_data = form_renderer.parse(form_data)
    validated_model = ExampleModel.model_validate(parsed_data)

    # Verify the model was created correctly with injected defaults
    assert validated_model.visible_field == "user provided value"
    assert validated_model.excluded_with_default == "default_value"
    assert validated_model.excluded_with_factory == ["item1", "item2"]
    assert validated_model.excluded_optional is None
    assert validated_model.excluded_required == "provided_value"


def test_excluded_fields_validation_failure():
    """Test that validation fails when required excluded field has no default"""
    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
            "excluded_required",  # This one has no default
        ],
    )

    # Simulate form data with only visible field
    form_data = {"test_form_visible_field": "user provided value"}

    # Parse the data
    parsed_data = form_renderer.parse(form_data)

    # Verify that excluded_required is NOT in parsed data (no default available)
    assert "excluded_required" not in parsed_data

    # Verify validation fails for missing required field
    with pytest.raises(Exception) as exc_info:
        ExampleModel.model_validate(parsed_data)

    # Should be a validation error about the missing required field
    assert "excluded_required" in str(exc_info.value)


def test_excluded_fields_not_rendered():
    """Test that excluded fields are not included in rendered form inputs"""
    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        exclude_fields=["excluded_with_default", "excluded_required"],
    )

    # Render the form inputs - this should succeed without errors
    rendered_inputs = form_renderer.render_inputs()

    # Verify that the render_inputs method returns a valid component
    assert rendered_inputs is not None

    # The actual test is that rendering doesn't fail and that the PydanticForm
    # instance correctly tracks which fields are excluded
    assert "excluded_with_default" in form_renderer.exclude_fields
    assert "excluded_required" in form_renderer.exclude_fields
    assert "visible_field" not in form_renderer.exclude_fields
    assert "excluded_with_factory" not in form_renderer.exclude_fields
    assert "excluded_optional" not in form_renderer.exclude_fields

    # Verify that the model has the expected fields
    all_fields = set(ExampleModel.model_fields.keys())
    excluded_fields = set(form_renderer.exclude_fields)
    rendered_fields = all_fields - excluded_fields

    expected_rendered = {"visible_field", "excluded_with_factory", "excluded_optional"}
    assert rendered_fields == expected_rendered


def test_model_validate_request_with_excluded_defaults():
    """Test the model_validate_request method with excluded fields having defaults"""
    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
        ],
    )

    # Mock request object with form data
    class MockRequest:
        async def form(self):
            return {
                "test_form_visible_field": "user input value",
                "test_form_excluded_required": "required value",
            }

    mock_req = MockRequest()

    # This should work without errors thanks to default injection
    async def test_validation():
        validated_model = await form_renderer.model_validate_request(mock_req)
        assert validated_model.visible_field == "user input value"
        assert validated_model.excluded_with_default == "default_value"
        assert validated_model.excluded_with_factory == ["item1", "item2"]
        assert validated_model.excluded_optional is None
        assert validated_model.excluded_required == "required value"

    # Run the async test
    import asyncio

    asyncio.run(test_validation())


class NestedExampleModel(BaseModel):
    """Nested model for testing BaseModel defaults"""

    nested_field: str = "nested_default"
    nested_number: int = 42


class ModelWithNestedDefaults(BaseModel):
    """Model with nested BaseModel defaults"""

    visible_field: str
    excluded_nested: NestedExampleModel = NestedExampleModel()


def test_excluded_fields_with_nested_model_defaults():
    """Test that excluded fields with BaseModel defaults are converted to dicts"""
    form_renderer = PydanticForm(
        "test_form",
        ModelWithNestedDefaults,
        exclude_fields=["excluded_nested"],
    )

    # Simulate form data with only visible field
    form_data = {"test_form_visible_field": "user input"}

    # Parse the data
    parsed_data = form_renderer.parse(form_data)

    # Verify the nested model default was injected and converted to dict
    assert "excluded_nested" in parsed_data
    assert isinstance(parsed_data["excluded_nested"], dict)
    assert parsed_data["excluded_nested"]["nested_field"] == "nested_default"
    assert parsed_data["excluded_nested"]["nested_number"] == 42

    # Verify validation works
    validated_model = ModelWithNestedDefaults.model_validate(parsed_data)
    assert validated_model.visible_field == "user input"
    assert validated_model.excluded_nested.nested_field == "nested_default"
    assert validated_model.excluded_nested.nested_number == 42


def test_excluded_fields_with_initial_values_dict():
    """Test that initial_values dict overrides model defaults for excluded fields"""
    # Initial values that override the model defaults
    initial_values = {
        "visible_field": "initial visible",
        "excluded_with_default": "overridden_default",
        "excluded_with_factory": ["custom", "list"],
        "excluded_optional": "not_none_anymore",
        "excluded_required": "initial_required",
    }

    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        initial_values=initial_values,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
            "excluded_required",
        ],
    )

    # Simulate form data with only visible field (user changed it)
    form_data = {"test_form_visible_field": "user changed value"}

    # Parse the data
    parsed_data = form_renderer.parse(form_data)

    # Verify that excluded fields got their initial_values, not model defaults
    assert parsed_data["visible_field"] == "user changed value"  # From form
    assert (
        parsed_data["excluded_with_default"] == "overridden_default"
    )  # From initial_values
    assert parsed_data["excluded_with_factory"] == [
        "custom",
        "list",
    ]  # From initial_values
    assert parsed_data["excluded_optional"] == "not_none_anymore"  # From initial_values
    assert parsed_data["excluded_required"] == "initial_required"  # From initial_values

    # Verify validation works
    validated_model = ExampleModel.model_validate(parsed_data)
    assert validated_model.visible_field == "user changed value"
    assert validated_model.excluded_with_default == "overridden_default"
    assert validated_model.excluded_with_factory == ["custom", "list"]
    assert validated_model.excluded_optional == "not_none_anymore"
    assert validated_model.excluded_required == "initial_required"


def test_excluded_fields_with_initial_values_model():
    """Test that initial_values as model instance overrides model defaults for excluded fields"""
    # Create a model instance with custom values
    initial_model = ExampleModel(
        visible_field="initial visible",
        excluded_with_default="model_overridden_default",
        excluded_with_factory=["model", "custom", "list"],
        excluded_optional="model_not_none",
        excluded_required="model_required",
    )

    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        initial_values=initial_model,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
            "excluded_required",
        ],
    )

    # Simulate form data with only visible field (user changed it)
    form_data = {"test_form_visible_field": "user final value"}

    # Parse the data
    parsed_data = form_renderer.parse(form_data)

    # Verify that excluded fields got their initial model values, not defaults
    assert parsed_data["visible_field"] == "user final value"  # From form
    assert (
        parsed_data["excluded_with_default"] == "model_overridden_default"
    )  # From initial model
    assert parsed_data["excluded_with_factory"] == [
        "model",
        "custom",
        "list",
    ]  # From initial model
    assert parsed_data["excluded_optional"] == "model_not_none"  # From initial model
    assert parsed_data["excluded_required"] == "model_required"  # From initial model

    # Verify validation works
    validated_model = ExampleModel.model_validate(parsed_data)
    assert validated_model.visible_field == "user final value"
    assert validated_model.excluded_with_default == "model_overridden_default"
    assert validated_model.excluded_with_factory == ["model", "custom", "list"]
    assert validated_model.excluded_optional == "model_not_none"
    assert validated_model.excluded_required == "model_required"


def test_excluded_fields_partial_initial_values():
    """Test that partial initial_values work correctly with model defaults as fallback"""
    # Initial values that only override some fields
    initial_values = {
        "visible_field": "initial visible",
        "excluded_with_default": "overridden_default",
        # excluded_with_factory not provided - should use model default
        "excluded_optional": "overridden_optional",
        # excluded_required not provided - should use model default (but there isn't one)
    }

    form_renderer = PydanticForm(
        "test_form",
        ExampleModel,
        initial_values=initial_values,
        exclude_fields=[
            "excluded_with_default",
            "excluded_with_factory",
            "excluded_optional",
        ],
    )

    # Simulate form data
    form_data = {
        "test_form_visible_field": "user input",
        "test_form_excluded_required": "user provided required",
    }

    # Parse the data
    parsed_data = form_renderer.parse(form_data)

    # Verify mixed sources: initial_values override where provided, model defaults as fallback
    assert parsed_data["visible_field"] == "user input"  # From form
    assert (
        parsed_data["excluded_with_default"] == "overridden_default"
    )  # From initial_values
    assert parsed_data["excluded_with_factory"] == [
        "item1",
        "item2",
    ]  # Model default (not in initial_values)
    assert (
        parsed_data["excluded_optional"] == "overridden_optional"
    )  # From initial_values
    assert (
        parsed_data["excluded_required"] == "user provided required"
    )  # From form (not excluded)

    # Verify validation works
    validated_model = ExampleModel.model_validate(parsed_data)
    assert validated_model.excluded_with_default == "overridden_default"
    assert validated_model.excluded_with_factory == ["item1", "item2"]
    assert validated_model.excluded_optional == "overridden_optional"


def test_all_missing_fields_get_defaults_except_lists():
    """Test that ALL missing fields get defaults, not just excluded fields."""

    class MixedDefaultsModel(BaseModel):
        # Visible field that user will provide
        visible_field: str

        # Field that will be missing from form but has default
        missing_with_default: str = "missing_default"

        # Field that will be missing from form with factory
        missing_list_with_factory: List[str] = Field(
            default_factory=lambda: ["missing1", "missing2"]
        )
        excluded_list_with_factory: List[str] = Field(
            default_factory=lambda: ["excluded1", "excluded2"]
        )

        # Optional field that will be missing
        missing_optional: Optional[str] = None

        # Required field without default that will be missing
        missing_required: str

    form_renderer = PydanticForm(
        "test_form",
        MixedDefaultsModel,
        # Note: NOT excluding any fields, they're just missing from form data
        exclude_fields=["excluded_list_with_factory"],
    )

    # Simulate sparse form data - many fields missing
    form_data = {
        "test_form_visible_field": "user provided",
        "test_form_missing_required": "also provided",  # Must provide this to avoid validation error
    }

    parsed_data = form_renderer.parse(form_data)

    # All fields with defaults should be present even though not excluded
    assert parsed_data["visible_field"] == "user provided"
    assert parsed_data["missing_with_default"] == "missing_default"
    # lists without items should parse to an empty list.
    assert parsed_data["missing_list_with_factory"] == []
    assert parsed_data["missing_optional"] is None
    assert parsed_data["missing_required"] == "also provided"

    # Validation should succeed
    validated_model = MixedDefaultsModel.model_validate(parsed_data)
    assert validated_model.missing_with_default == "missing_default"
    assert validated_model.missing_list_with_factory == []
    assert validated_model.excluded_list_with_factory == ["excluded1", "excluded2"]


def test_excluded_fields_with_nested_initial_values():
    """Test that initial_values work correctly with nested models in excluded fields"""
    # Custom nested model values
    custom_nested = NestedExampleModel(nested_field="custom_nested", nested_number=99)

    initial_values = {
        "visible_field": "initial visible",
        "excluded_nested": custom_nested,
    }

    form_renderer = PydanticForm(
        "test_form",
        ModelWithNestedDefaults,
        initial_values=initial_values,
        exclude_fields=["excluded_nested"],
    )

    # Simulate form data with only visible field
    form_data = {"test_form_visible_field": "user input"}

    # Parse the data
    parsed_data = form_renderer.parse(form_data)

    # Verify the nested model from initial_values was used and converted to dict
    assert "excluded_nested" in parsed_data
    assert isinstance(parsed_data["excluded_nested"], dict)
    assert (
        parsed_data["excluded_nested"]["nested_field"] == "custom_nested"
    )  # From initial_values
    assert parsed_data["excluded_nested"]["nested_number"] == 99  # From initial_values

    # Verify validation works
    validated_model = ModelWithNestedDefaults.model_validate(parsed_data)
    assert validated_model.visible_field == "user input"
    assert validated_model.excluded_nested.nested_field == "custom_nested"
    assert validated_model.excluded_nested.nested_number == 99
