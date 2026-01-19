import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, Field

from fh_pydantic_form import (
    ComparisonForm,
    PydanticForm,
    comparison_form_js,
    list_manipulation_js,
)


class Clause(BaseModel):
    content: str = ""


class Doc(BaseModel):
    clauses: list[Clause] = Field(default_factory=list)


app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
        comparison_form_js(),
    ],
    htmx=True,
    pico=False,
    default_hdrs=True,
    title="Dynamic forms example",
)

# Register one static form at startup (template routes only)
template = PydanticForm("doc_template", Doc)
template.register_routes(app)

ROW_IDS = [1, 2]

# Template ComparisonForm - registers routes ONCE under its name
template_left = PydanticForm(
    form_name="compare_template_left",
    model_class=Doc,
    initial_values={"clauses": [{"content": "Reference clause"}]},
)
template_right = PydanticForm(
    form_name="compare_template_right",
    model_class=Doc,
    initial_values={"clauses": [{"content": "Generated clause"}]},
)
template_comparison = ComparisonForm(
    name="compare_template",  # Routes registered under this name
    left_form=template_left,
    right_form=template_right,
    # template_name defaults to "compare_template"
    copy_right=True,
)
template_comparison.register_routes(app)

# Dynamic ComparisonForms - reuse template routes via template_name
comparison_forms: list[tuple[int, ComparisonForm[Doc]]] = []
for row_id in ROW_IDS:
    left_form = PydanticForm(
        form_name=f"compare_left_{row_id}",
        model_class=Doc,
        initial_values={"clauses": [{"content": f"Reference clause {row_id}"}]},
        template_name="compare_template_left",  # Reuse PydanticForm routes
    )
    right_form = PydanticForm(
        form_name=f"compare_right_{row_id}",
        model_class=Doc,
        initial_values={"clauses": [{"content": f"Generated clause {row_id}"}]},
        template_name="compare_template_right",  # Reuse PydanticForm routes
    )
    comparison = ComparisonForm(
        name=f"compare_{row_id}",
        left_form=left_form,
        right_form=right_form,
        template_name="compare_template",  # Reference the template's name
        copy_right=True,
    )
    # Note: NO register_routes() call - routes are shared via template_name
    comparison_forms.append((row_id, comparison))


@rt("/")
def index():
    cards = []
    for row_id in ROW_IDS:
        form = PydanticForm(
            form_name=f"row_{row_id}",
            model_class=Doc,
            initial_values={"clauses": []},
            template_name="doc_template",
        )
        cards.append(
            mui.Card(
                mui.CardHeader(mui.H3(f"Row {row_id}")),
                mui.CardBody(
                    mui.Form(
                        fh.Div(
                            form.refresh_button(),
                            form.reset_button(),
                            cls="flex gap-2 mb-3",
                        ),
                        form.render_inputs(),
                        cls="space-y-2",
                    )
                ),
                cls="p-4 border",
            )
        )

    comparison_cards = []
    for row_id, comparison in comparison_forms:
        comparison_cards.append(
            mui.Card(
                mui.CardHeader(mui.H3(f"Comparison Row {row_id}")),
                mui.CardBody(
                    comparison.form_wrapper(comparison.render_inputs()),
                    cls="space-y-2",
                ),
                cls="p-4 border",
            )
        )

    return fh.Div(
        mui.Container(
            mui.CardHeader(mui.H2("Dynamic forms example")),
            mui.Alert(
                "Dynamic forms reuse template routes via template_name (list + refresh/reset).",
                cls=mui.AlertT.info + " mb-4",
            ),
            fh.Div(*cards, cls="space-y-4 mb-8"),
            mui.CardHeader(mui.H2("Dynamic ComparisonForm")),
            mui.Alert(
                "ComparisonForm rows can use template_name for list actions.",
                cls=mui.AlertT.info + " mb-4",
            ),
            fh.Div(*comparison_cards, cls="space-y-4"),
        )
    )


if __name__ == "__main__":
    fh.serve()
