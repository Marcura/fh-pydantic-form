"""
Tests for ComparisonForm copy functionality with List[BaseModel] fields.

These tests validate the copy behavior between comparison form columns,
specifically for List[BaseModel] item copying and full list copying.
"""

import re
from typing import List, Optional

import pytest
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
import fasthtml.common as fh
import monsterui.all as mui
from starlette.testclient import TestClient

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.comparison_form import ComparisonForm, comparison_form_js

pytestmark = [pytest.mark.comparison]


# --- Test Models ---


class Review(BaseModel):
    """A review model for testing List[BaseModel] copy behavior."""

    rating: int = 5
    comment: str = ""

    def __str__(self) -> str:
        return f"Rating: {self.rating} - {self.comment[:20]}..."


class Product(BaseModel):
    """A product model with List[BaseModel] field for copy testing."""

    name: str = "Default Product"
    description: Optional[str] = None
    reviews: List[Review] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


# --- Fixtures ---


@pytest.fixture
def review_comparison_client():
    """
    Create a ComparisonForm with List[BaseModel] (reviews) for copy testing.

    Left form has 2 reviews, right form has 1 review.
    copy_left=True enables copying from right to left.
    """
    left_values = Product(
        name="Left Product",
        description="Reference product",
        reviews=[
            Review(rating=5, comment="Excellent product"),
            Review(rating=4, comment="Very good"),
        ],
        tags=["original", "reference"],
    )
    right_values = Product(
        name="Right Product",
        description="Generated product",
        reviews=[
            Review(rating=3, comment="Average product"),
        ],
        tags=["generated"],
    )

    left_form = PydanticForm(
        "left_form",
        Product,
        initial_values=left_values,
    )
    right_form = PydanticForm(
        "right_form",
        Product,
        initial_values=right_values,
    )

    comp = ComparisonForm(
        "review_test",
        left_form,
        right_form,
        left_label="Reference",
        right_label="Generated",
        copy_left=True,  # Enable copy from right to left
        copy_right=True,  # Enable copy from left to right
    )

    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js(), comparison_form_js()],
        pico=False,
        live=False,
    )
    comp.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            comp.form_wrapper(comp.render_inputs()),
            comparison_form_js(),
        )

    return TestClient(app), comp


@pytest.fixture
def soup():
    """BeautifulSoup parser for HTML analysis."""

    def _parse(html):
        return BeautifulSoup(html, "html.parser")

    return _parse


@pytest.fixture
def htmx_headers():
    """Standard HTMX request headers for testing."""
    return {
        "HX-Request": "true",
        "HX-Current-URL": "http://testserver/",
        "HX-Target": "result",
        "Content-Type": "application/x-www-form-urlencoded",
    }


# --- Tests for Copy Button Rendering ---


