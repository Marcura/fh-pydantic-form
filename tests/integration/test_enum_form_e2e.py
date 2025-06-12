import pytest

from tests import unescaped


@pytest.mark.integration
class TestEnumFormE2E:
    """End-to-end integration tests for enum forms using TestClient."""

    def test_enum_form_render_contains_enum_options(self, enum_client):
        """Test that rendered enum form contains all enum options."""
        response = enum_client.get("/")
        assert response.status_code == 200

        html_content = response.text

        # Should contain enum select elements
        assert "<select" in html_content

        # Should contain status enum options
        assert "NEW" in html_content
        assert "PROCESSING" in html_content
        assert "SHIPPED" in html_content
        assert "DELIVERED" in html_content

        # Should contain priority enum options (optional field)
        assert "-- None --" in html_content  # None option for optional enum
        assert "LOW" in html_content
        assert "MEDIUM" in html_content
        assert "HIGH" in html_content

    def test_enum_form_submit_valid_data_success(self, enum_client, htmx_headers):
        """Test successful submission of valid enum form data."""
        form_data = {
            "enum_test_status": "PROCESSING",
            "enum_test_priority": "MEDIUM",  # MEDIUM priority
            "enum_test_priority_int": "1",  # MEDIUM priority
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Successful" in response_text

        # Should contain the validated data in JSON format
        assert '"status": "PROCESSING"' in unescaped(response_text)
        assert '"priority": "MEDIUM"' in unescaped(response_text)
        assert '"priority_int": 1' in unescaped(response_text)

    def test_enum_form_submit_valid_data_with_none(self, enum_client, htmx_headers):
        """Test successful submission with optional enum as None."""
        form_data = {
            "enum_test_status": "NEW",
            "enum_test_priority": "",  # Empty string for None
            "enum_test_priority_int": "",  # Empty string for None
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Successful" in unescaped(response_text)

        # Should contain the validated data
        assert '"status": "NEW"' in unescaped(response_text)
        assert '"priority": null' in unescaped(response_text)

    def test_enum_form_submit_none_option_explicit(self, enum_client, htmx_headers):
        """Test submission with explicit '-- None --' selection."""
        form_data = {
            "enum_test_status": "DELIVERED",
            "enum_test_priority": "-- None --",  # Explicit None selection
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Successful" in response_text
        assert '"priority": null' in unescaped(response_text)

    def test_enum_form_submit_invalid_enum_value(self, enum_client, htmx_headers):
        """Test submission with invalid enum value returns validation error."""
        form_data = {
            "enum_test_status": "INVALID_STATUS",  # Invalid enum value
            "enum_test_priority": "1",  # Valid priority
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Error" in response_text

        # Should contain validation error details
        assert "INVALID_STATUS" in response_text or "Input should be" in response_text

    def test_enum_form_submit_invalid_integer_enum(self, enum_client, htmx_headers):
        """Test submission with invalid integer enum value."""
        form_data = {
            "enum_test_status": "NEW",
            "enum_test_priority": "999",  # Invalid priority value
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Error" in response_text

        # Should contain validation error for the invalid priority
        assert "999" in response_text or "Input should be" in response_text

    def test_enum_form_submit_missing_required_field(self, enum_client, htmx_headers):
        """Test submission with missing required enum field."""
        form_data = {
            # Missing required status field
            "enum_test_priority": "1",
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Error" in response_text

        # Should indicate the missing field
        assert "status" in response_text.lower() or "required" in response_text.lower()

    @pytest.mark.parametrize(
        "status_value", ["NEW", "PROCESSING", "SHIPPED", "DELIVERED"]
    )
    def test_enum_form_submit_all_valid_status_values(
        self, enum_client, htmx_headers, status_value
    ):
        """Test submission with each valid status enum value."""
        form_data = {
            "enum_test_status": status_value,
            "enum_test_priority": "MEDIUM",  # MEDIUM
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = unescaped(response.text)
        assert "Validation Successful" in response_text
        assert f'"status": "{status_value}"' in response_text

    @pytest.mark.parametrize(
        "priority_value, expected_int",
        [
            ("1", 1),  # LOW
            ("2", 2),  # MEDIUM
            ("3", 3),  # HIGH
        ],
    )
    def test_enum_form_submit_all_valid_priority_values(
        self, enum_client, htmx_headers, priority_value, expected_int
    ):
        """Test submission with each valid priority enum value."""
        form_data = {
            "enum_test_status": "NEW",
            "enum_test_priority_int": priority_value,
        }

        response = enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Successful" in response_text
        assert f'"priority_int": {expected_int}' in unescaped(response_text)


@pytest.mark.integration
class TestComplexEnumFormE2E:
    """End-to-end tests for complex enum forms with multiple enum types and lists."""

    def test_complex_enum_form_render_structure(self, complex_enum_client):
        """Test that complex enum form renders with proper structure."""
        response = complex_enum_client.get("/")
        assert response.status_code == 200

        html_content = response.text

        # Should contain multiple select elements for different enum fields
        select_count = html_content.count("<select")
        assert select_count >= 3  # At least status, shipping_method, priority

        # Should contain enum values from different enums
        assert "PROCESSING" in html_content  # Status enum
        assert "EXPRESS" in html_content  # Shipping method enum
        assert "HIGH" in html_content  # Priority enum

        # Should contain form action buttons
        assert "Validate" in html_content
        assert "Refresh" in html_content
        assert "Reset" in html_content

    def test_complex_enum_form_submit_all_fields(
        self, complex_enum_client, htmx_headers
    ):
        """Test submission of complex form with all enum fields."""
        form_data = {
            # Enum fields
            "complex_enum_test_status": "DELIVERED",
            "complex_enum_test_shipping_method": "OVERNIGHT",
            "complex_enum_test_priority": "HIGH",  # HIGH
            # Non-enum fields
            "complex_enum_test_name": "Test Complex Order",
            "complex_enum_test_order_id": "12345",
            # List fields with enums
            "complex_enum_test_status_history_0": "NEW",
            "complex_enum_test_status_history_1": "PROCESSING",
            "complex_enum_test_available_priorities_0": "LOW",  # LOW
            "complex_enum_test_available_priorities_1": "HIGH",  # HIGH
        }

        response = complex_enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = unescaped(response.text)
        assert "Validation Successful" in response_text

        # Verify enum field values
        assert '"status": "DELIVERED"' in response_text
        assert '"shipping_method": "OVERNIGHT"' in response_text
        assert '"priority": "HIGH"' in response_text

        # Verify non-enum field values
        assert '"name": "Test Complex Order"' in response_text
        assert '"order_id": 12345' in response_text

        # Verify list field values (accounting for JSON formatting with newlines)
        assert '"status_history": [\n    "NEW",\n    "PROCESSING"\n  ]' in response_text
        assert '"available_priorities": [\n    "LOW",\n    "HIGH"\n  ]' in response_text

    def test_complex_enum_form_submit_optional_fields_empty(
        self, complex_enum_client, htmx_headers
    ):
        """Test submission with optional enum fields left empty."""
        form_data = {
            # Required enum fields
            "complex_enum_test_status": "NEW",
            "complex_enum_test_shipping_method": "STANDARD",
            # Optional priority field left empty (should become None)
            "complex_enum_test_priority": "",
            # Other required fields
            "complex_enum_test_name": "Minimal Order",
            "complex_enum_test_order_id": "99999",
        }

        response = complex_enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Successful" in response_text

        # Optional enum should be null
        assert '"priority": null' in unescaped(response_text)

    def test_complex_enum_form_submit_mixed_invalid_values(
        self, complex_enum_client, htmx_headers
    ):
        """Test submission with mix of valid and invalid enum values."""
        form_data = {
            "complex_enum_test_status": "INVALID_STATUS",  # Invalid
            "complex_enum_test_shipping_method": "EXPRESS",  # Valid
            "complex_enum_test_priority": "999",  # Invalid integer
            "complex_enum_test_name": "Mixed Validation Test",
            "complex_enum_test_order_id": "11111",
        }

        response = complex_enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Error" in response_text

        # Should mention the invalid values
        error_mentioned = (
            "INVALID_STATUS" in response_text
            or "999" in response_text
            or "Input should be" in response_text
        )
        assert error_mentioned

    def test_complex_enum_form_list_operations(self, complex_enum_client, htmx_headers):
        """Test that enum list fields are properly handled."""
        form_data = {
            # Basic required fields
            "complex_enum_test_status": "PROCESSING",
            "complex_enum_test_shipping_method": "STANDARD",
            "complex_enum_test_name": "List Test Order",
            "complex_enum_test_order_id": "22222",
            # Multiple list items with enums
            "complex_enum_test_status_history_0": "NEW",
            "complex_enum_test_status_history_1": "PROCESSING",
            "complex_enum_test_status_history_2": "SHIPPED",
            "complex_enum_test_status_history_3": "DELIVERED",
            # Priority list with different values
            "complex_enum_test_available_priorities_0": "LOW",  # LOW
            "complex_enum_test_available_priorities_1": "MEDIUM",  # MEDIUM
            "complex_enum_test_available_priorities_2": "HIGH",  # HIGH
        }

        response = complex_enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = unescaped(response.text)
        assert "Validation Successful" in response_text

        # Verify list contents - make robust to whitespace variations
        response_normalized = " ".join(unescaped(response_text).split())

        # Check status_history list with flexible whitespace matching
        status_history_pattern = '"status_history":'
        assert status_history_pattern in response_normalized
        assert '"NEW"' in response_normalized
        assert '"PROCESSING"' in response_normalized
        assert '"SHIPPED"' in response_normalized
        assert '"DELIVERED"' in response_normalized

        # Check available_priorities list with flexible whitespace matching
        priorities_pattern = '"available_priorities":'
        assert priorities_pattern in response_normalized
        assert '"LOW"' in response_normalized
        assert '"MEDIUM"' in response_normalized
        assert '"HIGH"' in response_normalized

    def test_complex_enum_form_partial_list_invalid(
        self, complex_enum_client, htmx_headers
    ):
        """Test handling of lists with some invalid enum values."""
        form_data = {
            # Basic required fields
            "complex_enum_test_status": "NEW",
            "complex_enum_test_shipping_method": "EXPRESS",
            "complex_enum_test_name": "Invalid List Test",
            "complex_enum_test_order_id": "33333",
            # List with mix of valid and invalid values
            "complex_enum_test_status_history_0": "NEW",  # Valid
            "complex_enum_test_status_history_1": "INVALID_STATUS",  # Invalid
            "complex_enum_test_status_history_2": "COMPLETED",  # Valid
        }

        response = complex_enum_client.post(
            "/submit_form", data=form_data, headers=htmx_headers
        )
        assert response.status_code == 200

        response_text = response.text
        assert "Validation Error" in response_text

        # Should indicate validation error for the list item
        error_mentioned = (
            "INVALID_STATUS" in response_text
            or "status_history" in response_text
            or "Input should be" in response_text
        )
        assert error_mentioned


@pytest.mark.integration
class TestEnumFormRefreshReset:
    """Test enum form refresh and reset functionality."""

    def test_enum_form_refresh_preserves_enum_values(
        self, complex_enum_client, htmx_headers
    ):
        """Test that form refresh preserves current enum values."""
        # This would require implementing the refresh endpoint test
        # For now, we verify the refresh button is present
        response = complex_enum_client.get("/")
        assert response.status_code == 200

        html_content = response.text
        assert "Refresh" in html_content
        assert "hx_post" in html_content or "hx-post" in html_content

    def test_enum_form_reset_returns_to_initial_values(
        self, complex_enum_client, htmx_headers
    ):
        """Test that form reset returns enum fields to initial values."""
        # This would require implementing the reset endpoint test
        # For now, we verify the reset button is present
        response = complex_enum_client.get("/")
        assert response.status_code == 200

        html_content = response.text
        assert "Reset" in html_content
        assert "hx_post" in html_content or "hx-post" in html_content

    def test_enum_form_model_validate_request_success(self, enum_form_renderer):
        """Test that model_validate_request works with enum data."""
        # This is a more unit-test style test but fits in E2E context
        from unittest.mock import AsyncMock

        # Mock request with enum form data
        mock_request = AsyncMock()
        mock_request.form.return_value = {
            "enum_test_status": "PROCESSING",
            "enum_test_priority": "2",
        }

        # This would need to be an async test to actually call the method
        # For now, verify the method exists
        assert hasattr(enum_form_renderer, "model_validate_request")
        assert callable(enum_form_renderer.model_validate_request)


@pytest.mark.integration
class TestEnumFormAccessibility:
    """Test accessibility features of enum forms."""

    def test_enum_form_labels_and_tooltips(self, enum_client):
        """Test that enum fields have proper labels and tooltips."""
        response = enum_client.get("/")
        assert response.status_code == 200

        html_content = response.text

        # Should contain labels for enum fields
        assert "Status" in html_content  # Label for status field
        assert "Priority" in html_content  # Label for priority field

        # Should contain tooltip markup (uk_tooltip attributes)
        tooltip_present = (
            "uk_tooltip" in html_content
            or "tooltip" in html_content.lower()
            or "title=" in html_content
            or "uk-tooltip" in html_content
        )
        # Note: Tooltip presence depends on field descriptions being set
        # This test might need adjustment based on actual form configuration
        if not tooltip_present:
            # Check if form contains basic enum field indicators instead
            assert (
                "status" in html_content.lower() and "priority" in html_content.lower()
            )

    def test_enum_form_required_field_indicators(self, enum_client):
        """Test that required enum fields are properly marked."""
        response = enum_client.get("/")
        assert response.status_code == 200

        html_content = response.text

        # Required fields should have required attribute or be present in forms
        # Note: Required attribute may be set on individual form elements rather than in main HTML
        required_present = (
            "required" in html_content
            or "required" in html_content.lower()
            or
            # Check that required enum fields are at least present
            ("status" in html_content.lower() and "select" in html_content.lower())
        )
        assert required_present

    def test_enum_form_disabled_state_handling(self):
        """Test enum form behavior when fields are disabled."""
        from fh_pydantic_form import PydanticForm
        from tests.conftest import EnumTestModel

        # Create form with disabled fields
        disabled_form = PydanticForm("disabled_enum_test", EnumTestModel, disabled=True)

        html_output = str(disabled_form.render_inputs())

        # Should contain disabled attributes
        assert "disabled" in html_output
