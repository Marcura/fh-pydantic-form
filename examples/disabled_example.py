import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import PydanticForm

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
    ],
    pico=False,
    live=True,
)


class DisabledExampleModel(BaseModel):
    """Model for demonstrating disabled fields."""

    name: str = Field("Default Name", description="A standard text field.")
    count: int = Field(10, description="A number field.")
    is_required: bool = Field(True, description="A boolean checkbox.")
    notes: str | None = Field(None, description="An optional text field.")


# Create the three renderers
renderer_enabled = PydanticForm(
    form_name="enabled_form", model_class=DisabledExampleModel
)

renderer_globally_disabled = PydanticForm(
    form_name="global_disabled_form", model_class=DisabledExampleModel, disabled=True
)

renderer_partially_disabled = PydanticForm(
    form_name="partial_disabled_form",
    model_class=DisabledExampleModel,
    disabled_fields=["count", "is_required"],  # Disable count and is_required
    spacing="compact",  # Demonstrate that disabled + compact work together
)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.H1("Disabled Fields Example"),
            fh.P(
                "This example demonstrates three different forms using the same Pydantic model:",
                fh.Ul(
                    fh.Li("A fully enabled form (standard behavior)"),
                    fh.Li("A globally disabled form (all fields disabled)"),
                    fh.Li("A partially disabled form (only specific fields disabled)"),
                ),
                cls="mb-4",
            ),
            # Section 1: Fully Enabled Form
            mui.Card(
                mui.CardHeader(mui.H3("Fully Enabled Form")),
                mui.CardBody(
                    mui.Form(
                        renderer_enabled.render_inputs(),
                        mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                        id="enabled-form",
                    )
                ),
                cls="mb-4",
            ),
            # Section 2: Globally Disabled Form
            mui.Card(
                mui.CardHeader(mui.H3("Globally Disabled Form (disabled=True)")),
                mui.CardBody(
                    mui.Form(
                        renderer_globally_disabled.render_inputs(),
                        mui.Button(
                            "Submit",
                            type="submit",
                            cls=mui.ButtonT.primary,
                            disabled=True,
                        ),
                        id="global-disabled-form",
                    )
                ),
                cls="mb-4",
            ),
            # Section 3: Partially Disabled Form
            mui.Card(
                mui.CardHeader(
                    mui.H3("Partially Disabled Form (specific fields disabled)")
                ),
                mui.CardBody(
                    fh.P("Only the 'count' and 'is_required' fields are disabled."),
                    fh.P(
                        "This form also uses compact spacing theme.",
                        cls="text-sm text-gray-600 mb-2",
                    ),
                    mui.Form(
                        renderer_partially_disabled.render_inputs(),
                        mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                        id="partial-disabled-form",
                    ),
                ),
                cls="mb-4",
            ),
        ),
    )


if __name__ == "__main__":
    fh.serve()
