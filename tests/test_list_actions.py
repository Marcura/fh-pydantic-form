import re


def test_add_simple_list_item(list_client, htmx_headers, soup):
    """Test adding a new item to a simple list."""
    # Add a new item to the tags list
    response = list_client.post("/form/test_list/list/add/tags", headers=htmx_headers)

    assert response.status_code == 200
    dom = soup(response.text)

    # Check for a new list item in the response
    li_elem = dom.find("li")
    assert li_elem is not None

    # Check for the new_ pattern in the ID
    li_with_new_id = dom.find("li", {"id": re.compile(r"tags_new_\d+")})
    assert li_with_new_id is not None

    # Should contain an input field
    input_elem = dom.find("input", {"type": "text"})
    assert input_elem is not None

    # Should contain delete button
    delete_btn = dom.find("button", {"class": re.compile(r"uk-button-danger")})
    assert delete_btn is not None
    assert delete_btn.get("hx-delete") is not None


def test_add_model_list_item(complex_client, htmx_headers, soup):
    """Test adding a new item to a model list."""
    # Add a new item to the other_addresses list
    response = complex_client.post(
        "/form/test_complex/list/add/other_addresses", headers=htmx_headers
    )

    assert response.status_code == 200
    dom = soup(response.text)

    # Check for a new list item in the response
    li_elem = dom.find("li")
    assert li_elem is not None

    # Check for the new_ pattern in the ID
    li_with_new_id = dom.find("li", {"id": re.compile(r"other_addresses_new_\d+")})
    assert li_with_new_id is not None

    # Should contain input fields for the model properties
    assert "street" in response.text.lower()
    assert "city" in response.text.lower()
    assert "billing" in response.text.lower()

    # Check for input fields
    input_elems = dom.find_all("input")
    assert len(input_elems) > 0

    # At least one input should have a name attribute
    named_inputs = [inp for inp in input_elems if inp.get("name")]
    assert len(named_inputs) > 0

    # Should contain delete button
    delete_btn = dom.find("button", {"class": re.compile(r"uk-button-danger")})
    assert delete_btn is not None
    assert delete_btn.get("hx-delete") is not None

    # Should be opened by default (uk-open class)
    open_elem = dom.find(class_=re.compile(r"\buk-open\b"))
    assert open_elem is not None


def test_add_custom_model_list_item(complex_client, htmx_headers, soup):
    """Test adding a new item to a custom model list."""
    # Add a new item to the more_custom_details list
    response = complex_client.post(
        "/form/test_complex/list/add/more_custom_details", headers=htmx_headers
    )

    assert response.status_code == 200
    dom = soup(response.text)

    # Check for a new list item in the response
    li_elem = dom.find("li")
    assert li_elem is not None

    # Check for the new_ pattern in the ID
    li_with_new_id = dom.find("li", {"id": re.compile(r"more_custom_details_new_\d+")})
    assert li_with_new_id is not None

    # Should contain input fields for the model properties
    assert "value" in response.text.lower()
    assert "confidence" in response.text.lower()

    # Check for custom field rendering elements if applicable
    # Note: This may vary depending on how CustomDetail is rendered
    select_elem = dom.find("select")
    assert select_elem is not None

    # Check for confidence options
    options = dom.find_all("option")
    option_texts = [opt.get_text() for opt in options]
    assert "HIGH" in option_texts
    assert "MEDIUM" in option_texts
    assert "LOW" in option_texts

    # Should contain delete button
    delete_btn = dom.find("button", {"class": re.compile(r"uk-button-danger")})
    assert delete_btn is not None
    assert delete_btn.get("hx-delete") is not None


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
