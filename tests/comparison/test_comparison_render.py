"""Integration tests for ComparisonForm rendering."""

import re
from typing import List, Optional

import pytest
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm
from fh_pydantic_form.comparison_form import ComparisonForm, simple_diff_metrics

pytestmark = [pytest.mark.comparison, pytest.mark.integration]


class RenderTestModel(BaseModel):
    """Model for render testing."""

    title: str = "Default Title"
    count: int = 10
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


@pytest.fixture
def render_comparison():
    """Create comparison form for render testing."""
    left_values = RenderTestModel(
        title="Original", count=5, tags=["tag1", "tag2"], notes="Original notes"
    )
    right_values = RenderTestModel(
        title="Modified",
        count=5,  # Same as left
        tags=["tag1", "tag3"],  # Partially different
        notes=None,  # Missing
    )

    left = PydanticForm("render_left", RenderTestModel, initial_values=left_values)
    right = PydanticForm("render_right", RenderTestModel, initial_values=right_values)

    return ComparisonForm("render_test", left, right)


@pytest.fixture
def render_comparison_with_metrics():
    """Create comparison form with metrics."""
    left_values = RenderTestModel(
        title="Original", count=5, tags=["tag1", "tag2"], notes="Some notes"
    )
    right_values = RenderTestModel(
        title="Modified", count=10, tags=["tag1", "tag3"], notes="Some notes"
    )

    # Create metrics
    metrics = simple_diff_metrics(left_values, right_values, RenderTestModel)

    # Create forms with metrics
    left = PydanticForm(
        "metric_left", RenderTestModel, initial_values=left_values, metrics_dict=metrics
    )
    right = PydanticForm(
        "metric_right",
        RenderTestModel,
        initial_values=right_values,
        metrics_dict=metrics,
    )

    return ComparisonForm("metric_test", left, right)


@pytest.fixture
def soup():
    """BeautifulSoup parser for HTML analysis."""

    def _parse(html):
        import bs4

        return bs4.BeautifulSoup(html, "html.parser")

    return _parse


def test_render_inputs_basic_structure(render_comparison):
    """Test basic HTML structure of rendered comparison."""
    html = render_comparison.render_inputs().__html__()

    # Check grid structure
    assert 'class="fhpf-compare grid grid-cols-2' in html
    assert 'id="render_test-comparison-grid"' in html

    # Check wrapper divs
    assert 'id="render_left-inputs-wrapper"' in html
    assert 'id="render_right-inputs-wrapper"' in html
    assert 'class="contents"' in html


def test_render_inputs_headers(render_comparison, soup):
    """Test that column headers are rendered correctly."""
    html = render_comparison.render_inputs().__html__()
    dom = soup(html)

    # Find headers
    headers = dom.find_all("h3")
    header_texts = [h.text for h in headers]

    assert "Reference" in header_texts
    assert "Generated" in header_texts


def test_render_inputs_field_ordering(render_comparison, soup):
    """Test CSS grid ordering of fields."""
    html = render_comparison.render_inputs().__html__()
    dom = soup(html)

    # Find elements with order styles
    ordered_elements = dom.find_all(style=re.compile(r"order:\d+"))

    # Extract order values
    orders = []
    for elem in ordered_elements:
        match = re.search(r"order:(\d+)", elem.get("style", ""))
        if match:
            orders.append(int(match.group(1)))

    # Should have even and odd orders
    even_orders = [o for o in orders if o % 2 == 0]
    odd_orders = [o for o in orders if o % 2 == 1]

    assert len(even_orders) > 0  # Left column
    assert len(odd_orders) > 0  # Right column

    # Orders should be sequential within each column
    assert even_orders == sorted(even_orders)
    assert odd_orders == sorted(odd_orders)


