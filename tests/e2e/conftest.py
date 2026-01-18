import json
import socket
import threading
import time
from typing import Literal, Optional

import fasthtml.common as fh
from fastcore.xml import FT
import httpx
import monsterui.all as mui
import pytest
import uvicorn
from pydantic import BaseModel, Field, ValidationError

from fh_pydantic_form import PydanticForm, list_manipulation_js
from fh_pydantic_form.comparison_form import ComparisonForm, comparison_form_js


class Note(BaseModel):
    text: str
    severity: Literal["LOW", "HIGH"] = "LOW"

    def __str__(self) -> str:
        return f"{self.text} ({self.severity})"


class Entry(BaseModel):
    title: str
    count: int = 0
    notes: list[Note] = Field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.title} ({len(self.notes)} notes)"


class CopyModel(BaseModel):
    title: str
    count: int = 0
    entries: list[Entry] = Field(default_factory=list)
    labels: list[Literal["Alpha", "Beta", "Gamma"]] = Field(default_factory=list)


def _htmx_stub_script() -> FT:
    return fh.Script(
        """
(() => {
  if (window.htmx) {
    return;
  }
  window.htmx = {
    ajax: async (method, url, options = {}) => {
      const targetSelector = options.target || "";
      const swap = options.swap || "innerHTML";
      const values = options.values || {};
      const params = new URLSearchParams(values);
      const body = method.toUpperCase() === "GET" ? null : params.toString();
      const response = await fetch(url, {
        method,
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const html = await response.text();
      const targetEl = targetSelector ? document.querySelector(targetSelector) : null;
      if (targetEl) {
        if (swap === "beforeend") {
          targetEl.insertAdjacentHTML("beforeend", html);
        } else if (swap === "afterend") {
          targetEl.insertAdjacentHTML("afterend", html);
        } else if (swap === "beforebegin") {
          targetEl.insertAdjacentHTML("beforebegin", html);
        } else {
          targetEl.innerHTML = html;
        }
        targetEl.dispatchEvent(
          new CustomEvent("htmx:afterSwap", { detail: { xhr: { response: html } } })
        );
      }
      document.body.dispatchEvent(new CustomEvent("htmx:afterSettle"));
    },
  };
})();
"""
    )


def _build_app():
    left_values = CopyModel(
        title="Left Title",
        count=3,
        entries=[
            Entry(
                title="Entry Zero",
                count=1,
                notes=[Note(text="Left Note A", severity="HIGH")],
            ),
            Entry(
                title="Entry One",
                count=2,
                notes=[Note(text="Left Note B", severity="LOW")],
            ),
        ],
        labels=["Alpha", "Gamma"],
    )
    right_values = CopyModel(
        title="Right Title",
        count=1,
        entries=[
            Entry(
                title="Right Entry",
                count=0,
                notes=[],
            )
        ],
        labels=["Beta"],
    )

    left_form = PydanticForm("left_form", CopyModel, initial_values=left_values)
    right_form = PydanticForm("right_form", CopyModel, initial_values=right_values)
    comparison = ComparisonForm(
        "copy_test",
        left_form,
        right_form,
        left_label="Left",
        right_label="Right",
        copy_right=True,
    )

    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js(), comparison_form_js()],
        pico=False,
        live=False,
    )
    comparison.register_routes(app)

    htmx_stub = _htmx_stub_script()

    @rt("/")
    def index():
        return mui.Container(
            mui.H1("Comparison Copy E2E"),
            mui.Form(
                fh.Div(comparison.render_inputs(), cls="mt-4"),
                mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                action="/submit",
                method="post",
                id="comparison-form",
            ),
            htmx_stub,
        )

    @rt("/submit", methods=["POST"])
    async def submit(req):
        form_data = dict(await req.form())
        left_parsed = left_form.parse(form_data)
        right_parsed = right_form.parse(form_data)

        try:
            left_form.model_class.model_validate(left_parsed)
            right_form.model_class.model_validate(right_parsed)
        except ValidationError as exc:
            return fh.Pre(exc.json(indent=2), id="submit-result")

        payload = json.dumps(
            {"left": left_parsed, "right": right_parsed},
            indent=2,
        )
        return fh.Pre(payload, id="submit-result")

    return app


class Address(BaseModel):
    street: str
    city: str
    is_primary: bool = False
    tags: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.street}, {self.city}"


class Contact(BaseModel):
    name: str
    email: str
    phones: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        return f"{self.name} ({self.email})"


class ComplexFormModel(BaseModel):
    name: str
    age: int
    score: float
    active: bool = False
    notes: Optional[str] = None
    status: Literal["NEW", "IN_PROGRESS", "DONE"] = "NEW"
    rating: Optional[Literal["LOW", "MEDIUM", "HIGH"]] = None
    tags: list[str] = Field(default_factory=list)
    categories: list[Literal["Alpha", "Beta", "Gamma"]] = Field(default_factory=list)
    addresses: list[Address] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)


def _build_complex_form_app():
    initial_values = ComplexFormModel(
        name="Initial User",
        age=30,
        score=88.5,
        active=True,
        notes="Initial notes",
        status="IN_PROGRESS",
        rating="MEDIUM",
        tags=["initial", "seed"],
        categories=["Alpha"],
        addresses=[
            Address(
                street="123 Main St",
                city="Austin",
                is_primary=True,
                tags=["home"],
            )
        ],
        contacts=[
            Contact(name="Jane Doe", email="jane@example.com", phones=["555-0101"])
        ],
    )

    form = PydanticForm(
        "complex_form",
        ComplexFormModel,
        initial_values=initial_values,
    )

    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()],
        pico=False,
        live=False,
    )
    form.register_routes(app)

    htmx_stub = _htmx_stub_script()

    @rt("/")
    def index():
        return mui.Container(
            mui.H1("Complex Form E2E"),
            mui.Form(
                form.render_inputs(),
                fh.Div(
                    mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                    form.refresh_button(),
                    form.reset_button(),
                    cls="mt-4 flex gap-2",
                ),
                action="/submit",
                method="post",
                id="complex-form",
            ),
            htmx_stub,
        )

    @rt("/submit", methods=["POST"])
    async def submit(req):
        try:
            validated = await form.model_validate_request(req)
            return fh.Pre(
                validated.model_dump_json(indent=2),
                id="submit-result",
            )
        except ValidationError as exc:
            return fh.Pre(exc.json(indent=2), id="submit-result")

    return app


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def app_server():
    app = _build_app()
    port = _pick_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(base_url, timeout=0.5)
            break
        except httpx.RequestError:
            time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Timed out waiting for the app server to start")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def complex_form_server():
    app = _build_complex_form_app()
    port = _pick_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            httpx.get(base_url, timeout=0.5)
            break
        except httpx.RequestError:
            time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Timed out waiting for the complex form server to start")

    yield base_url

    server.should_exit = True
    thread.join(timeout=5)
