"""Comprehensive tests for SkipJsonSchema field handling in forms."""

import datetime
from typing import Annotated, Any, Dict, List, Optional, Type
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field, create_model
from pydantic.json_schema import SkipJsonSchema

from fh_pydantic_form import PydanticForm


class TestSkipJsonSchemaIntegration:
    """Test form handling with SkipJsonSchema fields."""

    @pytest.fixture
    def document_base_model(self) -> Type[BaseModel]:
        """Model simulating Document base class with SkipJsonSchema fields."""

        class DocumentBase(BaseModel):
            id: SkipJsonSchema[Optional[str]] = Field(  # type: ignore
                default_factory=lambda: str(uuid4()), description="Document ID"
            )
            created_at: SkipJsonSchema[datetime.datetime] = Field(  # type: ignore
                default_factory=datetime.datetime.now, description="Creation timestamp"
            )
            updated_at: SkipJsonSchema[datetime.datetime] = Field(  # type: ignore
                default_factory=datetime.datetime.now,
                description="Last update timestamp",
            )
            version: SkipJsonSchema[int] = Field(  # type: ignore
                default=1, description="Document version"
            )
            metadata: SkipJsonSchema[Dict[str, Any]] = Field(  # type: ignore
                default_factory=dict, description="Additional metadata"
            )

        return DocumentBase

    @pytest.fixture
    def user_document_model(
        self, document_base_model: Type[BaseModel]
    ) -> Type[BaseModel]:
        """User model inheriting from DocumentBase."""

        class UserDocument(document_base_model):  # type: ignore
            name: str = Field(description="User's full name")
            email: str = Field(description="User's email address")
            age: Optional[int] = Field(None, description="User's age")
            tags: List[str] = Field(default_factory=list, description="User tags")
            is_active: bool = Field(True, description="Whether user is active")

        return UserDocument

    @pytest.fixture
    def complex_document_model(
        self, document_base_model: Type[BaseModel]
    ) -> Type[BaseModel]:
        """Complex model with nested structures and SkipJsonSchema."""

        class Address(BaseModel):
            street: str
            city: str
            country: str = "USA"
            postal_code: Optional[str] = None

        class ComplexDocument(document_base_model):  # type: ignore
            title: str
            content: str
            author: str
            published: bool = False
            addresses: List[Address] = Field(default_factory=list)
            primary_address: Optional[Address] = None
            internal_notes: SkipJsonSchema[List[str]] = Field(  # type: ignore
                default_factory=list, description="Internal notes not exposed in API"
            )

        return ComplexDocument

    def test_skip_json_schema_fields_not_rendered(
        self, user_document_model: Type[BaseModel]
    ):
        """Verify SkipJsonSchema fields are not rendered in the form."""
        form = PydanticForm("test_user", user_document_model)
        rendered = form.render_inputs()
        rendered_str = str(rendered)

        # Assert SkipJsonSchema fields are NOT in rendered output
        assert 'name="test_user_id"' not in rendered_str
        assert 'name="test_user_created_at"' not in rendered_str
        assert 'name="test_user_updated_at"' not in rendered_str
        assert 'name="test_user_version"' not in rendered_str
        assert 'name="test_user_metadata"' not in rendered_str

        # Assert regular fields ARE in rendered output
        assert 'name="test_user_name"' in rendered_str
        assert 'name="test_user_email"' in rendered_str
        assert 'name="test_user_age"' in rendered_str
        assert 'name="test_user_is_active"' in rendered_str

    def test_skip_json_schema_defaults_injected(
        self, user_document_model: Type[BaseModel], mocker
    ):
        """Verify defaults are injected for missing SkipJsonSchema fields."""
        # Mock uuid for predictable ID - this works fine
        mock_uuid = mocker.patch("tests.test_skip_json_schema_fields.uuid4")
        mock_uuid.return_value = "test-uuid-123"

        form = PydanticForm("test_user", user_document_model)

        # Parse form data without SkipJsonSchema fields
        form_data = {
            "test_user_name": "John Doe",
            "test_user_email": "john@example.com",
            "test_user_age": "30",
            "test_user_is_active": "on",
        }

        parsed = form.parse(form_data)

        # Assert SkipJsonSchema fields have been injected with defaults
        assert parsed["id"] == "test-uuid-123"
        # Don't test exact datetime values - just verify they exist and are recent
        assert "created_at" in parsed
        assert "updated_at" in parsed
        assert isinstance(parsed["created_at"], datetime.datetime)
        assert isinstance(parsed["updated_at"], datetime.datetime)
        # Verify timestamps are recent (within last minute)
        now = datetime.datetime.now()
        assert (now - parsed["created_at"]).total_seconds() < 60
        assert (now - parsed["updated_at"]).total_seconds() < 60
        assert parsed["version"] == 1
        assert parsed["metadata"] == {}

        # Assert regular fields are parsed correctly
        assert parsed["name"] == "John Doe"
        assert parsed["email"] == "john@example.com"
        assert parsed["age"] == "30"
        assert parsed["is_active"] is True
        assert parsed["tags"] == []  # Default factory for list

    def test_model_validation_with_skip_fields(
        self, user_document_model: Type[BaseModel], mocker
    ):
        """Test that model validation succeeds with injected SkipJsonSchema defaults."""
        mock_uuid = mocker.patch("tests.test_skip_json_schema_fields.uuid4")
        mock_uuid.return_value = "validation-test-uuid"

        form = PydanticForm("test_user", user_document_model)

        form_data = {
            "test_user_name": "Jane Smith",
            "test_user_email": "jane@example.com",
        }

        parsed = form.parse(form_data)

        # Should validate successfully
        model = user_document_model.model_validate(parsed)

        assert model.name == "Jane Smith"  # type: ignore
        assert model.email == "jane@example.com"  # type: ignore
        assert model.id == "validation-test-uuid"  # type: ignore
        assert model.version == 1  # type: ignore
        assert isinstance(model.created_at, datetime.datetime)  # type: ignore
        assert isinstance(model.updated_at, datetime.datetime)  # type: ignore
        assert model.metadata == {}  # type: ignore

    def test_complex_model_with_nested_skip_fields(
        self, complex_document_model: Type[BaseModel], mocker
    ):
        """Test complex models with nested structures and SkipJsonSchema fields."""
        # Mock uuid for predictable ID - this works fine
        mock_uuid = mocker.patch("tests.test_skip_json_schema_fields.uuid4")
        mock_uuid.return_value = "complex-uuid"

        form = PydanticForm("test_doc", complex_document_model)

        form_data = {
            "test_doc_title": "Test Document",
            "test_doc_content": "Document content here",
            "test_doc_author": "Test Author",
            "test_doc_published": "on",
            "test_doc_addresses_0_street": "123 Main St",
            "test_doc_addresses_0_city": "Boston",
            "test_doc_addresses_0_country": "USA",
            "test_doc_primary_address_street": "456 Oak Ave",
            "test_doc_primary_address_city": "Cambridge",
        }

        parsed = form.parse(form_data)

        # Verify SkipJsonSchema fields are injected
        assert parsed["id"] == "complex-uuid"
        # Don't test exact datetime values - just verify they exist and are recent
        assert "created_at" in parsed
        assert "updated_at" in parsed
        assert isinstance(parsed["created_at"], datetime.datetime)
        assert isinstance(parsed["updated_at"], datetime.datetime)
        # Verify timestamps are recent (within last minute)
        now = datetime.datetime.now()
        assert (now - parsed["created_at"]).total_seconds() < 60
        assert (now - parsed["updated_at"]).total_seconds() < 60
        assert parsed["version"] == 1
        assert parsed["metadata"] == {}
        assert parsed["internal_notes"] == []

        # Verify nested structures are parsed correctly
        assert len(parsed["addresses"]) == 1
        assert parsed["addresses"][0]["street"] == "123 Main St"
        if parsed["primary_address"] is not None:
            assert parsed["primary_address"]["city"] == "Cambridge"

        # Validate the model
        model = complex_document_model.model_validate(parsed)
        assert model.title == "Test Document"  # type: ignore
        assert model.internal_notes == []  # type: ignore  # SkipJsonSchema field with list default

    def test_skip_fields_with_initial_values(
        self, user_document_model: Type[BaseModel]
    ):
        """Test that initial values override defaults for SkipJsonSchema fields."""
        initial_values = {
            "name": "Initial User",
            "email": "initial@example.com",
            "id": "custom-initial-id",
            "version": 5,
            "metadata": {"source": "test"},
        }

        form = PydanticForm(
            "test_user", user_document_model, initial_values=initial_values
        )

        # Change only the visible fields
        form_data = {
            "test_user_name": "Updated User",
            "test_user_email": "updated@example.com",
        }

        parsed = form.parse(form_data)

        # Visible fields should be updated
        assert parsed["name"] == "Updated User"
        assert parsed["email"] == "updated@example.com"

        # SkipJsonSchema fields should retain initial values
        assert parsed["id"] == "custom-initial-id"
        assert parsed["version"] == 5
        assert parsed["metadata"] == {"source": "test"}

    def test_form_refresh_with_skip_fields(
        self, user_document_model: Type[BaseModel], mocker
    ):
        """Test form refresh functionality with SkipJsonSchema fields."""
        # Mock uuid for predictable ID - this works fine
        mock_uuid = mocker.patch("tests.test_skip_json_schema_fields.uuid4")
        mock_uuid.return_value = "refresh-test-uuid"

        initial_values = {
            "name": "Refresh User",
            "email": "refresh@example.com",
            "id": "initial-refresh-id",
            "version": 2,
        }

        form = PydanticForm(
            "test_refresh", user_document_model, initial_values=initial_values
        )

        # Simulate form refresh with updated data
        refresh_data = {
            "test_refresh_name": "Refreshed User",
            "test_refresh_email": "refreshed@example.com",
            "test_refresh_age": "25",
        }

        # Create a mock request
        class MockRequest:
            async def form(self):
                return refresh_data

        # Test the refresh
        async def test_refresh():
            result = await form.handle_refresh_request(MockRequest())
            # Result should be a component, not None
            assert result is not None

        import asyncio

        asyncio.run(test_refresh())

    def test_inheritance_chain_with_skip_fields(self):
        """Test multiple levels of inheritance with SkipJsonSchema fields."""

        class BaseModel1(BaseModel):
            base1_id: SkipJsonSchema[str] = Field(default="base1")  # type: ignore
            base1_field: str = "base1_value"

        class BaseModel2(BaseModel1):
            base2_id: SkipJsonSchema[str] = Field(default="base2")  # type: ignore
            base2_field: str = "base2_value"

        class ConcreteModel(BaseModel2):
            concrete_field: str
            concrete_meta: SkipJsonSchema[Dict[str, Any]] = Field(default_factory=dict)  # type: ignore

        form = PydanticForm("test_inherit", ConcreteModel)
        rendered_str = str(form.render_inputs())

        # SkipJsonSchema fields should not be rendered
        assert 'name="test_inherit_base1_id"' not in rendered_str
        assert 'name="test_inherit_base2_id"' not in rendered_str
        assert 'name="test_inherit_concrete_meta"' not in rendered_str

        # Regular fields should be rendered
        assert 'name="test_inherit_base1_field"' in rendered_str
        assert 'name="test_inherit_base2_field"' in rendered_str
        assert 'name="test_inherit_concrete_field"' in rendered_str

        # Parse and verify defaults
        parsed = form.parse({"test_inherit_concrete_field": "test_value"})
        assert parsed["base1_id"] == "base1"
        assert parsed["base2_id"] == "base2"
        assert parsed["concrete_meta"] == {}
        assert parsed["concrete_field"] == "test_value"

    @pytest.mark.parametrize(
        "field_type,default_value",
        [
            (SkipJsonSchema[str], ""),  # type: ignore
            (SkipJsonSchema[int], 0),  # type: ignore
            (SkipJsonSchema[bool], False),  # type: ignore
            (SkipJsonSchema[float], 0.0),  # type: ignore
            (SkipJsonSchema[list], []),  # type: ignore
            (SkipJsonSchema[dict], {}),  # type: ignore
        ],
    )
    def test_various_skip_field_types(self, field_type: Any, default_value: Any):
        """Test various types wrapped in SkipJsonSchema."""

        # Extract the underlying type from SkipJsonSchema[T]
        underlying_type = (
            field_type.__args__[0] if hasattr(field_type, "__args__") else str
        )

        # Create model using create_model with Annotated type for SkipJsonSchema field
        TestModel = create_model(
            "TestModel",
            visible_field=(str, "visible"),
            skip_field=(Annotated[underlying_type, SkipJsonSchema()], default_value),
        )

        form = PydanticForm("test_types", TestModel)
        rendered_str = str(form.render_inputs())

        assert 'name="test_types_visible_field"' in rendered_str
        assert 'name="test_types_skip_field"' not in rendered_str

        parsed = form.parse({"test_types_visible_field": "updated"})
        assert parsed["visible_field"] == "updated"
        assert parsed["skip_field"] == default_value

    def test_skip_fields_excluded_fields_interaction(
        self, user_document_model: Type[BaseModel]
    ):
        """Test interaction between SkipJsonSchema and exclude_fields."""
        # Exclude some regular fields
        form = PydanticForm(
            "test_exclude", user_document_model, exclude_fields=["age", "tags"]
        )

        rendered_str = str(form.render_inputs())

        # Both SkipJsonSchema and excluded fields should not be rendered
        assert 'name="test_exclude_id"' not in rendered_str  # SkipJsonSchema
        assert 'name="test_exclude_age"' not in rendered_str  # Excluded
        assert 'name="test_exclude_tags"' not in rendered_str  # Excluded

        # Non-excluded regular fields should be rendered
        assert 'name="test_exclude_name"' in rendered_str
        assert 'name="test_exclude_email"' in rendered_str

        # Parse and verify all get defaults
        parsed = form.parse(
            {"test_exclude_name": "Test User", "test_exclude_email": "test@example.com"}
        )

        # SkipJsonSchema fields get defaults
        assert "id" in parsed
        assert "created_at" in parsed

        # Excluded fields get defaults
        assert parsed["age"] is None  # Optional field default
        assert parsed["tags"] == []  # List default

    def test_error_handling_skip_fields(
        self, user_document_model: Type[BaseModel], mocker
    ):
        """Test error handling when SkipJsonSchema default factories fail."""

        # Mock a failing default factory
        def failing_factory():
            raise ValueError("Factory failed")

        class FailingModel(BaseModel):
            name: str
            failing_skip: SkipJsonSchema[str] = Field(default_factory=failing_factory)  # type: ignore

        # Patch logger to verify warning is logged
        mock_logger = mocker.patch("fh_pydantic_form.type_helpers.logger")

        form = PydanticForm("test_fail", FailingModel)
        parsed = form.parse({"test_fail_name": "Test"})

        # Should not have the failing field
        assert "failing_skip" not in parsed

        # Should log warning about failed factory
        mock_logger.warning.assert_called()
