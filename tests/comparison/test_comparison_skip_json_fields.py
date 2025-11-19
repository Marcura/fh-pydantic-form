"""Comprehensive tests for SkipJsonSchema field handling in ComparisonForm."""

import datetime
from typing import List, Type
from uuid import uuid4

import pytest
from pydantic import BaseModel, Field
from pydantic.json_schema import SkipJsonSchema

from fh_pydantic_form import ComparisonForm, PydanticForm


class TestComparisonFormSkipJsonSchema:
    """Test ComparisonForm handling with SkipJsonSchema fields."""

    @pytest.fixture
    def address_model(self) -> Type[BaseModel]:
        """Address model with SkipJsonSchema fields."""

        class Address(BaseModel):
            street: str = "123 Main St"
            city: str = "Anytown"
            is_billing: bool = False
            tags: List[str] = Field(
                default=["tag1"], description="Tags for the address"
            )
            # SkipJsonSchema fields - normally hidden but can be selectively shown
            internal_id: SkipJsonSchema[str] = Field(  # type: ignore
                default_factory=lambda: f"addr_{uuid4().hex[:8]}",
                description="Internal address tracking ID (system use only)",
            )
            audit_notes: SkipJsonSchema[List[str]] = Field(  # type: ignore
                default_factory=list,
                description="Internal audit notes (system use only)",
            )

        return Address

    @pytest.fixture
    def customer_model(self, address_model: Type[BaseModel]) -> Type[BaseModel]:
        """Customer model with SkipJsonSchema fields and nested models."""

        class CustomerData(BaseModel):
            # Regular fields
            name: str = Field(description="Customer name")
            age: int = Field(description="Customer age")
            is_active: bool = Field(description="Is the customer active")

            # SkipJsonSchema fields - normally hidden
            document_id: SkipJsonSchema[str] = Field(  # type: ignore
                default_factory=lambda: f"doc_{uuid4().hex[:12]}",
                description="Document tracking ID (system generated)",
            )
            created_at: SkipJsonSchema[datetime.datetime] = Field(  # type: ignore
                default_factory=datetime.datetime.now,
                description="Creation timestamp (system managed)",
            )
            version: SkipJsonSchema[int] = Field(  # type: ignore
                default=1, description="Document version (system managed)"
            )
            security_flags: SkipJsonSchema[List[str]] = Field(  # type: ignore
                default_factory=lambda: ["verified", "approved"],
                description="Security flags (admin only)",
            )

            # Nested models with SkipJsonSchema fields
            main_address: address_model = Field(  # type: ignore
                default_factory=address_model,
                description="Main address",  # type: ignore
            )
            other_addresses: List[address_model] = Field(  # type: ignore
                default_factory=list, description="Other addresses"
            )

        return CustomerData

    def test_skip_fields_hidden_by_default_in_comparison(
        self, customer_model: Type[BaseModel]
    ):
        """Test that SkipJsonSchema fields are hidden by default in both forms."""
        left_values = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "document_id": "LEFT_DOC",
            "version": 1,
            "main_address": {"street": "123 Main", "city": "City1"},
        }
        right_values = {
            "name": "Bob",
            "age": 25,
            "is_active": False,
            "document_id": "RIGHT_DOC",
            "version": 2,
            "main_address": {"street": "456 Oak", "city": "City2"},
        }

        left_form = PydanticForm("left", customer_model, initial_values=left_values)
        right_form = PydanticForm("right", customer_model, initial_values=right_values)

        comparison = ComparisonForm(
            name="test_comparison",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # Regular fields should be present in both forms
        assert 'name="left_name"' in rendered_str
        assert 'name="right_name"' in rendered_str
        assert 'name="left_age"' in rendered_str
        assert 'name="right_age"' in rendered_str

        # SkipJsonSchema fields should NOT be present in either form
        assert 'name="left_document_id"' not in rendered_str
        assert 'name="right_document_id"' not in rendered_str
        assert 'name="left_version"' not in rendered_str
        assert 'name="right_version"' not in rendered_str
        assert 'name="left_created_at"' not in rendered_str
        assert 'name="right_created_at"' not in rendered_str
        assert 'name="left_security_flags_0"' not in rendered_str
        assert 'name="right_security_flags_0"' not in rendered_str

        # Nested SkipJsonSchema fields should NOT be present
        assert 'name="left_main_address_internal_id"' not in rendered_str
        assert 'name="right_main_address_internal_id"' not in rendered_str
        assert 'name="left_main_address_audit_notes_0"' not in rendered_str
        assert 'name="right_main_address_audit_notes_0"' not in rendered_str

    def test_keep_skip_json_fields_top_level_in_comparison(
        self, customer_model: Type[BaseModel]
    ):
        """Test keeping top-level SkipJsonSchema fields visible in comparison."""
        left_values = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "document_id": "LEFT_DOC_001",
            "version": 3,
            "security_flags": ["verified", "premium"],
        }
        right_values = {
            "name": "Bob",
            "age": 25,
            "is_active": False,
            "document_id": "RIGHT_DOC_999",
            "version": 7,
            "security_flags": ["verified", "business"],
        }

        # Left form keeps document_id and version
        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=left_values,
            keep_skip_json_fields=["document_id", "version"],
        )

        # Right form keeps document_id and security_flags
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=right_values,
            keep_skip_json_fields=["document_id", "security_flags"],
        )

        comparison = ComparisonForm(
            name="test_keep_top",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # Regular fields should be present
        assert 'name="left_name"' in rendered_str
        assert 'name="right_name"' in rendered_str

        # document_id should be in BOTH forms (kept by both)
        assert 'name="left_document_id"' in rendered_str
        assert 'name="right_document_id"' in rendered_str

        # version should ONLY be in left form
        assert 'name="left_version"' in rendered_str
        assert 'name="right_version"' not in rendered_str

        # security_flags should ONLY be in right form
        assert 'name="left_security_flags_0"' not in rendered_str
        assert 'name="right_security_flags_0"' in rendered_str

        # created_at should be in NEITHER form
        assert 'name="left_created_at"' not in rendered_str
        assert 'name="right_created_at"' not in rendered_str

    def test_keep_nested_skip_json_fields_in_comparison(
        self, customer_model: Type[BaseModel]
    ):
        """Test keeping nested SkipJsonSchema fields visible in comparison."""
        left_values = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "main_address": {
                "street": "123 Main",
                "city": "City1",
                "internal_id": "LEFT_MAIN_001",
                "audit_notes": ["Created", "Verified"],
            },
            "other_addresses": [
                {
                    "street": "456 Oak",
                    "city": "City2",
                    "internal_id": "LEFT_OTHER_002",
                    "audit_notes": ["Secondary address"],
                }
            ],
        }
        right_values = {
            "name": "Bob",
            "age": 25,
            "is_active": False,
            "main_address": {
                "street": "789 Pine",
                "city": "City3",
                "internal_id": "RIGHT_MAIN_999",
                "audit_notes": ["Business address"],
            },
            "other_addresses": [
                {
                    "street": "321 Elm",
                    "city": "City4",
                    "internal_id": "RIGHT_OTHER_888",
                    "audit_notes": ["Work address", "Primary office"],
                }
            ],
        }

        # Left form keeps main_address.internal_id
        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=left_values,
            keep_skip_json_fields=["main_address.internal_id"],
        )

        # Right form keeps other_addresses.audit_notes
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=right_values,
            keep_skip_json_fields=["other_addresses.audit_notes"],
        )

        comparison = ComparisonForm(
            name="test_keep_nested",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # Regular nested fields should be present in both
        assert 'name="left_main_address_street"' in rendered_str
        assert 'name="right_main_address_street"' in rendered_str
        assert 'name="left_other_addresses_0_street"' in rendered_str
        assert 'name="right_other_addresses_0_street"' in rendered_str

        # main_address.internal_id should ONLY be in left form
        assert 'name="left_main_address_internal_id"' in rendered_str
        assert 'name="right_main_address_internal_id"' not in rendered_str

        # other_addresses.audit_notes should ONLY be in right form
        # This is the key test that's failing!
        assert 'name="left_other_addresses_0_audit_notes_0"' not in rendered_str
        assert 'name="right_other_addresses_0_audit_notes_0"' in rendered_str, (
            "BUG: other_addresses.audit_notes not showing up in right form!"
        )

        # main_address.audit_notes should be in NEITHER form
        assert 'name="left_main_address_audit_notes_0"' not in rendered_str
        assert 'name="right_main_address_audit_notes_0"' not in rendered_str

    def test_keep_multiple_nested_skip_fields_in_comparison(
        self, customer_model: Type[BaseModel]
    ):
        """Test keeping multiple nested SkipJsonSchema fields in same form."""
        initial_values = {
            "name": "Test User",
            "age": 30,
            "is_active": True,
            "main_address": {
                "street": "123 Main",
                "city": "City1",
                "internal_id": "MAIN_001",
                "audit_notes": ["Main address note"],
            },
            "other_addresses": [
                {
                    "street": "456 Oak",
                    "city": "City2",
                    "internal_id": "OTHER_002",
                    "audit_notes": ["Other address note 1", "Other address note 2"],
                },
                {
                    "street": "789 Pine",
                    "city": "City3",
                    "internal_id": "OTHER_003",
                    "audit_notes": ["Another address note"],
                },
            ],
        }

        # Left form keeps both nested skip fields
        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=initial_values,
            keep_skip_json_fields=[
                "main_address.internal_id",
                "main_address.audit_notes",
                "other_addresses.internal_id",
                "other_addresses.audit_notes",
            ],
        )

        # Right form keeps no skip fields
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=initial_values,
        )

        comparison = ComparisonForm(
            name="test_multi_nested",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # All nested skip fields should be in left form
        assert 'name="left_main_address_internal_id"' in rendered_str
        assert 'name="left_main_address_audit_notes_0"' in rendered_str
        assert 'name="left_other_addresses_0_internal_id"' in rendered_str
        assert 'name="left_other_addresses_0_audit_notes_0"' in rendered_str
        assert 'name="left_other_addresses_0_audit_notes_1"' in rendered_str
        assert 'name="left_other_addresses_1_internal_id"' in rendered_str
        assert 'name="left_other_addresses_1_audit_notes_0"' in rendered_str

        # No nested skip fields should be in right form
        assert 'name="right_main_address_internal_id"' not in rendered_str
        assert 'name="right_main_address_audit_notes_0"' not in rendered_str
        assert 'name="right_other_addresses_0_internal_id"' not in rendered_str
        assert 'name="right_other_addresses_0_audit_notes_0"' not in rendered_str
        assert 'name="right_other_addresses_1_internal_id"' not in rendered_str
        assert 'name="right_other_addresses_1_audit_notes_0"' not in rendered_str

    def test_comparison_parsing_with_kept_skip_fields(
        self, customer_model: Type[BaseModel]
    ):
        """Test that parsing works correctly with kept skip fields in comparison."""
        left_values = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "document_id": "LEFT_DOC",
            "version": 3,
            "main_address": {
                "street": "123 Main",
                "city": "City1",
                "internal_id": "LEFT_MAIN",
            },
        }
        right_values = {
            "name": "Bob",
            "age": 25,
            "is_active": False,
            "document_id": "RIGHT_DOC",
            "version": 7,
            "main_address": {
                "street": "456 Oak",
                "city": "City2",
                "internal_id": "RIGHT_MAIN",
            },
        }

        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=left_values,
            keep_skip_json_fields=["document_id", "version"],
        )
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=right_values,
            keep_skip_json_fields=["document_id", "main_address.internal_id"],
        )

        # Test parsing behavior of forms with different keep_skip_json_fields
        # (ComparisonForm not needed for this parsing test)

        # Simulate form submission for left form
        left_form_data = {
            "left_name": "Alice Updated",
            "left_age": "31",
            "left_is_active": "on",
            "left_document_id": "LEFT_DOC_UPDATED",
            "left_version": "5",
            "left_main_address_street": "123 Main Updated",
            "left_main_address_city": "City1 Updated",
        }

        left_parsed = left_form.parse(left_form_data)

        # Verify kept skip fields are parsed
        assert left_parsed["document_id"] == "LEFT_DOC_UPDATED"
        assert left_parsed["version"] == "5"

        # Verify non-kept top-level skip fields get defaults
        assert "created_at" in left_parsed
        assert "security_flags" in left_parsed

        # Note: main_address.internal_id is NOT kept in left form, so it won't be in parsed data
        # Non-kept nested skip fields are not parsed from form data
        # They will get defaults when the full model is validated

        # Simulate form submission for right form
        right_form_data = {
            "right_name": "Bob Updated",
            "right_age": "26",
            "right_is_active": "",  # Unchecked
            "right_document_id": "RIGHT_DOC_UPDATED",
            "right_main_address_street": "456 Oak Updated",
            "right_main_address_city": "City2 Updated",
            "right_main_address_internal_id": "RIGHT_MAIN_UPDATED",
        }

        right_parsed = right_form.parse(right_form_data)

        # Verify kept skip fields are parsed
        assert right_parsed["document_id"] == "RIGHT_DOC_UPDATED"
        assert right_parsed["main_address"]["internal_id"] == "RIGHT_MAIN_UPDATED"

        # Verify non-kept skip fields get initial values
        assert right_parsed["version"] == 7  # From initial_values

    def test_comparison_with_different_list_lengths(
        self, customer_model: Type[BaseModel]
    ):
        """Test comparison when forms have different numbers of list items."""
        left_values = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "other_addresses": [
                {
                    "street": "123 Main",
                    "city": "City1",
                    "internal_id": "ADDR_1",
                    "audit_notes": ["Note 1"],
                },
                {
                    "street": "456 Oak",
                    "city": "City2",
                    "internal_id": "ADDR_2",
                    "audit_notes": ["Note 2", "Note 3"],
                },
            ],
        }
        right_values = {
            "name": "Bob",
            "age": 25,
            "is_active": False,
            "other_addresses": [
                {
                    "street": "789 Pine",
                    "city": "City3",
                    "internal_id": "ADDR_3",
                    "audit_notes": ["Note 4", "Note 5", "Note 6"],
                }
            ],
        }

        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=left_values,
            keep_skip_json_fields=["other_addresses.audit_notes"],
        )
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=right_values,
            keep_skip_json_fields=["other_addresses.audit_notes"],
        )

        comparison = ComparisonForm(
            name="test_diff_lengths",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # Left form should have 2 address items with audit notes
        assert 'name="left_other_addresses_0_audit_notes_0"' in rendered_str
        assert 'name="left_other_addresses_1_audit_notes_0"' in rendered_str
        assert 'name="left_other_addresses_1_audit_notes_1"' in rendered_str

        # Right form should have 1 address item with audit notes
        assert 'name="right_other_addresses_0_audit_notes_0"' in rendered_str
        assert 'name="right_other_addresses_0_audit_notes_1"' in rendered_str
        assert 'name="right_other_addresses_0_audit_notes_2"' in rendered_str

        # Left form should NOT have a third address
        assert 'name="left_other_addresses_2_street"' not in rendered_str

    def test_comparison_grid_alignment_with_skip_fields(
        self, customer_model: Type[BaseModel]
    ):
        """Test that grid alignment works correctly when forms have different skip fields."""
        initial_values = {
            "name": "Test",
            "age": 30,
            "is_active": True,
            "document_id": "DOC_001",
            "version": 1,
        }

        # Left form keeps document_id
        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=initial_values,
            keep_skip_json_fields=["document_id"],
        )

        # Right form keeps version
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=initial_values,
            keep_skip_json_fields=["version"],
        )

        comparison = ComparisonForm(
            name="test_alignment",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # Both forms should have regular fields
        assert 'name="left_name"' in rendered_str
        assert 'name="right_name"' in rendered_str

        # Check for data-path attributes (used for grid alignment)
        assert 'data-path="name"' in rendered_str
        assert 'data-path="age"' in rendered_str
        assert 'data-path="is_active"' in rendered_str

        # Skip fields that are kept should also have data-path
        # These will appear in only one column but shouldn't break grid
        assert (
            'data-path="document_id"' in rendered_str
            or 'name="left_document_id"' in rendered_str
        )
        assert (
            'data-path="version"' in rendered_str
            or 'name="right_version"' in rendered_str
        )

    def test_comparison_with_both_forms_keeping_same_fields(
        self, customer_model: Type[BaseModel]
    ):
        """Test comparison when both forms keep the same skip fields."""
        left_values = {
            "name": "Alice",
            "age": 30,
            "is_active": True,
            "document_id": "LEFT_DOC",
            "version": 3,
            "main_address": {
                "street": "123 Main",
                "city": "City1",
                "internal_id": "LEFT_MAIN",
            },
        }
        right_values = {
            "name": "Bob",
            "age": 25,
            "is_active": False,
            "document_id": "RIGHT_DOC",
            "version": 7,
            "main_address": {
                "street": "456 Oak",
                "city": "City2",
                "internal_id": "RIGHT_MAIN",
            },
        }

        # Both forms keep the same fields
        keep_fields = ["document_id", "version", "main_address.internal_id"]
        left_form = PydanticForm(
            "left",
            customer_model,
            initial_values=left_values,
            keep_skip_json_fields=keep_fields,
        )
        right_form = PydanticForm(
            "right",
            customer_model,
            initial_values=right_values,
            keep_skip_json_fields=keep_fields,
        )

        comparison = ComparisonForm(
            name="test_same_fields",
            left_form=left_form,
            right_form=right_form,
        )

        rendered = comparison.render_inputs()
        rendered_str = str(rendered)

        # All kept fields should appear in BOTH forms
        assert 'name="left_document_id"' in rendered_str
        assert 'name="right_document_id"' in rendered_str
        assert 'name="left_version"' in rendered_str
        assert 'name="right_version"' in rendered_str
        assert 'name="left_main_address_internal_id"' in rendered_str
        assert 'name="right_main_address_internal_id"' in rendered_str

        # Non-kept fields should not appear in either form
        assert 'name="left_created_at"' not in rendered_str
        assert 'name="right_created_at"' not in rendered_str
        assert 'name="left_security_flags_0"' not in rendered_str
        assert 'name="right_security_flags_0"' not in rendered_str
