import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from fh_pydantic_form.form_parser import (
    _identify_list_fields,
    _parse_boolean_field,
    _parse_list_fields,
    _parse_list_item_key,
    _parse_literal_field,
    _parse_nested_model_field,
    _parse_non_list_fields,
    _parse_simple_field,
)


# Test models for parser functions
class SimpleNested(BaseModel):
    """Simple nested model for testing."""

    sub_field: str = "Default"
    is_active: bool = False


class ParserTestModel(BaseModel):
    """Test model with various field types for parser testing."""

    name: str
    age: int
    is_active: bool = False
    status: Literal["PENDING", "COMPLETED"] = "PENDING"
    optional_status: Optional[Literal["PENDING", "COMPLETED"]] = None
    description: Optional[str] = None
    nested: SimpleNested = Field(default_factory=SimpleNested)
    tags: List[str] = Field(default_factory=list)
    addresses: List[SimpleNested] = Field(default_factory=list)


def test_identify_list_fields():
    """Test identifying list fields in a model."""
    list_fields = _identify_list_fields(ParserTestModel)

    assert len(list_fields) == 2
    assert "tags" in list_fields
    assert "addresses" in list_fields

    # Check item types
    assert list_fields["tags"]["item_type"] is str
    assert list_fields["tags"]["is_model_type"] is False

    assert list_fields["addresses"]["item_type"] is SimpleNested
    assert list_fields["addresses"]["is_model_type"] is True


def test_parse_boolean_field():
    """Test parsing boolean fields from form data."""
    # Present checkbox
    assert _parse_boolean_field("prefix_is_active", {"prefix_is_active": "on"}) is True

    # Missing checkbox (unchecked)
    assert _parse_boolean_field("prefix_is_active", {}) is False


def test_parse_literal_field():
    """Test parsing literal fields from form data."""
    from pydantic.fields import FieldInfo

    # Basic literal field
    field_info = FieldInfo()
    assert (
        _parse_literal_field(
            "prefix_status", {"prefix_status": "COMPLETED"}, field_info
        )
        == "COMPLETED"
    )

    # Optional literal field with value - use actual field info from model
    opt_field_info = ParserTestModel.model_fields["optional_status"]
    assert (
        _parse_literal_field(
            "prefix_opt_status", {"prefix_opt_status": "PENDING"}, opt_field_info
        )
        == "PENDING"
    )

    # Optional literal field with empty string
    assert (
        _parse_literal_field(
            "prefix_opt_status", {"prefix_opt_status": ""}, opt_field_info
        )
        is None
    )

    # Optional literal field with "-- None --" value (UI representation of None)
    assert (
        _parse_literal_field(
            "prefix_opt_status", {"prefix_opt_status": "-- None --"}, opt_field_info
        )
        is None
    )


def test_parse_simple_field():
    """Test parsing simple fields from form data."""

    # Basic field
    assert (
        _parse_simple_field("prefix_name", {"prefix_name": "Test Name"}) == "Test Name"
    )

    # Optional field with value - use actual field info from model
    opt_field_info = ParserTestModel.model_fields["description"]
    assert (
        _parse_simple_field(
            "prefix_desc", {"prefix_desc": "Test Description"}, opt_field_info
        )
        == "Test Description"
    )

    # Optional field with empty string
    assert (
        _parse_simple_field("prefix_desc", {"prefix_desc": ""}, opt_field_info) is None
    )

    # Missing field
    assert _parse_simple_field("prefix_missing", {}) is None

    # Missing optional field
    assert _parse_simple_field("prefix_missing", {}, opt_field_info) is None


def test_parse_nested_model_field():
    """Test parsing nested model fields from form data."""
    from pydantic.fields import FieldInfo

    field_info = FieldInfo()
    form_data = {
        "prefix_nested_sub_field": "Nested Value",
        "prefix_nested_is_active": "on",
    }

    # Parse nested model
    result = _parse_nested_model_field(
        "nested", form_data, SimpleNested, field_info, parent_prefix="prefix_"
    )

    assert result is not None
    assert isinstance(result, dict)
    assert result["sub_field"] == "Nested Value"
    assert result["is_active"] is True

    # Test with empty nested model fields
    result = _parse_nested_model_field(
        "missing", {}, SimpleNested, field_info, parent_prefix="prefix_"
    )
    assert result is not None  # Should at least return an empty dict, not None
    assert isinstance(result, dict)
    # If result contains keys, check they have expected values
    if "sub_field" in result:
        assert result["sub_field"] == "Default"  # Default values used
    if "is_active" in result:
        assert result["is_active"] is False


