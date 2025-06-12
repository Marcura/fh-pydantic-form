import logging
from enum import Enum
from types import UnionType
from typing import Any, Literal, Union, get_args, get_origin

logger = logging.getLogger(__name__)

# Sentinel value to indicate no default is available
_UNSET = object()


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


# Explicit exports for public API
__all__ = [
    "_is_optional_type",
    "_get_underlying_type_if_optional",
    "_is_literal_type",
    "_is_enum_type",
    "default_for_annotation",
]


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


# Local import placed after _UNSET is defined to avoid circular-import problems
from .defaults import default_for_annotation  # noqa: E402
