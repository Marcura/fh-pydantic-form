import pytest
from starlette.testclient import TestClient
import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# Remove imports from examples
from fh_pydantic_form import PydanticFormRenderer, list_manipulation_js

# Define test-specific Address model
class AddressTestModel(BaseModel):
    street: str = "123 Main St"
    city: str = "Anytown"
    is_billing: bool = False

    def __str__(self) -> str:
        return f"{self.street}, {self.city} ({'billing' if self.is_billing else 'shipping'})"

# Define test-specific CustomDetail model
class CustomDetailTestModel(BaseModel):
    value: str = "Default value"
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

    def __str__(self) -> str:
        return f"{self.value} ({self.confidence})"

# Define test-specific ComplexSchema
class ComplexTestSchema(BaseModel):
    """
    Test model mirroring the structure of ComplexSchema from examples
    """
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
        default_factory=list, description="Tags of the customer"
    )

    # Nested model
    main_address: AddressTestModel = Field(
        default_factory=AddressTestModel, description="Main address of the customer"
    )
    # list of nested models
    other_addresses: List[AddressTestModel] = Field(
        default_factory=list, description="Other addresses of the customer"
    )

    # single custom nested model
    custom_detail: CustomDetailTestModel = Field(
        default_factory=CustomDetailTestModel, description="Custom detail of the customer"
    )
    # list of custom nested models
    more_custom_details: List[CustomDetailTestModel] = Field(
        default_factory=list, description="More custom details of the customer"
    )

# Define SimpleTestModel outside of fixture for use in actual test client
class SimpleTestModel(BaseModel):
    """Simple test model for client fixtures."""
    name: str = "Test Model"
    age: int = 25
    score: float = 92.5

# Define ListTestModel outside of fixture for use in actual test client
class ListTestModel(BaseModel):
    """List test model for client fixtures."""
    name: str = ""
    tags: List[str] = Field(["tag1", "tag2"])

@pytest.fixture(scope="module")
def simple_client():
    """TestClient for a simple form defined locally."""
    import fasthtml.common as fh
    import monsterui.all as mui

    form_renderer = PydanticFormRenderer("test_simple", SimpleTestModel)
    app, rt = fh.fast_app(hdrs=[mui.Theme.blue.headers()], pico=False, live=False)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Simple Test Form"),
                mui.Card(
                    mui.CardBody(mui.Form(form_renderer.render_inputs(), id="test-simple-form")),
                ),
            ),
        )

    return TestClient(app)

@pytest.fixture(scope="module")
def validation_client():
    """TestClient for a validation form defined locally."""
    import fasthtml.common as fh
    import monsterui.all as mui
    from pydantic import ValidationError

    form_renderer = PydanticFormRenderer("test_validation", SimpleTestModel)
    app, rt = fh.fast_app(hdrs=[mui.Theme.blue.headers()], pico=False, live=False)

    @rt("/")
    def get():
         return fh.Div(
            mui.Container(
                mui.Card(
                    mui.CardHeader("Validate Test Form"),
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                            hx_post="/submit_form",
                            hx_target="#result",
                            hx_swap="innerHTML",
                            id="test-validation-form"
                        )
                    ),
                ),
                fh.Div(id="result"),
            ),
        )

    @rt("/submit_form", methods=["POST"])
    async def post_main_form(req):
        try:
            validated = await form_renderer.model_validate_request(req)
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Successful")),
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2)))
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2)))
            )

    return TestClient(app)

@pytest.fixture(scope="module")
def list_client():
    """TestClient for a list form defined locally."""
    import fasthtml.common as fh
    import monsterui.all as mui
    from pydantic import ValidationError

    form_renderer = PydanticFormRenderer("test_list", ListTestModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()],
        pico=False,
        live=False
    )
    form_renderer.register_routes(app)  # Register the list routes

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader(mui.H2("Test List Form")),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                            hx_post="/submit_form",
                            hx_target="#result",
                            hx_swap="innerHTML",
                            id="test-list-form"
                        )
                    ),
                ),
                fh.Div(id="result"),
            ),
        )

    @rt("/submit_form", methods=["POST"])
    async def post_main_form(req):
        try:
            validated = await form_renderer.model_validate_request(req)
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Successful")),
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2)))
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2)))
            )

    return TestClient(app)

