import datetime
from enum import Enum, IntEnum
from typing import List, Literal, Optional

import fasthtml.common as fh  # type: ignore
import monsterui.all as mui  # type: ignore
import pytest
from pydantic import BaseModel, Field
from starlette.testclient import TestClient

# Remove imports from examples
from fh_pydantic_form import PydanticForm, list_manipulation_js


# Define test Enum classes
class OrderStatus(Enum):
    NEW = "NEW"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"


class Priority(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class PriorityInt(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class ShippingMethod(Enum):
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    OVERNIGHT = "OVERNIGHT"


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
    tags: List[str] = Field(default_factory=list, description="Tags of the customer")

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
        default_factory=CustomDetailTestModel,
        description="Custom detail of the customer",
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


# Define Enum test models
class EnumTestModel(BaseModel):
    """Simple enum test model for fixtures."""

    status: OrderStatus = OrderStatus.NEW
    priority: Optional[Priority] = None
    priority_int: Optional[PriorityInt] = None


class ComplexEnumTestModel(BaseModel):
    """Complex enum test model with various enum field types."""

    # Required enum fields
    status: OrderStatus = OrderStatus.NEW
    shipping_method: ShippingMethod = ShippingMethod.STANDARD

    # Optional enum fields
    priority: Optional[Priority] = None

    # Basic fields mixed with enums
    name: str = "Test Order"
    order_id: int = 1

    # Lists of enums
    status_history: List[OrderStatus] = Field(default_factory=list)
    available_priorities: List[Priority] = Field(default_factory=list)


@pytest.fixture(scope="module")
def simple_client():
    """TestClient for a simple form defined locally."""

    form_renderer = PydanticForm("test_simple", SimpleTestModel)
    app, rt = fh.fast_app(hdrs=[mui.Theme.blue.headers()], pico=False, live=False)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Simple Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(form_renderer.render_inputs(), id="test-simple-form")
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def globally_disabled_simple_client():
    """TestClient for a simple form with all fields disabled."""

    form_renderer = PydanticForm(
        "test_simple_globally_disabled", SimpleTestModel, disabled=True
    )
    app, rt = fh.fast_app(hdrs=[mui.Theme.blue.headers()], pico=False, live=False)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Simple Test Form (Globally Disabled)"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            id="test-simple-globally-disabled-form",
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def partially_disabled_simple_client():
    """TestClient for a simple form with only the age field disabled."""

    form_renderer = PydanticForm(
        "test_simple_partially_disabled", SimpleTestModel, disabled_fields=["age"]
    )
    app, rt = fh.fast_app(hdrs=[mui.Theme.blue.headers()], pico=False, live=False)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Simple Test Form (Partially Disabled)"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            id="test-simple-partially-disabled-form",
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def validation_client():
    """TestClient for a validation form defined locally."""
    from pydantic import ValidationError

    form_renderer = PydanticForm("test_validation", SimpleTestModel)
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
                            mui.Button(
                                "Submit", type="submit", cls=mui.ButtonT.primary
                            ),
                            hx_post="/submit_form",
                            hx_target="#result",
                            hx_swap="innerHTML",
                            id="test-validation-form",
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
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2))),
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2))),
            )

    return TestClient(app)


@pytest.fixture(scope="module")
def list_client():
    """TestClient for a list form defined locally."""
    from pydantic import ValidationError

    form_renderer = PydanticForm("test_list", ListTestModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
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
                            mui.Button(
                                "Submit", type="submit", cls=mui.ButtonT.primary
                            ),
                            hx_post="/submit_form",
                            hx_target="#result",
                            hx_swap="innerHTML",
                            id="test-list-form",
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
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2))),
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2))),
            )

    return TestClient(app)


@pytest.fixture(scope="module")
def complex_client(complex_renderer):
    """TestClient for a complex form defined locally."""
    from pydantic import ValidationError

    # complex_renderer is already configured with ComplexTestSchema, form_name="test_complex"
    form_renderer = complex_renderer
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
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
                            id="test-complex-form",
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
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2))),
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2))),
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
    """A PydanticForm instance for a simple model."""
    return PydanticForm(form_name="test_simple", model_class=SimpleTestModel)


@pytest.fixture
def list_renderer():
    """A PydanticForm instance for a list model."""
    return PydanticForm(form_name="test_list", model_class=ListTestModel)


@pytest.fixture(scope="module")
def complex_renderer(complex_test_model, address_model, custom_detail_model):
    """A PydanticForm instance for the complex model."""
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
        main_address=address_model(
            street="123 Test St", city="Testville", is_billing=True
        ),
        custom_detail=custom_detail_model(value="Test Detail", confidence="HIGH"),
        other_addresses=[
            address_model(street="456 Other St", city="Otherville", is_billing=False),
        ],
        more_custom_details=[
            custom_detail_model(value="Test Detail 1", confidence="MEDIUM"),
        ],
    )
    return PydanticForm(
        form_name="test_complex",
        model_class=complex_test_model,
        initial_values=initial_values,
    )


