import pytest

from fh_pydantic_form import PydanticForm


class TestNestedModelRobustness:
    """Test nested model handling with partial and invalid data."""

    @pytest.fixture
    def nested_evolution_scenario(self):
        """Fixture for nested model evolution testing."""
        # Original nested data (missing new fields)
        return {
            "name": "Test User",
            "main_address": {
                "street": "123 Old St",
                "city": "Oldtown",
                # Missing 'is_billing' field
            },
        }

    def test_nested_model_partial_data_rendering(
        self, complex_test_model, nested_evolution_scenario
    ):
        """Test nested models render correctly with partial data."""
        form = PydanticForm(
            "test", complex_test_model, initial_values=nested_evolution_scenario
        )
        rendered = form.render_inputs()

        # Should preserve provided nested data in internal state
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        assert form.values_dict["main_address"]["street"] == "123 Old St"
        assert form.values_dict["main_address"]["city"] == "Oldtown"

    def test_nested_model_completely_missing(self, complex_test_model):
        """Test when entire nested model is missing from initial data."""
        partial_data = {
            "name": "Test User",
            # main_address completely missing
        }

        form = PydanticForm("test", complex_test_model, initial_values=partial_data)
        rendered = form.render_inputs()

        # Should render with nested model defaults
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        # The main_address should get default values during rendering
        # Check that the form doesn't crash when rendering nested models

    def test_nested_model_invalid_data(self, complex_test_model, mocker):
        """Test nested model with invalid data structure."""
        mocker.patch("fh_pydantic_form.field_renderers.logger")

        invalid_nested_data = {
            "name": "Test User",
            "main_address": "not_a_dict_should_be_object",  # Invalid nested data
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=invalid_nested_data
        )
        rendered = form.render_inputs()

        # Should handle gracefully without crashing
        assert rendered is not None
        # Should preserve valid field data
        assert form.values_dict["name"] == "Test User"
        # Should preserve invalid data as-is (for robustness)
        assert form.values_dict["main_address"] == "not_a_dict_should_be_object"

    def test_nested_model_with_none_value(self, complex_test_model):
        """Test nested model field explicitly set to None."""
        none_nested_data = {"name": "Test User", "main_address": None}

        form = PydanticForm("test", complex_test_model, initial_values=none_nested_data)
        rendered = form.render_inputs()

        # Should handle None gracefully and use defaults
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        assert form.values_dict["main_address"] is None

    def test_nested_model_type_mismatch(self, complex_test_model):
        """Test nested model with incorrect types in nested fields."""
        type_mismatch_data = {
            "name": "Test User",
            "main_address": {
                "street": 123,  # Should be string
                "city": True,  # Should be string
                "is_billing": "not_a_boolean",  # Should be boolean
            },
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=type_mismatch_data
        )
        rendered = form.render_inputs()

        # Should not crash and should render
        assert rendered is not None
        # Should preserve valid field data
        assert form.values_dict["name"] == "Test User"
        # Should preserve nested data even with type mismatches
        assert form.values_dict["main_address"]["street"] == 123
        assert form.values_dict["main_address"]["city"] is True
        assert form.values_dict["main_address"]["is_billing"] == "not_a_boolean"

    def test_deeply_nested_structures(self, complex_test_model):
        """Test handling of deeply nested data structures."""
        deeply_nested_data = {
            "name": "Deep User",
            "main_address": {
                "street": "Deep St",
                "city": "Deep City",
                "nested_extra": {"level1": {"level2": "deep_value"}},
            },
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=deeply_nested_data
        )
        rendered = form.render_inputs()

        # Should handle deep nesting without crashing
        assert rendered is not None
        # Should preserve valid nested fields in internal state
        assert form.values_dict["name"] == "Deep User"
        assert form.values_dict["main_address"]["street"] == "Deep St"
        assert form.values_dict["main_address"]["city"] == "Deep City"
        # Should preserve extra nested structure
        assert "nested_extra" in form.values_dict["main_address"]

    def test_nested_model_with_extra_fields(self, complex_test_model):
        """Test nested model with extra fields not in schema."""
        extra_fields_data = {
            "name": "Extra User",
            "main_address": {
                "street": "Extra St",
                "city": "Extra City",
                "is_billing": True,
                "country": "Extra Country",  # Not in schema
                "postal_code": "12345",  # Not in schema
            },
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=extra_fields_data
        )
        rendered = form.render_inputs()

        # Should handle extra fields gracefully
        assert rendered is not None
        # Should preserve valid fields in internal state
        assert form.values_dict["name"] == "Extra User"
        assert form.values_dict["main_address"]["street"] == "Extra St"
        assert form.values_dict["main_address"]["city"] == "Extra City"
        assert form.values_dict["main_address"]["is_billing"] is True
        # Should preserve extra fields even though not in schema
        assert form.values_dict["main_address"]["country"] == "Extra Country"
        assert form.values_dict["main_address"]["postal_code"] == "12345"

    def test_nested_model_empty_dict(self, complex_test_model):
        """Test nested model with empty dictionary."""
        empty_nested_data = {
            "name": "Empty User",
            "main_address": {},  # Empty nested dict
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=empty_nested_data
        )
        rendered = form.render_inputs()

        # Should handle empty nested dict gracefully
        assert rendered is not None
        # Should preserve provided data in internal state
        assert form.values_dict["name"] == "Empty User"
        assert form.values_dict["main_address"] == {}


