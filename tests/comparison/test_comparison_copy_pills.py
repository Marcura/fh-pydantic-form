"""
Tests for ComparisonForm copy functionality with List[Literal] pill fields.

These tests validate the HTML structure and data attributes required for
client-side pill copy logic between comparison form columns.
"""

import json
from typing import List, Literal

import pytest
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm
from fh_pydantic_form.comparison_form import ComparisonForm
from tests import to_html, unescaped

pytestmark = [pytest.mark.comparison]


# --- Test Models ---


class PillProduct(BaseModel):
    """Model with a top-level List[Literal] field."""

    name: str = "Default"
    categories: List[Literal["Electronics", "Clothing", "Home"]] = Field(
        default_factory=list
    )


class CategoryGroup(BaseModel):
    """Nested model containing a List[Literal] field."""

    categories: List[Literal["A", "B", "C"]] = Field(default_factory=list)


class NestedPillProduct(BaseModel):
    """Model with List[BaseModel] containing List[Literal] fields."""

    groups: List[CategoryGroup] = Field(default_factory=list)


# --- Fixtures ---


@pytest.fixture
def soup():
    """BeautifulSoup parser for HTML analysis."""

    def _parse(html):
        return BeautifulSoup(html, "html.parser")

    return _parse


@pytest.fixture
def pill_comparison_dom(soup):
    """Render a ComparisonForm with a top-level List[Literal] field."""
    left_values = PillProduct(
        name="Left",
        categories=["Electronics", "Home"],
    )
    right_values = PillProduct(
        name="Right",
        categories=["Clothing"],
    )

    left_form = PydanticForm("left_form", PillProduct, initial_values=left_values)
    right_form = PydanticForm("right_form", PillProduct, initial_values=right_values)

    comp = ComparisonForm(
        "pill_test",
        left_form,
        right_form,
        copy_left=True,
        copy_right=True,
    )

    html = to_html(comp.render_inputs())
    return soup(html)


@pytest.fixture
def nested_pill_comparison_dom(soup):
    """Render a ComparisonForm with nested List[Literal] pill fields."""
    left_values = NestedPillProduct(
        groups=[CategoryGroup(categories=["A"])],
    )
    right_values = NestedPillProduct(
        groups=[CategoryGroup(categories=["B", "C"])],
    )

    left_form = PydanticForm(
        "left_form", NestedPillProduct, initial_values=left_values
    )
    right_form = PydanticForm(
        "right_form", NestedPillProduct, initial_values=right_values
    )

    comp = ComparisonForm(
        "nested_pill_test",
        left_form,
        right_form,
        copy_left=True,
        copy_right=True,
    )

    html = to_html(comp.render_inputs())
    return soup(html)


# --- Tests ---


class TestPillFieldCopyMarkup:
    """Tests for List[Literal] pill field copy prerequisites."""

    def test_pill_containers_have_prefix_and_choices(self, pill_comparison_dom):
        containers = pill_comparison_dom.find_all(
            attrs={"data-pill-field": "true", "data-field-path": "categories"}
        )

        assert len(containers) == 2, "Expected pill containers for both forms"

        prefixes = {c.get("data-input-prefix") for c in containers}
        assert "left_form_" in prefixes
        assert "right_form_" in prefixes

        expected_ids = {
            "left_form_categories_pills_container",
            "right_form_categories_pills_container",
        }
        actual_ids = {c.get("id") for c in containers}
        assert expected_ids == actual_ids

        # Ensure choices JSON is present and valid
        for container in containers:
            raw = container.get("data-all-choices")
            assert raw, "Expected data-all-choices JSON on pill container"
            parsed = json.loads(unescaped(raw))
            values = {item["value"] for item in parsed}
            assert values == {"Electronics", "Clothing", "Home"}

    def test_nested_pill_containers_include_item_prefix(self, nested_pill_comparison_dom):
        containers = nested_pill_comparison_dom.find_all(
            attrs={"data-pill-field": "true", "data-field-path": "groups[0].categories"}
        )

        assert len(containers) == 2, "Expected nested pill containers for both forms"

        prefixes = {c.get("data-input-prefix") for c in containers}
        assert "left_form_groups_0_" in prefixes
        assert "right_form_groups_0_" in prefixes

        expected_ids = {
            "left_form_groups_0_categories_pills_container",
            "right_form_groups_0_categories_pills_container",
        }
        actual_ids = {c.get("id") for c in containers}
        assert expected_ids == actual_ids
