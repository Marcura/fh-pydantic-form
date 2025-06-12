import datetime
from enum import Enum
from typing import Literal, get_origin

from pydantic import BaseModel

from fh_pydantic_form.field_renderers import (
    BaseModelFieldRenderer,
    BooleanFieldRenderer,
    DateFieldRenderer,
    EnumFieldRenderer,
    ListFieldRenderer,
    LiteralFieldRenderer,
    NumberFieldRenderer,
    StringFieldRenderer,
    TimeFieldRenderer,
)
from fh_pydantic_form.form_renderer import PydanticForm, list_manipulation_js
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    _get_underlying_type_if_optional,
)
from fh_pydantic_form.ui_style import (
    SpacingTheme,
    SpacingValue,
    spacing,
    COMPACT_EXTRA_CSS,
)
from fh_pydantic_form.defaults import (
    default_dict_for_model,
    default_for_annotation,
)


def register_default_renderers() -> None:
    """
    Register built-in renderers for common types

    This method sets up:
    - Simple type renderers (str, bool, int, float, date, time)
    - Special field renderers (Detail)
    - Predicate-based renderers (Literal fields, Enum fields, lists, BaseModels)
    """
    # Import renderers by getting them from globals

    # Simple types
    FieldRendererRegistry.register_type_renderer(str, StringFieldRenderer)
    FieldRendererRegistry.register_type_renderer(bool, BooleanFieldRenderer)
    FieldRendererRegistry.register_type_renderer(int, NumberFieldRenderer)
    FieldRendererRegistry.register_type_renderer(float, NumberFieldRenderer)
    FieldRendererRegistry.register_type_renderer(datetime.date, DateFieldRenderer)
    FieldRendererRegistry.register_type_renderer(datetime.time, TimeFieldRenderer)

    # Register Enum field renderer (before Literal to prioritize Enum handling)
    def is_enum_field(field_info):
        """Check if field is an Enum type"""
        annotation = getattr(field_info, "annotation", None)
        if not annotation:
            return False
        underlying_type = _get_underlying_type_if_optional(annotation)
        return isinstance(underlying_type, type) and issubclass(underlying_type, Enum)

    FieldRendererRegistry.register_type_renderer_with_predicate(
        is_enum_field, EnumFieldRenderer
    )

    # Register Literal field renderer (after Enum to avoid conflicts)
    def is_literal_field(field_info):
        """Check if field is a Literal type"""
        annotation = getattr(field_info, "annotation", None)
        if not annotation:
            return False
        underlying_type = _get_underlying_type_if_optional(annotation)
        origin = get_origin(underlying_type)
        return origin is Literal

    FieldRendererRegistry.register_type_renderer_with_predicate(
        is_literal_field, LiteralFieldRenderer
    )

    # Register list renderer for List[*] types
    def is_list_field(field_info):
        """Check if field is a list type"""
        annotation = getattr(field_info, "annotation", None)
        return (
            annotation is not None
            and hasattr(annotation, "__origin__")
            and annotation.__origin__ is list
        )

    FieldRendererRegistry.register_type_renderer_with_predicate(
        is_list_field, ListFieldRenderer
    )

    # Register the BaseModelFieldRenderer for Pydantic models
    def is_basemodel_field(field_info):
        """Check if field is a BaseModel"""
        annotation = getattr(field_info, "annotation", None)
        underlying_type = _get_underlying_type_if_optional(annotation)

        return (
            isinstance(underlying_type, type)
            and issubclass(underlying_type, BaseModel)
            and not is_list_field(field_info)
        )

    FieldRendererRegistry.register_type_renderer_with_predicate(
        is_basemodel_field, BaseModelFieldRenderer
    )


register_default_renderers()


__all__ = [
    "PydanticForm",
    "FieldRendererRegistry",
    "list_manipulation_js",
    "SpacingTheme",
    "SpacingValue",
    "spacing",
    "COMPACT_EXTRA_CSS",
    "default_dict_for_model",
    "default_for_annotation",
]