class TestListFieldRobustness:
    """Test list field handling with various edge cases."""

    def test_list_field_partial_items(self, complex_test_model):
        """Test list fields with some items having partial data."""
        partial_list_data = {
            "name": "Test User",
            "other_addresses": [
                {"street": "Complete St", "city": "Complete City", "is_billing": True},
                {"street": "Partial St"},  # Missing city and is_billing
                {},  # Completely empty item
            ],
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=partial_list_data
        )
        rendered = form.render_inputs()

        # Should preserve complete items in internal state
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        assert len(form.values_dict["other_addresses"]) == 3
        assert form.values_dict["other_addresses"][0]["street"] == "Complete St"
        assert form.values_dict["other_addresses"][1]["street"] == "Partial St"

    def test_list_field_invalid_items(self, complex_test_model, mocker):
        """Test list fields containing invalid item data."""
        mocker.patch("fh_pydantic_form.field_renderers.logger")

        invalid_list_data = {
            "name": "Test User",
            "other_addresses": [
                {"street": "Valid St", "city": "Valid City"},  # Valid item
                "not_an_object",  # Invalid item type
                {"street": 123, "city": None},  # Invalid field types
                None,  # None item
            ],
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=invalid_list_data
        )
        rendered = form.render_inputs()

        # Should preserve valid items in internal state
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        # Check that some valid data is preserved
        assert "other_addresses" in form.values_dict

    def test_list_field_not_a_list(self, complex_test_model):
        """Test list field with non-list data."""
        non_list_data = {
            "name": "Test User",
            "tags": "not_a_list",  # Should be list
            "other_addresses": {"not": "a_list"},  # Should be list
        }

        form = PydanticForm("test", complex_test_model, initial_values=non_list_data)
        rendered = form.render_inputs()

        # Should handle gracefully without crashing
        assert rendered is not None
        # Should preserve valid field data
        assert form.values_dict["name"] == "Test User"
        # Should preserve invalid list data as-is (for robustness)
        assert form.values_dict["tags"] == "not_a_list"
        assert form.values_dict["other_addresses"] == {"not": "a_list"}

    def test_list_field_empty_list(self, complex_test_model):
        """Test list field with empty list."""
        empty_list_data = {"name": "Test User", "tags": [], "other_addresses": []}

        form = PydanticForm("test", complex_test_model, initial_values=empty_list_data)
        rendered = form.render_inputs()

        # Should render with empty list containers
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        assert form.values_dict["tags"] == []
        assert form.values_dict["other_addresses"] == []

    def test_list_field_none_value(self, complex_test_model):
        """Test list field explicitly set to None."""
        none_list_data = {"name": "Test User", "tags": None, "other_addresses": None}

        form = PydanticForm("test", complex_test_model, initial_values=none_list_data)
        rendered = form.render_inputs()

        # Should handle None gracefully without crashing
        assert rendered is not None
        # Should preserve all provided data in internal state
        assert form.values_dict["name"] == "Test User"
        assert form.values_dict["tags"] is None
        assert form.values_dict["other_addresses"] is None

    def test_simple_list_mixed_types(self, complex_test_model):
        """Test simple list with mixed data types."""
        mixed_list_data = {
            "name": "Test User",
            "tags": ["string", 123, True, None, {"dict": "value"}],
        }

        form = PydanticForm("test", complex_test_model, initial_values=mixed_list_data)
        rendered = form.render_inputs()

        # Should handle mixed types
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        assert form.values_dict["tags"] == [
            "string",
            123,
            True,
            None,
            {"dict": "value"},
        ]

    def test_nested_list_with_schema_mismatch(self, complex_test_model):
        """Test nested list where items don't match expected schema."""
        schema_mismatch_data = {
            "name": "Test User",
            "other_addresses": [
                {"wrong_field": "value"},  # Wrong field name
                {"street": "Right St", "wrong_city": "Wrong"},  # Mix of right and wrong
            ],
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=schema_mismatch_data
        )
        rendered = form.render_inputs()

        # Should handle gracefully
        assert rendered is not None
        assert form.values_dict["name"] == "Test User"
        # The malformed data should be preserved in internal state
        assert "other_addresses" in form.values_dict
        assert len(form.values_dict["other_addresses"]) == 2

    def test_large_list_performance(self, complex_test_model):
        """Test handling of large lists."""
        large_list_data = {
            "name": "Large List User",
            "tags": [f"tag_{i}" for i in range(100)],
            "other_addresses": [
                {"street": f"Street {i}", "city": f"City {i}"} for i in range(50)
            ],
        }

        form = PydanticForm("test", complex_test_model, initial_values=large_list_data)
        rendered = form.render_inputs()

        # Should handle large lists
        assert rendered is not None
        assert form.values_dict["name"] == "Large List User"
        assert len(form.values_dict["tags"]) == 100
        assert form.values_dict["tags"][0] == "tag_0"
        assert len(form.values_dict["other_addresses"]) == 50
        assert form.values_dict["other_addresses"][0]["street"] == "Street 0"

    def test_nested_list_circular_reference(self, complex_test_model):
        """Test nested list with circular references."""
        from typing import Any, Dict

        # Create a circular reference scenario
        circular_item: Dict[str, Any] = {
            "street": "Circular St",
            "city": "Circular City",
        }
        circular_item["self_ref"] = circular_item  # Circular reference

        circular_list_data = {
            "name": "Circular User",
            "other_addresses": [circular_item],
        }

        form = PydanticForm(
            "test", complex_test_model, initial_values=circular_list_data
        )
        rendered = form.render_inputs()

        # Should handle circular references gracefully
        assert rendered is not None
        assert form.values_dict["name"] == "Circular User"
        assert len(form.values_dict["other_addresses"]) == 1
        assert form.values_dict["other_addresses"][0]["street"] == "Circular St"


