from enum import Enum, IntEnum
from typing import Literal, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import PydanticForm

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
    ],
    pico=False,
    live=True,
)


# Define Enum classes for the form
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


class PaymentMethod(Enum):
    """Payment method options."""

    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"
    CASH_ON_DELIVERY = "cod"


class OrderModel(BaseModel):
    """Model demonstrating Literal, Enum, and IntEnum field rendering as dropdowns."""

    # Required Literal field - only defined choices available
    shipping_method: Literal["STANDARD", "EXPRESS", "OVERNIGHT"] = "STANDARD"

    # Optional Literal field - includes "None" option
    category: Optional[Literal["ELECTRONICS", "CLOTHING", "BOOKS", "OTHER"]] = Field(
        None, description="Product category (optional)"
    )

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


# Example initial values from a dictionary - demonstrating proper enum/int parsing
initial_values_dict = {
    "shipping_method": "EXPRESS",  # Literal value as string
    "category": "ELECTRONICS",  # Optional Literal value
    "status": "shipped",  # Enum value (will be parsed to OrderStatus.SHIPPED)
    "payment_method": "paypal",  # Optional Enum value (will be parsed to PaymentMethod.PAYPAL)
    "priority": 3,  # IntEnum value as integer (will be parsed to Priority.HIGH)
    "urgency_level": 4,  # Optional IntEnum value as integer (will be parsed to Priority.URGENT)
    "fulfillment_status": "confirmed",  # Required Enum value (will be parsed to OrderStatus.CONFIRMED)
}

# Create form renderer with initial values
form_renderer = PydanticForm(
    "order_form", OrderModel, initial_values=initial_values_dict
)

# Also create a form without initial values for comparison
form_renderer_empty = PydanticForm("order_form_empty", OrderModel)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.H1("Literal, Enum & IntEnum Fields with Initial Values"),
            fh.P(
                "This example demonstrates how different field types are automatically rendered as dropdown selects:",
                fh.Ul(
                    fh.Li("Literal fields: Show only the defined string choices"),
                    fh.Li("Enum fields: Display enum member values as options"),
                    fh.Li("IntEnum fields: Show integer values with proper ordering"),
                    fh.Li("Optional fields: Include a '-- None --' option"),
                    fh.Li("Required fields: No None option, must select a value"),
                    fh.Li(
                        "Initial values: Properly parse enum values and integers from dict"
                    ),
                ),
                cls="text-gray-600 mb-4",
            ),
            # Form with initial values
            mui.Card(
                mui.CardHeader("Order Form with Initial Values from Dict"),
                mui.CardBody(
                    fh.P(
                        "This form is pre-populated with values from a dictionary:",
                        fh.Pre(
                            str(initial_values_dict),
                            cls="bg-blue-50 p-2 rounded text-xs mt-2",
                        ),
                        cls="text-sm mb-4",
                    ),
                    mui.Form(
                        form_renderer.render_inputs(),
                        fh.Div(
                            mui.Button(
                                "Submit Order", type="submit", cls=mui.ButtonT.primary
                            ),
                            form_renderer.refresh_button("🔄"),
                            form_renderer.reset_button("↩️"),
                            cls="mt-4 flex items-center gap-2",
                        ),
                        hx_post="/submit_order",
                        hx_target="#result",
                        hx_swap="innerHTML",
                        id=f"{form_renderer.name}-form",
                    ),
                ),
            ),
            # Form without initial values for comparison
            mui.Card(
                mui.CardHeader("Order Form with Default Values Only"),
                mui.CardBody(
                    fh.P(
                        "This form uses only the model's default values for comparison:",
                        cls="text-sm mb-4",
                    ),
                    mui.Form(
                        form_renderer_empty.render_inputs(),
                        fh.Div(
                            mui.Button(
                                "Submit Order", type="submit", cls=mui.ButtonT.secondary
                            ),
                            form_renderer_empty.refresh_button("🔄"),
                            form_renderer_empty.reset_button("↩️"),
                            cls="mt-4 flex items-center gap-2",
                        ),
                        hx_post="/submit_order_empty",
                        hx_target="#result",
                        hx_swap="innerHTML",
                        id=f"{form_renderer_empty.name}-form",
                    ),
                ),
                cls="mt-4",
            ),
            fh.Div(id="result"),
        ),
    )


