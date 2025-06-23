import datetime
import logging
from enum import Enum
from typing import List

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import (
    MetricEntry,
    PydanticForm,
    list_manipulation_js,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
    ],
    pico=False,
    live=True,
)


# Enhanced Data Model with Nested Objects
class Status(Enum):
    DRAFT = "Draft"
    REVIEW = "Review"
    PUBLISHED = "Published"


class Priority(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Address(BaseModel):
    """Address information"""

    street: str = Field(description="Street address")
    city: str = Field(description="City")
    country: str = Field(description="Country")
    tags: List[str] = Field(default_factory=list, description="Location tags")


class Author(BaseModel):
    """Author information"""

    name: str = Field(description="Author name")
    email: str = Field(description="Email address")
    addresses: List[Address] = Field(
        default_factory=list, description="Author addresses"
    )


class Article(BaseModel):
    """Enhanced article model with nested objects to demonstrate complex metrics"""

    title: str = Field(description="Article title")
    author: Author = Field(description="Author information")
    status: Status = Field(description="Article status")
    priority: Priority = Field(description="Article priority level")
    word_count: int = Field(description="Number of words")
    rating: float = Field(description="Quality rating (0-5)")
    tags: List[str] = Field(default_factory=list, description="Article tags")
    is_featured: bool = Field(description="Featured article flag")
    publish_date: datetime.date = Field(description="Publication date")
    categories: List[str] = Field(
        default_factory=list, description="Article categories"
    )


# Sample data with nested structures
sample_article = Article(
    title="Getting Started with FastHTML",
    author=Author(
        name="John Doe",
        email="john.doe@example.com",
        addresses=[
            Address(
                street="123 Main St",
                city="San Francisco",
                country="USA",
                tags=["home", "primary"],
            ),
            Address(
                street="456 Oak Ave",
                city="Portland",
                country="USA",
                tags=["work", "secondary"],
            ),
        ],
    ),
    status=Status.PUBLISHED,
    priority=Priority.HIGH,
    word_count=1250,
    rating=4.2,
    tags=["python", "web", "tutorial", "beginner"],
    is_featured=True,
    publish_date=datetime.date(2024, 1, 15),
    categories=["programming", "web-development", "python"],
)


# Comprehensive Metrics Dictionary showcasing all capabilities with internal consistency
metrics_showcase = {
    # TOP-LEVEL FIELDS - Mixed quality to show variety
    # 1. Comment only (shows as tooltip)
    "title": MetricEntry(
        comment="This title is clear and engaging - hovers to show tooltip"
    ),
    # 2. Perfect score (1.0) - gets special bright green
    "author": MetricEntry(
        metric=1.0,
        comment="Excellent author information - metric 1.0 gets bright green",
    ),
    # 3. Zero score (0.0) - gets special bright red
    "status": MetricEntry(
        metric=0.0, comment="Critical status issue - metric 0.0 gets bright red"
    ),
    # 4. Enum field with custom color
    "priority": MetricEntry(
        metric=0.9,
        color="indigo",
        comment="Priority enum field - HIGH priority with custom indigo color",
    ),
    # 5. High range (0.5-1.0) - gets medium/forest green
    "word_count": MetricEntry(
        metric=0.85,
        comment="Good word count - metric 0.85 in high range gets medium green",
    ),
    # 6. Low range (0.0-0.5) - gets dark red
    "rating": MetricEntry(
        metric=0.3,
        comment="Low rating needs attention - metric 0.3 in low range gets dark red",
    ),
    # 7. String metric - good overall tags
    "tags": MetricEntry(
        metric="Good", comment="String metrics are supported - shows 'Good' as bullet"
    ),
    # 8. Boolean field with string metric
    "is_featured": MetricEntry(
        metric="excellent",
        comment="Featured status is excellent - string metric example",
    ),
    # 9. Date field with perfect score and custom color
    "publish_date": MetricEntry(
        metric=1.0,
        color="green",
        comment="Perfect publication timing - 1.0 with custom green color",
    ),
    # 10. Categories with zero score - consistent with low quality
    "categories": MetricEntry(
        metric=0.0, comment="Missing critical categories - another 0.0 example"
    ),
    # NESTED AUTHOR FIELDS - High quality (consistent with author=1.0)
    "author.name": MetricEntry(
        metric=0.95,
        comment="Author name is perfectly formatted - consistent with high-quality author",
    ),
    "author.email": MetricEntry(
        metric=0.9,
        comment="Email format is excellent - consistent with high-quality author",
    ),
    # SIMPLE LIST ITEMS - Mixed quality to show variety
    "tags[0]": MetricEntry(
        metric=1.0,
        color="blue",
        comment="First tag 'python' is perfect - custom blue color overrides 1.0 auto-color",
    ),
    "tags[1]": MetricEntry(
        metric=0.8,
        comment="Second tag 'web' is very good - consistent with good tags overall",
    ),
    "tags[2]": MetricEntry(
        metric=0.7,
        comment="Third tag 'tutorial' is good - consistent with good tags overall",
    ),
    "tags[3]": MetricEntry(
        metric=0.75,
        comment="Fourth tag 'beginner' is good - rounding out the good tags",
    ),
    # CATEGORIES - Consistently low (consistent with categories=0.0)
    "categories[0]": MetricEntry(
        metric=0.0,
        color="purple",
        comment="First category 'programming' is problematic - custom purple overrides 0.0 auto-color",
    ),
    "categories[1]": MetricEntry(
        metric=0.1,
        comment="Second category 'web-development' has major issues - consistent with low categories",
    ),
    "categories[2]": MetricEntry(
        metric=0.05,
        comment="Third category 'python' barely acceptable - consistent with low categories",
    ),
    # FIRST ADDRESS (HIGH QUALITY) - All subfields consistently high
    "author.addresses[0]": MetricEntry(
        metric=0.95, comment="First address data is excellent - high-quality address"
    ),
    "author.addresses[0].street": MetricEntry(
        metric=1.0,
        comment="Perfect street address '123 Main St' - excellent formatting",
    ),
    "author.addresses[0].city": MetricEntry(
        metric=0.9,
        comment="City 'San Francisco' is well-formatted - consistent with high-quality address",
    ),
    "author.addresses[0].country": MetricEntry(
        metric=0.88,
        color="orange",
        comment="Country 'USA' is properly formatted - custom orange with high quality",
    ),
    # First address tags - consistently high quality
    "author.addresses[0].tags[0]": MetricEntry(
        metric=0.85,
        comment="First address tag 'home' is well categorized - consistent with high-quality address",
    ),
    "author.addresses[0].tags[1]": MetricEntry(
        metric=0.9,
        comment="Second address tag 'primary' is excellent - consistent with high-quality address",
    ),
    # SECOND ADDRESS (LOW QUALITY) - All subfields consistently low
    "author.addresses[1]": MetricEntry(
        metric=0.2,
        comment="Second address data has significant issues - low-quality address",
    ),
    "author.addresses[1].street": MetricEntry(
        metric=0.15,
        comment="Street address '456 Oak Ave' has formatting issues - consistent with low-quality address",
    ),
    "author.addresses[1].city": MetricEntry(
        metric=0.1,
        color="teal",
        comment="City 'Portland' has verification problems - custom teal with low quality",
    ),
    "author.addresses[1].country": MetricEntry(
        metric=0.25,
        comment="Country format needs improvement - consistent with low-quality address",
    ),
    # Second address tags - consistently low quality
    "author.addresses[1].tags[0]": MetricEntry(
        metric=0.0,
        comment="First address tag 'work' has serious issues - consistent with low-quality address",
    ),
    "author.addresses[1].tags[1]": MetricEntry(
        metric=0.3,
        comment="Second address tag 'secondary' needs major improvement - consistent with low-quality address",
    ),
}

# Create two showcase forms with different spacing
showcase_form_normal = PydanticForm(
    form_name="metrics_showcase_normal",
    model_class=Article,
    initial_values=sample_article,
    metrics_dict=metrics_showcase,
    spacing="normal",
)

showcase_form_compact = PydanticForm(
    form_name="metrics_showcase_compact",
    model_class=Article,
    initial_values=sample_article,
    metrics_dict=metrics_showcase,
    spacing="compact",
)

# Register routes for both forms
showcase_form_normal.register_routes(app)
showcase_form_compact.register_routes(app)


def format_metrics_dict() -> str:
    """Format the metrics dictionary as raw dict for display"""
    lines = ["metrics_dict = {"]

    for key, entry in metrics_showcase.items():
        # Build the dictionary representation with only present fields
        dict_parts = []

        if "metric" in entry:
            metric_val = entry["metric"]
            if isinstance(metric_val, str):
                dict_parts.append(f'"metric": "{metric_val}"')
            else:
                dict_parts.append(f'"metric": {metric_val}')

        if "color" in entry:
            dict_parts.append(f'"color": "{entry["color"]}"')

        if "comment" in entry:
            comment = entry["comment"].replace('"', '\\"')  # Escape quotes
            dict_parts.append(f'"comment": "{comment}"')

        # Format the entry
        if dict_parts:
            dict_content = ", ".join(dict_parts)
            lines.append(f'    "{key}": {{{dict_content}}},')
        else:
            lines.append(f'    "{key}": {{}},')

    lines.append("}")
    return "\n".join(lines)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            # Header
            mui.Card(
                mui.CardHeader(
                    fh.H1(
                        "📊 Comprehensive Metrics Dictionary Showcase",
                        cls="text-2xl font-bold text-blue-600",
                    ),
                    fh.P(
                        "Demonstrates all metrics_dict capabilities with nested objects, lists, and complex field paths",
                        cls="text-gray-600 mt-2",
                    ),
                ),
                mui.CardBody(
                    mui.Alert(
                        fh.Strong("✨ Features Demonstrated:"),
                        fh.Ul(
                            fh.Li("📝 Comments show as tooltips (hover over fields)"),
                            fh.Li(
                                "🎯 Metric values: 1.0 (bright green), 0.0 (bright red), 0.5-1.0 (medium green), 0.0-0.5 (dark red)"
                            ),
                            fh.Li(
                                "🎨 Custom colors override automatic metric-based colors"
                            ),
                            fh.Li("🔗 Nested object fields: author.name, author.email"),
                            fh.Li("📋 List items: tags[0], categories[1]"),
                            fh.Li(
                                "🏗️ Complex nested paths: author.addresses[0].street, author.addresses[0].tags[1]"
                            ),
                            fh.Li("🔢 String, integer, float metrics, and enum fields"),
                            cls="list-disc list-inside mt-2 space-y-1",
                        ),
                        type="info",
                        cls="mb-4",
                    ),
                ),
            ),
            # Side-by-side form comparison
            mui.Card(
                mui.CardHeader(
                    fh.H2("🎯 Spacing Theme Comparison", cls="text-xl font-bold"),
                    fh.P(
                        "Compare Normal vs Compact spacing themes side by side. Hover over fields to see tooltips.",
                        cls="text-gray-600 mt-1",
                    ),
                ),
                mui.CardBody(
                    # Two-column layout for forms
                    fh.Div(
                        # Normal spacing form (left column)
                        fh.Div(
                            fh.H3("📏 Normal Spacing", cls="text-blue-600 mb-3"),
                            fh.P(
                                "Standard spacing with comfortable margins",
                                cls="text-sm text-gray-600 mb-4",
                            ),
                            mui.Form(
                                showcase_form_normal.render_inputs(),
                                fh.Div(
                                    mui.Button(
                                        "🔍 Submit Normal",
                                        cls=mui.ButtonT.primary,
                                    ),
                                    showcase_form_normal.refresh_button("🔄"),
                                    showcase_form_normal.reset_button("↩️"),
                                    cls="mt-4 flex items-center gap-2 flex-wrap",
                                ),
                                hx_post="/submit_normal",
                                hx_target="#result-normal",
                                hx_swap="innerHTML",
                                id=f"{showcase_form_normal.name}-form",
                            ),
                            fh.Div(id="result-normal", cls="mt-4"),
                            cls="w-full",
                        ),
                        # Compact spacing form (right column)
                        fh.Div(
                            fh.H3("📐 Compact Spacing", cls="text-green-600 mb-3"),
                            fh.P(
                                "Minimal spacing for dense layouts",
                                cls="text-sm text-gray-600 mb-4",
                            ),
                            mui.Form(
                                showcase_form_compact.render_inputs(),
                                fh.Div(
                                    mui.Button(
                                        "🔍 Submit Compact",
                                        cls=mui.ButtonT.primary,
                                    ),
                                    showcase_form_compact.refresh_button("🔄"),
                                    showcase_form_compact.reset_button("↩️"),
                                    cls="mt-4 flex items-center gap-2 flex-wrap",
                                ),
                                hx_post="/submit_compact",
                                hx_target="#result-compact",
                                hx_swap="innerHTML",
                                id=f"{showcase_form_compact.name}-form",
                            ),
                            fh.Div(id="result-compact", cls="mt-4"),
                            cls="w-full",
                        ),
                        cls="grid grid-cols-1 lg:grid-cols-2 gap-6",
                    ),
                ),
                cls="mb-6",
            ),
            # Metrics Dictionary Display
            mui.Card(
                mui.CardHeader(
                    fh.H2("📋 Raw Metrics Dictionary", cls="text-xl font-bold"),
                    fh.P(
                        f"Literal dictionary format with all {len(metrics_showcase)} entries (only includes fields that are used):",
                        cls="text-gray-600 mt-1",
                    ),
                ),
                mui.CardBody(
                    fh.Pre(
                        format_metrics_dict(),
                        cls="bg-gray-100 p-4 rounded text-xs overflow-x-auto whitespace-pre",
                        style="max-height: 400px; overflow-y: auto;",
                    ),
                ),
                cls="mb-6",
            ),
        ),
        cls="min-h-screen bg-gray-50 py-8",
    )