def test_parse_list_item_key():
    """Test parsing list item keys."""
    # Define list field definitions for testing
    list_defs = {
        "tags": {
            "item_type": str,
            "is_model_type": False,
            "field_info": None,
        },
        "addresses": {
            "item_type": SimpleNested,
            "is_model_type": True,
            "field_info": None,
        },
    }

    # Simple list item
    result = _parse_list_item_key("prefix_tags_0", list_defs, base_prefix="prefix_")
    assert result == ("tags", "0", None, True)

    # Simple list item with "new_" prefix
    result = _parse_list_item_key(
        "prefix_tags_new_12345", list_defs, base_prefix="prefix_"
    )
    assert result == ("tags", "new_12345", None, True)

    # Model list item
    result = _parse_list_item_key(
        "prefix_addresses_0_sub_field", list_defs, base_prefix="prefix_"
    )
    assert result == ("addresses", "0", "sub_field", False)

    # Model list item with "new_" prefix
    result = _parse_list_item_key(
        "prefix_addresses_new_12345_sub_field", list_defs, base_prefix="prefix_"
    )
    assert result == ("addresses", "new_12345", "sub_field", False)

    # Invalid key
    result = _parse_list_item_key("invalid_key", list_defs, base_prefix="prefix_")
    assert result is None


def test_parse_non_list_fields():
    """Test parsing non-list fields from form data."""
    list_field_defs = _identify_list_fields(ParserTestModel)

    form_data = {
        "prefix_name": "Test Name",
        "prefix_age": "30",
        "prefix_is_active": "on",
        "prefix_status": "COMPLETED",
        "prefix_optional_status": "",  # Empty string for None
        "prefix_description": "Test Description",
        "prefix_nested_sub_field": "Nested Value",
        "prefix_nested_is_active": "on",
        # Exclude list fields
    }

    parsed = _parse_non_list_fields(
        form_data, ParserTestModel, list_field_defs, base_prefix="prefix_"
    )

    assert parsed["name"] == "Test Name"
    assert parsed["age"] == "30"  # Still string, Pydantic will convert later
    assert parsed["is_active"] is True
    assert parsed["status"] == "COMPLETED"
    assert parsed["optional_status"] is None
    assert parsed["description"] == "Test Description"
    assert parsed["nested"]["sub_field"] == "Nested Value"
    assert parsed["nested"]["is_active"] is True


def test_parse_list_fields():
    """Test parsing list fields from form data."""
    list_field_defs = _identify_list_fields(ParserTestModel)

    form_data = {
        # Simple list
        "prefix_tags_0": "tag1",
        "prefix_tags_1": "tag2",
        "prefix_tags_new_12345": "new_tag",
        # List of models
        "prefix_addresses_0_sub_field": "Address 1",
        "prefix_addresses_0_is_active": "on",
        "prefix_addresses_1_sub_field": "Address 2",
        # Missing boolean field for second item
    }

    parsed = _parse_list_fields(form_data, list_field_defs, base_prefix="prefix_")

    # Check simple list
    assert parsed["tags"] is not None
    assert len(parsed["tags"]) == 3
    assert parsed["tags"] == ["tag1", "tag2", "new_tag"]

    # Check model list
    assert parsed["addresses"] is not None
    assert len(parsed["addresses"]) == 2
    assert parsed["addresses"][0]["sub_field"] == "Address 1"
    assert parsed["addresses"][0]["is_active"] is True
    assert parsed["addresses"][1]["sub_field"] == "Address 2"
    assert parsed["addresses"][1]["is_active"] is False  # Default for missing boolean


def test_parse_lists_with_missing_booleans():
    """Test handling of missing boolean fields in list items."""

    class Item(BaseModel):
        name: str
        is_active: bool = False
        is_primary: bool = False

    class ListBoolModel(BaseModel):
        items: List[Item] = Field(default_factory=list)

    list_field_defs = _identify_list_fields(ListBoolModel)

    form_data = {
        "prefix_items_0_name": "Item 1",
        "prefix_items_0_is_active": "on",
        # Missing is_primary (should default to False)
        "prefix_items_1_name": "Item 2",
        # Missing both boolean fields
    }

    parsed = _parse_list_fields(form_data, list_field_defs, base_prefix="prefix_")

    items = parsed["items"]
    assert items is not None
    assert len(items) == 2
    assert items[0]["name"] == "Item 1"
    assert items[0]["is_active"] is True
    assert items[0]["is_primary"] is False

    assert items[1]["name"] == "Item 2"
    assert items[1]["is_active"] is False
    assert items[1]["is_primary"] is False