@pytest.fixture(scope="module")
def complex_client(complex_renderer):
    """TestClient for a complex form defined locally."""
    import fasthtml.common as fh
    import monsterui.all as mui
    from pydantic import ValidationError

    # complex_renderer is already configured with ComplexTestSchema, form_name="test_complex"
    form_renderer = complex_renderer
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()],
        pico=False,
        live=False
    )
    form_renderer.register_routes(app)  # Register list and form action routes

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.H1("Complex Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            fh.Div(
                                mui.Button("Validate", cls=mui.ButtonT.primary),
                                form_renderer.refresh_button(),
                                form_renderer.reset_button(),
                                cls="mt-4 flex items-center gap-3",
                            ),
                            hx_post="/submit_form",
                            hx_target="#result",
                            hx_swap="innerHTML",
                            id="test-complex-form"
                        )
                    ),
                ),
                fh.Div(id="result"),
            ),
        )

    @rt("/submit_form", methods=["POST"])
    async def post_main_form(req):
        try:
            validated = await form_renderer.model_validate_request(req)
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Successful")),
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2)))
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2)))
            )

    return TestClient(app)

@pytest.fixture
def simple_test_model():
    """A simple model for testing basic fields."""
    class SimpleTestModel(BaseModel):
        name: str = "Test Model"
        age: int = 25
        score: float = 92.5
        
    return SimpleTestModel


@pytest.fixture
def nested_test_model():
    """A model with nested fields for testing form parsing."""
    class NestedModel(BaseModel):
        sub_field: str = "Default Sub"
        is_active: bool = False
        
    class TestModel(BaseModel):
        name: str = "Parent Model"
        count: Optional[int] = None
        nested: NestedModel = Field(default_factory=NestedModel)
        
    return TestModel


@pytest.fixture
def list_test_model():
    """A model with list fields for testing list handling."""
    class ListTestModel(BaseModel):
        name: str = "List Model"
        tags: List[str] = Field(default_factory=lambda: ["tag1", "tag2"])
        
    return ListTestModel


@pytest.fixture(scope="module")
def complex_test_model():
    """Returns the test-specific ComplexTestSchema for reuse in tests."""
    return ComplexTestSchema


@pytest.fixture(scope="module")
def address_model():
    """Returns the test-specific AddressTestModel for reuse in tests."""
    return AddressTestModel


@pytest.fixture(scope="module")
def custom_detail_model():
    """Returns the test-specific CustomDetailTestModel for reuse in tests."""
    return CustomDetailTestModel


@pytest.fixture
def simple_renderer():
    """A PydanticFormRenderer instance for a simple model."""
    return PydanticFormRenderer(form_name="test_simple", model_class=SimpleTestModel)


@pytest.fixture
def list_renderer():
    """A PydanticFormRenderer instance for a list model."""
    return PydanticFormRenderer(form_name="test_list", model_class=ListTestModel)


@pytest.fixture(scope="module")
def complex_renderer(complex_test_model, address_model, custom_detail_model):
    """A PydanticFormRenderer instance for the complex model."""
    initial_values = complex_test_model(
        name="Test User",
        age=30,
        score=95.0,
        is_active=True,
        description="Test description",
        creation_date=datetime.date(2023, 1, 1),
        start_time=datetime.time(12, 0, 0),
        status="PENDING",
        optional_status=None,
        tags=["test1", "test2"],
        main_address=address_model(street="123 Test St", city="Testville", is_billing=True),
        custom_detail=custom_detail_model(value="Test Detail", confidence="HIGH"),
        other_addresses=[
            address_model(street="456 Other St", city="Otherville", is_billing=False),
        ],
        more_custom_details=[
            custom_detail_model(value="Test Detail 1", confidence="MEDIUM"),
        ],
    )
    return PydanticFormRenderer(
        form_name="test_complex",
        model_class=complex_test_model,
        initial_values=initial_values
    )


@pytest.fixture
def htmx_headers():
    """Standard HTMX request headers for testing."""
    return {
        "HX-Request": "true",
        "HX-Current-URL": "http://testserver/",
        "HX-Target": "result",
        "Content-Type": "application/x-www-form-urlencoded"
    }

@pytest.fixture
def sample_field_info():
    """Create a sample FieldInfo for testing."""
    from pydantic.fields import FieldInfo
    return FieldInfo(annotation=str)