import datetime
import logging
from enum import Enum
from typing import List, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import (
    ComparisonForm,
    ComparisonMetric,
    PydanticForm,
    comparison_form_js,
    list_manipulation_js,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
        comparison_form_js(),  # Add comparison-specific JS
    ],
    pico=False,
    live=True,
)


# ============================================================================
# Simplified Data Model for Product Extraction
# ============================================================================


class Category(Enum):
    ELECTRONICS = "Electronics"
    CLOTHING = "Clothing"
    HOME_GARDEN = "Home & Garden"
    SPORTS = "Sports & Outdoors"
    BOOKS = "Books"
    TOYS = "Toys & Games"
    FOOD = "Food & Beverages"


class ProductInfo(BaseModel):
    name: str = Field(description="Product name")
    brand: str = Field(description="Brand name")
    category: Category = Field(description="Product category")
    price: float = Field(description="Price in USD")
    in_stock: bool = Field(description="Availability status")

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class Specifications(BaseModel):
    weight: Optional[str] = Field(None, description="Product weight")
    dimensions: Optional[str] = Field(None, description="Product dimensions")
    material: Optional[str] = Field(None, description="Primary material")
    color: Optional[str] = Field(None, description="Color options")
    warranty: Optional[str] = Field(None, description="Warranty period")

    def __str__(self) -> str:
        specs = [s for s in [self.weight, self.dimensions, self.material] if s]
        return f"{len(specs)} specifications"


class ExtractedProduct(BaseModel):
    """Extracted product information from e-commerce listing"""

    # Basic product info
    product: ProductInfo = Field(description="Core product information")

    # Features and specs
    key_features: List[str] = Field(
        default_factory=list, description="Main product features"
    )
    specifications: Specifications = Field(
        default_factory=Specifications, description="Technical specifications"
    )

    # Description and metadata
    description: str = Field(description="Product description")
    target_audience: Optional[str] = Field(None, description="Target customer segment")

    # Extraction metadata
    extraction_confidence: float = Field(0.0, description="Extraction confidence score")
    source_url: Optional[str] = Field(None, description="Source listing URL")
    extracted_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now, description="Extraction timestamp"
    )


# ============================================================================
# Evaluation Metrics for Error Analysis
# ============================================================================

eval_metrics = {
    # Product info metrics
    "product": ComparisonMetric(
        metric=0.75,
        comment="Product section: Most fields correct with minor issues",
    ),
    "product.name": ComparisonMetric(
        metric=0.90,
        comment="Minor difference: 'Pro Max' vs 'ProMax'",
    ),
    "product.brand": ComparisonMetric(
        metric=1.0,
        comment="Brand correctly extracted",
    ),
    "product.category": ComparisonMetric(
        metric=0.0,
        comment="Wrong category: 'Electronics' should be 'Sports & Outdoors'",
    ),
    "product.price": ComparisonMetric(
        metric=0.95,
        comment="Price extracted but missing cents: 299 vs 299.99",
    ),
    "product.in_stock": ComparisonMetric(
        metric=1.0,
        comment="Stock status correct",
    ),
    # Features metrics
    "key_features": ComparisonMetric(
        metric=0.60,
        comment="3 of 5 key features extracted, some paraphrasing",
    ),
    "key_features[0]": ComparisonMetric(
        metric=1.0,
        comment="Waterproof feature correctly identified",
    ),
    "key_features[1]": ComparisonMetric(
        metric=0.8,
        comment="Battery life rounded: '10 hours' vs '10.5 hours'",
    ),
    "key_features[2]": ComparisonMetric(
        metric=0.0,
        comment="Missed GPS tracking feature",
    ),
    # Specifications metrics
    "specifications": ComparisonMetric(
        metric=0.70,
        comment="Specifications partially extracted",
    ),
    "specifications.weight": ComparisonMetric(
        metric=0.0,
        comment="Weight not found in extraction",
    ),
    "specifications.dimensions": ComparisonMetric(
        metric=0.85,
        comment="Dimensions normalized: used 'x' instead of '×'",
    ),
    "specifications.material": ComparisonMetric(
        metric=1.0,
        comment="Material correctly identified",
    ),
    "specifications.warranty": ComparisonMetric(
        metric=0.5,
        comment="Warranty period incomplete: '1 year' vs '1 year limited'",
    ),
    # Other fields
    "description": ComparisonMetric(
        metric=0.75,
        comment="Description paraphrased, lost some marketing language",
    ),
    "target_audience": ComparisonMetric(
        metric=0.0,
        comment="Target audience not extracted from listing",
    ),
    "extraction_confidence": ComparisonMetric(
        metric=0.73,
        comment="Overall confidence: 73%",
    ),
}


