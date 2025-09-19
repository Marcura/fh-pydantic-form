# Explicit exports for public API
__all__ = [
    "_is_optional_type",
    "_get_underlying_type_if_optional",
    "_is_literal_type",
    "_is_enum_type",
    "_is_skip_json_schema_field",
    "normalize_path_segments",
    "MetricEntry",
    "MetricsDict",
    "DecorationScope",
]


import logging
from enum import Enum
from types import UnionType
from typing import (
    Annotated,
    Any,
    Dict,
    List,
    Literal,
    TypedDict,
    Union,
    get_args,
    get_origin,
)

from fh_pydantic_form.constants import _UNSET

logger = logging.getLogger(__name__)


class DecorationScope(str, Enum):
    """Controls which metric decorations are applied to an element"""

    BORDER = "border"
    BULLET = "bullet"
    BOTH = "both"


def normalize_path_segments(path_segments: List[str]) -> str:
    """Collapse path segments into a dot path ignoring list indices and placeholders."""
    normalized: List[str] = []
    for segment in path_segments:
        # Coerce to string to avoid surprises from enums or numbers
        seg_str = str(segment)
        if seg_str.isdigit() or seg_str.startswith("new_"):
            continue
        normalized.append(seg_str)
    return ".".join(normalized)


def _is_skip_json_schema_field(annotation_or_field_info: Any) -> bool:
    """
    Check if a field annotation or field_info indicates it should be skipped in JSON schema.

    This handles the pattern where SkipJsonSchema is used with typing.Annotated:
    - Annotated[str, SkipJsonSchema()]
    - SkipJsonSchema[str] (which internally uses Annotated)
    - Field metadata containing SkipJsonSchema (Pydantic 2 behavior)

    Args:
        annotation_or_field_info: The field annotation or field_info to check

    Returns:
        True if the field should be skipped in JSON schema
    """
    try:
        from pydantic.json_schema import SkipJsonSchema

        skip_json_schema_cls = SkipJsonSchema
    except ImportError:  # very old Pydantic
        skip_json_schema_cls = None

    if skip_json_schema_cls is None:
        return False

    # Check if it's a field_info object with metadata
    if hasattr(annotation_or_field_info, "metadata"):
        metadata = getattr(annotation_or_field_info, "metadata", [])
        if metadata:
            for item in metadata:
                if (
                    item is skip_json_schema_cls
                    or isinstance(item, skip_json_schema_cls)
                    or (
                        hasattr(item, "__class__")
                        and item.__class__.__name__ == "SkipJsonSchema"
                    )
                ):
                    return True

    # Fall back to checking annotation (for backward compatibility)
    annotation = annotation_or_field_info
    if hasattr(annotation_or_field_info, "annotation"):
        annotation = getattr(annotation_or_field_info, "annotation")

    # 1. Direct or generic alias
    if (
        annotation is skip_json_schema_cls
        or getattr(annotation, "__origin__", None) is skip_json_schema_cls
    ):
        return True

    # 2. Something like Annotated[T, SkipJsonSchema()]
    if get_origin(annotation) is Annotated:
        for meta in get_args(annotation)[1:]:
            meta_class = getattr(meta, "__class__", None)
            if (
                meta is skip_json_schema_cls  # plain class
                or isinstance(meta, skip_json_schema_cls)  # instance
                or (meta_class is not None and meta_class.__name__ == "SkipJsonSchema")
            ):
                return True

    # 3. Fallback – cheap but effective, but be more specific to avoid false positives
    # Only match if SkipJsonSchema appears as a standalone word (not part of a class name)
    repr_str = repr(annotation)
    # Look for patterns like "SkipJsonSchema[" or "SkipJsonSchema(" or "SkipJsonSchema]"
    # but not "SomeClassNameSkipJsonSchema"
    import re

    return bool(re.search(r"\bSkipJsonSchema\b", repr_str))


# Metrics types for field-level annotations
class MetricEntry(TypedDict, total=False):
    """Metrics for annotating field values with scores, colors, and comments"""

    metric: float | int | str  # Metric value (0-1 score, count, or label)
    color: str  # CSS-compatible color string
    comment: str  # Free-form text for tooltips/hover


# Type alias for metrics mapping
MetricsDict = Dict[
    str, MetricEntry
]  # Keys are dot-paths like "address.street" or "tags[0]"


def _is_optional_type(annotation: Any) -> bool:
    """
    Check if an annotation is Optional[T] (Union[T, None]).

    Args:
        annotation: The type annotation to check

    Returns:
        True if the annotation is Optional[T], False otherwise
    """
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        args = get_args(annotation)
        # Check if NoneType is one of the args and there are exactly two args
        return len(args) == 2 and type(None) in args
    return False


def _get_underlying_type_if_optional(annotation: Any) -> Any:
    """
    Extract the type T from Optional[T], otherwise return the original annotation.

    Args:
        annotation: The type annotation, potentially Optional[T]

    Returns:
        The underlying type if Optional, otherwise the original annotation
    """
    if _is_optional_type(annotation):
        args = get_args(annotation)
        # Return the non-None type
        return args[0] if args[1] is type(None) else args[1]
    return annotation


def _is_literal_type(annotation: Any) -> bool:
    """Check if the underlying type of an annotation is Literal."""
    underlying_type = _get_underlying_type_if_optional(annotation)
    return get_origin(underlying_type) is Literal


def _is_enum_type(annotation: Any) -> bool:
    """Check if the underlying type of an annotation is Enum."""
    underlying_type = _get_underlying_type_if_optional(annotation)
    return isinstance(underlying_type, type) and issubclass(underlying_type, Enum)


def get_default(field_info: Any) -> Any:
    """
    Extract the default value from a Pydantic field definition.

    Handles both literal defaults and default_factory functions.

    Args:
        field_info: The Pydantic FieldInfo object

    Returns:
        The default value if available, or _UNSET sentinel if no default exists
    """
    # Check for literal default value (including None, but not Undefined)
    if hasattr(field_info, "default") and not _is_pydantic_undefined(
        field_info.default
    ):
        return field_info.default

    # Check for default_factory
    default_factory = getattr(field_info, "default_factory", None)
    if default_factory is not None and callable(default_factory):
        try:
            return default_factory()
        except Exception as exc:
            logger.warning(f"default_factory failed for field: {exc}")
            # Don't raise - return sentinel to indicate no usable default

    return _UNSET


def _is_pydantic_undefined(value: Any) -> bool:
    """
    Check if a value is Pydantic's Undefined sentinel.

    Args:
        value: The value to check

    Returns:
        True if the value represents Pydantic's undefined default
    """
    # Check if value is None first (common case)
    if value is None:
        return False

    # Check for various Pydantic undefined markers
    if hasattr(value, "__class__"):
        class_name = value.__class__.__name__
        if class_name in ("Undefined", "PydanticUndefined"):
            return True

    # Check string representation as fallback
    str_repr = str(value)
    if str_repr in ("PydanticUndefined", "<class 'pydantic_core.PydanticUndefined'>"):
        return True

    # Check for pydantic.fields.Undefined (older versions)
    try:
        from pydantic import fields

        if hasattr(fields, "Undefined") and value is fields.Undefined:
            return True
    except ImportError:
        pass

    # Check for pydantic_core.PydanticUndefined (newer versions)
    try:
        import pydantic_core

        if (
            hasattr(pydantic_core, "PydanticUndefined")
            and value is pydantic_core.PydanticUndefined
        ):
            return True
    except ImportError:
        pass

    return False
