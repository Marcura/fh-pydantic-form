"""
Tests for recursive nested list copying in ComparisonForm.

These tests validate the DOM structure and patterns required for the
fhpfCopyItemTree recursive copy functionality to work correctly with
deeply nested List[BaseModel] structures.

Key concepts tested:
- Add button URL normalization for container pairing
- Immediate vs deep nested container detection
- DOM ownership patterns for list items
- Container ID patterns at multiple nesting levels
"""

import re
from typing import List

import pytest
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
import fasthtml.common as fh
import monsterui.all as mui
from starlette.testclient import TestClient

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.comparison_form import ComparisonForm, comparison_form_js

pytestmark = [pytest.mark.comparison]


# --- Test Models: 3-Level Nesting ---


class Tag(BaseModel):
    """Level 3: Innermost list item."""

    name: str = Field(default="", description="Tag name")


class Paragraph(BaseModel):
    """Level 2: Middle BaseModel containing List[Tag]."""

    text: str = Field(default="", description="Paragraph text")
    tags: List[str] = Field(default_factory=list, description="Simple tags")
    structured_tags: List[Tag] = Field(
        default_factory=list, description="Structured tags"
    )


class Section(BaseModel):
    """Level 1: Outermost list item containing List[Paragraph]."""

    title: str = Field(default="", description="Section title")
    paragraphs: List[Paragraph] = Field(
        default_factory=list, description="Section paragraphs"
    )


class Document(BaseModel):
    """Root model containing List[Section]."""

    name: str = Field(default="", description="Document name")
    sections: List[Section] = Field(
        default_factory=list, description="Document sections"
    )


# --- Fixtures ---