# ============================================================================
# Sample Data: Annotated Truth vs Generated Output
# ============================================================================

# Annotated truth (ground truth from manual annotation)
annotated_truth = ExtractedProduct(
    product=ProductInfo(
        name="Smart Fitness Tracker Pro Max",
        brand="FitTech",
        category=Category.SPORTS,  # This is actually correct
        price=299.99,
        in_stock=True,
    ),
    key_features=[
        "Waterproof up to 50 meters",
        "10.5 hours battery life",
        "Built-in GPS tracking",
        "Heart rate monitoring",
        "Sleep quality analysis",
    ],
    specifications=Specifications(
        weight="45g",
        dimensions="44mm × 38mm × 10.7mm",
        material="Aluminum case with silicone band",
        color="Black, Silver, Rose Gold",
        warranty="1 year limited warranty",
    ),
    description=(
        "The Smart Fitness Tracker Pro Max combines cutting-edge health monitoring "
        "technology with sleek design. Track your workouts, monitor your heart rate 24/7, "
        "and gain insights into your sleep patterns. Perfect for athletes and fitness "
        "enthusiasts who demand precision and style."
    ),
    target_audience="Athletes and fitness enthusiasts aged 18-45",
    extraction_confidence=1.0,
    source_url="https://example.com/products/fittech-tracker-pro-max",
)

# LLM-generated extraction (with typical errors)
generated_output = ExtractedProduct(
    product=ProductInfo(
        name="Smart Fitness Tracker ProMax",  # Missing space
        brand="FitTech",
        category=Category.ELECTRONICS,  # Wrong category!
        price=299.0,  # Missing cents
        in_stock=True,
    ),
    key_features=[
        "Waterproof up to 50 meters",
        "10 hours battery life",  # Rounded down
        # "Built-in GPS tracking",  # MISSED THIS FEATURE
        "Heart rate monitoring",
        # "Sleep quality analysis",  # MISSED THIS TOO
    ],
    specifications=Specifications(
        weight=None,  # Failed to extract
        dimensions="44mm x 38mm x 10.7mm",  # Different separator
        material="Aluminum case with silicone band",
        color="Black, Silver, Rose Gold",
        warranty="1 year",  # Missing "limited"
    ),
    description=(
        "This fitness tracker offers advanced health monitoring features with an elegant design. "
        "It tracks workouts, monitors heart rate continuously, and provides sleep insights. "
        "Ideal for those who want to stay fit and stylish."
        # Paraphrased, lost specific marketing language
    ),
    target_audience=None,  # Failed to extract
    extraction_confidence=0.73,
    source_url="https://example.com/products/fittech-tracker-pro-max",
)


# ============================================================================
# In-memory storage for annotation updates (for demo purposes)
# ============================================================================

# Track annotation updates
annotation_updates = []


def save_annotation_update(updated_data: dict, reason: str = ""):
    """Save annotation update with timestamp and reason"""
    annotation_updates.append(
        {
            "timestamp": datetime.datetime.now(),
            "reason": reason,
            "updated_fields": list(updated_data.keys()),
            "data": updated_data,
        }
    )
    logger.info(f"Annotation updated: {reason}")


# ============================================================================
# Create comparison forms
# ============================================================================

# Left form: Annotated truth (editable)
truth_form = PydanticForm(
    form_name="annotated_truth",
    model_class=ExtractedProduct,
    initial_values=annotated_truth,
    disabled=False,  # Can be edited
    spacing="compact",
    exclude_fields=["extracted_at", "source_url"],
)

# Right form: Generated output (read-only)
generated_form = PydanticForm(
    form_name="generated_output",
    model_class=ExtractedProduct,
    initial_values=generated_output,
    disabled=True,  # Cannot be edited
    spacing="compact",
    exclude_fields=["extracted_at", "source_url"],
)

