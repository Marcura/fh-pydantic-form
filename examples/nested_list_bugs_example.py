"""
Nested List Bugs Example - Demonstrates bugs in deeply nested list copying

This example showcases TWO BUGS that occur when copying in deeply nested
List[BaseModel] structures:

BUG 1: Nested List Item Treated as Subfield
========================================
Path: sections[0].paragraphs[1]

Expected: CASE 1 - Add new Paragraph to sections[0].paragraphs list
Actual:   CASE 2 - Treats it as a subfield copy (wrong!)

Why: The code checks `isSubfield` (has [N]. somewhere) BEFORE checking
`isFullListItem` (ends with [N]). For nested paths, BOTH are true, but
the subfield check runs first and returns early.


BUG 2: Wrong Container for Nested Subfield Copy
===============================================
Path: sections[0].paragraphs[1].text

Expected: Look in sections_0_paragraphs_items_container
Actual:   Looks in sections_items_container (wrong container!)

Why: `extractListFieldPath` uses regex that strips from the FIRST [index],
losing the nested context. "sections[0].paragraphs[1].text" becomes "sections".


HOW TO REPRODUCE
================
1. Run this example: python examples/nested_list_bugs_example.py
2. Open http://localhost:5002

Bug 1 - Nested Item Copy:
  - Find "paragraphs[0]" or "paragraphs[1]" in Section 1
  - Click the copy button (→)
  - Expected: New paragraph added to OTHER side's Section paragraphs
  - Actual: Unexpected behavior (may fail or do wrong thing)

Bug 2 - Nested Subfield Copy:
  - Find "paragraphs[0].text" field in Section 1
  - Click the copy button (→)
  - Expected: Text copied to corresponding paragraph on other side
  - Actual: May copy to wrong position or fail (wrong container lookup)

WHAT WORKS
==========
- Copying sections[0] (top-level list item) ✓
- Copying sections[0].title (top-level subfield) ✓
- Copying sections (full list) ✓
"""

from typing import List

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.comparison_form import ComparisonForm, comparison_form_js


# --- Models: 3-Level Nesting ---


class Paragraph(BaseModel):
    """Level 3: Innermost BaseModel with a simple list."""

    text: str = Field(default="", description="Paragraph text")
    tags: List[str] = Field(default_factory=list, description="Paragraph tags")

    def __str__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"Paragraph: {preview or '(empty)'}"


class Section(BaseModel):
    """Level 2: Middle BaseModel containing List[Paragraph]."""

    title: str = Field(default="", description="Section title")
    paragraphs: List[Paragraph] = Field(
        default_factory=list, description="Section paragraphs"
    )

    def __str__(self) -> str:
        return f"Section: {self.title or '(untitled)'}"


class Document(BaseModel):
    """Level 1: Outermost model containing List[Section]."""

    name: str = Field(default="", description="Document name")
    sections: List[Section] = Field(
        default_factory=list, description="Document sections"
    )


# --- Sample Data ---

LEFT_DATA = Document(
    name="Left Document",
    sections=[
        Section(
            title="Section 1 (Left)",
            paragraphs=[
                Paragraph(
                    text="First paragraph in section 1 (left)",
                    tags=["intro", "important"],
                ),
                Paragraph(
                    text="Second paragraph in section 1 (left)",
                    tags=["body"],
                ),
            ],
        ),
        Section(
            title="Section 2 (Left)",
            paragraphs=[
                Paragraph(
                    text="Only paragraph in section 2 (left)",
                    tags=["conclusion"],
                ),
            ],
        ),
    ],
)

RIGHT_DATA = Document(
    name="Right Document",
    sections=[
        Section(
            title="Section 1 (Right)",
            paragraphs=[
                Paragraph(
                    text="Single paragraph on right side",
                    tags=["generated"],
                ),
            ],
        ),
    ],
)


# --- App Setup ---

hdrs = (
    *mui.Theme.blue.headers(),
    fh.Script(src="https://unpkg.com/htmx.org@1.9.10"),
)

app = fh.FastHTML(hdrs=hdrs)


def create_comparison_form():
    """Create the comparison form with deeply nested data."""
    left_form = PydanticForm(
        "left_doc",
        Document,
        initial_values=LEFT_DATA,
    )

    right_form = PydanticForm(
        "right_doc",
        Document,
        initial_values=RIGHT_DATA,
    )

    comparison = ComparisonForm(
        "doc_comparison",
        left_form,
        right_form,
        left_label="Left (has more data)",
        right_label="Right (less data)",
        copy_left=True,
        copy_right=True,
    )

    return comparison


# Global form reference - recreated on each page load for stateless behavior
comparison_form = None


def get_comparison_form():
    """Get or create the comparison form. Recreates on each call for stateless behavior."""
    global comparison_form
    comparison_form = create_comparison_form()
    comparison_form.register_routes(app)
    return comparison_form


