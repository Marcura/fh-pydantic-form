import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from unittest.mock import Mock

import pytest
from pydantic import BaseModel, Field

from fh_pydantic_form.defaults import default_dict_for_model, default_for_annotation


# Test Enums for defaults testing
class StatusEnum(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class PriorityEnum(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class EmptyEnum(Enum):
    pass


class TestDefaultForAnnotation:
    """Test the default_for_annotation helper function."""

    @pytest.mark.parametrize(
        "annotation, expected",
        [
            (str, ""),
            (int, 0),
            (float, 0.0),
            (bool, False),
            (Optional[str], None),
            (Optional[int], None),
            (Literal["A", "B", "C"], "A"),
            (Literal["HIGH", "MEDIUM", "LOW"], "HIGH"),
            (Literal[1, 2, 3], 1),
            (StatusEnum, "PENDING"),  # First enum member value
            (PriorityEnum, 1),  # First enum member value (integer)
            (Optional[StatusEnum], None),  # Optional enum → None
            (Optional[PriorityEnum], None),  # Optional enum → None
        ],
    )
    def test_primitive_defaults(self, annotation, expected):
        """Test that primitive types get correct default values."""
        result = default_for_annotation(annotation)
        assert result == expected

    def test_date_default(self, freeze_today):
        """Test that date annotation returns today's date."""
        result = default_for_annotation(datetime.date)
        assert result == datetime.date(2021, 1, 1)

    def test_time_default(self):
        """Test that time annotation returns midnight."""
        result = default_for_annotation(datetime.time)
        assert result == datetime.time(0, 0)

    def test_unknown_type_returns_none(self):
        """Test that unknown types return None as fallback."""

        class CustomType:
            pass

        result = default_for_annotation(CustomType)
        assert result is None

    def test_empty_literal_returns_none(self, mocker):
        """Test that Literal with no args returns None."""
        # Create a mock annotation that looks like Literal but has no args
        mock_annotation = Mock()
        mock_annotation.__origin__ = Literal

        mocker.patch("fh_pydantic_form.defaults.get_args", return_value=[])
        mocker.patch("fh_pydantic_form.defaults.get_origin", return_value=Literal)

        result = default_for_annotation(mock_annotation)
        assert result is None

    def test_enum_default_first_member_value(self):
        """Test that Enum defaults to first member's value."""
        result = default_for_annotation(StatusEnum)
        assert result == "PENDING"  # First member value

        result = default_for_annotation(PriorityEnum)
        assert result == 1  # First member value (integer)

    def test_optional_enum_default_none(self):
        """Test that Optional[Enum] defaults to None."""
        result = default_for_annotation(Optional[StatusEnum])
        assert result is None

        result = default_for_annotation(Optional[PriorityEnum])
        assert result is None

    def test_empty_enum_returns_none(self):
        """Test that empty Enum returns None."""
        result = default_for_annotation(EmptyEnum)
        assert result is None

    def test_enum_with_complex_values(self):
        """Test enum with complex member values."""

        class ComplexEnum(Enum):
            COMPLEX_A = {"key": "value", "number": 42}
            COMPLEX_B = ("tuple", "value")

        result = default_for_annotation(ComplexEnum)
        assert result == {"key": "value", "number": 42}  # First member value

    def test_enum_subclass_default(self):
        """Test that Enum subclasses work correctly."""
        from enum import Enum

        # Use functional API to avoid Python 3.12 inheritance restrictions
        ExtendedStatusEnum = Enum(
            "ExtendedStatusEnum",
            [
                ("PENDING", "PENDING"),
                ("IN_PROGRESS", "IN_PROGRESS"),
                ("COMPLETED", "COMPLETED"),
                ("ARCHIVED", "ARCHIVED"),
            ],
        )

        result = default_for_annotation(ExtendedStatusEnum)
        # Should get first member from the extended enum
        expected_first_member = list(ExtendedStatusEnum)[0].value
        assert result == expected_first_member


class TestDefaultDictForModel:
    """Test the default_dict_for_model helper function."""

    def test_simple_model_with_heuristic_defaults(self, freeze_today):
        """Test that a simple model gets heuristic defaults for required fields."""

        class SimpleModel(BaseModel):
            name: str
            age: int
            score: float
            is_active: bool
            created_date: datetime.date
            start_time: datetime.time

        result = default_dict_for_model(SimpleModel)

        expected = {
            "name": "",
            "age": 0,
            "score": 0.0,
            "is_active": False,
            "created_date": datetime.date(2021, 1, 1),
            "start_time": datetime.time(0, 0),
        }
        assert result == expected

    def test_model_with_explicit_defaults(self):
        """Test that explicit field defaults take precedence over heuristics."""

        class ModelWithDefaults(BaseModel):
            name: str = "Default Name"
            city: str = "Amsterdam"  # Non-empty default should be preserved
            age: int = 25
            is_premium: bool = True
            empty_string: str = ""  # Falsy default should still be preserved

        result = default_dict_for_model(ModelWithDefaults)

        expected = {
            "name": "Default Name",
            "city": "Amsterdam",
            "age": 25,
            "is_premium": True,
            "empty_string": "",  # Falsy but explicit default preserved
        }
        assert result == expected

    def test_model_with_default_factory(self, freeze_today):
        """Test that default_factory functions are called correctly."""

        class ModelWithFactory(BaseModel):
            tags: List[str] = Field(default_factory=list)
            created_at: datetime.date = Field(default_factory=datetime.date.today)
            start_time: datetime.time = Field(
                default_factory=lambda: datetime.time(9, 0)
            )

        result = default_dict_for_model(ModelWithFactory)

        expected = {
            "tags": [],
            "created_at": datetime.date(2021, 1, 1),
            "start_time": datetime.time(9, 0),
        }
        assert result == expected

    def test_model_with_optional_fields(self):
        """Test that optional fields without defaults get None."""

        class ModelWithOptionals(BaseModel):
            name: str  # Required, should get heuristic default
            nickname: Optional[str]  # Optional, should get None
            age: Optional[int]  # Optional, should get None
            description: Optional[str] = "Has default"  # Optional with default

        result = default_dict_for_model(ModelWithOptionals)

        expected = {
            "name": "",
            "nickname": None,
            "age": None,
            "description": "Has default",
        }
        assert result == expected

    def test_model_with_literal_fields(self):
        """Test that Literal fields get the first literal value."""

        class ModelWithLiterals(BaseModel):
            status: Literal["PENDING", "PROCESSING", "COMPLETED"]
            priority: Optional[Literal["HIGH", "MEDIUM", "LOW"]]

        result = default_dict_for_model(ModelWithLiterals)

        expected = {
            "status": "PENDING",
            "priority": None,  # Optional Literal gets None
        }
        assert result == expected

    def test_model_with_enum_fields(self):
        """Test that Enum fields get the first enum member value."""

        class ModelWithEnums(BaseModel):
            status: StatusEnum
            priority: Optional[PriorityEnum]

        result = default_dict_for_model(ModelWithEnums)

        expected = {
            "status": "PENDING",  # First member of StatusEnum
            "priority": None,  # Optional Enum gets None
        }
        assert result == expected

    def test_model_with_enum_defaults(self):
        """Test that explicit enum defaults take precedence."""

        class ModelWithEnumDefaults(BaseModel):
            status: StatusEnum = StatusEnum.COMPLETED
            priority: PriorityEnum = PriorityEnum.HIGH
            optional_status: Optional[StatusEnum] = StatusEnum.ACTIVE

        result = default_dict_for_model(ModelWithEnumDefaults)

        expected = {
            "status": "COMPLETED",  # Explicit default
            "priority": 3,  # Explicit default value
            "optional_status": "ACTIVE",  # Explicit default
        }
        assert result == expected

    def test_model_with_enum_factory_defaults(self):
        """Test that enum default_factory functions work correctly."""

        def get_default_status():
            return StatusEnum.ACTIVE

        class ModelWithEnumFactory(BaseModel):
            status: StatusEnum = Field(default_factory=get_default_status)
            priority: Optional[PriorityEnum] = Field(
                default_factory=lambda: PriorityEnum.MEDIUM
            )

        result = default_dict_for_model(ModelWithEnumFactory)

        expected = {
            "status": "ACTIVE",  # From factory
            "priority": 2,  # From lambda factory
        }
        assert result == expected

    def test_model_with_list_of_enums(self):
        """Test that List[Enum] fields start empty."""

        class ModelWithEnumLists(BaseModel):
            status_history: List[StatusEnum]
            priority_options: List[PriorityEnum] = Field(default_factory=list)

        result = default_dict_for_model(ModelWithEnumLists)

        expected: Dict[str, Any] = {
            "status_history": [],
            "priority_options": [],
        }
        assert result == expected

    def test_nested_model_with_enums(self):
        """Test that nested models with enums are processed correctly."""

        class EnumDetail(BaseModel):
            status: StatusEnum = StatusEnum.PENDING
            priority: Optional[PriorityEnum] = None

        class ModelWithNestedEnums(BaseModel):
            name: str
            detail: EnumDetail

        result = default_dict_for_model(ModelWithNestedEnums)

        expected = {
            "name": "",
            "detail": {
                "status": "PENDING",
                "priority": None,
            },
        }
        assert result == expected

    def test_model_with_list_fields(self):
        """Test that list fields start empty."""

        class ModelWithLists(BaseModel):
            tags: List[str]
            scores: List[int]
            items: List[dict]

        result = default_dict_for_model(ModelWithLists)

        expected: Dict[str, Any] = {
            "tags": [],
            "scores": [],
            "items": [],
        }
        assert result == expected

    def test_nested_model_recursion(self):
        """Test that nested models are recursively processed."""

        class InnerModel(BaseModel):
            value: str
            count: int = 5

        class OuterModel(BaseModel):
            name: str
            inner: InnerModel

        result = default_dict_for_model(OuterModel)

        expected = {
            "name": "",
            "inner": {
                "value": "",
                "count": 5,
            },
        }
        assert result == expected

    def test_deeply_nested_models(self):
        """Test that deeply nested structures work correctly."""

        class Level3(BaseModel):
            deep_value: str

        class Level2(BaseModel):
            level3: Level3
            items: List[str]

        class Level1(BaseModel):
            level2: Level2
            name: str = "Root"

        result = default_dict_for_model(Level1)

        expected = {
            "name": "Root",
            "level2": {
                "level3": {
                    "deep_value": "",
                },
                "items": [],
            },
        }
        assert result == expected

    def test_user_defined_default_classmethod_dict(self):
        """Test that user-defined default() classmethod returning dict takes precedence."""

        class CustomDefaultModel(BaseModel):
            name: str
            age: int

            @classmethod
            def default(cls):
                return {"name": "Custom Default", "age": 99}

        result = default_dict_for_model(CustomDefaultModel)

        expected = {"name": "Custom Default", "age": 99}
        assert result == expected

    def test_user_defined_default_classmethod_instance(self):
        """Test that user-defined default() classmethod returning instance works."""

        class CustomDefaultModel(BaseModel):
            name: str
            age: int

            @classmethod
            def default(cls):
                return cls(name="Instance Default", age=42)

        result = default_dict_for_model(CustomDefaultModel)

        expected = {"name": "Instance Default", "age": 42}
        assert result == expected

    def test_model_with_nested_model_defaults(self):
        """Test that nested models with their own defaults work correctly."""

        class Address(BaseModel):
            street: str = "Main St"
            city: str = "Anytown"
            is_billing: bool = False

        class Person(BaseModel):
            name: str
            address: Address

        result = default_dict_for_model(Person)

        expected = {
            "name": "",
            "address": {
                "street": "Main St",
                "city": "Anytown",
                "is_billing": False,
            },
        }
        assert result == expected

    def test_model_with_basemodel_default_conversion(self):
        """Test that BaseModel defaults are converted to dict format."""

        class Address(BaseModel):
            street: str = "Default St"
            city: str = "Default City"

        class Person(BaseModel):
            name: str
            address: Address = Field(
                default_factory=lambda: Address(
                    street="Factory St", city="Factory City"
                )
            )

        result = default_dict_for_model(Person)

        expected = {
            "name": "",
            "address": {
                "street": "Factory St",
                "city": "Factory City",
            },
        }
        assert result == expected

    def test_complex_mixed_scenario(self, freeze_today):
        """Test a complex model mixing all default types."""

        class Detail(BaseModel):
            value: str = "Default Detail"
            confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"

        class ComplexModel(BaseModel):
            # Heuristic defaults
            name: str
            age: int

            # Explicit defaults
            city: str = "Amsterdam"
            is_active: bool = True

            # Optional fields
            nickname: Optional[str]
            score: Optional[float] = 95.5

            # Factory defaults
            created_at: datetime.date = Field(default_factory=datetime.date.today)
            tags: List[str] = Field(default_factory=list)

            # Literal types
            status: Literal["PENDING", "ACTIVE", "INACTIVE"]

            # Nested model
            detail: Detail

            # List of primitives and models
            scores: List[int]
            more_details: List[Detail]

        result = default_dict_for_model(ComplexModel)

        expected = {
            "name": "",
            "age": 0,
            "city": "Amsterdam",
            "is_active": True,
            "nickname": None,
            "score": 95.5,
            "created_at": datetime.date(2021, 1, 1),
            "tags": [],
            "status": "PENDING",
            "detail": {
                "value": "Default Detail",
                "confidence": "HIGH",
            },
            "scores": [],
            "more_details": [],
        }
        assert result == expected

    def test_complex_mixed_scenario_with_enums(self, freeze_today):
        """Test a complex model mixing all default types including enums."""

        class EnumDetail(BaseModel):
            value: str = "Default Detail"
            confidence: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
            status: StatusEnum = StatusEnum.ACTIVE

        class ComplexEnumModel(BaseModel):
            # Heuristic defaults
            name: str
            age: int

            # Explicit defaults
            city: str = "Amsterdam"
            is_active: bool = True

            # Optional fields
            nickname: Optional[str]
            score: Optional[float] = 95.5

            # Factory defaults
            created_at: datetime.date = Field(default_factory=datetime.date.today)
            tags: List[str] = Field(default_factory=list)

            # Enum types
            status: StatusEnum
            priority: Optional[PriorityEnum]
            explicit_status: StatusEnum = StatusEnum.COMPLETED

            # Nested model with enums
            detail: EnumDetail

            # Lists with enums
            status_history: List[StatusEnum]
            priority_options: List[PriorityEnum] = Field(default_factory=list)

        result = default_dict_for_model(ComplexEnumModel)

        expected = {
            "name": "",
            "age": 0,
            "city": "Amsterdam",
            "is_active": True,
            "nickname": None,
            "score": 95.5,
            "created_at": datetime.date(2021, 1, 1),
            "tags": [],
            "status": "PENDING",  # First StatusEnum member
            "priority": None,  # Optional enum
            "explicit_status": "COMPLETED",  # Explicit default
            "detail": {
                "value": "Default Detail",
                "confidence": "HIGH",
                "status": "ACTIVE",  # Explicit default in nested model
            },
            "status_history": [],
            "priority_options": [],
        }
        assert result == expected


class TestEnumDefaults:
    """Dedicated test class for enum-specific default behavior."""

    def test_user_defined_enum_default_classmethod(self):
        """Test that user-defined default() classmethod works with enums."""

        class CustomEnumModel(BaseModel):
            status: StatusEnum
            priority: PriorityEnum

            @classmethod
            def default(cls):
                return {
                    "status": StatusEnum.COMPLETED,
                    "priority": PriorityEnum.HIGH,
                }

        result = default_dict_for_model(CustomEnumModel)

        expected = {
            "status": "COMPLETED",
            "priority": 3,
        }
        assert result == expected

    def test_enum_default_conversion_in_nested_models(self):
        """Test that enum defaults in nested models are converted to values."""

        class EnumAddress(BaseModel):
            street: str = "Main St"
            status: StatusEnum = StatusEnum.ACTIVE

        class PersonWithEnumAddress(BaseModel):
            name: str
            address: EnumAddress

        result = default_dict_for_model(PersonWithEnumAddress)

        expected = {
            "name": "",
            "address": {
                "street": "Main St",
                "status": "ACTIVE",
            },
        }
        assert result == expected

    def test_enum_basemodel_default_conversion(self):
        """Test that BaseModel defaults with enums are converted correctly."""

        class EnumConfig(BaseModel):
            status: StatusEnum = StatusEnum.PENDING
            priority: PriorityEnum = PriorityEnum.LOW

        class ConfiguredModel(BaseModel):
            name: str
            config: EnumConfig = Field(
                default_factory=lambda: EnumConfig(
                    status=StatusEnum.ACTIVE, priority=PriorityEnum.HIGH
                )
            )

        result = default_dict_for_model(ConfiguredModel)

        expected = {
            "name": "",
            "config": {
                "status": "ACTIVE",
                "priority": 3,
            },
        }
        assert result == expected

    @pytest.mark.parametrize(
        "enum_class, expected_default",
        [
            (StatusEnum, "PENDING"),
            (PriorityEnum, 1),
        ],
    )
    def test_parametrized_enum_defaults(self, enum_class, expected_default):
        """Test enum defaults with parametrized enum classes."""
        result = default_for_annotation(enum_class)
        assert result == expected_default
