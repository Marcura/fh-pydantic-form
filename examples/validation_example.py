import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, ValidationError

from fh_pydantic_form.form_renderer import PydanticFormRenderer

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
    ],
    pico=False,
    live=True,
)


class SimpleModel(BaseModel):
    name: str = "Simple Model"
    age: int = 42
    score: float = 88.5


form_renderer = PydanticFormRenderer("simple_model", SimpleModel)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.Card(
                mui.CardHeader("Validate Pydantic Form Demo"),
                mui.CardBody(
                    mui.Form(
                        form_renderer.render_inputs(),
                        mui.Button("Submit", cls=mui.ButtonT.primary),
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
