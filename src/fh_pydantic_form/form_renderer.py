import logging
import time as pytime
from typing import (
    Any,
    Dict,
    Generic,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel

from fh_pydantic_form.constants import _UNSET
from fh_pydantic_form.defaults import default_dict_for_model, default_for_annotation
from fh_pydantic_form.field_renderers import (
    BaseFieldRenderer,
    ListFieldRenderer,
    StringFieldRenderer,
)
from fh_pydantic_form.form_parser import (
    _identify_list_fields,
    _parse_list_fields,
    _parse_non_list_fields,
)
from fh_pydantic_form.list_path import walk_path
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    _is_skip_json_schema_field,
    get_default,
    normalize_path_segments,
)
from fh_pydantic_form.ui_style import (
    SpacingTheme,
    SpacingValue,
    _normalize_spacing,
    spacing,
)

logger = logging.getLogger(__name__)

# TypeVar for generic model typing
ModelType = TypeVar("ModelType", bound=BaseModel)


def _compile_keep_paths(paths: Optional[List[str]]) -> set[str]:
    """Normalize and compile keep paths for fast membership tests."""
    if not paths:
        return set()

    compiled: set[str] = set()
    for raw_path in paths:
        if not raw_path:
            continue
        normalized = raw_path.strip()
        if normalized:
            compiled.add(normalized)
    return compiled


