import datetime
import logging
from datetime import date, time
from enum import Enum
from typing import List, Literal, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import (
    ComparisonForm,
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
# Enhanced Data Model for Product Extraction - Showcasing All Field Types
# ============================================================================


class Category(Enum):
    ELECTRONICS = "Electronics"
    CLOTHING = "Clothing"
    HOME_GARDEN = "Home & Garden"
    SPORTS = "Sports & Outdoors"
    BOOKS = "Books"
    TOYS = "Toys & Games"
    FOOD = "Food & Beverages"


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProductInfo(BaseModel):
    name: str = Field(description="Product name")
    brand: str = Field(description="Brand name")
    category: Category = Field(description="Product category")
    price: float = Field(description="Price in USD")
    in_stock: bool = Field(description="Availability status")
    # New fields to showcase more types
    release_date: date = Field(description="Product release date")
    availability_time: time = Field(description="Daily availability time")
    priority: Priority = Field(description="Product priority level")
    discount_percentage: Optional[float] = Field(
        None, description="Discount percentage if applicable"
    )
    is_featured: Optional[bool] = Field(None, description="Whether product is featured")

    def __str__(self) -> str:
        return f"{self.brand} {self.name}"


class Specifications(BaseModel):
    weight: Optional[str] = Field(None, description="Product weight")
    dimensions: Optional[str] = Field(None, description="Product dimensions")
    material: Optional[str] = Field(None, description="Primary material")
    color: Optional[str] = Field(None, description="Color options")
    warranty: Optional[str] = Field(None, description="Warranty period")
    # New fields to showcase more types
    certification_date: Optional[date] = Field(None, description="Certification date")
    testing_time: Optional[time] = Field(None, description="Testing time")
    quality_grade: Optional[Literal["A", "B", "C", "D"]] = Field(
        None, description="Quality grade"
    )

    def __str__(self) -> str:
        specs = [s for s in [self.weight, self.dimensions, self.material] if s]
        return f"{len(specs)} specifications"


class Review(BaseModel):
    rating: int = Field(description="Rating out of 5 stars", ge=1, le=5)
    title: str = Field(description="Review title")
    content: str = Field(description="Review content")
    reviewer: str = Field(description="Reviewer name")
    verified_purchase: bool = Field(description="Whether this is a verified purchase")
    # New fields to showcase more types
    review_date: date = Field(description="Date of review")
    review_time: time = Field(description="Time of review")
    helpfulness: Literal[
        "very_helpful", "helpful", "somewhat_helpful", "not_helpful"
    ] = Field(description="Review helpfulness rating")
    reviewer_level: Optional[Literal["beginner", "intermediate", "expert"]] = Field(
        None, description="Reviewer experience level"
    )

    def __str__(self) -> str:
        stars = "⭐" * int(self.rating)
        return f"{stars} {self.title} - {self.reviewer}"


class ExtractedProduct(BaseModel):
    """Enhanced extracted product information showcasing all field types"""

    # Basic product info
    product: ProductInfo = Field(description="Core product information")

    # Features and specs
    key_features: List[str] = Field(
        default_factory=list, description="Main product features"
    )
    specifications: Specifications = Field(
        default_factory=lambda: Specifications(
            weight=None,
            dimensions=None,
            material=None,
            color=None,
            warranty=None,
            certification_date=None,
            testing_time=None,
            quality_grade=None,
        ),
        description="Technical specifications",
    )

    # Customer reviews
    reviews: List[Review] = Field(
        default_factory=list, description="Customer reviews and ratings"
    )

    # Description and metadata
    description: str = Field(description="Product description")
    target_audience: Optional[str] = Field(None, description="Target customer segment")

    # Date and time fields
    extraction_date: date = Field(description="Date of extraction")
    extraction_time: time = Field(description="Time of extraction")
    last_updated: Optional[date] = Field(None, description="Last update date")
    scheduled_review_time: Optional[time] = Field(
        None, description="Scheduled review time"
    )

    # Literal fields for constrained choices
    extraction_status: Literal["pending", "processing", "completed", "failed"] = Field(
        description="Current extraction status"
    )
    data_source: Literal["web_scraping", "api", "manual_entry", "file_upload"] = Field(
        description="Source of the data"
    )
    language: Optional[Literal["en", "es", "fr", "de", "it"]] = Field(
        None, description="Content language"
    )

    # Numeric fields with optionals
    extraction_confidence: float = Field(0.0, description="Extraction confidence score")
    processing_time_seconds: Optional[float] = Field(
        None, description="Processing time in seconds"
    )
    retry_count: Optional[int] = Field(None, description="Number of retry attempts")

    # Boolean fields with optionals
    requires_human_review: bool = Field(
        False, description="Whether human review is required"
    )
    is_complete: Optional[bool] = Field(
        None, description="Whether extraction is complete"
    )
    contains_sensitive_data: Optional[bool] = Field(
        None, description="Whether data contains sensitive information"
    )

    # String fields with optionals
    validation_status: str = Field(
        "PENDING", description="Validation status of extraction"
    )
    data_quality: str = Field("UNKNOWN", description="Overall data quality assessment")
    extraction_method: str = Field("AUTO", description="Method used for extraction")
    error_message: Optional[str] = Field(
        None, description="Error message if extraction failed"
    )
    notes: Optional[str] = Field(None, description="Additional notes")

    # Metadata
    source_url: Optional[str] = Field(None, description="Source listing URL")
    extracted_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now, description="Extraction timestamp"
    )

    # Additional nested lists to showcase complex structures
    tags: List[str] = Field(default_factory=list, description="Product tags")
    related_products: List[str] = Field(
        default_factory=list, description="Related product IDs"
    )


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
        release_date=date(2023, 3, 15),
        availability_time=time(9, 0),
        priority=Priority.HIGH,
        discount_percentage=15.0,
        is_featured=True,
    ),
    key_features=[
        "Waterproof up to 50 meters",
        "10.5 hours battery life",
        "Built-in GPS tracking",
        "Sleep quality analysis",
    ],
    specifications=Specifications(
        weight="45g",
        dimensions="44mm × 38mm × 10.7mm",
        material="Aluminum case with silicone band",
        color="Black, Silver, Rose Gold",
        warranty="1 year limited warranty",
        certification_date=date(2023, 1, 20),
        testing_time=time(14, 30),
        quality_grade="A",
    ),
    reviews=[
        Review(
            rating=5,
            title="Perfect for my morning runs!",
            content="Works great!",
            reviewer="Sarah M.",
            verified_purchase=True,
            review_date=date(2023, 6, 10),
            review_time=time(10, 15),
            helpfulness="very_helpful",
            reviewer_level="intermediate",
        ),
        Review(
            rating=4,
            title="Good tracker but battery could be better",
            content="I've been using this fitness tracker for about 3 months now and overall I'm pretty satisfied with it. The heart rate monitoring is accurate and the GPS tracking works well during my outdoor runs. The sleep tracking feature has been really helpful in understanding my sleep patterns. However, I do wish the battery life was longer - I find myself charging it every 8-9 hours instead of the advertised 10.5 hours. The build quality feels solid and the waterproofing has held up well through multiple swimming sessions. The app interface is intuitive and syncs quickly with my phone. Would recommend for casual fitness enthusiasts, though serious athletes might want something with longer battery life.",
            reviewer="Mike R.",
            verified_purchase=True,
            review_date=date(2023, 5, 22),
            review_time=time(18, 45),
            helpfulness="helpful",
            reviewer_level="expert",
        ),
        Review(
            rating=5,
            title="Exceeded expectations in every way",
            content="This is hands down the best fitness tracker I've owned. The accuracy of the heart rate monitor is impressive - I've compared it to medical-grade equipment and it's consistently within 1-2 BPM. The GPS locks on quickly and tracks my routes perfectly. The sleep analysis has helped me identify patterns I never noticed before. The build quality is exceptional - the aluminum case feels premium and the silicone band is comfortable even during long workouts. Battery life easily lasts the full 10+ hours as advertised. The companion app is well-designed with detailed analytics and helpful insights. Customer support was also excellent when I had a question about syncing. Worth every penny and I'd buy it again in a heartbeat.",
            reviewer="Jennifer L.",
            verified_purchase=True,
            review_date=date(2023, 4, 8),
            review_time=time(20, 30),
            helpfulness="very_helpful",
            reviewer_level="expert",
        ),
        Review(
            rating=3,
            title="Mixed feelings",
            content="Some features work well, others don't. GPS is spotty indoors.",
            reviewer="Tom W.",
            verified_purchase=False,
            review_date=date(2023, 7, 2),
            review_time=time(12, 0),
            helpfulness="somewhat_helpful",
            reviewer_level=None,
        ),
    ],
    description=(
        "The Smart Fitness Tracker Pro Max combines cutting-edge health monitoring "
        "technology with sleek design. Track your workouts, monitor your heart rate 24/7, "
        "and gain insights into your sleep patterns. Perfect for athletes and fitness "
        "enthusiasts who demand precision and style."
    ),
    target_audience="Athletes and fitness enthusiasts aged 18-45",
    extraction_date=date(2023, 8, 1),
    extraction_time=time(9, 30),
    last_updated=date(2023, 8, 15),
    scheduled_review_time=time(16, 0),
    extraction_status="completed",
    data_source="web_scraping",
    language="en",
    extraction_confidence=1.0,
    processing_time_seconds=2.5,
    retry_count=0,
    requires_human_review=False,
    is_complete=True,
    contains_sensitive_data=False,
    validation_status="VERIFIED",
    data_quality="HIGH",
    extraction_method="MANUAL",
    error_message=None,
    notes="High-quality extraction with manual verification",
    source_url="https://example.com/products/fittech-tracker-pro-max",
    tags=["fitness", "tracker", "waterproof", "gps", "heart-rate"],
    related_products=["fittech-basic", "fittech-ultra", "competitor-tracker-x"],
)

