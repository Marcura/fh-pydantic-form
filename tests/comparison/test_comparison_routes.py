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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reset_handler_functionality(comparison, mock_app, mocker):
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
    req = mocker.Mock()  # Mock request
    result = await handler(req)

    # Should have called form's reset
    reset_spy.assert_called_once()

    # Should return rendered column
    assert result is not None  # Would be FT component


@pytest.mark.unit
@pytest.mark.asyncio
async def test_refresh_handler_functionality(comparison, mock_app, mocker):
    """Test that refresh handlers work correctly."""
    # Spy on form's handle_refresh_request
    refresh_spy = mocker.patch.object(comparison.right_form, "handle_refresh_request")

    comparison.register_routes(mock_app)

    # Find the right refresh handler
    right_refresh_route = next(
        r
        for r in mock_app.registered_routes
        if r["path"] == "/compare/test_comp/right/refresh"
    )

    # Call the handler
    handler = right_refresh_route["handler"]
    req = mocker.Mock()  # Mock request
    result = await handler(req)

    # Should have called form's refresh with request
    refresh_spy.assert_called_once_with(req)

    # Should return rendered column
    assert result is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_routes_use_correct_form_references(comparison, mock_app, mocker):
    """Test that route handlers capture correct form references."""
    # Track which form's methods are called
    left_reset_spy = mocker.patch.object(comparison.left_form, "handle_reset_request")
    right_reset_spy = mocker.patch.object(comparison.right_form, "handle_reset_request")

    comparison.register_routes(mock_app)

    # Get handlers
    routes_by_path = {r["path"]: r["handler"] for r in mock_app.registered_routes}

    # Call left reset
    req = mocker.Mock()
    await routes_by_path["/compare/test_comp/left/reset"](req)

    # Only left form should be reset
    left_reset_spy.assert_called_once()
    right_reset_spy.assert_not_called()

    # Reset spies
    left_reset_spy.reset_mock()
    right_reset_spy.reset_mock()

    # Call right reset
    await routes_by_path["/compare/test_comp/right/reset"](req)

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
