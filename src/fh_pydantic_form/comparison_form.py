"""
ComparisonForm - Side-by-side form comparison with metrics visualization

This module provides a meta-renderer that displays two PydanticForm instances
side-by-side with visual comparison feedback and synchronized accordion states.
"""

import json
import logging
import re
from copy import deepcopy
from typing import (
    Any,
    cast,
    Dict,
    Generic,
    List,
    Literal,
    Optional,
    Type,
    TypeVar,
    Union,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel

from fh_pydantic_form.constants import (
    ATTR_COMPARE_GRID,
    ATTR_COMPARE_NAME,
    ATTR_LEFT_PREFIX,
    ATTR_RIGHT_PREFIX,
)
from fh_pydantic_form.form_renderer import PydanticForm
from fh_pydantic_form.js_assets import load_js_asset
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import (
    MetricEntry,
    MetricsDict,
    _is_skip_json_schema_field,
)

logger = logging.getLogger(__name__)

# TypeVar for generic model typing
ModelType = TypeVar("ModelType", bound=BaseModel)
Side = Literal["left", "right"]


def comparison_form_js():
    """JavaScript for comparison: sync accordions and handle JS-only copy operations."""
    return fh.Script(load_js_asset("comparison-form.js"))


class ComparisonForm(Generic[ModelType]):
    """
    Meta-renderer for side-by-side form comparison with metrics visualization

    This class creates a two-column layout with synchronized accordions and
    visual comparison feedback (colors, tooltips, metric badges).

    The ComparisonForm is a view-only composition helper; state management
    lives in the underlying PydanticForm instances.
    """

    def __init__(
        self,
        name: str,
        left_form: PydanticForm[ModelType],
        right_form: PydanticForm[ModelType],
        *,
        left_label: str = "Reference",
        right_label: str = "Generated",
        copy_left: bool = False,
        copy_right: bool = False,
        template_name: Optional[str] = None,
    ):
        """
        Initialize the comparison form

        Args:
            name: Unique name for this comparison form
            left_form: Pre-constructed PydanticForm for left column
            right_form: Pre-constructed PydanticForm for right column
            left_label: Label for left column
            right_label: Label for right column
            copy_left: If True, show copy buttons in right column to copy to left
            copy_right: If True, show copy buttons in left column to copy to right
            template_name: Optional template name for routing refresh/reset actions.
                If provided, routes will be registered and URLs generated using this name
                instead of `name`. This allows multiple ComparisonForm instances to share
                the same registered routes (same pattern as PydanticForm.template_name).

        Raises:
            ValueError: If the two forms are not based on the same model class
        """
        # Validate that both forms use the same model
        if left_form.model_class is not right_form.model_class:
            raise ValueError(
                f"Both forms must be based on the same model class. "
                f"Got {left_form.model_class.__name__} and {right_form.model_class.__name__}"
            )

        self.name = name
        self.template_name = template_name or name
        self.left_form = left_form
        self.right_form = right_form
        self.model_class = left_form.model_class  # Convenience reference
        self.left_label = left_label
        self.right_label = right_label
        self.copy_left = copy_left
        self.copy_right = copy_right

        # Use spacing from left form (or could add override parameter if needed)
        self.spacing = left_form.spacing

    def _get_field_path_string(self, field_path: List[str]) -> str:
        """Convert field path list to dot-notation string for comparison lookup"""
        return ".".join(field_path)

    def _split_path(self, path: str) -> List[Union[str, int]]:
        """
        Split a dot/bracket path string into segments.

        Examples:
            "author.name" -> ["author", "name"]
            "addresses[0].street" -> ["addresses", 0, "street"]
            "experience[2].company" -> ["experience", 2, "company"]

        Args:
            path: Dot/bracket notation path string

        Returns:
            List of path segments (strings and ints)
        """
        _INDEX = re.compile(r"(.+?)\[(\d+)\]$")
        parts: List[Union[str, int]] = []

        for segment in path.split("."):
            m = _INDEX.match(segment)
            if m:
                # Segment has bracket notation like "name[3]"
                parts.append(m.group(1))
                parts.append(int(m.group(2)))
            else:
                parts.append(segment)

        return parts

    def _get_by_path(self, data: Dict[str, Any], path: str) -> tuple[bool, Any]:
        """
        Get a value from nested dict/list structure by path.

        Args:
            data: The data structure to traverse
            path: Dot/bracket notation path string

        Returns:
            Tuple of (found, value) where found is True if path exists, False otherwise
        """
        cur = data
        for seg in self._split_path(path):
            if isinstance(seg, int):
                if not isinstance(cur, list) or seg >= len(cur):
                    return (False, None)
                cur = cur[seg]
            else:
                if not isinstance(cur, dict) or seg not in cur:
                    return (False, None)
                cur = cur[seg]
        return (True, deepcopy(cur))

    def _set_by_path(self, data: Dict[str, Any], path: str, value: Any) -> None:
        """
        Set a value in nested dict/list structure by path, creating intermediates.

        Args:
            data: The data structure to modify
            path: Dot/bracket notation path string
            value: The value to set
        """
        cur = data
        parts = self._split_path(path)

        for i, seg in enumerate(parts):
            is_last = i == len(parts) - 1

            if is_last:
                # Set the final value
                if isinstance(seg, int):
                    if not isinstance(cur, list):
                        raise ValueError("Cannot set list index on non-list parent")
                    # Extend list if needed
                    while len(cur) <= seg:
                        cur.append(None)
                    cur[seg] = deepcopy(value)
                else:
                    if not isinstance(cur, dict):
                        raise ValueError("Cannot set dict key on non-dict parent")
                    cur[seg] = deepcopy(value)
            else:
                # Navigate or create intermediate containers
                nxt = parts[i + 1]

                if isinstance(seg, int):
                    if not isinstance(cur, list):
                        raise ValueError("Non-list where list expected")
                    # Extend list if needed
                    while len(cur) <= seg:
                        cur.append({} if isinstance(nxt, str) else [])
                    cur = cur[seg]
                else:
                    if seg not in cur or not isinstance(cur[seg], (dict, list)):
                        # Create appropriate container type
                        cur[seg] = {} if isinstance(nxt, str) else []
                    cur = cur[seg]

    def _render_column(
        self,
        *,
        form: PydanticForm[ModelType],
        header_label: str,
        start_order: int,
        wrapper_id: str,
        side: Side,
    ) -> FT:
        """
        Render a single column with CSS order values for grid alignment

        Args:
            form: The PydanticForm instance for this column
            header_label: Label for the column header
            start_order: Starting order value (0 for left, 1 for right)
            wrapper_id: ID for the wrapper div

        Returns:
            A div with class="contents" containing ordered grid items
        """
        # Header with order
        cells = [
            fh.Div(
                fh.H3(header_label, cls="text-lg font-semibold text-gray-700"),
                cls="pb-2 border-b",
                style=f"order:{start_order}",
            )
        ]

        # Start at order + 2, increment by 2 for each field
        order_idx = start_order + 2

        # Create renderers for each field
        registry = FieldRendererRegistry()

        for field_name, field_info in self.model_class.model_fields.items():
            # Skip excluded fields
            if field_name in (form.exclude_fields or []):
                continue

            # Skip SkipJsonSchema fields unless explicitly kept
            if _is_skip_json_schema_field(field_info) and not form._is_kept_skip_field(
                [field_name]
            ):
                continue

            # Get value from form
            value = form.values_dict.get(field_name)

            # Get path string for data-path attribute
            path_str = field_name

            # Get renderer class
            renderer_cls = registry.get_renderer(field_name, field_info)
            if not renderer_cls:
                from fh_pydantic_form.field_renderers import StringFieldRenderer

                renderer_cls = StringFieldRenderer

            # Determine comparison-specific refresh endpoint (use template_name for shared routes)
            comparison_refresh = f"/compare/{self.template_name}/{side}/refresh"

            # Get label color for this field if specified
            label_color = (
                form.label_colors.get(field_name)
                if hasattr(form, "label_colors")
                else None
            )

            # Determine comparison copy settings
            # Show copy buttons on the SOURCE form (the form you're copying FROM)
            is_left_column = side == "left"

            # If copy_left is enabled, show button on RIGHT form to copy TO left
            # If copy_right is enabled, show button on LEFT form to copy TO right
            if is_left_column:
                # This is the left form
                # Show copy button if we want to copy TO the right
                copy_feature_enabled = self.copy_right
                comparison_copy_target = "right" if copy_feature_enabled else None
                target_form = self.right_form
            else:
                # This is the right form
                # Show copy button if we want to copy TO the left
                copy_feature_enabled = self.copy_left
                comparison_copy_target = "left" if copy_feature_enabled else None
                target_form = self.left_form

            # Enable copy button if:
            # 1. The feature is enabled (copy_left or copy_right)
            # 2. The TARGET form is NOT disabled (you can't copy into a disabled/read-only form)
            comparison_copy_enabled = (
                copy_feature_enabled and not target_form.disabled
                if target_form
                else False
            )

            # Create renderer
            renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=value,
                prefix=form.base_prefix,
                disabled=form.disabled,
                spacing=form.spacing,
                field_path=[field_name],
                form_name=form.name,
                route_form_name=getattr(form, "template_name", form.name),
                label_color=label_color,  # Pass the label color if specified
                metrics_dict=form.metrics_dict,  # Use form's own metrics
                keep_skip_json_pathset=form._keep_skip_json_pathset,  # Pass keep_skip_json configuration
                refresh_endpoint_override=comparison_refresh,  # Pass comparison-specific refresh endpoint
                comparison_copy_enabled=comparison_copy_enabled,
                comparison_copy_target=comparison_copy_target,
                comparison_name=self.name,
            )

            # Render with data-path and order
            cells.append(
                fh.Div(
                    renderer.render(),
                    cls="",
                    **{"data-path": path_str, "style": f"order:{order_idx}"},
                )
            )

            order_idx += 2

        # Return wrapper with display: contents
        return fh.Div(*cells, id=wrapper_id, cls="contents")

    def render_inputs(self) -> FT:
        """
        Render the comparison form with side-by-side layout

        Returns:
            A FastHTML component with CSS Grid layout
        """
        # Render left column with wrapper
        left_wrapper = self._render_column(
            form=self.left_form,
            header_label=self.left_label,
            start_order=0,
            wrapper_id=f"{self.left_form.name}-inputs-wrapper",
            side="left",
        )

        # Render right column with wrapper
        right_wrapper = self._render_column(
            form=self.right_form,
            header_label=self.right_label,
            start_order=1,
            wrapper_id=f"{self.right_form.name}-inputs-wrapper",
            side="right",
        )

        # Create the grid container with both wrappers
        grid_container = fh.Div(
            left_wrapper,
            right_wrapper,
            cls="fhpf-compare grid grid-cols-2 gap-x-6 gap-y-2 items-start",
            id=f"{self.name}-comparison-grid",
            **{
                ATTR_COMPARE_GRID: "true",
                ATTR_COMPARE_NAME: self.name,
                ATTR_LEFT_PREFIX: self.left_form.base_prefix,
                ATTR_RIGHT_PREFIX: self.right_form.base_prefix,
            },
        )

        # Emit prefix globals for the copy registry
        prefix_script = fh.Script(f"""
window.__fhpfComparisonPrefixes = window.__fhpfComparisonPrefixes || {{}};
window.__fhpfComparisonPrefixes[{json.dumps(self.name)}] = {{
  left: {json.dumps(self.left_form.base_prefix)},
  right: {json.dumps(self.right_form.base_prefix)}
}};
window.__fhpfLeftPrefix = {json.dumps(self.left_form.base_prefix)};
window.__fhpfRightPrefix = {json.dumps(self.right_form.base_prefix)};
""")

        return fh.Div(prefix_script, grid_container, cls="w-full")

    def register_routes(self, app):
        """
        Register HTMX routes for the comparison form

        Args:
            app: FastHTML app instance
        """
        # Register individual form routes (for list manipulation)
        self.left_form.register_routes(app)
        self.right_form.register_routes(app)

        # Register comparison-specific reset/refresh routes
        def create_reset_handler(
            form: PydanticForm[ModelType],
            side: Side,
            label: str,
        ):
            """Factory function to create reset handler with proper closure"""

            async def handler(req):
                """Reset one side of the comparison form"""
                # Check for dynamic form name override
                form_data = await req.form()
                form_name_override = form_data.get("fhpf_form_name")
                if not form_name_override:
                    form_name_override = req.query_params.get("fhpf_form_name")

                # Use cloned form if name differs (dynamic form scenario)
                if form_name_override and form_name_override != form.name:
                    effective_form = form._clone_with_name(form_name_override)
                else:
                    effective_form = form

                # Reset the form state
                await effective_form.handle_reset_request()

                # Render the entire column with proper ordering
                start_order = 0 if side == "left" else 1
                wrapper = self._render_column(
                    form=effective_form,
                    header_label=label,
                    start_order=start_order,
                    wrapper_id=f"{effective_form.name}-inputs-wrapper",
                    side=side,
                )
                return wrapper

            return handler

        def create_refresh_handler(
            form: PydanticForm[ModelType],
            side: Side,
            label: str,
        ):
            """Factory function to create refresh handler with proper closure"""

            async def handler(req):
                """Refresh one side of the comparison form"""
                # Check for dynamic form name override
                form_data = await req.form()
                form_name_override = form_data.get("fhpf_form_name")
                if not form_name_override:
                    form_name_override = req.query_params.get("fhpf_form_name")

                # Use cloned form if name differs (dynamic form scenario)
                if form_name_override and form_name_override != form.name:
                    effective_form = form._clone_with_name(form_name_override)
                    effective_form._handle_refresh_with_form_data(dict(form_data))
                else:
                    effective_form = form
                    effective_form._handle_refresh_with_form_data(dict(form_data))

                # Render the entire column with proper ordering
                start_order = 0 if side == "left" else 1
                wrapper = self._render_column(
                    form=effective_form,
                    header_label=label,
                    start_order=start_order,
                    wrapper_id=f"{effective_form.name}-inputs-wrapper",
                    side=side,
                )
                return wrapper

            return handler

        for side, form, label in [
            ("left", self.left_form, self.left_label),
            ("right", self.right_form, self.right_label),
        ]:
            side = cast(Side, side)
            assert form is not None

            # Reset route (use template_name for shared routes)
            reset_path = f"/compare/{self.template_name}/{side}/reset"
            reset_handler = create_reset_handler(form, side, label)
            app.route(reset_path, methods=["POST"])(reset_handler)

            # Refresh route (use template_name for shared routes)
            refresh_path = f"/compare/{self.template_name}/{side}/refresh"
            refresh_handler = create_refresh_handler(form, side, label)
            app.route(refresh_path, methods=["POST"])(refresh_handler)

        # Note: Copy routes are not needed - copy is handled entirely in JavaScript
        # via window.fhpfPerformCopy() function called directly from onclick handlers

    def form_wrapper(self, content: FT, form_id: Optional[str] = None) -> FT:
        """
        Wrap the comparison content in a form element with proper ID

        Args:
            content: The form content to wrap
            form_id: Optional form ID (defaults to {name}-comparison-form)

        Returns:
            A form element containing the content
        """
        form_id = form_id or f"{self.name}-comparison-form"
        wrapper_id = f"{self.name}-comparison-wrapper"

        # Note: Removed hx_include="closest form" since the wrapper only contains foreign forms
        return mui.Form(
            fh.Div(content, id=wrapper_id),
            id=form_id,
        )

    def _button_helper(self, *, side: str, action: str, text: str, **kwargs) -> FT:
        """
        Helper method to create buttons that target comparison-specific routes

        Args:
            side: "left" or "right"
            action: "reset" or "refresh"
            text: Button text
            **kwargs: Additional button attributes

        Returns:
            A button component
        """
        form = self.left_form if side == "left" else self.right_form

        # For shared template routes, server-side reset cannot reliably restore
        # per-instance initial values. Prefer the client-side snapshot reset,
        # consistent with PydanticForm.reset_button() for dynamic forms.
        if action == "reset" and self.template_name != self.name:
            confirm_message = (
                "Are you sure you want to reset the form to its initial values? "
                "Any unsaved changes will be lost."
            )
            wrapper_js = json.dumps(f"{form.name}-inputs-wrapper")
            prefix_js = json.dumps(form.base_prefix)
            confirm_js = json.dumps(confirm_message)
            button_attrs = {
                "type": "button",
                "onclick": (
                    "return window.fhpfResetForm ? "
                    f"window.fhpfResetForm({wrapper_js}, {prefix_js}, {confirm_js}) : false;"
                ),
                "uk_tooltip": "Reset the form fields to their original values",
                "cls": mui.ButtonT.destructive,
            }
            button_attrs.update(kwargs)
            return mui.Button(mui.UkIcon("history"), text, **button_attrs)

        # Create prefix-based selector
        prefix_selector = f"form [name^='{form.base_prefix}']"

        # Set default attributes (use template_name for shared routes)
        kwargs.setdefault("hx_post", f"/compare/{self.template_name}/{side}/{action}")
        kwargs.setdefault("hx_target", f"#{form.name}-inputs-wrapper")
        kwargs.setdefault("hx_swap", "innerHTML")
        kwargs.setdefault("hx_include", prefix_selector)
        kwargs.setdefault("hx_preserve", "scroll")

        # Send form name when routing via templates so the handler can parse the
        # correct prefix / render the correct wrapper IDs.
        should_send_form_name = False
        if self.template_name != self.name:
            should_send_form_name = True
        else:
            form_template_name = getattr(form, "template_name", None)
            if form_template_name and form_template_name != form.name:
                should_send_form_name = True

        if should_send_form_name:
            existing_vals = kwargs.get("hx_vals")
            if existing_vals:
                try:
                    merged = dict(json.loads(existing_vals))
                except Exception:
                    merged = {}
                merged.setdefault("fhpf_form_name", form.name)
                kwargs["hx_vals"] = json.dumps(merged)
            else:
                kwargs["hx_vals"] = json.dumps({"fhpf_form_name": form.name})

        # Delegate to the underlying form's button method
        button_method = getattr(form, f"{action}_button")
        return button_method(text, **kwargs)

    def left_reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a reset button for the left form"""
        return self._button_helper(
            side="left", action="reset", text=text or "↩️ Reset Left", **kwargs
        )

    def left_refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a refresh button for the left form"""
        return self._button_helper(
            side="left", action="refresh", text=text or "🔄 Refresh Left", **kwargs
        )

    def right_reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a reset button for the right form"""
        return self._button_helper(
            side="right", action="reset", text=text or "↩️ Reset Right", **kwargs
        )

    def right_refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """Create a refresh button for the right form"""
        return self._button_helper(
            side="right", action="refresh", text=text or "🔄 Refresh Right", **kwargs
        )


def simple_diff_metrics(
    left_data: BaseModel | Dict[str, Any],
    right_data: BaseModel | Dict[str, Any],
    model_class: Type[BaseModel],
) -> MetricsDict:
    """
    Simple helper to generate metrics based on equality

    Args:
        left_data: Reference data
        right_data: Data to compare
        model_class: Model class for structure

    Returns:
        MetricsDict with simple equality-based metrics
    """
    metrics_dict = {}

    # Convert to dicts if needed
    if hasattr(left_data, "model_dump"):
        left_dict = left_data.model_dump()
    else:
        left_dict = left_data or {}

    if hasattr(right_data, "model_dump"):
        right_dict = right_data.model_dump()
    else:
        right_dict = right_data or {}

    # Compare each field
    for field_name in model_class.model_fields:
        left_val = left_dict.get(field_name)
        right_val = right_dict.get(field_name)

        if left_val == right_val:
            metrics_dict[field_name] = MetricEntry(
                metric=1.0, color="green", comment="Values match exactly"
            )
        elif left_val is None or right_val is None:
            metrics_dict[field_name] = MetricEntry(
                metric=0.0, color="orange", comment="One value is missing"
            )
        else:
            # Try to compute similarity for strings
            if isinstance(left_val, str) and isinstance(right_val, str):
                # Simple character overlap ratio
                common = sum(1 for a, b in zip(left_val, right_val) if a == b)
                max_len = max(len(left_val), len(right_val))
                similarity = common / max_len if max_len > 0 else 0

                metrics_dict[field_name] = MetricEntry(
                    metric=round(similarity, 2),
                    comment=f"String similarity: {similarity:.0%}",
                )
            else:
                metrics_dict[field_name] = MetricEntry(
                    metric=0.0,
                    comment=f"Different values: {left_val} vs {right_val}",
                )

    return metrics_dict