@pytest.fixture(scope="module")
def complex_initial_values(complex_test_model, address_model, custom_detail_model):
    """Return initial values for complex form tests (reusable fixture)."""
    return complex_test_model(
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
        main_address=address_model(
            street="123 Test St", city="Testville", is_billing=True
        ),
        custom_detail=custom_detail_model(value="Test Detail", confidence="HIGH"),
        other_addresses=[
            address_model(street="456 Other St", city="Otherville", is_billing=False),
        ],
        more_custom_details=[
            custom_detail_model(value="Test Detail 1", confidence="MEDIUM"),
        ],
    )


# Enum-related fixtures
@pytest.fixture(scope="session")
def order_status_enum():
    """Returns the OrderStatus enum class."""
    return OrderStatus


@pytest.fixture(scope="session")
def priority_enum():
    """Returns the Priority enum class."""
    return Priority


@pytest.fixture(scope="session")
def shipping_method_enum():
    """Returns the ShippingMethod enum class."""
    return ShippingMethod


@pytest.fixture(scope="module")
def enum_test_model():
    """Returns the EnumTestModel class."""
    return EnumTestModel


@pytest.fixture(scope="module")
def complex_enum_test_model():
    """Returns the ComplexEnumTestModel class."""
    return ComplexEnumTestModel


@pytest.fixture(scope="module")
def enum_form_renderer(enum_test_model):
    """PydanticForm renderer for simple enum model."""
    return PydanticForm("enum_test", enum_test_model)


@pytest.fixture(scope="module")
def complex_enum_form_renderer(complex_enum_test_model):
    """PydanticForm renderer for complex enum model."""
    initial_values = complex_enum_test_model(
        status=OrderStatus.PROCESSING,
        shipping_method=ShippingMethod.EXPRESS,
        priority=Priority.HIGH,
        name="Test Complex Order",
        order_id=12345,
        status_history=[OrderStatus.NEW, OrderStatus.PROCESSING],
        available_priorities=[Priority.LOW, Priority.MEDIUM],
    )
    return PydanticForm(
        "complex_enum_test",
        complex_enum_test_model,
        initial_values=initial_values,
    )


@pytest.fixture(scope="module")
def enum_client(enum_form_renderer):
    """TestClient for enum form testing."""
    from pydantic import ValidationError

    form_renderer = enum_form_renderer
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Enum Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            mui.Button(
                                "Submit", type="submit", cls=mui.ButtonT.primary
                            ),
                            hx_post="/submit_form",
                            hx_target="#result",
                            hx_swap="innerHTML",
                            id="enum-test-form",
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
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2))),
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2))),
            )

    return TestClient(app)


@pytest.fixture(scope="module")
def complex_enum_client(complex_enum_form_renderer):
    """TestClient for complex enum form testing."""
    from pydantic import ValidationError

    form_renderer = complex_enum_form_renderer
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.H1("Complex Enum Test Form"),
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
                            id="complex-enum-test-form",
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
                mui.CardBody(fh.Pre(validated.model_dump_json(indent=2))),
            )
        except ValidationError as e:
            return mui.Card(
                mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
                mui.CardBody(fh.Pre(e.json(indent=2))),
            )

    return TestClient(app)


