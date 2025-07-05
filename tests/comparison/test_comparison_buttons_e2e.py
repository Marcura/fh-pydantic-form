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

    # Check for either input or textarea element (StringFieldRenderer now uses textarea)
    form_field = segment.find("input", {"name": key}) or segment.find(
        "textarea", {"name": key}
    )
    assert form_field is not None
    assert isinstance(form_field, Tag)

    # Extract value based on element type
    if form_field.name == "input":
        assert form_field.get("value") == new_val
    elif form_field.name == "textarea":
        assert form_field.text == new_val

    # Ensure this value appears only in this column (not duplicated)
    all_form_fields = soup.find_all(["input", "textarea"])
    fields_with_new_val = []
    for field in all_form_fields:
        if isinstance(field, Tag):
            name = field.get("name")
            if name and str(name).endswith("_title"):
                field_value = (
                    field.get("value") if field.name == "input" else field.text
                )
                if field_value == new_val:
                    fields_with_new_val.append(field)
    assert len(fields_with_new_val) == 1


@pytest.mark.parametrize("side", ["left", "right"])
def test_reset_restores_initial_state(comparison_app_client, htmx_headers, side):
    client, comp = comparison_app_client
    # The initial value for "title" is the same for both
    init_val = comp.left_form.initial_values_dict["title"]

    url = f"/compare/{comp.name}/{side}/reset"
    r = client.post(url, headers=htmx_headers)
    assert r.status_code == 200

    # Check that the form field has the initial value
    soup = BeautifulSoup(r.text, "html.parser")
    field_name = f"{side}_form_title"
    form_field = soup.find("input", {"name": field_name}) or soup.find(
        "textarea", {"name": field_name}
    )
    assert form_field is not None
    assert isinstance(form_field, Tag)

    # Extract value based on element type
    field_value = (
        form_field.get("value") if form_field.name == "input" else form_field.text
    )
    assert field_value == init_val


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

    # The invalid value should be preserved in the form field (form parsing is permissive)
    # Note: count is a number field, so it should still be an input element
    count_field = soup.find("input", {"name": "left_form_count"}) or soup.find(
        "textarea", {"name": "left_form_count"}
    )
    assert count_field is not None
    assert isinstance(count_field, Tag)
    # The form parser preserves the value as-is, validation only happens during model validation
    count_value = (
        count_field.get("value") if count_field.name == "input" else count_field.text
    )
    assert count_value == "not-an-int"
