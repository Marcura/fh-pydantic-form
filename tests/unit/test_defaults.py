import datetime
from typing import Any, Dict, List, Literal, Optional
from unittest.mock import Mock

import pytest
from pydantic import BaseModel, Field

from fh_pydantic_form.defaults import default_dict_for_model, default_for_annotation


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
