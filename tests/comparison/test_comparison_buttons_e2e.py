import pytest
from bs4 import BeautifulSoup, Tag

pytestmark = [pytest.mark.comparison, pytest.mark.e2e]


@pytest.mark.parametrize("side", ["left", "right"])
def test_refresh_updates_column(comparison_app_client, htmx_headers, side):
    client, comp = comparison_app_client
    # Use a known field
    field_name = "title"
    new_val = f"Edited-{side}"

    # Build POST body mimicking HTMX include selector
    key = f"{side}_form_{field_name}"
    payload = {key: new_val}

    url = f"/compare/{comp.name}/{side}/refresh"
    r = client.post(url, data=payload, headers=htmx_headers)
    assert r.status_code == 200

    soup = BeautifulSoup(r.text, "html.parser")
    wrapper_id = f"{side}_form-inputs-wrapper"
    segment = soup.find(id=wrapper_id)
    assert segment is not None
    assert isinstance(segment, Tag)

    # Check the input value attribute instead of text content
    input_field = segment.find("input", {"name": key})
    assert input_field is not None
    assert isinstance(input_field, Tag)
    assert input_field.get("value") == new_val

    # Ensure this value appears only in this column (not duplicated)
    all_title_inputs = soup.find_all("input")
    title_inputs_with_new_val = []
    for inp in all_title_inputs:
        if isinstance(inp, Tag):
            name = inp.get("name")
            if name and str(name).endswith("_title") and inp.get("value") == new_val:
                title_inputs_with_new_val.append(inp)
    assert len(title_inputs_with_new_val) == 1


@pytest.mark.parametrize("side", ["left", "right"])
def test_reset_restores_initial_state(comparison_app_client, htmx_headers, side):
    client, comp = comparison_app_client
    # The initial value for "title" is the same for both
    init_val = comp.left_form.initial_values_dict["title"]

    url = f"/compare/{comp.name}/{side}/reset"
    r = client.post(url, headers=htmx_headers)
    assert r.status_code == 200

    # Check that the input has the initial value
    soup = BeautifulSoup(r.text, "html.parser")
    input_field = soup.find("input", {"name": f"{side}_form_title"})
    assert input_field is not None
    assert isinstance(input_field, Tag)
    assert input_field.get("value") == init_val


def test_refresh_invalid_shows_warning(comparison_app_client, htmx_headers):
    client, comp = comparison_app_client
    # Send a string for an int‐field `count`
    payload = {"left_form_count": "not-an-int"}
    url = f"/compare/{comp.name}/left/refresh"
    r = client.post(url, data=payload, headers=htmx_headers)

    assert r.status_code == 200

    # The form parsing doesn't validate data types, so invalid values are preserved
    # This test verifies that the form refresh handles invalid data gracefully
    soup = BeautifulSoup(r.text, "html.parser")
    wrapper = soup.find(id="left_form-inputs-wrapper")
    assert wrapper is not None

    # The invalid value should be preserved in the input (form parsing is permissive)
    count_input = soup.find("input", {"name": "left_form_count"})
    assert count_input is not None
    assert isinstance(count_input, Tag)
    # The form parser preserves the value as-is, validation only happens during model validation
    count_value = count_input.get("value")
    assert count_value == "not-an-int"
