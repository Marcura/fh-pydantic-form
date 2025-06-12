from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, get_args, get_origin, Literal

from pydantic import BaseModel

from .type_helpers import _UNSET, get_default, _is_optional_type


def _today():
    """Wrapper for datetime.date.today() to enable testability."""
    return _dt.date.today()


# Simple type defaults - callables will be invoked to get fresh values
_SIMPLE_DEFAULTS = {
    str: "",
    int: 0,
    float: 0.0,
    bool: False,
    _dt.date: lambda: _today(),  # callable - gets current date (late-bound)
    _dt.time: lambda: _dt.time(0, 0),  # callable - midnight
}


def _first_literal_choice(annotation):
    """Get the first literal value from a Literal type annotation."""
    args = get_args(annotation)
    return args[0] if args else None


def default_for_annotation(annotation: Any) -> Any:
    """
    Return a sensible runtime default for type annotations.

    Args:
        annotation: The type annotation to generate a default for

    Returns:
        A sensible default value for the given type
    """
    origin = get_origin(annotation) or annotation

    # Optional[T] → None
    if _is_optional_type(annotation):
        return None

    # Literal[...] → first literal value
    if origin is Literal:
        return _first_literal_choice(annotation)

    # Enum → first member value
    if isinstance(origin, type) and issubclass(origin, Enum):
        enum_members = list(origin)
        return enum_members[0].value if enum_members else None

    # Simple primitives & datetime helpers
    if origin in _SIMPLE_DEFAULTS:
        default_val = _SIMPLE_DEFAULTS[origin]
        return default_val() if callable(default_val) else default_val

    # For unknown types, return None as a safe fallback
    return None


def _convert_enum_values(obj: Any) -> Any:
    """
    Recursively convert enum instances to their values in nested structures.

    Args:
        obj: Object that may contain enum instances

    Returns:
        Object with enum instances converted to their values
    """
    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {key: _convert_enum_values(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_convert_enum_values(item) for item in obj]
    else:
        return obj


def default_dict_for_model(model_cls: type[BaseModel]) -> dict[str, Any]:
    """
    Recursively build a dict with sensible defaults for all fields in a Pydantic model.

    Precedence order:
    1. User-defined @classmethod default() override
    2. Field.default or Field.default_factory values
    3. None for Optional fields without explicit defaults
    4. Smart defaults for primitive types

    Args:
        model_cls: The Pydantic model class to generate defaults for

    Returns:
        Dictionary with default values for all model fields
    """
    # Check for user-defined default classmethod first
    if hasattr(model_cls, "default") and callable(model_cls.default):
        instance = model_cls.default()  # may return model instance or dict
        result = (
            instance.model_dump() if isinstance(instance, BaseModel) else dict(instance)
        )
        return _convert_enum_values(result)

    out: dict[str, Any] = {}

    for name, field in model_cls.model_fields.items():
        # --- NEW: recognise "today" factories for date fields early ---------
        if (get_origin(field.annotation) or field.annotation) is _dt.date and getattr(
            field, "default_factory", None
        ) is not None:
            # Never call the real factory – delegate to our _today() helper so
            # tests can patch it (freeze_today fixture).
            out[name] = _today()
            continue
        # --------------------------------------------------------------------

        # 1. Check for model-supplied default or factory
        default_val = get_default(field)  # returns _UNSET if no default
        if default_val is not _UNSET:
            # Handle BaseModel defaults by converting to dict
            if hasattr(default_val, "model_dump"):
                out[name] = default_val.model_dump()
            # Convert enum instances to their values
            elif isinstance(default_val, Enum):
                out[name] = default_val.value
            else:
                out[name] = default_val
            continue

        # 2. Optional fields without explicit default → None
        if _is_optional_type(field.annotation):
            out[name] = None
            continue

        # 3. Handle nested structures
        ann = field.annotation
        base_ann = get_origin(ann) or ann

        # List fields start empty
        if base_ann is list:
            out[name] = []
            continue

        # Nested BaseModel - recurse
        if isinstance(base_ann, type) and issubclass(base_ann, BaseModel):
            out[name] = default_dict_for_model(base_ann)
            continue

        # 4. Fallback to smart defaults for primitives
        out[name] = default_for_annotation(ann)

    return _convert_enum_values(out)
