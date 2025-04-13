import logging
import time as pytime
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel

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

logger = logging.getLogger(__name__)

LIST_MANIPULATION_JS = """  
function moveItem(buttonElement, direction) {
    // Find the card container (may need to adjust selector)
    const card = buttonElement.closest('.uk-card');
    if (!card) return;

    const container = card.parentElement;
    if (!container) return;

    // Find the sibling in the direction we want to move
    const sibling = direction === 'up' ? card.previousElementSibling : card.nextElementSibling;
    
    if (sibling) {
        if (direction === 'up') {
            container.insertBefore(card, sibling);
        } else {
            // Insert card after the next sibling
            container.insertBefore(card, sibling.nextElementSibling);
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
    const cards = container.querySelectorAll('.uk-card');
    cards.forEach((card, index) => {
        const upButton = card.querySelector('button[onclick^="moveItemUp"]');
        const downButton = card.querySelector('button[onclick^="moveItemDown"]');
        
        if (upButton) upButton.disabled = (index === 0);
        if (downButton) downButton.disabled = (index === cards.length - 1);
    });
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
"""


class FormRenderer:
    """
    Renders a form from a Pydantic model class

    This class handles:
    - Finding appropriate renderers for each field
    - Managing field prefixes for proper form submission
    - Creating the overall form structure
    - Registering HTMX routes for list manipulation
    - Parsing form data back to Pydantic model format
    - Handling refresh and reset requests
    - providing refresh and reset buttons
    """

    def __init__(
        self,
        name: str,
        model_class: Type[BaseModel],
        initial_data: Optional[BaseModel] = None,
        custom_renderers: Optional[List[Tuple[Type, Type[BaseFieldRenderer]]]] = None,
    ):
        """
        Initialize the form renderer

        Args:
            name: Unique name for this form
            model_class: The Pydantic model class to render
            initial_data: Optional initial Pydantic model instance
            custom_renderers: Optional list of tuples (field_type, renderer_cls) to register
        """
        self.name = name
        self.model_class = model_class
        self.initial_data_model = initial_data  # Store original model for fallback
        self.values_dict = initial_data.model_dump() if initial_data else {}
        self.base_prefix = f"{name}_"

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
        logger.info(
            f"Starting render_inputs for form '{self.name}' with {len(self.model_class.model_fields)} fields"
        )
        logger.info(
            f"values_dict contains {len(self.values_dict) if self.values_dict else 0} keys"
        )

        for field_name, field_info in self.model_class.model_fields.items():
            # Determine initial value
            initial_value = (
                self.values_dict.get(field_name) if self.values_dict else None
            )

            # Log the initial value type and a summary for debugging
            if initial_value is not None:
                value_type = type(initial_value).__name__
                if isinstance(initial_value, (list, dict)):
                    value_size = f"size={len(initial_value)}"
                else:
                    value_size = ""
                logger.info(f"Field '{field_name}': {value_type} {value_size}")
            else:
                logger.info(
                    f"Field '{field_name}': None (will use default if available)"
                )

            # Use default if no value is provided
            if initial_value is None:
                if field_info.default is not None:
                    initial_value = field_info.default
                    logger.info(f"  - Using default value for '{field_name}'")
                elif getattr(field_info, "default_factory", None) is not None:
                    try:
                        initial_value = field_info.default_factory()
                        logger.info(f"  - Using default_factory for '{field_name}'")
                    except Exception as e:
                        initial_value = None
                        logger.warning(
                            f"  - Error in default_factory for '{field_name}': {e}"
                        )

            # Get renderer from global registry
            renderer_cls = registry.get_renderer(field_name, field_info)
            renderer_name = renderer_cls.__name__ if renderer_cls else "None"

            if not renderer_cls:
                # Fall back to StringFieldRenderer if no renderer found
                renderer_cls = StringFieldRenderer
                logger.warning(
                    f"  - No renderer found for '{field_name}', falling back to StringFieldRenderer"
                )
            else:
                logger.info(f"  - Using renderer {renderer_name} for '{field_name}'")

            # Create and render the field
            renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=initial_value,
                prefix=self.base_prefix,
            )

            rendered_field = renderer.render()
            form_inputs.append(rendered_field)

            # Special debug for ListFieldRenderer which often causes issues
            if renderer_name == "ListFieldRenderer" and isinstance(initial_value, list):
                logger.info(
                    f"  - List field '{field_name}' with {len(initial_value)} items rendered"
                )

        # Create container for inputs, ensuring items stretch to full width
        logger.info(f"Rendered {len(form_inputs)} field components")
        inputs_container = mui.DivVStacked(*form_inputs, cls="space-y-3 items-stretch")

        # Define the ID for the wrapper div - this is what the HTMX request targets
        form_content_wrapper_id = f"{self.name}-inputs-wrapper"
        logger.info(f"Creating form inputs wrapper with ID: {form_content_wrapper_id}")

        # Return only the inner container without the wrapper div
        # The wrapper will be added by the main route handler instead
        logger.info("Completed render_inputs, returning inner inputs container")
        return inputs_container

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
        logger.info(
            f"Refresh request for form '{self.name}' received raw data: {form_dict}"
        )
        logger.info(f"Form data keys count: {len(form_dict.keys())} keys")

        parsed_data = {}
        alert_ft = None  # Changed to hold an FT object instead of a string
        try:
            # Use the instance's parse method directly
            logger.info(
                f"Starting parse() for form '{self.name}' with base_prefix: '{self.base_prefix}'"
            )
            parsed_data = self.parse(form_dict)
            logger.info(f"Parsed data for refresh: {parsed_data}")
            logger.info(
                f"Parsed data contains {len(parsed_data.keys())} top-level keys"
            )

            # Log some specific field types for debugging
            for key, value in parsed_data.items():
                if isinstance(value, list):
                    logger.info(f"List field '{key}' has {len(value)} items")
                elif isinstance(value, dict):
                    logger.info(f"Dict field '{key}' has {len(value.keys())} keys")
        except Exception as e:
            logger.error(
                f"Error parsing form data for refresh on form '{self.name}': {e}",
                exc_info=True,
            )
            # Fallback: Use original initial data model dump if available, otherwise empty dict
            parsed_data = (
                self.initial_data_model.model_dump() if self.initial_data_model else {}
            )
            logger.warning(f"Using fallback data with {len(parsed_data.keys())} keys")
            alert_ft = mui.Alert(
                f"Warning: Could not fully process current form values for refresh. Display might not be fully updated. Error: {str(e)}",
                cls=mui.AlertT.warning + " mb-4",  # Add margin bottom
            )

        # Create Temporary Renderer instance
        temp_renderer = FormRenderer(
            name=self.name,
            model_class=self.model_class,
            # No initial_data needed here, we set values_dict below
        )
        # Set the values based on the parsed (or fallback) data
        temp_renderer.values_dict = parsed_data
        logger.info(
            f"Temporary renderer created with {len(temp_renderer.values_dict.keys())} values"
        )

        # Verify field values in temp_renderer
        for field_name in self.model_class.model_fields:
            if field_name in temp_renderer.values_dict:
                value = temp_renderer.values_dict[field_name]
                value_type = type(value).__name__
                value_summary = (
                    str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                )
                logger.info(
                    f"Temp renderer field '{field_name}': {value_type} = {value_summary}"
                )
            else:
                logger.warning(f"Temp renderer missing field '{field_name}'")

        # Re-render Form Inputs using the temporary renderer with current data
        logger.info("Calling render_inputs() on temporary renderer")
        refreshed_inputs_component = temp_renderer.render_inputs()

        if refreshed_inputs_component is None:
            logger.error("render_inputs() returned None!")
            alert_ft = mui.Alert(
                "Critical error: Form refresh failed to generate content",
                cls=mui.AlertT.error + " mb-4",
            )
            # Emergency fallback - use original renderer's inputs
            refreshed_inputs_component = self.render_inputs()
            logger.info("Used emergency fallback to original renderer")

        # Log information about what we're returning
        logger.info(f"Returning refreshed FT components for form '{self.name}'")

        # Return the FT components directly instead of creating a Response object
        if alert_ft:
            # Return both the alert and the form inputs as a tuple
            logger.info("Returning alert and refreshed inputs as tuple")
            return (alert_ft, refreshed_inputs_component)
        else:
            # Return just the form inputs
            logger.info("Returning refreshed inputs only")
            return refreshed_inputs_component

    async def handle_reset_request(self) -> FT:
        """
        Handles the POST request for resetting this form instance to its initial values.

        Returns:
            HTML response with reset form inputs
        """
        logger.info(
            f"Handling reset request for form '{self.name}' using initial data."
        )

        # Create a temporary renderer with the original initial data
        temp_renderer = FormRenderer(
            name=self.name,
            model_class=self.model_class,
            initial_data=self.initial_data_model,  # Use the originally stored model
        )

        # Render inputs with the initial data
        reset_inputs_component = temp_renderer.render_inputs()
        logger.info(f"Reset form '{self.name}' to initial values")

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
        logger.info(
            f"Starting parse() for form '{self.name}' with prefix '{self.base_prefix}'"
        )
        logger.info(f"Form dict contains {len(form_dict)} keys")

        # Count how many keys actually have the prefix
        prefix_count = sum(1 for key in form_dict if key.startswith(self.base_prefix))
        logger.info(
            f"Form has {prefix_count} keys with the expected prefix '{self.base_prefix}'"
        )

        # Log a sample of keys for debugging
        key_sample = list(form_dict.keys())[:5]  # First 5 keys
        for key in key_sample:
            logger.info(f"Sample key: '{key}' = {form_dict[key]}")

        # Identify list field definitions
        list_field_defs = _identify_list_fields(self.model_class)
        logger.info(f"Identified {len(list_field_defs)} list fields in the model")
        for field_name, field_def in list_field_defs.items():
            is_model = field_def["is_model_type"]
            item_type = field_def["item_type"]
            item_type_name = (
                item_type.__name__ if hasattr(item_type, "__name__") else str(item_type)
            )
            logger.info(
                f"  - List field '{field_name}': {item_type_name} (is_model={is_model})"
            )

        # Parse non-list fields first - pass the base_prefix
        logger.info("Parsing non-list fields")
        result = _parse_non_list_fields(
            form_dict, self.model_class, list_field_defs, self.base_prefix
        )
        logger.info(f"Non-list field parsing resulted in {len(result)} fields")

        # Parse list fields based on keys present in form_dict - pass the base_prefix
        logger.info("Parsing list fields")
        list_results = _parse_list_fields(form_dict, list_field_defs, self.base_prefix)
        logger.info(f"List field parsing resulted in {len(list_results)} fields")

        # Log the parsed list fields
        for field_name, items in list_results.items():
            if isinstance(items, list):
                logger.info(f"  - Parsed list '{field_name}' with {len(items)} items")
                # Log a sample of the first item if available
                if items and len(items) > 0:
                    first_item = items[0]
                    if isinstance(first_item, dict):
                        logger.info(f"    - First item keys: {list(first_item.keys())}")
                    else:
                        item_preview = str(first_item)[:50]
                        logger.info(
                            f"    - First item ({type(first_item).__name__}): {item_preview}"
                        )
            else:
                logger.warning(
                    f"  - Parsed field '{field_name}' is not a list: {type(items).__name__}"
                )

        # Merge list results into the main result
        result.update(list_results)
        logger.info(f"Final parsed result contains {len(result)} fields")

        return result

    def register_routes(self, rt):
        """
        Register HTMX routes for list manipulation and form refresh

        Args:
            rt: The route registrar function from the application
        """

        # --- Register the form-specific refresh route ---
        refresh_route_path = f"/form/{self.name}/refresh"

        @rt(refresh_route_path, methods=["POST"])
        async def _instance_specific_refresh_handler(req):
            """Handle form refresh request for this specific form instance"""
            # Add entry point logging to confirm the route is being hit
            logger.info(f"Received POST request on {refresh_route_path}")
            # Calls the instance method to handle the logic
            return await self.handle_refresh_request(req)

        logger.info(
            f"Registered refresh route for form '{self.name}' at {refresh_route_path}"
        )

        # --- Register the form-specific reset route ---
        reset_route_path = f"/form/{self.name}/reset"

        @rt(reset_route_path, methods=["POST"])
        async def _instance_specific_reset_handler(req):
            """Handle form reset request for this specific form instance"""
            logger.info(f"Received POST request on {reset_route_path}")
            # Calls the instance method to handle the logic
            return await self.handle_reset_request()

        logger.info(
            f"Registered reset route for form '{self.name}' at {reset_route_path}"
        )

        @rt(f"/form/{self.name}/list/add/{{field_name}}")
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
                    item_type_name = (
                        item_type.__name__
                        if hasattr(item_type, "__name__")
                        else str(item_type)
                    )
                    logger.info(f"Determined item type: {item_type_name}")

                if not item_type:
                    logger.error(
                        f"Cannot determine item type for list field {field_name}"
                    )
                    return mui.Alert(
                        f"Cannot determine item type for list field {field_name}",
                        cls=mui.AlertT.error,
                    )

            # Create a default item
            try:
                # Ensure item_type is not None before checking attributes or type
                if item_type:
                    # For Pydantic models, try to use model_construct for default values
                    if hasattr(item_type, "model_construct"):
                        try:
                            default_item = item_type.model_construct()
                        except Exception as e:
                            return fh.Li(
                                mui.Alert(
                                    f"Error creating model instance: {str(e)}",
                                    cls=mui.AlertT.error,
                                ),
                                cls="mb-2",
                            )
                    # Handle simple types with appropriate defaults
                    elif item_type is str:
                        default_item = ""
                    elif item_type is int:
                        default_item = 0
                    elif item_type is float:
                        default_item = 0.0
                    elif item_type is bool:
                        default_item = False
                    else:
                        default_item = None
                else:
                    # Case where item_type itself was None (should ideally be caught earlier)
                    default_item = None
                    logger.warning(
                        f"item_type was None when trying to create default for {field_name}"
                    )
            except Exception as e:
                return fh.Li(
                    mui.Alert(
                        f"Error creating default item: {str(e)}", cls=mui.AlertT.error
                    ),
                    cls="mb-2",
                )

            # Generate a unique placeholder index
            placeholder_idx = f"new_{int(pytime.time() * 1000)}"

            # Create a list renderer and render the new item
            list_renderer = ListFieldRenderer(
                field_name=field_name,
                field_info=field_info,
                value=[],  # Empty list, we only need to render one item
                prefix=self.base_prefix,  # Use the form's base prefix
            )

            # Render the new item card, set is_open=True to make it expanded by default
            new_item_card = list_renderer._render_item_card(
                default_item, placeholder_idx, item_type, is_open=True
            )

            return new_item_card

        @rt(f"/form/{self.name}/list/delete/{{field_name}}", methods=["DELETE"])
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
            return fh.Response(status_code=200, content="")

    def get_refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
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

    def get_reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
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