# Create comparison form
comparison_form = ComparisonForm(
    name="product_extraction_comparison",
    left_form=truth_form,
    right_form=generated_form,
    left_metrics={},  # putting the metrics on right side only, but could be on the left as well
    right_metrics=eval_metrics,  # Metrics show on generated side
    left_label="📝 Annotated Truth (Ground Truth)",
    right_label="🤖 LLM Generated Output",
)


truth_form.register_routes(app)


@rt("/update_annotation")
async def post_update_annotation(req):
    """Handle annotation update with validation"""
    try:
        # Validate the truth form (left side)
        validated = await truth_form.model_validate_request(req)

        # Simulate saving the annotation update
        save_annotation_update(
            validated.model_dump(),
            reason="Manual annotation correction after model comparison",
        )

        return fh.Div(
            mui.Card(
                mui.CardHeader(
                    fh.H4("✅ Annotation Updated Successfully!", cls="text-green-600")
                ),
                mui.CardBody(
                    fh.P(
                        "🎉 The annotated truth has been validated and updated!",
                        cls="text-green-700 font-medium mb-2",
                    ),
                    fh.P(
                        "✨ Changes have been saved to the annotation database.",
                        cls="text-sm text-gray-600 mb-3",
                    ),
                    mui.Details(
                        mui.Summary("📋 View Updated Data"),
                        fh.Pre(
                            validated.model_dump_json(indent=2),
                            cls="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-64",
                        ),
                        cls="mt-2",
                    ),
                ),
                cls="border-green-200 bg-green-50",
            ),
        )
    except Exception:
        return fh.Div(
            mui.Card(
                mui.CardHeader(
                    fh.H4("❌ Annotation Update Failed", cls="text-red-500")
                ),
                cls="border-red-200 bg-red-50",
            ),
        )


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            # Header
            mui.Card(
                mui.CardHeader(
                    fh.H1(
                        "🔍 Eval Run Error Analysis",
                        cls="text-2xl font-bold text-blue-600",
                    ),
                    fh.P(
                        "Compare LLM-generated output with annotated truth. Update annotations when the generated output is actually correct.",
                        cls="text-gray-600 mt-2",
                    ),
                ),
                mui.CardBody(
                    # Workflow explanation
                    mui.Card(
                        mui.CardHeader(
                            fh.H2("📋 Workflow", cls="text-lg font-semibold")
                        ),
                        mui.CardBody(
                            fh.Ol(
                                fh.Li(
                                    "Review differences between generated output (right) and annotated truth (left)"
                                ),
                                fh.Li(
                                    "If generated output is correct but marked as wrong, update the annotation"
                                ),
                                fh.Li(
                                    "If generated output is wrong, note the error pattern for prompt improvement"
                                ),
                                cls="list-decimal list-inside space-y-2 text-sm",
                            ),
                        ),
                        cls="mb-4 bg-blue-50",
                    ),
                ),
            ),
            # Main comparison form
            mui.Card(
                mui.CardHeader(
                    fh.H2("🆚 Side-by-Side Comparison", cls="text-xl font-bold"),
                ),
                mui.CardBody(
                    comparison_form.form_wrapper(
                        fh.Div(
                            comparison_form.render_inputs(),
                            # Action buttons
                            fh.Div(
                                # Update annotation button (prominent)
                                mui.Button(
                                    "📝 Update Annotation",
                                    type="submit",
                                    cls=mui.ButtonT.destructive,
                                    hx_post="/update_annotation",
                                    hx_target="#annotation-result",
                                    hx_swap="innerHTML",
                                ),
                                # Form controls
                                fh.Div(
                                    truth_form.reset_button(
                                        "↩️ Reset Annotation",
                                    ),
                                    cls="inline-flex gap-1",
                                ),
                                cls="mt-4 flex items-center gap-3 flex-wrap",
                            ),
                            # Result area for validation feedback
                            fh.Div(id="annotation-result", cls="mt-4"),
                        )
                    ),
                ),
            ),
        ),
        cls="min-h-screen bg-gray-50 py-8",
    )


if __name__ == "__main__":
    fh.serve()