class TestCopyButtonRendering:
    """Tests for copy button rendering in ComparisonForm with List[BaseModel]."""

    def test_list_item_copy_button_has_correct_path(
        self, review_comparison_client, soup
    ):
        """
        Test that copy buttons on List[BaseModel] items have the correct path.

        The path should be like "reviews[0]" for the first item.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy buttons with onclick containing reviews[
        copy_buttons = dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy.*reviews\[")
        )

        # Should have copy buttons for list items
        assert len(copy_buttons) > 0, "Expected copy buttons for review items"

        # Extract paths from onclick handlers
        paths = []
        for btn in copy_buttons:
            onclick = btn.get("onclick", "")
            match = re.search(r"fhpfPerformCopy\('([^']+)'", onclick)
            if match:
                paths.append(match.group(1))

        # Verify we have paths for individual review items
        item_paths = [p for p in paths if re.match(r"reviews\[\d+\]$", p)]
        assert len(item_paths) > 0, f"Expected paths like 'reviews[0]', got {paths}"

    def test_full_list_copy_button_has_correct_path(
        self, review_comparison_client, soup
    ):
        """
        Test that the copy button for the full reviews list has path "reviews".
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy buttons with onclick for the full list (path without brackets)
        copy_buttons = dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy\('reviews',")
        )

        # Should have copy buttons for the full list field
        assert len(copy_buttons) >= 2, (
            "Expected copy buttons for reviews field on both sides"
        )

    def test_data_field_path_set_on_list_item_inputs(
        self, review_comparison_client, soup
    ):
        """
        Test that data-field-path is correctly set on inputs within list items.

        For List[BaseModel] items, paths should be like:
        - reviews[0].rating
        - reviews[0].comment
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all elements with data-field-path containing reviews[
        path_elements = dom.find_all(
            attrs={"data-field-path": re.compile(r"reviews\[")}
        )

        # Extract paths
        paths = [el["data-field-path"] for el in path_elements]

        # Should have paths for nested fields
        nested_paths = [p for p in paths if "." in p]
        assert len(nested_paths) > 0, (
            f"Expected nested paths like 'reviews[0].rating', got {paths}"
        )

        # Verify specific patterns exist
        rating_paths = [p for p in paths if ".rating" in p]
        comment_paths = [p for p in paths if ".comment" in p]

        assert len(rating_paths) > 0, "Expected rating paths in list items"
        assert len(comment_paths) > 0, "Expected comment paths in list items"


class TestCopyListItemBehavior:
    """
    Tests for copying individual List[BaseModel] items.

    When copying a single list item (e.g., reviews[0]) from source to target:
    1. A new item should be added to the target list
    2. Values should be copied from source item to new item
    3. The new item should appear after the corresponding index or at end
    """

    def test_copy_item_creates_correct_target_path_mapping(self):
        """
        Test the JavaScript path mapping logic for list item copy.

        Source path: reviews[0].rating
        Target path after add: reviews[new_TIMESTAMP].rating

        The copy logic should correctly map source field paths to target field paths.
        """
        # This tests the conceptual behavior:
        # When copying reviews[0] to left:
        # 1. Add new item to left list -> gets placeholder new_TIMESTAMP
        # 2. Map source "reviews[0].rating" to target "reviews[new_TIMESTAMP].rating"
        # 3. Copy value from source to target

        # Document expected path transformation
        source_path = "reviews[0]"
        source_field_path = "reviews[0].rating"

        # After adding item, target gets placeholder like "new_1234567890"
        target_placeholder = "new_1234567890"
        expected_target_path = f"reviews[{target_placeholder}].rating"

        # The relative path extraction should give:
        # source: "reviews[0].rating" -> relative: ".rating"
        # target: "reviews[new_1234567890].rating" -> relative: ".rating"

        # Extract relative path (what the JS does)
        relative_path = source_field_path.replace(source_path, "")
        assert relative_path == ".rating"

        # Construct target path (what the JS should do)
        computed_target_path = f"reviews[{target_placeholder}]{relative_path}"
        assert computed_target_path == expected_target_path

    def test_add_item_returns_proper_structure_for_copy(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that adding a list item returns HTML with correct structure for copying.

        The new item should have:
        - Inputs with data-field-path attributes
        - Name attributes with new_TIMESTAMP placeholder
        """
        client, comp = review_comparison_client

        # Add item to left form's reviews list
        response = client.post(
            "/form/left_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Find inputs with new_ in name
        new_inputs = dom.find_all(
            ["input", "textarea"],
            attrs={"name": re.compile(r"left_form_reviews_new_\d+")},
        )
        assert len(new_inputs) > 0, "Expected inputs with new_ placeholder"

        # Verify data-field-path is also set
        for inp in new_inputs:
            assert inp.has_attr("data-field-path"), (
                f"Input {inp.get('name')} missing data-field-path"
            )
            path = inp["data-field-path"]
            assert "reviews[new_" in path, (
                f"Expected path with new_ placeholder, got {path}"
            )


class TestCopyFullListBehavior:
    """
    Tests for copying entire List[BaseModel] fields.

    When copying a full list (e.g., reviews) from source to target:
    1. Target list should be aligned to source length
    2. Values should be copied by position (item 0 to item 0, etc.)
    3. Excess items in target should be removed
    """

    def test_list_containers_have_matching_ids(self, review_comparison_client, soup):
        """
        Test that list containers have proper IDs for full list copy detection.

        The JavaScript detects full list copy by checking for containers:
        - left_form_reviews_items_container
        - right_form_reviews_items_container
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find list containers
        left_container = dom.find(id="left_form_reviews_items_container")
        right_container = dom.find(id="right_form_reviews_items_container")

        assert left_container is not None, "Expected left_form_reviews_items_container"
        assert right_container is not None, (
            "Expected right_form_reviews_items_container"
        )

    def test_list_items_have_correct_index_in_data_field_path(
        self, review_comparison_client, soup
    ):
        """
        Test that list items have correct indices in data-field-path.

        Left form has 2 reviews, so we should have:
        - reviews[0].rating, reviews[0].comment
        - reviews[1].rating, reviews[1].comment

        Right form has 1 review, so we should have:
        - reviews[0].rating, reviews[0].comment
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all data-field-path values for reviews
        left_paths = []
        right_paths = []

        for elem in dom.find_all(attrs={"data-field-path": re.compile(r"reviews\[")}):
            name = elem.get("name", "")
            path = elem["data-field-path"]

            if name.startswith("left_form_"):
                left_paths.append(path)
            elif name.startswith("right_form_"):
                right_paths.append(path)

        # Left should have indices 0 and 1
        left_indices: set[str] = set()
        for p in left_paths:
            m = re.search(r"reviews\[(\d+)\]", p)
            if m:
                left_indices.add(m.group(1))
        assert "0" in left_indices, (
            f"Expected index 0 in left paths, got {left_indices}"
        )
        assert "1" in left_indices, (
            f"Expected index 1 in left paths, got {left_indices}"
        )

        # Right should have index 0
        right_indices: set[str] = set()
        for p in right_paths:
            m = re.search(r"reviews\[(\d+)\]", p)
            if m:
                right_indices.add(m.group(1))
        assert "0" in right_indices, (
            f"Expected index 0 in right paths, got {right_indices}"
        )

    def test_relative_path_extraction_pattern_for_list_items(self):
        """
        Test the regex pattern used in JavaScript for extracting relative paths.

        The JS uses:
        var listItemPattern = new RegExp('^' + listFieldPath.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') + '\\\\[[^\\\\]]+\\\\]');

        This should match the list field prefix and extract the relative path.

        BUG: The regex escaping in the JavaScript seems overly escaped.
        """
        import re

        list_field_path = "reviews"

        # What the pattern SHOULD be (Python equivalent)
        # Match: "reviews[anything]" and extract what comes after
        correct_pattern = f"^{re.escape(list_field_path)}\\[[^\\]]+\\]"

        test_paths = [
            ("reviews[0].rating", ".rating"),
            ("reviews[0].comment", ".comment"),
            ("reviews[1].rating", ".rating"),
            ("reviews[new_1234567890].rating", ".rating"),
        ]

        for source_path, expected_relative in test_paths:
            match = re.match(correct_pattern, source_path)
            assert match is not None, f"Pattern should match {source_path}"

            relative = source_path[match.end() :]
            assert relative == expected_relative, (
                f"Expected relative path '{expected_relative}' from '{source_path}', got '{relative}'"
            )


class TestCopyLeftIntegration:
    """
    Integration tests for copy-left functionality.

    These tests verify the server-side components that enable copy-left to work.
    The actual copy is done in JavaScript, but these tests verify prerequisites.
    """

    def test_copy_button_targets_correct_side(self, review_comparison_client, soup):
        """
        Test that copy buttons on right form target 'left'.

        With copy_left=True:
        - Right form should have buttons that copy TO left
        - onclick should contain copyTarget='left'
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find the right form wrapper
        right_wrapper = dom.find(id="right_form-inputs-wrapper")
        assert right_wrapper is not None

        # Find copy buttons within right wrapper
        copy_buttons = right_wrapper.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy")
        )

        # All should target 'left'
        for btn in copy_buttons:
            onclick = btn.get("onclick", "")
            assert "'left'" in onclick, (
                f"Expected copy target 'left' in right form button, got: {onclick}"
            )

    def test_copy_button_targets_correct_side_for_copy_right(
        self, review_comparison_client, soup
    ):
        """
        Test that copy buttons on left form target 'right'.

        With copy_right=True:
        - Left form should have buttons that copy TO right
        - onclick should contain copyTarget='right'
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find the left form wrapper
        left_wrapper = dom.find(id="left_form-inputs-wrapper")
        assert left_wrapper is not None

        # Find copy buttons within left wrapper
        copy_buttons = left_wrapper.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy")
        )

        # All should target 'right'
        for btn in copy_buttons:
            onclick = btn.get("onclick", "")
            assert "'right'" in onclick, (
                f"Expected copy target 'right' in left form button, got: {onclick}"
            )

    def test_prefix_globals_are_emitted(self, review_comparison_client, soup):
        """
        Test that global prefix variables are emitted for JavaScript copy.

        The render_inputs should include a script setting:
        - window.__fhpfLeftPrefix
        - window.__fhpfRightPrefix
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find script tags
        scripts = dom.find_all("script")
        script_contents = [s.string or "" for s in scripts]
        all_scripts = "\n".join(script_contents)

        assert "__fhpfLeftPrefix" in all_scripts, (
            "Expected __fhpfLeftPrefix to be set in script"
        )
        assert "__fhpfRightPrefix" in all_scripts, (
            "Expected __fhpfRightPrefix to be set in script"
        )
        assert '"left_form_"' in all_scripts, "Expected left_form_ prefix in script"
        assert '"right_form_"' in all_scripts, "Expected right_form_ prefix in script"
        assert "__fhpfComparisonPrefixes" in all_scripts, (
            "Expected comparison prefix registry in script"
        )
        assert '"review_test"' in all_scripts, (
            "Expected comparison name in prefix registry"
        )

    def test_comparison_grid_has_prefix_data_attrs(
        self, review_comparison_client, soup
    ):
        """
        Test that comparison grid includes data attributes for prefix scoping.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)
        grid = dom.find(id="review_test-comparison-grid")
        assert grid is not None, "Expected comparison grid element"
        assert grid.get("data-fhpf-compare-grid") == "true"
        assert grid.get("data-fhpf-left-prefix") == "left_form_"
        assert grid.get("data-fhpf-right-prefix") == "right_form_"

    def test_copy_buttons_pass_trigger_element(self, review_comparison_client, soup):
        """
        Test that copy buttons pass the trigger element for context resolution.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)
        copy_buttons = dom.find_all("button", onclick=re.compile(r"fhpfPerformCopy"))
        assert copy_buttons, "Expected copy buttons to be rendered"
        assert all(
            re.search(r",\s*this\)\s*;?\s*return false", btn.get("onclick", ""))
            for btn in copy_buttons
        ), "Expected copy handlers to pass the trigger element"


class TestCopyListItemJavaScriptLogic:
    """
    Tests that document the expected JavaScript behavior for list item copying.

    These tests verify the conceptual logic that the JavaScript should follow.
    They help identify potential bugs in the path matching and value copying.
    """

    def test_path_transformation_for_new_item_placeholder(self):
        """
        Document the path transformation when copying to a newly added item.

        Source: reviews[0] on right form
        Target: After clicking "Add Item" on left form

        The new item gets a placeholder ID like "new_1234567890".
        All nested fields should be mapped correctly.
        """
        # Prefixes documented for context:
        # source_prefix = "right_form_", target_prefix = "left_form_"
        source_path_prefix = "reviews[0]"
        target_placeholder = "new_1234567890"
        target_path_prefix = f"reviews[{target_placeholder}]"

        # Field mappings that should occur:
        expected_mappings = [
            # (source_data_field_path, source_name, target_data_field_path, target_name)
            (
                "reviews[0].rating",
                "right_form_reviews_0_rating",
                f"reviews[{target_placeholder}].rating",
                f"left_form_reviews_{target_placeholder}_rating",
            ),
            (
                "reviews[0].comment",
                "right_form_reviews_0_comment",
                f"reviews[{target_placeholder}].comment",
                f"left_form_reviews_{target_placeholder}_comment",
            ),
        ]

        for src_path, src_name, tgt_path, tgt_name in expected_mappings:
            # Verify path transformation
            relative = src_path.replace(source_path_prefix, "")
            computed_target_path = f"{target_path_prefix}{relative}"
            assert computed_target_path == tgt_path, (
                f"Path transform failed: {src_path} -> {computed_target_path}, expected {tgt_path}"
            )

    def test_position_based_copy_for_full_list(self):
        """
        Document the position-based copy logic for full list copying.

        When copying entire "reviews" list:
        - Source item 0 maps to target item 0
        - Source item 1 maps to target item 1
        - etc.

        The JavaScript should extract relative paths and match by position,
        not by absolute indices (which may differ).
        """
        # Source list has items [0, 1, 2] with different values
        # Target list has items [0, 1] with placeholder IDs

        # After copy:
        # - Target[0] should have values from Source[0]
        # - Target[1] should have values from Source[1]
        # - Target[2] should be added and have values from Source[2]

        source_items = [
            {"rating": 5, "comment": "Excellent"},
            {"rating": 4, "comment": "Good"},
            {"rating": 3, "comment": "Average"},
        ]

        # This test documents the expected behavior
        # The actual JavaScript implementation uses performListCopyByPosition
        assert len(source_items) == 3

    def test_relative_path_matching_handles_different_placeholders(self):
        """
        Test that relative path matching works across different placeholder formats.

        Source might have: reviews[0], reviews[1]
        Target might have: reviews[new_123], reviews[new_456]

        The matching should be by relative path (.rating, .comment), not by index.
        """
        # This is the key insight: the JavaScript needs to match by relative path
        # because source and target may have completely different indices/placeholders.

        source_paths = [
            "reviews[0].rating",
            "reviews[0].comment",
            "reviews[1].rating",
            "reviews[1].comment",
        ]

        target_paths = [
            "reviews[new_1234].rating",
            "reviews[new_1234].comment",
            "reviews[new_5678].rating",
            "reviews[new_5678].comment",
        ]

        # Extract relative paths
        def extract_relative(path):
            # Remove "reviews[X]" prefix to get relative path
            match = re.match(r"reviews\[[^\]]+\](.*)", path)
            return match.group(1) if match else None

        source_relatives = [extract_relative(p) for p in source_paths]
        target_relatives = [extract_relative(p) for p in target_paths]

        # All relative paths should match
        assert source_relatives == target_relatives, (
            f"Relative paths should match: {source_relatives} vs {target_relatives}"
        )

    def test_truncation_when_copying_shorter_list_to_longer(self):
        """
        Test that copying a shorter list to a longer list truncates excess items.

        When copying:
        - Source list has 2 items
        - Target list has 5 items

        Expected behavior:
        - Copy source items 0,1 to target items 0,1
        - Remove target items 2,3,4 (excess items)
        - Result: target has exactly 2 items matching source

        This documents the expected contract for performListCopyByPosition.
        The JavaScript must call targetItems[i].remove() for excess items.

        BUG FIX: Prior to 0.3.17, performListCopyByPosition did NOT truncate
        excess items - it only copied matching positions and left extras intact.
        """
        source_items = [
            {"rating": 5, "comment": "Great"},
            {"rating": 4, "comment": "Good"},
        ]
        target_items_before = [
            {"rating": 1, "comment": "Bad"},
            {"rating": 2, "comment": "Poor"},
            {"rating": 3, "comment": "Average"},
            {"rating": 4, "comment": "Good"},
            {"rating": 5, "comment": "Excellent"},
        ]

        # Expected behavior after copy: target matches source length
        expected_target_after = [
            {"rating": 5, "comment": "Great"},  # copied from source[0]
            {"rating": 4, "comment": "Good"},  # copied from source[1]
            # items 2,3,4 should be REMOVED (not left unchanged)
        ]

        assert len(source_items) == 2
        assert len(target_items_before) == 5
        assert len(expected_target_after) == 2, (
            "After copying shorter list to longer, target should be truncated"
        )


class TestCopyDisabledFormInteraction:
    """Tests for copy behavior when target form is disabled."""

    def test_copy_button_not_shown_when_target_disabled(self, soup):
        """
        Test that copy buttons are not shown when target form is disabled.

        If left form is disabled, copy_left should not show buttons on right form.
        """
        left_values = Product(name="Left")
        right_values = Product(name="Right")

        # Left form is disabled
        left_form = PydanticForm(
            "disabled_left",
            Product,
            initial_values=left_values,
            disabled=True,
        )
        right_form = PydanticForm(
            "enabled_right",
            Product,
            initial_values=right_values,
        )

        comp = ComparisonForm(
            "disabled_test",
            left_form,
            right_form,
            copy_left=True,  # Would enable copy to left, but left is disabled
        )

        html = comp.render_inputs().__html__()
        dom = soup(html)

        # Find right wrapper
        right_wrapper = dom.find(id="enabled_right-inputs-wrapper")
        if right_wrapper:
            # Should NOT have copy buttons targeting disabled left
            copy_buttons = right_wrapper.find_all(
                "button", onclick=re.compile(r"fhpfPerformCopy.*'left'")
            )
            assert len(copy_buttons) == 0, (
                "Should not have copy-to-left buttons when left form is disabled"
            )


class TestAddItemButtonForCopy:
    """
    Tests that verify the "Add Item" button has correct attributes for copy.

    The JavaScript copy logic relies on finding the add button via:
    `container.parentElement.querySelector('button[hx-post*="/list/add/"]')`
    """

    def test_add_button_has_correct_hx_post_for_list(
        self, review_comparison_client, soup
    ):
        """
        Test that the Add Item button has the expected hx-post attribute.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find add buttons for reviews list
        add_buttons = dom.find_all(
            "button", attrs={"hx-post": re.compile(r"/list/add/reviews")}
        )

        # Should have add buttons for both left and right forms
        assert len(add_buttons) >= 2, (
            f"Expected add buttons for reviews on both forms, found {len(add_buttons)}"
        )

        # Verify the button paths
        for btn in add_buttons:
            hx_post = btn.get("hx-post")
            assert "/list/add/reviews" in hx_post, f"Unexpected hx-post: {hx_post}"

    def test_add_button_is_sibling_or_child_of_container_parent(
        self, review_comparison_client, soup
    ):
        """
        Test that the Add Item button is findable from the container's parent.

        The JavaScript uses: `targetContainer.parentElement.querySelector('button[hx-post*="/list/add/"]')`
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find the left form's reviews container
        left_container = dom.find(id="left_form_reviews_items_container")
        assert left_container is not None, "Expected left_form_reviews_items_container"

        # Navigate to parent
        parent = left_container.parent
        assert parent is not None, "Container should have a parent element"

        # Find add button from parent
        add_button = parent.find(
            "button", attrs={"hx-post": re.compile(r"/list/add/reviews")}
        )
        assert add_button is not None, (
            "Add button should be findable from container's parent"
        )


class TestHTMXAddItemForCopy:
    """
    Tests that verify adding items via HTMX produces correct structure for copying.
    """

    def test_newly_added_item_has_id_attribute(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that newly added list items have an id attribute.

        The JavaScript needs this to target the swap:
        `htmx.ajax('POST', addUrl, { target: '#' + insertBeforeElement.id, ... })`
        """
        client, comp = review_comparison_client

        # Add item to left form's reviews
        response = client.post(
            "/form/left_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # The response should be a list item with an id
        list_item = dom.find("li")
        assert list_item is not None, "Expected a list item in response"
        assert list_item.has_attr("id"), "List item should have an id attribute"

        item_id = list_item.get("id")
        assert item_id, "List item id should not be empty"
        assert "left_form_reviews" in item_id, (
            f"List item id should contain form and field name, got: {item_id}"
        )

    def test_newly_added_item_has_data_field_path_with_new_placeholder(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that inputs in newly added items have data-field-path with new_ placeholder.
        """
        client, comp = review_comparison_client

        # Add item to left form's reviews
        response = client.post(
            "/form/left_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all elements with data-field-path
        path_elements = dom.find_all(attrs={"data-field-path": True})
        assert len(path_elements) > 0, "Expected elements with data-field-path"

        # All paths should contain new_TIMESTAMP placeholder
        for elem in path_elements:
            path = elem["data-field-path"]
            assert "new_" in path, f"Expected 'new_' placeholder in path, got: {path}"
            # Verify pattern: reviews[new_TIMESTAMP].field or reviews[new_TIMESTAMP]
            assert re.match(r"reviews\[new_\d+\]", path), (
                f"Expected reviews[new_TIMESTAMP]... pattern, got: {path}"
            )

    def test_newly_added_item_name_attributes_match_data_field_path(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that name attributes are consistent with data-field-path.

        For data-field-path="reviews[new_123].rating"
        name should be "left_form_reviews_new_123_rating"
        """
        client, comp = review_comparison_client

        # Add item to left form's reviews
        response = client.post(
            "/form/left_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Find input elements
        inputs = dom.find_all(["input", "textarea"])
        for inp in inputs:
            if not inp.has_attr("data-field-path") or not inp.has_attr("name"):
                continue

            path = inp["data-field-path"]
            name = inp["name"]

            # Extract placeholder from path
            path_match = re.search(r"reviews\[(new_\d+)\]", path)
            if path_match:
                placeholder = path_match.group(1)

                # Name should contain the same placeholder
                assert placeholder in name, (
                    f"Name '{name}' should contain placeholder '{placeholder}' from path '{path}'"
                )


class TestCopyPathMappingEdgeCases:
    """
    Tests for edge cases in path mapping during copy.
    """

    def test_nested_list_path_copy_button(self, soup):
        """
        Test copy button path for nested lists like addresses[0].tags.

        BUG HYPOTHESIS: If the list is nested (e.g., addresses[0].tags),
        the JavaScript may fail to construct the correct container ID.
        """

        class AddressWithTags(BaseModel):
            street: str = ""
            tags: List[str] = Field(default_factory=list)

        class PersonWithAddresses(BaseModel):
            name: str = ""
            addresses: List[AddressWithTags] = Field(default_factory=list)

        left_values = PersonWithAddresses(
            name="Left",
            addresses=[
                AddressWithTags(street="123 Main", tags=["home", "primary"]),
            ],
        )
        right_values = PersonWithAddresses(
            name="Right",
            addresses=[
                AddressWithTags(street="456 Oak", tags=["work"]),
            ],
        )

        left_form = PydanticForm(
            "nested_left", PersonWithAddresses, initial_values=left_values
        )
        right_form = PydanticForm(
            "nested_right", PersonWithAddresses, initial_values=right_values
        )

        comp = ComparisonForm(
            "nested_test",
            left_form,
            right_form,
            copy_left=True,
        )

        html = comp.render_inputs().__html__()
        dom = soup(html)

        # Find copy buttons for nested tags (addresses[0].tags)
        nested_copy_buttons = dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy.*addresses\[0\]\.tags")
        )

        # Should have copy buttons for nested lists
        assert len(nested_copy_buttons) > 0, (
            "Expected copy buttons for nested tags list"
        )

    def test_simple_list_string_path_copy_button(self, review_comparison_client, soup):
        """
        Test that simple List[str] fields (tags) have correct copy button paths.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy buttons for tags (List[str])
        tags_copy_buttons = dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy\('tags',")
        )

        # Should have copy buttons for tags field
        assert len(tags_copy_buttons) >= 2, (
            "Expected copy buttons for tags field on both forms"
        )


class TestContainerIdConstruction:
    """
    Tests to verify the container ID construction matches JavaScript expectations.

    JavaScript constructs ID as:
    `targetPrefix.replace(/_$/, '') + '_' + listFieldPath + '_items_container'`
    """

    def test_list_container_id_format(self, review_comparison_client, soup):
        """
        Test that list containers follow the expected ID format.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Expected container IDs based on form names and field
        expected_ids = [
            "left_form_reviews_items_container",
            "right_form_reviews_items_container",
            "left_form_tags_items_container",
            "right_form_tags_items_container",
        ]

        for expected_id in expected_ids:
            container = dom.find(id=expected_id)
            assert container is not None, f"Expected container with id='{expected_id}'"

    def test_prefix_trailing_underscore_handling(self):
        """
        Test that the prefix handling in JavaScript correctly handles trailing underscore.

        JavaScript: `targetPrefix.replace(/_$/, '')`

        For prefix "left_form_", this should produce "left_form".
        """
        # Test cases for JavaScript's replace(/_$/, '')
        test_cases = [
            ("left_form_", "left_form"),
            ("right_form_", "right_form"),
            ("my_form_prefix_", "my_form_prefix"),
            ("no_trailing", "no_trailing"),  # Edge case: no trailing underscore
        ]

        for prefix, expected in test_cases:
            # Simulate JavaScript's replace(/_$/, '')
            # In Python: rstrip doesn't work the same, need regex
            import re

            result = re.sub(r"_$", "", prefix)
            assert result == expected, (
                f"Prefix '{prefix}' should become '{expected}', got '{result}'"
            )


class TestJavaScriptRegexPatterns:
    """
    Tests that validate the regex patterns used in JavaScript would work correctly.

    These tests simulate what the JavaScript does to help identify potential bugs.
    """

    def test_list_item_pattern_construction_in_python(self):
        """
        Test the JavaScript regex pattern construction logic in Python.

        JavaScript code (line 496):
        var listItemPattern = new RegExp(
            '^' + listFieldPath.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&') +
            '\\\\[[^\\\\]]+\\\\]'
        );

        The Python string contains the JavaScript code, so we need to account for
        double-escaping. This test validates the INTENDED pattern.

        BUG FOUND: The regex in the Python string is overly escaped.
        The JavaScript pattern should be: ^reviews\\[[^\\]]+\\]
        Which matches: reviews[anything]

        But the actual pattern from the Python string may be wrong.
        """
        list_field_path = "reviews"

        # What the JavaScript SHOULD create (correctly escaped for RegExp constructor)
        # Pattern string: ^reviews\\[[^\\]]+\\]
        # Which becomes regex: ^reviews\[[^\]]+\]
        # Which matches: reviews followed by [anything]

        # Test the correct pattern
        import re

        # The correct pattern to match "reviews[0]", "reviews[new_123]", etc.
        correct_pattern = f"^{re.escape(list_field_path)}\\[[^\\]]+\\]"

        test_cases = [
            ("reviews[0]", True),
            ("reviews[1]", True),
            ("reviews[new_123456]", True),
            ("reviews[0].rating", True),  # Should match the prefix
            ("reviews", False),  # No brackets
            ("other[0]", False),  # Different field
        ]

        for path, should_match in test_cases:
            match = re.match(correct_pattern, path)
            matched = match is not None
            assert matched == should_match, (
                f"Pattern '{correct_pattern}' should {'match' if should_match else 'not match'} "
                f"'{path}', but it {'did' if matched else 'did not'}"
            )

    def test_relative_path_extraction_from_full_path(self):
        """
        Test extracting relative path by removing list prefix.

        Given: reviews[0].rating
        List prefix: reviews[0]
        Expected relative: .rating
        """
        import re

        test_cases = [
            # (full_path, list_field_path, expected_relative)
            ("reviews[0].rating", "reviews", ".rating"),
            ("reviews[0].comment", "reviews", ".comment"),
            ("reviews[new_123].rating", "reviews", ".rating"),
            ("addresses[0].street", "addresses", ".street"),
            ("addresses[0].tags[0]", "addresses", ".tags[0]"),
        ]

        for full_path, list_field_path, expected_relative in test_cases:
            # Build pattern (what JavaScript should do)
            pattern = f"^{re.escape(list_field_path)}\\[[^\\]]+\\]"

            match = re.match(pattern, full_path)
            assert match is not None, f"Pattern should match {full_path}"

            # Extract relative path
            relative = full_path[match.end() :]
            assert relative == expected_relative, (
                f"Expected relative '{expected_relative}' from '{full_path}', got '{relative}'"
            )

    def test_javascript_string_escaping_in_python_source(self):
        r"""
        Test that helps understand the escaping layers.

        In the Python source file, JavaScript code is inside triple-quoted strings.
        This test documents the escaping behavior.

        Python source (in triple-quoted string): '\\\\[[^\\\\]]+\\\\]'
        This is 4 backslashes, which in Python becomes 2 backslashes in the string value.
        So the string value sent to browser is: \\[[^\\]]+\\]

        When JavaScript's new RegExp() parses this string:
        Each \\ becomes a single \
        So the final regex pattern is: \[[^\]]+\]

        Regex meaning: literal [ followed by one-or-more non-] chars followed by literal ]
        """
        # In Python, '\\\\' in a regular string literal gives us '\\'
        # Let's verify with a raw string comparison
        python_source_fragment = "\\\\[[^\\\\]]+\\\\]"

        # The actual string value (what gets sent to browser)
        # Each pair of backslashes becomes one
        assert python_source_fragment == r"\\[[^\\]]+\\]", (
            "Python string should have escaped backslashes"
        )

        # When JavaScript receives this string and passes to new RegExp():
        # '\\[' becomes '\[' (regex escape for literal [)
        # '[^\\]]+' becomes '[^\]]+' (character class not containing ])
        # '\\]' becomes '\]' (regex escape for literal ])

        # The final JavaScript regex pattern matches: [anything]
        # Let's test the equivalent Python pattern
        import re

        # This is what the JavaScript regex effectively does
        js_equivalent_pattern = r"\[[^\]]+\]"

        # Test it works
        assert re.match(js_equivalent_pattern, "[0]"), "Pattern should match [0]"
        assert re.match(js_equivalent_pattern, "[new_123]"), (
            "Pattern should match [new_123]"
        )
        assert not re.match(js_equivalent_pattern, "[]"), (
            "Pattern should not match empty brackets"
        )


class TestJavaScriptPatternBugs:
    """
    Tests that demonstrate potential bugs in the JavaScript regex patterns.
    """

    def test_python_source_regex_has_extra_escaping(self):
        """
        BUG: The Python source has extra backslash escaping that may cause issues.

        Looking at line 496 in comparison_form.py:
        The pattern '\\\\[[^\\\\]]+\\\\]' seems overly escaped.

        Let's verify what the actual JavaScript would receive.
        """
        # The raw Python source text (inside triple-quoted string)
        # is: '\\\\[[^\\\\]]+\\\\]'
        #
        # When Python parses this string literal:
        # Each \\\\ becomes \\ (four backslashes become two)
        #
        # So the resulting string is: \\[[^\\]]+\\]
        #
        # When this is sent to the browser and JavaScript's new RegExp() parses it:
        # Each \\ becomes \ (two backslashes become one)
        #
        # So the final regex is: \[[^\]]+\]
        #
        # This SHOULD be correct!

        # Let's verify the intended behavior
        import re

        # What the JavaScript regex should match:
        # \[ -> literal [
        # [^\]]+ -> one or more characters that are not ]
        # \] -> literal ]
        js_pattern_meaning = r"\[[^\]]+\]"

        assert re.match(js_pattern_meaning, "[0]")
        assert re.match(js_pattern_meaning, "[new_123]")
        assert re.match(js_pattern_meaning, "[anything_here]")

    def test_character_class_escaping_in_replace_pattern(self):
        """
        Test the character class used for escaping special regex characters.

        JavaScript: /[.*+?^${}()|[\\]\\\\]/g

        This should match: . * + ? ^ $ { } ( ) | [ ] \\
        """
        # The Python source contains: /[.*+?^${}()|[\\]\\\\]/g
        #
        # After Python string parsing (inside triple-quoted string):
        # [\\] becomes [\] (escaping in Python)
        # \\\\ becomes \\ (escaping in Python)
        #
        # So JavaScript sees: /[.*+?^${}()|[\]\\]/g
        #
        # In JavaScript regex character class:
        # [\] is an escaped ] (literal ])
        # \\ is an escaped \ (literal \)
        #
        # So the character class contains: . * + ? ^ $ { } ( ) | [ ] \

        # Test in Python with equivalent pattern
        import re

        # Characters that should be escaped for regex
        special_chars = r".*+?^${}()|[]\\"

        # Build a Python pattern that matches these characters
        # (Note: Python regex character classes have different escaping rules)
        py_pattern = r"[.*+?^${}()|[\]\\]"

        for char in special_chars:
            # Each special char should match the pattern
            match = re.search(py_pattern, char)
            assert match is not None, f"Pattern should match special char '{char}'"


class TestIsListItemPathBug:
    """
    Regression tests for isListItemPath() detection.

    These tests ensure we correctly detect full list items (including new_
    placeholders) and ignore subfields.
    """

    def test_isListItemPath_should_match_numeric_index(self):
        """
        Test that isListItemPath matches numeric indices.
        This test PASSES - numeric indices work.
        """
        import re

        # The JavaScript pattern: /\[\d+\]/
        pattern = r"\[\d+\]"

        # These should match (and do)
        assert re.search(pattern, "reviews[0]")
        assert re.search(pattern, "reviews[1]")
        assert re.search(pattern, "reviews[99]")
        assert re.search(pattern, "addresses[0].street")

    def test_isListItemPath_should_match_new_placeholder_index(self):
        """
        isListItemPath should match full items with new_ placeholder indices.
        """
        import re

        # The JavaScript pattern: /\[(\d+|new_\d+)\]$/
        current_pattern = r"\[(\d+|new_\d+)\]$"

        # Full item paths should match
        assert re.search(current_pattern, "reviews[new_1234567890]")
        assert re.search(current_pattern, "addresses[new_123]")

        # Subfield paths should not match
        assert not re.search(current_pattern, "addresses[new_123].street")

    def test_correct_pattern_would_match_both_numeric_and_placeholder(self):
        """
        Demonstrate what the correct pattern should be.

        The pattern should match both:
        - [0], [1], [99] (numeric)
        - [new_1234567890] (placeholder)
        """
        import re

        # Correct pattern that matches both numeric and new_ placeholders
        correct_pattern = r"\[(\d+|new_\d+)\]"

        # Numeric indices
        assert re.search(correct_pattern, "reviews[0]")
        assert re.search(correct_pattern, "reviews[99]")

        # Placeholder indices
        assert re.search(correct_pattern, "reviews[new_1234567890]")
        assert re.search(correct_pattern, "addresses[new_123].street")


class TestExtractListFieldPathBug:
    """
    Regression tests for extractListFieldPath() behavior.
    """

    def test_extractListFieldPath_works_for_numeric_indices(self):
        """
        Test that extractListFieldPath works for numeric indices.
        This test PASSES.
        """
        import re

        # The JavaScript pattern: /\[\d+\].*$/
        pattern = r"\[\d+\].*$"

        # Test extraction
        assert re.sub(pattern, "", "reviews[0]") == "reviews"
        assert re.sub(pattern, "", "addresses[0].street") == "addresses"

    def test_extractListFieldPath_should_work_for_new_placeholders(self):
        """
        extractListFieldPath should work for new_ placeholders.
        """
        import re

        # The JavaScript pattern: /\[(\d+|new_\d+)\].*$/
        current_pattern = r"\[(\d+|new_\d+)\].*$"

        # These should extract "reviews"
        result = re.sub(current_pattern, "", "reviews[new_1234567890]")
        assert result == "reviews"

    def test_correct_pattern_handles_both(self):
        """
        Demonstrate what the correct pattern should be.
        """
        import re

        # Correct pattern that handles both numeric and placeholder indices
        correct_pattern = r"\[(\d+|new_\d+)\].*$"

        # Numeric
        assert re.sub(correct_pattern, "", "reviews[0]") == "reviews"
        assert re.sub(correct_pattern, "", "addresses[5].street") == "addresses"

        # Placeholder
        assert re.sub(correct_pattern, "", "reviews[new_1234567890]") == "reviews"
        assert re.sub(correct_pattern, "", "addresses[new_123].street") == "addresses"


class TestExtractListIndexBug:
    """
    Regression tests for extractListIndex() behavior.
    """

    def test_extractListIndex_works_for_numeric(self):
        """
        Test that extractListIndex works for numeric indices.
        This test PASSES.
        """
        import re

        # The JavaScript pattern: /\[(\d+)\]/
        pattern = r"\[(\d+)\]"

        # Should extract the number
        match = re.search(pattern, "reviews[5]")
        assert match and match.group(1) == "5"

        match = re.search(pattern, "addresses[0].street")
        assert match and match.group(1) == "0"

    def test_extractListIndex_should_work_for_new_placeholders(self):
        """
        extractListIndex should return something useful for placeholders.
        """
        import re

        # The JavaScript pattern: /\[(\d+|new_\d+)\]/
        current_pattern = r"\[(\d+|new_\d+)\]"

        match = re.search(current_pattern, "reviews[new_1234567890]")
        assert match is not None
        assert match.group(1) == "new_1234567890"


class TestCopyNewlyAddedItemBug:
    """
    Regression tests for copying newly added items.
    """

    def test_copy_button_path_for_newly_added_item(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that copy buttons on newly added items have paths with new_ placeholder.
        """
        client, comp = review_comparison_client

        # Add a new item to the right form
        response = client.post(
            "/form/right_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy buttons in the new item
        copy_buttons = dom.find_all("button", onclick=re.compile(r"fhpfPerformCopy"))

        # The copy button path should contain new_ placeholder
        for btn in copy_buttons:
            onclick = btn.get("onclick", "")
            # Extract the path from onclick
            match = re.search(r"fhpfPerformCopy\('([^']+)'", onclick)
            if match:
                path = match.group(1)
                # The path should be like "reviews[new_1234567890]"
                assert "new_" in path, (
                    f"Copy button path should contain 'new_' placeholder, got: {path}"
                )

    def test_newly_added_item_detected_as_list_item(self):
        """
        Paths with new_ placeholder should be detected as list items.
        """
        import re

        # The current JavaScript pattern
        current_pattern = r"\[(\d+|new_\d+)\]$"

        # This path would be passed to isListItemPath after adding an item
        new_item_path = "reviews[new_1234567890]"

        assert re.search(current_pattern, new_item_path)


class TestFullListCopyBug:
    """
    Regression tests for full list copy functionality.

    When copying a full list (e.g., path="reviews"), the JavaScript:
    1. Detects both source and target have list containers
    2. Aligns list lengths (adds items if needed)
    3. Copies by position using performListCopyByPosition()
    """

    def test_full_list_copy_path_is_field_name_only(
        self, review_comparison_client, soup
    ):
        """
        Test that full list copy buttons have just the field name as path.
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy buttons for the full reviews list
        copy_buttons = dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy\('reviews',")
        )

        assert len(copy_buttons) >= 1, "Expected at least one full-list copy button"

    def test_relative_path_extraction_for_list_items(self):
        """
        Validate relative path extraction using bracket positions.

        This mirrors the performListCopyByPosition logic that uses
        indexOf '[' and ']' to derive the relative path.
        """

        def extract_relative(path: str, list_field_path: str) -> str:
            bracket_start = path.find("[", len(list_field_path))
            bracket_end = path.find("]", bracket_start)
            return path[bracket_end + 1 :] if bracket_end >= 0 else ""

        test_cases = [
            ("reviews[0].rating", "reviews", ".rating"),
            ("reviews[0].comment", "reviews", ".comment"),
            ("reviews[new_123].rating", "reviews", ".rating"),
            ("addresses[0].street", "addresses", ".street"),
            ("addresses[0].tags[0]", "addresses", ".tags[0]"),
        ]

        for path, list_field_path, expected in test_cases:
            assert extract_relative(path, list_field_path) == expected


class TestPerformStandardCopyPathMapping:
    """
    Tests for path mapping in performStandardCopy function.

    When copying from reviews[0] to reviews[new_123], the function needs to:
    1. Find source inputs with data-field-path starting with "reviews[0]"
    2. Map paths: reviews[0].rating -> reviews[new_123].rating
    3. Find target inputs by the mapped path
    """

    def test_path_prefix_matching_logic(self):
        """
        Test the path prefix matching logic used in performStandardCopy.

        The JavaScript checks:
        - fp === sourcePathPrefix
        - fp.startsWith(sourcePathPrefix + '.')
        - fp.startsWith(sourcePathPrefix + '[')
        """
        source_path_prefix = "reviews[0]"

        # Paths that should match
        should_match = [
            "reviews[0]",  # Exact match
            "reviews[0].rating",  # Starts with prefix + '.'
            "reviews[0].comment",
            # Note: reviews[0][something] would also match (starts with prefix + '[')
        ]

        # Paths that should NOT match
        should_not_match = [
            "reviews[1]",  # Different index
            "reviews[1].rating",
            "reviews",  # No index
            "other[0]",  # Different field
        ]

        for path in should_match:
            matches = (
                path == source_path_prefix
                or path.startswith(source_path_prefix + ".")
                or path.startswith(source_path_prefix + "[")
            )
            assert matches, f"Path '{path}' should match prefix '{source_path_prefix}'"

        for path in should_not_match:
            matches = (
                path == source_path_prefix
                or path.startswith(source_path_prefix + ".")
                or path.startswith(source_path_prefix + "[")
            )
            assert not matches, (
                f"Path '{path}' should NOT match prefix '{source_path_prefix}'"
            )

    def test_path_remapping_from_numeric_to_placeholder(self):
        """
        Test path remapping from numeric index to placeholder index.

        When copying reviews[0] to reviews[new_123]:
        - reviews[0].rating -> reviews[new_123].rating
        - reviews[0].comment -> reviews[new_123].comment
        """
        source_path_prefix = "reviews[0]"
        target_path_prefix = "reviews[new_1234567890]"

        test_cases = [
            ("reviews[0]", "reviews[new_1234567890]"),
            ("reviews[0].rating", "reviews[new_1234567890].rating"),
            ("reviews[0].comment", "reviews[new_1234567890].comment"),
        ]

        for source_fp, expected_target_fp in test_cases:
            # Simulate the JavaScript logic
            if source_fp == source_path_prefix:
                target_fp = target_path_prefix
            elif source_fp.startswith(source_path_prefix + "."):
                target_fp = target_path_prefix + source_fp[len(source_path_prefix) :]
            elif source_fp.startswith(source_path_prefix + "["):
                target_fp = target_path_prefix + source_fp[len(source_path_prefix) :]
            else:
                target_fp = source_fp

            assert target_fp == expected_target_fp, (
                f"Expected '{expected_target_fp}', got '{target_fp}'"
            )


class TestHTMXSwapTiming:
    """
    Tests related to HTMX swap timing issues that could cause copy failures.

    The JavaScript copy logic waits for HTMX to settle before copying.
    Race conditions or timing issues could cause failures.
    """

    def test_add_item_response_is_valid_html(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that the add item response is valid HTML that HTMX can swap.
        """
        client, comp = review_comparison_client

        response = client.post(
            "/form/left_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Should have a root element (li)
        root = dom.find("li")
        assert root is not None, "Response should have an <li> root element"

        # Root should have an ID for HTMX targeting
        assert root.has_attr("id"), "Root element should have an id attribute"

    def test_add_item_response_has_accordion_structure(
        self, review_comparison_client, htmx_headers, soup
    ):
        """
        Test that added items have proper accordion structure for copy.

        The JavaScript expects list items to have .uk-accordion-content
        for state management.
        """
        client, comp = review_comparison_client

        response = client.post(
            "/form/left_form/list/add/reviews",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Should have accordion content div
        accordion_content = dom.find(class_="uk-accordion-content")
        assert accordion_content is not None, (
            "Added item should have .uk-accordion-content for proper UI"
        )


class TestCopySubfieldVsFullItemBug:
    """
    Regression tests for distinguishing subfields vs full items during copy.

    - `reviews[0]` (full item) → Add new item to target, copy all fields
    - `reviews[0].rating` (subfield) → Update target's reviews[0].rating in-place
    """

    def test_subfield_path_is_detected_as_list_item(self):
        """
        Document the current behavior: subfields ARE detected as list items.

        This is technically correct - reviews[0].rating IS within a list item.
        The bug is in how it's HANDLED, not how it's detected.
        """
        import re

        pattern = r"\[\d+\]"

        # Full item path
        assert re.search(pattern, "reviews[0]"), "Full item should match"

        # Subfield path - also matches!
        assert re.search(pattern, "reviews[0].rating"), "Subfield also matches"
        assert re.search(pattern, "reviews[0].comment"), "Subfield also matches"

    def test_full_item_vs_subfield_path_distinction(self):
        """
        Demonstrate how to distinguish full item paths from subfield paths.

        Full item: reviews[0] (ends with ])
        Subfield: reviews[0].rating (has content after ])
        """
        import re

        # Full item pattern: ends with [index]
        full_item_pattern = r"\[\d+\]$"

        # Test cases
        full_items = ["reviews[0]", "addresses[1]", "items[99]"]
        subfields = ["reviews[0].rating", "addresses[1].street", "items[0].nested.deep"]

        for path in full_items:
            assert re.search(full_item_pattern, path), (
                f"'{path}' should be detected as full item"
            )

        for path in subfields:
            assert not re.search(full_item_pattern, path), (
                f"'{path}' should NOT be detected as full item (it's a subfield)"
            )

    def test_subfield_copy_should_not_add_new_item(self):
        """
        Copying a subfield should update existing item, not add new.
        """
        import re

        # Subfield path
        subfield_path = "reviews[0].rating"

        # Full items end with the index, subfields continue after the index
        is_full_item = bool(re.search(r"\[(\d+|new_\d+)\]$", subfield_path))
        is_subfield = bool(re.search(r"\[(\d+|new_\d+)\]\.", subfield_path))

        assert not is_full_item
        assert is_subfield

    def test_copy_button_path_for_subfield(self, review_comparison_client, soup):
        """
        Test that copy buttons on subfields have the full subfield path.

        e.g., reviews[0].rating should have path "reviews[0].rating"
        """
        client, comp = review_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy buttons for subfields (paths containing both [index] and .)
        subfield_copy_buttons = dom.find_all(
            "button", onclick=re.compile(r"fhpfPerformCopy\('reviews\[\d+\]\.[^']+',")
        )

        # Should have copy buttons for subfields like reviews[0].rating
        assert len(subfield_copy_buttons) > 0, (
            "Expected copy buttons for subfields like reviews[0].rating"
        )

        # Verify paths
        for btn in subfield_copy_buttons:
            onclick = btn.get("onclick", "")
            match = re.search(r"fhpfPerformCopy\('([^']+)'", onclick)
            if match:
                path = match.group(1)
                # Should be a subfield path
                assert re.search(r"\[\d+\]\.", path), (
                    f"Expected subfield path with [index]., got: {path}"
                )

    def test_correct_behavior_for_subfield_copy(self):
        """
        Document what the correct behavior SHOULD be for subfield copy.

        When copying reviews[0].rating from right to left:
        1. Detect that this is a SUBFIELD (has content after [index])
        2. Find the corresponding item in target by index (reviews[0])
        3. Update just the subfield (rating) in the target item
        4. Do NOT add a new item

        This is different from full item copy (reviews[0]):
        1. Detect that this is a FULL ITEM (ends with [index])
        2. Add a new item to target list
        3. Copy all fields from source item to new target item
        """
        import re

        def get_copy_behavior(path: str) -> str:
            """Determine correct copy behavior based on path structure."""
            # Check if path ends with [index] (full item)
            if re.search(r"\[\d+\]$", path):
                return "add_new_item"
            # Check if path has [index] followed by more content (subfield)
            elif re.search(r"\[\d+\]\.", path):
                return "update_existing_subfield"
            # No index at all (full list or scalar field)
            else:
                return "standard_copy"

        # Test cases
        assert get_copy_behavior("reviews[0]") == "add_new_item"
        assert get_copy_behavior("reviews[1]") == "add_new_item"
        assert get_copy_behavior("reviews[0].rating") == "update_existing_subfield"
        assert get_copy_behavior("reviews[0].comment") == "update_existing_subfield"
        assert get_copy_behavior("reviews") == "standard_copy"
        assert get_copy_behavior("name") == "standard_copy"


class TestSubfieldCopyPathMapping:
    """
    Tests for how subfield paths should be mapped during copy.

    When copying reviews[0].rating from right to left:
    - Source path: reviews[0].rating
    - Target path: reviews[0].rating (SAME index, not a new placeholder)

    The target should be the EXISTING item at the same index, not a new item.
    """

    def test_subfield_path_should_map_to_same_index(self):
        """
        Test that subfield copy should target the same index in target list.
        """
        source_path = "reviews[0].rating"

        # Expected target path: same index, same field
        expected_target_path = "reviews[0].rating"

        # NOT a new placeholder - we're updating existing item
        assert expected_target_path == source_path, (
            "Subfield copy should target same index, not create new"
        )

    def test_subfield_copy_when_target_item_exists(self):
        """
        Document correct behavior when target item exists at same index.

        Scenario: Both left and right have reviews[0]
        Action: Copy reviews[0].rating from right to left
        Expected: Left's reviews[0].rating is updated
        """
        # Source (right form)
        source_values = {"reviews": [{"rating": 5, "comment": "Great"}]}

        # Target (left form) - item exists at index 0
        target_values = {"reviews": [{"rating": 3, "comment": "OK"}]}

        # After copying reviews[0].rating from right to left:
        expected_target = {"reviews": [{"rating": 5, "comment": "OK"}]}

        # Only rating changed, comment stays the same
        assert (
            expected_target["reviews"][0]["rating"]
            == source_values["reviews"][0]["rating"]
        )
        assert (
            expected_target["reviews"][0]["comment"]
            == target_values["reviews"][0]["comment"]
        )

    def test_subfield_copy_when_target_item_missing(self):
        """
        Document behavior when target doesn't have item at that index.

        Scenario: Right has reviews[2], left only has reviews[0], reviews[1]
        Action: Copy reviews[2].rating from right to left
        Options:
        1. Do nothing (index doesn't exist) - safest
        2. Add items until index exists, then update - more complex
        3. Error/warning to user
        """
        # This is an edge case that needs design decision
        # For now, document that it's undefined behavior
        pass

    def test_isListItemPath_should_return_false_for_subfields(self):
        """
        isListItemPath should only return true for FULL item paths.
        """
        import re

        # Correct pattern for FULL items only
        correct_full_item_pattern = r"\[(\d+|new_\d+)\]$"

        # Full item - should return True
        assert re.search(correct_full_item_pattern, "reviews[0]"), (
            "Full item should match"
        )

        # Subfield - should return False (but current impl returns True)
        assert not re.search(correct_full_item_pattern, "reviews[0].rating"), (
            "Subfield should NOT match full item pattern"
        )


class TestListItemVsSubfieldDetection:
    """
    Tests to document the correct detection logic for list items vs subfields.
    """

    def test_detection_patterns(self):
        """
        Document the different path patterns and how they should be handled.
        """
        import re

        test_cases = [
            # (path, is_full_list_item, is_subfield, is_list_field, description)
            ("reviews", False, False, True, "Full list field"),
            ("reviews[0]", True, False, False, "Full list item"),
            ("reviews[1]", True, False, False, "Full list item at index 1"),
            ("reviews[0].rating", False, True, False, "Subfield of list item"),
            ("reviews[0].comment", False, True, False, "Subfield of list item"),
            ("reviews[0].nested.deep", False, True, False, "Deeply nested subfield"),
            ("name", False, False, False, "Scalar field"),
            ("address.street", False, False, False, "Nested scalar field"),
        ]

        # Patterns for detection
        full_item_pattern = r"\[(\d+|new_\d+)\]$"  # Ends with [index]
        subfield_pattern = r"\[(\d+|new_\d+)\]\."  # Has [index] followed by .

        for path, is_full_item, is_subfield, is_list_field, desc in test_cases:
            detected_full = bool(re.search(full_item_pattern, path))
            detected_sub = bool(re.search(subfield_pattern, path))

            assert detected_full == is_full_item, (
                f"'{path}' ({desc}): expected is_full_item={is_full_item}, got {detected_full}"
            )
            assert detected_sub == is_subfield, (
                f"'{path}' ({desc}): expected is_subfield={is_subfield}, got {detected_sub}"
            )

    def test_proposed_fix_for_isListItemPath(self):
        """
        Document the proposed fix for isListItemPath function.

        Current (buggy):
        function isListItemPath(pathPrefix) {
          return /[\\d+]/.test(pathPrefix);
        }

        Proposed fix:
        function isListItemPath(pathPrefix) {
          // Only match full list items, not subfields
          return /[(\\d+|new_\\d+)]$/.test(pathPrefix);
        }

        This would also need a new function for subfield detection:
        function isListSubfieldPath(pathPrefix) {
          return /[(\\d+|new_\\d+)]\\./.test(pathPrefix);
        }
        """
        import re

        # Current buggy pattern (documented): r'\[\d+\]'
        # Fixed pattern for full items only
        fixed_full_item_pattern = r"\[(\d+|new_\d+)\]$"

        # New pattern for subfields
        subfield_pattern = r"\[(\d+|new_\d+)\]\."

        # Test full items
        for path in ["reviews[0]", "reviews[1]", "items[new_123]"]:
            assert re.search(fixed_full_item_pattern, path), f"Should match: {path}"
            assert not re.search(subfield_pattern, path), (
                f"Should not match subfield: {path}"
            )

        # Test subfields
        for path in ["reviews[0].rating", "items[new_123].name"]:
            assert not re.search(fixed_full_item_pattern, path), (
                f"Should not match full: {path}"
            )
            assert re.search(subfield_pattern, path), f"Should match subfield: {path}"


class TestNestedBaseModelWithMultipleLists:
    """
    Tests for BaseModels that have multiple List fields at the same level.

    This can cause selector confusion when multiple add buttons exist as siblings.
    """

    @pytest.fixture
    def multi_list_models(self):
        """
        Create a model with multiple List fields at the same level.
        """

        class Person(BaseModel):
            """Person with multiple list fields."""

            name: str = ""
            emails: List[str] = Field(default_factory=list)
            phones: List[str] = Field(default_factory=list)
            addresses: List[str] = Field(default_factory=list)

        class Team(BaseModel):
            """Team with list of people (each having multiple lists)."""

            team_name: str = ""
            members: List[Person] = Field(default_factory=list)

        return {"Person": Person, "Team": Team}

    @pytest.fixture
    def multi_list_comparison_client(self, multi_list_models):
        """Create a ComparisonForm with multiple sibling lists."""
        from fh_pydantic_form.comparison_form import ComparisonForm, comparison_form_js

        Person = multi_list_models["Person"]
        Team = multi_list_models["Team"]

        left_values = Team(
            team_name="Left Team",
            members=[
                Person(
                    name="Alice",
                    emails=["alice@example.com"],
                    phones=["123-456"],
                    addresses=["123 Main St"],
                ),
            ],
        )

        right_values = Team(
            team_name="Right Team",
            members=[
                Person(
                    name="Bob",
                    emails=["bob@example.com"],
                    phones=["789-012"],
                    addresses=["456 Oak Ave"],
                ),
            ],
        )

        left_form = PydanticForm("multi_left", Team, initial_values=left_values)
        right_form = PydanticForm("multi_right", Team, initial_values=right_values)

        comp = ComparisonForm(
            "multi_test",
            left_form,
            right_form,
            copy_left=True,
            copy_right=True,
        )

        app, rt = fh.fast_app(
            hdrs=[
                mui.Theme.blue.headers(),
                list_manipulation_js(),
                comparison_form_js(),
            ],
            pico=False,
            live=False,
        )
        comp.register_routes(app)

        @rt("/")
        def get():
            return fh.Div(
                comp.form_wrapper(comp.render_inputs()),
                comparison_form_js(),
            )

        return TestClient(app), comp

    def test_multiple_sibling_list_containers_exist(
        self, multi_list_comparison_client, soup
    ):
        """
        Test that multiple sibling list containers are created correctly.
        """
        client, comp = multi_list_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # members[0] should have three sibling list containers
        emails_container = dom.find(id="multi_left_members_0_emails_items_container")
        phones_container = dom.find(id="multi_left_members_0_phones_items_container")
        addresses_container = dom.find(
            id="multi_left_members_0_addresses_items_container"
        )

        assert emails_container is not None, "Expected emails container"
        assert phones_container is not None, "Expected phones container"
        assert addresses_container is not None, "Expected addresses container"

    def test_sibling_list_add_buttons_have_distinct_paths(
        self, multi_list_comparison_client, soup
    ):
        """
        Test that sibling lists have distinct add button paths.
        """
        client, comp = multi_list_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        add_buttons = dom.find_all(
            "button", attrs={"hx-post": re.compile(r"/list/add/members/0/")}
        )
        add_urls = [btn.get("hx-post", "") for btn in add_buttons]

        # Should have distinct paths for each list
        emails_urls = [u for u in add_urls if u.endswith("/emails")]
        phones_urls = [u for u in add_urls if u.endswith("/phones")]
        addresses_urls = [u for u in add_urls if u.endswith("/addresses")]

        assert emails_urls, f"Expected emails add button, found: {add_urls}"
        assert phones_urls, f"Expected phones add button, found: {add_urls}"
        assert addresses_urls, f"Expected addresses add button, found: {add_urls}"

    def test_correct_add_button_selected_for_each_sibling_list(
        self, multi_list_comparison_client, soup
    ):
        """
        Test that the fixed selector finds the correct button for each sibling list.
        """
        client, comp = multi_list_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # For each sibling list, verify the correct button would be found
        sibling_lists = ["emails", "phones", "addresses"]

        for list_name in sibling_lists:
            container_id = f"multi_left_members_0_{list_name}_items_container"
            container = dom.find(id=container_id)
            assert container is not None, f"Expected container {container_id}"

            parent = container.parent
            assert parent is not None

            # Find all add buttons
            all_buttons = parent.find_all(
                "button", attrs={"hx-post": re.compile(r"/list/add/")}
            )
            all_urls = [btn.get("hx-post", "") for btn in all_buttons]

            # The fixed selector uses endsWith
            expected_suffix = f"/list/add/members/0/{list_name}"
            correct_buttons = [u for u in all_urls if u.endswith(expected_suffix)]

            assert correct_buttons, (
                f"Expected button ending with '{expected_suffix}' for {list_name}, "
                f"found: {all_urls}"
            )

    def test_copying_member_with_multiple_lists(
        self, multi_list_comparison_client, htmx_headers, soup
    ):
        """
        Test that copying a member (with multiple nested lists) works correctly.
        """
        client, comp = multi_list_comparison_client

        # Add a new member
        response = client.post(
            "/form/multi_left/list/add/members",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # New member should have containers for all three lists
        new_item = dom.find("li")
        assert new_item is not None

        # Check for nested list containers in the new item
        new_item_html = str(new_item)
        assert "emails_items_container" in new_item_html or "emails" in new_item_html
        assert "phones_items_container" in new_item_html or "phones" in new_item_html