@pytest.fixture
def deeply_nested_comparison_client():
    """
    Create a ComparisonForm with 3-level nested lists for recursive copy testing.

    Structure:
    Document
    └── sections: List[Section]      (Level 1)
        └── paragraphs: List[Paragraph]  (Level 2)
            ├── tags: List[str]          (Level 3 - simple)
            └── structured_tags: List[Tag] (Level 3 - BaseModel)

    Left has more data than right to test copy-from-left scenarios.
    """
    left_values = Document(
        name="Left Document",
        sections=[
            Section(
                title="Section 1 (Left)",
                paragraphs=[
                    Paragraph(
                        text="First paragraph",
                        tags=["intro", "important"],
                        structured_tags=[Tag(name="tag1"), Tag(name="tag2")],
                    ),
                    Paragraph(
                        text="Second paragraph",
                        tags=["body"],
                        structured_tags=[Tag(name="tag3")],
                    ),
                ],
            ),
            Section(
                title="Section 2 (Left)",
                paragraphs=[
                    Paragraph(
                        text="Only paragraph in section 2",
                        tags=["conclusion"],
                        structured_tags=[],
                    ),
                ],
            ),
        ],
    )
    right_values = Document(
        name="Right Document",
        sections=[
            Section(
                title="Section 1 (Right)",
                paragraphs=[
                    Paragraph(
                        text="Single paragraph on right",
                        tags=["generated"],
                        structured_tags=[],
                    ),
                ],
            ),
        ],
    )

    left_form = PydanticForm(
        "left_doc",
        Document,
        initial_values=left_values,
    )
    right_form = PydanticForm(
        "right_doc",
        Document,
        initial_values=right_values,
    )

    comp = ComparisonForm(
        "doc_comparison",
        left_form,
        right_form,
        left_label="Left (more data)",
        right_label="Right (less data)",
        copy_left=True,
        copy_right=True,
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
    """Return a BeautifulSoup parser function."""

    def parse(html):
        return BeautifulSoup(html, "html.parser")

    return parse


@pytest.fixture
def htmx_headers():
    """Return common HTMX request headers."""
    return {"HX-Request": "true"}


# --- URL Normalization Tests ---


class TestAddUrlNormalization:
    """Tests for fhpfNormalizeListAddUrl-style URL pattern matching."""

    def test_add_button_urls_at_each_nesting_level(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that add button URLs follow the expected pattern at each level.

        Level 1: /list/add/sections
        Level 2: /list/add/sections/N/paragraphs
        Level 3a: /list/add/sections/N/paragraphs/M/tags
        Level 3b: /list/add/sections/N/paragraphs/M/structured_tags
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all add buttons
        add_buttons = dom.find_all(
            "button", attrs={"hx-post": re.compile(r"/list/add/")}
        )
        add_urls = [btn.get("hx-post", "") for btn in add_buttons]

        # Level 1: sections
        level1_urls = [u for u in add_urls if u.endswith("/list/add/sections")]
        assert len(level1_urls) >= 2, (
            f"Expected sections add buttons on both sides: {add_urls}"
        )

        # Level 2: paragraphs (under some section)
        level2_pattern = re.compile(r"/list/add/sections/\d+/paragraphs$")
        level2_urls = [u for u in add_urls if level2_pattern.search(u)]
        assert len(level2_urls) >= 1, f"Expected paragraphs add buttons: {add_urls}"

        # Level 3a: tags (under some paragraph)
        level3a_pattern = re.compile(r"/list/add/sections/\d+/paragraphs/\d+/tags$")
        level3a_urls = [u for u in add_urls if level3a_pattern.search(u)]
        assert len(level3a_urls) >= 1, f"Expected tags add buttons: {add_urls}"

        # Level 3b: structured_tags (under some paragraph)
        level3b_pattern = re.compile(
            r"/list/add/sections/\d+/paragraphs/\d+/structured_tags$"
        )
        level3b_urls = [u for u in add_urls if level3b_pattern.search(u)]
        assert len(level3b_urls) >= 1, (
            f"Expected structured_tags add buttons: {add_urls}"
        )

    def test_normalized_url_keys_match_across_indices(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that URLs can be normalized to stable keys for container pairing.

        The JS function fhpfNormalizeListAddUrl replaces numeric indices with '*'
        so that "sections/0/paragraphs" and "sections/1/paragraphs" both become
        "sections/*/paragraphs".
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        add_buttons = dom.find_all(
            "button", attrs={"hx-post": re.compile(r"/list/add/")}
        )
        add_urls = [btn.get("hx-post", "") for btn in add_buttons]

        def normalize_url(url):
            """Python equivalent of fhpfNormalizeListAddUrl."""
            idx = url.find("/list/add/")
            if idx == -1:
                return None
            path_part = url[idx + len("/list/add/") :]
            segments = path_part.split("/")
            normalized = [
                "*" if (seg.isdigit() or seg.startswith("new_")) else seg
                for seg in segments
            ]
            return "/".join(normalized)

        # Normalize all URLs
        normalized_urls = [normalize_url(u) for u in add_urls if normalize_url(u)]

        # Check that normalized keys group correctly
        # Multiple "sections/*/paragraphs" should exist (one per section)
        paragraphs_keys = [k for k in normalized_urls if k == "sections/*/paragraphs"]
        assert len(paragraphs_keys) >= 2, (
            f"Expected multiple paragraphs keys (one per section): {normalized_urls}"
        )

        # Tags keys should all normalize to the same pattern
        tags_keys = [k for k in normalized_urls if k == "sections/*/paragraphs/*/tags"]
        assert len(tags_keys) >= 1, (
            f"Expected tags keys to normalize: {normalized_urls}"
        )

    def test_data_list_path_present_and_normalizable(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that containers expose data-list-path and it can be normalized.

        The JS now prefers data-list-path when pairing containers.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        containers = dom.find_all(id=re.compile(r"_items_container$"))
        assert containers, "Expected list containers in DOM"

        def normalize_list_path(path):
            if not path:
                return None
            segments = path.split("/")
            normalized = [
                "*" if (seg.isdigit() or seg.startswith("new_")) else seg
                for seg in segments
            ]
            return "/".join(normalized)

        normalized_paths = []
        for container in containers:
            list_path = container.get("data-list-path")
            assert list_path, (
                f"Expected data-list-path on container {container.get('id')}"
            )
            normalized = normalize_list_path(list_path)
            assert normalized is not None
            normalized_paths.append(normalized)

        assert "sections" in normalized_paths, (
            f"Expected normalized 'sections' path, got: {normalized_paths}"
        )
        assert "sections/*/paragraphs" in normalized_paths, (
            f"Expected normalized 'sections/*/paragraphs' path, got: {normalized_paths}"
        )
        assert "sections/*/paragraphs/*/tags" in normalized_paths, (
            f"Expected normalized 'sections/*/paragraphs/*/tags' path, got: {normalized_paths}"
        )
        assert "sections/*/paragraphs/*/structured_tags" in normalized_paths, (
            "Expected normalized 'sections/*/paragraphs/*/structured_tags' path"
        )


# --- Container ID Tests ---


class TestContainerIdPatterns:
    """Tests for _items_container ID patterns at different nesting levels."""

    def test_container_ids_at_each_level(self, deeply_nested_comparison_client, soup):
        """
        Test that list containers have correct IDs at each nesting level.

        Level 1: {prefix}_sections_items_container
        Level 2: {prefix}_sections_N_paragraphs_items_container
        Level 3: {prefix}_sections_N_paragraphs_M_tags_items_container
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Level 1: sections container
        sections_container = dom.find(id="left_doc_sections_items_container")
        assert sections_container is not None, "Expected sections container"
        assert sections_container.get("data-list-path") == "sections"

        # Level 2: paragraphs container (under section 0)
        paragraphs_container = dom.find(
            id="left_doc_sections_0_paragraphs_items_container"
        )
        assert paragraphs_container is not None, (
            "Expected paragraphs container for section 0"
        )
        assert paragraphs_container.get("data-list-path") == "sections/0/paragraphs"

        # Level 3a: tags container (under section 0, paragraph 0)
        tags_container = dom.find(
            id="left_doc_sections_0_paragraphs_0_tags_items_container"
        )
        assert tags_container is not None, (
            "Expected tags container for section 0, paragraph 0"
        )
        assert tags_container.get("data-list-path") == "sections/0/paragraphs/0/tags"

        # Level 3b: structured_tags container
        struct_tags_container = dom.find(
            id="left_doc_sections_0_paragraphs_0_structured_tags_items_container"
        )
        assert struct_tags_container is not None, (
            "Expected structured_tags container for section 0, paragraph 0"
        )
        assert (
            struct_tags_container.get("data-list-path")
            == "sections/0/paragraphs/0/structured_tags"
        )

    def test_containers_end_with_items_container_suffix(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that all list containers use the _items_container suffix.

        This is required for fhpfFindImmediateNestedListContainers to work.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all elements with IDs ending in _items_container
        containers = dom.find_all(id=re.compile(r"_items_container$"))

        # Should have containers for: sections, paragraphs, tags, structured_tags
        # on both left and right sides
        assert len(containers) >= 4, (
            f"Expected at least 4 list containers, found {len(containers)}"
        )

        # All should be ul or ol (list elements)
        for container in containers:
            assert container.name in ["ul", "ol"], (
                f"Container {container.get('id')} should be ul or ol, got {container.name}"
            )


# --- DOM Ownership Tests ---


class TestDomOwnership:
    """Tests for DOM ownership patterns (closest li ancestor in items_container)."""

    def test_nested_containers_are_inside_parent_list_items(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that nested containers are inside their parent's list item.

        For fhpfOwningListItem to work, nested containers must be descendants
        of <li> elements inside _items_container.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find the paragraphs container (Level 2)
        paragraphs_container = dom.find(
            id="left_doc_sections_0_paragraphs_items_container"
        )
        assert paragraphs_container is not None

        # The paragraphs container should be inside an li
        parent_li = paragraphs_container.find_parent("li")
        assert parent_li is not None, (
            "Paragraphs container should be inside a list item"
        )

        # That li should be inside the sections container
        sections_container = dom.find(id="left_doc_sections_items_container")
        assert sections_container is not None
        assert parent_li in sections_container.find_all("li"), (
            "The parent li should be inside the sections container"
        )

    def test_immediate_vs_deep_nested_containers(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that we can distinguish immediate vs deep nested containers.

        For Section item at sections[0]:
        - Immediate: sections_0_paragraphs_items_container
        - Deep: sections_0_paragraphs_0_tags_items_container (inside paragraph)

        The JS fhpfFindImmediateNestedListContainers uses fhpfOwningListItem to filter.
        fhpfOwningListItem does: el.closest('[id$="_items_container"] > li')
        This means: find the closest li that is a direct child of any items_container.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find section[0] list item
        sections_container = dom.find(id="left_doc_sections_items_container")
        assert sections_container is not None

        section_items = sections_container.find_all("li", recursive=False)
        assert len(section_items) >= 1, "Expected at least one section item"

        section_0_li = section_items[0]

        # Find all _items_container within section_0_li
        all_nested_containers = section_0_li.find_all(
            id=re.compile(r"_items_container$")
        )

        # Should have paragraphs, tags, and structured_tags containers
        assert len(all_nested_containers) >= 3, (
            f"Expected at least 3 nested containers, found {len(all_nested_containers)}"
        )

        # The JS implementation of fhpfOwningListItem:
        # el.closest('[id$="_items_container"] > li')
        # This finds the closest li that is a DIRECT child of an items_container.
        #
        # For a container to be "immediate" to section_0_li:
        # - The container must be inside section_0_li
        # - When we call fhpfOwningListItem(container), we should get section_0_li
        #
        # In practice, this means the container is NOT inside any other li that
        # is itself inside an items_container within section_0_li.

        # Categorize containers by their owning list item path
        paragraphs_container = dom.find(
            id="left_doc_sections_0_paragraphs_items_container"
        )
        tags_container = dom.find(
            id="left_doc_sections_0_paragraphs_0_tags_items_container"
        )

        # paragraphs container should be in section[0]
        assert paragraphs_container is not None
        para_parent_li = paragraphs_container.find_parent("li")
        # The paragraphs container is inside section[0]'s li
        assert para_parent_li is not None

        # tags container should be in paragraph[0], not directly in section[0]
        assert tags_container is not None
        tags_parent_li = tags_container.find_parent("li")
        assert tags_parent_li is not None

        # The tags container's immediate owning li should be a paragraph li, not the section li
        # This is the key distinction: tags is "deep" relative to section, but "immediate" relative to paragraph
        tags_parent_li_id = tags_parent_li.get("id", "")
        # The tags' parent li should be inside the paragraphs container (a paragraph item)
        assert "paragraphs" in tags_parent_li_id or tags_parent_li != section_0_li, (
            "Tags container should be inside a paragraph li, not directly in section li"
        )


# --- Add Item Response Tests ---


class TestAddItemResponse:
    """Tests for HTMX add item responses at different nesting levels."""

    def test_add_section_creates_item_with_nested_containers(
        self, deeply_nested_comparison_client, htmx_headers, soup
    ):
        """
        Test that adding a section creates an item with nested paragraphs container.
        """
        client, comp = deeply_nested_comparison_client

        response = client.post(
            "/form/left_doc/list/add/sections",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        # Should return a new li element
        new_item = dom.find("li")
        assert new_item is not None, "Expected a new list item"

        # The new item should have a paragraphs container
        paragraphs_container = new_item.find(
            id=re.compile(r"paragraphs_items_container$")
        )
        assert paragraphs_container is not None, (
            "New section should have a paragraphs container"
        )

    def test_add_paragraph_creates_item_with_tags_containers(
        self, deeply_nested_comparison_client, htmx_headers, soup
    ):
        """
        Test that adding a paragraph creates an item with nested tags containers.
        """
        client, comp = deeply_nested_comparison_client

        response = client.post(
            "/form/left_doc/list/add/sections/0/paragraphs",
            headers=htmx_headers,
        )
        assert response.status_code == 200

        dom = soup(response.text)

        new_item = dom.find("li")
        assert new_item is not None, "Expected a new list item"

        # Should have both tags and structured_tags containers
        tags_container = new_item.find(id=re.compile(r"tags_items_container$"))
        struct_tags_container = new_item.find(
            id=re.compile(r"structured_tags_items_container$")
        )

        assert tags_container is not None, "New paragraph should have a tags container"
        assert struct_tags_container is not None, (
            "New paragraph should have a structured_tags container"
        )


# --- Data Field Path Tests ---


class TestDataFieldPaths:
    """Tests for data-field-path attributes at different nesting levels."""

    def test_data_field_paths_at_each_level(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that input fields have correct data-field-path at each level.

        Level 1: sections[0].title
        Level 2: sections[0].paragraphs[0].text
        Level 3a: sections[0].paragraphs[0].tags[0]
        Level 3b: sections[0].paragraphs[0].structured_tags[0].name
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Level 1: section title
        section_title = dom.find(attrs={"data-field-path": "sections[0].title"})
        assert section_title is not None, "Expected sections[0].title field"

        # Level 2: paragraph text
        para_text = dom.find(
            attrs={"data-field-path": "sections[0].paragraphs[0].text"}
        )
        assert para_text is not None, "Expected sections[0].paragraphs[0].text field"

        # Level 3a: simple tag
        simple_tag = dom.find(
            attrs={"data-field-path": "sections[0].paragraphs[0].tags[0]"}
        )
        assert simple_tag is not None, (
            "Expected sections[0].paragraphs[0].tags[0] field"
        )

        # Level 3b: structured tag name
        struct_tag = dom.find(
            attrs={
                "data-field-path": "sections[0].paragraphs[0].structured_tags[0].name"
            }
        )
        assert struct_tag is not None, (
            "Expected sections[0].paragraphs[0].structured_tags[0].name field"
        )

    def test_relative_path_extraction_works_for_nested_fields(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that relative path extraction (after last ]) works correctly.

        fhpfCopyOwnedFields uses this to match fields between source/target.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        def extract_relative_path(full_path):
            """Extract everything after the last ]."""
            last_bracket = full_path.rfind("]")
            return full_path[last_bracket + 1 :] if last_bracket >= 0 else full_path

        # Test relative paths
        test_cases = {
            "sections[0].title": ".title",
            "sections[0].paragraphs[0].text": ".text",
            "sections[0].paragraphs[0].tags[0]": "",  # Simple list item has no suffix
            "sections[0].paragraphs[0].structured_tags[0].name": ".name",
        }

        for full_path, expected_relative in test_cases.items():
            actual = extract_relative_path(full_path)
            assert actual == expected_relative, (
                f"For {full_path}: expected relative '{expected_relative}', got '{actual}'"
            )


# --- Copy Button Tests ---


class TestCopyButtonsForNestedLists:
    """Tests for copy button paths at different nesting levels."""

    def test_copy_buttons_exist_for_all_list_levels(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that copy buttons exist for lists at all levels.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all copy buttons
        copy_buttons = dom.find_all("button", onclick=re.compile(r"fhpfPerformCopy"))

        # Extract paths from onclick
        paths = []
        for btn in copy_buttons:
            onclick = btn.get("onclick", "")
            match = re.search(r"fhpfPerformCopy\('([^']+)'", onclick)
            if match:
                paths.append(match.group(1))

        # Should have copy buttons for:
        # - sections (full list)
        # - sections[N] (section items)
        # - sections[N].paragraphs (full list)
        # - sections[N].paragraphs[M] (paragraph items)
        # - sections[N].paragraphs[M].tags (full list)
        # etc.

        assert any(p == "sections" for p in paths), (
            f"Expected copy button for 'sections' list: {paths}"
        )
        assert any(re.match(r"^sections\[\d+\]$", p) for p in paths), (
            f"Expected copy button for section items: {paths}"
        )
        assert any(re.match(r"^sections\[\d+\]\.paragraphs$", p) for p in paths), (
            f"Expected copy button for nested paragraphs list: {paths}"
        )
        assert any(
            re.match(r"^sections\[\d+\]\.paragraphs\[\d+\]\.tags$", p) for p in paths
        ), f"Expected copy button for tags list: {paths}"
        assert any(
            re.match(r"^sections\[\d+\]\.paragraphs\[\d+\]\.structured_tags$", p)
            for p in paths
        ), f"Expected copy button for structured_tags list: {paths}"

    def test_copy_button_for_full_nested_list(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that copy button for sections[0].paragraphs exists and has correct path.

        This is the CASE 3 scenario for nested lists.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy button for sections[0].paragraphs
        copy_buttons = dom.find_all(
            "button",
            onclick=re.compile(r"fhpfPerformCopy\('sections\[0\]\.paragraphs'"),
        )

        assert len(copy_buttons) >= 1, (
            "Expected copy button for 'sections[0].paragraphs' nested list"
        )

    def test_copy_button_for_nested_item(self, deeply_nested_comparison_client, soup):
        """
        Test that copy button for sections[0].paragraphs[0] exists.

        This is the CASE 1 scenario for nested list items.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find copy button for sections[0].paragraphs[0]
        copy_buttons = dom.find_all(
            "button",
            onclick=re.compile(r"fhpfPerformCopy\('sections\[0\]\.paragraphs\[0\]',"),
        )

        assert len(copy_buttons) >= 1, (
            "Expected copy button for 'sections[0].paragraphs[0]' nested item"
        )

    def test_copy_button_for_structured_tag_item(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that copy button for sections[0].paragraphs[0].structured_tags[0] exists.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        copy_buttons = dom.find_all(
            "button",
            onclick=re.compile(
                r"fhpfPerformCopy\('sections\[0\]\.paragraphs\[0\]\.structured_tags\[0\]',"
            ),
        )
        assert len(copy_buttons) >= 1, (
            "Expected copy button for 'sections[0].paragraphs[0].structured_tags[0]'"
        )


# --- JavaScript Function Tests (via HTML patterns) ---


class TestJavaScriptHelperPatterns:
    """
    Tests validating DOM patterns required for JS helper functions.

    These tests verify that the HTML structure supports the JS functions:
    - fhpfOwningListItem
    - fhpfFindImmediateNestedListContainers
    - fhpfListKeyForContainer
    """

    def test_add_button_is_sibling_of_container(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that add button is in the parent element of its container.

        fhpfGetAddButtonForContainer expects: container.parentElement.querySelector('button')
        The button may not be the FIRST one in the parent (due to nested content),
        but there should be an add button with the correct URL.
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find paragraphs container
        paragraphs_container = dom.find(
            id="left_doc_sections_0_paragraphs_items_container"
        )
        assert paragraphs_container is not None

        # The parent should contain the add button for paragraphs
        parent = paragraphs_container.parent
        all_add_buttons = parent.find_all(
            "button", attrs={"hx-post": re.compile(r"/list/add/")}
        )

        assert len(all_add_buttons) > 0, (
            "Expected at least one add button in the parent element"
        )

        # Find the button specifically for paragraphs (ends with /sections/0/paragraphs)
        paragraphs_add_button = None
        for btn in all_add_buttons:
            hx_post = btn.get("hx-post", "")
            if hx_post.endswith("/sections/0/paragraphs"):
                paragraphs_add_button = btn
                break

        assert paragraphs_add_button is not None, (
            f"Expected add button for paragraphs in parent, found URLs: "
            f"{[b.get('hx-post') for b in all_add_buttons]}"
        )

    def test_add_button_matches_container_list_path(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that each container's data-list-path has a matching add button.

        This mirrors fhpfGetAddButtonForContainer behavior (endsWith check).
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Check a few representative containers at different depths
        container_ids = [
            "left_doc_sections_items_container",
            "left_doc_sections_0_paragraphs_items_container",
            "left_doc_sections_0_paragraphs_0_tags_items_container",
            "left_doc_sections_0_paragraphs_0_structured_tags_items_container",
        ]

        for container_id in container_ids:
            container = dom.find(id=container_id)
            assert container is not None, f"Expected container {container_id}"
            list_path = container.get("data-list-path")
            assert list_path, f"Expected data-list-path on {container_id}"
            expected_suffix = f"/list/add/{list_path}"

            parent = container.parent
            add_buttons = parent.find_all(
                "button", attrs={"hx-post": re.compile(r"/list/add/")}
            )
            assert add_buttons, f"Expected add buttons for {container_id}"

            matches = [
                btn
                for btn in add_buttons
                if (btn.get("hx-post") or "").endswith(expected_suffix)
            ]
            assert matches, (
                f"Expected add button ending with '{expected_suffix}' for {container_id}"
            )

    def test_containers_have_ul_with_li_children(
        self, deeply_nested_comparison_client, soup
    ):
        """
        Test that containers are ul elements with li children.

        fhpfOwningListItem uses: el.closest('[id$="_items_container"] > li')
        """
        client, comp = deeply_nested_comparison_client
        response = client.get("/")
        assert response.status_code == 200

        dom = soup(response.text)

        # Find all containers
        containers = dom.find_all(id=re.compile(r"_items_container$"))

        for container in containers:
            # Should be ul or ol
            assert container.name in ["ul", "ol"], (
                f"Container should be ul/ol: {container.get('id')}"
            )

            # Direct children should be li (if any)
            for child in container.children:
                if hasattr(child, "name") and child.name is not None:
                    assert child.name == "li", (
                        f"Container children should be li: {container.get('id')}"
                    )
