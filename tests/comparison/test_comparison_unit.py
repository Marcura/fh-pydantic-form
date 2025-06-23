"""Unit tests for ComparisonForm class."""

from typing import Optional

import fasthtml.common as fh
import pytest
from pydantic import BaseModel

from fh_pydantic_form import PydanticForm
from fh_pydantic_form.comparison_form import ComparisonForm, simple_diff_metrics

pytestmark = pytest.mark.comparison


# Test models
class SimpleComparisonModel(BaseModel):
    """Simple model for comparison testing."""

    name: str = "Default Name"
    value: int = 42
    description: Optional[str] = None


class AnotherModel(BaseModel):
    """Different model to test mismatch."""

    title: str = "Another"
    count: int = 10


# Fixtures
@pytest.fixture(scope="session")
def example_model():
    """Simple BaseModel for testing."""
    return SimpleComparisonModel


@pytest.fixture
def left_form(example_model):
    """Left form instance."""
    return PydanticForm("left_form", example_model)


@pytest.fixture
def right_form(example_model):
    """Right form instance."""
    return PydanticForm("right_form", example_model)


@pytest.fixture
def comparison(left_form, right_form):
    """ComparisonForm instance."""
    return ComparisonForm("test_comparison", left_form, right_form)


@pytest.fixture
def mock_app(mocker):
    """Mock FastHTML app for route testing."""
    app = mocker.Mock()
    # Make route decorator return the function it decorates
    app.route = mocker.Mock(side_effect=lambda path, methods=None: lambda f: f)
    return app


# Constructor tests
@pytest.mark.unit
def test_constructor_model_mismatch():
    """Test that constructor raises ValueError for different models."""
    left = PydanticForm("left", SimpleComparisonModel)
    right = PydanticForm("right", AnotherModel)

    with pytest.raises(
        ValueError, match="Both forms must be based on the same model class"
    ):
        ComparisonForm[SimpleComparisonModel]("bad", left, right)


@pytest.mark.unit
def test_constructor_valid(comparison):
    """Test valid constructor initialization."""
    assert comparison.name == "test_comparison"
    assert comparison.left_label == "Reference"
    assert comparison.right_label == "Generated"
    assert comparison.model_class == SimpleComparisonModel


@pytest.mark.unit
def test_constructor_custom_labels():
    """Test constructor with custom labels."""
    left = PydanticForm("left", SimpleComparisonModel)
    right = PydanticForm("right", SimpleComparisonModel)
    comp = ComparisonForm(
        "test", left, right, left_label="Original", right_label="Modified"
    )

    assert comp.left_label == "Original"
    assert comp.right_label == "Modified"


# Column rendering tests
@pytest.mark.unit
@pytest.mark.parametrize(
    "start_order,expected_header_order,expected_first_field_order",
    [
        (0, 0, 2),  # Left column: header=0, first field=2
        (1, 1, 3),  # Right column: header=1, first field=3
    ],
)
def test_render_column_order(
    comparison, start_order, expected_header_order, expected_first_field_order
):
    """Test that column rendering produces correct CSS order values."""
    col = comparison._render_column(
        form=comparison.left_form if start_order == 0 else comparison.right_form,
        header_label="Test Label",
        start_order=start_order,
        wrapper_id="test-wrapper",
    )

    html = col.__html__()

    # Check header order
    assert f'style="order:{expected_header_order}"' in html

    # Check first field order
    assert f'style="order:{expected_first_field_order}"' in html

    # Check wrapper has display: contents
    assert 'class="contents"' in html
    assert 'id="test-wrapper"' in html


@pytest.mark.unit
def test_render_column_data_path_attributes(comparison):
    """Test that rendered columns include data-path attributes."""
    col = comparison._render_column(
        form=comparison.left_form,
        header_label="Left",
        start_order=0,
        wrapper_id="left-wrapper",
    )

    html = col.__html__()

    # Check data-path attributes for each field
    assert 'data-path="name"' in html
    assert 'data-path="value"' in html
    assert 'data-path="description"' in html


@pytest.mark.unit
def test_render_column_excludes_fields(example_model):
    """Test that excluded fields are not rendered."""
    # Create form with excluded field
    form = PydanticForm("test", example_model, exclude_fields=["value"])
    comp = ComparisonForm("test", form, PydanticForm("right", example_model))

    col = comp._render_column(
        form=form, header_label="Test", start_order=0, wrapper_id="test-wrapper"
    )

    html = col.__html__()

    # Should have name and description but not value
    assert 'data-path="name"' in html
    assert 'data-path="description"' in html
    assert 'data-path="value"' not in html


# Button helper tests
@pytest.mark.unit
@pytest.mark.parametrize(
    "side,action,expected_path",
    [
        ("left", "reset", "/compare/test_comparison/left/reset"),
        ("left", "refresh", "/compare/test_comparison/left/refresh"),
        ("right", "reset", "/compare/test_comparison/right/reset"),
        ("right", "refresh", "/compare/test_comparison/right/refresh"),
    ],
)
def test_button_helper_paths(comparison, side, action, expected_path):
    """Test that button helpers generate correct HTMX paths."""
    method_name = f"{side}_{action}_button"
    button_method = getattr(comparison, method_name)
    button = button_method()

    html = button.__html__()
    assert f'hx-post="{expected_path}"' in html


