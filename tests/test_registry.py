from datetime import date, time
from typing import List, Literal, Optional

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import (
    BaseFieldRenderer,
    BooleanFieldRenderer,
    ListFieldRenderer,
    LiteralFieldRenderer,
    NumberFieldRenderer,
    StringFieldRenderer,
)
from fh_pydantic_form.registry import FieldRendererRegistry


# Custom field renderer for testing
class CustomFieldRenderer(BaseFieldRenderer):
    """Custom renderer for testing."""

    def render_input(self):
        return None  # Just a stub for testing


# Simple test model for renderer testing
class SampleModelForRegistry(BaseModel):
    """Test model for renderer testing."""

    name: str
    age: int


def test_registry_singleton():
    """Test that registry is a singleton."""
    registry1 = FieldRendererRegistry()
    registry2 = FieldRendererRegistry()

    assert registry1 is registry2


def test_register_type_renderer():
    """Test registering type-specific renderers."""
    registry = FieldRendererRegistry()

    # Store original renderers to restore later
    original_renderers = registry._type_renderers.copy()

    try:
        # Register a custom renderer
        registry.register_type_renderer(SampleModelForRegistry, CustomFieldRenderer)

        # Verify registration
        assert (
            registry._type_renderers.get(SampleModelForRegistry) is CustomFieldRenderer
        )
    finally:
        # Restore original renderers
        FieldRendererRegistry._type_renderers = original_renderers


def test_register_type_name_renderer():
    """Test registering type name-specific renderers."""
    registry = FieldRendererRegistry()

    # Store original renderers to restore later
    original_renderers = registry._type_name_renderers.copy()

    try:
        # Register a custom renderer by type name
        registry.register_type_name_renderer(
            "SampleModelForRegistry", CustomFieldRenderer
        )

        # Verify registration
        assert (
            registry._type_name_renderers["SampleModelForRegistry"]
            is CustomFieldRenderer
        )
    finally:
        # Restore original renderers
        FieldRendererRegistry._type_name_renderers = original_renderers


def test_register_type_renderer_with_predicate():
    """Test registering predicate-based renderers."""
    registry = FieldRendererRegistry()

    # Store original predicate renderers to restore later
    original_renderers = registry._predicate_renderers.copy()

    try:
        # Define a predicate function
        def is_sample_model(field_info):
            return getattr(field_info, "annotation", None) is SampleModelForRegistry

        # Register a predicate renderer
        registry.register_type_renderer_with_predicate(
            is_sample_model, CustomFieldRenderer
        )

        # Verify registration - find our predicate in the list
        assert any(
            p[0] is is_sample_model and p[1] is CustomFieldRenderer
            for p in registry._predicate_renderers
        )

        # Test the predicate function
        field_info = FieldInfo(annotation=SampleModelForRegistry)
        assert is_sample_model(field_info) is True
    finally:
        # Restore original renderers
        FieldRendererRegistry._predicate_renderers = original_renderers


def test_register_list_item_renderer():
    """Test registering list item renderers."""
    registry = FieldRendererRegistry()

    # Store original renderers to restore later
    original_renderers = registry._list_item_renderers.copy()

    try:
        # Register a list item renderer
        registry.register_list_item_renderer(
            SampleModelForRegistry, CustomFieldRenderer
        )

        # Verify registration
        assert (
            registry._list_item_renderers.get(SampleModelForRegistry)
            is CustomFieldRenderer
        )
    finally:
        # Restore original renderers
        FieldRendererRegistry._list_item_renderers = original_renderers


def test_get_renderer_for_basic_types():
    """Test getting renderers for basic field types."""
    registry = FieldRendererRegistry()

    # Test getting renderers for basic types
    str_field = FieldInfo(annotation=str)
    int_field = FieldInfo(annotation=int)
    float_field = FieldInfo(annotation=float)
    bool_field = FieldInfo(annotation=bool)
    date_field = FieldInfo(annotation=date)
    time_field = FieldInfo(annotation=time)

    # Since this is a singleton, we can only assert that these all return a renderer
    # The exact renderer may change if other tests registered custom ones
    assert registry.get_renderer("name", str_field) is not None
    assert registry.get_renderer("age", int_field) is not None
    assert registry.get_renderer("score", float_field) is not None
    assert registry.get_renderer("is_active", bool_field) is not None
    assert registry.get_renderer("birth_date", date_field) is not None
    assert registry.get_renderer("start_time", time_field) is not None


