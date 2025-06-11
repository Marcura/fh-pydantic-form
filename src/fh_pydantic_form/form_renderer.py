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
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import _UNSET, get_default
from fh_pydantic_form.ui_style import (
    SpacingTheme,
    SpacingValue,
    _normalize_spacing,
    spacing,
)

logger = logging.getLogger(__name__)

# TypeVar for generic model typing
ModelType = TypeVar("ModelType", bound=BaseModel)


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

// Wait for the DOM to be fully loaded before initializing
document.addEventListener('DOMContentLoaded', () => {
    // Initialize button states for elements present on initial load
    document.querySelectorAll('[id$="_items_container"]').forEach(container => {
        updateMoveButtons(container);
    });
    
    // Now it's safe to attach the HTMX event listener to document.body
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

    def _compact_wrapper(self, inner: FT) -> FT:
        """
        Wrap inner markup with a '.compact-form' div and inject one <style>
        block when compact theme is used.
        """
        if self.spacing == SpacingTheme.COMPACT:
            from fh_pydantic_form.ui_style import COMPACT_EXTRA_CSS

            return fh.Div(COMPACT_EXTRA_CSS, inner, cls="compact-form")
        else:
            return inner

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
        spacing: SpacingValue = SpacingTheme.NORMAL,
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
            spacing: Spacing theme to use for form layout ("normal", "compact", or SpacingTheme enum)
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

        # Register custom renderers with the global registry if provided
        if custom_renderers:
            registry = FieldRendererRegistry()  # Get singleton instance
            for field_type, renderer_cls in custom_renderers:
                registry.register_type_renderer(field_type, renderer_cls)

    def render_inputs(self) -> FT:
        """
        Render just the form inputs based on the model class (no form tag)

        Returns:
            A component containing the rendered form input fields
        """
        form_inputs = []
        registry = FieldRendererRegistry()  # Get singleton instance
        logger.debug(
            f"Starting render_inputs for form '{self.name}' with {len(self.model_class.model_fields)} fields"
        )

        for field_name, field_info in self.model_class.model_fields.items():
            # Skip excluded fields
            if field_name in self.exclude_fields:
                logger.debug(f"Skipping excluded field: {field_name}")
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

            # Log the initial value type and a summary for debugging
            if initial_value is not None:
                value_type = type(initial_value).__name__
                if isinstance(initial_value, (list, dict)):
                    value_size = f"size={len(initial_value)}"
                else:
                    value_size = ""
                logger.debug(
                    f"Field '{field_name}': {value_type} {value_size} (provided: {field_was_provided})"
                )
            else:
                logger.debug(
                    f"Field '{field_name}': None (provided: {field_was_provided})"
                )

            # Only use defaults if field was not provided at all
            if not field_was_provided:
                # Field not provided - use model defaults
                if field_info.default is not None:
                    initial_value = field_info.default
                    logger.debug(f"  - Using default value for '{field_name}'")
                elif getattr(field_info, "default_factory", None) is not None:
                    try:
                        default_factory = field_info.default_factory
                        if callable(default_factory):
                            initial_value = default_factory()
                            logger.debug(
                                f"  - Using default_factory for '{field_name}'"
                            )
                        else:
                            initial_value = None
                            logger.warning(
                                f"  - default_factory for '{field_name}' is not callable"
                            )
                    except Exception as e:
                        initial_value = None
                        logger.warning(
                            f"  - Error in default_factory for '{field_name}': {e}"
                        )
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
            logger.debug(
                f"Field '{field_name}' disabled state: {is_field_disabled} (Global: {self.disabled}, Specific: {field_name in self.disabled_fields})"
            )

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
        logger.debug(f"Creating form inputs wrapper with ID: {form_content_wrapper_id}")

        # Create the wrapper div and apply compact styling if needed
        wrapped = self._compact_wrapper(
            fh.Div(inputs_container, id=form_content_wrapper_id)
        )

        return wrapped

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
            # Fallback: Use original initial values dict if available, otherwise empty dict
            parsed_data = (
                self.initial_values_dict.copy() if self.initial_values_dict else {}
            )
            alert_ft = mui.Alert(
                f"Warning: Could not fully process current form values for refresh. Display might not be fully updated. Error: {str(e)}",
                cls=mui.AlertT.warning + " mb-4",  # Add margin bottom
            )

        # Create Temporary Renderer instance
        temp_renderer = PydanticForm(
            form_name=self.name,
            model_class=self.model_class,
            # No initial_data needed here, we set values_dict below
            spacing=self.spacing,
        )
        # Set the values based on the parsed (or fallback) data
        temp_renderer.values_dict = parsed_data

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
        logger.info(f"Resetting form '{self.name}' to initial values")

        # Create temporary renderer with original initial dict
        temp_renderer = PydanticForm(
            form_name=self.name,
            model_class=self.model_class,
            initial_values=self.initial_values_dict,  # Use dict instead of BaseModel
            custom_renderers=getattr(self, "custom_renderers", None),
            disabled=self.disabled,
            disabled_fields=self.disabled_fields,
            label_colors=self.label_colors,
            exclude_fields=self.exclude_fields,
            spacing=self.spacing,
        )

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

        # Parse non-list fields first - pass the base_prefix and exclude_fields
        result = _parse_non_list_fields(
            form_dict,
            self.model_class,
            list_field_defs,
            self.base_prefix,
            self.exclude_fields,
        )

        # Parse list fields based on keys present in form_dict - pass the base_prefix
        # Use filtered list field definitions to skip excluded list fields
        list_results = _parse_list_fields(
            form_dict, filtered_list_field_defs, self.base_prefix
        )

        # Merge list results into the main result
        result.update(list_results)

        # Inject defaults for excluded fields before returning
        self._inject_default_values_for_excluded(result)

        return result

    def _inject_default_values_for_excluded(
        self, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ensures that every field listed in self.exclude_fields is present in data
        if the model defines a default or default_factory, or if initial_values were provided.

        Priority order:
        1. initial_values (if provided during form creation)
        2. model defaults/default_factory

        Operates top-level only (exclude_fields spec is top-level names).

        Args:
            data: Dictionary to modify in-place

        Returns:
            The same dictionary instance for method chaining
        """
        for field_name in self.exclude_fields:
            # Skip if already present (e.g., user provided initial_values)
            if field_name in data:
                continue

            # First priority: check if initial_values_dict has this field
            if field_name in self.initial_values_dict:
                initial_val = self.initial_values_dict[field_name]
                # If the initial value is a BaseModel, convert to dict for consistency
                if hasattr(initial_val, "model_dump"):
                    initial_val = initial_val.model_dump()
                data[field_name] = initial_val
                logger.debug(
                    f"Injected initial value for excluded field '{field_name}'"
                )
                continue

            # Second priority: use model defaults
            field_info = self.model_class.model_fields.get(field_name)
            if field_info is None:
                logger.warning(f"exclude_fields contains unknown field '{field_name}'")
                continue

            default_val = get_default(field_info)
            if default_val is not _UNSET:
                # If the default is a BaseModel, convert to dict for consistency
                if hasattr(default_val, "model_dump"):
                    default_val = default_val.model_dump()
                data[field_name] = default_val
                logger.debug(
                    f"Injected model default value for excluded field '{field_name}'"
                )
            else:
                # No default → leave missing; validation will surface error
                logger.debug(f"No default found for excluded field '{field_name}'")

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
            logger.debug(f"Received POST request on {refresh_route_path}")
            # Calls the instance method to handle the logic
            return await self.handle_refresh_request(req)

        logger.debug(
            f"Registered refresh route for form '{self.name}' at {refresh_route_path}"
        )

        # --- Register the form-specific reset route ---
        reset_route_path = f"/form/{self.name}/reset"

        @app.route(reset_route_path, methods=["POST"])
        async def _instance_specific_reset_handler(req):
            """Handle form reset request for this specific form instance"""
            logger.debug(f"Received POST request on {reset_route_path}")
            # Calls the instance method to handle the logic
            return await self.handle_reset_request()

        logger.debug(
            f"Registered reset route for form '{self.name}' at {reset_route_path}"
        )

        @app.route(f"/form/{self.name}/list/add/{{field_name}}")
        async def post_list_add(req, field_name: str):
            """
            Handle adding an item to a list for this specific form

            Args:
                req: The request object
                field_name: The name of the list field

            Returns:
                A component for the new list item
            """
            # Find field info
            field_info = None
            item_type = None

            if field_name in self.model_class.model_fields:
                field_info = self.model_class.model_fields[field_name]
                annotation = getattr(field_info, "annotation", None)

                if (
                    annotation is not None
                    and hasattr(annotation, "__origin__")
                    and annotation.__origin__ is list
                ):
                    item_type = annotation.__args__[0]

                if not item_type:
                    logger.error(
                        f"Cannot determine item type for list field {field_name}"
                    )
                    return mui.Alert(
                        f"Cannot determine item type for list field {field_name}",
                        cls=mui.AlertT.error,
                    )

            # Create a default item using smart defaults
            default_item_dict: Dict[str, Any] | str | Any | None = None
            try:
                if not item_type:
                    logger.warning(
                        f"item_type was None when trying to create default for {field_name}"
                    )
                    default_item_dict = ""
                elif hasattr(item_type, "model_fields"):
                    # For Pydantic models, use smart default generation
                    default_item_dict = default_dict_for_model(item_type)
                else:
                    # For simple types, use annotation-based defaults
                    default_item_dict = default_for_annotation(item_type)

                # Final fallback for exotic cases
                if default_item_dict is None:
                    default_item_dict = ""

            except Exception as e:
                logger.error(
                    f"Error creating default item for {field_name}: {e}", exc_info=True
                )
                return fh.Li(
                    mui.Alert(
                        f"Error creating default item: {str(e)}", cls=mui.AlertT.error
                    ),
                    cls="mb-2",
                )

            # Generate a unique placeholder index
            placeholder_idx = f"new_{int(pytime.time() * 1000)}"

            # Create a list renderer
            if field_info is not None:
                list_renderer = ListFieldRenderer(
                    field_name=field_name,
                    field_info=field_info,
                    value=[],  # Empty list, we only need to render one item
                    prefix=self.base_prefix,  # Use the form's base prefix
                )
            else:
                logger.error(f"field_info is None for field {field_name}")
                return mui.Alert(
                    f"Field info not found for {field_name}",
                    cls=mui.AlertT.error,
                )

            # The default_item_dict is already in the correct format (dict for models, primitive for simple types)
            item_data_for_renderer = default_item_dict
            logger.debug(
                f"Add item: Using smart default for renderer: {item_data_for_renderer}"
            )

            # Render the new item card, set is_open=True to make it expanded by default
            new_item_card = list_renderer._render_item_card(
                item_data_for_renderer,  # Pass the dictionary or simple value
                placeholder_idx,
                item_type,
                is_open=True,
            )

            return new_item_card

        @app.route(f"/form/{self.name}/list/delete/{{field_name}}", methods=["DELETE"])
        async def delete_list_item(req, field_name: str):
            """
            Handle deleting an item from a list for this specific form

            Args:
                req: The request object
                field_name: The name of the list field

            Returns:
                Empty string to delete the target element
            """
            # Return empty string to delete the target element
            logger.debug(
                f"Received DELETE request for {field_name} for form '{self.name}'"
            )
            return fh.Response(status_code=200, content="")

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

        # Define the form ID to include
        form_id = f"{self.name}-form"

        # Define the target URL
        refresh_url = f"/form/{self.name}/refresh"

        # Base button attributes
        button_attrs = {
            "type": "button",  # Prevent form submission
            "hx_post": refresh_url,  # Target the instance-specific route
            "hx_target": f"#{form_content_wrapper_id}",  # Target the wrapper Div ID
            "hx_swap": "innerHTML",
            "hx_trigger": "click",  # Explicit trigger on click
            "hx_include": f"#{form_id}",  # Include all form fields in the request
            "uk_tooltip": "Update the form display based on current values (e.g., list item titles)",
            "cls": mui.ButtonT.secondary,
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
        logger.debug(f"Validating request for form '{self.name}'")
        form_data = await req.form()
        form_dict = dict(form_data)

        # Parse the form data using the renderer's logic
        parsed_data = self.parse(form_dict)

        # Validate against the model - allow ValidationError to propagate
        validated_model = self.model_class.model_validate(parsed_data)
        logger.info(f"Request validation successful for form '{self.name}'")

        return validated_model
