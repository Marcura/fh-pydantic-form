import logging
import re
from datetime import date, time
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    List,
    Optional,
    get_args,
    get_origin,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel, ValidationError
from pydantic.fields import FieldInfo

from fh_pydantic_form.color_utils import (
    DEFAULT_METRIC_GREY,
    get_metric_colors,
    robust_color_to_rgba,
)
from fh_pydantic_form.constants import _UNSET
from fh_pydantic_form.defaults import default_dict_for_model, default_for_annotation
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    DecorationScope,
    MetricEntry,
    MetricsDict,
    _get_underlying_type_if_optional,
    _is_optional_type,
    _is_skip_json_schema_field,
    get_default,
    normalize_path_segments,
)
from fh_pydantic_form.ui_style import (
    SpacingTheme,
    SpacingValue,
    _normalize_spacing,
    spacing,
    spacing_many,
)

logger = logging.getLogger(__name__)


def _is_form_control(node: Any) -> bool:
    """
    Returns True if this node is a form control element that should receive highlighting.

    Detects both raw HTML form controls and MonsterUI wrapper components.
    """
    if not hasattr(node, "tag"):
        return False

    tag = str(getattr(node, "tag", "")).lower()

    # Raw HTML controls
    if tag in ("input", "select", "textarea"):
        return True

    # For MonsterUI components, highlight the outer div container instead of inner elements
    # This provides better visual feedback since MonsterUI hides the actual select elements
    if hasattr(node, "attrs") and hasattr(node, "children"):
        classes = str(node.attrs.get("cls", "") or node.attrs.get("class", ""))

        # Check if this div contains a MonsterUI component
        if tag == "div" and node.children:
            for child in node.children:
                child_tag = str(getattr(child, "tag", "")).lower()
                if child_tag.startswith("uk-") and any(
                    control in child_tag for control in ["select", "input", "checkbox"]
                ):
                    return True

        # Also check for direct MonsterUI wrapper classes
        if tag == "div" and "uk-select" in classes:
            return True

        # MonsterUI typically uses uk- prefixed classes
        if any(
            c
            for c in classes.split()
            if c.startswith("uk-")
            and any(t in c for t in ["input", "select", "checkbox"])
        ):
            return True

    return False


def _merge_cls(base: str, extra: str) -> str:
    """Return base plus extra class(es) separated by a single space (handles blanks)."""
    if extra:
        combined = f"{base} {extra}".strip()
        # Remove duplicate whitespace
        return " ".join(combined.split())
    return base


class MetricsRendererMixin:
    """Mixin to add metrics highlighting capabilities to field renderers"""

    def _decorate_label(
        self,
        label: FT,
        metric_entry: Optional[MetricEntry],
    ) -> FT:
        """
        Decorate a label element with a metric badge (bullet) if applicable.
        """
        return self._decorate_metrics(label, metric_entry, scope=DecorationScope.BULLET)

    def _decorate_metrics(
        self,
        element: FT,
        metric_entry: Optional[MetricEntry],
        *,
        scope: DecorationScope = DecorationScope.BOTH,
    ) -> FT:
        """
        Decorate an element with metrics visual feedback.

        Args:
            element: The FastHTML element to decorate
            metric_entry: Optional metric entry with color, score, and comment
            scope: Which decorations to apply (BORDER, BULLET, or BOTH)

        Returns:
            Decorated element with left color bar, tooltip, and optional metric badge
        """
        if not metric_entry:
            return element

        # Add tooltip with comment if available
        comment = metric_entry.get("comment")
        if comment and hasattr(element, "attrs"):
            element.attrs["uk-tooltip"] = comment
            element.attrs["title"] = comment  # Fallback standard tooltip

        # Add left color bar if requested
        if scope in {DecorationScope.BORDER, DecorationScope.BOTH}:
            border_color = self._metric_border_color(metric_entry)
            if border_color and hasattr(element, "attrs"):
                existing_style = element.attrs.get("style", "")
                element.attrs["style"] = (
                    f"border-left: 4px solid {border_color}; padding-left: 0.25rem; position: relative; z-index: 0; {existing_style}"
                )

        # Add metric score badge if requested and present
        score = metric_entry.get("metric")
        color = metric_entry.get("color")
        if (
            scope in {DecorationScope.BULLET, DecorationScope.BOTH}
            and score is not None
        ):
            # Determine bullet colors based on LangSmith-style system when no color provided
            if color:
                # Use provided color - convert to full opacity for badge
                badge_bg_rgba = robust_color_to_rgba(color, 1.0)
                # Extract RGB values and use them for badge background
                rgb_match = re.match(
                    r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*[\d.]+\)", badge_bg_rgba
                )
                if rgb_match:
                    r, g, b = rgb_match.groups()
                    badge_bg = f"rgb({r}, {g}, {b})"
                else:
                    badge_bg = color
                text_color = "white"
            else:
                # Use metric-based color system
                badge_bg, text_color = get_metric_colors(score)

            # Create custom styled span that looks like a bullet/pill
            metric_badge = fh.Span(
                str(score),
                style=f"""
                    background-color: {badge_bg};
                    color: {text_color};
                    padding: 0.125rem 0.5rem;
                    border-radius: 9999px;
                    font-size: 0.75rem;
                    font-weight: 500;
                    display: inline-block;
                    margin-left: 0.5rem;
                    vertical-align: top;
                    line-height: 1.25;
                    white-space: nowrap;
                    text-shadow: 0 1px 2px rgba(0,0,0,0.1);
                """,
                cls="uk-text-nowrap",
            )

            # Use helper to attach badge properly
            return self._attach_metric_badge(element, metric_badge)

        return element

    def _attach_metric_badge(self, element: FT, badge: FT) -> FT:
        """
        Attach a metric badge to an element in the most appropriate way.

        Args:
            element: The element to attach the badge to
            badge: The badge element to attach

        Returns:
            Element with badge attached
        """
        # Check if element is an inline-capable tag
        tag = str(getattr(element, "tag", "")).lower()
        inline_tags = {"span", "a", "h1", "h2", "h3", "h4", "h5", "h6", "label"}

        if tag in inline_tags and hasattr(element, "children"):
            # For inline elements, append badge directly to children
            if isinstance(element.children, list):
                element.children.append(badge)
            else:
                # Convert to list if needed
                element.children = list(element.children) + [badge]
            return element

        # For other elements, wrap in a flex container
        return fh.Div(element, badge, cls="relative inline-flex items-center w-full")

    def _highlight_input_fields(self, element: FT, metric_entry: MetricEntry) -> FT:
        """
        Find nested form controls and add a colored box-shadow to them
        based on the metric entry color.

        Args:
            element: The FT element to search within
            metric_entry: The metric entry containing color information

        Returns:
            The element with highlighted input fields
        """
        if not metric_entry:
            return element

        # Determine the color to use for highlighting
        color = metric_entry.get("color")
        score = metric_entry.get("metric")

        if color:
            # Use the provided color
            highlight_color = color
        elif score is not None:
            # Use metric-based color system (background color from the helper)
            highlight_color, _ = get_metric_colors(score)
        else:
            # No color or metric available
            return element

        # Create the highlight CSS with appropriate opacity for both border and background
        # Use !important to ensure our styles override MonsterUI defaults
        # Focus on border highlighting since background might conflict with MonsterUI styling
        border_rgba = robust_color_to_rgba(highlight_color, 0.8)
        background_rgba = robust_color_to_rgba(highlight_color, 0.1)
        highlight_css = f"border: 2px solid {border_rgba} !important; border-radius: 4px !important; box-shadow: 0 0 0 1px {border_rgba} !important; background-color: {background_rgba} !important;"

        # Track how many elements we highlight
        highlight_count = 0

        # Recursively find and style input elements
        def apply_highlight(node):
            """Recursively apply highlighting to input elements"""
            nonlocal highlight_count

            if _is_form_control(node):
                # Add or update the style attribute
                if hasattr(node, "attrs"):
                    existing_style = node.attrs.get("style", "")
                    node.attrs["style"] = highlight_css + " " + existing_style
                    highlight_count += 1

            # Process children if they exist
            if hasattr(node, "children") and node.children:
                for child in node.children:
                    apply_highlight(child)

        # Apply highlighting to the element tree
        apply_highlight(element)

        if highlight_count == 0:
            pass  # No form controls found to highlight

        return element

    def _metric_border_color(
        self, metric_entry: Optional[MetricEntry]
    ) -> Optional[str]:
        """
        Get an RGBA color string for a metric entry's left border bar.

        Args:
            metric_entry: The metric entry containing color/score information

        Returns:
            RGBA color string for left border bar, or None if no metric
        """
        if not metric_entry:
            return None

        # Use provided color if available
        if metric_entry.get("color"):
            return robust_color_to_rgba(metric_entry["color"], 0.8)

        # Otherwise derive from metric score
        metric = metric_entry.get("metric")
        if metric is not None:
            color, _ = get_metric_colors(metric)
            # If get_metric_colors returns the fallback grey, use our unified light grey
            if color == DEFAULT_METRIC_GREY:
                return DEFAULT_METRIC_GREY
            return robust_color_to_rgba(color, 0.8)

        # If only a comment is present, return the unified light grey color
        if metric_entry.get("comment"):
            return DEFAULT_METRIC_GREY

        return None