def test_get_renderer_for_optional_types():
    """Test getting renderers for optional field types."""
    registry = FieldRendererRegistry()

    # Test getting renderers for optional types
    opt_str_field = FieldInfo(annotation=Optional[str])
    opt_int_field = FieldInfo(annotation=Optional[int])
    opt_bool_field = FieldInfo(annotation=Optional[bool])

    assert registry.get_renderer("name", opt_str_field) is StringFieldRenderer
    assert registry.get_renderer("age", opt_int_field) is NumberFieldRenderer
    assert registry.get_renderer("is_active", opt_bool_field) is BooleanFieldRenderer


def test_get_renderer_for_literal_type():
    """Test getting renderers for literal field types."""
    registry = FieldRendererRegistry()

    # Test with literal field
    literal_field = FieldInfo(annotation=Literal["A", "B", "C"])
    opt_literal_field = FieldInfo(annotation=Optional[Literal["A", "B", "C"]])

    assert registry.get_renderer("status", literal_field) is LiteralFieldRenderer
    assert (
        registry.get_renderer("opt_status", opt_literal_field) is LiteralFieldRenderer
    )


def test_get_renderer_for_list_type():
    """Test getting renderers for list field types."""
    registry = FieldRendererRegistry()

    # Test with list field
    list_str_field = FieldInfo(annotation=List[str])
    list_model_field = FieldInfo(annotation=List[SampleModelForRegistry])

    assert registry.get_renderer("tags", list_str_field) is ListFieldRenderer
    assert registry.get_renderer("items", list_model_field) is ListFieldRenderer


def test_get_renderer_for_basemodel_type():
    """Test getting renderers for BaseModel field types."""
    registry = FieldRendererRegistry()

    # Store original renderers to restore later
    original_renderers = registry._type_renderers.copy()
    original_predicates = registry._predicate_renderers.copy()

    try:
        # Test with BaseModel field
        model_field = FieldInfo(annotation=SampleModelForRegistry)
        opt_model_field = FieldInfo(annotation=Optional[SampleModelForRegistry])

        # The result might be BaseModelFieldRenderer or a custom renderer if it was registered earlier
        # Just check that we get a renderer back
        assert registry.get_renderer("model", model_field) is not None
        assert registry.get_renderer("opt_model", opt_model_field) is not None
    finally:
        # Restore original renderers
        FieldRendererRegistry._type_renderers = original_renderers
        FieldRendererRegistry._predicate_renderers = original_predicates


def test_get_renderer_with_custom_registration():
    """Test getting renderers with custom registrations."""
    registry = FieldRendererRegistry()

    # Register a custom renderer
    original_renderers = registry._type_renderers.copy()
    try:
        registry.register_type_renderer(SampleModelForRegistry, CustomFieldRenderer)

        # Test with the custom registered type
        model_field = FieldInfo(annotation=SampleModelForRegistry)
        assert registry.get_renderer("model", model_field) is CustomFieldRenderer
    finally:
        # Restore original renderers
        FieldRendererRegistry._type_renderers = original_renderers


def test_get_list_item_renderer():
    """Test getting list item renderers."""
    registry = FieldRendererRegistry()

    # Register a list item renderer
    original_renderers = registry._list_item_renderers.copy()
    try:
        registry.register_list_item_renderer(
            SampleModelForRegistry, CustomFieldRenderer
        )

        # Test getting the renderer
        assert (
            registry.get_list_item_renderer(SampleModelForRegistry)
            is CustomFieldRenderer
        )

        # Test with subclass
        class SubModel(SampleModelForRegistry):
            extra: str

        assert registry.get_list_item_renderer(SubModel) is CustomFieldRenderer

        # Test with non-registered type
        assert registry.get_list_item_renderer(str) is None
    finally:
        # Restore original renderers
        FieldRendererRegistry._list_item_renderers = original_renderers
