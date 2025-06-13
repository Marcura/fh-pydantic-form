from __future__ import annotations
import logging
from typing import List, Tuple, Type, get_origin, get_args
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from fh_pydantic_form.type_helpers import _get_underlying_type_if_optional

logger = logging.getLogger(__name__)


def walk_path(
    model: Type[BaseModel], segments: List[str]
) -> Tuple[FieldInfo, List[str], Type]:
    """
    Resolve `segments` against `model`, stopping at the *list* field.

    Args:
        model: The BaseModel class to traverse
        segments: Path segments like ["main_address", "tags"] or ["other_addresses", "1", "tags"]
                 The final segment should always be a list field name.

    Returns:
        Tuple of:
        - list_field_info: the FieldInfo for the target list field
        - html_prefix_parts: segments used to build element IDs (includes indices)
        - item_type: the concrete python type of items in the list

    Raises:
        ValueError: if the path is invalid or doesn't lead to a list field
    """
    if not segments:
        raise ValueError("Empty path provided")

    current_model = model
    html_parts = []
    i = 0

    # Process all segments except the last one (which should be the list field)
    while i < len(segments) - 1:
        segment = segments[i]

        # Check if this segment is a field name
        if segment in current_model.model_fields:
            field_info = current_model.model_fields[segment]
            field_type = _get_underlying_type_if_optional(field_info.annotation)
            html_parts.append(segment)

            # Check if this is a list field (we're traversing into a list element)
            if get_origin(field_type) is list:
                # Next segment should be an index
                if i + 1 >= len(segments) - 1:
                    raise ValueError(f"Expected index after list field '{segment}'")

                next_segment = segments[i + 1]
                if not _is_index_segment(next_segment):
                    raise ValueError(
                        f"Expected index after list field '{segment}', got '{next_segment}'"
                    )

                # Get the item type of the list
                list_item_type = (
                    get_args(field_type)[0] if get_args(field_type) else None
                )
                if not list_item_type or not hasattr(list_item_type, "model_fields"):
                    raise ValueError(
                        f"List field '{segment}' does not contain BaseModel items"
                    )

                # Add the index to html_parts and update current model
                html_parts.append(next_segment)
                current_model = list_item_type

                # Skip the next segment (the index) since we processed it
                i += 2
                continue

            # Check if this is a BaseModel field
            elif hasattr(field_type, "model_fields"):
                current_model = field_type
                i += 1
            else:
                raise ValueError(f"Field '{segment}' is not a BaseModel or list type")

        elif _is_index_segment(segment):
            # This should only happen if we're processing an index that wasn't handled above
            raise ValueError(
                f"Unexpected index segment '{segment}' without preceding list field"
            )
        else:
            raise ValueError(
                f"Field '{segment}' not found in model {current_model.__name__}"
            )

    # Process the final segment (should be a list field)
    final_field_name = segments[-1]
    if final_field_name not in current_model.model_fields:
        raise ValueError(
            f"Field '{final_field_name}' not found in model {current_model.__name__}"
        )

    list_field_info = current_model.model_fields[final_field_name]
    list_field_type = _get_underlying_type_if_optional(list_field_info.annotation)

    # Verify this is actually a list field
    if get_origin(list_field_type) is not list:
        raise ValueError(f"Final field '{final_field_name}' is not a list type")

    # Get the item type
    item_type_args = get_args(list_field_type)
    if not item_type_args:
        raise ValueError(
            f"Cannot determine item type for list field '{final_field_name}'"
        )

    item_type = item_type_args[0]
    html_parts.append(final_field_name)

    logger.debug(
        f"walk_path resolved: {segments} -> field_info={list_field_info}, html_parts={html_parts}, item_type={item_type}"
    )

    return list_field_info, html_parts, item_type


def _is_index_segment(segment: str) -> bool:
    """
    Check if a segment represents an index (purely numeric or placeholder like 'new_1234').

    Args:
        segment: The segment to check

    Returns:
        True if the segment represents an index
    """
    # Pure numeric (like "0", "1", "2")
    if segment.isdigit():
        return True

    # Placeholder format (like "new_1234567890")
    if segment.startswith("new_") and len(segment) > 4:
        timestamp_part = segment[4:]
        return timestamp_part.isdigit()

    return False