@app.get("/")
def home():
    """Render the main page with nested list bug demonstration."""
    # Recreate form on each page load - page reload = fresh state
    get_comparison_form()
    return (
        fh.Title("Nested List Bugs - Demo"),
        mui.Container(
            # Header
            fh.H1("Nested List Copy Bugs Demo", cls="text-2xl font-bold mb-4"),
            fh.P(
                "This example demonstrates bugs when copying in deeply nested "
                "List[BaseModel] structures.",
                cls="text-gray-600 mb-6",
            ),
            # Bug 1 Card
            mui.Card(
                mui.CardHeader(
                    fh.H3(
                        "BUG 1: Nested List Item Copy", cls="font-semibold text-red-600"
                    )
                ),
                mui.CardBody(
                    fh.Div(
                        fh.P(
                            fh.Strong("Path: "),
                            fh.Code("sections[0].paragraphs[1]"),
                            cls="mb-2",
                        ),
                        fh.P(
                            fh.Strong("Expected: "),
                            "Add new Paragraph to target's paragraphs list",
                            cls="mb-2",
                        ),
                        fh.P(
                            fh.Strong("Actual: "),
                            "Treated as subfield copy (wrong code path)",
                            cls="mb-2 text-red-600",
                        ),
                        fh.P(
                            fh.Strong("To reproduce: "),
                            "Click copy (→) on any 'paragraphs[N]' item",
                            cls="mb-2",
                        ),
                    ),
                ),
                cls="mb-4 border-red-200",
            ),
            # Bug 2 Card
            mui.Card(
                mui.CardHeader(
                    fh.H3(
                        "BUG 2: Wrong Container for Nested Subfield",
                        cls="font-semibold text-red-600",
                    )
                ),
                mui.CardBody(
                    fh.Div(
                        fh.P(
                            fh.Strong("Path: "),
                            fh.Code("sections[0].paragraphs[1].text"),
                            cls="mb-2",
                        ),
                        fh.P(
                            fh.Strong("Expected: "),
                            "Look in ",
                            fh.Code("sections_0_paragraphs_items_container"),
                            cls="mb-2",
                        ),
                        fh.P(
                            fh.Strong("Actual: "),
                            "Looks in ",
                            fh.Code("sections_items_container"),
                            " (wrong!)",
                            cls="mb-2 text-red-600",
                        ),
                        fh.P(
                            fh.Strong("To reproduce: "),
                            "Click copy (→) on any 'paragraphs[N].text' field",
                            cls="mb-2",
                        ),
                    ),
                ),
                cls="mb-4 border-red-200",
            ),
            # What Works Card
            mui.Card(
                mui.CardHeader(
                    fh.H3("What Works Correctly", cls="font-semibold text-green-600")
                ),
                mui.CardBody(
                    fh.Ul(
                        fh.Li(
                            fh.Code("sections[0]"),
                            " - Copy full section (top-level item) ✓",
                        ),
                        fh.Li(
                            fh.Code("sections[0].title"),
                            " - Copy section title (top-level subfield) ✓",
                        ),
                        fh.Li(fh.Code("sections"), " - Copy entire sections list ✓"),
                        fh.Li(fh.Code("name"), " - Copy document name ✓"),
                        cls="list-disc ml-6",
                    ),
                ),
                cls="mb-6 border-green-200",
            ),
            # Comparison form (page reload resets to initial state)
            fh.Div(
                render_comparison_form(),
                id="comparison-container",
            ),
            # Required JavaScript
            list_manipulation_js(),
            comparison_form_js(),
        ),
    )


def render_comparison_form():
    """Render the comparison form content."""
    return comparison_form.form_wrapper(
        fh.Div(
            comparison_form.render_inputs(),
            cls="mt-4",
        )
    )


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 70)
    print("NESTED LIST COPY BUGS DEMONSTRATION")
    print("=" * 70)
    print("""
This example demonstrates TWO BUGS in deeply nested list copying:

BUG 1: Nested List Item Treated as Subfield
  - Path: sections[0].paragraphs[1]
  - Expected: Add new Paragraph to target
  - Actual: Wrong code path (subfield copy)

BUG 2: Wrong Container for Nested Subfield
  - Path: sections[0].paragraphs[1].text
  - extractListFieldPath returns "sections" (loses nested context)
  - Looks in sections_items_container instead of sections_0_paragraphs_items_container

Structure:
  Document
  └── sections: List[Section]      (Level 1)
      └── paragraphs: List[Paragraph]  (Level 2)
          └── tags: List[str]          (Level 3)

Open http://localhost:5002 to reproduce the bugs.
""")
    print("=" * 70 + "\n")

    # Note: reload=True requires running as a module (python -m examples.nested_list_bugs_example)
    # For simplicity, we run without reload - restart server to pick up changes
    uvicorn.run(app, host="0.0.0.0", port=5002)