@pytest.fixture(scope="module")
def globally_disabled_complex_client(complex_test_model, complex_initial_values):
    """TestClient for a complex form with all fields disabled."""

    form_renderer = PydanticForm(
        form_name="test_complex_globally_disabled",
        model_class=complex_test_model,
        initial_values=complex_initial_values,
        disabled=True,
    )

    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.H1("Complex Test Form (Globally Disabled)"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            id="test-complex-globally-disabled-form",
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def partially_disabled_complex_client(complex_test_model, complex_initial_values):
    """TestClient for a complex form with specific fields disabled."""

    form_renderer = PydanticForm(
        form_name="test_complex_partially_disabled",
        model_class=complex_test_model,
        initial_values=complex_initial_values,
        disabled_fields=["name", "main_address", "tags"],
    )

    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.H1("Complex Test Form (Partially Disabled)"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            id="test-complex-partially-disabled-form",
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture
def htmx_headers():
    """Standard HTMX request headers for testing."""
    return {
        "HX-Request": "true",
        "HX-Current-URL": "http://testserver/",
        "HX-Target": "result",
        "Content-Type": "application/x-www-form-urlencoded",
    }


@pytest.fixture
def sample_field_info():
    """Create a sample FieldInfo for testing."""
    from pydantic.fields import FieldInfo

    return FieldInfo(annotation=str)


@pytest.fixture
def freeze_today(mocker):
    """Freeze datetime.date.today to a predictable value for testing."""
    return mocker.patch(
        "fh_pydantic_form.defaults._today", return_value=datetime.date(2021, 1, 1)
    )


@pytest.fixture(scope="module")
def simple_list_client():
    """TestClient for testing simple list operations."""

    class SimpleListModel(BaseModel):
        name: str = "Test Model"
        tags: List[str] = Field(default_factory=list)

    form_renderer = PydanticForm("test_simple_list", SimpleListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Simple List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-simple-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def address_list_client():
    """TestClient for testing address list operations with model items."""

    class AddressModel(BaseModel):
        street: str
        city: str
        is_billing: bool = False

        def __str__(self) -> str:
            return f"{self.street}, {self.city} ({'billing' if self.is_billing else 'shipping'})"

    class AddressListModel(BaseModel):
        name: str = "Address List"
        addresses: List[AddressModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_address_list", AddressListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Address List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-address-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def custom_model_list_client():
    """TestClient for testing list operations with models that have explicit defaults."""

    class CustomItemModel(BaseModel):
        name: str = "Default Item"
        value: str = "Default Value"
        priority: int = 1
        is_active: bool = True

        def __str__(self) -> str:
            return f"{self.name}: {self.value}"

    class CustomListModel(BaseModel):
        title: str = "Custom List"
        items: List[CustomItemModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_custom_list", CustomListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Custom List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-custom-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def optional_model_list_client():
    """TestClient for testing list operations with optional fields."""

    class OptionalItemModel(BaseModel):
        name: str  # Required field
        description: Optional[str]  # Optional field without default
        nickname: Optional[str] = "Default Nick"  # Optional field with default
        score: Optional[int]  # Optional field without default

        def __str__(self) -> str:
            return f"{self.name} ({self.nickname or 'no nickname'})"

    class OptionalListModel(BaseModel):
        title: str = "Optional List"
        items: List[OptionalItemModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_optional_list", OptionalListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Optional List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-optional-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def literal_model_list_client():
    """TestClient for testing list operations with Literal fields."""

    class LiteralItemModel(BaseModel):
        name: str
        status: Literal["PENDING", "ACTIVE", "COMPLETED"]
        priority: Optional[Literal["HIGH", "MEDIUM", "LOW"]]

        def __str__(self) -> str:
            return f"{self.name} ({self.status})"

    class LiteralListModel(BaseModel):
        title: str = "Literal List"
        items: List[LiteralItemModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_literal_list", LiteralListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Literal List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-literal-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def nested_model_list_client():
    """TestClient for testing list operations with nested models."""

    class InnerModel(BaseModel):
        inner_name: str
        inner_value: int = 10

        def __str__(self) -> str:
            return f"Inner: {self.inner_name}"

    class NestedItemModel(BaseModel):
        name: str
        inner: InnerModel

        def __str__(self) -> str:
            return f"{self.name} -> {self.inner}"

    class NestedListModel(BaseModel):
        title: str = "Nested List"
        items: List[NestedItemModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_nested_list", NestedListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("Nested List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-nested-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(scope="module")
def datetime_model_list_client():
    """TestClient for testing list operations with date/time fields."""

    class DateTimeItemModel(BaseModel):
        name: str
        created_date: datetime.date
        start_time: datetime.time
        optional_date: Optional[datetime.date]

        def __str__(self) -> str:
            return f"{self.name} ({self.created_date})"

    class DateTimeListModel(BaseModel):
        title: str = "DateTime List"
        items: List[DateTimeItemModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_datetime_list", DateTimeListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("DateTime List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(), id="test-datetime-list-form"
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)


@pytest.fixture(autouse=True)
def _stub_fasthtml_serve(monkeypatch):
    """
    Prevent `fh.serve()` from starting a real event-loop when any example
    is imported.  It only affects the *examples* because core library code
    never calls `fh.serve()` at import time.
    """
    monkeypatch.setattr("fasthtml.common.serve", lambda *a, **kw: None, raising=False)


@pytest.fixture(scope="module")
def user_default_list_client():
    """TestClient for testing list operations with user-defined default methods."""

    class UserDefaultItemModel(BaseModel):
        name: str
        value: str
        count: int

        @classmethod
        def default(cls):
            return cls(name="User Default Name", value="User Default Value", count=42)

        def __str__(self) -> str:
            return f"{self.name}: {self.value} (x{self.count})"

    class UserDefaultListModel(BaseModel):
        title: str = "User Default List"
        items: List[UserDefaultItemModel] = Field(default_factory=list)

    form_renderer = PydanticForm("test_user_default_list", UserDefaultListModel)
    app, rt = fh.fast_app(
        hdrs=[mui.Theme.blue.headers(), list_manipulation_js()], pico=False, live=False
    )
    form_renderer.register_routes(app)

    @rt("/")
    def get():
        return fh.Div(
            mui.Container(
                mui.CardHeader("User Default List Test Form"),
                mui.Card(
                    mui.CardBody(
                        mui.Form(
                            form_renderer.render_inputs(),
                            id="test-user-default-list-form",
                        )
                    ),
                ),
            ),
        )

    return TestClient(app)
