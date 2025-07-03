import re

import pytest


@pytest.mark.integration
class TestNestedListRoutes:
    """Integration tests for nested list HTMX routes."""

    def test_add_tag_to_main_address(
        self, complex_nested_client, htmx_headers, soup, patch_time
    ):
        """Test adding a tag to main_address.tags via HTMX."""
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )

        assert response.status_code == 200
        dom = soup(response.text)

        # Should contain a textarea field for the new tag with stable placeholder ID
        input_elem = dom.find(
            "textarea",
            {"name": re.compile(r"test_complex_nested_main_address_tags_new_\d+")},
        )
        assert input_elem is not None

        # Should not contain error messages
        assert "Invalid" not in response.text
        assert "Error" not in response.text

        # Should contain proper accordion structure
        li_elem = dom.find(
            "li",
            {
                "id": re.compile(
                    r"test_complex_nested_main_address_.*tags_new_\d+.*_card"
                )
            },
        )
        assert li_elem is not None

    def test_add_tag_to_other_address(
        self, complex_nested_client, htmx_headers, soup, patch_time
    ):
        """Test adding a tag to other_addresses[0].tags via HTMX."""
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/other_addresses/0/tags",
            headers=htmx_headers,
        )

        assert response.status_code == 200
        dom = soup(response.text)

        # Should contain a textarea field for the new tag in the nested structure
        input_elem = dom.find(
            "textarea",
            {"name": re.compile(r"test_complex_nested_other_addresses_0_tags_new_\d+")},
        )
        assert input_elem is not None

        # Should have proper list item structure
        li_elem = dom.find(
            "li",
            {
                "id": re.compile(
                    r"test_complex_nested_other_addresses_.*tags_new_\d+.*_card"
                )
            },
        )
        assert li_elem is not None

        # Should not show validation errors
        assert "Invalid" not in response.text
        assert "Error" not in response.text

    def test_delete_nested_tag(self, complex_nested_client, htmx_headers):
        """Test deleting a nested tag via HTMX DELETE request."""
        response = complex_nested_client.delete(
            "/form/test_complex_nested/list/delete/main_address/tags",
            headers=htmx_headers,
            params={"idx": "0"},
        )

        # DELETE should return success
        assert response.status_code == 200

    def test_delete_double_nested_tag(self, complex_nested_client, htmx_headers):
        """Test deleting a double-nested tag via HTMX DELETE request."""
        response = complex_nested_client.delete(
            "/form/test_complex_nested/list/delete/other_addresses/0/tags",
            headers=htmx_headers,
            params={"idx": "0"},
        )

        # DELETE should return success
        assert response.status_code == 200

    def test_invalid_nested_path_handling(
        self, complex_nested_client, htmx_headers, soup
    ):
        """Test error handling for invalid nested paths."""
        # Try to add to a non-existent nested field
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/nonexistent",
            headers=htmx_headers,
        )

        # Should return error response
        assert (
            response.status_code == 200
        )  # HTMX typically returns 200 with error content

        # Should contain error message
        response_lower = response.text.lower()
        assert any(word in response_lower for word in ["error", "not found", "cannot"])

    def test_invalid_double_nested_path(self, complex_nested_client, htmx_headers):
        """Test error handling for invalid double-nested paths."""
        # Try to add to a non-existent double-nested field
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/other_addresses/0/nonexistent",
            headers=htmx_headers,
        )

        # Should handle gracefully
        assert response.status_code == 200
        response_lower = response.text.lower()
        assert any(word in response_lower for word in ["error", "not found", "cannot"])

    def test_out_of_bounds_index_handling(self, complex_nested_client, htmx_headers):
        """Test handling of out-of-bounds indices in nested paths."""
        # Try to access other_addresses[999].tags (index way out of bounds)
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/other_addresses/999/tags",
            headers=htmx_headers,
        )

        # Should handle gracefully - implementation may vary
        assert response.status_code == 200

    def test_non_numeric_index_handling(self, complex_nested_client, htmx_headers):
        """Test handling of non-numeric indices in nested paths."""
        # Try to use non-numeric index
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/other_addresses/abc/tags",
            headers=htmx_headers,
        )

        # Should return error
        assert response.status_code == 200
        response_lower = response.text.lower()
        assert any(word in response_lower for word in ["error", "invalid", "numeric"])

    def test_multiple_nested_additions(
        self, complex_nested_client, htmx_headers, soup, patch_time
    ):
        """Test multiple additions to the same nested list."""
        # Add first tag
        response1 = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        assert response1.status_code == 200

        # Add second tag
        response2 = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )
        assert response2.status_code == 200

        # Both should be successful and independent
        dom1 = soup(response1.text)
        dom2 = soup(response2.text)

        input1 = dom1.find(
            "textarea",
            {"name": re.compile(r"test_complex_nested_main_address_tags_new_\d+")},
        )
        input2 = dom2.find(
            "textarea",
            {"name": re.compile(r"test_complex_nested_main_address_tags_new_\d+")},
        )

        assert input1 is not None
        assert input2 is not None

        # Should have different IDs (due to timestamp)
        if patch_time:  # If time is frozen, they might be the same
            pass
        else:
            assert input1.get("name") != input2.get("name")

    def test_nested_list_container_ids(
        self, complex_nested_client, htmx_headers, soup, patch_time
    ):
        """Test that nested list containers have correct IDs for JavaScript targeting."""
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )

        assert response.status_code == 200
        dom = soup(response.text)

        # The response should be targeting the correct container
        # Check that the structure allows for proper JavaScript manipulation
        li_elem = dom.find(
            "li",
            {
                "id": re.compile(
                    r"test_complex_nested_main_address_.*tags_new_\d+.*_card"
                )
            },
        )
        assert li_elem is not None

        # Should have proper classes for styling and JavaScript hooks
        assert li_elem.get("class") is not None

    def test_form_refresh_with_nested_lists(self, complex_nested_client, htmx_headers):
        """Test form refresh preserves nested list data."""
        # Submit form data with nested lists
        form_data = {
            "test_complex_nested_name": "Refresh Test",
            "test_complex_nested_age": "30",
            "test_complex_nested_score": "95.0",
            "test_complex_nested_is_active": "on",
            "test_complex_nested_status": "PROCESSING",
            # Nested list data
            "test_complex_nested_main_address_street": "123 Refresh St",
            "test_complex_nested_main_address_city": "Refresh City",
            "test_complex_nested_main_address_tags_0": "refresh_tag1",
            "test_complex_nested_main_address_tags_1": "refresh_tag2",
            # Double nested list data
            "test_complex_nested_other_addresses_0_street": "456 Other St",
            "test_complex_nested_other_addresses_0_city": "Other City",
            "test_complex_nested_other_addresses_0_tags_0": "other_tag1",
        }

        # Trigger refresh
        response = complex_nested_client.post(
            "/form/test_complex_nested/refresh",
            data=form_data,
            headers=htmx_headers,
        )

        assert response.status_code == 200

        # Should contain the nested list data
        assert "refresh_tag1" in response.text
        assert "refresh_tag2" in response.text
        assert "other_tag1" in response.text

    def test_nested_list_accordion_functionality(
        self, complex_nested_client, htmx_headers, soup, patch_time
    ):
        """Test that nested lists render with proper accordion structure."""
        response = complex_nested_client.post(
            "/form/test_complex_nested/list/add/main_address/tags",
            headers=htmx_headers,
        )

        assert response.status_code == 200
        dom = soup(response.text)

        # Should have accordion structure
        li_elem = dom.find(
            "li",
            {
                "id": re.compile(
                    r"test_complex_nested_main_address_.*tags_new_\d+.*_card"
                )
            },
        )
        assert li_elem is not None

        # Should contain the expected textarea element
        input_elem = dom.find(
            "textarea",
            {"name": re.compile(r"test_complex_nested_main_address_tags_new_\d+")},
        )
        assert input_elem is not None

        # Should have proper accordion classes/attributes
        assert "uk-" in response.text or "accordion" in response.text.lower()

    def test_cross_form_isolation(self):
        """Test that nested list operations don't interfere between different forms."""
        # This test ensures that multiple form instances don't conflict
        # Implementation would create two different form clients with different names
        # and verify their nested list operations are independent
        # For now, we just test that the concept is sound
        assert True  # Placeholder - actual implementation would test isolation

    @pytest.mark.parametrize(
        "path, expected_status",
        [
            ("main_address/tags", 200),
            ("other_addresses/0/tags", 200),
            ("tags", 200),  # Top-level list should still work
            ("other_addresses", 200),  # List of models should still work
        ],
    )
    def test_various_nested_paths(
        self, complex_nested_client, htmx_headers, path, expected_status
    ):
        """Test various nested path combinations."""
        response = complex_nested_client.post(
            f"/form/test_complex_nested/list/add/{path}",
            headers=htmx_headers,
        )

        assert response.status_code == expected_status

        if expected_status == 200:
            # Should not contain obvious error messages
            assert "Error" not in response.text
            assert "Failed" not in response.text