def test_render_inputs_data_path_attributes(render_comparison, soup):
    """Test that data-path attributes are present."""
    html = render_comparison.render_inputs().__html__()
    dom = soup(html)

    # Find elements with data-path
    path_elements = dom.find_all(attrs={"data-path": True})
    paths = [elem["data-path"] for elem in path_elements]

    # Should have paths for each field (duplicated for left/right)
    expected_paths = ["title", "count", "tags", "notes"]
    for path in expected_paths:
        assert paths.count(path) == 2  # One for left, one for right


def test_render_inputs_field_values(render_comparison, soup):
    """Test that field values are rendered correctly."""
    html = render_comparison.render_inputs().__html__()

    # Check left values - string fields are now in textarea elements, others in input elements
    # For string fields (like "title"), content is in textarea text
    assert "Original" in html  # Should be in textarea content
    assert 'value="5"' in html  # Numbers still use input with value attribute
    assert "tag1" in html  # List items for strings now use textarea content
    assert "tag2" in html  # List items for strings now use textarea content
    assert (
        "Original notes" in html
    )  # Notes field (string) should be in textarea content

    # Check right values
    assert "Modified" in html  # Should be in textarea content
    assert "tag3" in html  # List items for strings now use textarea content


def test_render_with_excluded_fields():
    """Test rendering with excluded fields."""
    left = PydanticForm("left", RenderTestModel, exclude_fields=["tags"])
    right = PydanticForm("right", RenderTestModel, exclude_fields=["notes"])
    comp = ComparisonForm("exclude_test", left, right)

    html = comp.render_inputs().__html__()

    # Left should not have tags
    assert html.count('data-path="tags"') == 1  # Only right side

    # Right should not have notes
    assert html.count('data-path="notes"') == 1  # Only left side


def test_render_custom_labels():
    """Test rendering with custom column labels."""
    left = PydanticForm("left", RenderTestModel)
    right = PydanticForm("right", RenderTestModel)
    comp = ComparisonForm(
        "label_test", left, right, left_label="Before", right_label="After"
    )

    html = comp.render_inputs().__html__()

    assert "Before" in html
    assert "After" in html
    assert "Reference" not in html
    assert "Generated" not in html


def test_form_wrapper_integration(render_comparison):
    """Test form wrapper with actual content."""
    inputs = render_comparison.render_inputs()
    wrapped = render_comparison.form_wrapper(inputs)

    html = wrapped.__html__()

    # Should have form element
    assert "<form" in html
    assert 'id="render_test-comparison-form"' in html

    # Should contain the grid
    assert 'id="render_test-comparison-grid"' in html


def test_render_with_metrics_visual_indicators(render_comparison_with_metrics):
    """Test that metrics affect visual rendering."""
    html = render_comparison_with_metrics.render_inputs().__html__()

    # The forms should have metrics_dict set, which field renderers use
    # to add visual indicators (colors, badges, etc.)
    # This is a smoke test - specific visual implementation depends on field renderers

    # At minimum, the HTML should be generated without errors
    assert "metric_test-comparison-grid" in html
    assert "metric_left-inputs-wrapper" in html
    assert "metric_right-inputs-wrapper" in html


def test_comparison_form_js_included():
    """Test that comparison JS is included when needed."""
    from fh_pydantic_form.comparison_form import comparison_form_js

    js = comparison_form_js()
    html = js.__html__()

    # Should have script tag
    assert "<script>" in html
    assert "</script>" in html

    # Should have key functions
    assert "initComparisonSync" in html
    assert "mirrorTopLevel" in html
    assert "toggleListItems" in html


def test_render_empty_model():
    """Test rendering with minimal/empty model."""

    class EmptyModel(BaseModel):
        pass

    left = PydanticForm("empty_left", EmptyModel)
    right = PydanticForm("empty_right", EmptyModel)
    comp = ComparisonForm("empty_test", left, right)

    html = comp.render_inputs().__html__()

    # Should still have basic structure
    assert "empty_test-comparison-grid" in html
    assert 'class="contents"' in html

    # Should have headers
    assert "Reference" in html
    assert "Generated" in html
