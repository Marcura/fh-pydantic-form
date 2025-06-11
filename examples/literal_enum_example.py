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


class OrderModel(BaseModel):
    """Model demonstrating Literal field rendering as dropdowns."""

    # Required Literal field - only defined choices available
    status: Literal["NEW", "PROCESSING", "SHIPPED", "DELIVERED"] = "NEW"

    # Optional Literal field - includes "None" option
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None

    # Another required Literal with different choices
    shipping_method: Literal["STANDARD", "EXPRESS", "OVERNIGHT"] = "STANDARD"

    # Optional category field
    category: Optional[Literal["ELECTRONICS", "CLOTHING", "BOOKS", "OTHER"]] = Field(
        None, description="Product category (optional)"
    )


form_renderer = PydanticForm("order_form", OrderModel)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.H1("Literal Fields Example"),
            fh.P(
                "This example demonstrates how Literal fields are automatically rendered as dropdown selects:",
                fh.Ul(
                    fh.Li("Required Literal fields show only the defined choices"),
                    fh.Li("Optional Literal fields include a '-- None --' option"),
                    fh.Li("Field descriptions become tooltips on hover"),
                ),
                cls="text-gray-600 mb-4",
            ),
            mui.Card(
                mui.CardHeader("Order Form with Literal Fields"),
                mui.CardBody(
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
                    )
                ),
            ),
            fh.Div(id="result"),
        ),
    )


@rt("/submit_order")
async def post_submit_order(req):
    try:
        validated_order: OrderModel = await form_renderer.model_validate_request(req)

        return mui.Card(
            mui.CardHeader(fh.H3("✅ Order Validated Successfully")),
            mui.CardBody(
                fh.P("Your order has been processed with the following details:"),
                fh.Pre(
                    validated_order.model_dump_json(indent=2),
                    cls="bg-gray-100 p-3 rounded text-sm",
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
