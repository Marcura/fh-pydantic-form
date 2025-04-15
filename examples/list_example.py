from typing import List

import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import PydanticFormRenderer, list_manipulation_js

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
    ],
    pico=False,
    live=True,
)


class ListModel(BaseModel):
    name: str = ""
    tags: List[str] = Field(["tag1", "tag2"])


form_renderer = PydanticFormRenderer("list_model", ListModel)
form_renderer.register_list_manipulation_routes(app)


@rt("/")
def get():
    return fh.Div(
        mui.Container(
            mui.CardHeader(
                mui.H2("Simple PydanticFormRenderer Demo with editable List field")
            ),
            mui.Card(
                mui.CardBody(
                    mui.Form(
                        form_renderer.render_inputs(),
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
