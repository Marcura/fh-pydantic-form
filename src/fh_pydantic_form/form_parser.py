import logging
from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    get_args,
    get_origin,
)

from fh_pydantic_form.type_helpers import (
    _get_underlying_type_if_optional,
    _is_enum_type,
    _is_literal_type,
    _is_optional_type,
    _is_skip_json_schema_field,
)

logger = logging.getLogger(__name__)


def _identify_list_fields(model_class) -> Dict[str, Dict[str, Any]]:
    """
    Identifies list fields in a model and their item types.

    Args:
        model_class: The Pydantic model class to analyze

    Returns:
        Dictionary mapping field names to their metadata
    """
    list_fields = {}
    for field_name, field_info in model_class.model_fields.items():
        annotation = getattr(field_info, "annotation", None)
        if annotation is not None:
            # Handle Optional[List[...]] by unwrapping the Optional
            base_ann = _get_underlying_type_if_optional(annotation)
            if get_origin(base_ann) is list:
                item_type = get_args(base_ann)[0]
                list_fields[field_name] = {
                    "item_type": item_type,
                    "is_model_type": hasattr(item_type, "model_fields"),
                    "field_info": field_info,  # Store for later use if needed
                }
    return list_fields


def _parse_non_list_fields(
    form_data: Dict[str, Any],
    model_class,
    list_field_defs: Dict[str, Dict[str, Any]],
    base_prefix: str = "",
    exclude_fields: Optional[List[str]] = None,
    keep_skip_json_pathset: Optional[set[str]] = None,
    current_field_path: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Parses non-list fields from form data based on the model definition.

    Args:
        form_data: Dictionary containing form field data
        model_class: The Pydantic model class defining the structure
        list_field_defs: Dictionary of list field definitions (to skip)
        base_prefix: Prefix to use when looking up field names in form_data
        exclude_fields: Optional list of field names to exclude from parsing
        keep_skip_json_pathset: Optional set of normalized paths for SkipJsonSchema fields to keep

    Returns:
        Dictionary with parsed non-list fields
    """
    result: Dict[str, Any] = {}
    exclude_fields = exclude_fields or []
    keep_skip_json_pathset = keep_skip_json_pathset or set()

    # Helper function to check if a SkipJsonSchema field should be kept
    def _should_keep_skip_field(path_segments: List[str]) -> bool:
        from fh_pydantic_form.type_helpers import normalize_path_segments

        normalized = normalize_path_segments(path_segments)
        return bool(normalized) and normalized in keep_skip_json_pathset

    # Calculate the current path context for fields at this level
    # For top-level parsing, this will be empty
    # For nested parsing, this will contain the nested path segments
    current_path_segments: List[str] = []
    if current_field_path is not None:
        # Use explicitly passed field path
        current_path_segments = current_field_path
    # For top-level parsing (base_prefix is just form name), current_path_segments remains empty

    for field_name, field_info in model_class.model_fields.items():
        if field_name in list_field_defs:
            continue  # Skip list fields, handled separately

        # Skip excluded fields - they will be handled by default injection later
        if field_name in exclude_fields:
            continue

        # Skip SkipJsonSchema fields unless they're explicitly kept
        if _is_skip_json_schema_field(field_info):
            field_path_segments = current_path_segments + [field_name]
            if not _should_keep_skip_field(field_path_segments):
                continue

        # Create full key with prefix
        full_key = f"{base_prefix}{field_name}"

        annotation = getattr(field_info, "annotation", None)

        # Handle boolean fields (including Optional[bool])
        if annotation is bool or (
            _is_optional_type(annotation)
            and _get_underlying_type_if_optional(annotation) is bool
        ):
            result[field_name] = _parse_boolean_field(full_key, form_data)

        # Handle Literal fields (including Optional[Literal[...]])
        elif _is_literal_type(annotation):
            if full_key in form_data:  # User sent it
                result[field_name] = _parse_literal_field(
                    full_key, form_data, field_info
                )
            elif _is_optional_type(annotation):  # Optional but omitted
                result[field_name] = None
            # otherwise leave the key out – defaults will be injected later

        # Handle Enum fields (including Optional[Enum])
        elif _is_enum_type(annotation):
            if full_key in form_data:  # User sent it
                result[field_name] = _parse_enum_field(full_key, form_data, field_info)
            elif _is_optional_type(annotation):  # Optional but omitted
                result[field_name] = None
            # otherwise leave the key out – defaults will be injected later

        # Handle nested model fields (including Optional[NestedModel])
        elif (
            isinstance(annotation, type)
            and hasattr(annotation, "model_fields")
            or (
                _is_optional_type(annotation)
                and isinstance(_get_underlying_type_if_optional(annotation), type)
                and hasattr(
                    _get_underlying_type_if_optional(annotation), "model_fields"
                )
            )
        ):
            # Get the nested model class (unwrap Optional if needed)
            nested_model_class = _get_underlying_type_if_optional(annotation)

            # Parse the nested model - pass the base_prefix, exclude_fields, and keep paths
            nested_field_path = current_path_segments + [field_name]
            nested_value = _parse_nested_model_field(
                field_name,
                form_data,
                nested_model_class,
                field_info,
                base_prefix,
                exclude_fields,
                keep_skip_json_pathset,
                nested_field_path,
            )

            # Only assign if we got a non-None value or the field is not optional
            if nested_value is not None:
                result[field_name] = nested_value
            elif _is_optional_type(annotation):
                # Explicitly set None for optional nested models
                result[field_name] = None

        # Handle simple fields
        else:
            if full_key in form_data:  # User sent it
                result[field_name] = _parse_simple_field(
                    full_key, form_data, field_info
                )
            elif _is_optional_type(annotation):  # Optional but omitted
                result[field_name] = None
            # otherwise leave the key out – defaults will be injected later

    return result


def _parse_boolean_field(field_name: str, form_data: Dict[str, Any]) -> bool:
    """
    Parse a boolean field from form data.

    Args:
        field_name: Name of the field to parse
        form_data: Dictionary containing form field data

    Returns:
        Boolean value - True if field name exists in form_data, False otherwise
    """
    return field_name in form_data


def _parse_literal_field(field_name: str, form_data: Dict[str, Any], field_info) -> Any:
    """
    Parse a Literal field, converting empty string OR '-- None --' to None for optional fields.

    Args:
        field_name: Name of the field to parse
        form_data: Dictionary containing form field data
        field_info: FieldInfo object to check for optionality

    Returns:
        The parsed value or None for empty/None values with optional fields
    """
    value = form_data.get(field_name)

    # Check if the field is Optional[Literal[...]]
    if _is_optional_type(field_info.annotation):
        # If the submitted value is the empty string OR the display text for None, treat it as None
        if value == "" or value == "-- None --":
            return None

    # Return the actual submitted value (string) for Pydantic validation
    return value


def _parse_enum_field(field_name: str, form_data: Dict[str, Any], field_info) -> Any:
    """
    Parse an Enum field, converting empty string OR '-- None --' to None for optional fields.

    Args:
        field_name: Name of the field to parse
        form_data: Dictionary containing form field data
        field_info: FieldInfo object to check for optionality

    Returns:
        The parsed value or None for empty/None values with optional fields
    """
    value = form_data.get(field_name)

    # Check if the field is Optional[Enum]
    if _is_optional_type(field_info.annotation):
        # If the submitted value is the empty string OR the display text for None, treat it as None
        if value == "" or value == "-- None --":
            return None

    enum_cls = _get_underlying_type_if_optional(field_info.annotation)
    if isinstance(enum_cls, type) and issubclass(enum_cls, Enum) and value is not None:
        try:
            first = next(iter(enum_cls))
            # Handle integer enums - convert string to int
            if isinstance(first.value, int):
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    # leave it as-is; pydantic will raise if really invalid
                    pass
            # Handle string enums - keep the value as-is, let Pydantic handle validation
            elif isinstance(first.value, str):
                # Keep the submitted value unchanged for string enums
                pass
        except StopIteration:
            # Empty enum, leave value as-is
            pass

    # Return the actual submitted value for Pydantic validation
    return value


def _parse_simple_field(
    field_name: str, form_data: Dict[str, Any], field_info=None
) -> Any:
    """
    Parse a simple field (string, number, etc.) from form data.

    Args:
        field_name: Name of the field to parse
        form_data: Dictionary containing form field data
        field_info: Optional FieldInfo object to check for optionality

    Returns:
        Value of the field or None if not found
    """
    if field_name in form_data:
        value = form_data[field_name]

        # Handle empty strings for optional fields
        if value == "" and field_info and _is_optional_type(field_info.annotation):
            return None

        return value

    # If field is optional and not in form_data, return None
    if field_info and _is_optional_type(field_info.annotation):
        return None

    return None


def _parse_nested_model_field(
    field_name: str,
    form_data: Dict[str, Any],
    nested_model_class,
    field_info,
    parent_prefix: str = "",
    exclude_fields: Optional[List[str]] = None,
    keep_skip_json_pathset: Optional[set[str]] = None,
    current_field_path: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Parse a nested Pydantic model field from form data.

    Args:
        field_name: Name of the field to parse
        form_data: Dictionary containing form field data
        nested_model_class: The nested model class
        field_info: The field info from the parent model
        parent_prefix: Prefix from parent form/model to use when constructing keys
        exclude_fields: Optional list of field names to exclude from parsing
        keep_skip_json_pathset: Optional set of normalized paths for SkipJsonSchema fields to keep

    Returns:
        Dictionary with nested model structure or None/default if no data found
    """
    # Construct the full prefix for this nested model's fields
    current_prefix = f"{parent_prefix}{field_name}_"
    nested_data: Dict[str, Optional[Any]] = {}
    found_any_subfield = False

    # Check if any keys match this prefix
    for key in form_data:
        if key.startswith(current_prefix):
            found_any_subfield = True
            break

    if found_any_subfield:
        # Helper function to check if a SkipJsonSchema field should be kept
        def _should_keep_skip_field_nested(path_segments: List[str]) -> bool:
            from fh_pydantic_form.type_helpers import normalize_path_segments

            normalized = normalize_path_segments(path_segments)
            return bool(normalized) and normalized in (keep_skip_json_pathset or set())

        # Use the passed field path for calculating nested paths
        nested_path_segments: List[str] = current_field_path or []

        # ------------------------------------------------------------------
        # 1. Process each **non-list** field in the nested model
        # ------------------------------------------------------------------
        for sub_field_name, sub_field_info in nested_model_class.model_fields.items():
            sub_key = f"{current_prefix}{sub_field_name}"
            annotation = getattr(sub_field_info, "annotation", None)

            # Skip SkipJsonSchema fields unless they're explicitly kept
            if _is_skip_json_schema_field(sub_field_info):
                sub_field_path_segments = nested_path_segments + [sub_field_name]
                if not _should_keep_skip_field_nested(sub_field_path_segments):
                    logger.debug(
                        f"Skipping SkipJsonSchema field in nested model during parsing: {sub_field_name}"
                    )
                    continue

            # Handle based on field type, with Optional unwrapping
            is_optional = _is_optional_type(annotation)
            base_type = _get_underlying_type_if_optional(annotation)

            # Handle boolean fields (including Optional[bool])
            if annotation is bool or (is_optional and base_type is bool):
                nested_data[sub_field_name] = _parse_boolean_field(sub_key, form_data)

            # Handle nested model fields (including Optional[NestedModel])
            elif isinstance(base_type, type) and hasattr(base_type, "model_fields"):
                # Pass the current_prefix and keep paths to the recursive call
                sub_field_path = nested_path_segments + [sub_field_name]
                sub_value = _parse_nested_model_field(
                    sub_field_name,
                    form_data,
                    base_type,
                    sub_field_info,
                    current_prefix,
                    exclude_fields,
                    keep_skip_json_pathset,
                    sub_field_path,
                )
                if sub_value is not None:
                    nested_data[sub_field_name] = sub_value
                elif is_optional:
                    nested_data[sub_field_name] = None

            # Handle simple fields, including empty string to None conversion for Optional fields
            elif sub_key in form_data:
                value = form_data[sub_key]
                if value == "" and is_optional:
                    nested_data[sub_field_name] = None
                else:
                    nested_data[sub_field_name] = value

            # Handle missing optional fields
            elif is_optional:
                nested_data[sub_field_name] = None

        # ------------------------------------------------------------------
        # 2. Handle **list fields** inside this nested model (e.g. Address.tags)
        #    Re-use the generic helpers so behaviour matches top-level lists.
        # ------------------------------------------------------------------
        nested_list_defs = _identify_list_fields(nested_model_class)
        if nested_list_defs:
            list_results = _parse_list_fields(
                form_data,
                nested_list_defs,
                current_prefix,  # ← prefix for this nested model
                exclude_fields,  # Pass through exclude_fields
                keep_skip_json_pathset,
            )
            # Merge without clobbering keys already set in step 1
            for lf_name, lf_val in list_results.items():
                if lf_name not in nested_data:
                    nested_data[lf_name] = lf_val

        return nested_data

    # No data found for this nested model
    logger.debug(
        f"No form data found for nested model field: {field_name} with prefix: {current_prefix}"
    )

    is_field_optional = _is_optional_type(field_info.annotation)

    # If the field is optional, return None
    if is_field_optional:
        logger.debug(
            f"Nested field {field_name} is optional and no data found, returning None."
        )
        return None

    # If not optional, try to use default or default_factory
    default_value = None
    default_applied = False

    # Import PydanticUndefined to check for it specifically
    try:
        from pydantic_core import PydanticUndefined
    except ImportError:
        # Fallback for older pydantic versions
        from pydantic.fields import PydanticUndefined

    if (
        hasattr(field_info, "default")
        and field_info.default is not None
        and field_info.default is not PydanticUndefined
    ):
        default_value = field_info.default
        default_applied = True
    elif (
        hasattr(field_info, "default_factory")
        and field_info.default_factory is not None
        and field_info.default_factory is not PydanticUndefined
    ):
        try:
            default_value = field_info.default_factory()
            default_applied = True
        except Exception as e:
            logger.warning(
                f"Error creating default for {field_name} using default_factory: {e}"
            )

    if default_applied:
        if default_value is not None and hasattr(default_value, "model_dump"):
            return default_value.model_dump()
        elif isinstance(default_value, dict):
            return default_value
        else:
            # Handle cases where default might not be a model/dict (unlikely for nested model)
            logger.warning(
                f"Default value for nested field {field_name} is not a model or dict: {type(default_value)}"
            )
            # Don't return PydanticUndefined or other non-dict values directly
            # Fall through to empty dict return instead

    # If not optional, no data found, and no default applicable, always return an empty dict
    # This ensures the test_parse_nested_model_field passes and allows Pydantic to validate
    # if the nested model can be created from empty data
    logger.debug(
        f"Nested field {field_name} is required, no data/default found, returning empty dict {{}}."
    )
    return {}


def _parse_list_fields(
    form_data: Dict[str, Any],
    list_field_defs: Dict[str, Dict[str, Any]],
    base_prefix: str = "",
    exclude_fields: Optional[List[str]] = None,
    keep_skip_json_pathset: Optional[set[str]] = None,
) -> Dict[str, Optional[List[Any]]]:
    """
    Parse list fields from form data by analyzing keys and reconstructing ordered lists.

    Args:
        form_data: Dictionary containing form field data
        list_field_defs: Dictionary of list field definitions
        base_prefix: Prefix to use when looking up field names in form_data
        exclude_fields: Optional list of field names to exclude from parsing
        keep_skip_json_pathset: Optional set of normalized paths for SkipJsonSchema fields to keep

    Returns:
        Dictionary with parsed list fields
    """
    exclude_fields = exclude_fields or []

    # Skip if no list fields defined
    if not list_field_defs:
        return {}

    # Temporary storage: { list_field_name: { idx_str: item_data } }
    list_items_temp: Dict[str, Dict[str, Union[Dict[str, Any], Any]]] = {
        field_name: {} for field_name in list_field_defs
    }

    # Order tracking: { list_field_name: [idx_str1, idx_str2, ...] }
    list_item_indices_ordered: Dict[str, List[str]] = {
        field_name: [] for field_name in list_field_defs
    }

    # Process all form keys that might belong to list fields
    for key, value in form_data.items():
        parse_result = _parse_list_item_key(key, list_field_defs, base_prefix)
        if not parse_result:
            continue  # Key doesn't belong to a known list field

        field_name, idx_str, subfield, is_simple_list = parse_result

        # Track order if seeing this index for the first time for this field
        if idx_str not in list_items_temp[field_name]:
            list_item_indices_ordered[field_name].append(idx_str)
            # Initialize storage for this item index
            list_items_temp[field_name][idx_str] = {} if not is_simple_list else None

        # Store the value
        if is_simple_list:
            list_items_temp[field_name][idx_str] = value
        else:
            # It's a model list item, store subfield value
            if subfield:  # Should always have a subfield for model list items
                list_items_temp[field_name][idx_str][subfield] = value

    # Build final lists based on tracked order
    final_lists: Dict[str, Optional[List[Any]]] = {}
    for field_name, ordered_indices in list_item_indices_ordered.items():
        field_def = list_field_defs[field_name]
        item_type = field_def["item_type"]

        items = []
        for idx_str in ordered_indices:
            # ------------------------------------------------------------------
            # If this list stores *BaseModel* items, completely re-parse the item
            # so that any inner lists (e.g. tags inside Address) become real lists
            # instead of a bunch of 'tags_0', 'tags_new_xxx' flat entries.
            # ------------------------------------------------------------------
            if field_def["is_model_type"]:
                item_prefix = f"{base_prefix}{field_name}_{idx_str}_"
                # For list items, the field path is the list field name (without index)
                item_field_path = [field_name]
                parsed_item = _parse_model_list_item(
                    form_data,
                    item_type,
                    item_prefix,
                    keep_skip_json_pathset,
                    item_field_path,
                )
                items.append(parsed_item)
                continue

            # ───────── simple (non-model) items – keep existing logic ──────────
            item_data = list_items_temp[field_name][idx_str]

            # Convert string to int for integer-valued enums in simple lists
            if (
                isinstance(item_type, type)
                and issubclass(item_type, Enum)
                and isinstance(item_data, str)
            ):
                try:
                    first = next(iter(item_type))
                    if isinstance(first.value, int):
                        try:
                            item_data = int(item_data)
                        except (TypeError, ValueError):
                            # leave it as-is; pydantic will raise if really invalid
                            pass
                except StopIteration:
                    # Empty enum, leave item_data as-is
                    pass

            items.append(item_data)

        if items:  # Only add if items were found
            final_lists[field_name] = items

    # Ensure every rendered list field appears in final_lists
    for field_name, field_def in list_field_defs.items():
        # Skip list fields the UI never showed (those in exclude_fields)
        if field_name in exclude_fields:
            continue

        # When user supplied ≥1 item we already captured it
        if field_name in final_lists:
            continue

        # User submitted form with zero items → honour intent with None for Optional[List]
        field_info = field_def["field_info"]
        if _is_optional_type(field_info.annotation):
            final_lists[field_name] = None  # Use None for empty Optional[List]
        else:
            final_lists[field_name] = []  # Regular empty list for required fields

    return final_lists


def _parse_model_list_item(
    form_data: Dict[str, Any],
    item_type,
    item_prefix: str,
    keep_skip_json_pathset: Optional[set[str]] = None,
    current_field_path: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Fully parse a single BaseModel list item – including its own nested lists.

    Re-uses the existing non-list and list helpers so we don't duplicate logic.

    Args:
        form_data: Dictionary containing form field data
        item_type: The BaseModel class for this list item
        item_prefix: Prefix for this specific list item (e.g., "main_form_compact_other_addresses_0_")
        keep_skip_json_pathset: Optional set of normalized paths for SkipJsonSchema fields to keep

    Returns:
        Dictionary with fully parsed item data including nested lists
    """
    nested_list_defs = _identify_list_fields(item_type)
    # 1. Parse scalars & nested models
    result = _parse_non_list_fields(
        form_data,
        item_type,
        nested_list_defs,
        base_prefix=item_prefix,
        exclude_fields=[],
        keep_skip_json_pathset=keep_skip_json_pathset,
        current_field_path=current_field_path,
    )
    # 2. Parse inner lists
    result.update(
        _parse_list_fields(
            form_data,
            nested_list_defs,
            base_prefix=item_prefix,
            exclude_fields=[],
            keep_skip_json_pathset=keep_skip_json_pathset,
        )
    )
    return result


def _parse_list_item_key(
    key: str, list_field_defs: Dict[str, Dict[str, Any]], base_prefix: str = ""
) -> Optional[Tuple[str, str, Optional[str], bool]]:
    """
    Parse a form key that might represent a list item.

    Args:
        key: Form field key to parse
        list_field_defs: Dictionary of list field definitions
        base_prefix: Prefix to use when looking up field names in form_data

    Returns:
        Tuple of (field_name, idx_str, subfield, is_simple_list) if key is for a list item,
        None otherwise
    """
    # Check if key starts with any of our list field names with underscore
    for field_name, field_def in list_field_defs.items():
        full_prefix = f"{base_prefix}{field_name}_"
        if key.startswith(full_prefix):
            remaining = key[len(full_prefix) :]
            is_model_type = field_def["is_model_type"]

            # Handle key format based on whether it's a model list or simple list
            if is_model_type:
                # Complex model field: field_name_idx_subfield
                try:
                    if "_" not in remaining:
                        # Invalid format for model list item
                        continue

                    # Special handling for "new_" prefix
                    if remaining.startswith("new_"):
                        # Format is "new_timestamp_subfield"
                        parts = remaining.split("_")
                        if len(parts) >= 3:  # "new", "timestamp", "subfield"
                            idx_str = f"{parts[0]}_{parts[1]}"  # "new_timestamp"
                            subfield = "_".join(
                                parts[2:]
                            )  # "subfield" (or "subfield_with_underscores")

                            # Validate timestamp part is numeric
                            timestamp_part = parts[1]
                            if not timestamp_part.isdigit():
                                continue

                            return (
                                field_name,
                                idx_str,
                                subfield,
                                False,
                            )  # Not a simple list
                        else:
                            continue
                    else:
                        # Regular numeric index format: "123_subfield"
                        idx_part, subfield = remaining.split("_", 1)

                        # Validate index is numeric
                        if not idx_part.isdigit():
                            continue

                        return (
                            field_name,
                            idx_part,
                            subfield,
                            False,
                        )  # Not a simple list

                except Exception:
                    continue
            else:
                # Simple list: field_name_idx
                try:
                    # For simple types, the entire remaining part is the index
                    idx_str = remaining

                    # Validate index format - either numeric or "new_timestamp"
                    if idx_str.isdigit():
                        # Regular numeric index
                        pass
                    elif idx_str.startswith("new_"):
                        # New item with timestamp - validate timestamp part is numeric
                        timestamp_part = idx_str[4:]  # Skip "new_" prefix
                        if not timestamp_part.isdigit():
                            continue
                    else:
                        continue

                    return field_name, idx_str, None, True  # Simple list

                except Exception:
                    continue

    # Not a list field key
    return None
