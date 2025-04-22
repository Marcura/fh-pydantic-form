import re


def test_add_simple_list_item(list_client, htmx_headers):
    """Test adding a new item to a simple list."""
    # Add a new item to the tags list
    response = list_client.post("/form/test_list/list/add/tags", headers=htmx_headers)

    assert response.status_code == 200

    # Check for a new list item in the response
    assert "<li " in response.text

    # Check for the new_ pattern in the ID
    new_pattern = r"test_list_tags_new_\d+"
    assert re.search(new_pattern, response.text) is not None

    # Should contain an input field
    assert "<input " in response.text
    assert 'type="text"' in response.text

    # Should contain delete button
    assert "hx-delete=" in response.text
    assert "uk-button-danger" in response.text


def test_add_model_list_item(complex_client, htmx_headers):
    """Test adding a new item to a model list."""
    # Add a new item to the other_addresses list
    response = complex_client.post(
        "/form/test_complex/list/add/other_addresses", headers=htmx_headers
    )

    assert response.status_code == 200

    # Check for a new list item in the response
    assert "<li " in response.text

    # Check for the new_ pattern in the ID
    new_pattern = r"test_complex_other_addresses_new_\d+"
    assert re.search(new_pattern, response.text) is not None

    # Should contain input fields for the model properties
    assert "street" in response.text
    assert "city" in response.text
    assert "is_billing" in response.text

    # Check for input fields
    assert "<input " in response.text
    assert "name=" in response.text

    # Should contain delete button
    assert "hx-delete=" in response.text
    assert "uk-button-danger" in response.text

    # Should be opened by default (uk-open class)
    assert "uk-open" in response.text


def test_add_custom_model_list_item(complex_client, htmx_headers):
    """Test adding a new item to a custom model list."""
    # Add a new item to the more_custom_details list
    response = complex_client.post(
        "/form/test_complex/list/add/more_custom_details", headers=htmx_headers
    )

    assert response.status_code == 200

    # Check for a new list item in the response
    assert "<li " in response.text

    # Check for the new_ pattern in the ID
    new_pattern = r"test_complex_more_custom_details_new_\d+"
    assert re.search(new_pattern, response.text) is not None

    # Should contain input fields for the model properties
    assert "value" in response.text.lower()
    assert "confidence" in response.text.lower()

    # Check for custom field rendering elements if applicable
    # Note: This may vary depending on how CustomDetail is rendered
    assert "<select " in response.text
    assert ">HIGH<" in response.text
    assert ">MEDIUM<" in response.text
    assert ">LOW<" in response.text

    # Should contain delete button
    assert "hx-delete=" in response.text
    assert "uk-button-danger" in response.text


def test_delete_list_item(list_client, htmx_headers):
    """Test deleting an item from a list."""
    # Delete an item from the tags list
    # Note: The actual item index doesn't matter for this test
    # since we're just checking that the endpoint returns an empty response
    response = list_client.delete(
        "/form/test_list/list/delete/tags?idx=0", headers=htmx_headers
    )

    assert response.status_code == 200
    assert response.text == ""  # Empty response for deletion


def test_delete_model_list_item(complex_client, htmx_headers):
    """Test deleting an item from a model list."""
    # Delete an item from the other_addresses list
    response = complex_client.delete(
        "/form/test_complex/list/delete/other_addresses?idx=0", headers=htmx_headers
    )

    assert response.status_code == 200
    assert response.text == ""  # Empty response for deletion
