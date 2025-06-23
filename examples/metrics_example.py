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


# Comprehensive Metrics Dictionary showcasing all capabilities
metrics_showcase = {
    # 1. Comment only (shows as tooltip)
    "title": MetricEntry(
        comment="This title is clear and engaging - hovers to show tooltip"
    ),
    # 2. Perfect score (1.0) - gets special bright green
    "author": MetricEntry(
        metric=1.0, comment="Perfect author information - metric 1.0 gets bright green"
    ),
    # 3. Zero score (0.0) - gets special bright red
    "status": MetricEntry(
        metric=0.0, comment="Critical status issue - metric 0.0 gets bright red"
    ),
    # 3.5. Enum field with custom color
    "priority": MetricEntry(
        metric=0.9,
        color="indigo",
        comment="Priority enum field - HIGH priority with custom indigo color",
    ),
    # 4. High range (0.5-1.0) - gets medium/forest green
    "word_count": MetricEntry(
        metric=0.85,
        comment="Good word count - metric 0.85 in high range gets medium green",
    ),
    # 5. Low range (0.0-0.5) - gets dark red
    "rating": MetricEntry(
        metric=0.3,
        comment="Low rating needs attention - metric 0.3 in low range gets dark red",
    ),
    # 6. String metric
    "tags": MetricEntry(
        metric="Good", comment="String metrics are supported - shows 'Good' as bullet"
    ),
    # 7. Integer metric
    "is_featured": MetricEntry(
        metric=5, comment="Integer metrics work too - shows '5' as bullet"
    ),
    # 8. Another perfect score (1.0)
    "publish_date": MetricEntry(
        metric=1.0, comment="Perfect publication timing - another 1.0 example"
    ),
    # 9. Another zero score (0.0)
    "categories": MetricEntry(
        metric=0.0, comment="Missing critical categories - another 0.0 example"
    ),
    # NESTED OBJECT FIELDS
    # 10. Nested field: author.name
    "author.name": MetricEntry(
        metric=0.9, comment="Author name is well formatted - nested field example"
    ),
    # 11. Nested field: author.email
    "author.email": MetricEntry(
        metric=0.6, comment="Email format is acceptable but could be improved"
    ),
    # SIMPLE LIST ITEMS
    # 12. First tag
    "tags[0]": MetricEntry(
        metric=1.0,
        color="blue",
        comment="First tag 'python' is perfect - custom blue color overrides 1.0 auto-color",
    ),
    # 13. Second tag
    "tags[1]": MetricEntry(
        metric=0.4, comment="Second tag needs improvement - low range metric"
    ),
    # 14. Third tag
    "tags[2]": MetricEntry(metric=0.7, comment="Third tag is good - high range metric"),
    # 15. Categories list items
    "categories[0]": MetricEntry(
        metric=0.0,
        color="purple",
        comment="First category problematic - custom purple overrides 0.0 auto-color",
    ),
    "categories[1]": MetricEntry(metric=0.8, comment="Second category is good"),
    # NESTED LIST ITEMS (Complex paths)
    # 16. First address overall
    "author.addresses[0]": MetricEntry(
        metric=0.95, comment="First address data is excellent"
    ),
    # 17. First address street
    "author.addresses[0].street": MetricEntry(
        metric=1.0, comment="Perfect street address format - nested list item field"
    ),
    # 18. First address city
    "author.addresses[0].city": MetricEntry(
        metric=0.2,
        comment="City information needs verification - low score in nested structure",
    ),
    # 19. Second address street
    "author.addresses[1].street": MetricEntry(
        metric=0.6, comment="Second address street format is adequate"
    ),
    # 20. Nested list within nested object: first address tags
    "author.addresses[0].tags[0]": MetricEntry(
        metric=0.0, comment="First address tag has issues - deeply nested path example"
    ),
    # 21. Another deeply nested example
    "author.addresses[0].tags[1]": MetricEntry(
        metric=1.0,
        comment="Second tag of first address is perfect - complex nested path",
    ),
    # 22. Second address tags
    "author.addresses[1].tags[0]": MetricEntry(
        metric=0.75, comment="Work tag is well categorized"
    ),
    # Custom color examples with different ranges
    # 23. High range with custom color
    "author.addresses[0].country": MetricEntry(
        metric=0.88,
        color="orange",
        comment="Custom orange color overrides high-range auto-color",
    ),
    # 24. Low range with custom color
    "author.addresses[1].city": MetricEntry(
        metric=0.15,
        color="teal",
        comment="Custom teal color overrides low-range auto-color",
    ),
}

# Create the showcase form
showcase_form = PydanticForm(
    form_name="metrics_showcase",
    model_class=Article,
    initial_values=sample_article,
    # disabled=True,  # Read-only for demonstration
    metrics_dict=metrics_showcase,
)

# Register routes
showcase_form.register_routes(app)


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
            # Main showcase form
            mui.Card(
                mui.CardHeader(
                    fh.H2("🎯 Live Demo", cls="text-xl font-bold"),
                    fh.P(
                        "Hover over fields to see tooltips. Notice the colored bullets and field highlighting on nested fields.",
                        cls="text-gray-600 mt-1",
                    ),
                ),
                mui.CardBody(
                    mui.Form(showcase_form.render_inputs()),
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


if __name__ == "__main__":
    fh.serve()
