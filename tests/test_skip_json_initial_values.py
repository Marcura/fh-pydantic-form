"""Test that SkipJsonSchema fields preserve initial_values correctly (Policy B)."""

from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema
from fh_pydantic_form import PydanticForm


class Model(BaseModel):
    """Test model with SkipJsonSchema field."""

    visible: str
    hidden_sys: SkipJsonSchema[str] = Field(default="MODEL_DEFAULT")


def test_hidden_skip_uses_initial_values_when_missing_from_form():
    """Test that hidden SkipJsonSchema fields use initial_values when not in form data."""
    form = PydanticForm(
        "f",
        Model,
        initial_values={"hidden_sys": "FROM_INITIALS", "visible": "hello"},
        keep_skip_json_fields=[],  # hidden_sys remains hidden (not rendered)
    )
    parsed = form.parse({"f_visible": "hello"})  # hidden_sys omitted in form

    # Policy B: form > initial_values > default
    # Since hidden_sys is not in form data, it should use initial_values
    assert parsed["hidden_sys"] == "FROM_INITIALS"
    assert parsed["visible"] == "hello"


def test_hidden_skip_uses_default_when_no_initial_values():
    """Test that hidden SkipJsonSchema fields use model default when no initial_values."""
    form = PydanticForm("f", Model, initial_values={"visible": "hello"})
    parsed = form.parse({"f_visible": "hello"})

    # No initial_values for hidden_sys, so use model default
    assert parsed["hidden_sys"] == "MODEL_DEFAULT"
    assert parsed["visible"] == "hello"


def test_hidden_skip_uses_sensible_default_when_no_model_default():
    """Test that SkipJsonSchema fields without model defaults use sensible defaults."""

    class ModelNoDefault(BaseModel):
        visible: str
        hidden_sys: SkipJsonSchema[str]  # No default

    form = PydanticForm("f", ModelNoDefault, initial_values={"visible": "hello"})
    parsed = form.parse({"f_visible": "hello"})

    # No initial_values, no model default → sensible default (empty string for str)
    assert parsed["hidden_sys"] == ""
    assert parsed["visible"] == "hello"


def test_form_value_overrides_initial_values():
    """Test that form values have highest priority (Policy B precedence)."""
    form = PydanticForm(
        "f",
        Model,
        initial_values={"hidden_sys": "FROM_INITIALS", "visible": "initial_visible"},
    )
    parsed = form.parse({"f_visible": "form_visible"})

    # Form value should override initial_values
    assert parsed["visible"] == "form_visible"
    # hidden_sys not in form, should use initial_values
    assert parsed["hidden_sys"] == "FROM_INITIALS"


def test_kept_skip_field_from_form_overrides_initial_values():
    """Test that kept SkipJsonSchema fields in form data override initial_values."""
    form = PydanticForm(
        "f",
        Model,
        initial_values={"hidden_sys": "FROM_INITIALS", "visible": "hello"},
        keep_skip_json_fields=["hidden_sys"],  # Now rendered in form
    )
    parsed = form.parse({"f_visible": "hello", "f_hidden_sys": "FROM_FORM"})

    # Form value should have highest priority
    assert parsed["hidden_sys"] == "FROM_FORM"
    assert parsed["visible"] == "hello"