# LLM-generated extraction (with typical errors)
generated_output = ExtractedProduct(
    product=ProductInfo(
        name="Smart Fitness Tracker ProMax",  # Missing space
        brand="FitTech",
        category=Category.ELECTRONICS,  # Wrong category!
        price=299.0,  # Missing cents
        in_stock=True,
        release_date=date(2023, 3, 16),  # Wrong date
        availability_time=time(9, 30),  # Wrong time
        priority=Priority.MEDIUM,  # Wrong priority
        discount_percentage=None,  # Failed to extract
        is_featured=None,  # Failed to extract
    ),
    key_features=[
        "Waterproof up to 50 meters",
        "10 hours battery life",  # Rounded down
        # "Built-in GPS tracking",  # MISSED THIS FEATURE
        # "Sleep quality analysis",  # MISSED THIS TOO
    ],
    specifications=Specifications(
        weight=None,  # Failed to extract
        dimensions="44mm x 38mm x 10.7mm",  # Different separator
        material="Aluminum case with silicone band",
        color="Black, Silver, Rose Gold",
        warranty="1 year",  # Missing "limited"
        certification_date=None,  # Failed to extract
        testing_time=None,  # Failed to extract
        quality_grade="B",  # Wrong grade
    ),
    reviews=[
        Review(
            rating=5,
            title="Perfect for my morning runs!",
            content="Works great!",
            reviewer="Sarah M.",
            verified_purchase=True,
            review_date=date(2023, 6, 10),
            review_time=time(10, 15),
            helpfulness="very_helpful",
            reviewer_level="intermediate",
        ),
        Review(
            rating=4,
            title="Good tracker but battery could be better",
            content="I've been using this fitness tracker for about 3 months now and overall I'm pretty satisfied with it. The heart rate monitoring is accurate and the GPS tracking works well during my outdoor runs. However, I do wish the battery life was longer - I find myself charging it every 8-9 hours instead of the advertised 10.5 hours.",
            reviewer="Mike R.",
            verified_purchase=True,
            review_date=date(2023, 5, 22),
            review_time=time(18, 45),
            helpfulness="helpful",
            reviewer_level="expert",
        ),
        # Missing the longest review - extraction failed
        Review(
            rating=2,  # Different rating extracted
            title="Not great",  # Different title
            content="GPS doesn't work well.",  # Much shorter content
            reviewer="Tom W.",
            verified_purchase=False,
            review_date=date(2023, 7, 1),  # Wrong date
            review_time=time(11, 30),  # Wrong time
            helpfulness="not_helpful",  # Wrong helpfulness
            reviewer_level=None,
        ),
        # Extra review that wasn't in ground truth
        Review(
            rating=4,
            title="Decent value for money",
            content="Good basic features but missing some advanced options. The heart rate monitor works fine for basic tracking. Setup was straightforward and the app is user-friendly. Build quality seems solid so far after 2 weeks of use. Sleep tracking provides some useful insights though not as detailed as I'd hoped. For the price point, it's a reasonable choice if you don't need all the bells and whistles of premium trackers.",
            reviewer="Alex K.",
            verified_purchase=True,
            review_date=date(2023, 7, 10),
            review_time=time(14, 20),
            helpfulness="helpful",
            reviewer_level="beginner",
        ),
    ],
    description=(
        "This fitness tracker offers advanced health monitoring features with an elegant design. "
        "It tracks workouts, monitors heart rate continuously, and provides sleep insights. "
        "Ideal for those who want to stay fit and stylish."
        # Paraphrased, lost specific marketing language
    ),
    target_audience=None,  # Failed to extract
    extraction_date=date(2023, 8, 1),
    extraction_time=time(9, 25),  # Wrong time
    last_updated=None,  # Failed to extract
    scheduled_review_time=time(15, 0),  # Wrong time
    extraction_status="processing",  # Wrong status
    data_source="api",  # Wrong source
    language=None,  # Failed to extract
    extraction_confidence=0.73,
    processing_time_seconds=4.2,  # Higher processing time
    retry_count=2,  # Had retries
    requires_human_review=True,  # Correctly identified need for review
    is_complete=False,  # Incomplete
    contains_sensitive_data=None,  # Failed to extract
    validation_status="NEEDS_REVIEW",
    data_quality="MEDIUM",
    extraction_method="AUTO",
    error_message="Some fields could not be extracted with high confidence",
    notes="Requires manual review for accuracy",
    source_url="https://example.com/products/fittech-tracker-pro-max",
    tags=["fitness", "tracker"],  # Missing tags
    related_products=["fittech-basic"],  # Missing related products
)


