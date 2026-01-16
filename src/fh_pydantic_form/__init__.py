import datetime
import decimal
from enum import Enum
from typing import Literal, get_args, get_origin

from pydantic import BaseModel

from fh_pydantic_form.comparison_form import (
    ComparisonForm,
    comparison_form_js,
    simple_diff_metrics,
)
from fh_pydantic_form.defaults import (
    default_dict_for_model,
    default_for_annotation,
)
from fh_pydantic_form.field_renderers import (
    BaseModelFieldRenderer,
    BooleanFieldRenderer,
    ChoiceItem,
    DateFieldRenderer,
    DecimalFieldRenderer,
    EnumFieldRenderer,
    ListChoiceFieldRenderer,
    ListFieldRenderer,
    ListLiteralFieldRenderer,
    LiteralFieldRenderer,
    NumberFieldRenderer,
    StringFieldRenderer,
    TimeFieldRenderer,
    list_choice_js as list_choice_js,  # Deprecated, kept for backward compatibility
    list_literal_js as list_literal_js,  # Deprecated, kept for backward compatibility
)
from fh_pydantic_form.form_renderer import PydanticForm, list_manipulation_js
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    MetricEntry,
    MetricsDict,
    _get_underlying_type_if_optional,
)
from fh_pydantic_form.ui_style import (
    SpacingTheme,
    SpacingValue,
    spacing,
    spacing_many,
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
    FieldRendererRegistry.register_type_renderer(decimal.Decimal, DecimalFieldRenderer)
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

    # Register List[Literal] and List[Enum] renderer BEFORE generic list renderer
    def is_list_choice_field(field_info):
        """Check if field is List[Literal[...]] or List[Enum]"""
        annotation = getattr(field_info, "annotation", None)
        if annotation is None:
            return False

        # Unwrap Optional if present
        underlying_type = _get_underlying_type_if_optional(annotation)

        # Must be a list type
        if get_origin(underlying_type) is not list:
            return False

        # Get the item type
        list_args = get_args(underlying_type)
        if not list_args:
            return False

        item_type = list_args[0]
        item_type_base = _get_underlying_type_if_optional(item_type)

        # Check for Literal item type
        if get_origin(item_type_base) is Literal:
            return True

        # Check for Enum item type
        if isinstance(item_type_base, type) and issubclass(item_type_base, Enum):
            return True

        return False

    FieldRendererRegistry.register_type_renderer_with_predicate(
        is_list_choice_field, ListChoiceFieldRenderer
    )

    # Register list renderer for List[*] types (generic fallback)
    def is_list_field(field_info):
        """Check if field is a list type, including Optional[List[...]]"""
        annotation = getattr(field_info, "annotation", None)
        if annotation is None:
            return False

        # Handle Optional[List[...]] by unwrapping the Optional
        underlying_type = _get_underlying_type_if_optional(annotation)

        # Check if the underlying type is a list
        return get_origin(underlying_type) is list

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
    "spacing_many",
    "default_dict_for_model",
    "default_for_annotation",
    "ComparisonForm",
    "MetricEntry",
    "MetricsDict",
    "comparison_form_js",
    "simple_diff_metrics",
    "ListChoiceFieldRenderer",
    "ListLiteralFieldRenderer",
    "ChoiceItem",
    # Note: list_choice_js and list_literal_js are deprecated (return empty script)
    # and are not exported but remain importable for backward compatibility
]
