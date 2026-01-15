import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

import re

import pytest


def get_base_form_data():
    """Return base form data with all required fields for ComplexNestedTestSchema."""
    return {
        "test_complex_nested_creation_date": "2023-06-01",
        "test_complex_nested_start_time": "14:30",
        "test_complex_nested_custom_detail_value": "Test Detail",
        "test_complex_nested_custom_detail_confidence": "MEDIUM",
    }


def assert_json_contains(response_text: str, expected_content: str) -> None:
    """
    Assert that the response text contains the expected JSON content,
    handling both HTML-encoded and unencoded quotes.

    This function checks for the content in both formats:
    - HTML-encoded: &quot;key&quot;: value
    - Unencoded: "key": value
    """
    # Check for both HTML-encoded and unencoded versions
    encoded_version = expected_content.replace('"', "&quot;")
    unencoded_version = expected_content.replace("&quot;", '"')

    # Try both versions
    if encoded_version in response_text or unencoded_version in response_text:
        return

    # If neither works, provide a helpful error message
    raise AssertionError(
        f"Expected JSON content not found in response.\n"
        f"Expected (encoded): {encoded_version}\n"
        f"Expected (unencoded): {unencoded_version}\n"
        f"Response text: {response_text[:500]}..."
    )


@pytest.mark.e2e
class TestNestedListWorkflow:
    """End-to-end workflow tests for nested list functionality."""

    def test_nested_list_happy_path_submission(
        self, complex_nested_client, htmx_headers
    ):
        """Test complete workflow: build form -> add nested tags -> submit -> validate."""
        # Prepare form data with nested lists
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "E2E Test User",
            "test_complex_nested_age": "35",
            "test_complex_nested_score": "88.5",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_description": "End-to-end testing",
            "test_complex_nested_status": "PROCESSING",
            # Top-level tags
            "test_complex_nested_tags_0": "e2e",
            "test_complex_nested_tags_1": "testing",
            # Main address with nested tags
            "test_complex_nested_main_address_street": "123 E2E Street",
            "test_complex_nested_main_address_city": "Test City",
            "test_complex_nested_main_address_is_billing": "on",
            "test_complex_nested_main_address_tags_0": "home",
            "test_complex_nested_main_address_tags_1": "primary",
            # Other addresses with double-nested tags
            "test_complex_nested_other_addresses_0_street": "456 Other Street",
            "test_complex_nested_other_addresses_0_city": "Other City",
            "test_complex_nested_other_addresses_0_is_billing": "",  # False
            "test_complex_nested_other_addresses_0_tags_0": "work",
            "test_complex_nested_other_addresses_0_tags_1": "backup",
            # More custom details
            "test_complex_nested_more_custom_details_0_value": "More E2E Detail",
            "test_complex_nested_more_custom_details_0_confidence": "MEDIUM",
        }

        # Submit the form
        response = complex_nested_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Successful" in response.text

        # Verify nested list data is present in the response (HTML format, not JSON)
        assert "e2e" in response.text
        assert "testing" in response.text

        # Verify main_address nested tags
        assert "home" in response.text
        assert "primary" in response.text

        # Verify double-nested tags in other_addresses
        assert "work" in response.text
        assert "backup" in response.text

    def test_add_nested_tags_dynamically_then_submit(
        self, complex_nested_client, htmx_headers, patch_time
    ):
        """Test adding nested tags dynamically via HTMX then submitting the form."""
        # First, add a tag to main_address
        add_response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        assert add_response.status_code == 200

        # Extract the new field name from the response - account for form prefix
        match = re.search(
            r'name="(test_complex_nested_main_address_tags_new_\d+)"', add_response.text
        )
        assert match is not None
        new_tag_field = match.group(1)

        # Now submit a form with both existing and new tags
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Dynamic Test User",
            "test_complex_nested_age": "40",
            "test_complex_nested_score": "92.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "COMPLETED",
            # Main address base fields
            "test_complex_nested_main_address_street": "789 Dynamic St",
            "test_complex_nested_main_address_city": "Dynamic City",
            # Existing tags (from initial values)
            "test_complex_nested_main_address_tags_0": "existing_home",
            "test_complex_nested_main_address_tags_1": "existing_primary",
            # New tag added dynamically
            new_tag_field: "dynamically_added",
        }

        response = complex_nested_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Successful" in response.text

        # Should contain all tags
        assert "existing_home" in response.text
        assert "existing_primary" in response.text
        assert "dynamically_added" in response.text

    def test_refresh_preserves_nested_list_state(
        self, complex_nested_client, htmx_headers
    ):
        """Test that form refresh preserves nested list modifications."""
        # Submit form with nested list modifications
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Refresh User",
            "test_complex_nested_age": "28",
            "test_complex_nested_score": "85.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "PENDING",
            # Modified main address tags
            "test_complex_nested_main_address_street": "321 Refresh Ave",
            "test_complex_nested_main_address_city": "Refresh Town",
            "test_complex_nested_main_address_tags_0": "modified_home",
            "test_complex_nested_main_address_tags_1": "modified_primary",
            "test_complex_nested_main_address_tags_2": "added_tag",
        }

        # Trigger refresh
        response = complex_nested_client.post(
            "/form/test_complex_nested/refresh",
            data=form_data,
            headers=htmx_headers,
        )

        assert response.status_code == 200

        # Should preserve all the nested modifications
        assert "modified_home" in response.text
        assert "modified_primary" in response.text
        assert "added_tag" in response.text
        assert "Refresh User" in response.text

    def test_reset_restores_initial_nested_values(
        self, complex_nested_client, htmx_headers
    ):
        """Test that form reset restores initial nested list values."""
        # Trigger reset
        response = complex_nested_client.post(
            "/form/test_complex_nested/reset",
            headers=htmx_headers,
        )

        assert response.status_code == 200

        # Should restore initial values (from complex_nested_client fixture)
        assert "Nested Test User" in response.text
        assert "Test City" in response.text

        # Should restore initial nested tags
        # The initial values from the fixture include:
        # main_address tags: ["home", "primary"]
        # other_addresses[0] tags: ["work", "backup"]
        assert "home" in response.text or "primary" in response.text
        assert "work" in response.text or "backup" in response.text

    def test_complex_nested_validation_errors(
        self, complex_nested_client, htmx_headers
    ):
        """Test validation errors with nested list data."""
        # Submit form with invalid data
        invalid_form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Invalid User",
            "test_complex_nested_age": "not_a_number",  # Invalid
            "test_complex_nested_score": "also_invalid",  # Invalid
            "test_complex_nested_status": "INVALID_STATUS",  # Invalid literal
            # Valid nested data - should be preserved in error response
            "test_complex_nested_main_address_street": "Valid Street",
            "test_complex_nested_main_address_tags_0": "valid_tag",
        }

        response = complex_nested_client.post(
            "/submit_form", data=invalid_form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Error" in response.text

        # Should show validation errors
        assert "Input should be a valid integer" in response.text
        assert "Input should be a valid number" in response.text

    def test_empty_nested_lists_submission(self, complex_nested_client, htmx_headers):
        """Test submission with empty nested lists."""
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Empty Lists User",
            "test_complex_nested_age": "25",
            "test_complex_nested_score": "90.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "PENDING",
            # Main address without tags
            "test_complex_nested_main_address_street": "123 Empty St",
            "test_complex_nested_main_address_city": "Empty City",
            # No nested list data provided
        }

        response = complex_nested_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Successful" in response.text

        # Should handle empty nested lists gracefully
        # Check for empty list indicators in the HTML response
        assert "Empty Lists User" in response.text

    def test_mixed_nested_and_simple_lists(self, complex_nested_client, htmx_headers):
        """Test forms with both simple lists (top-level) and nested lists."""
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Mixed Lists User",
            "test_complex_nested_age": "33",
            "test_complex_nested_score": "87.5",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "PROCESSING",
            # Top-level simple list
            "test_complex_nested_tags_0": "top_level_1",
            "test_complex_nested_tags_1": "top_level_2",
            # Nested simple list in main_address
            "test_complex_nested_main_address_street": "456 Mixed St",
            "test_complex_nested_main_address_city": "Mixed City",
            "test_complex_nested_main_address_tags_0": "nested_1",
            "test_complex_nested_main_address_tags_1": "nested_2",
            # Double-nested in other_addresses
            "test_complex_nested_other_addresses_0_street": "789 Double St",
            "test_complex_nested_other_addresses_0_city": "Double City",
            "test_complex_nested_other_addresses_0_tags_0": "double_nested",
        }

        response = complex_nested_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Successful" in response.text

        # Should contain all levels of lists
        assert "top_level_1" in response.text
        assert "nested_1" in response.text
        assert "double_nested" in response.text

    def test_large_nested_list_performance(self, complex_nested_client, htmx_headers):
        """Test performance with larger nested lists."""
        # Build form data with many nested items
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Performance User",
            "test_complex_nested_age": "45",
            "test_complex_nested_score": "95.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "COMPLETED",
            # Main address
            "test_complex_nested_main_address_street": "Performance St",
            "test_complex_nested_main_address_city": "Performance City",
        }

        # Add many nested tags
        for i in range(20):  # 20 tags should be reasonable for testing
            form_data[f"test_complex_nested_main_address_tags_{i}"] = f"perf_tag_{i}"

        # Add multiple other addresses with tags
        for addr_idx in range(3):
            form_data[f"test_complex_nested_other_addresses_{addr_idx}_street"] = (
                f"Addr {addr_idx} St"
            )
            form_data[f"test_complex_nested_other_addresses_{addr_idx}_city"] = (
                f"City {addr_idx}"
            )
            for tag_idx in range(5):
                form_data[
                    f"test_complex_nested_other_addresses_{addr_idx}_tags_{tag_idx}"
                ] = f"addr_{addr_idx}_tag_{tag_idx}"

        response = complex_nested_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Successful" in response.text

        # Spot check a few items
        assert "perf_tag_0" in response.text
        assert "perf_tag_19" in response.text
        assert "addr_0_tag_0" in response.text
        assert "addr_2_tag_4" in response.text

    def test_nested_list_with_special_characters(
        self, complex_nested_client, htmx_headers
    ):
        """Test nested lists with special characters in values."""
        form_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Special Chars User",
            "test_complex_nested_age": "30",
            "test_complex_nested_score": "88.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "PROCESSING",
            # Main address with special character tags
            "test_complex_nested_main_address_street": "Special & Street",
            "test_complex_nested_main_address_city": "City with Spaces",
            "test_complex_nested_main_address_tags_0": "tag with spaces",
            "test_complex_nested_main_address_tags_1": "tag-with-dashes",
            "test_complex_nested_main_address_tags_2": "tag_with_underscores",
            "test_complex_nested_main_address_tags_3": "tag.with.dots",
        }

        response = complex_nested_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Successful" in response.text

        # Should handle special characters properly
        assert "tag with spaces" in response.text
        assert "tag-with-dashes" in response.text
        assert "tag_with_underscores" in response.text
        assert "tag.with.dots" in response.text

    def test_concurrent_nested_operations(
        self, complex_nested_client, htmx_headers, patch_time
    ):
        """Test multiple concurrent operations on nested lists."""
        # This simulates rapid user interactions

        # Add to main_address tags
        response1 = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        assert response1.status_code == 200

        # Add to other_addresses tags
        response2 = complex_nested_client.post(
            "/form/test_complex_nested/list/add/other_addresses/0/tags",
            headers=htmx_headers,
        )
        assert response2.status_code == 200

        # Both operations should succeed independently
        assert "Invalid" not in response1.text
        assert "Invalid" not in response2.text

        # Should have different field names/IDs - account for form prefix
        assert "test_complex_nested_main_address_tags_new_" in response1.text
        assert "test_complex_nested_other_addresses_0_tags_new_" in response2.text

    def test_workflow_state_consistency(self, complex_nested_client, htmx_headers):
        """Test that workflow state remains consistent through multiple operations."""
        # This test ensures that the form state is properly managed
        # throughout a complex workflow of operations

        initial_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Consistency User",
            "test_complex_nested_age": "35",
            "test_complex_nested_score": "90.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "PENDING",
            "test_complex_nested_main_address_street": "Consistency St",
            "test_complex_nested_main_address_city": "Consistency City",
            "test_complex_nested_main_address_tags_0": "initial_tag",
        }

        # 1. Refresh with initial data
        refresh_response = complex_nested_client.post(
            "/form/test_complex_nested/refresh",
            data=initial_data,
            headers=htmx_headers,
        )
        assert refresh_response.status_code == 200
        assert "initial_tag" in refresh_response.text

        # 2. Reset to original state
        reset_response = complex_nested_client.post(
            "/form/test_complex_nested/reset",
            headers=htmx_headers,
        )
        assert reset_response.status_code == 200

        # 3. Final submission should work with original state
        final_data = {
            **get_base_form_data(),
            "test_complex_nested_name": "Final User",
            "test_complex_nested_age": "40",
            "test_complex_nested_score": "95.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "COMPLETED",
            "test_complex_nested_main_address_street": "Final St",
            "test_complex_nested_main_address_city": "Final City",
        }

        final_response = complex_nested_client.post(
            "/submit_form", data=final_data, headers=htmx_headers
        )
        assert final_response.status_code == 200
        assert "Validation Successful" in final_response.text


