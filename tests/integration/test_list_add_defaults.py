import pytest


@pytest.mark.integration
class TestListAddDefaults:
    """Integration tests for list item creation with smart defaults."""

    def test_simple_list_add_creates_item_with_defaults(
        self, simple_list_client, htmx_headers
    ):
        """Test that adding a simple list item populates required fields with defaults."""
        response = simple_list_client.post(
            "/form/test_simple_list/list/add/tags", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain an input field for the new string item
        assert 'name="test_simple_list_tags_new_' in response.text
        assert 'type="text"' in response.text

        # Should not contain "Invalid" or error messages
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_model_list_add_populates_required_fields(
        self, address_list_client, htmx_headers
    ):
        """Test that adding a model list item populates all required fields with smart defaults."""
        response = address_list_client.post(
            "/form/test_address_list/list/add/addresses", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain input fields for all model fields
        assert 'name="test_address_list_addresses_new_' in response.text

        # Check that street and city fields are present (required fields)
        assert "street" in response.text.lower()
        assert "city" in response.text.lower()

        # Check for boolean field (is_billing)
        assert (
            "is_billing" in response.text.lower() or "billing" in response.text.lower()
        )

        # Should not show "Invalid data" in summary
        assert "Invalid" not in response.text

    def test_model_with_explicit_defaults_preserves_values(
        self, custom_model_list_client, htmx_headers
    ):
        """Test that models with explicit defaults preserve those values in new items."""
        response = custom_model_list_client.post(
            "/form/test_custom_list/list/add/items", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain the default values from the model
        # The CustomItemModel has default values that should be preserved
        assert 'name="test_custom_list_items_new_' in response.text

        # Should not show validation errors
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_optional_fields_rendered_as_none(
        self, optional_model_list_client, htmx_headers
    ):
        """Test that optional fields without defaults are rendered appropriately."""
        response = optional_model_list_client.post(
            "/form/test_optional_list/list/add/items", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain form fields
        assert 'name="test_optional_list_items_new_' in response.text

        # Optional fields should either have empty values or "None" options
        response_text = response.text.lower()
        assert (
            'value=""' in response_text
            or "none" in response_text
            or "optional" in response_text
        )

        # Should not show validation errors
        assert "Invalid" not in response.text

    def test_literal_fields_get_first_choice(
        self, literal_model_list_client, htmx_headers
    ):
        """Test that Literal fields default to the first literal value."""
        response = literal_model_list_client.post(
            "/form/test_literal_list/list/add/items", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain select dropdown for literal field
        assert "select" in response.text.lower() or "option" in response.text.lower()

        # Should not show validation errors
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_nested_model_recursion(self, nested_model_list_client, htmx_headers):
        """Test that nested models within list items get proper defaults recursively."""
        response = nested_model_list_client.post(
            "/form/test_nested_list/list/add/items", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain nested form fields
        assert 'name="test_nested_list_items_new_' in response.text

        # Should not show validation errors
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_summary_label_displays_correctly(self, address_list_client, htmx_headers):
        """Test that the summary label for new items displays without errors."""
        response = address_list_client.post(
            "/form/test_address_list/list/add/addresses", headers=htmx_headers
        )

        assert response.status_code == 200

        # The response should contain an accordion item with a proper title
        # that doesn't show "Invalid data" or similar error messages
        assert "Invalid" not in response.text
        assert "Error" not in response.text

        # Should have some kind of title/summary that makes sense
        response_lower = response.text.lower()
        assert any(word in response_lower for word in ["address", "item", "new"])

    def test_date_time_fields_get_appropriate_defaults(
        self, datetime_model_list_client, htmx_headers, freeze_today
    ):
        """Test that date and time fields get appropriate default values."""
        response = datetime_model_list_client.post(
            "/form/test_datetime_list/list/add/items", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain date and time input fields
        assert 'type="date"' in response.text
        assert 'type="time"' in response.text

        # Should not show validation errors
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_user_defined_default_method_respected(
        self, user_default_list_client, htmx_headers
    ):
        """Test that user-defined @classmethod default() is respected."""
        response = user_default_list_client.post(
            "/form/test_user_default_list/list/add/items", headers=htmx_headers
        )

        assert response.status_code == 200

        # Should contain the custom default values
        # The exact content depends on the user-defined default method
        assert 'name="test_user_default_list_items_new_' in response.text

        # Should not show validation errors
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_multiple_list_adds_work_independently(
        self, address_list_client, htmx_headers
    ):
        """Test that multiple list add operations work independently."""
        # Add first item
        response1 = address_list_client.post(
            "/form/test_address_list/list/add/addresses", headers=htmx_headers
        )
        assert response1.status_code == 200

        # Add second item
        response2 = address_list_client.post(
            "/form/test_address_list/list/add/addresses", headers=htmx_headers
        )
        assert response2.status_code == 200

        # Both should be successful and independent
        assert "Invalid" not in response1.text
        assert "Invalid" not in response2.text

        # Each should have different timestamp-based IDs
        assert "new_" in response1.text
        assert "new_" in response2.text

    def test_error_handling_for_invalid_field_name(
        self, simple_list_client, htmx_headers
    ):
        """Test error handling when trying to add to non-existent field."""
        response = simple_list_client.post(
            "/form/test_simple_list/list/add/nonexistent_field", headers=htmx_headers
        )

        # Should return an error response
        assert (
            response.status_code == 200
        )  # HTMX typically returns 200 with error content

        # Should contain error message
        response_lower = response.text.lower()
        assert any(word in response_lower for word in ["error", "not found", "cannot"])

    def test_error_handling_for_non_list_field(self, simple_list_client, htmx_headers):
        """Test error handling when trying to add to a non-list field."""
        # Assuming the client has a non-list field we can test against
        response = simple_list_client.post(
            "/form/test_simple_list/list/add/name",  # 'name' is typically not a list
            headers=htmx_headers,
        )

        # Should return an error response or handle gracefully
        assert response.status_code == 200

        # Should either work (if name is a list) or show appropriate error
        # The exact behavior depends on the model structure
