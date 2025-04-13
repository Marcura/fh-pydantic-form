from typing import Any, Literal, Union, get_args, get_origin


def _is_optional_type(annotation: Any) -> bool:
    """
    Check if an annotation is Optional[T] (Union[T, None]).

    Args:
        annotation: The type annotation to check

    Returns:
        True if the annotation is Optional[T], False otherwise
    """
    origin = get_origin(annotation)
    if origin is Union:
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
