"""Unit tests for ComparisonForm route registration."""

import pytest
from pydantic import BaseModel

from fh_pydantic_form import PydanticForm
from fh_pydantic_form.comparison_form import ComparisonForm

pytestmark = pytest.mark.comparison


class SimpleModel(BaseModel):
    """Simple model for route testing."""

    name: str = "Test"
    value: int = 42


@pytest.fixture
def comparison():
    """Create a comparison form for testing."""
    left = PydanticForm("left_form", SimpleModel)
    right = PydanticForm("right_form", SimpleModel)
    return ComparisonForm("test_comp", left, right)


@pytest.fixture
def mock_app(mocker):
    """Mock FastHTML app with route tracking."""
    app = mocker.Mock()
    registered_routes = []

    def track_route(path, methods=None):
        def decorator(func):
            registered_routes.append(
                {"path": path, "methods": methods, "handler": func}
            )
            return func

        return decorator

    app.route = mocker.Mock(side_effect=track_route)
    app.registered_routes = registered_routes
    return app


@pytest.mark.unit
def test_register_routes_creates_all_endpoints(comparison, mock_app):
    """Test that register_routes creates all expected endpoints."""
    comparison.register_routes(mock_app)

    # Extract just the paths
    paths = [r["path"] for r in mock_app.registered_routes]

    # Should register comparison-specific routes
    assert "/compare/test_comp/left/reset" in paths
    assert "/compare/test_comp/left/refresh" in paths
    assert "/compare/test_comp/right/reset" in paths
    assert "/compare/test_comp/right/refresh" in paths

    # Should also register underlying form routes (list manipulation)
    # These come from left_form.register_routes() and right_form.register_routes()
    assert any("/form/left_form/" in p for p in paths)
    assert any("/form/right_form/" in p for p in paths)


@pytest.mark.unit
def test_register_routes_methods(comparison, mock_app):
    """Test that routes are registered with POST method."""
    comparison.register_routes(mock_app)

    # Find comparison routes
    comp_routes = [
        r for r in mock_app.registered_routes if r["path"].startswith("/compare/")
    ]

    # All should be POST
    for route in comp_routes:
        assert route["methods"] == ["POST"]


@pytest.fixture
def mock_request(mocker):
    """Create a mock request with async form() method."""
    req = mocker.Mock()
    # Mock form() to return an async result (empty dict, no fhpf_form_name)
    req.form = mocker.AsyncMock(return_value={})
    req.query_params = {}
    return req


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_handler_functionality(comparison, mock_app, mocker, mock_request):
    """Test that reset handlers work correctly."""
    # Spy on form's handle_reset_request
    reset_spy = mocker.patch.object(comparison.left_form, "handle_reset_request")

    comparison.register_routes(mock_app)

    # Find the left reset handler
    left_reset_route = next(
        r
        for r in mock_app.registered_routes
        if r["path"] == "/compare/test_comp/left/reset"
    )

    # Call the handler
    handler = left_reset_route["handler"]
    result = await handler(mock_request)

    # Should have called form's reset
    reset_spy.assert_called_once()

    # Should return rendered column
    assert result is not None  # Would be FT component


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_handler_functionality(
    comparison, mock_app, mocker, mock_request
):
    """Test that refresh handlers work correctly."""
    # Spy on internal helper to avoid re-parsing request body
    refresh_spy = mocker.patch.object(
        comparison.right_form, "_handle_refresh_with_form_data"
    )

    comparison.register_routes(mock_app)

    # Find the right refresh handler
    right_refresh_route = next(
        r
        for r in mock_app.registered_routes
        if r["path"] == "/compare/test_comp/right/refresh"
    )

    # Call the handler
    handler = right_refresh_route["handler"]
    result = await handler(mock_request)

    # Should have refreshed from parsed form dict
    refresh_spy.assert_called_once_with({})

    # Should return rendered column
    assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_routes_use_correct_form_references(
    comparison, mock_app, mocker, mock_request
):
    """Test that route handlers capture correct form references."""
    # Track which form's methods are called
    left_reset_spy = mocker.patch.object(comparison.left_form, "handle_reset_request")
    right_reset_spy = mocker.patch.object(comparison.right_form, "handle_reset_request")

    comparison.register_routes(mock_app)

    # Get handlers
    routes_by_path = {r["path"]: r["handler"] for r in mock_app.registered_routes}

    # Call left reset
    await routes_by_path["/compare/test_comp/left/reset"](mock_request)

    # Only left form should be reset
    left_reset_spy.assert_called_once()
    right_reset_spy.assert_not_called()

    # Reset spies
    left_reset_spy.reset_mock()
    right_reset_spy.reset_mock()

    # Call right reset
    await routes_by_path["/compare/test_comp/right/reset"](mock_request)

    # Only right form should be reset
    left_reset_spy.assert_not_called()
    right_reset_spy.assert_called_once()


@pytest.mark.unit
def test_multiple_comparison_forms_separate_routes(mock_app):
    """Test that multiple comparison forms don't interfere."""
    # Create two comparison forms
    comp1 = ComparisonForm(
        "comp1", PydanticForm("left1", SimpleModel), PydanticForm("right1", SimpleModel)
    )
    comp2 = ComparisonForm(
        "comp2", PydanticForm("left2", SimpleModel), PydanticForm("right2", SimpleModel)
    )

    # Register both
    comp1.register_routes(mock_app)
    comp2.register_routes(mock_app)

    # Extract paths
    paths = [r["path"] for r in mock_app.registered_routes]

    # Should have routes for both
    assert "/compare/comp1/left/reset" in paths
    assert "/compare/comp2/left/reset" in paths

    # No path collisions
    assert len(paths) == len(set(paths))