def _build_path_string_static(path_segments: List[str]) -> str:
    """
    Static version of BaseFieldRenderer._build_path_string for use without instance.

    Convert field_path list to dot/bracket notation string for metric lookup.

    Examples:
        ['experience', '0', 'company'] -> 'experience[0].company'
        ['skills', 'programming_languages', '2'] -> 'skills.programming_languages[2]'

    Args:
        path_segments: List of path segments

    Returns:
        Path string in dot/bracket notation
    """
    parts: List[str] = []
    for segment in path_segments:
        # Check if segment is numeric or a list index pattern
        if segment.isdigit() or segment.startswith("new_"):
            # Interpret as list index
            if parts:
                parts[-1] += f"[{segment}]"
            else:  # Defensive fallback
                parts.append(f"[{segment}]")
        else:
            parts.append(segment)
    return ".".join(parts)


class BaseFieldRenderer(MetricsRendererMixin):
    """
    Base class for field renderers

    Field renderers are responsible for:
    - Rendering a label for the field
    - Rendering an appropriate input element for the field
    - Combining the label and input with proper spacing
    - Optionally applying comparison visual feedback

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
        field_path: Optional[List[str]] = None,
        form_name: Optional[str] = None,
        metric_entry: Optional[MetricEntry] = None,
        metrics_dict: Optional[MetricsDict] = None,
        refresh_endpoint_override: Optional[str] = None,
        keep_skip_json_pathset: Optional[set[str]] = None,
        comparison_copy_enabled: bool = False,
        comparison_copy_target: Optional[str] = None,
        comparison_name: Optional[str] = None,
        **kwargs,  # Accept additional kwargs for extensibility
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
            field_path: Path segments from root to this field (for nested list support)
            form_name: Explicit form name (used for nested list URLs)
            metric_entry: Optional metric entry for visual feedback
            metrics_dict: Optional full metrics dict for auto-lookup
            refresh_endpoint_override: Optional override URL for refresh actions (used in ComparisonForm)
            comparison_copy_enabled: If True, show copy button for this field
            comparison_copy_target: "left" or "right" - which side this field is on
            comparison_name: Name of the ComparisonForm (for copy route URLs)
            **kwargs: Additional keyword arguments for extensibility
        """
        self.field_name = f"{prefix}{field_name}" if prefix else field_name
        self.original_field_name = field_name
        self.field_info = field_info
        # Normalize PydanticUndefined → None so it never renders as text
        try:
            from pydantic_core import PydanticUndefined

            if value is PydanticUndefined:
                value = None
        except Exception:
            pass
        self.value = value
        self.prefix = prefix
        self.field_path: List[str] = field_path or []
        self.explicit_form_name: Optional[str] = form_name
        self.is_optional = _is_optional_type(field_info.annotation)
        self.disabled = disabled
        self.label_color = label_color
        self.spacing = _normalize_spacing(spacing)
        self.metrics_dict = metrics_dict
        self._refresh_endpoint_override = refresh_endpoint_override
        self._keep_skip_json_pathset = keep_skip_json_pathset or set()
        self._cmp_copy_enabled = comparison_copy_enabled
        self._cmp_copy_target = comparison_copy_target
        self._cmp_name = comparison_name

        # Initialize metric entry attribute
        self.metric_entry: Optional[MetricEntry] = None

        # Auto-resolve metric entry if not explicitly provided
        if metric_entry is not None:
            self.metric_entry = metric_entry
        elif metrics_dict:
            path_string = self._build_path_string()
            self.metric_entry = metrics_dict.get(path_string)

    def _build_path_string(self) -> str:
        """
        Convert field_path list to dot/bracket notation string for comparison lookup.

        Examples:
            ['experience', '0', 'company'] -> 'experience[0].company'
            ['skills', 'programming_languages', '2'] -> 'skills.programming_languages[2]'

        Returns:
            Path string in dot/bracket notation
        """
        parts: List[str] = []
        for segment in self.field_path:
            # Check if segment is numeric or a list index pattern
            if segment.isdigit() or segment.startswith("new_"):
                # Interpret as list index
                if parts:
                    parts[-1] += f"[{segment}]"
                else:  # Defensive fallback
                    parts.append(f"[{segment}]")
            else:
                parts.append(segment)
        return ".".join(parts)

    def _normalized_dot_path(self, path_segments: List[str]) -> str:
        """Normalize path segments by dropping indices and joining with dots."""
        return normalize_path_segments(path_segments)

    def _is_kept_skip_field(self, full_path: List[str]) -> bool:
        """Return True if a SkipJsonSchema field should be kept based on keep list."""
        normalized = self._normalized_dot_path(full_path)
        return bool(normalized) and normalized in self._keep_skip_json_pathset

    def _is_inline_color(self, color: str) -> bool:
        """
        Determine if a color should be applied as an inline style or CSS class.

        Args:
            color: The color value to check

        Returns:
            True if the color should be applied as inline style, False if as CSS class
        """
        # Check if it's a hex color value (starts with #) or basic HTML color name
        return color.startswith("#") or color in [
            "red",
            "blue",
            "green",
            "yellow",
            "orange",
            "purple",
            "pink",
            "cyan",
            "magenta",
            "brown",
            "black",
            "white",
            "gray",
            "grey",
        ]

    def _get_color_class(self, color: str) -> str:
        """
        Get the appropriate CSS class for a color.

        Args:
            color: The color name

        Returns:
            The CSS class string for the color
        """
        return f"text-{color}-600"

    def _render_comparison_copy_button(self) -> Optional[FT]:
        """
        Render a copy button for comparison forms.

        Note: Copy buttons are never disabled, even if the field itself is disabled.
        This allows copying from disabled (read-only) fields to editable fields.

        Returns:
            A copy button component, or None if not in comparison mode
        """
        if not (self._cmp_copy_enabled and self._cmp_copy_target and self._cmp_name):
            return None

        path = self._build_path_string()
        # Use arrow pointing in the direction of the copy (towards target)
        arrow = "arrow-left" if self._cmp_copy_target == "left" else "arrow-right"
        tooltip_text = f"Copy to {self._cmp_copy_target}"

        # Note: We explicitly do NOT pass disabled=self.disabled here
        # Copy buttons should always be enabled, even in disabled forms
        #
        # Pure JS copy: Bypass HTMX entirely to avoid accordion collapse
        # Button is on SOURCE side, arrow points to TARGET side
        return mui.Button(
            mui.UkIcon(arrow, cls="w-4 h-4 text-gray-500 hover:text-blue-600"),
            type="button",
            onclick=f"window.fhpfPerformCopy('{path}', '{self.prefix}', '{self._cmp_copy_target}'); return false;",
            uk_tooltip=tooltip_text,
            cls="uk-button-text uk-button-small flex-shrink-0",
            style="all: unset; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0.25rem; min-width: 1.5rem;",
        )

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
        label_attrs = {"for": self.field_name}

        # Build label classes with tokenized gap
        label_gap_class = spacing("label_gap", self.spacing)
        base_classes = f"block text-sm font-medium text-gray-700 {label_gap_class}"

        cls_attr = base_classes

        # Apply color styling if specified
        if self.label_color:
            if self._is_inline_color(self.label_color):
                # Treat as color value
                label_attrs["style"] = f"color: {self.label_color};"
            else:
                # Treat as CSS class (includes Tailwind colors like emerald, amber, rose, teal, indigo, lime, violet, etc.)
                cls_attr = f"block text-sm font-medium {self._get_color_class(self.label_color)} {label_gap_class}".strip()

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
        Render the complete field (label + input) with spacing

        For compact spacing: renders label and input side-by-side
        For normal spacing: renders label above input (traditional)

        Returns:
            A FastHTML component containing the complete field
        """
        # 1. Get the label component (without copy button)
        label_component = self.render_label()

        # 2. Render the input field
        input_component = self.render_input()

        # 3. Get the copy button if enabled
        copy_button = self._render_comparison_copy_button()

        # 4. Choose layout based on spacing theme
        if self.spacing == SpacingTheme.COMPACT:
            # Horizontal layout for compact mode
            field_element = fh.Div(
                fh.Div(
                    label_component,
                    input_component,
                    cls=f"flex {spacing('horizontal_gap', self.spacing)} {spacing('label_align', self.spacing)} w-full",
                ),
                cls=f"{spacing('outer_margin', self.spacing)} w-full",
            )
        else:
            # Vertical layout for normal mode
            field_element = fh.Div(
                label_component,
                input_component,
                cls=spacing("outer_margin", self.spacing),
            )

        # 5. Apply metrics decoration if available
        decorated_field = self._decorate_metrics(field_element, self.metric_entry)

        # 6. If copy button exists, wrap the entire decorated field with copy button on the right
        if copy_button:
            return fh.Div(
                decorated_field,
                copy_button,
                cls="flex items-start gap-2 w-full",
            )
        else:
            return decorated_field


# ---- Specific Field Renderers ----


class StringFieldRenderer(BaseFieldRenderer):
    """Renderer for string fields"""

    def __init__(self, *args, **kwargs):
        """Initialize string field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A TextArea component appropriate for string values
        """

        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Enter {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_cls_parts = ["w-full"]
        input_spacing_cls = spacing_many(
            ["input_size", "input_padding", "input_line_height", "input_font_size"],
            self.spacing,
        )
        if input_spacing_cls:
            input_cls_parts.append(input_spacing_cls)

        # Calculate appropriate number of rows based on content
        if isinstance(self.value, str) and self.value:
            # Count line breaks
            line_count = len(self.value.split("\n"))
            # Also consider content length for very long single lines (assuming ~60 chars per line)
            char_count = len(self.value)
            estimated_lines = max(line_count, (char_count // 60) + 1)
            # Compact bounds: minimum 1 row, maximum 3 rows
            rows = min(max(estimated_lines, 1), 3)
        else:
            # Single row for empty content
            rows = 1

        input_attrs = {
            "id": self.field_name,
            "name": self.field_name,
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": " ".join(input_cls_parts),
            "rows": rows,
            "style": "resize: vertical; min-height: 2.5rem; padding: 0.5rem; line-height: 1.25;",
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        # Convert value to string representation, handling None and all other types
        if self.value is None:
            display_value = ""
        else:
            display_value = str(self.value)

        return mui.TextArea(display_value, **input_attrs)


class NumberFieldRenderer(BaseFieldRenderer):
    """Renderer for number fields (int, float)"""

    def __init__(self, *args, **kwargs):
        """Initialize number field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

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

        input_cls_parts = ["w-full"]
        input_spacing_cls = spacing_many(
            ["input_size", "input_padding", "input_line_height", "input_font_size"],
            self.spacing,
        )
        if input_spacing_cls:
            input_cls_parts.append(input_spacing_cls)

        input_attrs = {
            "value": str(self.value) if self.value is not None else "",
            "id": self.field_name,
            "name": self.field_name,
            "type": "number",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": " ".join(input_cls_parts),
            "step": "any"
            if self.field_info.annotation is float
            or get_origin(self.field_info.annotation) is float
            else "1",
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class DecimalFieldRenderer(BaseFieldRenderer):
    """Renderer for decimal.Decimal fields"""

    def __init__(self, *args, **kwargs):
        """Initialize decimal field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

    def render_input(self) -> FT:
        """
        Render input element for decimal fields

        Returns:
            A NumberInput component appropriate for decimal values
        """
        # Determine if field is required
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Enter {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_cls_parts = ["w-full"]
        input_spacing_cls = spacing_many(
            ["input_size", "input_padding", "input_line_height", "input_font_size"],
            self.spacing,
        )
        if input_spacing_cls:
            input_cls_parts.append(input_spacing_cls)

        # Convert Decimal value to string for display
        if isinstance(self.value, Decimal):
            # Use format to avoid scientific notation
            display_value = format(self.value, "f")
            # Normalize zero values to display as "0"
            if self.value == 0:
                display_value = "0"
        elif self.value is not None:
            display_value = str(self.value)
        else:
            display_value = ""

        input_attrs = {
            "value": display_value,
            "id": self.field_name,
            "name": self.field_name,
            "type": "number",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": " ".join(input_cls_parts),
            "step": "any",  # Allow arbitrary decimal precision
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class BooleanFieldRenderer(BaseFieldRenderer):
    """Renderer for boolean fields"""

    def __init__(self, *args, **kwargs):
        """Initialize boolean field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

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
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            checkbox_attrs["disabled"] = True

        return mui.CheckboxX(**checkbox_attrs)

    def render(self) -> FT:
        """
        Render the complete field (label + input) with spacing, placing the checkbox next to the label.

        Returns:
            A FastHTML component containing the complete field
        """
        # Get the label component
        label_component = self.render_label()
        # Decorate the label with the metric badge (bullet)
        label_component = self._decorate_label(label_component, self.metric_entry)

        # Get the checkbox component
        checkbox_component = self.render_input()

        # Get the copy button if enabled
        copy_button = self._render_comparison_copy_button()

        # Create a flex container to place label and checkbox side by side
        field_element = fh.Div(
            fh.Div(
                label_component,
                checkbox_component,
                cls="flex items-center gap-2 w-full",  # Use flexbox to align items horizontally with a small gap
            ),
            cls=f"{spacing('outer_margin', self.spacing)} w-full",
        )

        # Apply metrics decoration if available (border only, as bullet is in the label)
        decorated_field = self._decorate_metrics(
            field_element, self.metric_entry, scope=DecorationScope.BORDER
        )

        # If copy button exists, wrap the entire decorated field with copy button on the right
        if copy_button:
            return fh.Div(
                decorated_field,
                copy_button,
                cls="flex items-start gap-2 w-full",
            )
        else:
            return decorated_field


class DateFieldRenderer(BaseFieldRenderer):
    """Renderer for date fields"""

    def __init__(self, *args, **kwargs):
        """Initialize date field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

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

        input_cls_parts = ["w-full"]
        input_spacing_cls = spacing_many(
            ["input_size", "input_padding", "input_line_height", "input_font_size"],
            self.spacing,
        )
        if input_spacing_cls:
            input_cls_parts.append(input_spacing_cls)

        input_attrs = {
            "value": formatted_value,
            "id": self.field_name,
            "name": self.field_name,
            "type": "date",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": " ".join(input_cls_parts),
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class TimeFieldRenderer(BaseFieldRenderer):
    """Renderer for time fields"""

    def __init__(self, *args, **kwargs):
        """Initialize time field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

    def render_input(self) -> FT:
        """
        Render input element for the field

        Returns:
            A TimeInput component appropriate for time values
        """
        formatted_value = ""
        if isinstance(self.value, str):
            # Try to parse the time string using various formats
            time_formats = ["%H:%M", "%H:%M:%S", "%H:%M:%S.%f"]

            for fmt in time_formats:
                try:
                    from datetime import datetime

                    parsed_time = datetime.strptime(self.value, fmt).time()
                    formatted_value = parsed_time.strftime("%H:%M")
                    break
                except ValueError:
                    continue
        elif isinstance(self.value, time):
            formatted_value = self.value.strftime("%H:%M")  # HH:MM

        # Determine if field is required
        has_default = get_default(self.field_info) is not _UNSET
        is_field_required = not self.is_optional and not has_default

        placeholder_text = f"Select {self.original_field_name.replace('_', ' ')}"
        if self.is_optional:
            placeholder_text += " (Optional)"

        input_cls_parts = ["w-full"]
        input_spacing_cls = spacing_many(
            ["input_size", "input_padding", "input_line_height", "input_font_size"],
            self.spacing,
        )
        if input_spacing_cls:
            input_cls_parts.append(input_spacing_cls)

        input_attrs = {
            "value": formatted_value,
            "id": self.field_name,
            "name": self.field_name,
            "type": "time",
            "placeholder": placeholder_text,
            "required": is_field_required,
            "cls": " ".join(input_cls_parts),
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            input_attrs["disabled"] = True

        return mui.Input(**input_attrs)


class LiteralFieldRenderer(BaseFieldRenderer):
    """Renderer for Literal fields as dropdown selects"""

    def __init__(self, *args, **kwargs):
        """Initialize literal field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

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
        select_cls_parts = ["w-full"]
        select_spacing_cls = spacing_many(
            ["input_size", "input_padding", "input_line_height", "input_font_size"],
            self.spacing,
        )
        if select_spacing_cls:
            select_cls_parts.append(select_spacing_cls)

        select_attrs = {
            "id": self.field_name,
            "name": self.field_name,
            "required": is_field_required,
            "placeholder": placeholder_text,
            "cls": " ".join(select_cls_parts),
            "data-field-path": self._build_path_string(),
        }

        if self.disabled:
            select_attrs["disabled"] = True

        # Render the select element with options and attributes
        return mui.Select(*options, **select_attrs)


class EnumFieldRenderer(BaseFieldRenderer):
    """Renderer for Enum fields as dropdown selects"""

    def __init__(self, *args, **kwargs):
        """Initialize enum field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

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
            "data-field-path": self._build_path_string(),
        }

        # Only add the disabled attribute if the field should actually be disabled
        if self.disabled:
            select_attrs["disabled"] = True

        # Render the select element with options and attributes
        return mui.Select(*options, **select_attrs)


class BaseModelFieldRenderer(BaseFieldRenderer):
    """Renderer for nested Pydantic BaseModel fields"""

    def __init__(self, *args, **kwargs):
        """Initialize base model field renderer, passing all arguments to parent"""
        super().__init__(*args, **kwargs)

    def render(self) -> FT:
        """
        Render the nested BaseModel field as a single-item accordion using mui.Accordion.

        Returns:
            A FastHTML component (mui.Accordion) containing the accordion structure.
        """

        # Extract the label text and apply color styling
        label_text = self.original_field_name.replace("_", " ").title()

        # Create the title component with proper color styling
        if self.label_color:
            if self._is_inline_color(self.label_color):
                # Color value - apply as inline style
                title_span = fh.Span(
                    label_text,
                    style=f"color: {self.label_color};",
                    cls="text-sm font-medium",
                )
            else:
                # CSS class - apply as Tailwind class (includes emerald, amber, rose, teal, indigo, lime, violet, etc.)
                title_span = fh.Span(
                    label_text,
                    cls=f"text-sm font-medium {self._get_color_class(self.label_color)}",
                )
        else:
            # No color specified - use default styling
            title_span = fh.Span(label_text, cls="text-sm font-medium text-gray-700")

        # Add tooltip if description is available
        description = getattr(self.field_info, "description", None)
        if description:
            title_span.attrs["uk-tooltip"] = description
            title_span.attrs["title"] = description

        # Apply metrics decoration to title (bullet only, no border)
        title_with_metrics = self._decorate_metrics(
            title_span, self.metric_entry, scope=DecorationScope.BULLET
        )

        # Get copy button if enabled - add it AFTER metrics decoration
        copy_button = self._render_comparison_copy_button()

        # Wrap title (with metrics) and copy button together if copy button exists
        if copy_button:
            title_component = fh.Div(
                title_with_metrics,
                copy_button,
                cls="flex items-center justify-between gap-2 w-full",
            )
        else:
            title_component = title_with_metrics

        # Compute border color for the top-level BaseModel card
        border_color = self._metric_border_color(self.metric_entry)
        li_style = {}
        if border_color:
            li_style["style"] = (
                f"border-left: 4px solid {border_color}; padding-left: 0.25rem;"
            )

        # 2. Render the nested input fields that will be the accordion content
        input_component = self.render_input()

        # 3. Define unique IDs for potential targeting
        item_id = f"{self.field_name}_item"
        accordion_id = f"{self.field_name}_accordion"

        # 4. Create the AccordionItem using the MonsterUI component
        accordion_item = mui.AccordionItem(
            title_component,  # Title component with proper color styling
            input_component,  # Content component (the Card with nested fields)
            open=True,  # Open by default
            li_kwargs={
                "id": item_id,
                **li_style,
            },  # Pass the specific ID and style for the <li>
            cls=spacing(
                "outer_margin", self.spacing
            ),  # Add bottom margin to the <li> element
        )

        # 5. Wrap the single AccordionItem in an Accordion container
        accordion_cls = spacing_many(
            ["accordion_divider", "accordion_content"], self.spacing
        )
        accordion_container = mui.Accordion(
            accordion_item,  # The single item to include
            id=accordion_id,  # ID for the accordion container (ul)
            multiple=True,  # Allow multiple open (though only one exists)
            collapsible=True,  # Allow toggling
            cls=f"{accordion_cls} w-full".strip(),
        )

        # 6. Apply metrics decoration to the title only (bullet), not the container
        # The parent list renderer handles the border decoration
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
                    dv = get_default(nested_field_info)  # _UNSET if truly unset
                    if dv is not _UNSET:
                        nested_field_value = dv
                    else:
                        ann = nested_field_info.annotation
                        base_ann = get_origin(ann) or ann
                        if isinstance(base_ann, type) and issubclass(
                            base_ann, BaseModel
                        ):
                            nested_field_value = default_dict_for_model(base_ann)
                        else:
                            nested_field_value = default_for_annotation(ann)

                # Skip SkipJsonSchema fields unless explicitly kept
                if _is_skip_json_schema_field(
                    nested_field_info
                ) and not self._is_kept_skip_field(
                    self.field_path + [nested_field_name]
                ):
                    continue

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
                    field_path=self.field_path
                    + [nested_field_name],  # Propagate path with field name
                    form_name=self.explicit_form_name,  # Propagate form name
                    metric_entry=None,  # Let auto-lookup handle it
                    metrics_dict=self.metrics_dict,  # Pass down the metrics dict
                    refresh_endpoint_override=self._refresh_endpoint_override,  # Propagate refresh override
                    keep_skip_json_pathset=self._keep_skip_json_pathset,  # Propagate keep paths
                    comparison_copy_enabled=self._cmp_copy_enabled,  # Propagate comparison copy settings
                    comparison_copy_target=self._cmp_copy_target,
                    comparison_name=self._cmp_name,
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

    def __init__(
        self,
        field_name: str,
        field_info: FieldInfo,
        value: Any = None,
        prefix: str = "",
        disabled: bool = False,
        label_color: Optional[str] = None,
        spacing: SpacingValue = SpacingTheme.NORMAL,
        field_path: Optional[List[str]] = None,
        form_name: Optional[str] = None,
        metric_entry: Optional[MetricEntry] = None,
        metrics_dict: Optional[MetricsDict] = None,
        show_item_border: bool = True,
        **kwargs,  # Accept additional kwargs
    ):
        """
        Initialize the list field renderer

        Args:
            field_name: The name of the field
            field_info: The FieldInfo for the field
            value: The current value of the field (optional)
            prefix: Optional prefix for the field name (used for nested fields)
            disabled: Whether the field should be rendered as disabled
            label_color: Optional CSS color value for the field label
            spacing: Spacing theme to use for layout
            field_path: Path segments from root to this field
            form_name: Explicit form name
            metric_entry: Optional metric entry for visual feedback
            metrics_dict: Optional full metrics dict for auto-lookup
            show_item_border: Whether to show colored borders on list items based on metrics
            **kwargs: Additional keyword arguments passed to parent
        """
        super().__init__(
            field_name=field_name,
            field_info=field_info,
            value=value,
            prefix=prefix,
            disabled=disabled,
            label_color=label_color,
            spacing=spacing,
            field_path=field_path,
            form_name=form_name,
            metric_entry=metric_entry,
            metrics_dict=metrics_dict,
            **kwargs,  # Pass kwargs to parent
        )
        self.show_item_border = show_item_border

    def _container_id(self) -> str:
        """
        Return a DOM-unique ID for the list's <ul> / <div> wrapper.

        Format: <formname>_<hierarchy>_items_container
        Example:  main_form_compact_tags_items_container
        """
        base = "_".join(self.field_path)  # tags  or  main_address_tags
        if self._form_name:  # already resolved in property
            return f"{self._form_name}_{base}_items_container"
        return f"{base}_items_container"  # fallback (shouldn't happen)

    @property
    def _form_name(self) -> str:
        """Get form name - prefer explicit form name if provided"""
        if self.explicit_form_name:
            return self.explicit_form_name

        # Fallback to extracting from prefix (for backward compatibility)
        # The prefix always starts with the form name followed by underscore
        # e.g., "main_form_compact_" or "main_form_compact_main_address_tags_"
        # We need to extract just "main_form_compact"
        if self.prefix:
            # For backward compatibility with existing non-nested lists
            # Split by underscore and rebuild the form name by removing known field components
            parts = self.prefix.rstrip("_").split("_")

            # For a simple heuristic: form names typically have 2-3 parts (main_form_compact)
            # Field paths are at the end, so we find where the form name ends
            # This is imperfect but works for most cases
            if len(parts) >= 3 and parts[1] == "form":
                # Standard pattern: main_form_compact
                form_name = "_".join(parts[:3])
            elif len(parts) >= 2:
                # Fallback: take first 2 parts
                form_name = "_".join(parts[:2])
            else:
                # Single part
                form_name = parts[0] if parts else ""

            return form_name
        return ""

    @property
    def _list_path(self) -> str:
        """Get the hierarchical path for this list field"""
        return "/".join(self.field_path)

    def render(self) -> FT:
        """
        Render the complete field (label + input) with spacing, adding a refresh icon for list fields.
        Makes the label clickable to toggle all list items open/closed.

        Returns:
            A FastHTML component containing the complete field with refresh icon
        """
        # Extract form name from prefix (removing trailing underscore if present)
        # form_name = self.prefix.rstrip("_") if self.prefix else None
        form_name = self._form_name or None

        # Create the label text with proper color styling and item count
        items = [] if not isinstance(self.value, list) else self.value
        item_count = len(items)
        label_text = f"{self.original_field_name.replace('_', ' ').title()} ({item_count} item{'s' if item_count != 1 else ''})"

        # Create the styled label span
        if self.label_color:
            if self._is_inline_color(self.label_color):
                # Color value - apply as inline style
                label_span = fh.Span(
                    label_text,
                    style=f"color: {self.label_color};",
                    cls=f"block text-sm font-medium {spacing('label_gap', self.spacing)}",
                )
            else:
                # CSS class - apply as Tailwind class (includes emerald, amber, rose, teal, indigo, lime, violet, etc.)
                label_span = fh.Span(
                    label_text,
                    cls=f"block text-sm font-medium {self._get_color_class(self.label_color)} {spacing('label_gap', self.spacing)}",
                )
        else:
            # No color specified - use default styling
            label_span = fh.Span(
                label_text,
                cls=f"block text-sm font-medium text-gray-700 {spacing('label_gap', self.spacing)}",
            )

        # Add tooltip if description is available
        description = getattr(self.field_info, "description", None)
        if description:
            label_span.attrs["uk-tooltip"] = description
            label_span.attrs["title"] = description

        # Metric decoration will be applied to the title_component below

        # Build action buttons row (refresh only, NOT copy - copy goes after metrics)
        action_buttons = []

        # Add refresh icon if we have a form name and field is not disabled
        if form_name and not self.disabled:
            # Create the smaller icon component
            refresh_icon_component = mui.UkIcon(
                "refresh-ccw",
                cls="w-3 h-3 text-gray-500 hover:text-blue-600",  # Smaller size
            )

            # Use override endpoint if provided (for ComparisonForm), otherwise use standard form refresh
            refresh_url = (
                self._refresh_endpoint_override or f"/form/{form_name}/refresh"
            )

            # Get container ID for accordion state preservation
            container_id = self._container_id()

            # Create refresh icon as a button with aggressive styling reset
            refresh_icon_trigger = mui.Button(
                refresh_icon_component,
                type="button",  # Prevent form submission
                hx_post=refresh_url,
                hx_target=f"#{form_name}-inputs-wrapper",
                hx_swap="innerHTML",
                hx_trigger="click",  # Explicit trigger on click
                hx_include="closest form",  # Include all form fields from the enclosing form
                hx_preserve="scroll",
                uk_tooltip="Refresh form display to update list summaries",
                style="all: unset; display: inline-flex; align-items: center; cursor: pointer; padding: 0 0.5rem;",
                **{
                    "hx-on::before-request": f"window.saveAccordionState && window.saveAccordionState('{container_id}')"
                },
                **{
                    "hx-on::after-swap": f"window.restoreAccordionState && window.restoreAccordionState('{container_id}')"
                },
            )
            action_buttons.append(refresh_icon_trigger)

        # Build title component with label and action buttons (excluding copy button)
        if action_buttons:
            # Combine label and action buttons
            title_base = fh.Div(
                fh.Div(
                    label_span,  # Use the properly styled label span
                    cls="flex-1",  # Take up remaining space
                ),
                fh.Div(
                    *action_buttons,
                    cls="flex-shrink-0 flex items-center gap-1 px-1",  # Don't shrink, add horizontal padding
                    onclick="event.stopPropagation();",  # Isolate the action buttons area
                ),
                cls="flex items-center",
            )
        else:
            # If no action buttons, just use the styled label
            title_base = fh.Div(
                label_span,  # Use the properly styled label span
                cls="flex items-center",
            )

        # Apply metrics decoration to title (bullet only, no border)
        title_with_metrics = self._decorate_metrics(
            title_base, self.metric_entry, scope=DecorationScope.BULLET
        )

        # Add copy button AFTER metrics decoration
        copy_button = self._render_comparison_copy_button()
        if copy_button:
            # Wrap title (with metrics) and copy button together
            title_component = fh.Div(
                title_with_metrics,
                copy_button,
                cls="flex items-center justify-between gap-2 w-full",
            )
        else:
            title_component = title_with_metrics

        # Compute border color for the wrapper accordion
        border_color = self._metric_border_color(self.metric_entry)
        li_style = {}
        if border_color:
            li_style["style"] = (
                f"border-left: 4px solid {border_color}; padding-left: 0.25rem;"
            )

        # Create the wrapper AccordionItem that contains all the list items
        list_content = self.render_input()

        # Define unique IDs for the wrapper accordion
        wrapper_item_id = f"{self.field_name}_wrapper_item"
        wrapper_accordion_id = f"{self.field_name}_wrapper_accordion"

        # Create the wrapper AccordionItem
        wrapper_accordion_item = mui.AccordionItem(
            title_component,  # Title component with label and refresh icon
            list_content,  # Content component (the list items)
            open=True,  # Open by default
            li_kwargs={
                "id": wrapper_item_id,
                **li_style,
            },
            cls=spacing("outer_margin", self.spacing),
        )

        # Wrap in an Accordion container
        accordion_cls = spacing_many(
            ["accordion_divider", "accordion_content"], self.spacing
        )
        wrapper_accordion = mui.Accordion(
            wrapper_accordion_item,
            id=wrapper_accordion_id,
            multiple=True,
            collapsible=True,
            cls=f"{accordion_cls} w-full".strip(),
        )

        return wrapper_accordion

    def render_input(self) -> FT:
        """
        Render a list of items with add/delete/move capabilities

        Returns:
            A component containing the list items and controls
        """
        # Initialize the value as an empty list, ensuring it's always a list
        items = [] if not isinstance(self.value, list) else self.value

        annotation = getattr(self.field_info, "annotation", None)
        item_type = None  # Initialize here to avoid UnboundLocalError

        # Handle Optional[List[...]] by unwrapping the Optional first
        base_annotation = _get_underlying_type_if_optional(annotation)

        if (
            base_annotation is not None
            and hasattr(base_annotation, "__origin__")
            and base_annotation.__origin__ is list
        ):
            item_type = base_annotation.__args__[0]

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

        # Container for list items using hierarchical field path
        container_id = self._container_id()

        # Use mui.Accordion component
        accordion_cls = spacing_many(
            ["inner_gap_small", "accordion_content", "accordion_divider"], self.spacing
        )
        accordion = mui.Accordion(
            *item_elements,
            id=container_id,
            multiple=True,  # Allow multiple items to be open at once
            collapsible=True,  # Make it collapsible
            cls=accordion_cls.strip(),  # Add space between items and accordion content styling
        )

        # Empty state message if no items
        empty_state = ""
        if not items:
            # Use hierarchical path for URL
            add_url = (
                f"/form/{self._form_name}/list/add/{self._list_path}"
                if self._form_name
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

            # Differentiate message for Optional[List] vs required List
            if self.is_optional:
                empty_message = (
                    "No items in this optional list. Click 'Add Item' if needed."
                )
            else:
                empty_message = (
                    "No items in this required list. Click 'Add Item' to create one."
                )

            empty_state = mui.Alert(
                fh.Div(
                    mui.UkIcon("info", cls="mr-2"),
                    empty_message,
                    mui.Button("Add Item", **add_button_attrs),
                    cls="flex flex-col items-start",
                ),
                cls=mui.AlertT.info,
            )

        # Return the complete component (minimal styling since it's now wrapped in an accordion)
        t = self.spacing
        return fh.Div(
            accordion,
            empty_state,
            cls=f"{spacing('padding', t)}".strip(),  # Keep padding for content, remove border and margin
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

            # Look up metrics for this list item
            item_path_segments = self.field_path + [str(idx)]
            path_string = _build_path_string_static(item_path_segments)
            item_metric_entry: Optional[MetricEntry] = (
                self.metrics_dict.get(path_string) if self.metrics_dict else None
            )

            # Check if it's a simple type or BaseModel
            is_model = hasattr(item_type, "model_fields")

            # --- Generate item summary for the accordion title ---
            # Create a user-friendly display index
            if isinstance(idx, str) and idx.startswith("new_"):
                # Get the type name for new items
                if is_model:
                    # For BaseModel types, use the class name
                    type_name = item_type.__name__
                else:
                    # For simple types, use a friendly name
                    type_name_map = {
                        str: "String",
                        int: "Number",
                        float: "Number",
                        bool: "Boolean",
                        date: "Date",
                        time: "Time",
                    }
                    type_name = type_name_map.get(
                        item_type,
                        item_type.__name__
                        if hasattr(item_type, "__name__")
                        else str(item_type),
                    )

                display_idx = f"New {type_name}"
            else:
                display_idx = str(idx)

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
                        item_summary_text = f"{display_idx}: {str(model_for_display)}"
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
                item_summary_text = f"{display_idx}: {str(item)}"

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
                        spacing=self.spacing,  # Propagate spacing
                        field_path=self.field_path
                        + [str(idx)],  # Propagate path with index
                        form_name=self.explicit_form_name,  # Propagate form name
                        metric_entry=None,  # Let auto-lookup handle it
                        metrics_dict=self.metrics_dict,  # Pass down the metrics dict
                        refresh_endpoint_override=self._refresh_endpoint_override,  # Propagate refresh override
                        keep_skip_json_pathset=self._keep_skip_json_pathset,  # Propagate keep paths
                        comparison_copy_enabled=self._cmp_copy_enabled,  # Propagate comparison copy settings
                        comparison_copy_target=self._cmp_copy_target,
                        comparison_name=self._cmp_name,
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
                                dv = get_default(nested_field_info)
                                if dv is not _UNSET:
                                    nested_field_value = dv
                                else:
                                    ann = nested_field_info.annotation
                                    base_ann = get_origin(ann) or ann
                                    if isinstance(base_ann, type) and issubclass(
                                        base_ann, BaseModel
                                    ):
                                        nested_field_value = default_dict_for_model(
                                            base_ann
                                        )
                                    else:
                                        nested_field_value = default_for_annotation(ann)

                            # Skip SkipJsonSchema fields unless explicitly kept
                            if _is_skip_json_schema_field(
                                nested_field_info
                            ) and not self._is_kept_skip_field(
                                self.field_path + [nested_field_name]
                            ):
                                continue

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
                                field_path=self.field_path
                                + [
                                    str(idx),
                                    nested_field_name,
                                ],  # Propagate path with index
                                form_name=self.explicit_form_name,  # Propagate form name
                                metric_entry=None,  # Let auto-lookup handle it
                                metrics_dict=self.metrics_dict,  # Pass down the metrics dict
                                refresh_endpoint_override=self._refresh_endpoint_override,  # Propagate refresh override
                                keep_skip_json_pathset=self._keep_skip_json_pathset,  # Propagate keep paths
                                comparison_copy_enabled=self._cmp_copy_enabled,  # Propagate comparison copy settings
                                comparison_copy_target=self._cmp_copy_target,
                                comparison_name=self._cmp_name,
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
                    field_path=self.field_path
                    + [str(idx)],  # Propagate path with index
                    form_name=self.explicit_form_name,  # Propagate form name
                    metric_entry=None,  # Let auto-lookup handle it
                    metrics_dict=self.metrics_dict,  # Pass down the metrics dict
                    refresh_endpoint_override=self._refresh_endpoint_override,  # Propagate refresh override
                )
                input_element = simple_renderer.render_input()
                wrapper = fh.Div(input_element)
                # Don't apply metrics decoration here - the card border handles it
                item_content_elements.append(wrapper)

            # --- Create action buttons with form-specific URLs ---
            # Generate HTMX endpoints using hierarchical paths
            delete_url = (
                f"/form/{self._form_name}/list/delete/{self._list_path}"
                if self._form_name
                else f"/list/delete/{self.field_name}"
            )

            add_url = (
                f"/form/{self._form_name}/list/add/{self._list_path}"
                if self._form_name
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
            title_span = fh.Span(
                item_summary_text, cls="text-gray-700 font-medium pl-3"
            )

            # Apply metrics decoration to the title span FIRST (bullet only)
            title_with_metrics = self._decorate_metrics(
                title_span, item_metric_entry, scope=DecorationScope.BULLET
            )

            # Get copy button for this specific list item (if enabled) - add AFTER metrics
            # Create a temporary renderer context with this item's path
            if self._cmp_copy_enabled and self._cmp_copy_target and self._cmp_name:
                # Build the path for this specific item
                item_path_for_copy = self.field_path + [str(idx)]
                item_path_string = _build_path_string_static(item_path_for_copy)
                arrow = (
                    "arrow-left" if self._cmp_copy_target == "left" else "arrow-right"
                )
                tooltip_text = f"Copy item to {self._cmp_copy_target}"

                # Note: Copy button is never disabled, even in disabled forms
                # Pure JS copy: Bypass HTMX entirely to avoid accordion collapse
                item_copy_button = mui.Button(
                    mui.UkIcon(arrow, cls="w-4 h-4 text-gray-500 hover:text-blue-600"),
                    type="button",
                    onclick=f"window.fhpfPerformCopy('{item_path_string}', '{self.prefix}', '{self._cmp_copy_target}'); return false;",
                    uk_tooltip=tooltip_text,
                    cls="uk-button-text uk-button-small flex-shrink-0",
                    style="all: unset; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; padding: 0.25rem; min-width: 1.5rem;",
                )

                # Wrap title (with metrics) and copy button together
                title_component = fh.Div(
                    title_with_metrics,
                    item_copy_button,
                    cls="flex items-center justify-between gap-2 w-full",
                )
            else:
                title_component = title_with_metrics

            # Prepare li attributes with optional border styling
            li_attrs = {"id": full_card_id}

            # Add colored border based on metrics if enabled
            if self.show_item_border and item_metric_entry:
                border_color = self._metric_border_color(item_metric_entry)
                if border_color:
                    li_attrs["style"] = (
                        f"border-left: 4px solid {border_color}; padding-left: 0.25rem;"
                    )

            # Build card classes using spacing tokens
            card_cls_parts = ["uk-card"]
            if self.spacing == SpacingTheme.NORMAL:
                card_cls_parts.append("uk-card-default")

            # Add spacing-based classes
            card_spacing_cls = spacing_many(
                ["accordion_item_margin", "card_border_thin"], self.spacing
            )
            if card_spacing_cls:
                card_cls_parts.append(card_spacing_cls)

            card_cls = " ".join(card_cls_parts)

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

            # Still try to get metrics for error items
            item_path_segments = self.field_path + [str(idx)]
            path_string = _build_path_string_static(item_path_segments)

            title_component = fh.Span(
                f"Error in item {idx}", cls="text-red-600 font-medium pl-3"
            )

            # Apply metrics decoration even to error items (bullet only)
            title_component = self._decorate_metrics(
                title_component, item_metric_entry, scope=DecorationScope.BULLET
            )

            content_component = mui.Alert(
                f"Error rendering item {idx}: {str(e)}", cls=mui.AlertT.error
            )

            li_attrs = {"id": f"{self.field_name}_{idx}_error_card"}

            # Add colored border for error items too if metrics present
            if self.show_item_border and item_metric_entry:
                border_color = self._metric_border_color(item_metric_entry)
                if border_color:
                    li_attrs["style"] = (
                        f"border-left: 4px solid {border_color}; padding-left: 0.25rem;"
                    )

            # Wrap error component in a div with consistent padding
            t = self.spacing
            content_wrapper = fh.Div(content_component, cls=spacing("card_body_pad", t))

            # Build card classes using spacing tokens
            card_cls_parts = ["uk-card"]
            if self.spacing == SpacingTheme.NORMAL:
                card_cls_parts.append("uk-card-default")

            # Add spacing-based classes
            card_spacing_cls = spacing_many(
                ["accordion_item_margin", "card_border_thin"], self.spacing
            )
            if card_spacing_cls:
                card_cls_parts.append(card_spacing_cls)

            card_cls = " ".join(card_cls_parts)

            return mui.AccordionItem(
                title_component,  # Title as first positional argument
                content_wrapper,  # Wrapped content element
                cls=card_cls,  # Use theme-aware card classes
                li_kwargs=li_attrs,  # Pass remaining li attributes without cls
            )