@pytest.mark.unit
def test_button_helper_targets(comparison):
    """Test that button helpers set correct HTMX targets."""
    left_reset = comparison.left_reset_button()
    right_reset = comparison.right_reset_button()

    left_html = left_reset.__html__()
    right_html = right_reset.__html__()

    assert 'hx-target="#left_form-inputs-wrapper"' in left_html
    assert 'hx-target="#right_form-inputs-wrapper"' in right_html
    assert 'hx-swap="innerHTML"' in left_html
    assert 'hx-swap="innerHTML"' in right_html


@pytest.mark.unit
def test_button_custom_text_and_kwargs(comparison):
    """Test button helpers with custom text and attributes."""
    button = comparison.left_reset_button(
        text="Custom Reset", cls="custom-class", id="custom-id"
    )

    html = button.__html__()
    assert "Custom Reset" in html
    assert 'class="uk-btn custom-class"' in html  # May have additional classes
    assert 'id="custom-id"' in html


# Path string helper test
@pytest.mark.unit
def test_get_field_path_string(comparison):
    """Test field path string conversion."""
    assert comparison._get_field_path_string(["field"]) == "field"
    assert comparison._get_field_path_string(["parent", "child"]) == "parent.child"
    assert comparison._get_field_path_string([]) == ""


# Form wrapper test
@pytest.mark.unit
def test_form_wrapper(comparison):
    """Test form wrapper generation."""
    content = fh.Div("Test content")
    wrapped = comparison.form_wrapper(content)

    html = wrapped.__html__()
    assert "<form" in html
    assert 'id="test_comparison-comparison-form"' in html
    assert 'id="test_comparison-comparison-wrapper"' in html
    assert "Test content" in html


@pytest.mark.unit
def test_form_wrapper_custom_id(comparison):
    """Test form wrapper with custom ID."""
    content = fh.Div("Test")
    wrapped = comparison.form_wrapper(content, form_id="custom-form-id")

    html = wrapped.__html__()
    assert 'id="custom-form-id"' in html


# simple_diff_metrics tests
@pytest.mark.unit
@pytest.mark.parametrize(
    "left_val,right_val,expected_metric,expected_color,expected_comment",
    [
        # Exact match
        ("same", "same", 1.0, "green", "Values match exactly"),
        (42, 42, 1.0, "green", "Values match exactly"),
        # One value missing
        ("value", None, 0.0, "orange", "One value is missing"),
        (None, "value", 0.0, "orange", "One value is missing"),
        # Different values (non-string)
        (10, 20, 0.0, None, "Different values: 10 vs 20"),
        # String similarity
        ("hello", "hello", 1.0, "green", "Values match exactly"),
        ("test", "text", 0.75, None, "String similarity: 75%"),
        ("abc", "xyz", 0.0, None, "String similarity: 0%"),
    ],
)
def test_simple_diff_metrics_field_comparison(
    left_val, right_val, expected_metric, expected_color, expected_comment
):
    """Test simple_diff_metrics for individual field comparisons."""

    class TestModel(BaseModel):
        field: Optional[str] = None

    left_data = {"field": left_val}
    right_data = {"field": right_val}

    metrics = simple_diff_metrics(left_data, right_data, TestModel)

    assert "field" in metrics
    entry = metrics["field"]
    # Check that entry is a dictionary with expected keys
    assert isinstance(entry, dict)
    assert entry["metric"] == expected_metric
    if expected_color:
        assert entry["color"] == expected_color
    assert entry["comment"] == expected_comment


@pytest.mark.unit
def test_simple_diff_metrics_model_instances():
    """Test simple_diff_metrics with BaseModel instances."""
    left = SimpleComparisonModel(name="Test", value=42, description="Desc")
    right = SimpleComparisonModel(name="Test", value=100, description="Desc")

    metrics = simple_diff_metrics(left, right, SimpleComparisonModel)

    # Name and description match
    assert metrics["name"]["metric"] == 1.0
    assert metrics["description"]["metric"] == 1.0

    # Value differs
    assert metrics["value"]["metric"] == 0.0
    assert "Different values: 42 vs 100" in metrics["value"]["comment"]


@pytest.mark.unit
def test_simple_diff_metrics_empty_data():
    """Test simple_diff_metrics with missing values (one None, one not)."""
    # Create instances where one side has missing values
    left_data = SimpleComparisonModel(name="Test", value=42, description=None)
    right_data = SimpleComparisonModel(
        name="Test", value=42, description="Has description"
    )

    metrics = simple_diff_metrics(left_data, right_data, SimpleComparisonModel)

    # Should have entries for all fields
    assert len(metrics) == 3  # name, value, description

    # Name and value should match
    assert metrics["name"]["metric"] == 1.0  # Same strings match
    assert metrics["value"]["metric"] == 1.0  # Same values match
    # Description should indicate one value missing
    assert metrics["description"]["metric"] == 0.0
    assert metrics["description"]["color"] == "orange"
    assert metrics["description"]["comment"] == "One value is missing"
