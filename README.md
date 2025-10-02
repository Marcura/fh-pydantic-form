# fh-pydantic-form

[![PyPI](https://img.shields.io/pypi/v/fh-pydantic-form)](https://pypi.org/project/fh-pydantic-form/)
[![GitHub](https://img.shields.io/github/stars/Marcura/fh-pydantic-form?style=social)](https://github.com/Marcura/fh-pydantic-form)

**Generate HTML forms from Pydantic models for your FastHTML applications.**

`fh-pydantic-form` simplifies creating web forms for [FastHTML](https://github.com/AnswerDotAI/fasthtml) by automatically generating the necessary HTML input elements based on your Pydantic model definitions. It integrates seamlessly with  and leverages [MonsterUI](https://github.com/AnswerDotAI/monsterui) components for styling. This makes it ideal for annotation workflows for structured outputs: when the schema updates, so does your annotation app.

<img width="1072" alt="image" src="https://github.com/user-attachments/assets/9e189266-0118-4de2-a35c-1118f11b0581" />




<details >
    <summary>show demo screen recording</summary>
<video src="https://private-user-images.githubusercontent.com/27999937/462832274-a00096d9-47ee-485b-af0a-e74838ec6c6d.mp4" controls="controls">
</video>
</details>

## Table of Contents
1. [Purpose](#purpose)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Key Features](#key-features)
5. [Spacing & Styling](#spacing--styling)
6. [Working with Lists](#working-with-lists)
7. [Nested Models](#nested-models)
8. [Literal & Enum Fields](#literal--enum-fields)
9. [Initial Values & Enum Parsing](#initial-values--enum-parsing)
10. [Disabling & Excluding Fields](#disabling--excluding-fields)
11. [Refreshing & Resetting](#refreshing--resetting)
12. [Label Colors](#label-colors)
13. [Metrics & Highlighting](#metrics--highlighting)
14. [ComparisonForm](#comparisonform)
15. [Schema Drift Resilience](#schema-drift-resilience)
16. [Custom Renderers](#custom-renderers)
17. [API Reference](#api-reference)
18. [Contributing](#contributing)

## Purpose

-   **Reduce Boilerplate:** Automatically render form inputs (text, number, checkbox, select, date, time, etc.) based on Pydantic field types and annotations.
-   **Data Validation:** Leverage Pydantic's validation rules directly from form submissions.
-   **Nested Structures:** Support for nested Pydantic models and lists of models/simple types with accordion UI.
-   **Dynamic Lists:** Built-in HTMX endpoints and JavaScript for adding, deleting, and reordering items in lists within the form.
-   **Customization:** Easily register custom renderers for specific Pydantic types or fields.
-   **Robust Schema Handling:** Gracefully handles model changes and missing fields in initial data.

## Installation

You can install `fh-pydantic-form` using either `pip` or `uv`.

**Using pip:**

```bash
pip install fh-pydantic-form
```

Using uv:
```bash
uv add fh-pydantic-form
```

This will also install necessary dependencies like `pydantic`, `python-fasthtml`, and `monsterui`.

## Quick Start

```python
# examples/simple_example.py
import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, ValidationError

# 1. Import the form renderer
from fh_pydantic_form import PydanticForm

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        # Add list_manipulation_js() if using list fields
        # from fh_pydantic_form import list_manipulation_js
        # list_manipulation_js(),
    ],
    pico=False, # Using MonsterUI, not PicoCSS
    live=True,  # Enable live reload for development
)

# 2. Define your Pydantic model
class SimpleModel(BaseModel):
    """Model representing a simple form"""
    name: str = "Default Name"
    age: int
    is_active: bool = True

# 3. Create a form renderer instance
#    - 'my_form': Unique name for the form (used for prefixes and routes)
#    - SimpleModel: The Pydantic model class
form_renderer = PydanticForm("my_form", SimpleModel)

# (Optional) Register list manipulation routes if your model has List fields
# form_renderer.register_routes(app)

# 4. Define routes
@rt("/")
def get():
    """Display the form"""
    return fh.Div(
        mui.Container(
            mui.Card(
                mui.CardHeader("Simple Pydantic Form"),
                mui.CardBody(
                    # Use MonsterUI Form component for structure
                    mui.Form(
                        # Render the inputs using the renderer
                        form_renderer.render_inputs(),
                        # Add standard form buttons
                        fh.Div(
                            mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                            form_renderer.refresh_button("🔄"),
                            form_renderer.reset_button("↩️"),
                            cls="mt-4 flex items-center gap-2",
                        ),
                        # HTMX attributes for form submission
                        hx_post="/submit_form",
                        hx_target="#result", # Target div for response
                        hx_swap="innerHTML",
                        # Set a unique ID for the form itself for refresh/reset inclusion
                        id=f"{form_renderer.name}-form",
                    )
                ),
            ),
            # Div to display validation results
            fh.Div(id="result"),
        ),
    )

@rt("/submit_form")
async def post_submit_form(req):
    """Handle form submission and validation"""
    try:
        # 5. Validate the request data against the model
        validated_data: SimpleModel = await form_renderer.model_validate_request(req)

        # Success: Display the validated data
        return mui.Card(
            mui.CardHeader(fh.H3("Validation Successful")),
            mui.CardBody(
                fh.Pre(
                    validated_data.model_dump_json(indent=2),
                )
            ),
            cls="mt-4",
        )
    except ValidationError as e:
        # Validation Error: Display the errors
        return mui.Card(
            mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
            mui.CardBody(
                fh.Pre(
                    e.json(indent=2),
                )
            ),
            cls="mt-4",
        )

if __name__ == "__main__":
    fh.serve()
```

## Key Features

-   **Automatic Field Rendering:** Handles `str`, `int`, `float`, `bool`, `date`, `time`, `Optional`, `Literal`, nested `BaseModel`s, and `List`s out-of-the-box.
-   **Sensible Defaults:** Uses appropriate HTML5 input types (`text`, `number`, `date`, `time`, `checkbox`, `select`).
-   **Labels & Placeholders:** Generates labels from field names (converting snake_case to Title Case) and basic placeholders.
-   **Descriptions as Tooltips:** Uses `Field(description=...)` from Pydantic to create tooltips (`uk-tooltip` via UIkit).
-   **Required Fields:** Automatically adds the `required` attribute based on field definitions (considering `Optional` and defaults).
-   **Disabled Fields:** Disable the whole form with `disabled=True` or disable specific fields with `disabled_fields`
-   **Collapsible Nested Models:** Renders nested Pydantic models in accordion-style components for better form organization and space management.
-   **List Manipulation:**
    -   Renders lists of simple types or models in accordion-style cards with an enhanced UI.
    -   Provides HTMX endpoints (registered via `register_routes`) for adding and deleting list items.
    -   Includes JavaScript (`list_manipulation_js()`) for client-side reordering (moving items up/down).
    -   Click list field labels to toggle all items open/closed.
-   **Form Refresh & Reset:**
    -   Provides HTMX-powered "Refresh" and "Reset" buttons (`form_renderer.refresh_button()`, `form_renderer.reset_button()`).
    -   Refresh updates list item summaries or other dynamic parts without full page reload.
    -   Reset reverts the form to its initial values.
-   **Custom Renderers:** Register your own `BaseFieldRenderer` subclasses for specific Pydantic types or complex field logic using `FieldRendererRegistry` or by passing `custom_renderers` during `PydanticForm` initialization.
-   **Form Data Parsing:** Includes logic (`form_renderer.parse` and `form_renderer.model_validate_request`) to correctly parse submitted form data (handling prefixes, list indices, nested structures, boolean checkboxes, etc.) back into a dictionary suitable for Pydantic validation.

## Spacing & Styling

`fh-pydantic-form` ships with two spacing presets to fit different UI requirements:

| Theme | Purpose | Usage |
|-------|---------|-------|
| **normal** (default) | Comfortable margins & borders – great for desktop forms | `PydanticForm(..., spacing="normal")` |
| **compact** | Ultra-dense UIs, mobile layouts, or forms with many fields | `PydanticForm(..., spacing="compact")` |

```python
# Example: side-by-side normal vs compact forms
form_normal = PydanticForm("normal_form", MyModel, spacing="normal")
form_compact = PydanticForm("compact_form", MyModel, spacing="compact")
```


**Important:** The compact CSS is now scoped with `.fhpf-compact` classes and only affects form inputs, not layout containers. This prevents conflicts with your application's layout system.

## Working with Lists

When your Pydantic models contain `List[str]`, `List[int]`, or `List[BaseModel]` fields, `fh-pydantic-form` provides rich list manipulation capabilities:

### Basic Setup

```python
from fh_pydantic_form import PydanticForm, list_manipulation_js
from typing import List

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),  # Required for list manipulation
    ],
    pico=False,
    live=True,
)

class ListModel(BaseModel):
    name: str = ""
    tags: List[str] = Field(["tag1", "tag2"])
    addresses: List[Address] = Field(default_factory=list)

form_renderer = PydanticForm("list_model", ListModel)
form_renderer.register_routes(app)  # Register HTMX endpoints
```

### List Features

- **Add Items:** Each list has an "Add Item" button that creates new entries
- **Delete Items:** Each list item has a delete button with confirmation
- **Reorder Items:** Move items up/down with arrow buttons
- **Toggle All:** Click the list field label to expand/collapse all items at once
- **Refresh Display:** Use the 🔄 icon next to list labels to update item summaries
- **Smart Defaults:** New items are created with sensible default values

The list manipulation uses HTMX for seamless updates without page reloads, and includes JavaScript for client-side reordering.

## Nested Models

Nested Pydantic models are automatically rendered in collapsible accordion components:

```python
class Address(BaseModel):
    street: str = "123 Main St"
    city: str = "Anytown"
    is_billing: bool = False

class User(BaseModel):
    name: str
    address: Address  # Rendered as collapsible accordion
    backup_addresses: List[Address]  # List of accordions
```

**Key behaviors:**
- Nested models inherit `disabled` and `spacing` settings from the parent form
- Field prefixes are automatically managed (e.g., `user_address_street`)
- Accordions are open by default for better user experience
- Schema drift is handled gracefully - missing fields use defaults, unknown fields are ignored

## Literal & Enum Fields

`fh-pydantic-form` provides comprehensive support for choice-based fields through `Literal`, `Enum`, and `IntEnum` types, all automatically rendered as dropdown selects:

### Literal Fields

```python
from typing import Literal, Optional

class OrderModel(BaseModel):
    # Required Literal field - only defined choices available
    shipping_method: Literal["STANDARD", "EXPRESS", "OVERNIGHT"] = "STANDARD"
    
    # Optional Literal field - includes "-- None --" option
    category: Optional[Literal["ELECTRONICS", "CLOTHING", "BOOKS", "OTHER"]] = None
```

### Enum Fields

```python
from enum import Enum, IntEnum

class OrderStatus(Enum):
    """Order status enum with string values."""
    PENDING = "pending"
    CONFIRMED = "confirmed" 
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Priority(IntEnum):
    """Priority levels using IntEnum for numeric ordering."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

class OrderModel(BaseModel):
    # Required Enum field with default
    status: OrderStatus = OrderStatus.PENDING
    
    # Optional Enum field without default
    payment_method: Optional[PaymentMethod] = None
    
    # Required IntEnum field with default
    priority: Priority = Priority.MEDIUM
    
    # Optional IntEnum field without default
    urgency_level: Optional[Priority] = Field(
        None, description="Override priority for urgent orders"
    )
    
    # Enum field without default (required)
    fulfillment_status: OrderStatus = Field(
        ..., description="Current fulfillment status"
    )
```

### Field Rendering Behavior

| Field Type | Required | Optional | Notes |
|------------|----------|----------|-------|
| **Literal** | Shows only defined choices | Includes "-- None --" option | String values displayed as-is |
| **Enum** | Shows enum member values | Includes "-- None --" option | Displays `enum.value` in dropdown |
| **IntEnum** | Shows integer values | Includes "-- None --" option | Maintains numeric ordering |

**Key features:**
- **Automatic dropdown generation** for all choice-based field types
- **Proper value handling** - enum values are correctly parsed during form submission
- **Optional field support** - includes None option when fields are Optional
- **Field descriptions** become tooltips on hover
- **Default value selection** - dropdowns pre-select the appropriate default value

## Initial Values & Enum Parsing

`fh-pydantic-form` intelligently parses initial values from dictionaries, properly converting strings and integers to their corresponding enum types:

### Setting Initial Values

```python
# Example initial values from a dictionary
initial_values_dict = {
    "shipping_method": "EXPRESS",      # Literal value as string
    "category": "ELECTRONICS",         # Optional Literal value
    "status": "shipped",               # Enum value (parsed to OrderStatus.SHIPPED)
    "payment_method": "paypal",        # Optional Enum (parsed to PaymentMethod.PAYPAL)
    "priority": 3,                     # IntEnum as integer (parsed to Priority.HIGH)
    "urgency_level": 4,                # Optional IntEnum as integer (parsed to Priority.URGENT)
    "fulfillment_status": "confirmed"  # Required Enum (parsed to OrderStatus.CONFIRMED)
}

# Create form with initial values
form_renderer = PydanticForm("order_form", OrderModel, initial_values=initial_values_dict)
```

### Parsing Behavior

The form automatically handles conversion between different value formats:

| Input Type | Target Type | Example | Result |
|------------|-------------|---------|--------|
| String | Enum | `"shipped"` | `OrderStatus.SHIPPED` |
| String | Optional[Enum] | `"paypal"` | `PaymentMethod.PAYPAL` |
| Integer | IntEnum | `3` | `Priority.HIGH` |
| Integer | Optional[IntEnum] | `4` | `Priority.URGENT` |
| String | Literal | `"EXPRESS"` | `"EXPRESS"` (unchanged) |

**Benefits:**
- **Flexible data sources** - works with database records, API responses, or any dictionary
- **Type safety** - ensures enum values are valid during parsing
- **Graceful handling** - invalid enum values are passed through for Pydantic validation
- **Consistent behavior** - same parsing logic for required and optional fields

### Example Usage

```python
@rt("/")
def get():
    return mui.Form(
        form_renderer.render_inputs(),  # Pre-populated with parsed enum values
        fh.Div(
            mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
            form_renderer.refresh_button("🔄"),
            form_renderer.reset_button("↩️"),  # Resets to initial parsed values
            cls="mt-4 flex items-center gap-2",
        ),
        hx_post="/submit_order",
        hx_target="#result",
        id=f"{form_renderer.name}-form",
    )

@rt("/submit_order")
async def post_submit_order(req):
    try:
        # Validates and converts form data back to proper enum types
        validated_order: OrderModel = await form_renderer.model_validate_request(req)
        
        # Access enum properties
        print(f"Status: {validated_order.status.value} ({validated_order.status.name})")
        print(f"Priority: {validated_order.priority.value} ({validated_order.priority.name})")
        
        return success_response(validated_order)
    except ValidationError as e:
        return error_response(e)
```

This makes it easy to work with enum-based forms when loading data from databases, APIs, or configuration files.

## Disabling & Excluding Fields

### Disabling Fields

You can disable the entire form or specific fields:

```python
# Disable all fields
form_renderer = PydanticForm("my_form", FormModel, disabled=True)

# Disable specific fields only
form_renderer = PydanticForm(
    "my_form",
    FormModel,
    disabled_fields=["field1", "field3"]
)
```

### Excluding Fields

Exclude specific fields from being rendered in the form:

```python
form_renderer = PydanticForm(
    "my_form",
    FormModel,
    exclude_fields=["internal_field", "computed_field"]
)
```

**Important:** When fields are excluded from the UI, `fh-pydantic-form` automatically injects their default values during form parsing and validation. This ensures:

- **Hidden fields with defaults** are still included in the final validated data
- **Required fields without defaults** will still cause validation errors if not provided elsewhere
- **Default factories** are executed to provide computed default values
- **Nested BaseModel defaults** are converted to dictionaries for consistency

This automatic default injection means you can safely exclude fields that shouldn't be user-editable while maintaining data integrity.

### SkipJsonSchema Fields

`fh-pydantic-form` provides advanced handling for `SkipJsonSchema` fields with selective visibility control. By default, fields marked with `SkipJsonSchema` are hidden from forms, but you can selectively show specific ones using the `keep_skip_json_fields` parameter.

```python
from pydantic.json_schema import SkipJsonSchema

class DocumentModel(BaseModel):
    title: str
    content: str
    
    # Hidden by default - system fields
    document_id: SkipJsonSchema[str] = Field(
        default_factory=lambda: f"doc_{uuid4().hex[:12]}",
        description="Internal document ID"
    )
    created_at: SkipJsonSchema[datetime.datetime] = Field(
        default_factory=datetime.datetime.now,
        description="Creation timestamp"
    )
    version: SkipJsonSchema[int] = Field(
        default=1, 
        description="Document version"
    )

# Normal form - all SkipJsonSchema fields hidden
form_normal = PydanticForm("doc_form", DocumentModel)

# Admin form - selectively show some SkipJsonSchema fields
form_admin = PydanticForm(
    "admin_form", 
    DocumentModel,
    keep_skip_json_fields=[
        "document_id",  # Show document ID
        "version",      # Show version number
        # created_at remains hidden
    ]
)
```

#### Nested SkipJsonSchema Fields

The feature supports dot notation for nested objects and list items:

```python
class Address(BaseModel):
    street: str
    city: str
    # Hidden system field
    internal_id: SkipJsonSchema[str] = Field(default_factory=lambda: f"addr_{uuid4().hex[:8]}")

class UserModel(BaseModel):
    name: str
    main_address: Address
    other_addresses: List[Address]

# Show specific nested SkipJsonSchema fields
form = PydanticForm(
    "user_form",
    UserModel,
    keep_skip_json_fields=[
        "main_address.internal_id",        # Show main address ID
        "other_addresses.internal_id",     # Show all address IDs in the list
    ]
)
```

**Key Features:**
- **Hidden by default:** SkipJsonSchema fields are automatically excluded from forms
- **Selective visibility:** Use `keep_skip_json_fields` to show specific fields
- **Nested support:** Access nested fields with dot notation (`"main_address.internal_id"`)
- **List support:** Show fields in all list items (`"addresses.internal_id"`)
- **Smart defaults:** Non-kept fields use model defaults, kept fields retain initial values
- **Admin interfaces:** Perfect for admin panels or debugging where you need to see system fields

See `examples/complex_example.py` for a comprehensive demonstration of SkipJsonSchema field handling.

## Refreshing & Resetting

Forms support dynamic refresh and reset functionality:

```python
mui.Form(
    form_renderer.render_inputs(),
    fh.Div(
        mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
        form_renderer.refresh_button("🔄 Refresh"),  # Update display
        form_renderer.reset_button("↩️ Reset"),      # Restore initial values
        cls="mt-4 flex items-center gap-2",
    ),
    # ... rest of form setup
)
```

- **Refresh button** updates the form display based on current values (useful for updating list item summaries)
- **Reset button** restores all fields to their initial values with confirmation
- Both use HTMX for seamless updates without page reloads


## Label Colors

Customize the appearance of field labels with the `label_colors` parameter:

```python
form_renderer = PydanticForm(
    "my_form",
    MyModel,
    label_colors={
        "name": "text-blue-600",    # Tailwind CSS class
        "score": "#E12D39",        # Hex color value
        "status": "text-green-500", # Another Tailwind class
    },
)
```

**Supported formats:**
- **Tailwind CSS classes:** `"text-blue-600"`, `"text-red-500"`, etc.
- **Hex color values:** `"#FF0000"`, `"#0066CC"`, etc.
- **CSS color names:** `"red"`, `"blue"`, `"darkgreen"`, etc.

This can be useful for e.g. highlighting the values of different fields in a pdf with different highlighting colors matching the form input label color. 

## Metrics & Highlighting

`fh-pydantic-form` provides a powerful metrics system for visual highlighting of form fields based on extraction quality scores and confidence assessments. This is particularly useful for evaluating LLM structured output extraction, comparing generated data against ground truth, and building quality assessment interfaces.

<img width="796" alt="image" src="https://github.com/user-attachments/assets/df2f8623-991d-45b1-80d8-5c7239187a74" />


### Basic Metrics Usage

```python
from fh_pydantic_form import PydanticForm

# Define metrics for your form fields
metrics_dict = {
    "title": {
        "metric": 0.95,
        "comment": "Excellent title quality - clear and engaging"
    },
    "rating": {
        "metric": 0.3,
        "comment": "Low rating needs attention"
    },
    "status": {
        "metric": 0.0,
        "comment": "Critical status issue - requires immediate review"
    }
}

# Create form with metrics
form_renderer = PydanticForm(
    "my_form",
    MyModel,
    metrics_dict=metrics_dict
)
```

### Metrics Dictionary Structure

Each field can have the following metrics properties:

| Property | Type | Description |
|----------|------|-------------|
| `metric` | `float` or `str` | Numeric score (0.0-1.0) or string assessment |
| `color` | `str` | Custom color (overrides automatic color-coding) |
| `comment` | `str` | Tooltip text shown on hover |

### Automatic Color Coding

Numeric metrics are automatically color-coded:

- **1.0**: Bright green (perfect score)
- **0.5-1.0**: Medium green (good range)
- **0.0-0.5**: Dark red (needs attention)
- **0.0**: Bright red (critical issue)

```python
metrics_dict = {
    "field1": {"metric": 1.0, "comment": "Perfect!"},      # Bright green
    "field2": {"metric": 0.8, "comment": "Very good"},     # Medium green
    "field3": {"metric": 0.3, "comment": "Needs work"},    # Dark red
    "field4": {"metric": 0.0, "comment": "Critical"},      # Bright red
}
```

### Custom Colors

Override automatic colors with custom values:

```python
metrics_dict = {
    "status": {
        "metric": 0.0,
        "color": "purple",  # Custom color overrides red
        "comment": "Status requires special attention"
    },
    "priority": {
        "metric": 1.0,
        "color": "#FF6B35",  # Custom hex color
        "comment": "High priority with custom highlight"
    }
}
```

### String Metrics

Use string values for qualitative assessments:

```python
metrics_dict = {
    "validation_status": {
        "metric": "NEEDS_REVIEW",
        "color": "#F59E0B",  # Amber color
        "comment": "Requires human review"
    },
    "data_quality": {
        "metric": "EXCELLENT",
        "color": "#10B981",  # Green color
        "comment": "Data quality exceeds standards"
    }
}
```

### Nested Field Metrics

Support for nested objects and list items:

```python
metrics_dict = {
    # Nested object fields
    "author.name": {
        "metric": 0.95,
        "comment": "Author name perfectly formatted"
    },
    "author.email": {
        "metric": 0.9,
        "comment": "Email format excellent"
    },
    
    # List item metrics
    "tags[0]": {
        "metric": 1.0,
        "comment": "First tag is perfect"
    },
    "tags[1]": {
        "metric": 0.8,
        "comment": "Second tag very good"
    },
    
    # Complex nested paths
    "author.addresses[0].street": {
        "metric": 1.0,
        "comment": "Street address perfectly formatted"
    },
    "author.addresses[1].city": {
        "metric": 0.1,
        "color": "teal",
        "comment": "City has verification problems"
    }
}
```

### Practical Use Cases

**LLM Structured Output Evaluation:**
```python
# Evaluate LLM extraction quality against ground truth
extraction_metrics = {
    "product.name": {
        "metric": 0.9,
        "comment": "Name extracted with minor formatting issue: missing space"
    },
    "product.category": {
        "metric": 0.0,
        "comment": "Critical error: LLM misclassified Electronics instead of Sports"
    },
    "key_features": {
        "metric": 0.6,
        "comment": "LLM missed 2 of 5 key features from source text"
    },
    "extraction_confidence": {
        "metric": 1.0,
        "comment": "LLM confidence score accurately reflects actual performance"
    }
}
```

**Document Processing Quality:**
```python
# Highlight extraction quality from documents
doc_extraction_metrics = {
    "invoice_number": {
        "metric": 1.0,
        "comment": "Invoice number perfectly extracted from PDF"
    },
    "line_items": {
        "metric": 0.75,
        "comment": "3/4 line items extracted correctly"
    },
    "total_amount": {
        "metric": 0.0,
        "comment": "Amount extraction failed - currency symbol confusion"
    }
}
```

See `examples/metrics_example.py` for a comprehensive demonstration of all metrics features.

## ComparisonForm

The `ComparisonForm` component provides side-by-side comparison of two related forms, perfect for evaluating LLM structured output against ground truth, annotation correction workflows, and comparing extraction results.


<img width="1177" alt="image" src="https://github.com/user-attachments/assets/75020059-0d4d-4519-9c71-70a082d3242e" />

### Basic Usage

```python
from fh_pydantic_form import PydanticForm, ComparisonForm

# Create two forms to compare
left_form = PydanticForm(
    "ground_truth",
    ProductModel,
    initial_values=annotated_ground_truth,
    disabled=False  # Editable for annotation correction
)

right_form = PydanticForm(
    "llm_output", 
    ProductModel,
    initial_values=llm_extracted_data,
    disabled=True,  # Read-only LLM output
    metrics_dict=extraction_quality_metrics
)

# Create comparison form
comparison_form = ComparisonForm(
    name="extraction_evaluation",
    left_form=left_form,
    right_form=right_form,
    left_label="📝 Ground Truth (Editable)",
    right_label="🤖 LLM Output (with Quality Scores)"
)
```

### Required JavaScript

Include the comparison form JavaScript in your app headers:

```python
from fh_pydantic_form import comparison_form_js

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        comparison_form_js(),  # Required for comparison forms
    ],
    pico=False,
    live=True,
)
```

### Complete Example

```python
@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.Card(
                mui.CardHeader(
                    fh.H1("LLM Extraction Evaluation")
                ),
                mui.CardBody(
                    # Render the comparison form
                    comparison_form.form_wrapper(
                        fh.Div(
                            comparison_form.render_inputs(),
                            
                            # Action buttons
                            fh.Div(
                                mui.Button(
                                    "Update Ground Truth",
                                    type="submit",
                                    hx_post="/update_ground_truth",
                                    hx_target="#result"
                                ),
                                comparison_form.left_reset_button("Reset Left"),
                                comparison_form.left_refresh_button("Refresh Left"),
                                cls="mt-4 flex gap-2"
                            ),
                            
                            fh.Div(id="result", cls="mt-4")
                        )
                    )
                )
            )
        )
    )

@rt("/update_ground_truth")
async def post_update_ground_truth(req):
    # Validate left form (ground truth side)
    validated = await comparison_form.left_form.model_validate_request(req)
    
    # Process the ground truth update
    return success_response(validated)

# Register routes for both forms
comparison_form.register_routes(app)
```

### Key Features
- **Aligned fields** input fields are horizontally aligned for easy comparison.
- **Synchronized Accordions**: Expanding/collapsing sections syncs between both forms
- **Independent Controls**: Separate refresh and reset buttons for each side
- **Metrics Integration**: Right side typically shows LLM output quality scores
- **Flexible Layout**: Responsive design works on desktop and mobile
- **Form Validation**: Standard validation works with either form
- **Intelligent List Copying**: Copy lists between forms with automatic length adjustment

### Copying Between Forms

The ComparisonForm provides granular copy functionality at multiple levels. When you enable copy buttons (via `copy_left=True` or `copy_right=True`), each field, nested model, and list item gets its own copy button for maximum flexibility:

```python
# Enable copy buttons (copy FROM right TO left)
comparison_form = ComparisonForm(
    name="extraction_evaluation",
    left_form=left_form,
    right_form=right_form,
    left_label="Ground Truth",
    right_label="LLM Output",
    copy_left=True,  # Show copy buttons on right form to copy TO left
)
```

**Copy Granularity Levels:**

The copy feature works at five different levels of granularity:

1. **Individual Fields** - Copy a single field value (e.g., `name`, `price`, `status`)

2. **Nested BaseModel (Entire Object)** - Copy all fields within a nested model at once

3. **Individual Fields in Nested Models** - Copy a specific field within a nested object

4. **Full List Fields** - Copy entire lists with automatic length adjustment

5. **Individual List Items** - Add a single item from one list to another


### Common Patterns

**LLM Output Evaluation:**
```python
# Left: Editable ground truth
# Right: Read-only LLM output with extraction quality metrics
truth_form = PydanticForm(..., disabled=False, metrics_dict={})
llm_form = PydanticForm(..., disabled=True, metrics_dict=extraction_metrics)
```

**Document Extraction Comparison:**
```python
# Left: Manual annotation
# Right: Automated LLM extraction
manual_form = PydanticForm(..., initial_values=manual_annotation)
auto_form = PydanticForm(..., initial_values=llm_extraction, metrics_dict=quality_scores)
```

**Annotation Correction Workflow:**
```python
# Left: Correctable ground truth
# Right: LLM output with confidence scores
ground_truth_form = PydanticForm(..., disabled=False)
llm_output_form = PydanticForm(..., disabled=True, metrics_dict=confidence_scores)
```

See `examples/comparison_example.py` for a complete LLM extraction evaluation interface demonstration.

## Setting Initial Values

You can set initial form values of the form by passing a model instance or dictionary:

```python
initial_data = MyModel(name="John", tags=["happy", "joy"])
form_renderer = PydanticForm("my_form", MyModel, initial_values=initial_data)


initial_data_dict = {"name": "John"} 
form_renderer = PydanticForm("my_form", MyModel, initial_values=initial_values_dict)
```

The dictionary does not have to be complete, and we try to handle schema drift gracefully. If you exclude fields from the form, we fill those fields with the initial_values or the default values.

### Reusing Form Configuration with Different Values

The `with_initial_values()` method allows you to create a new form instance with the same configuration but different initial values:

```python
# Create a base form configuration
base_form = PydanticForm(
    "product_form",
    ProductModel,
    disabled_fields=["id"],
    label_colors={"name": "text-blue-600", "price": "text-green-600"},
    spacing="compact"
)

# Create forms with different initial values using the same configuration
form_for_product_a = base_form.with_initial_values({"name": "Product A", "price": 29.99})
form_for_product_b = base_form.with_initial_values({"name": "Product B", "price": 45.50})

# Or with model instances
existing_product = ProductModel(name="Existing Product", price=19.99)
form_for_existing = base_form.with_initial_values(existing_product)
```

This is particularly useful for:
- **Editing workflows** where you need the same form configuration for different records
- **Template forms** where you want to reuse styling and field configurations
- **Bulk operations** where you process multiple items with the same form structure



### Schema Drift Resilience

`fh-pydantic-form` gracefully handles model evolution and schema changes:

Initial values can come from **older or newer** versions of your model – unknown fields are ignored gracefully and missing fields use defaults.

```python
# Your model evolves over time
class UserModel(BaseModel):
    name: str
    email: str           # Added in v2
    phone: Optional[str] # Added in v3

# Old data still works
old_data = {"name": "John"}  # Missing newer fields
form = PydanticForm("user", UserModel, initial_values=old_data)

# Newer data works too
new_data = {"name": "Jane", "email": "jane@example.com", "phone": "555-1234", "removed_field": "ignored"}
form = PydanticForm("user", UserModel, initial_values=new_data)
```

**Benefits:**
- **Backward compatibility:** Old data structures continue to work
- **Forward compatibility:** Unknown fields are silently ignored
- **Graceful degradation:** Missing fields fall back to model defaults
- **Production stability:** No crashes during rolling deployments

## Custom Renderers

The library is extensible through custom field renderers for specialized input types:

```python
from fh_pydantic_form.field_renderers import BaseFieldRenderer
from fh_pydantic_form import FieldRendererRegistry

class CustomDetail(BaseModel):
    value: str = "Default value"
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

    def __str__(self) -> str:
        return f"{self.value} ({self.confidence})"

class CustomDetailFieldRenderer(BaseFieldRenderer):
    """Display value input and dropdown side by side"""

    def render_input(self):
        value_input = fh.Div(
            mui.Input(
                value=self.value.get("value", ""),
                id=f"{self.field_name}_value",
                name=f"{self.field_name}_value",
                placeholder=f"Enter {self.original_field_name.replace('_', ' ')} value",
                cls="uk-input w-full",  
            ),
            cls="flex-grow",
        )

        confidence_options = [
            fh.Option(
                opt, value=opt, selected=(opt == self.value.get("confidence", "MEDIUM"))
            )
            for opt in ["HIGH", "MEDIUM", "LOW"]
        ]

        confidence_select = mui.Select(
            *confidence_options,
            id=f"{self.field_name}_confidence",
            name=f"{self.field_name}_confidence",
            cls_wrapper="w-[110px] min-w-[110px] flex-shrink-0",
        )

        return fh.Div(
            value_input,
            confidence_select,
            cls="flex items-start gap-2 w-full",
        )

# Register the custom renderer (multiple ways)
FieldRendererRegistry.register_type_renderer(CustomDetail, CustomDetailFieldRenderer)

# Or pass directly to PydanticForm
form_renderer = PydanticForm(
    "my_form",
    MyModel,
    custom_renderers=[(CustomDetail, CustomDetailFieldRenderer)],
)
```

### Registration Methods

- **Type-based:** `register_type_renderer(CustomDetail, CustomDetailFieldRenderer)`
- **Type name:** `register_type_name_renderer("CustomDetail", CustomDetailFieldRenderer)`
- **Predicate:** `register_type_renderer_with_predicate(lambda field: isinstance(field.annotation, CustomDetail), CustomDetailFieldRenderer)`

## API Reference

### PydanticForm Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `form_name` | `str` | Required | Unique identifier for the form (used for HTMX routes and prefixes) |
| `model_class` | `Type[BaseModel]` | Required | The Pydantic model class to render |
| `initial_values` | `Optional[Union[BaseModel, Dict]]` | `None` | Initial form values as model instance or dictionary |
| `custom_renderers` | `Optional[List[Tuple[Type, Type[BaseFieldRenderer]]]]` | `None` | List of (type, renderer_class) pairs for custom rendering |
| `disabled` | `bool` | `False` | Whether to disable all form inputs |
| `disabled_fields` | `Optional[List[str]]` | `None` | List of specific field names to disable |
| `label_colors` | `Optional[Dict[str, str]]` | `None` | Mapping of field names to CSS colors or Tailwind classes |
| `exclude_fields` | `Optional[List[str]]` | `None` | List of field names to exclude from rendering (auto-injected on submission) |
| `keep_skip_json_fields` | `Optional[List[str]]` | `None` | List of SkipJsonSchema field paths to selectively show (supports dot notation for nested fields) |
| `spacing` | `SpacingValue` | `"normal"` | Spacing theme: `"normal"`, `"compact"`, or `SpacingTheme` enum |
| `metrics_dict` | `Optional[Dict[str, Dict]]` | `None` | Field metrics for highlighting and tooltips |

### ComparisonForm Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Unique identifier for the comparison form |
| `left_form` | `PydanticForm` | Required | Form to display on the left side |
| `right_form` | `PydanticForm` | Required | Form to display on the right side |
| `left_label` | `str` | `"Left"` | Label for the left form |
| `right_label` | `str` | `"Right"` | Label for the right form |

### PydanticForm Methods

| Method | Purpose |
|--------|---------|
| `render_inputs()` | Generate the HTML form inputs (without `<form>` wrapper) |
| `with_initial_values(initial_values, metrics_dict=None)` | Create a new form instance with same configuration but different initial values |
| `refresh_button(text=None, **kwargs)` | Create a refresh button component |
| `reset_button(text=None, **kwargs)` | Create a reset button component |
| `register_routes(app)` | Register HTMX endpoints for list manipulation |
| `parse(form_dict)` | Parse raw form data into model-compatible dictionary |
| `model_validate_request(req)` | Extract, parse, and validate form data from request |

### ComparisonForm Methods

| Method | Purpose |
|--------|---------|
| `render_inputs()` | Generate side-by-side form inputs |
| `form_wrapper(content)` | Wrap content with comparison form structure |
| `left_reset_button(text=None, **kwargs)` | Reset button for left form |
| `right_reset_button(text=None, **kwargs)` | Reset button for right form |
| `left_refresh_button(text=None, **kwargs)` | Refresh button for left form |
| `right_refresh_button(text=None, **kwargs)` | Refresh button for right form |
| `register_routes(app)` | Register HTMX endpoints for both forms |

### Utility Functions

| Function | Purpose |
|----------|---------|
| `list_manipulation_js()` | JavaScript for list reordering and toggle functionality |
| `comparison_form_js()` | JavaScript for comparison form accordion synchronization |
| `default_dict_for_model(model_class)` | Generate default values for all fields in a model |
| `default_for_annotation(annotation)` | Get sensible default for a type annotation |

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
