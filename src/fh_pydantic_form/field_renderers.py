import logging
from datetime import date, time
from enum import Enum
from typing import (
    Any,
    Optional,
    get_args,
    get_origin,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import ValidationError
from pydantic.fields import FieldInfo

from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    _UNSET,
    _get_underlying_type_if_optional,
    _is_optional_type,
    get_default,
)
from fh_pydantic_form.ui_style import (
    SpacingTheme,
    SpacingValue,
    _normalize_spacing,
    spacing,
)

logger = logging.getLogger(__name__)


def _merge_cls(base: str, extra: str) -> str:
    """Return base plus extra class(es) separated by a single space (handles blanks)."""
    if extra:
        combined = f"{base} {extra}".strip()
        # Remove duplicate whitespace
        return " ".join(combined.split())
    return base


class BaseFieldRenderer:
    """
    Base class for field renderers

    Field renderers are responsible for:
    - Rendering a label for the field
    - Rendering an appropriate input element for the field
    - Combining the label and input with proper spacing

    Subclasses must implement render_input()
    """

    def __init__(
        self,
        field_name: str,
        field_info: FieldInfo,
        value: Any = None,
        prefix: str = "",
        disabled: bool = False,
        label_color: Optional[str] = None,
        spacing: SpacingValue = SpacingTheme.NORMAL,
    ):
        """
        Initialize the field renderer

        Args:
            field_name: The name of the field
            field_info: The FieldInfo for the field
            value: The current value of the field (optional)
            prefix: Optional prefix for the field name (used for nested fields)
            disabled: Whether the field should be rendered as disabled
            label_color: Optional CSS color value for the field label
            spacing: Spacing theme to use for layout ("normal", "compact", or SpacingTheme enum)
        """
        self.field_name = f"{prefix}{field_name}" if prefix else field_name
        self.original_field_name = field_name
        self.field_info = field_info
        self.value = value
        self.prefix = prefix
        self.is_optional = _is_optional_type(field_info.annotation)
        self.disabled = disabled
        self.label_color = label_color
        self.spacing = _normalize_spacing(spacing)

    def render_label(self) -> FT:
        """
        Render label for the field

        Returns:
            A FastHTML component for the label
        """
        # Get field description from field_info
        description = getattr(self.field_info, "description", None)

        # Prepare label text
        label_text = self.original_field_name.replace("_", " ").title()

        # Create span attributes with tooltip if description is available
        span_attrs = {}
        if description:
            span_attrs["uk-tooltip"] = description  # UIkit tooltip
            span_attrs["title"] = description  # Standard HTML tooltip
            # Removed cursor-help class while preserving tooltip functionality

        # Create the span with the label text and tooltip
        label_text_span = fh.Span(label_text, **span_attrs)

        # Prepare label attributes
        label_attrs = {"For": self.field_name}

        # Build label classes with tokenized gap
        label_gap_class = spacing("label_gap", self.spacing)
        base_classes = f"block text-sm font-medium text-gray-700 {label_gap_class}"

        cls_attr = base_classes

        # Apply color styling if specified
        if self.label_color:
            # Check if it's a CSS class (contains letters/hyphens) or a color value
            if self.label_color.replace("-", "").replace("#", "").isalnum():
                # Looks like a CSS class, add it to the class list
                cls_attr = f"block text-sm font-medium {self.label_color} {label_gap_class}".strip()
            else:
                # Treat as color value
                label_attrs["style"] = f"color: {self.label_color};"

        # Create and return the label - using standard fh.Label with appropriate styling
        return fh.Label(
            label_text_span,
            **label_attrs,
            cls=cls_attr,
        )

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A FastHTML component for the input element

        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError("Subclasses must implement render_input")

    def render(self) -> FT:
        """
        Render the complete field (label + input) with spacing in a collapsible accordion

        Returns:
            A FastHTML component (mui.Accordion) containing the complete field
        """
        # 1. Get the full label component (fh.Label)
        label_component = self.render_label()

        # Apply color styling directly to the Label component if needed
        if self.label_color and isinstance(label_component, fh.FT):
            if "style" in label_component.attrs:
                label_component.attrs["style"] += f" color: {self.label_color};"
            else:
                label_component.attrs["style"] = f"color: {self.label_color};"

        # 2. Render the input field that will be the accordion content
        input_component = self.render_input()

        # 3. Define unique IDs for potential targeting
        item_id = f"{self.field_name}_item"
        accordion_id = f"{self.field_name}_accordion"

        # 4. Create the AccordionItem with the full label component as title
        accordion_item = mui.AccordionItem(
            label_component,  # Use the entire label component including the "for" attribute
            input_component,  # Content component (the input field)
            open=True,  # Open by default
            li_kwargs={"id": item_id},  # Pass the specific ID for the <li>
            cls=spacing(
                "outer_margin_sm", self.spacing
            ),  # Add spacing between accordion items
        )

        # 5. Wrap the single AccordionItem in an Accordion container
        accordion_container = mui.Accordion(
            accordion_item,  # The single item to include
            id=accordion_id,  # ID for the accordion container (ul)
            multiple=True,  # Allow multiple open (though only one exists)
            collapsible=True,  # Allow toggling
            cls=f"{spacing('accordion_divider', self.spacing)} {spacing('accordion_content', self.spacing)}".strip(),
        )

        return accordion_container