@rt("/submit_order")
async def post_submit_order(req):
    try:
        validated_order: OrderModel = await form_renderer.model_validate_request(req)

        return mui.Card(
            mui.CardHeader(
                fh.H3("✅ Order Validated Successfully (With Initial Values)")
            ),
            mui.CardBody(
                fh.P("Your order has been processed with the following details:"),
                fh.Pre(
                    validated_order.model_dump_json(indent=2),
                    cls="bg-gray-100 p-3 rounded text-sm",
                ),
                fh.Hr(),
                fh.P("Field type breakdown:", cls="font-semibold mt-4"),
                fh.Ul(
                    fh.Li(
                        f"Shipping Method (Literal): {validated_order.shipping_method}"
                    ),
                    fh.Li(f"Category (Optional Literal): {validated_order.category}"),
                    fh.Li(
                        f"Status (Enum): {validated_order.status.value} ({validated_order.status.name})"
                    ),
                    fh.Li(
                        f"Payment Method (Optional Enum): {validated_order.payment_method.value if validated_order.payment_method else 'None'} ({validated_order.payment_method.name if validated_order.payment_method else 'None'})"
                    ),
                    fh.Li(
                        f"Priority (IntEnum): {validated_order.priority.value} ({validated_order.priority.name})"
                    ),
                    fh.Li(
                        f"Urgency Level (Optional IntEnum): {validated_order.urgency_level.value if validated_order.urgency_level else 'None'} ({validated_order.urgency_level.name if validated_order.urgency_level else 'None'})"
                    ),
                    fh.Li(
                        f"Fulfillment Status (Required Enum): {validated_order.fulfillment_status.value} ({validated_order.fulfillment_status.name})"
                    ),
                    cls="text-sm space-y-1",
                ),
                fh.Hr(),
                fh.P("Initial values parsing demonstration:", cls="font-semibold mt-4"),
                fh.Ul(
                    fh.Li(f"'shipped' string → {validated_order.status} enum"),
                    fh.Li(f"'paypal' string → {validated_order.payment_method} enum"),
                    fh.Li(f"3 integer → {validated_order.priority} IntEnum"),
                    fh.Li(f"4 integer → {validated_order.urgency_level} IntEnum"),
                    fh.Li(
                        f"'confirmed' string → {validated_order.fulfillment_status} enum"
                    ),
                    cls="text-sm space-y-1",
                ),
            ),
            cls="mt-4",
        )
    except ValidationError as e:
        return mui.Card(
            mui.CardHeader(fh.H3("❌ Validation Error", cls="text-red-500")),
            mui.CardBody(
                fh.P("Please correct the following errors:"),
                fh.Pre(
                    e.json(indent=2),
                    cls="bg-red-50 p-3 rounded text-sm",
                ),
            ),
            cls="mt-4",
        )


@rt("/submit_order_empty")
async def post_submit_order_empty(req):
    try:
        validated_order: OrderModel = await form_renderer_empty.model_validate_request(
            req
        )

        return mui.Card(
            mui.CardHeader(
                fh.H3("✅ Order Validated Successfully (Default Values Only)")
            ),
            mui.CardBody(
                fh.P("Your order has been processed with the following details:"),
                fh.Pre(
                    validated_order.model_dump_json(indent=2),
                    cls="bg-gray-100 p-3 rounded text-sm",
                ),
                fh.Hr(),
                fh.P(
                    "This form used only model defaults (no initial_values dict)",
                    cls="text-sm italic",
                ),
            ),
            cls="mt-4",
        )
    except ValidationError as e:
        return mui.Card(
            mui.CardHeader(fh.H3("❌ Validation Error", cls="text-red-500")),
            mui.CardBody(
                fh.P("Please correct the following errors:"),
                fh.Pre(
                    e.json(indent=2),
                    cls="bg-red-50 p-3 rounded text-sm",
                ),
            ),
            cls="mt-4",
        )


if __name__ == "__main__":
    fh.serve()
