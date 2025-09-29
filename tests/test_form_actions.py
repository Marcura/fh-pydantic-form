def test_form_refresh(complex_client, htmx_headers):
    """Test refreshing a form with updated values."""
    # Prepare form data with modified values
    form_data = {
        "test_complex_name": "Updated Name",
        "test_complex_age": "35",
        "test_complex_score": "97.5",
        "test_complex_is_active": "on",
        "test_complex_description": "Updated description",
        "test_complex_creation_date": "2023-02-15",
        "test_complex_start_time": "15:30",
        "test_complex_status": "COMPLETED",
        "test_complex_optional_status": "PENDING",
        # Tags list
        "test_complex_tags_0": "updated",
        "test_complex_tags_1": "values",
        # Main address
        "test_complex_main_address_street": "456 Updated Street",
        "test_complex_main_address_city": "Updated City",
        "test_complex_main_address_is_billing": "on",
        # Custom detail
        "test_complex_custom_detail_value": "Updated value",
        "test_complex_custom_detail_confidence": "MEDIUM",
        # Other addresses list
        "test_complex_other_addresses_0_street": "789 Updated Street",
        "test_complex_other_addresses_0_city": "Updated City",
        "test_complex_other_addresses_0_is_billing": "on",
        # Custom details list
        "test_complex_more_custom_details_0_value": "Updated detail",
        "test_complex_more_custom_details_0_confidence": "LOW",
    }

    # Use the test_complex form directly
    response = complex_client.post(
        "/form/test_complex/refresh", data=form_data, headers=htmx_headers
    )

    assert response.status_code == 200

    # Check that the response contains all our updated values
    assert "Updated Name" in response.text
    assert "35" in response.text
    assert "97.5" in response.text
    assert "Updated description" in response.text
    assert "2023-02-15" in response.text
    assert "15:30" in response.text
    assert "COMPLETED" in response.text
    assert "PENDING" in response.text  # From optional status

    # Check updated list values
    assert "updated" in response.text
    assert "values" in response.text

    # Check updated address
    assert "456 Updated Street" in response.text
    assert "Updated City" in response.text

    # Check custom detail
    assert "Updated value" in response.text
    assert "MEDIUM" in response.text

    # Check list of addresses
    assert "789 Updated Street" in response.text

    # Check list of custom details
    assert "Updated detail" in response.text
    assert "LOW" in response.text


def test_form_reset(complex_client, htmx_headers):
    """Test resetting a form to initial values."""
    # Use the test_complex form directly
    response = complex_client.post("/form/test_complex/reset", headers=htmx_headers)

    assert response.status_code == 200

    # Check that response contains elements
    # Since we don't know the exact initial values, we'll just check
    # that the response contains form elements
    assert 'name="test_complex_name"' in response.text
    assert 'name="test_complex_age"' in response.text
    assert 'name="test_complex_is_active"' in response.text
    assert "PENDING" in response.text
    assert "PROCESSING" in response.text
    assert "COMPLETED" in response.text

    # Check for list containers
    assert "items_container" in response.text

    # Check for typical complex form elements
    assert "street" in response.text.lower()
    assert "city" in response.text.lower()
    assert "confidence" in response.text.lower()


def test_combined_refresh_and_validation(complex_client, htmx_headers):
    """Test the workflow of refreshing a form then validating it."""
    # Step 1: Get the initial form
    initial_response = complex_client.get("/")
    assert initial_response.status_code == 200

    # Step 2: Modify and refresh the form
    form_data = {
        "test_complex_name": "Workflow Test",
        "test_complex_age": "40",
        "test_complex_score": "99.5",
        "test_complex_is_active": "on",
        "test_complex_description": "Testing workflow",
        "test_complex_creation_date": "2023-03-15",
        "test_complex_start_time": "16:30",
        "test_complex_status": "PROCESSING",
        # Other fields with default values
    }

    refresh_response = complex_client.post(
        "/form/test_complex/refresh", data=form_data, headers=htmx_headers
    )

    assert refresh_response.status_code == 200
    assert "Workflow Test" in refresh_response.text
    assert "40" in refresh_response.text

    # Step 3: Submit the refreshed form for validation with complete form data
    complete_form_data = {
        # Updated fields from step 2
        "test_complex_name": "Workflow Test",
        "test_complex_age": "40",
        "test_complex_score": "99.5",
        "test_complex_is_active": "on",
        "test_complex_description": "Testing workflow",
        "test_complex_creation_date": "2023-03-15",
        "test_complex_start_time": "16:30",
        "test_complex_status": "PROCESSING",
        "test_complex_optional_status": "",  # Empty string for None
        # Add fields for lists and nested models (using representative values)
        "test_complex_tags_0": "test1",
        "test_complex_tags_1": "test2",
        # Main address
        "test_complex_main_address_street": "123 Test St",
        "test_complex_main_address_city": "Testville",
        "test_complex_main_address_is_billing": "on",
        # Custom detail
        "test_complex_custom_detail_value": "Test Detail",
        "test_complex_custom_detail_confidence": "HIGH",
        # Other addresses (at least one entry)
        "test_complex_other_addresses_0_street": "456 Other St",
        "test_complex_other_addresses_0_city": "Otherville",
        # Custom details (at least one entry)
        "test_complex_more_custom_details_0_value": "Test Detail 1",
        "test_complex_more_custom_details_0_confidence": "MEDIUM",
    }

    validation_response = complex_client.post(
        "/submit_form", data=complete_form_data, headers=htmx_headers
    )

    assert validation_response.status_code == 200
    assert "Validation Successful" in validation_response.text
    # Handle both encoded and unencoded quotes
    assert (
        '"name": "Workflow Test"' in validation_response.text
        or "&quot;name&quot;: &quot;Workflow Test&quot;" in validation_response.text
    )
    assert (
        '"age": 40' in validation_response.text
        or "&quot;age&quot;: 40" in validation_response.text
    )
    assert (
        '"score": 99.5' in validation_response.text
        or "&quot;score&quot;: 99.5" in validation_response.text
    )


def test_error_handling_in_refresh(complex_client, htmx_headers):
    """Test error handling when refreshing a form with invalid data."""
    # Send invalid data for refresh (non-numeric value for age)
    invalid_form_data = {
        "test_complex_name": "Error Test",
        "test_complex_age": "not-a-number",  # Invalid age
        "test_complex_score": "99.5",
        # Other fields with default values
    }

    response = complex_client.post(
        "/form/test_complex/refresh", data=invalid_form_data, headers=htmx_headers
    )

    # Refresh should still work even with invalid data
    # It should either show a warning or fall back to default values
    assert response.status_code == 200

    # The form should still contain our valid inputs
    assert "Error Test" in response.text

    # Either our invalid input is preserved or a warning is shown
    # Depending on implementation, this could vary
    assert "not-a-number" in response.text or "Warning" in response.text
