import pytest
import re


def test_render_simple_form(simple_client):
    """Test rendering the simple form."""
    response = simple_client.get("/")
    
    assert response.status_code == 200
    assert 'content-type' in response.headers
    assert response.headers['content-type'].startswith('text/html')
    
    # Check for field inputs
    assert 'name="test_simple_name"' in response.text
    assert 'name="test_simple_age"' in response.text
    assert 'name="test_simple_score"' in response.text
    
    # Check for labels
    assert '<label for="test_simple_name"' in response.text
    assert '<label for="test_simple_age"' in response.text
    assert '<label for="test_simple_score"' in response.text


def test_render_validation_form(validation_client):
    """Test rendering the validation form."""
    response = validation_client.get("/")
    
    assert response.status_code == 200
    
    # Check for field inputs
    assert 'name="test_validation_name"' in response.text
    assert 'name="test_validation_age"' in response.text
    assert 'name="test_validation_score"' in response.text
    
    # Check for form submission elements
    assert 'hx-post="/submit_form"' in response.text
    assert 'hx-target="#result"' in response.text


def test_render_list_form(list_client):
    """Test rendering the list form."""
    response = list_client.get("/")
    
    assert response.status_code == 200
    
    # Check for basic field
    assert 'name="test_list_name"' in response.text
    
    # Check for list container and default items
    assert 'id="test_list_tags_items_container"' in response.text
    
    # Check for default list items (may vary based on how the form renders)
    assert 'test_list_tags_0' in response.text
    assert 'test_list_tags_1' in response.text
    
    # Check for form submission elements
    assert 'hx-post="/submit_form"' in response.text


def test_render_complex_form(complex_client):
    """Test rendering the complex form."""
    response = complex_client.get("/")
    
    assert response.status_code == 200
    
    # Check for basic fields
    assert 'name="test_complex_name"' in response.text
    assert 'name="test_complex_age"' in response.text
    assert 'name="test_complex_score"' in response.text
    assert 'name="test_complex_is_active"' in response.text
    
    # Check for date/time fields
    assert 'name="test_complex_creation_date"' in response.text
    assert 'type="date"' in response.text
    assert 'name="test_complex_start_time"' in response.text
    assert 'type="time"' in response.text
    
    # Check for literal/select fields
    assert 'name="test_complex_status"' in response.text
    assert '>PENDING<' in response.text
    assert '>PROCESSING<' in response.text
    assert '>COMPLETED<' in response.text
    
    # Check for optional fields
    assert 'name="test_complex_description"' in response.text
    assert 'name="test_complex_optional_status"' in response.text
    
    # Check for list fields
    assert 'id="test_complex_tags_items_container"' in response.text
    assert 'test_complex_tags_0' in response.text
    
    # Check for nested model fields
    assert 'name="test_complex_main_address_street"' in response.text
    assert 'name="test_complex_main_address_city"' in response.text
    assert 'name="test_complex_main_address_is_billing"' in response.text
    
    # Check for list of nested models
    assert 'id="test_complex_other_addresses_items_container"' in response.text
    assert 'test_complex_other_addresses_0_street' in response.text
    
    # Check for custom nested model
    assert 'name="test_complex_custom_detail_value"' in response.text
    assert 'name="test_complex_custom_detail_confidence"' in response.text
    
    # Check for list of custom nested models
    assert 'id="test_complex_more_custom_details_items_container"' in response.text
    assert 'test_complex_more_custom_details_0' in response.text
    
    # Check for buttons
    assert 'Validate' in response.text
    assert 'hx-post="/submit_form"' in response.text


def test_form_contains_refresh_button(complex_client):
    """Test that the complex form contains the refresh button."""
    response = complex_client.get("/")
    
    assert response.status_code == 200
    
    # Look for refresh button pattern
    # Note: The exact HTML structure may vary, adjust as needed
    refresh_btn_pattern = r'hx-post="/form/test_complex/refresh"'
    assert re.search(refresh_btn_pattern, response.text) is not None


def test_form_contains_reset_button(complex_client):
    """Test that the complex form contains the reset button."""
    response = complex_client.get("/")
    
    assert response.status_code == 200
    
    # Look for reset button pattern
    reset_btn_pattern = r'hx-post="/form/test_complex/reset"'
    assert re.search(reset_btn_pattern, response.text) is not None


def test_render_globally_disabled_simple_form(globally_disabled_simple_client):
    """Test rendering a simple form with all fields disabled."""
    response = globally_disabled_simple_client.get("/")
    
    assert response.status_code == 200
    assert 'content-type' in response.headers
    assert response.headers['content-type'].startswith('text/html')
    
    # Check that all fields are disabled
    assert 'name="test_simple_globally_disabled_name"' in response.text
    assert 'name="test_simple_globally_disabled_age"' in response.text
    assert 'name="test_simple_globally_disabled_score"' in response.text
    
    # Check for disabled attribute in all input fields
    assert 'disabled' in response.text
    # More specific checks for each field
    assert re.search(r'name="test_simple_globally_disabled_name"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_simple_globally_disabled_age"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_simple_globally_disabled_score"[^>]*disabled', response.text) is not None


