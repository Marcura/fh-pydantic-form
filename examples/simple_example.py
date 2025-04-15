import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form.form_renderer import PydanticFormRenderer

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
    ],
    pico=False,
    live=True,
)


class SimpleModel(BaseModel):
    """Model representing a simple model"""

    name: str = "Simple Model"
    age: int = Field(
        description="Age of the customer"
    )  # description will be rendered as tooltip
    score: float = 88.5


form_renderer = PydanticFormRenderer("simple_model", SimpleModel)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.CardHeader("Simple Pydantic Form Demo"),
            mui.Card(
                mui.CardBody(mui.Form(form_renderer.render_inputs())),
            ),
        ),
    )


if __name__ == "__main__":
    fh.serve()
