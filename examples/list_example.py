from typing import List

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import LIST_MANIPULATION_JS, FormRenderer

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        fh.Script(LIST_MANIPULATION_JS),
    ],
    pico=False,
    live=True,
)


class ListModel(BaseModel):
    """Model representing a simple model"""

    name: str = ""
    tags: List[str] = Field(["tag1", "tag2"])


form_renderer = FormRenderer("list_model", ListModel)
form_renderer.register_routes(rt)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.H1("SimplePydantic Form Demo"),
            mui.Card(
                mui.CardBody(
                    mui.Form(
                        *form_renderer.render_inputs(),
                        mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
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
    """
    Handle form submission for the main form

    Args:
        req: The request object

    Returns:
        A component showing validation results or errors
    """
    form_data = await req.form()
    form_dict = dict(form_data)

    try:
        parsed_data = form_renderer.parse(form_dict)
        validated = form_renderer.model_class.model_validate(parsed_data)

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
