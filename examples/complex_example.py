import datetime
import logging
from decimal import Decimal
from enum import Enum, IntEnum
from typing import List, Literal, Optional
from uuid import uuid4

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field, ValidationError
from pydantic.json_schema import SkipJsonSchema

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.field_renderers import BaseFieldRenderer

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


class Address(BaseModel):
    street: str = "123 Main St"
    city: str  # = "Anytown"
    is_billing: bool = False
    tags: List[str] = Field(default=["tag1"], description="Tags for the address")
    # SkipJsonSchema fields - normally hidden but can be selectively shown
    internal_id: SkipJsonSchema[str] = Field(  # type: ignore
        default_factory=lambda: f"addr_{uuid4().hex[:8]}",
        description="Internal address tracking ID (system use only)",
    )
    audit_notes: SkipJsonSchema[List[str]] = Field(  # type: ignore
        default_factory=list,
        description="Internal audit notes (system use only)",
    )

    def __str__(self) -> str:
        return f"{self.street}, {self.city} ({'billing' if self.is_billing else 'shipping'})"


class CustomDetail(BaseModel):
    value: str = "Default value"
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

    def __str__(self) -> str:
        return f"{self.value} ({self.confidence})"


class CustomerTypeEnum(Enum):
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"


class PriorityIntEnum(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class CustomDetailFieldRenderer(BaseFieldRenderer):
    """display value input and dropdown side by side for Detail"""

    def render_input(self):
        current_value_val = ""
        current_confidence = "MEDIUM"
        if isinstance(self.value, dict):
            current_value_val = str(self.value.get("value", "") or "")
            current_confidence = str(self.value.get("confidence", "MEDIUM") or "MEDIUM")
        elif self.value is not None:
            current_value_val = str(getattr(self.value, "value", "") or "")
            current_confidence = str(
                getattr(self.value, "confidence", "MEDIUM") or "MEDIUM"
            )

        value_input = fh.Div(
            mui.Input(
                value=current_value_val,
                id=f"{self.field_name}_value",
                name=f"{self.field_name}_value",
                placeholder=f"Enter {self.original_field_name.replace('_', ' ')} value",
                cls="uk-input w-full",  # apply some custom css
            ),
            cls="flex-grow",
        )

        confidence_options_ft = [
            fh.Option(
                opt,
                value=opt,
                selected=(opt == current_confidence),
            )
            for opt in ["HIGH", "MEDIUM", "LOW"]
        ]

        confidence_select = mui.Select(
            *confidence_options_ft,
            id=f"{self.field_name}_confidence",
            name=f"{self.field_name}_confidence",
            cls_wrapper="w-[110px] min-w-[110px] flex-shrink-0",  # apply some custom css
        )

        return fh.Div(
            value_input,
            confidence_select,
            cls="flex items-start gap-2 w-full",  # apply some custom css
        )


class ComplexSchema(BaseModel):
    """
    Complex schema demonstrating various field types for form generation

    This model includes simple types, dates, literals, and nested models to
    showcase all the rendering capabilities of the form system.
    """

    skip_field: str = Field(description="This field will be skipped")
    # SkipJsonSchema fields - normally hidden from forms
    document_id: SkipJsonSchema[str] = Field(  # type: ignore
        default_factory=lambda: f"doc_{uuid4().hex[:12]}",
        description="Document tracking ID (system generated)",
    )
    created_at: SkipJsonSchema[datetime.datetime] = Field(  # type: ignore
        default_factory=datetime.datetime.now,
        description="Creation timestamp (system managed)",
    )
    version: SkipJsonSchema[int] = Field(  # type: ignore
        default=1, description="Document version (system managed)"
    )
    security_flags: SkipJsonSchema[List[str]] = Field(  # type: ignore
        default_factory=lambda: ["verified", "approved"],
        description="Security flags (admin only)",
    )
    name: str = Field(description="Name of the customer")
    age: int = Field(description="Age of the customer")
    score: float = Field(description="Score of the customer")
    balance: Decimal = Field(description="Account balance (decimal precision)")
    is_active: bool = Field(description="Is the customer active")
    description: Optional[str] = Field(description="Description of the customer")
    customer_type: CustomerTypeEnum = Field(description="Type of the customer")
    priority: Optional[PriorityIntEnum] = Field(
        None, description="Priority of the customer"
    )

    # Date and time fields
    creation_date: datetime.date = Field(
        default_factory=datetime.date.today, description="Creation date of the customer"
    )
    start_time: datetime.time = Field(
        default_factory=lambda: datetime.datetime.now().time().replace(microsecond=0),
        description="Start time of the customer",
    )

    # Literal/enum field
    status: Literal["PENDING", "PROCESSING", "COMPLETED"] = Field(
        description="Status of the customer"
    )
    # Optional fields
    optional_status: Optional[Literal["PENDING", "PROCESSING", "COMPLETED"]] = Field(
        description="Optional status of the customer"
    )

    # Lists of simple types
    tags: List[str] = Field(
        default_factory=lambda: ["tag1", "tag2"], description="Tags of the customer"
    )

    # List[Literal] - renders as pills with dropdown (NEW!)
    selected_regions: List[Literal["EMEA", "APAC", "AMERICAS", "OTHER"]] = Field(
        default_factory=lambda: ["EMEA"],
        description="Selected regions for the customer (pill/tag selector)",
    )

    # List[Enum] - also renders as pills with dropdown (NEW!)
    active_priorities: List[PriorityIntEnum] = Field(
        default_factory=list,
        description="Active priority levels (pill/tag selector)",
    )

    # Nested model
    main_address: Address = Field(
        default_factory=lambda: Address(), description="Main address of the customer"
    )
    # list of nested models
    other_addresses: List[Address] = Field(
        default_factory=list, description="Other addresses of the customer"
    )

    # single custom nested model
    custom_detail: CustomDetail = Field(
        default_factory=lambda: CustomDetail(),
        description="Custom detail of the customer",
    )
    # list of custom nested models
    more_custom_details: List[CustomDetail] = Field(
        default_factory=list, description="More custom details of the customer"
    )

    # --- EXCLUDED FIELDS WITH DEFAULTS ---
    # These fields will be excluded from the form but will have their defaults injected
    internal_id: str = Field(
        default="AUTO_GENERATED_ID",
        description="Internal system ID (auto-generated, not shown in form)",
    )
    audit_trail: List[str] = Field(
        default_factory=lambda: ["Created", "Initialized"],
        description="Audit trail (system managed, not shown in form)",
    )
    system_metadata: dict = Field(
        default_factory=lambda: {"version": "1.0", "source": "web_form"},
        description="System metadata (auto-populated, not shown in form)",
    )
    processing_flags: Optional[dict] = Field(
        default=None, description="Processing flags (system use only)"
    )
    backup_address: Address = Field(
        default_factory=lambda: Address(
            street="Backup St", city="Backup City", is_billing=False
        ),
        description="Backup address (auto-generated, not shown in form)",
    )
    optional_list: Optional[List[str]] = Field(
        default=None, description="Optional list of strings"
    )


# Create an initial model with example data
initial_values = ComplexSchema(
    skip_field="This field will be skipped",
    # SkipJsonSchema field values - these will be hidden by default
    document_id="DEMO_DOC_12345ABC",
    created_at=datetime.datetime(2023, 1, 1, 10, 30, 0),
    version=5,
    security_flags=["demo", "test", "verified"],
    name="Demo User",
    age=42,
    score=88.5,
    balance=Decimal("1234.56"),
    is_active=True,
    description="Demo description",
    customer_type=CustomerTypeEnum.INDIVIDUAL,
    priority=PriorityIntEnum.HIGH,
    creation_date=datetime.date(2023, 1, 1),
    start_time=datetime.time(12, 0, 0),
    status="PENDING",
    optional_status=None,
    tags=["tag1", "tag2", "tag3"],
    # NEW: List[Literal] and List[Enum] fields for pill/tag selector demo
    selected_regions=["EMEA", "APAC"],
    active_priorities=[PriorityIntEnum.HIGH, PriorityIntEnum.MEDIUM],
    main_address=Address(
        street="123 Main St",
        city="Anytown",
        is_billing=True,
        internal_id="MAIN_ADDR_001",
        audit_notes=["Created as main", "Verified address"],
    ),
    custom_detail=CustomDetail(value="Main Detail", confidence="HIGH"),
    other_addresses=[
        Address(
            street="456 Second St",
            city="Othertown",
            is_billing=False,
            internal_id="OTHER_ADDR_002",
            audit_notes=["Secondary address", "Shipping only"],
        ),
        Address(
            street="789 Third St",
            city="Thirdville",
            is_billing=True,
            internal_id="OTHER_ADDR_003",
            audit_notes=["Backup billing", "High priority"],
        ),
    ],
    more_custom_details=[
        CustomDetail(value="Detail 1", confidence="HIGH"),
        CustomDetail(value="Detail 2", confidence="MEDIUM"),
        CustomDetail(value="Detail 3", confidence="LOW"),
    ],
    # Custom values for excluded fields (these will override model defaults)
    internal_id="DEMO_USER_12345",
    audit_trail=["Created", "Demo initialized", "Form loaded"],
    system_metadata={"version": "1.2", "source": "demo_form", "demo_mode": True},
    processing_flags={"priority": "high", "demo": True},
    backup_address=Address(
        street="999 Demo Backup St", city="Demo City", is_billing=False
    ),
)

# Create two form renderers with different spacing themes for comparison
form_renderer_normal = PydanticForm(
    form_name="main_form_normal",
    model_class=ComplexSchema,
    initial_values=initial_values,
    custom_renderers=[
        (CustomDetail, CustomDetailFieldRenderer)
    ],  # Register Detail renderer
    exclude_fields=[
        "skip_field",
        # Exclude the new fields with defaults - these will be auto-injected
        "internal_id",
        "audit_trail",
        "system_metadata",
        "processing_flags",
        "backup_address",
    ],
    label_colors={
        # Basic fields
        "name": "blue",
        "age": "green",
        "score": "#FF0000",  # red
        "balance": "emerald",
        "is_active": "purple",
        "description": "orange",
        # Enum fields
        "customer_type": "teal",
        "priority": "cyan",
        # Date/time fields
        "creation_date": "pink",
        "start_time": "indigo",
        # Status fields
        "status": "yellow",
        "optional_status": "lime",
        # List fields
        "tags": "amber",
        # NEW: List[Literal] and List[Enum] pill/tag fields
        "selected_regions": "sky",
        "active_priorities": "fuchsia",
        # Nested model fields
        "main_address": "emerald",
        "other_addresses": "red",
        "custom_detail": "violet",
        "more_custom_details": "rose",
    },  # Customize field label colors - see README "Label Colors" section
    spacing="normal",
)

form_renderer_compact = PydanticForm(
    form_name="main_form_compact",
    model_class=ComplexSchema,
    initial_values=initial_values.model_dump(),  # also works with dict
    custom_renderers=[
        (CustomDetail, CustomDetailFieldRenderer)
    ],  # Register Detail renderer
    exclude_fields=[
        "skip_field",
        # Exclude the new fields with defaults - these will be auto-injected
        "internal_id",
        "audit_trail",
        "system_metadata",
        "processing_flags",
        "backup_address",
    ],
    label_colors={
        # Basic fields
        "name": "blue",
        "age": "green",
        "score": "#FF0000",  # red
        "balance": "emerald",
        "is_active": "purple",
        "description": "orange",
        # Enum fields
        "customer_type": "teal",
        "priority": "cyan",
        # Date/time fields
        "creation_date": "pink",
        "start_time": "indigo",
        # Status fields
        "status": "yellow",
        "optional_status": "lime",
        # List fields
        "tags": "amber",
        # NEW: List[Literal] and List[Enum] pill/tag fields
        "selected_regions": "sky",
        "active_priorities": "fuchsia",
        # Nested model fields
        "main_address": "emerald",
        "other_addresses": "red",
        "custom_detail": "violet",
        "more_custom_details": "rose",
    },
    spacing="compact",
)

# Create a third form demonstrating SkipJsonSchema with keep_skip_json_fields
form_renderer_skip_demo = PydanticForm(
    form_name="main_form_skip_demo",
    model_class=ComplexSchema,
    initial_values=initial_values.model_dump(),
    custom_renderers=[(CustomDetail, CustomDetailFieldRenderer)],
    exclude_fields=[
        "skip_field",
        # Still exclude the regular excluded fields
        "internal_id",
        "audit_trail",
        "system_metadata",
        "processing_flags",
        "backup_address",
    ],
    # DEMO: Selectively keep some SkipJsonSchema fields visible!
    keep_skip_json_fields=[
        "document_id",  # Top-level skip field
        "version",  # Another top-level skip field
        "main_address.internal_id",  # Nested skip field
        "other_addresses.audit_notes",  # Skip field in list items
    ],
    label_colors={
        # Basic fields
        "name": "blue",
        "age": "green",
        "score": "#FF0000",
        "balance": "emerald",
        "is_active": "purple",
        "description": "orange",
        # SkipJsonSchema fields that are kept
        "document_id": "red",
        "version": "amber",
        # Enum fields
        "customer_type": "teal",
        "priority": "cyan",
        # Date/time fields
        "creation_date": "pink",
        "start_time": "indigo",
        # Status fields
        "status": "yellow",
        "optional_status": "lime",
        # List fields
        "tags": "amber",
        # NEW: List[Literal] and List[Enum] pill/tag fields
        "selected_regions": "sky",
        "active_priorities": "fuchsia",
        # Nested model fields
        "main_address": "emerald",
        "other_addresses": "red",
        "custom_detail": "violet",
        "more_custom_details": "rose",
    },
    spacing="normal",
)

# Register routes for all three forms
form_renderer_normal.register_routes(app)
form_renderer_compact.register_routes(app)
form_renderer_skip_demo.register_routes(app)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.H1("FastHTML/MonsterUI Pydantic Form Demo"),
            # Comprehensive feature overview
            mui.Card(
                mui.CardHeader(
                    fh.H2("🚀 Complete Feature Demonstration", cls="text-purple-600")
                ),
                mui.CardBody(
                    fh.P(
                        "This comprehensive demo showcases all major features of the fh-pydantic-form library:",
                        cls="text-lg mb-4",
                    ),
                    # Field Types Section
                    mui.Details(
                        mui.Summary(
                            fh.H3("📝 Field Types & Renderers", cls="text-blue-600")
                        ),
                        fh.Div(
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("String fields: "),
                                    "Basic text input with validation",
                                ),
                                fh.Li(
                                    fh.Strong("Numeric fields: "),
                                    "Integer and float inputs with proper parsing",
                                ),
                                fh.Li(
                                    fh.Strong("Boolean fields: "),
                                    "Checkbox inputs with proper on/off handling",
                                ),
                                fh.Li(
                                    fh.Strong("Date fields: "),
                                    "Date picker with ISO format parsing",
                                ),
                                fh.Li(
                                    fh.Strong("Time fields: "),
                                    "Time picker with proper time parsing",
                                ),
                                fh.Li(
                                    fh.Strong("Literal/Enum fields: "),
                                    "Dropdown selects with predefined options",
                                ),
                                fh.Li(
                                    fh.Strong("Optional fields: "),
                                    "Nullable fields with proper None handling",
                                ),
                                fh.Li(
                                    fh.Strong("List fields: "),
                                    "Dynamic lists with add/remove/reorder functionality",
                                ),
                                fh.Li(
                                    fh.Strong("Nested models: "),
                                    "Complex object fields with accordion UI",
                                ),
                                fh.Li(
                                    fh.Strong("Lists of nested models: "),
                                    "Dynamic lists of complex objects",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # Custom Renderers Section
                    mui.Details(
                        mui.Summary(
                            fh.H3("🎨 Custom Field Renderers", cls="text-green-600")
                        ),
                        fh.Div(
                            fh.P(
                                "Demonstrates custom renderer registration and implementation:"
                            ),
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("CustomDetailFieldRenderer: "),
                                    "Side-by-side value input and confidence dropdown",
                                ),
                                fh.Li(
                                    fh.Strong("Type-based registration: "),
                                    "Automatic renderer selection based on field type",
                                ),
                                fh.Li(
                                    fh.Strong("Custom UI components: "),
                                    "Tailored user experience for specific data types",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # Excluded Fields Section
                    mui.Details(
                        mui.Summary(
                            fh.H3(
                                "🔧 Excluded Fields with Auto-Injection",
                                cls="text-orange-600",
                            )
                        ),
                        fh.Div(
                            fh.P("Advanced functionality for system-managed fields:"),
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("Field exclusion: "),
                                    "Hide fields from UI while maintaining them in data model",
                                ),
                                fh.Li(
                                    fh.Strong("Default injection: "),
                                    "Automatically inject model defaults for excluded fields",
                                ),
                                fh.Li(
                                    fh.Strong("Initial value override: "),
                                    "initial_values take precedence over model defaults",
                                ),
                                fh.Li(
                                    fh.Strong("Complex defaults: "),
                                    "Support for default_factory functions and nested models",
                                ),
                                fh.Li(
                                    fh.Strong("System fields: "),
                                    "Perfect for audit trails, IDs, metadata, etc.",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            fh.P(
                                fh.Strong("Excluded fields in this demo: "),
                                fh.Code(", ".join(form_renderer_normal.exclude_fields)),
                                cls="text-sm text-gray-600 mt-2",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # SkipJsonSchema Section (NEW!)
                    mui.Details(
                        mui.Summary(
                            fh.H3(
                                "🔒 SkipJsonSchema Fields with Selective Keeping",
                                cls="text-red-600",
                            )
                        ),
                        fh.Div(
                            fh.P(
                                "Advanced SkipJsonSchema field management with selective visibility:"
                            ),
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("Hidden by default: "),
                                    "SkipJsonSchema fields are automatically hidden from forms",
                                ),
                                fh.Li(
                                    fh.Strong("Selective keeping: "),
                                    "Use keep_skip_json_fields to selectively show specific fields",
                                ),
                                fh.Li(
                                    fh.Strong("Nested field support: "),
                                    'Dot notation for nested fields: "main_address.internal_id"',
                                ),
                                fh.Li(
                                    fh.Strong("List item support: "),
                                    'Keep fields in list items: "other_addresses.audit_notes"',
                                ),
                                fh.Li(
                                    fh.Strong("Smart defaults: "),
                                    "Non-kept fields use model defaults, kept fields retain initial values",
                                ),
                                fh.Li(
                                    fh.Strong("Admin/debug use: "),
                                    "Perfect for admin panels or debugging interfaces",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            fh.P(
                                fh.Strong("Skip fields in this demo: "),
                                fh.Code(
                                    "document_id, created_at, version, security_flags, main_address.internal_id, other_addresses.audit_notes"
                                ),
                                cls="text-sm text-gray-600 mt-2",
                            ),
                            fh.P(
                                fh.Strong("Kept in SkipJsonSchema demo form: "),
                                fh.Code(
                                    ", ".join(
                                        form_renderer_skip_demo.keep_skip_json_fields
                                    )
                                ),
                                cls="text-sm text-green-600 mt-1",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # Form Features Section
                    mui.Details(
                        mui.Summary(
                            fh.H3("⚡ Dynamic Form Features", cls="text-purple-600")
                        ),
                        fh.Div(
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("HTMX integration: "),
                                    "Seamless dynamic updates without page reloads",
                                ),
                                fh.Li(
                                    fh.Strong("List manipulation: "),
                                    "Add, remove, and reorder list items with JavaScript",
                                ),
                                fh.Li(
                                    fh.Strong("Accordion UI: "),
                                    "Collapsible sections for complex nested data",
                                ),
                                fh.Li(
                                    fh.Strong("Form refresh: "),
                                    "Update display based on current form values",
                                ),
                                fh.Li(
                                    fh.Strong("Form reset: "),
                                    "Restore to initial values with confirmation",
                                ),
                                fh.Li(
                                    fh.Strong("Real-time validation: "),
                                    "Immediate feedback on form submission",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # Styling & UX Section
                    mui.Details(
                        mui.Summary(
                            fh.H3("🎯 Styling & User Experience", cls="text-indigo-600")
                        ),
                        fh.Div(
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("MonsterUI integration: "),
                                    "Beautiful, modern UI components",
                                ),
                                fh.Li(
                                    fh.Strong("Custom label colors: "),
                                    "Field-specific styling (name=blue, score=red)",
                                ),
                                fh.Li(
                                    fh.Strong("Spacing themes: "),
                                    "Normal and Compact spacing options for different use cases",
                                ),
                                fh.Li(
                                    fh.Strong("Responsive design: "),
                                    "Mobile-friendly layouts and interactions",
                                ),
                                fh.Li(
                                    fh.Strong("Accessibility: "),
                                    "Proper ARIA labels and keyboard navigation",
                                ),
                                fh.Li(
                                    fh.Strong("Visual feedback: "),
                                    "Success/error states with color coding",
                                ),
                                fh.Li(
                                    fh.Strong("Tooltips: "),
                                    "Helpful hints and explanations",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # Data Handling Section
                    mui.Details(
                        mui.Summary(
                            fh.H3("🔄 Robust Data Handling", cls="text-teal-600")
                        ),
                        fh.Div(
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("Schema drift resilience: "),
                                    "Graceful handling of model changes",
                                ),
                                fh.Li(
                                    fh.Strong("Type coercion: "),
                                    "Automatic conversion of form strings to proper types",
                                ),
                                fh.Li(
                                    fh.Strong("Validation integration: "),
                                    "Full Pydantic validation with detailed error messages",
                                ),
                                fh.Li(
                                    fh.Strong("Default value handling: "),
                                    "Smart use of model defaults and factories",
                                ),
                                fh.Li(
                                    fh.Strong("Nested data parsing: "),
                                    "Complex object reconstruction from flat form data",
                                ),
                                fh.Li(
                                    fh.Strong("List data parsing: "),
                                    "Dynamic list reconstruction with proper indexing",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    # Architecture Section
                    mui.Details(
                        mui.Summary(
                            fh.H3("🏗️ Architecture & Extensibility", cls="text-pink-600")
                        ),
                        fh.Div(
                            fh.Ul(
                                fh.Li(
                                    fh.Strong("Registry pattern: "),
                                    "Pluggable renderer system with type-based dispatch",
                                ),
                                fh.Li(
                                    fh.Strong("Generic typing: "),
                                    "Full TypeScript-like type safety with Python",
                                ),
                                fh.Li(
                                    fh.Strong("Route registration: "),
                                    "Automatic HTMX endpoint creation",
                                ),
                                fh.Li(
                                    fh.Strong("Prefix management: "),
                                    "Namespace isolation for multiple forms",
                                ),
                                fh.Li(
                                    fh.Strong("Event handling: "),
                                    "Comprehensive JavaScript integration",
                                ),
                                fh.Li(
                                    fh.Strong("Error handling: "),
                                    "Graceful degradation and user-friendly messages",
                                ),
                                cls="space-y-1 ml-4",
                            ),
                            cls="mt-2",
                        ),
                    ),
                    cls="space-y-3",
                ),
                cls="mb-6",
            ),
            mui.Details(
                mui.Summary("📋 Initial Values JSON (includes excluded field values)"),
                fh.Pre(
                    initial_values.model_dump_json(indent=2),
                    cls="bg-gray-100 p-4 rounded text-sm overflow-auto max-h-96",
                ),
                cls="mb-4",
            ),
            # Three-form comparison
            mui.Card(
                mui.CardHeader(
                    fh.H2("🎨 Form Feature Comparison", cls="text-purple-600")
                ),
                mui.CardBody(
                    fh.P(
                        "Compare three different form configurations: Normal spacing, Compact spacing, and SkipJsonSchema demo:",
                        cls="text-gray-600 mb-4",
                    ),
                    # Two-column layout for forms
                    fh.Div(
                        # Normal spacing form (left column)
                        fh.Div(
                            mui.Card(
                                mui.CardHeader(
                                    fh.H3("📏 Normal Spacing", cls="text-blue-600"),
                                    fh.P(
                                        "Standard spacing with comfortable margins",
                                        cls="text-sm text-gray-600",
                                    ),
                                ),
                                mui.CardBody(
                                    mui.Form(
                                        form_renderer_normal.render_inputs(),
                                        fh.Div(
                                            mui.Button(
                                                "🔍 Validate Normal",
                                                cls=mui.ButtonT.primary,
                                            ),
                                            form_renderer_normal.refresh_button("🔄"),
                                            form_renderer_normal.reset_button("↩️"),
                                            cls="mt-4 flex items-center gap-2 flex-wrap",
                                        ),
                                        hx_post="/submit_form_normal",
                                        hx_target="#result-normal",
                                        hx_swap="innerHTML",
                                        id=f"{form_renderer_normal.name}-form",
                                    )
                                ),
                            ),
                            fh.Div(id="result-normal", cls="mt-4"),
                            cls="w-full",
                        ),
                        # Compact spacing form (right column)
                        fh.Div(
                            mui.Card(
                                mui.CardHeader(
                                    fh.H3("📐 Compact Spacing", cls="text-green-600"),
                                    fh.P(
                                        "Minimal spacing for dense layouts",
                                        cls="text-sm text-gray-600",
                                    ),
                                ),
                                mui.CardBody(
                                    mui.Form(
                                        form_renderer_compact.render_inputs(),
                                        fh.Div(
                                            mui.Button(
                                                "🔍 Validate Compact",
                                                cls=mui.ButtonT.primary,
                                            ),
                                            form_renderer_compact.refresh_button("🔄"),
                                            form_renderer_compact.reset_button("↩️"),
                                            cls="mt-4 flex items-center gap-2 flex-wrap",
                                        ),
                                        hx_post="/submit_form_compact",
                                        hx_target="#result-compact",
                                        hx_swap="innerHTML",
                                        id=f"{form_renderer_compact.name}-form",
                                    ),
                                    cls="compact-form",  # Add compact styling class
                                ),
                            ),
                            fh.Div(id="result-compact", cls="mt-4"),
                            cls="w-full",
                        ),
                        # SkipJsonSchema demo form (third column)
                        fh.Div(
                            mui.Card(
                                mui.CardHeader(
                                    fh.H3("🔒 SkipJsonSchema Demo", cls="text-red-600"),
                                    fh.P(
                                        "Selective keeping of normally hidden fields",
                                        cls="text-sm text-gray-600",
                                    ),
                                ),
                                mui.CardBody(
                                    mui.Form(
                                        form_renderer_skip_demo.render_inputs(),
                                        fh.Div(
                                            mui.Button(
                                                "🔍 Validate SkipJsonSchema",
                                                cls=mui.ButtonT.primary,
                                            ),
                                            form_renderer_skip_demo.refresh_button(
                                                "🔄"
                                            ),
                                            form_renderer_skip_demo.reset_button("↩️"),
                                            cls="mt-4 flex items-center gap-2 flex-wrap",
                                        ),
                                        hx_post="/submit_form_skip_demo",
                                        hx_target="#result-skip-demo",
                                        hx_swap="innerHTML",
                                        id=f"{form_renderer_skip_demo.name}-form",
                                    )
                                ),
                            ),
                            fh.Div(id="result-skip-demo", cls="mt-4"),
                            cls="w-full",
                        ),
                        cls="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6",
                    ),
                ),
            ),
        ),
        cls="min-h-screen bg-gray-50 py-8",
    )


@rt("/submit_form_normal")
async def post_main_form_normal(req):
    try:
        validated = await form_renderer_normal.model_validate_request(req)

        # Get the raw parsed data to show what was injected
        form_data = await req.form()
        form_dict = dict(form_data)
        parsed_data = form_renderer_normal.parse(form_dict)

        # Identify which fields were excluded and auto-injected
        excluded_fields_data = {
            field_name: parsed_data.get(field_name, "NOT_FOUND")
            for field_name in form_renderer_normal.exclude_fields
        }

        return fh.Div(
            mui.Card(
                mui.CardHeader(
                    fh.H4(
                        "✅ Normal Form - Validation Successful", cls="text-green-600"
                    )
                ),
                mui.CardBody(
                    mui.H5("Complete Validated Model:"),
                    fh.Pre(
                        validated.model_dump_json(indent=2),
                        cls="bg-gray-100 p-3 rounded text-xs overflow-auto max-h-64",
                    ),
                ),
            ),
            mui.Card(
                mui.CardHeader(
                    fh.H5("🔧 Excluded Fields (Auto-Injected)", cls="text-blue-600")
                ),
                mui.CardBody(
                    fh.Pre(
                        fh.Code(
                            "\n".join(
                                [
                                    f"{field_name}: {repr(value)}"
                                    for field_name, value in excluded_fields_data.items()
                                ]
                            )
                        ),
                        cls="bg-blue-50 p-2 rounded text-xs",
                    ),
                ),
            ),
            cls="space-y-2",
        )
    except ValidationError as e:
        return mui.Card(
            mui.CardHeader(
                fh.H4("❌ Normal Form - Validation Error", cls="text-red-500")
            ),
            mui.CardBody(fh.Pre(e.json(indent=2), cls="bg-red-50 p-2 rounded text-xs")),
        )


@rt("/submit_form_compact")
async def post_main_form_compact(req):
    try:
        validated = await form_renderer_compact.model_validate_request(req)

        # Get the raw parsed data to show what was injected
        form_data = await req.form()
        form_dict = dict(form_data)
        parsed_data = form_renderer_compact.parse(form_dict)

        # Identify which fields were excluded and auto-injected
        excluded_fields_data = {
            field_name: parsed_data.get(field_name, "NOT_FOUND")
            for field_name in form_renderer_compact.exclude_fields
        }

        return fh.Div(
            mui.Card(
                mui.CardHeader(
                    fh.H4(
                        "✅ Compact Form - Validation Successful", cls="text-green-600"
                    )
                ),
                mui.CardBody(
                    mui.H5("Complete Validated Model:"),
                    fh.Pre(
                        validated.model_dump_json(indent=2),
                        cls="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-64",
                    ),
                ),
            ),
            mui.Card(
                mui.CardHeader(
                    fh.H5("🔧 Excluded Fields (Auto-Injected)", cls="text-blue-600")
                ),
                mui.CardBody(
                    fh.Pre(
                        fh.Code(
                            "\n".join(
                                [
                                    f"{field_name}: {repr(value)}"
                                    for field_name, value in excluded_fields_data.items()
                                ]
                            )
                        ),
                        cls="bg-blue-50 p-1 rounded text-xs",
                    ),
                ),
            ),
            cls="space-y-1",
        )
    except ValidationError as e:
        return mui.Card(
            mui.CardHeader(
                fh.H4("❌ Compact Form - Validation Error", cls="text-red-500")
            ),
            mui.CardBody(fh.Pre(e.json(indent=2), cls="bg-red-50 p-1 rounded text-xs")),
        )


@rt("/submit_form_skip_demo")
async def post_main_form_skip_demo(req):
    try:
        validated = await form_renderer_skip_demo.model_validate_request(req)

        # Get the raw parsed data to show what was injected
        form_data = await req.form()
        form_dict = dict(form_data)
        parsed_data = form_renderer_skip_demo.parse(form_dict)

        # Identify which SkipJsonSchema fields were kept vs hidden
        kept_skip_fields = {}
        hidden_skip_fields = {}

        for field_name in ["document_id", "created_at", "version", "security_flags"]:
            if field_name in form_renderer_skip_demo.keep_skip_json_fields:
                kept_skip_fields[field_name] = parsed_data.get(field_name, "NOT_FOUND")
            else:
                hidden_skip_fields[field_name] = parsed_data.get(
                    field_name, "NOT_FOUND"
                )

        # Also check nested fields
        if "main_address" in parsed_data and isinstance(
            parsed_data["main_address"], dict
        ):
            kept_skip_fields["main_address.internal_id"] = parsed_data[
                "main_address"
            ].get("internal_id", "NOT_FOUND")

        if "other_addresses" in parsed_data and isinstance(
            parsed_data["other_addresses"], list
        ):
            for i, addr in enumerate(parsed_data["other_addresses"]):
                if isinstance(addr, dict) and "audit_notes" in addr:
                    kept_skip_fields[f"other_addresses[{i}].audit_notes"] = addr[
                        "audit_notes"
                    ]

        # Identify regular excluded fields
        excluded_fields_data = {
            field_name: parsed_data.get(field_name, "NOT_FOUND")
            for field_name in form_renderer_skip_demo.exclude_fields
        }

        return fh.Div(
            mui.Card(
                mui.CardHeader(
                    fh.H4(
                        "✅ SkipJsonSchema Demo - Validation Successful",
                        cls="text-green-600",
                    )
                ),
                mui.CardBody(
                    mui.H5("Complete Validated Model:"),
                    fh.Pre(
                        validated.model_dump_json(indent=2),
                        cls="bg-gray-100 p-2 rounded text-xs overflow-auto max-h-64",
                    ),
                ),
            ),
            mui.Card(
                mui.CardHeader(
                    fh.H5("🔒 Kept SkipJsonSchema Fields", cls="text-green-600")
                ),
                mui.CardBody(
                    fh.Pre(
                        fh.Code(
                            "\n".join(
                                [
                                    f"{field_name}: {repr(value)}"
                                    for field_name, value in kept_skip_fields.items()
                                ]
                            )
                        ),
                        cls="bg-green-50 p-2 rounded text-xs",
                    ),
                ),
            ),
            mui.Card(
                mui.CardHeader(
                    fh.H5(
                        "🙈 Hidden SkipJsonSchema Fields (Got Defaults)",
                        cls="text-orange-600",
                    )
                ),
                mui.CardBody(
                    fh.Pre(
                        fh.Code(
                            "\n".join(
                                [
                                    f"{field_name}: {repr(value)}"
                                    for field_name, value in hidden_skip_fields.items()
                                ]
                            )
                        ),
                        cls="bg-orange-50 p-2 rounded text-xs",
                    ),
                ),
            ),
            mui.Card(
                mui.CardHeader(
                    fh.H5(
                        "🔧 Regular Excluded Fields (Auto-Injected)",
                        cls="text-blue-600",
                    )
                ),
                mui.CardBody(
                    fh.Pre(
                        fh.Code(
                            "\n".join(
                                [
                                    f"{field_name}: {repr(value)}"
                                    for field_name, value in excluded_fields_data.items()
                                ]
                            )
                        ),
                        cls="bg-blue-50 p-2 rounded text-xs",
                    ),
                ),
            ),
            cls="space-y-2",
        )
    except ValidationError as e:
        return mui.Card(
            mui.CardHeader(
                fh.H4("❌ SkipJsonSchema Demo - Validation Error", cls="text-red-500")
            ),
            mui.CardBody(fh.Pre(e.json(indent=2), cls="bg-red-50 p-2 rounded text-xs")),
        )


if __name__ == "__main__":
    fh.serve()
