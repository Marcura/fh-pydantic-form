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