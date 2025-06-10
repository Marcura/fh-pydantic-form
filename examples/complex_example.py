import datetime
import logging
from typing import List, Literal, Optional

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.field_renderers import BaseFieldRenderer

logging.basicConfig(level=logging.DEBUG)
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
    city: str = "Anytown"
    is_billing: bool = False

    def __str__(self) -> str:
        return f"{self.street}, {self.city} ({'billing' if self.is_billing else 'shipping'})"


class CustomDetail(BaseModel):
    value: str = "Default value"
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

    def __str__(self) -> str:
        return f"{self.value} ({self.confidence})"


class CustomDetailFieldRenderer(BaseFieldRenderer):
    """display value input and dropdown side by side for Detail"""

    def render_input(self):
        current_value_val = self.value.get("value", "")
        current_confidence = self.value.get("confidence", "MEDIUM")

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
    name: str = Field(description="Name of the customer")
    age: int = Field(description="Age of the customer")
    score: float = Field(description="Score of the customer")
    is_active: bool = Field(description="Is the customer active")
    description: Optional[str] = Field(description="Description of the customer")

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

    # Nested model
    main_address: Address = Field(
        default_factory=Address, description="Main address of the customer"
    )
    # list of nested models
    other_addresses: List[Address] = Field(
        default_factory=list, description="Other addresses of the customer"
    )

    # single custom nested model
    custom_detail: CustomDetail = Field(
        default_factory=CustomDetail, description="Custom detail of the customer"
    )
    # list of custom nested models
    more_custom_details: List[CustomDetail] = Field(
        default_factory=list, description="More custom details of the customer"
    )


# Create an initial model with example data
initial_values = ComplexSchema(
    skip_field="This field will be skipped",
    name="Demo User",
    age=42,
    score=88.5,
    is_active=True,
    description="Demo description",
    creation_date=datetime.date(2023, 1, 1),
    start_time=datetime.time(12, 0, 0),
    status="PENDING",
    optional_status=None,
    tags=["tag1", "tag2", "tag3"],
    main_address=Address(street="123 Main St", city="Anytown", is_billing=True),
    custom_detail=CustomDetail(value="Main Detail", confidence="HIGH"),
    other_addresses=[
        Address(street="456 Second St", city="Othertown", is_billing=False),
        Address(street="789 Third St", city="Thirdville", is_billing=True),
    ],
    more_custom_details=[
        CustomDetail(value="Detail 1", confidence="HIGH"),
        CustomDetail(value="Detail 2", confidence="MEDIUM"),
        CustomDetail(value="Detail 3", confidence="LOW"),
    ],
)

form_renderer = PydanticForm(
    form_name="main_form",
    model_class=ComplexSchema,
    initial_values=initial_values,
    custom_renderers=[
        (CustomDetail, CustomDetailFieldRenderer)
    ],  # Register Detail renderer
    exclude_fields=["skip_field"],
    label_colors={"name": "blue", "score": "#FF0000"},
)

form_renderer.register_routes(app)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.H1("FastHTML/MonsterUI Pydantic Form Demo"),
            mui.Details(
                mui.Summary("input json"),
                fh.Pre(initial_values.model_dump_json(indent=2)),
            ),
            mui.Card(
                mui.CardBody(
                    mui.Form(
                        mui.H2("Form"),
                        form_renderer.render_inputs(),
                        fh.Div(
                            mui.Button(
                                "Validate and Show JSON",
                                cls=mui.ButtonT.primary,
                            ),
                            form_renderer.refresh_button(),
                            form_renderer.reset_button(),
                            cls="mt-4 flex items-center gap-3",
                        ),
                        hx_post="/submit_form",
                        hx_target="#result",
                        hx_swap="innerHTML",
                    )
                ),
            ),
            fh.Div(id="result"),
        ),
    )


@rt("/submit_form")
async def post_main_form(req):
    try:
        validated = await form_renderer.model_validate_request(req)

        return mui.Card(
            mui.CardHeader(fh.H3("Validation Successful")),
            mui.CardBody(
                fh.Pre(
                    validated.model_dump_json(indent=2),
                )
            ),
        )
    except ValidationError as e:
        return mui.Card(
            mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
            mui.CardBody(
                fh.Pre(
                    e.json(indent=2),
                )
            ),
        )


if __name__ == "__main__":
    fh.serve()