def test_form_renderer_parse(complex_renderer):
    """Test the main parse method of PydanticForm with complex form data."""
    # Use model_class from complex_renderer fixture instead of importing from examples

    # Sample form data for a complex form
    form_data = {
        "test_complex_name": "Test User",
        "test_complex_age": "30",
        "test_complex_score": "95.5",
        "test_complex_is_active": "on",
        "test_complex_description": "Test description",
        "test_complex_creation_date": "2023-01-01",
        "test_complex_start_time": "12:00",
        "test_complex_status": "PENDING",
        # Optional field empty
        "test_complex_optional_status": "",
        # List of strings
        "test_complex_tags_0": "test1",
        "test_complex_tags_1": "test2",
        # Nested model
        "test_complex_main_address_street": "123 Test St",
        "test_complex_main_address_city": "Testville",
        "test_complex_main_address_is_billing": "on",
        # List of nested models
        "test_complex_other_addresses_0_street": "456 Other St",
        "test_complex_other_addresses_0_city": "Otherville",
        # "test_complex_other_addresses_0_is_billing": missing, should be False
        # Custom nested model
        "test_complex_custom_detail_value": "Test Detail",
        "test_complex_custom_detail_confidence": "HIGH",
        # List of custom nested models
        "test_complex_more_custom_details_0_value": "Test Detail 1",
        "test_complex_more_custom_details_0_confidence": "MEDIUM",
    }

    # Parse the form data
    parsed = complex_renderer.parse(form_data)

    # Verify basic fields
    assert parsed["name"] == "Test User"
    assert parsed["age"] == "30"
    assert parsed["score"] == "95.5"
    assert parsed["is_active"] is True

    # Verify list fields
    assert len(parsed["tags"]) == 2
    assert parsed["tags"] == ["test1", "test2"]

    # Verify nested model
    assert parsed["main_address"]["street"] == "123 Test St"
    assert parsed["main_address"]["is_billing"] is True

    # Verify list of models
    assert len(parsed["other_addresses"]) == 1
    assert parsed["other_addresses"][0]["street"] == "456 Other St"
    assert parsed["other_addresses"][0]["is_billing"] is False  # Default for missing

    # Verify custom models
    assert parsed["custom_detail"]["value"] == "Test Detail"
    assert parsed["custom_detail"]["confidence"] == "HIGH"

    # Ensure the parsed data can be validated by the model
    model = complex_renderer.model_class.model_validate(parsed)
    assert model.name == "Test User"
    assert model.tags == ["test1", "test2"]
    assert model.other_addresses[0].street == "456 Other St"


def test_parse_list_fields_handles_empty_optional_and_required_lists(
    optional_list_test_model,
):
    """
    Tests that an empty optional list becomes None, while an empty required list becomes [].
    """
    # Arrange
    list_field_defs = _identify_list_fields(optional_list_test_model)
    form_data: dict[str, str] = {}  # No list items submitted
    base_prefix = "test_form_"

    # Act
    parsed_lists = _parse_list_fields(form_data, list_field_defs, base_prefix)

    # Assert
    assert parsed_lists.get("optional_tags") is None
    assert parsed_lists.get("required_tags") == []


def test_parse_list_fields_handles_populated_optional_list(optional_list_test_model):
    """
    Tests that a populated optional list results in a list, not None.
    """
    # Arrange
    list_field_defs = _identify_list_fields(optional_list_test_model)
    form_data = {
        "test_form_optional_tags_0": "item1",
        "test_form_optional_tags_1": "item2",
    }
    base_prefix = "test_form_"

    # Act
    parsed_lists = _parse_list_fields(form_data, list_field_defs, base_prefix)

    # Assert
    assert parsed_lists.get("optional_tags") == ["item1", "item2"]
    assert parsed_lists.get("required_tags") == []


def test_parse_list_fields_handles_excluded_optional_list(optional_list_test_model):
    """
    Tests that excluded optional lists don't appear in the result.
    """
    # Arrange
    list_field_defs = _identify_list_fields(optional_list_test_model)
    form_data: dict[str, str] = {}  # No list items submitted
    base_prefix = "test_form_"
    exclude_fields = ["optional_tags"]

    # Act
    parsed_lists = _parse_list_fields(
        form_data, list_field_defs, base_prefix, exclude_fields
    )

    # Assert
    assert "optional_tags" not in parsed_lists
    assert parsed_lists.get("required_tags") == []


def test_identify_list_fields_recognizes_optional_lists(optional_list_test_model):
    """
    Tests that _identify_list_fields correctly identifies both optional and required lists.
    """
    # Act
    list_fields = _identify_list_fields(optional_list_test_model)

    # Assert
    assert len(list_fields) == 2
    assert "optional_tags" in list_fields
    assert "required_tags" in list_fields

    # Check that both are identified as string lists
    assert list_fields["optional_tags"]["item_type"] is str
    assert list_fields["optional_tags"]["is_model_type"] is False
    assert list_fields["required_tags"]["item_type"] is str
    assert list_fields["required_tags"]["is_model_type"] is False