# ---- Specific Field Renderers ----


class StringFieldRenderer(BaseFieldRenderer):
    """Renderer for string fields"""

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A TextInput component appropriate for string values
        """
        # is_field_required = (
        #     not self.is_optional
        #     and self.field_info.default is None
        #     and getattr(self.field_info, "default_factory", None) is None
        # )
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Enter {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_attrs = {
            "value": self.value or "",
            "id": self.field_name,
            "name": self.field_name,
            "type": "text",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": _merge_cls(
                "w-full",
                f"{spacing('input_size', self.spacing)} {spacing('input_padding', self.spacing)}".strip(),
            ),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class NumberFieldRenderer(BaseFieldRenderer):
    """Renderer for number fields (int, float)"""

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A NumberInput component appropriate for numeric values
        """
        # Determine if field is required
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Enter {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_attrs = {
            "value": str(self.value) if self.value is not None else "",
            "id": self.field_name,
            "name": self.field_name,
            "type": "number",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": _merge_cls(
                "w-full",
                f"{spacing('input_size', self.spacing)} {spacing('input_padding', self.spacing)}".strip(),
            ),
            "step": "any"
            if self.field_info.annotation is float
            or get_origin(self.field_info.annotation) is float
            else "1",
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class BooleanFieldRenderer(BaseFieldRenderer):
    """Renderer for boolean fields"""

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A CheckboxX component appropriate for boolean values
        """
        checkbox_attrs = {
            "id": self.field_name,
            "name": self.field_name,
            "checked": bool(self.value),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            checkbox_attrs["disabled"] = True

        return mui.CheckboxX(**checkbox_attrs)


class DateFieldRenderer(BaseFieldRenderer):
    """Renderer for date fields"""

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A DateInput component appropriate for date values
        """
        formatted_value = ""
        if (
            isinstance(self.value, str) and len(self.value) == 10
        ):  # Basic check for YYYY-MM-DD format
            # Assume it's the correct string format from the form
            formatted_value = self.value
        elif isinstance(self.value, date):
            formatted_value = self.value.isoformat()  # YYYY-MM-DD

        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Select {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_attrs = {
            "value": formatted_value,
            "id": self.field_name,
            "name": self.field_name,
            "type": "date",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": _merge_cls(
                "w-full",
                f"{spacing('input_size', self.spacing)} {spacing('input_padding', self.spacing)}".strip(),
            ),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class TimeFieldRenderer(BaseFieldRenderer):
    """Renderer for time fields"""

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A TimeInput component appropriate for time values
        """
        formatted_value = ""
        if (
            isinstance(self.value, str) and len(self.value) == 5
        ):  # Basic check for HH:MM format
            # Assume it's the correct string format from the form
            formatted_value = self.value
        elif isinstance(self.value, time):
            formatted_value = self.value.strftime("%H:%M")  # HH:MM

        # Determine if field is required
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Select {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_attrs = {
            "value": formatted_value,
            "id": self.field_name,
            "name": self.field_name,
            "type": "time",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": _merge_cls(
                "w-full",
                f"{spacing('input_size', self.spacing)} {spacing('input_padding', self.spacing)}".strip(),
            ),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class LiteralFieldRenderer(BaseFieldRenderer):
    """Renderer for Literal fields as dropdown selects"""

    def render_input(self) -> FT:
        """
        Render input element for the field as a select dropdown

        Returns:
            A Select component with options based on the Literal values
        """
        # Get the Literal values from annotation
        annotation = _get_underlying_type_if_optional(self.field_info.annotation)
        literal_values = get_args(annotation)

        if not literal_values:
            return mui.Alert(
                f"No literal values found for {self.field_name}", cls=mui.AlertT.warning
            )

        # Determine if field is required
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        # Create options for each literal value
        options = []
        current_value_str = str(self.value) if self.value is not None else None

        # Add empty option for optional fields
        if self.is_optional:
            options.append(
                fh.Option("-- None --", value="", selected=(self.value is None))
            )

        # Add options for each literal value
        for value in literal_values:
            value_str = str(value)
            is_selected = current_value_str == value_str
            options.append(
                fh.Option(
                    value_str,  # Display text
                    value=value_str,  # Value attribute
                    selected=is_selected,
                )
            )

        placeholder_text = f"Select {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        # Prepare attributes dictionary
        select_attrs = {
            "id": self.field_name,
            "name": self.field_name,
            "required": is_field_required,
            "placeholder": placeholder_text,
            "cls": _merge_cls(
                "w-full",
                f"{spacing('input_size', self.spacing)} {spacing('input_padding', self.spacing)}".strip(),
            ),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            select_attrs["disabled"] = True

        # Render the select element with options and attributes
        return mui.Select(*options, **select_attrs)


class EnumFieldRenderer(BaseFieldRenderer):
    """Renderer for Enum fields as dropdown selects"""

    def render_input(self) -> FT:
        """
        Render input element for the field as a select dropdown

        Returns:
            A Select component with options based on the Enum values
        """
        # Get the Enum class from annotation
        annotation = _get_underlying_type_if_optional(self.field_info.annotation)
        enum_class = annotation

        if not (isinstance(enum_class, type) and issubclass(enum_class, Enum)):
            return mui.Alert(
                f"No enum class found for {self.field_name}", cls=mui.AlertT.warning
            )

        # Get all enum members
        enum_members = list(enum_class)

        if not enum_members:
            return mui.Alert(
                f"No enum values found for {self.field_name}", cls=mui.AlertT.warning
            )

        # Determine if field is required
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        # Create options for each enum value
        options = []
        current_value_str = None

        # Convert current value to string for comparison
        if self.value is not None:
            if isinstance(self.value, Enum):
                current_value_str = str(self.value.value)
            else:
                current_value_str = str(self.value)

        # Add empty option for optional fields
        if self.is_optional:
            options.append(
                fh.Option("-- None --", value="", selected=(self.value is None))
            )

        # Add options for each enum member
        for member in enum_members:
            member_value_str = str(member.value)
            display_name = member.name.replace("_", " ").title()
            is_selected = current_value_str == member_value_str
            options.append(
                fh.Option(
                    display_name,  # Display text
                    value=member_value_str,  # Value attribute
                    selected=is_selected,
                )
            )

        placeholder_text = f"Select {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        # Prepare attributes dictionary
        select_attrs = {
            "id": self.field_name,
            "name": self.field_name,
            "required": is_field_required,
            "placeholder": placeholder_text,
            "cls": _merge_cls(
                "w-full",
                f"{spacing('input_size', self.spacing)} {spacing('input_padding', self.spacing)}".strip(),
            ),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            select_attrs["disabled"] = True

        # Render the select element with options and attributes
        return mui.Select(*options, **select_attrs)


class BaseModelFieldRenderer(BaseFieldRenderer):
    """Renderer for nested Pydantic BaseModel fields"""

    def render(self) -> FT:
        """
        Render the nested BaseModel field as a single-item accordion using mui.Accordion.

        Returns:
            A FastHTML component (mui.Accordion) containing the accordion structure.
        """
        # 1. Get the label content (the inner Span with text/tooltip)
        label_component = self.render_label()
        if isinstance(label_component, fh.FT) and label_component.children:
            label_content = label_component.children[0]
            # Extract label style if present
            label_style = label_component.attrs.get("style", "")
            # Apply label style directly to the span if needed
            if label_style:
                # Check if label_content is already a Span, otherwise wrap it
                if isinstance(label_content, fh.Span):
                    label_content.attrs["style"] = label_style
                else:
                    # This case is less likely if render_label returns Label(Span(...))
                    label_content = fh.Span(label_content, style=label_style)
        else:
            # Fallback if structure is different (should not happen ideally)
            label_content = self.original_field_name.replace("_", " ").title()
            label_style = f"color: {self.label_color};" if self.label_color else ""
            if label_style:
                label_content = fh.Span(label_content, style=label_style)

        # 2. Render the nested input fields that will be the accordion content
        input_component = self.render_input()

        # 3. Define unique IDs for potential targeting
        item_id = f"{self.field_name}_item"
        accordion_id = f"{self.field_name}_accordion"

        # 4. Create the AccordionItem using the MonsterUI component
        #    - Pass label_content as the title.
        #    - Pass input_component as the content.
        #    - Set 'open=True' to be expanded by default.
        #    - Pass item_id via li_kwargs.
        #    - Add 'mb-4' class for bottom margin spacing.
        accordion_item = mui.AccordionItem(
            label_content,  # Title component (already potentially styled Span)
            input_component,  # Content component (the Card with nested fields)
            open=True,  # Open by default
            li_kwargs={"id": item_id},  # Pass the specific ID for the <li>
            cls=spacing(
                "outer_margin", self.spacing
            ),  # Add bottom margin to the <li> element
        )

        # 5. Wrap the single AccordionItem in an Accordion container
        accordion_container = mui.Accordion(
            accordion_item,  # The single item to include
            id=accordion_id,  # ID for the accordion container (ul)
            multiple=True,  # Allow multiple open (though only one exists)
            collapsible=True,  # Allow toggling
            cls=f"{spacing('accordion_divider', self.spacing)} {spacing('accordion_content', self.spacing)}".strip(),
        )

        return accordion_container

    def render_input(self) -> FT:
        """
        Render input elements for nested model fields with robust schema drift handling

        Returns:
            A Card component containing nested form fields
        """
        # Get the nested model class from annotation
        nested_model_class = _get_underlying_type_if_optional(
            self.field_info.annotation
        )

        if nested_model_class is None or not hasattr(
            nested_model_class, "model_fields"
        ):
            return mui.Alert(
                f"No nested model class found for {self.field_name}",
                cls=mui.AlertT.error,
            )

        # Robust value preparation
        if isinstance(self.value, dict):
            values_dict = self.value.copy()
        elif hasattr(self.value, "model_dump"):
            values_dict = self.value.model_dump()
        else:
            values_dict = {}

        # Create nested field inputs with error handling
        nested_inputs = []
        skipped_fields = []

        # Only process fields that exist in current model schema
        for (
            nested_field_name,
            nested_field_info,
        ) in nested_model_class.model_fields.items():
            try:
                # Check if field exists in provided values
                field_was_provided = nested_field_name in values_dict
                nested_field_value = (
                    values_dict.get(nested_field_name) if field_was_provided else None
                )

                # Only use defaults if field wasn't provided
                if not field_was_provided:
                    if nested_field_info.default is not None:
                        nested_field_value = nested_field_info.default
                    elif (
                        getattr(nested_field_info, "default_factory", None) is not None
                    ):
                        try:
                            nested_field_value = nested_field_info.default_factory()
                        except Exception as e:
                            logger.warning(
                                f"Default factory failed for {nested_field_name}: {e}"
                            )
                            nested_field_value = None

                # Get renderer for this nested field
                registry = FieldRendererRegistry()  # Get singleton instance
                renderer_cls = registry.get_renderer(
                    nested_field_name, nested_field_info
                )

                if not renderer_cls:
                    # Fall back to StringFieldRenderer if no renderer found
                    renderer_cls = StringFieldRenderer

                # The prefix for nested fields is simply the field_name of this BaseModel instance + underscore
                # field_name already includes the form prefix, so we don't need to add self.prefix again
                nested_prefix = f"{self.field_name}_"

                # Create and render the nested field
                renderer = renderer_cls(
                    field_name=nested_field_name,
                    field_info=nested_field_info,
                    value=nested_field_value,
                    prefix=nested_prefix,
                    disabled=self.disabled,  # Propagate disabled state to nested fields
                    spacing=self.spacing,  # Propagate spacing to nested fields
                )

                nested_inputs.append(renderer.render())

            except Exception as e:
                logger.warning(
                    f"Skipping field {nested_field_name} in nested model: {e}"
                )
                skipped_fields.append(nested_field_name)
                continue

        # Log summary if fields were skipped
        if skipped_fields:
            logger.info(
                f"Skipped {len(skipped_fields)} fields in {self.field_name}: {skipped_fields}"
            )

        # Create container for nested inputs
        nested_form_content = mui.DivVStacked(
            *nested_inputs,
            cls=f"{spacing('inner_gap', self.spacing)} items-stretch",
        )

        # Wrap in card for visual distinction
        t = self.spacing
        return mui.Card(
            nested_form_content,
            cls=f"{spacing('padding_sm', t)} mt-1 {spacing('card_border', t)} rounded".strip(),
        )


class ListFieldRenderer(BaseFieldRenderer):
    """Renderer for list fields containing any type"""

    def render(self) -> FT:
        """
        Render the complete field (label + input) with spacing, adding a refresh icon for list fields.
        Makes the label clickable to toggle all list items open/closed.

        Returns:
            A FastHTML component containing the complete field with refresh icon
        """
        # Extract form name from prefix (removing trailing underscore if present)
        form_name = self.prefix.rstrip("_") if self.prefix else None

        # Get the original label
        original_label = self.render_label()

        # Construct the container ID that will be generated by render_input()
        container_id = f"{self.prefix}{self.original_field_name}_items_container"

        # Only add refresh icon if we have a form name
        if form_name:
            # Create the smaller icon component
            refresh_icon_component = mui.UkIcon(
                "refresh-ccw",
                cls="w-3 h-3 text-gray-500 hover:text-blue-600",  # Smaller size
            )

            # Create the clickable span wrapper for the icon
            refresh_icon_trigger = fh.Span(
                refresh_icon_component,
                cls="ml-1 inline-block align-middle cursor-pointer",  # Add margin, ensure inline-like behavior
                hx_post=f"/form/{form_name}/refresh",
                hx_target=f"#{form_name}-inputs-wrapper",
                hx_swap="innerHTML",
                hx_include=f"#{form_name}-form",
                uk_tooltip="Refresh form display to update list summaries",
            )

            # Combine label and icon
            label_with_icon = fh.Div(
                original_label,
                refresh_icon_trigger,
                cls="flex items-center cursor-pointer",  # Added cursor-pointer
                onclick=f"toggleListItems('{container_id}'); return false;",  # Add click handler
            )
        else:
            # If no form name, just use the original label but still make it clickable
            label_with_icon = fh.Div(
                original_label,
                cls="flex items-center cursor-pointer",  # Added cursor-pointer
                onclick=f"toggleListItems('{container_id}'); return false;",  # Add click handler
                uk_tooltip="Click to toggle all items open/closed",
            )

        # Return container with label+icon and input
        return fh.Div(
            label_with_icon,
            self.render_input(),
            cls=spacing("outer_margin", self.spacing),
        )

    def render_input(self) -> FT:
        """
        Render a list of items with add/delete/move capabilities

        Returns:
            A component containing the list items and controls
        """
        # Initialize the value as an empty list, ensuring it's always a list
        items = [] if not isinstance(self.value, list) else self.value

        annotation = getattr(self.field_info, "annotation", None)

        if (
            annotation is not None
            and hasattr(annotation, "__origin__")
            and annotation.__origin__ is list
        ):
            item_type = annotation.__args__[0]

        if not item_type:
            logger.error(f"Cannot determine item type for list field {self.field_name}")
            return mui.Alert(
                f"Cannot determine item type for list field {self.field_name}",
                cls=mui.AlertT.error,
            )

        # Create list items
        item_elements = []
        for idx, item in enumerate(items):
            try:
                item_card = self._render_item_card(item, idx, item_type)
                item_elements.append(item_card)
            except Exception as e:
                logger.error(f"Error rendering item {idx}: {str(e)}", exc_info=True)
                error_message = f"Error rendering item {idx}: {str(e)}"

                # Add more context to the error for debugging
                if isinstance(item, dict):
                    error_message += f" (Dict keys: {list(item.keys())})"

                item_elements.append(
                    mui.AccordionItem(
                        mui.Alert(
                            error_message,
                            cls=mui.AlertT.error,
                        ),
                        # title=f"Error in item {idx}",
                        li_kwargs={"cls": "mb-2"},
                    )
                )

        # Container for list items with form-specific prefix in ID
        container_id = f"{self.prefix}{self.original_field_name}_items_container"

        # Use mui.Accordion component
        accordion = mui.Accordion(
            *item_elements,
            id=container_id,
            multiple=True,  # Allow multiple items to be open at once
            collapsible=True,  # Make it collapsible
            cls=f"{spacing('inner_gap_small', self.spacing)} {spacing('accordion_content', self.spacing)}".strip(),  # Add space between items and accordion content styling
        )

        # Empty state message if no items
        empty_state = ""
        if not items:
            # Extract form name from prefix if available
            form_name = self.prefix.rstrip("_") if self.prefix else None

            # Check if it's a simple type or BaseModel
            add_url = (
                f"/form/{form_name}/list/add/{self.original_field_name}"
                if form_name
                else f"/list/add/{self.field_name}"
            )

            # Prepare button attributes
            add_button_attrs = {
                "cls": "uk-button-primary uk-button-small mt-2",
                "hx_post": add_url,
                "hx_target": f"#{container_id}",
                "hx_swap": "beforeend",
                "type": "button",
            }

            # Only add disabled attribute if field should be disabled
            if self.disabled:
                add_button_attrs["disabled"] = "true"

            empty_state = mui.Alert(
                fh.Div(
                    mui.UkIcon("info", cls="mr-2"),
                    "No items in this list. Click 'Add Item' to create one.",
                    mui.Button("Add Item", **add_button_attrs),
                    cls="flex flex-col items-start",
                ),
                cls=mui.AlertT.info,
            )

        # Return the complete component
        t = self.spacing
        return fh.Div(
            accordion,
            empty_state,
            cls=f"{spacing('outer_margin', t)} {spacing('card_border', t)} rounded-md {spacing('padding', t)}".strip(),
        )

    def _render_item_card(self, item, idx, item_type, is_open=False) -> FT:
        """
        Render a card for a single item in the list

        Args:
            item: The item data
            idx: The index of the item
            item_type: The type of the item
            is_open: Whether the accordion item should be open by default

        Returns:
            A FastHTML component for the item card
        """
        try:
            # Create a unique ID for this item
            item_id = f"{self.field_name}_{idx}"
            item_card_id = f"{item_id}_card"

            # Extract form name from prefix if available
            form_name = self.prefix.rstrip("_") if self.prefix else None

            # Check if it's a simple type or BaseModel
            is_model = hasattr(item_type, "model_fields")

            # --- Generate item summary for the accordion title ---
            if is_model:
                try:
                    # Determine how to get the string representation based on item type
                    if isinstance(item, item_type):
                        # Item is already a model instance
                        model_for_display = item

                    elif isinstance(item, dict):
                        # Item is a dict, use model_construct for better performance (defaults are known-good)
                        model_for_display = item_type.model_construct(**item)

                    else:
                        # Handle cases where item is None or unexpected type
                        model_for_display = None
                        logger.warning(
                            f"Item {item} is neither a model instance nor a dict: {type(item).__name__}"
                        )

                    if model_for_display is not None:
                        # Use the model's __str__ method
                        item_summary_text = (
                            f"{item_type.__name__}: {str(model_for_display)}"
                        )
                    else:
                        # Fallback for None or unexpected types
                        item_summary_text = f"{item_type.__name__}: (Unknown format: {type(item).__name__})"
                        logger.warning(
                            f"Using fallback summary text: {item_summary_text}"
                        )
                except ValidationError as e:
                    # Handle validation errors when creating model from dict
                    logger.warning(
                        f"Validation error creating display string for {item_type.__name__}: {e}"
                    )
                    if isinstance(item, dict):
                        logger.warning(
                            f"Validation failed for dict keys: {list(item.keys())}"
                        )
                    item_summary_text = f"{item_type.__name__}: (Invalid data)"
                except Exception as e:
                    # Catch any other unexpected errors
                    logger.error(
                        f"Error creating display string for {item_type.__name__}: {e}",
                        exc_info=True,
                    )
                    item_summary_text = f"{item_type.__name__}: (Error displaying item)"
            else:
                item_summary_text = str(item)

            # --- Render item content elements ---
            item_content_elements = []

            if is_model:
                # Handle BaseModel items with robust schema drift handling
                # Form name prefix + field name + index + _
                name_prefix = f"{self.prefix}{self.original_field_name}_{idx}_"

                # Robust value preparation for schema drift handling
                if isinstance(item, dict):
                    nested_values = item.copy()
                elif hasattr(item, "model_dump"):
                    nested_values = item.model_dump()
                else:
                    nested_values = {}

                # Check if there's a specific renderer registered for this item_type
                registry = FieldRendererRegistry()
                # Create a dummy FieldInfo for the renderer lookup
                item_field_info = FieldInfo(annotation=item_type)
                # Look up potential custom renderer for this item type
                item_renderer_cls = registry.get_renderer(
                    f"item_{idx}", item_field_info
                )

                # Get the default BaseModelFieldRenderer class for comparison
                from_imports = globals()
                BaseModelFieldRenderer_cls = from_imports.get("BaseModelFieldRenderer")

                # Check if a specific renderer (different from BaseModelFieldRenderer) was found
                if (
                    item_renderer_cls
                    and item_renderer_cls is not BaseModelFieldRenderer_cls
                ):
                    # Use the custom renderer for the entire item
                    item_renderer = item_renderer_cls(
                        field_name=f"{self.original_field_name}_{idx}",
                        field_info=item_field_info,
                        value=item,
                        prefix=self.prefix,
                        disabled=self.disabled,  # Propagate disabled state
                    )
                    # Add the rendered input to content elements
                    item_content_elements.append(item_renderer.render_input())
                else:
                    # Fall back to original behavior: render each field individually with schema drift handling
                    valid_fields = []
                    skipped_fields = []

                    # Only process fields that exist in current model
                    for (
                        nested_field_name,
                        nested_field_info,
                    ) in item_type.model_fields.items():
                        try:
                            field_was_provided = nested_field_name in nested_values
                            nested_field_value = (
                                nested_values.get(nested_field_name)
                                if field_was_provided
                                else None
                            )

                            # Use defaults only if field not provided
                            if not field_was_provided:
                                if nested_field_info.default is not None:
                                    nested_field_value = nested_field_info.default
                                elif (
                                    getattr(nested_field_info, "default_factory", None)
                                    is not None
                                ):
                                    try:
                                        nested_field_value = (
                                            nested_field_info.default_factory()
                                        )
                                    except Exception:
                                        continue  # Skip fields with problematic defaults

                            # Get renderer and render field with error handling
                            renderer_cls = FieldRendererRegistry().get_renderer(
                                nested_field_name, nested_field_info
                            )
                            if not renderer_cls:
                                renderer_cls = StringFieldRenderer

                            renderer = renderer_cls(
                                field_name=nested_field_name,
                                field_info=nested_field_info,
                                value=nested_field_value,
                                prefix=name_prefix,
                                disabled=self.disabled,  # Propagate disabled state
                                spacing=self.spacing,  # Propagate spacing
                            )

                            # Add rendered field to valid fields
                            valid_fields.append(renderer.render())

                        except Exception as e:
                            logger.warning(
                                f"Skipping problematic field {nested_field_name} in list item: {e}"
                            )
                            skipped_fields.append(nested_field_name)
                            continue

                    # Log summary if fields were skipped
                    if skipped_fields:
                        logger.info(
                            f"Skipped {len(skipped_fields)} fields in list item {idx}: {skipped_fields}"
                        )

                    item_content_elements = valid_fields
            else:
                # Handle simple type items
                field_info = FieldInfo(annotation=item_type)
                renderer_cls = FieldRendererRegistry().get_renderer(
                    f"item_{idx}", field_info
                )
                # Calculate the base name for the item within the list
                item_base_name = f"{self.original_field_name}_{idx}"  # e.g., "tags_0"

                simple_renderer = renderer_cls(
                    field_name=item_base_name,  # Correct: Use name relative to list field
                    field_info=field_info,
                    value=item,
                    prefix=self.prefix,  # Correct: Provide the form prefix
                    disabled=self.disabled,  # Propagate disabled state
                    spacing=self.spacing,  # Propagate spacing
                )
                input_element = simple_renderer.render_input()
                item_content_elements.append(fh.Div(input_element))

            # --- Create action buttons with form-specific URLs ---
            # Generate HTMX endpoints with form name if available
            delete_url = (
                f"/form/{form_name}/list/delete/{self.original_field_name}"
                if form_name
                else f"/list/delete/{self.field_name}"
            )

            add_url = (
                f"/form/{form_name}/list/add/{self.original_field_name}"
                if form_name
                else f"/list/add/{self.field_name}"
            )

            # Use the full ID (with prefix) for targeting
            full_card_id = (
                f"{self.prefix}{item_card_id}" if self.prefix else item_card_id
            )

            # Create attribute dictionaries for buttons
            delete_button_attrs = {
                "cls": "uk-button-danger uk-button-small",
                "hx_delete": delete_url,
                "hx_target": f"#{full_card_id}",
                "hx_swap": "outerHTML",
                "uk_tooltip": "Delete this item",
                "hx_params": f"idx={idx}",
                "hx_confirm": "Are you sure you want to delete this item?",
                "type": "button",  # Prevent form submission
            }

            add_below_button_attrs = {
                "cls": "uk-button-secondary uk-button-small ml-2",
                "hx_post": add_url,
                "hx_target": f"#{full_card_id}",
                "hx_swap": "afterend",
                "uk_tooltip": "Insert new item below",
                "type": "button",  # Prevent form submission
            }

            move_up_button_attrs = {
                "cls": "uk-button-link move-up-btn",
                "onclick": "moveItemUp(this); return false;",
                "uk_tooltip": "Move up",
                "type": "button",  # Prevent form submission
            }

            move_down_button_attrs = {
                "cls": "uk-button-link move-down-btn ml-2",
                "onclick": "moveItemDown(this); return false;",
                "uk_tooltip": "Move down",
                "type": "button",  # Prevent form submission
            }

            # Create buttons using attribute dictionaries, passing disabled state directly
            delete_button = mui.Button(
                mui.UkIcon("trash"), disabled=self.disabled, **delete_button_attrs
            )

            add_below_button = mui.Button(
                mui.UkIcon("plus-circle"),
                disabled=self.disabled,
                **add_below_button_attrs,
            )

            move_up_button = mui.Button(
                mui.UkIcon("arrow-up"), disabled=self.disabled, **move_up_button_attrs
            )

            move_down_button = mui.Button(
                mui.UkIcon("arrow-down"),
                disabled=self.disabled,
                **move_down_button_attrs,
            )

            # Assemble actions div
            t = self.spacing
            actions = fh.Div(
                fh.Div(  # Left side buttons
                    delete_button, add_below_button, cls="flex items-center"
                ),
                fh.Div(  # Right side buttons
                    move_up_button, move_down_button, cls="flex items-center space-x-1"
                ),
                cls=f"flex justify-between w-full mt-3 pt-3 {spacing('section_divider', t)}".strip(),
            )

            # Create a wrapper Div for the main content elements with proper padding
            t = self.spacing
            content_wrapper = fh.Div(
                *item_content_elements,
                cls=f"{spacing('card_body_pad', t)} {spacing('inner_gap', t)}",
            )

            # Return the accordion item
            title_component = fh.Span(
                item_summary_text, cls="text-gray-700 font-medium pl-3"
            )
            li_attrs = {"id": full_card_id}

            # Build card classes conditionally based on spacing theme
            card_cls = "uk-card uk-margin-small-bottom"
            if self.spacing == SpacingTheme.NORMAL:
                card_cls += " uk-card-default"

            return mui.AccordionItem(
                title_component,  # Title as first positional argument
                content_wrapper,  # Use the new padded wrapper for content
                actions,  # More content elements
                cls=card_cls,  # Use theme-aware card classes
                open=is_open,
                li_kwargs=li_attrs,  # Pass remaining li attributes without cls
            )

        except Exception as e:
            # Return error representation
            title_component = f"Error in item {idx}"
            content_component = mui.Alert(
                f"Error rendering item {idx}: {str(e)}", cls=mui.AlertT.error
            )
            li_attrs = {"id": f"{self.field_name}_{idx}_error_card"}

            # Wrap error component in a div with consistent padding
            t = self.spacing
            content_wrapper = fh.Div(content_component, cls=spacing("card_body_pad", t))

            # Build card classes conditionally based on spacing theme
            card_cls = "uk-card uk-margin-small-bottom"
            if self.spacing == SpacingTheme.NORMAL:
                card_cls += " uk-card-default"

            return mui.AccordionItem(
                title_component,  # Title as first positional argument
                content_wrapper,  # Wrapped content element
                cls=card_cls,  # Use theme-aware card classes
                li_kwargs=li_attrs,  # Pass remaining li attributes without cls
            )