class TestComplexScenarios:
    """Test complex scenarios combining multiple robustness challenges."""

    def test_multiple_nesting_levels_with_partial_data(self, complex_test_model):
        """Test multiple levels of nesting with partial data at each level."""
        multi_level_data = {
            "name": "Multi User",
            # Some fields missing
            "main_address": {
                "street": "Main St"
                # city missing
            },
            "other_addresses": [
                {"street": "Other St"},  # city missing
                {},  # completely empty
            ],
            "more_custom_details": [
                {"value": "Detail 1"},  # confidence missing
                {"confidence": "HIGH"},  # value missing
            ],
        }

        form = PydanticForm("test", complex_test_model, initial_values=multi_level_data)
        rendered = form.render_inputs()

        # Should handle all partial data gracefully - check internal state
        assert rendered is not None
        assert form.values_dict["name"] == "Multi User"
        assert form.values_dict["main_address"]["street"] == "Main St"
        assert len(form.values_dict["other_addresses"]) == 2
        assert len(form.values_dict["more_custom_details"]) == 2

    def test_mixed_valid_invalid_across_structure(self, complex_test_model):
        """Test mixture of valid and invalid data across the entire structure."""
        mixed_data = {
            "name": "Mixed User",
            "age": "not_a_number",  # Invalid type
            "is_active": "not_a_boolean",  # Invalid type
            "main_address": "not_an_object",  # Invalid type
            "tags": "not_a_list",  # Invalid type
            "other_addresses": [
                {"street": "Valid St", "city": "Valid City"},  # Valid
                "invalid_item",  # Invalid
                {"street": 123, "city": None},  # Invalid types
            ],
            "more_custom_details": None,  # None instead of list
        }

        form = PydanticForm("test", complex_test_model, initial_values=mixed_data)
        rendered = form.render_inputs()

        # Should preserve valid data and handle invalid gracefully - check internal state
        assert rendered is not None
        assert form.values_dict["name"] == "Mixed User"
        # Check that the form preserves what it can from the mixed data
        assert "other_addresses" in form.values_dict

    def test_schema_evolution_with_nested_changes(self, complex_test_model):
        """Test schema evolution scenarios with nested model changes."""
        # Simulate old data format with different nested structure
        old_format_data = {
            "name": "Evolution User",
            "main_address": {
                "address_line": "Old Format Street",  # Different field name
                "town": "Old Format Town",  # Different field name
            },
            "addresses": [  # Different list name
                {"address_line": "Old List Street", "town": "Old List Town"}
            ],
        }

        form = PydanticForm("test", complex_test_model, initial_values=old_format_data)
        rendered = form.render_inputs()

        # Should handle gracefully despite schema mismatch
        assert rendered is not None
        assert form.values_dict["name"] == "Evolution User"
        # Form should preserve the provided data even if it doesn't match schema
        assert "main_address" in form.values_dict

    def test_recursive_nested_structures(self, complex_test_model):
        """Test handling of recursive nested structures."""
        recursive_data = {
            "name": "Recursive User",
            "main_address": {
                "street": "Recursive St",
                "city": "Recursive City",
                "nested": {"sub_nested": {"deep_field": "deep_value"}},
            },
        }

        form = PydanticForm("test", complex_test_model, initial_values=recursive_data)
        rendered = form.render_inputs()

        # Should handle deep nesting
        assert rendered is not None
        assert form.values_dict["name"] == "Recursive User"
        assert form.values_dict["main_address"]["street"] == "Recursive St"
        assert form.values_dict["main_address"]["city"] == "Recursive City"

    def test_error_recovery_during_rendering(self, complex_test_model, mocker):
        """Test error recovery during the rendering process."""
        mocker.patch("fh_pydantic_form.field_renderers.logger")

        # Data that might cause rendering errors
        problematic_data = {
            "name": "Problem User",
            "main_address": {"street": "Problem St", "city": "Problem City"},
            "other_addresses": [
                {"street": "Good St", "city": "Good City"},
                {"problematic_field": object()},  # Problematic data
            ],
        }

        form = PydanticForm("test", complex_test_model, initial_values=problematic_data)
        rendered = form.render_inputs()

        # Should recover from errors and continue rendering
        assert rendered is not None
        assert form.values_dict["name"] == "Problem User"
        assert form.values_dict["main_address"]["street"] == "Problem St"
        assert form.values_dict["main_address"]["city"] == "Problem City"
        # Should handle problematic list items gracefully
        assert "other_addresses" in form.values_dict
