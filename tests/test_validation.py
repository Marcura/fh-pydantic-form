import pytest
import re


def test_submit_valid_simple_form(validation_client, htmx_headers):
    """Test submitting a valid simple form."""
    valid_data = {
        "test_validation_name": "Test Name",
        "test_validation_age": "30",
        "test_validation_score": "95.5",
    }
    
    response = validation_client.post("/submit_form", data=valid_data, headers=htmx_headers)
    
    assert response.status_code == 200
    assert "Validation Successful" in response.text
    
    # Check for the expected JSON output in the response
    assert '&quot;name&quot;: &quot;Test Name&quot;' in response.text
    assert '&quot;age&quot;: 30' in response.text
    assert '&quot;score&quot;: 95.5' in response.text


def test_submit_invalid_simple_form(validation_client, htmx_headers):
    """Test submitting an invalid simple form."""
    invalid_data = {
        "test_validation_name": "Test Name",
        "test_validation_age": "not-a-number",  # Invalid age
        "test_validation_score": "95.5",
    }
    
    response = validation_client.post("/submit_form", data=invalid_data, headers=htmx_headers)
    
    assert response.status_code == 200
    assert "Validation Error" in response.text
    assert "Input should be a valid integer" in response.text


def test_submit_valid_list_form(list_client, htmx_headers):
    """Test submitting a valid list form."""
    valid_data = {
        "test_list_name": "Test List",
        "test_list_tags_0": "tag1",
        "test_list_tags_1": "tag2",
        "test_list_tags_2": "tag3",
    }
    
    response = list_client.post("/submit_form", data=valid_data, headers=htmx_headers)
    
    assert response.status_code == 200
    assert "Validation Successful" in response.text
    
    # Check for expected JSON output in the response
    assert '&quot;name&quot;: &quot;Test List&quot;' in response.text
    assert '&quot;tags&quot;: [' in response.text
    assert '&quot;tag1&quot;' in response.text
    assert '&quot;tag2&quot;' in response.text
    assert '&quot;tag3&quot;' in response.text


def test_submit_valid_complex_form(complex_client, htmx_headers):
    """Test submitting a valid complex form."""
    valid_data = {
        "test_complex_name": "Complex User",
        "test_complex_age": "42",
        "test_complex_score": "98.7",
        "test_complex_is_active": "on",
        "test_complex_description": "Test description",
        "test_complex_creation_date": "2023-05-15",
        "test_complex_start_time": "14:30",
        "test_complex_status": "PROCESSING",
        "test_complex_optional_status": "",  # Empty for None
        
        # Tags list
        "test_complex_tags_0": "complex",
        "test_complex_tags_1": "test",
        "test_complex_tags_2": "valid",
        
        # Main address
        "test_complex_main_address_street": "123 Test Street",
        "test_complex_main_address_city": "Test City",
        "test_complex_main_address_is_billing": "on",
        
        # Custom detail
        "test_complex_custom_detail_value": "Custom value",
        "test_complex_custom_detail_confidence": "HIGH",
        
        # Other addresses list
        "test_complex_other_addresses_0_street": "456 Other Street",
        "test_complex_other_addresses_0_city": "Other City",
        # No is_billing, should default to false
        
        "test_complex_other_addresses_1_street": "789 Second Street",
        "test_complex_other_addresses_1_city": "Second City",
        "test_complex_other_addresses_1_is_billing": "on",
        
        # Custom details list
        "test_complex_more_custom_details_0_value": "First detail",
        "test_complex_more_custom_details_0_confidence": "MEDIUM",
        
        "test_complex_more_custom_details_1_value": "Second detail",
        "test_complex_more_custom_details_1_confidence": "LOW",
    }
    
    response = complex_client.post("/submit_form", data=valid_data, headers=htmx_headers)
    
    assert response.status_code == 200
    assert "Validation Successful" in response.text
    
    # Check for expected JSON patterns in the response
    assert '&quot;name&quot;: &quot;Complex User&quot;' in response.text
    assert '&quot;age&quot;: 42' in response.text
    assert '&quot;score&quot;: 98.7' in response.text
    assert '&quot;is_active&quot;: true' in response.text
    assert '&quot;description&quot;: &quot;Test description&quot;' in response.text
    assert '&quot;creation_date&quot;: &quot;2023-05-15&quot;' in response.text
    assert '&quot;start_time&quot;: &quot;14:30:00&quot;' in response.text
    assert '&quot;status&quot;: &quot;PROCESSING&quot;' in response.text
    assert '&quot;optional_status&quot;: null' in response.text
    
    # Check for list content
    assert '&quot;tags&quot;: [' in response.text
    assert '&quot;complex&quot;' in response.text
    assert '&quot;test&quot;' in response.text
    assert '&quot;valid&quot;' in response.text
    
    # Check for nested model content
    assert '&quot;main_address&quot;: {' in response.text
    assert '&quot;street&quot;: &quot;123 Test Street&quot;' in response.text
    assert '&quot;is_billing&quot;: true' in response.text
    
    # Check for list of nested models
    assert '&quot;other_addresses&quot;: [' in response.text
    assert '&quot;street&quot;: &quot;456 Other Street&quot;' in response.text
    assert '&quot;is_billing&quot;: false' in response.text  # Default for missing
    assert '&quot;street&quot;: &quot;789 Second Street&quot;' in response.text
    assert '&quot;is_billing&quot;: true' in response.text
    
    # Check for custom model content
    assert '&quot;custom_detail&quot;: {' in response.text
    assert '&quot;value&quot;: &quot;Custom value&quot;' in response.text
    assert '&quot;confidence&quot;: &quot;HIGH&quot;' in response.text
    
    # Check for list of custom models
    assert '&quot;more_custom_details&quot;: [' in response.text
    assert '&quot;value&quot;: &quot;First detail&quot;' in response.text
    assert '&quot;confidence&quot;: &quot;MEDIUM&quot;' in response.text
    assert '&quot;value&quot;: &quot;Second detail&quot;' in response.text
    assert '&quot;confidence&quot;: &quot;LOW&quot;' in response.text


def test_submit_invalid_complex_form(complex_client, htmx_headers):
    """Test submitting an invalid complex form."""
    invalid_data = {
        "test_complex_name": "Complex User",
        "test_complex_age": "not-a-number",  # Invalid age
        "test_complex_score": "not-a-float",  # Invalid score
        "test_complex_is_active": "on",
        "test_complex_status": "INVALID-STATUS",  # Invalid literal value
        
        # Valid data for other fields
        "test_complex_description": "Test description",
        "test_complex_creation_date": "2023-05-15",
        "test_complex_start_time": "14:30",
    }
    
    response = complex_client.post("/submit_form", data=invalid_data, headers=htmx_headers)
    
    assert response.status_code == 200
    assert "Validation Error" in response.text
    
    # Check for specific validation error messages
    assert "Input should be a valid integer" in response.text
    assert "Input should be a valid number" in response.text
    
    # Updated assertion for Literal error - checking for presence of allowed values instead of exact message
    assert "PENDING" in response.text
    assert "PROCESSING" in response.text
    assert "COMPLETED" in response.text