@pytest.mark.unit
def test_template_name_used_for_routes(mock_app):
    """Test that template_name is used for registered routes."""
    # Create a comparison form with template_name
    comp = ComparisonForm(
        name="row_123",
        left_form=PydanticForm("left_row_123", SimpleModel),
        right_form=PydanticForm("right_row_123", SimpleModel),
        template_name="template_comp",
    )

    comp.register_routes(mock_app)

    # Extract paths
    paths = [r["path"] for r in mock_app.registered_routes]

    # Routes should use template_name, NOT name
    assert "/compare/template_comp/left/reset" in paths
    assert "/compare/template_comp/left/refresh" in paths
    assert "/compare/template_comp/right/reset" in paths
    assert "/compare/template_comp/right/refresh" in paths

    # Should NOT have routes with the instance name
    assert "/compare/row_123/left/reset" not in paths


@pytest.mark.unit
def test_template_name_shared_by_multiple_forms(mock_app):
    """Test multiple ComparisonForms can share the same template_name."""
    # Create a template form and register its routes once
    template = ComparisonForm(
        name="template",
        left_form=PydanticForm("left_template", SimpleModel),
        right_form=PydanticForm("right_template", SimpleModel),
        template_name="shared_template",
    )
    template.register_routes(mock_app)

    # Now create dynamic forms that use the same template_name
    # (These would NOT register routes - they reuse the template's routes)
    row1 = ComparisonForm(
        name="row_1",
        left_form=PydanticForm(
            "left_row_1", SimpleModel, template_name="left_template"
        ),
        right_form=PydanticForm(
            "right_row_1", SimpleModel, template_name="right_template"
        ),
        template_name="shared_template",  # Reuses template routes
    )
    row2 = ComparisonForm(
        name="row_2",
        left_form=PydanticForm(
            "left_row_2", SimpleModel, template_name="left_template"
        ),
        right_form=PydanticForm(
            "right_row_2", SimpleModel, template_name="right_template"
        ),
        template_name="shared_template",  # Reuses template routes
    )

    # Verify the template_name is stored correctly
    assert row1.name == "row_1"
    assert row1.template_name == "shared_template"
    assert row2.name == "row_2"
    assert row2.template_name == "shared_template"


@pytest.mark.unit
def test_template_name_defaults_to_name():
    """Test that template_name defaults to name when not specified."""
    comp = ComparisonForm(
        name="my_comparison",
        left_form=PydanticForm("left_form", SimpleModel),
        right_form=PydanticForm("right_form", SimpleModel),
    )

    assert comp.name == "my_comparison"
    assert comp.template_name == "my_comparison"


@pytest.mark.unit
def test_template_name_used_in_button_helper():
    """Test that _button_helper uses template_name for hx_post."""
    comp = ComparisonForm(
        name="dynamic_row",
        left_form=PydanticForm("left", SimpleModel),
        right_form=PydanticForm("right", SimpleModel),
        template_name="template_routes",
    )

    # Get the left refresh button
    button = comp.left_refresh_button()
    button_str = str(button)

    # Button should use template_name, not name
    assert "/compare/template_routes/left/refresh" in button_str
    assert "/compare/dynamic_row/left/refresh" not in button_str


class ModelWithList(BaseModel):
    """Model with a list field for testing refresh URLs."""

    items: list[str] = []


@pytest.mark.unit
def test_template_name_used_in_render_refresh_url():
    """Test that _render_column uses template_name for refresh URLs in list fields."""
    comp = ComparisonForm(
        name="instance_name",
        left_form=PydanticForm(
            "left", ModelWithList, initial_values={"items": ["a", "b"]}
        ),
        right_form=PydanticForm(
            "right", ModelWithList, initial_values={"items": ["x", "y"]}
        ),
        template_name="template_name",
    )

    # Render the inputs (calls _render_column internally)
    rendered = str(comp.render_inputs())

    # Refresh URLs should use template_name (these appear in list add buttons)
    assert (
        "/compare/template_name/left/refresh" in rendered
        or "/compare/template_name/right/refresh" in rendered
    )
    # Should NOT contain instance name in refresh URLs
    assert "/compare/instance_name/left/refresh" not in rendered
    assert "/compare/instance_name/right/refresh" not in rendered


@pytest.mark.unit
def test_button_helper_sends_fhpf_form_name_for_template_forms():
    """Test that _button_helper sends fhpf_form_name when PydanticForm uses template_name."""
    # Create forms where the PydanticForm uses template_name (dynamic form scenario)
    dynamic_left = PydanticForm(
        "dynamic_left_row1", SimpleModel, template_name="template_left"
    )
    dynamic_right = PydanticForm(
        "dynamic_right_row1", SimpleModel, template_name="template_right"
    )

    comp = ComparisonForm(
        name="dynamic_row1",
        left_form=dynamic_left,
        right_form=dynamic_right,
        template_name="shared_routes",
    )

    # Get the left refresh button
    button = comp.left_refresh_button()
    button_str = str(button)

    # Button should include hx-vals with fhpf_form_name
    assert "fhpf_form_name" in button_str
    assert "dynamic_left_row1" in button_str


@pytest.mark.unit
def test_button_helper_no_fhpf_form_name_without_template():
    """Test that _button_helper does NOT send fhpf_form_name when no template_name."""
    # Create regular forms without template_name
    left = PydanticForm("left_form", SimpleModel)
    right = PydanticForm("right_form", SimpleModel)

    comp = ComparisonForm(
        name="my_comp",
        left_form=left,
        right_form=right,
    )

    # Get the left refresh button
    button = comp.left_refresh_button()
    button_str = str(button)

    # Button should NOT include hx-vals with fhpf_form_name
    assert "fhpf_form_name" not in button_str