@pytest.mark.e2e
class TestOptionalListWorkflow:
    """End-to-end workflow tests for Optional[List[...]] functionality."""

    def test_submit_form_with_empty_optional_list_parses_as_none(
        self, optional_list_client, htmx_headers
    ):
        """
        E2E test to ensure submitting a form with no items in an optional list
        results in a `None` value after validation.
        """
        # Arrange: Form data with no items for 'optional_tags'
        form_data = {
            "optional_list_form_name": "E2E Test",
            # No 'optional_list_form_optional_tags_...' fields are sent
            # An empty required list will also be sent
        }

        # Act
        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        # Assert
        assert response.status_code == 200
        assert "Validation Successful" in response.text
        # The validated JSON output should show "optional_tags": null
        assert_json_contains(response.text, '"optional_tags": null')
        # The required list should be an empty array
        assert_json_contains(response.text, '"required_tags": []')

    def test_submit_form_with_populated_optional_list_parses_as_list(
        self, optional_list_client, htmx_headers
    ):
        """
        E2E test to ensure submitting a form with items in an optional list
        results in a list value after validation.
        """
        # Arrange
        form_data = {
            "optional_list_form_name": "E2E Test with Items",
            "optional_list_form_optional_tags_0": "item1",
            "optional_list_form_optional_tags_1": "item2",
        }

        # Act
        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        # Assert
        assert response.status_code == 200
        assert "Validation Successful" in response.text
        # The validated JSON output should show a list with the items
        assert_json_contains(
            response.text, '"optional_tags": [\n    "item1",\n    "item2"\n  ]'
        )

    def test_submit_form_with_populated_required_list_parses_as_list(
        self, optional_list_client, htmx_headers
    ):
        """
        E2E test to ensure submitting a form with items in a required list
        results in a list value after validation.
        """
        # Arrange
        form_data = {
            "optional_list_form_name": "E2E Test Required",
            "optional_list_form_required_tags_0": "req1",
            "optional_list_form_required_tags_1": "req2",
        }

        # Act
        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        # Assert
        assert response.status_code == 200
        assert "Validation Successful" in response.text
        # The validated JSON output should show a list with the items
        assert_json_contains(
            response.text, '"required_tags": [\n    "req1",\n    "req2"\n  ]'
        )
        # The optional list should be null
        assert_json_contains(response.text, '"optional_tags": null')

    def test_submit_form_with_mixed_optional_and_required_lists(
        self, optional_list_client, htmx_headers
    ):
        """
        E2E test to ensure mixed optional and required lists work correctly.
        """
        # Arrange
        form_data = {
            "optional_list_form_name": "Mixed Test",
            "optional_list_form_optional_tags_0": "opt1",
            "optional_list_form_required_tags_0": "req1",
            "optional_list_form_required_tags_1": "req2",
        }

        # Act
        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        # Assert
        assert response.status_code == 200
        assert "Validation Successful" in response.text
        # Both lists should have items
        assert_json_contains(response.text, '"optional_tags": [\n    "opt1"\n  ]')
        assert_json_contains(
            response.text, '"required_tags": [\n    "req1",\n    "req2"\n  ]'
        )

    def test_add_item_to_optional_list_then_submit(
        self, optional_list_client, htmx_headers, patch_time
    ):
        """
        E2E test to ensure adding items to optional lists via HTMX works correctly.
        """
        # First, add an item to optional_tags
        add_response = optional_list_client.post(
            "/form/optional_list_form/list/add/optional_tags", headers=htmx_headers
        )
        assert add_response.status_code == 200

        # Extract the new field name from the response
        import re

        match = re.search(
            r'name="(optional_list_form_optional_tags_new_\d+)"', add_response.text
        )
        assert match is not None
        new_field_name = match.group(1)

        # Now submit the form with the new field
        form_data = {
            "optional_list_form_name": "Dynamic Add Test",
            new_field_name: "dynamically_added_item",
        }

        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        # Assert
        assert response.status_code == 200
        assert "Validation Successful" in response.text
        # The dynamically added item should be in the result
        assert_json_contains(
            response.text, '"optional_tags": [\n    "dynamically_added_item"\n  ]'
        )

    def test_add_item_to_required_list_then_submit(
        self, optional_list_client, htmx_headers, patch_time
    ):
        """
        E2E test to ensure adding items to required lists via HTMX works correctly.
        """
        # First, add an item to required_tags
        add_response = optional_list_client.post(
            "/form/optional_list_form/list/add/required_tags", headers=htmx_headers
        )
        assert add_response.status_code == 200

        # Extract the new field name from the response
        import re

        match = re.search(
            r'name="(optional_list_form_required_tags_new_\d+)"', add_response.text
        )
        assert match is not None
        new_field_name = match.group(1)

        # Now submit the form with the new field
        form_data = {
            "optional_list_form_name": "Dynamic Add Required Test",
            new_field_name: "dynamically_added_required_item",
        }

        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        # Assert
        assert response.status_code == 200
        assert "Validation Successful" in response.text
        # The dynamically added item should be in the result
        assert_json_contains(
            response.text,
            '"required_tags": [\n    "dynamically_added_required_item"\n  ]',
        )

    def test_validation_error_preserves_optional_list_state(
        self, optional_list_client, htmx_headers
    ):
        """
        E2E test to ensure validation errors preserve the state of optional lists.
        """
        # Trigger a validation error by submitting an empty name (min_length=1)
        form_data = {
            "optional_list_form_name": "",
            "optional_list_form_optional_tags_0": "opt_error_1",
            "optional_list_form_optional_tags_1": "opt_error_2",
            "optional_list_form_required_tags_0": "req_error_1",
        }

        response = optional_list_client.post(
            "/submit", data=form_data, headers=htmx_headers
        )

        assert response.status_code == 200
        assert "Validation Error" in response.text

        # The optional/required list values should still be present in the rendered form
        assert "opt_error_1" in response.text
        assert "opt_error_2" in response.text
        assert "req_error_1" in response.text
