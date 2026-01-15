"""
Copy Example - Demonstrates ComparisonForm copy functionality

This example showcases the copy behavior between left and right forms in a
ComparisonForm, including:

1. Copying individual List[BaseModel] items (e.g., reviews[0])
2. Copying subfields of list items (e.g., reviews[0].rating) - updates existing item
3. Copying entire lists (e.g., reviews)
4. Copying simple scalar fields (e.g., name)
5. Copying List[Literal] pill fields (e.g., categories)

Use this to test that:
- Copying a full list item creates a NEW item in the target list
- Copying a subfield UPDATES the existing item (doesn't create new)
- Copying works for both numeric indices (reviews[0]) and placeholder indices (reviews[new_123])
- Copying pill fields transfers all selected pills to target
"""

from typing import List, Literal

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.comparison_form import ComparisonForm, comparison_form_js


# --- Models ---


class Review(BaseModel):
    """A product review with rating and comment."""

    rating: int = Field(default=3, ge=1, le=5, description="Rating from 1-5 stars")
    comment: str = Field(default="", description="Review comment")


class Product(BaseModel):
    """A product with reviews and tags."""

    name: str = Field(default="", description="Product name")
    description: str = Field(default="", description="Product description")
    categories: List[Literal["Electronics", "Clothing", "Home", "Sports", "Books"]] = Field(
        default_factory=list, description="Product categories (pill selector)"
    )
    reviews: List[Review] = Field(default_factory=list, description="Customer reviews")
    tags: List[str] = Field(default_factory=list, description="Product tags")


# --- Sample Data ---

# Left form: "Reference" data with 2 reviews
LEFT_DATA = Product(
    name="Left Product",
    description="This is the reference product on the left side.",
    categories=["Electronics", "Home"],
    reviews=[
        Review(rating=5, comment="Excellent quality!"),
        Review(rating=4, comment="Good value for money."),
    ],
    tags=["featured", "sale", "popular"],
)

# Right form: "Generated" data with 1 review (different content)
RIGHT_DATA = Product(
    name="Right Product",
    description="This is the generated product on the right side.",
    categories=["Clothing", "Sports", "Books"],
    reviews=[
        Review(rating=3, comment="Average product."),
    ],
    tags=["new", "trending"],
)


# --- App Setup ---

hdrs = (
    *mui.Theme.blue.headers(),
    fh.Script(src="https://unpkg.com/htmx.org@1.9.10"),
)

app = fh.FastHTML(hdrs=hdrs)


def create_comparison_form():
    """Create the comparison form with sample data."""
    left_form = PydanticForm(
        "left_form",
        Product,
        initial_values=LEFT_DATA,
    )

    right_form = PydanticForm(
        "right_form",
        Product,
        initial_values=RIGHT_DATA,
    )

    comparison = ComparisonForm(
        "product_comparison",
        left_form,
        right_form,
        left_label="Reference (Target)",
        right_label="Generated (Source)",
        copy_left=True,  # Enable copy buttons on right to copy TO left
        copy_right=True,  # Enable copy buttons on left to copy TO right
    )

    return comparison


# Global comparison form instance
comparison_form = create_comparison_form()


@app.get("/")
def home():
    """Render the main page with comparison form."""
    return (
        fh.Title("Copy Example - ComparisonForm"),
        mui.Container(
            # Header
            fh.H1("ComparisonForm Copy Example", cls="text-2xl font-bold mb-4"),
            fh.P(
                "Test the copy functionality between left and right forms.",
                cls="text-gray-600 mb-6",
            ),
            # Instructions
            mui.Card(
                mui.CardHeader(fh.H3("How to Test", cls="font-semibold")),
                mui.CardBody(
                    fh.Ul(
                        fh.Li(
                            fh.Strong("Copy Full Item: "),
                            "Click copy on 'reviews[0]' - should ADD a new item to target list",
                            cls="mb-2",
                        ),
                        fh.Li(
                            fh.Strong("Copy Subfield: "),
                            "Click copy on 'reviews[0].rating' - should UPDATE existing item's rating (not create new)",
                            cls="mb-2",
                        ),
                        fh.Li(
                            fh.Strong("Copy Full List: "),
                            "Click copy on 'reviews' field header - should copy entire list",
                            cls="mb-2",
                        ),
                        fh.Li(
                            fh.Strong("Add Item Then Copy: "),
                            "Add a new item (creates new_TIMESTAMP placeholder), then copy it",
                            cls="mb-2",
                        ),
                        fh.Li(
                            fh.Strong("Copy Pill Field: "),
                            "Click copy on 'categories' - should copy all selected pills to target",
                            cls="mb-2",
                        ),
                        cls="list-disc ml-6",
                    ),
                ),
                cls="mb-6",
            ),
            # Legend
            mui.Card(
                mui.CardHeader(fh.H3("Copy Directions", cls="font-semibold")),
                mui.CardBody(
                    fh.Div(
                        fh.Span(
                            "Copy buttons on RIGHT side copy TO LEFT (target)",
                            cls="block mb-1",
                        ),
                        fh.Span(
                            "Copy buttons on LEFT side copy TO RIGHT (target)",
                            cls="block",
                        ),
                        cls="text-sm text-gray-600",
                    ),
                ),
                cls="mb-6",
            ),
            # Reset button
            fh.Div(
                fh.Button(
                    "Reset Forms",
                    hx_get="/reset",
                    hx_target="#comparison-container",
                    hx_swap="innerHTML",
                    cls="uk-button uk-button-secondary mb-4",
                ),
            ),
            # Comparison form
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


@app.get("/reset")
def reset_forms():
    """Reset the comparison form to initial state."""
    global comparison_form
    comparison_form = create_comparison_form()
    comparison_form.register_routes(app)
    return render_comparison_form()


# Register routes for the comparison form
comparison_form.register_routes(app)


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 60)
    print("ComparisonForm Copy Example")
    print("=" * 60)
    print("\nThis example demonstrates:")
    print("  - Copying full list items (adds new item)")
    print("  - Copying subfields (updates existing item)")
    print("  - Copying newly added items (new_TIMESTAMP placeholders)")
    print("  - Copying List[Literal] pill fields (categories)")
    print("\nOpen http://localhost:5001 in your browser")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=5001)