@rt("/submit_normal")
async def post_normal_form(req):
    try:
        validated = await showcase_form_normal.model_validate_request(req)
        return mui.Card(
            mui.CardHeader(
                fh.H4("✅ Normal Form - Validation Successful", cls="text-green-600")
            ),
            mui.CardBody(
                mui.H5("Validated Model:"),
                fh.Pre(
                    validated.model_dump_json(indent=2),
                    cls="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-64",
                ),
            ),
        )
    except Exception as e:
        return mui.Card(
            mui.CardHeader(
                fh.H4("❌ Normal Form - Validation Error", cls="text-red-500")
            ),
            mui.CardBody(fh.Pre(str(e), cls="bg-red-50 p-2 rounded text-xs")),
        )


@rt("/submit_compact")
async def post_compact_form(req):
    try:
        validated = await showcase_form_compact.model_validate_request(req)
        return mui.Card(
            mui.CardHeader(
                fh.H4("✅ Compact Form - Validation Successful", cls="text-green-600")
            ),
            mui.CardBody(
                mui.H5("Validated Model:"),
                fh.Pre(
                    validated.model_dump_json(indent=2),
                    cls="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-64",
                ),
            ),
        )
    except Exception as e:
        return mui.Card(
            mui.CardHeader(
                fh.H4("❌ Compact Form - Validation Error", cls="text-red-500")
            ),
            mui.CardBody(fh.Pre(str(e), cls="bg-red-50 p-1 rounded text-xs")),
        )


if __name__ == "__main__":
    fh.serve()