# ============================================================================
# Production-Ready Evaluation Metrics for Product Extraction Quality Assessment
# ============================================================================

eval_metrics = {
    # Product info metrics - realistic evaluation scores
    "product": {
        "metric": 0.75,
        "comment": "Overall accuracy: 6/10 fields correct. Category classification and date extraction errors detected.",
    },
    "product.name": {
        "metric": 0.90,
        "comment": "Name extracted with minor formatting issue: missing space in compound word",
    },
    "product.brand": {
        "metric": 1.0,
        "comment": "Brand name perfectly extracted - exact match with source",
    },
    "product.category": {
        "metric": 0.0,
        "comment": "Critical error: Miscategorized as Electronics instead of Sports & Outdoors",
    },
    "product.price": {
        "metric": 0.95,
        "comment": "Price extracted correctly but lost decimal precision (299.00 vs 299.99)",
    },
    "product.in_stock": {
        "metric": 1.0,
        "comment": "Stock status correctly identified as available",
    },
    "product.release_date": {
        "metric": 0.85,
        "comment": "Release date extracted but off by one day (2023-03-16 vs 2023-03-15)",
    },
    "product.availability_time": {
        "metric": 0.70,
        "comment": "Availability time partially correct but 30 minutes off (9:30 vs 9:00)",
    },
    "product.priority": {
        "metric": 0.60,
        "comment": "Priority level incorrect: extracted as MEDIUM instead of HIGH",
    },
    "product.discount_percentage": {
        "metric": 0.0,
        "comment": "Discount percentage not extracted - field missing from output",
    },
    "product.is_featured": {
        "metric": 0.0,
        "comment": "Featured status not extracted - field missing from output",
    },
    # Features extraction quality
    "key_features": {
        "metric": 0.50,
        "comment": "Feature extraction incomplete: 2/4 key features captured, 2 critical features missed",
    },
    "key_features[0]": {
        "metric": 1.0,
        "comment": "Waterproof specification perfectly extracted with correct technical details",
    },
    "key_features[1]": {
        "metric": 0.80,
        "comment": "Battery life captured but rounded down (10.0h vs 10.5h) - minor precision loss",
    },
    "key_features.missing_items": {
        "metric": 0.0,
        "comment": "Critical features not extracted: GPS tracking, sleep analysis - major content gaps",
    },
    # Technical specifications quality
    "specifications": {
        "metric": 0.65,
        "comment": "Specification extraction: 5/8 fields captured with varying accuracy",
    },
    "specifications.weight": {
        "metric": 0.0,
        "comment": "Weight specification not found in source content - extraction failed",
    },
    "specifications.dimensions": {
        "metric": 0.85,
        "comment": "Dimensions extracted but formatting normalized (× symbol → x)",
    },
    "specifications.material": {
        "metric": 1.0,
        "comment": "Material description captured perfectly - complete and accurate",
    },
    "specifications.color": {
        "metric": 1.0,
        "comment": "Color options extracted completely and accurately",
    },
    "specifications.warranty": {
        "metric": 0.67,
        "comment": "Warranty period captured but missing 'limited' qualifier - partial extraction",
    },
    "specifications.certification_date": {
        "metric": 0.0,
        "comment": "Certification date not extracted - field missing from output",
    },
    "specifications.testing_time": {
        "metric": 0.0,
        "comment": "Testing time not extracted - field missing from output",
    },
    "specifications.quality_grade": {
        "metric": 0.75,
        "comment": "Quality grade extracted but incorrect: B instead of A",
    },
    # Content quality assessment
    "description": {
        "metric": 0.78,
        "comment": "Product description adequately captured but simplified - marketing tone lost",
    },
    "target_audience": {
        "metric": 0.0,
        "comment": "Target audience not identified - field extraction failed",
    },
    # Date and time fields
    "extraction_date": {
        "metric": 1.0,
        "comment": "Extraction date correctly recorded",
    },
    "extraction_time": {
        "metric": 0.92,
        "comment": "Extraction time close but 5 minutes off (9:25 vs 9:30)",
    },
    "last_updated": {
        "metric": 0.0,
        "comment": "Last updated date not extracted - field missing from output",
    },
    "scheduled_review_time": {
        "metric": 0.75,
        "comment": "Scheduled review time extracted but 1 hour off (15:00 vs 16:00)",
    },
    # Literal fields
    "extraction_status": {
        "metric": 0.0,
        "comment": "Status incorrect: processing instead of completed",
    },
    "data_source": {
        "metric": 0.0,
        "comment": "Data source incorrect: api instead of web_scraping",
    },
    "language": {
        "metric": 0.0,
        "comment": "Language not extracted - field missing from output",
    },
    # Numeric fields
    "extraction_confidence": {
        "metric": 1.0,
        "comment": "Model confidence score (0.73) accurately reflects actual performance",
    },
    "processing_time_seconds": {
        "metric": 0.80,
        "comment": "Processing time recorded but higher than actual (4.2s vs 2.5s)",
    },
    "retry_count": {
        "metric": 0.50,
        "comment": "Retry count recorded but inaccurate (2 vs 0)",
    },
    # Boolean fields
    "requires_human_review": {
        "metric": 1.0,
        "comment": "Human review requirement correctly identified as true",
    },
    "is_complete": {
        "metric": 1.0,
        "comment": "Completion status correctly identified as false",
    },
    "contains_sensitive_data": {
        "metric": 0.0,
        "comment": "Sensitive data assessment not extracted - field missing from output",
    },
    # String fields with custom colors for status indicators
    "validation_status": {
        "metric": "NEEDS_REVIEW",  # Status requiring human attention
        "color": "#F59E0B",  # Amber for review-required status
        "comment": "Extraction requires human review due to category classification error",
    },
    "data_quality": {
        "metric": "ACCEPTABLE",  # Quality assessment for production readiness
        "color": "#10B981",  # Green for acceptable quality
        "comment": "Data quality sufficient for publication with minor corrections needed",
    },
    "extraction_method": {
        "metric": "AUTOMATED",  # Method type for audit trail
        "color": "#6B7280",  # Gray for neutral system info
        "comment": "Fully automated extraction - consider manual verification for critical errors",
    },
    "error_message": {
        "metric": 0.80,
        "comment": "Error message appropriately captured extraction issues",
    },
    "notes": {
        "metric": 0.75,
        "comment": "Notes field captured but could be more detailed",
    },
    # List fields
    "tags": {
        "metric": 0.40,
        "comment": "Tag extraction incomplete: 2/5 tags captured, missing key descriptors",
    },
    "related_products": {
        "metric": 0.33,
        "comment": "Related products extraction incomplete: 1/3 products captured",
    },
    # Reviews extraction metrics
    "reviews": {
        "metric": 0.65,
        "comment": "Review extraction partially successful: 4/4 reviews found but content quality varies",
    },
    "reviews[0]": {
        "metric": 1.0,
        "comment": "First review extracted perfectly - exact match with source",
    },
    "reviews[0].review_date": {
        "metric": 1.0,
        "comment": "Review date correctly extracted",
    },
    "reviews[0].review_time": {
        "metric": 1.0,
        "comment": "Review time correctly extracted",
    },
    "reviews[0].helpfulness": {
        "metric": 1.0,
        "comment": "Helpfulness rating correctly extracted",
    },
    "reviews[0].reviewer_level": {
        "metric": 1.0,
        "comment": "Reviewer level correctly extracted",
    },
    "reviews[1]": {
        "metric": 0.75,
        "comment": "Review content truncated - missing key details about sleep tracking and app interface",
    },
    "reviews[1].review_date": {
        "metric": 1.0,
        "comment": "Review date correctly extracted",
    },
    "reviews[1].review_time": {
        "metric": 1.0,
        "comment": "Review time correctly extracted",
    },
    "reviews[1].helpfulness": {
        "metric": 1.0,
        "comment": "Helpfulness rating correctly extracted",
    },
    "reviews[1].reviewer_level": {
        "metric": 1.0,
        "comment": "Reviewer level correctly extracted",
    },
    "reviews[2]": {
        "metric": 0.30,
        "comment": "Critical extraction errors: wrong rating (2 vs 3), different title, severely truncated content",
    },
    "reviews[2].review_date": {
        "metric": 0.85,
        "comment": "Review date close but off by one day (2023-07-01 vs 2023-07-02)",
    },
    "reviews[2].review_time": {
        "metric": 0.75,
        "comment": "Review time off by 30 minutes (11:30 vs 12:00)",
    },
    "reviews[2].helpfulness": {
        "metric": 0.0,
        "comment": "Helpfulness rating incorrect: not_helpful instead of somewhat_helpful",
    },
    "reviews[2].reviewer_level": {
        "metric": 1.0,
        "comment": "Reviewer level correctly extracted as None",
    },
    "reviews[3]": {
        "metric": 0.0,
        "comment": "Hallucinated review - this review does not exist in the original source data",
    },
    "reviews[3].review_date": {
        "metric": 0.0,
        "comment": "Hallucinated review date - not from original source",
    },
    "reviews[3].review_time": {
        "metric": 0.0,
        "comment": "Hallucinated review time - not from original source",
    },
    "reviews[3].helpfulness": {
        "metric": 0.0,
        "comment": "Hallucinated helpfulness rating - not from original source",
    },
    "reviews[3].reviewer_level": {
        "metric": 0.0,
        "comment": "Hallucinated reviewer level - not from original source",
    },
}


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
    metrics_dict={},  # No metrics on left side
)

# Right form: Generated output (read-only)
generated_form = PydanticForm(
    form_name="generated_output",
    model_class=ExtractedProduct,
    initial_values=generated_output,
    # disabled=True,  # Cannot be edited
    spacing="compact",
    exclude_fields=["extracted_at", "source_url"],
    metrics_dict=eval_metrics,  # Metrics show on generated side
)

# Create comparison form
comparison_form = ComparisonForm(
    name="product_extraction_comparison",
    left_form=truth_form,
    right_form=generated_form,
    left_label="📝 Annotated Truth (Ground Truth)",
    right_label="🤖 LLM Generated Output",
    copy_left=True,
    copy_right=True,
)


comparison_form.register_routes(app)


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
                        "Production-ready ML evaluation interface comparing LLM output with ground truth. Uses automatic red/green color coding based on 0.0-1.0 scores with custom colors for specific status indicators.",
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
                                # Form controls - use comparison form's button helpers
                                fh.Div(
                                    comparison_form.left_reset_button(
                                        "↩️ Reset Annotation",
                                    ),
                                    comparison_form.left_refresh_button(
                                        "🔄 Refresh Display",
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