def test_render_partially_disabled_simple_form(partially_disabled_simple_client):
    """Test rendering a simple form with only specific fields disabled."""
    response = partially_disabled_simple_client.get("/")
    
    assert response.status_code == 200
    
    # Check for all fields present
    assert 'name="test_simple_partially_disabled_name"' in response.text
    assert 'name="test_simple_partially_disabled_age"' in response.text
    assert 'name="test_simple_partially_disabled_score"' in response.text
    
    # Check that only the age field has the disabled attribute
    assert re.search(r'name="test_simple_partially_disabled_age"[^>]*disabled', response.text) is not None
    
    # Check that the name and score fields do NOT have the disabled attribute
    # Get the full input tags for these fields
    name_input_match = re.search(r'<input[^>]*name="test_simple_partially_disabled_name"[^>]*>', response.text)
    score_input_match = re.search(r'<input[^>]*name="test_simple_partially_disabled_score"[^>]*>', response.text)
    
    assert name_input_match is not None
    assert score_input_match is not None
    
    # Verify disabled attribute is not in these tags
    assert ' disabled' not in name_input_match.group(0)
    assert ' disabled' not in score_input_match.group(0)


def test_render_globally_disabled_complex_form(globally_disabled_complex_client):
    """Test rendering a complex form with all fields disabled."""
    response = globally_disabled_complex_client.get("/")
    
    assert response.status_code == 200
    
    # Check that the response contains a sampling of input fields
    assert 'name="test_complex_globally_disabled_name"' in response.text
    assert 'name="test_complex_globally_disabled_age"' in response.text
    assert 'name="test_complex_globally_disabled_is_active"' in response.text
    assert 'name="test_complex_globally_disabled_creation_date"' in response.text
    assert 'name="test_complex_globally_disabled_start_time"' in response.text
    assert 'name="test_complex_globally_disabled_status"' in response.text
    
    # Check for disabled attribute in sample fields across different types
    assert re.search(r'name="test_complex_globally_disabled_name"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_globally_disabled_age"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_globally_disabled_is_active"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_globally_disabled_creation_date"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_globally_disabled_start_time"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_globally_disabled_status"[^>]*disabled', response.text) is not None
    
    # Check for disabled attribute in nested model fields
    assert re.search(r'name="test_complex_globally_disabled_main_address_street"[^>]*disabled', response.text) is not None
    
    # Check for disabled attribute in list buttons
    if 'test_complex_globally_disabled_tags_0' in response.text:
        # If list item exists, check that it's disabled
        assert re.search(r'name="test_complex_globally_disabled_tags_0"[^>]*disabled', response.text) is not None
    
    # Check that action buttons in lists are disabled
    # (These could be delete, add, move up/down buttons)
    assert re.search(r'<button[^>]*?(?=.*\buk-button-danger\b)(?=.*disabled)[^>]*>', response.text) is not None  # Delete button
    assert re.search(r'<button[^>]*?(?=.*\buk-button-secondary\b)(?=.*disabled)[^>]*>', response.text) is not None  # Add button
    assert re.search(r'<button[^>]*?(?=.*\bmove-up-btn\b)(?=.*disabled)[^>]*>', response.text) is not None  # Move up button
    assert re.search(r'<button[^>]*?(?=.*\bmove-down-btn\b)(?=.*disabled)[^>]*>', response.text) is not None  # Move down button


def test_render_partially_disabled_complex_form(partially_disabled_complex_client):
    """Test rendering a complex form with only specific fields disabled."""
    response = partially_disabled_complex_client.get("/")
    
    assert response.status_code == 200
    
    # Check for all expected fields
    assert 'name="test_complex_partially_disabled_name"' in response.text
    assert 'name="test_complex_partially_disabled_age"' in response.text
    assert 'name="test_complex_partially_disabled_is_active"' in response.text
    assert 'name="test_complex_partially_disabled_main_address_street"' in response.text
    
    # Check that specified disabled fields have the disabled attribute
    # 1. The name field should be disabled
    assert re.search(r'name="test_complex_partially_disabled_name"[^>]*disabled', response.text) is not None
    
    # 2. All main_address fields should be disabled
    assert re.search(r'name="test_complex_partially_disabled_main_address_street"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_partially_disabled_main_address_city"[^>]*disabled', response.text) is not None
    assert re.search(r'name="test_complex_partially_disabled_main_address_is_billing"[^>]*disabled', response.text) is not None
    
    # 3. All tags fields should be disabled
    if 'test_complex_partially_disabled_tags_0' in response.text:
        assert re.search(r'name="test_complex_partially_disabled_tags_0"[^>]*disabled', response.text) is not None
    
    # 4. Check that the non-disabled fields do NOT have the disabled attribute
    # Get the full input tags for age and is_active
    age_input_match = re.search(r'<input[^>]*name="test_complex_partially_disabled_age"[^>]*>', response.text)
    is_active_input_match = re.search(r'<input[^>]*name="test_complex_partially_disabled_is_active"[^>]*>', response.text)
    
    assert age_input_match is not None
    assert is_active_input_match is not None
    
    # Verify disabled attribute is not in these tags
    assert ' disabled' not in age_input_match.group(0)
    assert ' disabled' not in is_active_input_match.group(0)
    
    # 5. Check that other_addresses fields are NOT disabled
    other_address_match = re.search(r'<input[^>]*name="test_complex_partially_disabled_other_addresses_0_street"[^>]*>', response.text)
    if other_address_match:
        assert ' disabled' not in other_address_match.group(0)
    
    # 6. Check that custom_detail fields are NOT disabled
    custom_detail_match = re.search(r'<input[^>]*name="test_complex_partially_disabled_custom_detail_value"[^>]*>', response.text)
    if custom_detail_match:
        assert ' disabled' not in custom_detail_match.group(0)