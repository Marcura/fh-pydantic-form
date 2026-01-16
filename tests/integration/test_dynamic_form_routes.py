import re

import fasthtml.common as fh
import pytest
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

from fh_pydantic_form import PydanticForm, list_manipulation_js


class Clause(BaseModel):
    content: str = ""


class Doc(BaseModel):
    clauses: list[Clause] = Field(default_factory=list)


def _build_dynamic_form_client(
    initial_clauses=None, template_initial=None, include_controls: bool = False
):
    app, rt = fh.fast_app(
        hdrs=[list_manipulation_js()],
        htmx=True,
        pico=False,
        default_hdrs=True,
        title="Dynamic form repro",
    )

    template = PydanticForm("doc_template", Doc, initial_values=template_initial)
    template.register_routes(app)

    @rt("/")
    def index():
        rows = [1, 2]
        cards = []
        for row_id in rows:
            form = PydanticForm(
                form_name=f"row_{row_id}",
                model_class=Doc,
                initial_values={"clauses": initial_clauses or []},
                template_name="doc_template",
            )
            body = []
            if include_controls:
                body.append(
                    fh.Div(
                        form.refresh_button(),
                        form.reset_button(),
                        cls="flex gap-2 mb-3",
                    )
                )
            body.append(form.render_inputs())
            cards.append(fh.Div(*body, cls="p-4 border"))
        return fh.Div(*cards, cls="space-y-4")

    return TestClient(app)


@pytest.mark.integration
def test_dynamic_form_list_add_uses_registered_template_routes(htmx_headers, soup):
    """
    Regression test: list add should work for dynamically named forms when only
    a template form is registered at startup.
    """

    client = _build_dynamic_form_client()

    response = client.get("/")
    assert response.status_code == 200
    dom = soup(response.text)
    add_button = dom.find("button", string=re.compile(r"Add Item", re.I))
    assert add_button is not None
    hx_post = add_button.get("hx-post") or ""
    hx_vals = add_button.get("hx-vals") or ""
    assert re.search(r"/form/doc_template/list/add/clauses", hx_post)
    assert re.search(r"row_\d+", hx_vals)

    # Expect list add for dynamic form name to succeed via template route.
    response = client.post(
        "/form/doc_template/list/add/clauses",
        headers=htmx_headers,
        data={"fhpf_form_name": "row_1"},
    )

    assert response.status_code == 200
    assert re.search(r"(row_1_)+clauses_new_\d+_card", response.text)


@pytest.mark.integration
def test_dynamic_form_list_add_uses_form_name_override(htmx_headers):
    client = _build_dynamic_form_client()

    response = client.post(
        "/form/doc_template/list/add/clauses",
        headers=htmx_headers,
        data={"fhpf_form_name": "row_2"},
    )

    assert response.status_code == 200
    assert re.search(r"(row_2_)+clauses_new_\d+_card", response.text)


@pytest.mark.integration
def test_dynamic_form_list_item_controls_use_template_route(soup):
    client = _build_dynamic_form_client(initial_clauses=[{"content": "One"}])

    response = client.get("/")
    assert response.status_code == 200
    dom = soup(response.text)

    add_below = dom.find(
        "button",
        attrs={"hx-post": re.compile(r"/form/doc_template/list/add/clauses")},
    )
    assert add_below is not None
    add_vals = add_below.get("hx-vals") or ""
    assert re.search(r"row_\d+", add_vals)

    delete_btn = dom.find(
        "button",
        attrs={"hx-delete": re.compile(r"/form/doc_template/list/delete/clauses")},
    )
    assert delete_btn is not None
    delete_vals = delete_btn.get("hx-vals") or ""
    assert re.search(r"row_\d+", delete_vals)


@pytest.mark.integration
def test_dynamic_form_refresh_uses_template_route(htmx_headers, soup):
    client = _build_dynamic_form_client(
        initial_clauses=[{"content": "One"}], include_controls=True
    )

    response = client.get("/")
    assert response.status_code == 200
    dom = soup(response.text)
    refresh_btn = dom.find(
        "button",
        attrs={"hx-post": re.compile(r"/form/doc_template/refresh")},
    )
    assert refresh_btn is not None
    refresh_vals = refresh_btn.get("hx-vals") or ""
    assert re.search(r"row_\d+", refresh_vals)
    refresh_include = refresh_btn.get("hx-include") or ""
    assert re.search(r"\[name\^='row_\d+_'\]", refresh_include)

    payload = {
        "fhpf_form_name": "row_1",
        "row_1_clauses_0_content": "Updated content",
    }
    response = client.post(
        "/form/doc_template/refresh",
        headers=htmx_headers,
        data=payload,
    )
    assert response.status_code == 200
    assert 'name="row_1_clauses_0_content"' in response.text
    assert "Updated content" in response.text


@pytest.mark.integration
def test_dynamic_form_reset_is_client_side(soup):
    client = _build_dynamic_form_client(include_controls=True)

    response = client.get("/")
    assert response.status_code == 200
    dom = soup(response.text)
    reset_btn = dom.find(
        "button",
        attrs={"uk-tooltip": re.compile(r"Reset the form fields", re.I)},
    )
    assert reset_btn is not None
    assert reset_btn.get("hx-post") is None
    onclick = reset_btn.get("onclick") or ""
    assert "fhpfResetForm" in onclick