def list_manipulation_js():
    return fh.Script("""  
function moveItem(buttonElement, direction) {
    // Find the accordion item (list item)
    const item = buttonElement.closest('li');
    if (!item) return;

    const container = item.parentElement;
    if (!container) return;

    // Find the sibling in the direction we want to move
    const sibling = direction === 'up' ? item.previousElementSibling : item.nextElementSibling;
    
    if (sibling) {
        if (direction === 'up') {
            container.insertBefore(item, sibling);
        } else {
            // Insert item after the next sibling
            container.insertBefore(item, sibling.nextElementSibling);
        }
        // Update button states after move
        updateMoveButtons(container);
    }
}

function moveItemUp(buttonElement) {
    moveItem(buttonElement, 'up');
}

function moveItemDown(buttonElement) {
    moveItem(buttonElement, 'down');
}

// Function to update button states (disable if at top/bottom)
function updateMoveButtons(container) {
    const items = container.querySelectorAll(':scope > li');
    items.forEach((item, index) => {
        const upButton = item.querySelector('button[onclick^="moveItemUp"]');
        const downButton = item.querySelector('button[onclick^="moveItemDown"]');
        
        if (upButton) upButton.disabled = (index === 0);
        if (downButton) downButton.disabled = (index === items.length - 1);
    });
}

// Function to toggle all list items open or closed
function toggleListItems(containerId) {
    const containerElement = document.getElementById(containerId);
    if (!containerElement) {
        console.warn('Accordion container not found:', containerId);
        return;
    }

    // Find all direct li children (the accordion items)
    const items = Array.from(containerElement.children).filter(el => el.tagName === 'LI');
    if (!items.length) {
        return; // No items to toggle
    }

    // Determine if we should open all (if any are closed) or close all (if all are open)
    const shouldOpen = items.some(item => !item.classList.contains('uk-open'));

    // Toggle each item accordingly
    items.forEach(item => {
        if (shouldOpen) {
            // Open the item if it's not already open
            if (!item.classList.contains('uk-open')) {
                item.classList.add('uk-open');
                // Make sure the content is expanded
                const content = item.querySelector('.uk-accordion-content');
                if (content) {
                    content.style.height = 'auto';
                    content.hidden = false;
                }
            }
        } else {
            // Close the item
            item.classList.remove('uk-open');
            // Hide the content
            const content = item.querySelector('.uk-accordion-content');
            if (content) {
                content.hidden = true;
            }
        }
    });

    // Attempt to use UIkit's API if available (more reliable)
    if (window.UIkit && UIkit.accordion) {
        try {
            const accordion = UIkit.accordion(containerElement);
            if (accordion) {
                // In UIkit, indices typically start at 0
                items.forEach((item, index) => {
                    const isOpen = item.classList.contains('uk-open');
                    if (shouldOpen && !isOpen) {
                        accordion.toggle(index, false); // Open item without animation
                    } else if (!shouldOpen && isOpen) {
                        accordion.toggle(index, false); // Close item without animation
                    }
                });
            }
        } catch (e) {
            console.warn('UIkit accordion API failed, falling back to manual toggle', e);
            // The manual toggle above should have handled it
        }
    }
}

// Simple accordion state preservation using item IDs
window.saveAccordionState = function(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const openItemIds = [];
    container.querySelectorAll('li.uk-open').forEach(item => {
        if (item.id) {
            openItemIds.push(item.id);
        }
    });
    
    // Store in sessionStorage with container-specific key
    sessionStorage.setItem(`accordion_state_${containerId}`, JSON.stringify(openItemIds));
};

window.restoreAccordionState = function(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const savedState = sessionStorage.getItem(`accordion_state_${containerId}`);
    if (!savedState) return;
    
    try {
        const openItemIds = JSON.parse(savedState);
        
        // Restore open state for each saved item by ID
        openItemIds.forEach(itemId => {
            const item = document.getElementById(itemId);
            if (item && container.contains(item)) {
                item.classList.add('uk-open');
                const content = item.querySelector('.uk-accordion-content');
                if (content) {
                    content.hidden = false;
                    content.style.height = 'auto';
                }
            }
        });
    } catch (e) {
        console.warn('Failed to restore accordion state:', e);
    }
};

// Save all accordion states in the form (both lists and nested BaseModels)
window.saveAllAccordionStates = function() {
    // Save list container states
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        window.saveAccordionState(container.id);
    });

    // Save all UIkit accordion item states (nested BaseModels, etc.)
    document.querySelectorAll('.uk-accordion > li').forEach(item => {
        if (item.id) {
            const isOpen = item.classList.contains('uk-open');
            sessionStorage.setItem('accordion_state_' + item.id, isOpen ? 'open' : 'closed');
        }
    });
};

// Restore all accordion states in the form (both lists and nested BaseModels)
window.restoreAllAccordionStates = function() {
    // Restore list container states
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        window.restoreAccordionState(container.id);
    });

    // Use requestAnimationFrame to ensure DOM has fully updated after swap
    requestAnimationFrame(() => {
        setTimeout(() => {
            // Restore ALL UIkit accordion item states in the entire document (not just swapped area)
            document.querySelectorAll('.uk-accordion > li').forEach(item => {
                if (item.id) {
                    const savedState = sessionStorage.getItem('accordion_state_' + item.id);

                    if (savedState === 'open' && !item.classList.contains('uk-open')) {
                        item.classList.add('uk-open');
                    } else if (savedState === 'closed' && item.classList.contains('uk-open')) {
                        item.classList.remove('uk-open');
                    }
                }
            });
        }, 150);
    });
};

// Wait for the DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', () => {
    // Initialize button states for elements present on initial load
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        updateMoveButtons(container);
    });

    // Attach HTMX event listener to document.body for list operations
    document.body.addEventListener('htmx:afterSwap', function(event) {
        // Check if this is an insert (afterend swap)
        const targetElement = event.detail.target;
        const requestElement = event.detail.requestConfig?.elt;
        const swapStrategy = requestElement ? requestElement.getAttribute('hx-swap') : null;
        
        if (swapStrategy === 'afterend') {
            // For insertions, get the parent container of the original target
            const listContainer = targetElement.closest('[id$="_items_container"]');
            if (listContainer) {
                updateMoveButtons(listContainer);
            }
        } else {
            // Original logic for other swap types
            const containers = event.detail.target.querySelectorAll('[id$="_items_container"]');
            containers.forEach(container => {
                updateMoveButtons(container);
            });
            
            // If the target itself is a container
            if (event.detail.target.id && event.detail.target.id.endsWith('_items_container')) {
                updateMoveButtons(event.detail.target);
            }
        }
    }); 
});
""")


