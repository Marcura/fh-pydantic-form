import fasthtml.common as fh
import monsterui.all as mui
import pytest
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

from fh_pydantic_form import PydanticForm, comparison_form_js, list_manipulation_js
from fh_pydantic_form.comparison_form import ComparisonForm

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


# --- template_name E2E tests ---


class RouteTemplateModel(BaseModel):
    """Model for template_name testing."""

    name: str = "Default"
    items: list[str] = Field(default_factory=list)


@pytest.fixture(scope="module")
def template_routing_client():
    """
    Test client where a TEMPLATE ComparisonForm registers routes,
    and DYNAMIC ComparisonForm instances (with different names) use them.
    """
    # Template forms - these register the routes
    template_left = PydanticForm(
        "template_left",
        RouteTemplateModel,
        initial_values={"name": "Template Left", "items": ["a"]},
    )
    template_right = PydanticForm(
        "template_right",
        RouteTemplateModel,
        initial_values={"name": "Template Right", "items": ["b"]},
    )
    template_comp = ComparisonForm(
        name="template_comp",
        left_form=template_left,
        right_form=template_right,
        template_name="shared_routes",  # Routes registered under this name
    )

    # Dynamic forms - these reuse the template's routes
    dynamic_left = PydanticForm(
        "dynamic_left_row1",
        RouteTemplateModel,
        initial_values={"name": "Dynamic Left", "items": ["x", "y"]},
        template_name="template_left",  # Reuse PydanticForm routes
    )
    dynamic_right = PydanticForm(
        "dynamic_right_row1",
        RouteTemplateModel,
        initial_values={"name": "Dynamic Right", "items": ["z"]},
        template_name="template_right",
    )
    dynamic_comp = ComparisonForm(
        name="dynamic_row1",  # Different instance name
        left_form=dynamic_left,
        right_form=dynamic_right,
        template_name="shared_routes",  # Same template routes
    )

    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js(), comparison_form_js()],
        pico=False,
        live=False,
    )

    # Only register routes ONCE via template
    template_comp.register_routes(app)

    @rt("/")
    def _root():
        # Render the DYNAMIC form (not the template)
        return fh.Div(
            dynamic_comp.form_wrapper(dynamic_comp.render_inputs()),
            id="dynamic-form-container",
        )

    return TestClient(app), dynamic_comp, template_comp


@pytest.mark.parametrize("side", ["left", "right"])
def test_template_name_refresh_works(template_routing_client, htmx_headers, side):
    """
    Verify that shared routes respond correctly.

    When routes are shared via template_name, the route handlers use the
    TEMPLATE's forms (captured in the closure when register_routes was called).
    Dynamic forms just generate URLs pointing to these shared routes.
    """
    client, dynamic_comp, template_comp = template_routing_client

    # The dynamic form has a different name than the route
    assert dynamic_comp.name == "dynamic_row1"
    assert dynamic_comp.template_name == "shared_routes"

    # The template form is what the route handler uses
    template_form = (
        template_comp.left_form if side == "left" else template_comp.right_form
    )

    # Build payload with TEMPLATE form's prefix (since route handler uses template)
    payload = {f"{template_form.base_prefix}name": "Updated Value"}

    # Hit the shared route
    url = f"/compare/{template_comp.template_name}/{side}/refresh"
    r = client.post(url, data=payload, headers=htmx_headers)

    assert r.status_code == 200

    soup = BeautifulSoup(r.text, "html.parser")
    # Response uses TEMPLATE form's wrapper ID (route handler captured template forms)
    wrapper = soup.find(id=f"{template_form.name}-inputs-wrapper")
    assert wrapper is not None, (
        f"Expected wrapper {template_form.name}-inputs-wrapper not found"
    )

    # Check that the updated value appears
    name_field = soup.find("textarea", {"name": f"{template_form.base_prefix}name"})
    assert name_field is not None
    assert name_field.text == "Updated Value"


def test_template_name_wrong_route_fails(template_routing_client, htmx_headers):
    """
    Verify that hitting a non-existent route (using the dynamic form's name) fails.

    The route /compare/dynamic_row1/left/refresh should NOT exist - only
    /compare/shared_routes/left/refresh was registered.
    """
    client, dynamic_comp, _ = template_routing_client

    # Try to hit a route using the dynamic form's NAME (not template_name)
    url = f"/compare/{dynamic_comp.name}/left/refresh"
    r = client.post(url, headers=htmx_headers)

    # Should fail because this route was never registered
    assert r.status_code == 404


@pytest.mark.parametrize("side", ["left", "right"])
def test_fhpf_form_name_allows_dynamic_prefix_parsing(
    template_routing_client, htmx_headers, side
):
    """
    Verify that fhpf_form_name allows dynamic forms to use shared routes with their own prefix.

    When a dynamic form sends fhpf_form_name with its actual name, the handler should:
    1. Clone the template form with the dynamic name
    2. Parse form data using the dynamic form's prefix
    3. Return a response with the dynamic form's wrapper ID
    """
    client, dynamic_comp, template_comp = template_routing_client

    # Get the dynamic form for this side
    dynamic_form = dynamic_comp.left_form if side == "left" else dynamic_comp.right_form

    # Build payload using the DYNAMIC form's prefix (not template's)
    # This simulates what the actual UI would send
    field_name = f"{dynamic_form.base_prefix}name"
    new_val = f"Dynamic-{side}-Value"
    payload = {
        field_name: new_val,
        "fhpf_form_name": dynamic_form.name,  # Tell handler which form name/prefix to use
    }

    # Hit the shared route
    url = f"/compare/{template_comp.template_name}/{side}/refresh"
    r = client.post(url, data=payload, headers=htmx_headers)

    assert r.status_code == 200

    soup = BeautifulSoup(r.text, "html.parser")

    # Response should use DYNAMIC form's wrapper ID (because we sent fhpf_form_name)
    wrapper = soup.find(id=f"{dynamic_form.name}-inputs-wrapper")
    assert wrapper is not None, (
        f"Expected wrapper {dynamic_form.name}-inputs-wrapper not found. "
        f"Response: {r.text[:500]}"
    )

    # Check that the form field has the dynamic prefix and the updated value
    name_field = soup.find("textarea", {"name": f"{dynamic_form.base_prefix}name"})
    assert name_field is not None, (
        f"Expected field {dynamic_form.base_prefix}name not found"
    )
    assert name_field.text == new_val
