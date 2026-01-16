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

    left_form = PydanticForm("left_form", NestedPillProduct, initial_values=left_values)
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

    def test_nested_pill_containers_include_item_prefix(
        self, nested_pill_comparison_dom
    ):
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


class TestNestedPillFieldCopyBugs:
    """
    Tests documenting bugs in nested pill field copy functionality.

    These tests verify the behavior of copying List[Literal] (pill) fields
    that are nested inside List[BaseModel] items.

    Bug scenarios:
    1. Copying full list: performListCopyByPosition() skips pill containers (DIV elements)
    2. Copying full item: performStandardCopy() only matches exact path, misses nested pills
    3. Copying subfield: subfield copy code doesn't handle pill containers
    """

    def test_nested_pill_field_has_data_pill_field_marker(
        self, nested_pill_comparison_dom
    ):
        """
        Verify that nested pill containers have the data-pill-field marker.

        This marker is essential for the JavaScript copy logic to identify
        pill containers and handle them specially.
        """
        # Find all elements with data-pill-field="true"
        pill_containers = nested_pill_comparison_dom.find_all(
            attrs={"data-pill-field": "true"}
        )

        assert len(pill_containers) >= 2, (
            "Expected at least 2 pill containers (one per form)"
        )

        # Verify the path attribute is set correctly for nested pills
        nested_paths = [
            c.get("data-field-path")
            for c in pill_containers
            if c.get("data-field-path", "").startswith("groups[")
        ]
        assert len(nested_paths) >= 2, (
            f"Expected nested paths like 'groups[0].categories', got {nested_paths}"
        )

    def test_nested_pill_containers_are_div_elements(self, nested_pill_comparison_dom):
        """
        Verify that pill containers are DIV elements, not standard form inputs.

        This is important because the JavaScript copy functions handle
        TEXTAREA, SELECT, UK-SELECT, INPUT but not DIV.

        BUG: performListCopyByPosition() iterates inputs by tagName but
        pill containers are DIVs, so they get skipped.
        """
        pill_containers = nested_pill_comparison_dom.find_all(
            attrs={"data-pill-field": "true"}
        )

        for container in pill_containers:
            # Pill containers should be DIV elements
            assert container.name == "div", (
                f"Expected DIV element, got {container.name}"
            )

    def test_nested_pill_copy_button_path_structure(self, nested_pill_comparison_dom):
        """
        Verify that copy buttons for nested pill fields have correct path structure.

        For nested pills, the path should be something like:
        - "groups[0].categories" (subfield copy)
        - NOT just "categories" (which would be a top-level field)
        """
        import re

        # Find copy buttons with onclick containing groups[
        copy_buttons = nested_pill_comparison_dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy.*groups\[")
        )

        # Should have copy buttons for nested fields
        assert len(copy_buttons) > 0, "Expected copy buttons for nested groups"

        # Check for copy buttons specifically for the nested categories field
        categories_copy_buttons = [
            btn
            for btn in copy_buttons
            if "groups[0].categories" in btn.get("onclick", "")
        ]

        # There should be copy buttons for the nested categories pill field
        assert len(categories_copy_buttons) >= 1, (
            "Expected copy button for groups[0].categories nested pill field"
        )

    def test_performListCopyByPosition_should_handle_pill_containers(self):
        """
        Document the bug: performListCopyByPosition() doesn't handle pill containers.

        The function iterates through sourceInputs and copies based on tagName:
        - TEXTAREA → copies .value
        - SELECT, UK-SELECT → copies selected option
        - INPUT → copies .value
        - DIV (pill container) → SKIPPED (bug!)

        This test documents the expected behavior when this bug is fixed.
        """
        # When performListCopyByPosition encounters a pill container:
        # 1. It should detect data-pill-field="true" attribute
        # 2. It should use the pill-specific copy logic from performStandardCopy
        # 3. It should copy the selected pills (hidden inputs) to the target

        # This is a conceptual test - the actual fix is in JavaScript
        # The fix should check:
        # if (sourceInput.dataset.pillField === 'true') {
        #     copyPillField(sourceInput, targetInput);
        # }
        pass

    def test_performStandardCopy_should_find_nested_pills_by_prefix(self):
        """
        Document the bug: performStandardCopy() only matches exact path for pills.

        Current code (line 858-861):
        var sourcePillCandidates = document.querySelectorAll(
          '[data-field-path="' + sourcePathPrefix + '"][data-pill-field="true"]'
        );

        When copying "groups[0]" (full list item), this looks for:
        '[data-field-path="groups[0]"][data-pill-field="true"]'

        But the actual pill container has:
        '[data-field-path="groups[0].categories"][data-pill-field="true"]'

        So the pill field is NOT found and NOT copied.

        EXPECTED: When copying a list item, the function should also find and
        copy any pill fields that are CHILDREN of that path.
        """
        # The fix should query for pill fields that START WITH the source path:
        # '[data-field-path^="' + sourcePathPrefix + '"][data-pill-field="true"]'
        #
        # Or iterate through sourceInputs and check for data-pill-field attribute.
        pass

    def test_subfield_copy_should_handle_pill_fields(self):
        """
        Document the bug: subfield copy (lines 119-268) doesn't handle pill fields.

        When copying "groups[0].categories" (a nested pill field), the code:
        1. Finds sourceInput with data-field-path="groups[0].categories"
        2. The sourceInput is a DIV with data-pill-field="true"
        3. Tries to copy based on tagName (TEXTAREA, SELECT, etc.)
        4. DIV doesn't match any case, so copy fails silently

        EXPECTED: Should detect data-pill-field and use pill-specific copy logic.
        """
        # The fix should add a check before the tag-based switch:
        # if (sourceInput.dataset.pillField === 'true') {
        #     // Use pill-aware copy logic
        #     copyPillFieldToTarget(sourceInput, targetInput, ...);
        #     return;
        # }
        pass