class PydanticForm(Generic[ModelType]):
    """
    Renders a form from a Pydantic model class with robust schema drift handling

    Accepts initial values as either BaseModel instances or dictionaries.
    Gracefully handles missing fields and schema mismatches by rendering
    available fields and skipping problematic ones.

    This class handles:
    - Finding appropriate renderers for each field
    - Managing field prefixes for proper form submission
    - Creating the overall form structure
    - Registering HTMX routes for list manipulation
    - Parsing form data back to Pydantic model format
    - Handling refresh and reset requests
    - providing refresh and reset buttons
    - validating request data against the model
    """

    # --- module-level flag (add near top of file) ---

    def __init__(
        self,
        form_name: str,
        model_class: Type[ModelType],
        initial_values: Optional[Union[ModelType, Dict[str, Any]]] = None,
        custom_renderers: Optional[List[Tuple[Type, Type[BaseFieldRenderer]]]] = None,
        disabled: bool = False,
        disabled_fields: Optional[List[str]] = None,
        label_colors: Optional[Dict[str, str]] = None,
        exclude_fields: Optional[List[str]] = None,
        keep_skip_json_fields: Optional[List[str]] = None,
        spacing: SpacingValue = SpacingTheme.NORMAL,
        metrics_dict: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the form renderer

        Args:
            form_name: Unique name for this form
            model_class: The Pydantic model class to render
            initial_values: Initial values as BaseModel instance or dict.
                           Missing fields will not be auto-filled with defaults.
                           Supports robust handling of schema drift.
            custom_renderers: Optional list of tuples (field_type, renderer_cls) to register
            disabled: Whether all form inputs should be disabled
            disabled_fields: Optional list of top-level field names to disable specifically
            label_colors: Optional dictionary mapping field names to label colors (CSS color values)
            exclude_fields: Optional list of top-level field names to exclude from the form
            keep_skip_json_fields: Optional list of dot-paths for SkipJsonSchema fields to force-keep
            spacing: Spacing theme to use for form layout ("normal", "compact", or SpacingTheme enum)
            metrics_dict: Optional metrics dictionary for field-level visual feedback
        """
        self.name = form_name
        self.model_class = model_class

        self.initial_values_dict: Dict[str, Any] = {}

        # Store initial values as dict for robustness to schema drift
        if initial_values is None:
            self.initial_values_dict = {}
        elif isinstance(initial_values, dict):
            self.initial_values_dict = initial_values.copy()
        elif hasattr(initial_values, "model_dump"):
            self.initial_values_dict = initial_values.model_dump()
        else:
            # Fallback - attempt dict conversion
            try:
                temp_dict = dict(initial_values)
                model_field_names = set(self.model_class.model_fields.keys())
                # Only accept if all keys are in the model's field names
                if not isinstance(temp_dict, dict) or not set(
                    temp_dict.keys()
                ).issubset(model_field_names):
                    raise ValueError("Converted to dict with keys not in model fields")
                self.initial_values_dict = temp_dict
            except (TypeError, ValueError):
                logger.warning(
                    "Could not convert initial_values to dict, using empty dict"
                )
                self.initial_values_dict = {}

        # Use copy for rendering to avoid mutations
        self.values_dict: Dict[str, Any] = self.initial_values_dict.copy()

        self.base_prefix = f"{form_name}_"
        self.disabled = disabled
        self.disabled_fields = (
            disabled_fields or []
        )  # Store as list for easier checking
        self.label_colors = label_colors or {}  # Store label colors mapping
        self.exclude_fields = exclude_fields or []  # Store excluded fields list
        self.spacing = _normalize_spacing(spacing)  # Store normalized spacing
        self.metrics_dict = metrics_dict or {}  # Store metrics dictionary
        self.keep_skip_json_fields = keep_skip_json_fields or []
        self._keep_skip_json_pathset = _compile_keep_paths(self.keep_skip_json_fields)

        # Register custom renderers with the global registry if provided
        if custom_renderers:
            registry = FieldRendererRegistry()  # Get singleton instance
            for field_type, renderer_cls in custom_renderers:
                registry.register_type_renderer(field_type, renderer_cls)

    @property
    def form_name(self) -> str:
        """
        LLMs like to hallucinate this property, so might as well make it real.
        """
        return self.name

    def _compact_wrapper(self, inner: FT) -> FT:
        """
        Wrap inner markup in a wrapper div.
        """
        wrapper_cls = "fhpf-wrapper w-full flex-1"
        return fh.Div(inner, cls=wrapper_cls)

    def _normalized_dot_path(self, path_segments: List[str]) -> str:
        """Normalize path segments by dropping indices and joining with dots."""
        return normalize_path_segments(path_segments)

    def _is_kept_skip_field(self, full_path: List[str]) -> bool:
        """Return True if a SkipJsonSchema field should be kept based on keep list."""
        normalized = self._normalized_dot_path(full_path)
        return bool(normalized) and normalized in self._keep_skip_json_pathset

    def reset_state(self) -> None:
        """
        Restore the live state of the form to its immutable baseline.
        Call this *before* rendering if you truly want a factory-fresh view.
        """
        self.values_dict = self.initial_values_dict.copy()

    def with_initial_values(
        self,
        initial_values: Optional[Union[ModelType, Dict[str, Any]]] = None,
        metrics_dict: Optional[Dict[str, Any]] = None,
    ) -> "PydanticForm":
        """
        Create a new PydanticForm instance with the same configuration but different initial values.

        This preserves all constructor arguments (label_colors, custom_renderers, spacing, etc.)
        while allowing you to specify new initial values. This is useful for reusing form
        configurations with different data.

        Args:
            initial_values: New initial values as BaseModel instance or dict.
                           Same format as the constructor accepts.
            metrics_dict: Optional metrics dictionary for field-level visual feedback

        Returns:
            A new PydanticForm instance with identical configuration but updated initial values
        """
        # Create the new instance with the same configuration
        clone = PydanticForm(
            form_name=self.name,
            model_class=self.model_class,
            initial_values=initial_values,  # Pass through to constructor for proper handling
            custom_renderers=None,  # Registry is global, no need to re-register
            disabled=self.disabled,
            disabled_fields=self.disabled_fields,
            label_colors=self.label_colors,
            exclude_fields=self.exclude_fields,
            keep_skip_json_fields=self.keep_skip_json_fields,
            spacing=self.spacing,
            metrics_dict=metrics_dict
            if metrics_dict is not None
            else self.metrics_dict,
        )

        return clone

    def render_inputs(self) -> FT:
        """
        Render just the form inputs based on the model class (no form tag)

        Returns:
            A component containing the rendered form input fields
        """
        form_inputs = []
        registry = FieldRendererRegistry()  # Get singleton instance

        for field_name, field_info in self.model_class.model_fields.items():
            # Skip excluded fields
            if field_name in self.exclude_fields:
                continue

            # Skip SkipJsonSchema fields unless explicitly kept
            if _is_skip_json_schema_field(field_info) and not self._is_kept_skip_field(
                [field_name]
            ):
                continue

            # Only use what was explicitly provided in initial values
            initial_value = (
                self.values_dict.get(field_name) if self.values_dict else None
            )

            # Only use model defaults if field was not provided at all
            # (not if it was provided as None/empty)
            field_was_provided = (
                field_name in self.values_dict if self.values_dict else False
            )

            # Only use defaults if field was not provided at all
            if not field_was_provided:
                # Field not provided - use model defaults in order of priority
                # 1. Try explicit field default
                default_val = get_default(field_info)
                if default_val is not _UNSET:
                    initial_value = default_val
                else:
                    # 2. Fall back to smart defaults for the type
                    initial_value = default_for_annotation(field_info.annotation)
            # If field was provided (even as None), respect that value

            # Get renderer from global registry
            renderer_cls = registry.get_renderer(field_name, field_info)

            if not renderer_cls:
                # Fall back to StringFieldRenderer if no renderer found
                renderer_cls = StringFieldRenderer
                logger.warning(
                    f"  - No renderer found for '{field_name}', falling back to StringFieldRenderer"
                )

            # Determine if this specific field should be disabled
            is_field_disabled = self.disabled or (field_name in self.disabled_fields)

            # Get label color for this field if specified
            label_color = self.label_colors.get(field_name)

            # Create and render the field
            renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=initial_value,
                prefix=self.base_prefix,
                disabled=is_field_disabled,  # Pass the calculated disabled state
                label_color=label_color,  # Pass the label color if specified
                spacing=self.spacing,  # Pass the spacing
                field_path=[field_name],  # Set top-level field path
                form_name=self.name,  # Pass form name
                metrics_dict=self.metrics_dict,  # Pass the metrics dict
                keep_skip_json_pathset=self._keep_skip_json_pathset,
            )

            rendered_field = renderer.render()
            form_inputs.append(rendered_field)

        # Create container for inputs, ensuring items stretch to full width
        inputs_container = mui.DivVStacked(
            *form_inputs,
            cls=f"{spacing('stack_gap', self.spacing)} items-stretch",
        )

        # Define the ID for the wrapper div - this is what the HTMX request targets
        form_content_wrapper_id = f"{self.name}-inputs-wrapper"

        # Create the wrapper div and apply compact styling if needed
        wrapped = self._compact_wrapper(
            fh.Div(inputs_container, id=form_content_wrapper_id)
        )

        return wrapped

    def _filter_by_prefix(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter form data to include only keys that start with this form's base_prefix.

        This prevents cross-contamination when multiple forms share the same HTML form element.

        Args:
            data: Raw form data dictionary

        Returns:
            Filtered dictionary containing only keys with matching prefix
        """
        if not self.base_prefix:
            return data  # No prefix = no filtering needed

        filtered = {
            key: value
            for key, value in data.items()
            if key.startswith(self.base_prefix)
        }

        return filtered

    # ---- Form Renderer Methods (continued) ----

    async def handle_refresh_request(self, req):
        """
        Handles the POST request for refreshing this form instance.

        Args:
            req: The request object

        Returns:
            HTML response with refreshed form inputs
        """
        form_data = await req.form()
        form_dict = dict(form_data)

        # Filter to only this form's fields
        form_dict = self._filter_by_prefix(form_dict)

        logger.info(f"Refresh request for form '{self.name}'")

        parsed_data = {}
        alert_ft = None  # Changed to hold an FT object instead of a string
        try:
            # Use the instance's parse method directly

            parsed_data = self.parse(form_dict)

        except Exception as e:
            logger.error(
                f"Error parsing form data for refresh on form '{self.name}': {e}",
                exc_info=True,
            )

            # Merge strategy - preserve existing values for unparseable fields
            # Start with current values
            parsed_data = self.values_dict.copy() if self.values_dict else {}

            # Try to extract any simple fields that don't require complex parsing
            for key, value in form_dict.items():
                if key.startswith(self.base_prefix):
                    field_name = key[len(self.base_prefix) :]
                    # Only update simple fields to avoid corruption
                    if "_" not in field_name:  # Not a nested field
                        parsed_data[field_name] = value

            alert_ft = mui.Alert(
                f"Warning: Some fields could not be refreshed. Preserved previous values. Error: {str(e)}",
                cls=mui.AlertT.warning + " mb-4",  # Add margin bottom
            )

        # Parsed successfully (or merged best effort) – make it the new truth
        self.values_dict = parsed_data.copy()

        # Create temporary renderer with same configuration but updated values
        temp_renderer = self.with_initial_values(parsed_data)

        refreshed_inputs_component = temp_renderer.render_inputs()

        if refreshed_inputs_component is None:
            logger.error("render_inputs() returned None!")
            alert_ft = mui.Alert(
                "Critical error: Form refresh failed to generate content",
                cls=mui.AlertT.error + " mb-4",
            )
            # Emergency fallback - use original renderer's inputs
            refreshed_inputs_component = self.render_inputs()

        # Return the FT components directly instead of creating a Response object
        if alert_ft:
            # Return both the alert and the form inputs as a tuple
            return (alert_ft, refreshed_inputs_component)
        else:
            # Return just the form inputs
            return refreshed_inputs_component

    async def handle_reset_request(self) -> FT:
        """
        Handles the POST request for resetting this form instance to its initial values.

        Returns:
            HTML response with reset form inputs
        """
        # Rewind internal state to the immutable baseline
        self.reset_state()

        logger.info(f"Resetting form '{self.name}' to initial values")

        # Create temporary renderer with original initial dict
        temp_renderer = self.with_initial_values(self.initial_values_dict)

        reset_inputs_component = temp_renderer.render_inputs()

        if reset_inputs_component is None:
            logger.error(f"Reset for form '{self.name}' failed to render inputs.")
            return mui.Alert("Error resetting form.", cls=mui.AlertT.error)

        logger.info(f"Reset form '{self.name}' successful")
        return reset_inputs_component

    def parse(self, form_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse form data into a structure that matches the model.

        This method processes form data that includes the form's base_prefix
        and reconstructs the structure expected by the Pydantic model.

        Args:
            form_dict: Dictionary containing form field data (name -> value)

        Returns:
            Dictionary with parsed data in a structure matching the model
        """

        list_field_defs = _identify_list_fields(self.model_class)

        # Filter out excluded fields from list field definitions
        filtered_list_field_defs = {
            field_name: field_def
            for field_name, field_def in list_field_defs.items()
            if field_name not in self.exclude_fields
        }

        # Parse non-list fields first - pass the base_prefix, exclude_fields, and keep paths
        result = _parse_non_list_fields(
            form_dict,
            self.model_class,
            list_field_defs,
            self.base_prefix,
            self.exclude_fields,
            self._keep_skip_json_pathset,
            None,  # Top-level parsing, no field path
        )

        # Parse list fields based on keys present in form_dict - pass the base_prefix and keep paths
        # Use filtered list field definitions to skip excluded list fields
        list_results = _parse_list_fields(
            form_dict,
            filtered_list_field_defs,
            self.base_prefix,
            self.exclude_fields,
            self._keep_skip_json_pathset,
        )

        # Merge list results into the main result
        result.update(list_results)

        # Inject defaults for missing fields before returning
        self._inject_missing_defaults(result)

        return result

    def _inject_missing_defaults(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure missing fields are filled following precedence:
        1) form value (already in `data`)
        2) initial_values
        3) model/default_factory
        4) sensible default (for SkipJsonSchema fields only)

        For required fields without defaults or initial_values, they are left missing
        so that Pydantic validation can properly surface the error.

        Args:
            data: Dictionary to modify in-place

        Returns:
            The same dictionary instance for method chaining
        """
        for field_name, field_info in self.model_class.model_fields.items():
            # 1) Respect any value already parsed from the form (top priority)
            if field_name in data:
                continue

            # 2) Prefer initial_values for ANY missing field (including hidden SkipJsonSchema fields)
            if field_name in self.initial_values_dict:
                initial_val = self.initial_values_dict[field_name]
                if hasattr(initial_val, "model_dump"):
                    initial_val = initial_val.model_dump()
                data[field_name] = initial_val
                continue

            # 3) Use model/default_factory if available
            default_val = get_default(field_info)
            if default_val is not _UNSET:
                # If the default is a BaseModel, convert to dict for consistency
                if hasattr(default_val, "model_dump"):
                    default_val = default_val.model_dump()
                data[field_name] = default_val
            else:
                # 4) For SkipJsonSchema fields without defaults, provide sensible defaults
                # For regular required fields, leave them missing so validation catches them
                if _is_skip_json_schema_field(field_info):
                    data[field_name] = default_for_annotation(field_info.annotation)
                # else: leave missing, let validation fail

        return data

    def register_routes(self, app):
        """
        Register HTMX routes for list manipulation and form refresh

        Args:
            rt: The route registrar function from the application
        """

        # --- Register the form-specific refresh route ---
        refresh_route_path = f"/form/{self.name}/refresh"

        @app.route(refresh_route_path, methods=["POST"])
        async def _instance_specific_refresh_handler(req):
            """Handle form refresh request for this specific form instance"""
            # Add entry point logging to confirm the route is being hit
            # Calls the instance method to handle the logic
            return await self.handle_refresh_request(req)

        # --- Register the form-specific reset route ---
        reset_route_path = f"/form/{self.name}/reset"

        @app.route(reset_route_path, methods=["POST"])
        async def _instance_specific_reset_handler(req):
            """Handle form reset request for this specific form instance"""
            # Calls the instance method to handle the logic
            return await self.handle_reset_request()

        # Try the route with a more explicit pattern
        route_pattern = f"/form/{self.name}/list/{{action}}/{{list_path:path}}"

        @app.route(route_pattern, methods=["POST", "DELETE"])
        async def list_action(req, action: str, list_path: str):
            """
            Handle list actions (add/delete) for nested lists in this specific form

            Args:
                req: The request object
                action: Either "add" or "delete"
                list_path: Path to the list field (e.g., "tags" or "main_address/tags" or "other_addresses/1/tags")

            Returns:
                A component for the new list item (add) or empty response (delete)
            """
            if action not in {"add", "delete"}:
                return fh.Response(status_code=400, content="Unknown list action")

            segments = list_path.split("/")
            try:
                list_field_info, html_parts, item_type = walk_path(
                    self.model_class, segments
                )
            except ValueError as exc:
                logger.warning("Bad list path %s – %s", list_path, exc)
                return mui.Alert(str(exc), cls=mui.AlertT.error)

            if req.method == "DELETE":
                return fh.Response(status_code=200, content="")

            # === add (POST) ===
            default_item = (
                default_dict_for_model(item_type)
                if hasattr(item_type, "model_fields")
                else default_for_annotation(item_type)
            )

            # Build prefix **without** the list field itself to avoid duplication
            parts_before_list = html_parts[:-1]  # drop final segment
            if parts_before_list:
                html_prefix = f"{self.base_prefix}{'_'.join(parts_before_list)}_"
            else:
                html_prefix = self.base_prefix

            # Create renderer for the list field
            renderer = ListFieldRenderer(
                field_name=segments[-1],
                field_info=list_field_info,
                value=[],
                prefix=html_prefix,
                spacing=self.spacing,
                disabled=self.disabled,
                field_path=segments,  # Pass the full path segments
                form_name=self.name,  # Pass the explicit form name
                metrics_dict=self.metrics_dict,  # Pass the metrics dict
                keep_skip_json_pathset=self._keep_skip_json_pathset,
            )

            # Generate a unique placeholder index
            placeholder_idx = f"new_{int(pytime.time() * 1000)}"

            # Render the new item card, set is_open=True to make it expanded by default
            new_card = renderer._render_item_card(
                default_item, placeholder_idx, item_type, is_open=True
            )

            return new_card

    def refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """
        Generates the HTML component for the form's refresh button.

        Args:
            text: Optional custom text for the button. Defaults to "Refresh Form Display".
            **kwargs: Additional attributes to pass to the mui.Button component.

        Returns:
            A FastHTML component (mui.Button) representing the refresh button.
        """
        # Use provided text or default
        button_text = text if text is not None else " Refresh Form Display"

        # Define the target wrapper ID
        form_content_wrapper_id = f"{self.name}-inputs-wrapper"

        # Define the target URL
        refresh_url = f"/form/{self.name}/refresh"

        # Base button attributes
        button_attrs = {
            "type": "button",  # Prevent form submission
            "hx_post": refresh_url,  # Target the instance-specific route
            "hx_target": f"#{form_content_wrapper_id}",  # Target the wrapper Div ID
            "hx_swap": "innerHTML",
            "hx_trigger": "click",  # Explicit trigger on click
            "hx_include": "closest form",  # Include all form fields from the enclosing form
            "hx_preserve": "scroll",
            "uk_tooltip": "Update the form display based on current values (e.g., list item titles)",
            "cls": mui.ButtonT.secondary,
            **{
                "hx-on::before-request": "window.saveAllAccordionStates && window.saveAllAccordionStates()"
            },
            **{
                "hx-on::after-swap": "window.restoreAllAccordionStates && window.restoreAllAccordionStates()"
            },
        }

        # Update with any additional attributes
        button_attrs.update(kwargs)

        # Create and return the button
        return mui.Button(mui.UkIcon("refresh-ccw"), button_text, **button_attrs)

    def reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """
        Generates the HTML component for the form's reset button.

        Args:
            text: Optional custom text for the button. Defaults to "Reset to Initial".
            **kwargs: Additional attributes to pass to the mui.Button component.

        Returns:
            A FastHTML component (mui.Button) representing the reset button.
        """
        # Use provided text or default
        button_text = text if text is not None else " Reset to Initial"

        # Define the target wrapper ID
        form_content_wrapper_id = f"{self.name}-inputs-wrapper"

        # Define the target URL
        reset_url = f"/form/{self.name}/reset"

        # Base button attributes
        button_attrs = {
            "type": "button",  # Prevent form submission
            "hx_post": reset_url,  # Target the instance-specific route
            "hx_target": f"#{form_content_wrapper_id}",  # Target the wrapper Div ID
            "hx_swap": "innerHTML",
            "hx_confirm": "Are you sure you want to reset the form to its initial values? Any unsaved changes will be lost.",
            "hx_preserve": "scroll",
            "uk_tooltip": "Reset the form fields to their original values",
            "cls": mui.ButtonT.destructive,  # Use danger style to indicate destructive action
        }

        # Update with any additional attributes
        button_attrs.update(kwargs)

        # Create and return the button
        return mui.Button(
            mui.UkIcon("history"),  # Icon representing reset/history
            button_text,
            **button_attrs,
        )

    async def model_validate_request(self, req: Any) -> ModelType:
        """
        Extracts form data from a request, parses it, and validates against the model.

        This method encapsulates the common pattern of:
        1. Extracting form data from a request
        2. Converting it to a dictionary
        3. Parsing with the renderer's logic (handling prefixes, etc.)
        4. Validating against the Pydantic model

        Args:
            req: The request object (must have an awaitable .form() method)

        Returns:
            A validated instance of the model class

        Raises:
            ValidationError: If validation fails based on the model's rules
        """
        form_data = await req.form()
        form_dict = dict(form_data)

        # Parse the form data using the renderer's logic
        parsed_data = self.parse(form_dict)

        # Validate against the model - allow ValidationError to propagate
        validated_model = self.model_class.model_validate(parsed_data)
        logger.info(f"Request validation successful for form '{self.name}'")

        return validated_model

    def form_id(self) -> str:
        """
        Get the standard form ID for this renderer.

        Returns:
            The form ID string that should be used for the HTML form element
        """
        return f"{self.name}-form"
