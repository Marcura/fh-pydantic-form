"""
ComparisonForm - Side-by-side form comparison with metrics visualization

This module provides a meta-renderer that displays two PydanticForm instances
side-by-side with visual comparison feedback and synchronized accordion states.
"""

import logging
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

from fh_pydantic_form.field_renderers import BaseFieldRenderer
from fh_pydantic_form.form_renderer import PydanticForm
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import ComparisonMap, ComparisonMetric
from fh_pydantic_form.ui_style import SpacingTheme, SpacingValue, _normalize_spacing

logger = logging.getLogger(__name__)

# TypeVar for generic model typing
ModelType = TypeVar("ModelType", bound=BaseModel)


def comparison_form_js():
    """JavaScript for comparison: sync top-level and list accordions."""
    return fh.Script("""
(function initComparisonSync(){
  // 1) Wait until UIkit and its util are available
  if (!window.UIkit || !UIkit.util) {
    return setTimeout(initComparisonSync, 50);
  }

  // 2) Sync top-level accordions (BaseModelFieldRenderer)
  UIkit.util.on(
    document,
    'show hide',                  // UIkit fires plain 'show'/'hide'
    'ul[uk-accordion] > li',      // only the top-level items
    mirrorTopLevel
  );

  function mirrorTopLevel(ev) {
    const sourceLi = ev.target.closest('li');
    if (!sourceLi) return;

    // Find our grid-cell wrapper (both left & right share the same data-path)
    const cell = sourceLi.closest('[data-path]');
    if (!cell) return;
    const path = cell.dataset.path;

    // Determine index of this <li> inside its <ul>
    const idx     = Array.prototype.indexOf.call(
      sourceLi.parentElement.children,
      sourceLi
    );
    const opening = ev.type === 'show';

    // Mirror on the other side
    document
      .querySelectorAll(`[data-path="${path}"]`)
      .forEach(peerCell => {
        if (peerCell === cell) return;

        const peerAcc = peerCell.querySelector('ul[uk-accordion]');
        if (!peerAcc || idx >= peerAcc.children.length) return;

        const peerLi      = peerAcc.children[idx];
        const peerContent = peerLi.querySelector('.uk-accordion-content');

        if (opening) {
          peerLi.classList.add('uk-open');
          if (peerContent) {
            peerContent.hidden = false;
            peerContent.style.height = 'auto';
          }
        } else {
          peerLi.classList.remove('uk-open');
          if (peerContent) {
            peerContent.hidden = true;
          }
        }
      });
  }

  // 3) Wrap the list-toggle so ListFieldRenderer accordions sync too
  if (typeof window.toggleListItems === 'function' && !window.__listSyncWrapped) {
    // guard to only wrap once
    window.__listSyncWrapped = true;
    const originalToggle = window.toggleListItems;

    window.toggleListItems = function(containerId) {
      // a) Toggle this column first
      originalToggle(containerId);

      // b) Find the enclosing data-path
      const container = document.getElementById(containerId);
      if (!container) return;
      const cell = container.closest('[data-path]');
      if (!cell) return;
      const path = cell.dataset.path;

      // c) Find the peer's list-container by suffix match
      document
        .querySelectorAll(`[data-path="${path}"]`)
        .forEach(peerCell => {
          if (peerCell === cell) return;

          // look up any [id$="_items_container"]
          const peerContainer = peerCell.querySelector('[id$="_items_container"]');
          if (peerContainer) {
            originalToggle(peerContainer.id);
          }
        });
    };
  }
})();
""")


class ComparisonForm(Generic[ModelType]):
    """
    Meta-renderer for side-by-side form comparison with metrics visualization

    This class creates a two-column layout with synchronized accordions and
    visual comparison feedback (colors, tooltips, metric badges).
    """

    def __init__(
        self,
        name: str,
        model_class: Type[ModelType],
        left_initial: Optional[Union[ModelType, Dict[str, Any]]] = None,
        right_initial: Optional[Union[ModelType, Dict[str, Any]]] = None,
        comparison: Optional[ComparisonMap] = None,
        disabled_left: bool = False,
        disabled_right: bool = False,
        left_label: str = "Reference",
        right_label: str = "Generated",
        spacing: SpacingValue = SpacingTheme.NORMAL,
        exclude_fields: Optional[List[str]] = None,
    ):
        """
        Initialize the comparison form

        Args:
            name: Unique name for this comparison form
            model_class: The Pydantic model class to render
            left_initial: Initial values for left form
            right_initial: Initial values for right form
            comparison: Mapping of field paths to comparison metrics
            disabled_left: Whether left form should be disabled
            disabled_right: Whether right form should be disabled
            left_label: Label for left column
            right_label: Label for right column
            spacing: Spacing theme to use
            exclude_fields: Fields to exclude from rendering
        """
        self.name = name
        self.model_class = model_class
        self.comparison = comparison or {}
        self.left_label = left_label
        self.right_label = right_label
        self.spacing = _normalize_spacing(spacing)

        # Create the two inner forms
        self.left_form = PydanticForm(
            form_name=f"{name}_left",
            model_class=model_class,
            initial_values=left_initial,
            disabled=disabled_left,
            spacing=spacing,
            exclude_fields=exclude_fields,
        )

        self.right_form = PydanticForm(
            form_name=f"{name}_right",
            model_class=model_class,
            initial_values=right_initial,
            disabled=disabled_right,
            spacing=spacing,
            exclude_fields=exclude_fields,
        )

    def _get_field_path_string(self, field_path: List[str]) -> str:
        """Convert field path list to dot-notation string for comparison lookup"""
        return ".".join(field_path)

    def _create_field_pairs(
        self,
    ) -> List[Tuple[str, BaseFieldRenderer, BaseFieldRenderer]]:
        """
        Create pairs of renderers (left, right) for each field path

        Returns:
            List of (path_string, left_renderer, right_renderer) tuples
        """
        pairs = []
        registry = FieldRendererRegistry()

        # Walk through model fields to create renderer pairs
        for field_name, field_info in self.model_class.model_fields.items():
            # Skip excluded fields
            if field_name in (self.left_form.exclude_fields or []):
                continue

            # Get values from each form
            left_value = self.left_form.values_dict.get(field_name)
            right_value = self.right_form.values_dict.get(field_name)

            # Get the path string for comparison lookup
            path_str = field_name
            comparison_metric = self.comparison.get(path_str)

            # Get renderer class
            renderer_cls = registry.get_renderer(field_name, field_info)
            if not renderer_cls:
                from fh_pydantic_form.field_renderers import StringFieldRenderer

                renderer_cls = StringFieldRenderer

            # Create left renderer
            left_renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=left_value,
                prefix=self.left_form.base_prefix,
                disabled=self.left_form.disabled,
                spacing=self.spacing,
                field_path=[field_name],
                form_name=self.left_form.name,
                comparison=comparison_metric,
                comparison_map=self.comparison,  # Pass the full comparison map
            )

            # Create right renderer
            right_renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=right_value,
                prefix=self.right_form.base_prefix,
                disabled=self.right_form.disabled,
                spacing=self.spacing,
                field_path=[field_name],
                form_name=self.right_form.name,
                comparison=comparison_metric,
                comparison_map=self.comparison,  # Pass the full comparison map
            )

            pairs.append((path_str, left_renderer, right_renderer))

        return pairs

    def render_inputs(self) -> FT:
        """
        Render the comparison form with side-by-side layout

        Returns:
            A FastHTML component with CSS Grid layout
        """
        # Column headers
        headers = [
            fh.Div(
                fh.H3(self.left_label, cls="text-lg font-semibold text-gray-700"),
                cls="pb-2 border-b",
            ),
            fh.Div(
                fh.H3(self.right_label, cls="text-lg font-semibold text-gray-700"),
                cls="pb-2 border-b",
            ),
        ]

        # Create field pairs and render them
        rows = headers.copy()

        for path_str, left_renderer, right_renderer in self._create_field_pairs():
            # Render each field and wrap with data-path
            left_rendered = left_renderer.render()
            right_rendered = right_renderer.render()

            # Add data-path attribute for accordion sync
            left_cell = fh.Div(left_rendered, cls="", **{"data-path": path_str})

            right_cell = fh.Div(right_rendered, cls="", **{"data-path": path_str})

            rows.extend([left_cell, right_cell])

        # Create the grid container
        grid_container = fh.Div(
            *rows,
            cls="fhpf-compare grid grid-cols-2 gap-x-6 gap-y-2 items-start",
            id=f"{self.name}-comparison-grid",
        )

        return fh.Div(grid_container, cls="w-full")

    def refresh_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """
        Create a refresh button that updates both forms

        Args:
            text: Optional button text
            **kwargs: Additional button attributes

        Returns:
            A button component that refreshes both forms
        """
        button_text = text if text is not None else " Refresh Comparison"

        # Create a wrapper div that will be replaced
        wrapper_id = f"{self.name}-comparison-wrapper"

        button_attrs = {
            "type": "button",
            "hx_post": f"/form/{self.name}/comparison/refresh",
            "hx_target": f"#{wrapper_id}",
            "hx_swap": "innerHTML",
            "hx_include": "closest form",
            "uk_tooltip": "Update both forms display",
            "cls": mui.ButtonT.secondary,
        }

        button_attrs.update(kwargs)

        return mui.Button(mui.UkIcon("refresh-ccw"), button_text, **button_attrs)

    def reset_button(self, text: Optional[str] = None, **kwargs) -> FT:
        """
        Create a reset button that resets both forms to initial values

        Args:
            text: Optional button text
            **kwargs: Additional button attributes

        Returns:
            A button component that resets both forms
        """
        button_text = text if text is not None else " Reset Both"

        wrapper_id = f"{self.name}-comparison-wrapper"

        button_attrs = {
            "type": "button",
            "hx_post": f"/form/{self.name}/comparison/reset",
            "hx_target": f"#{wrapper_id}",
            "hx_swap": "innerHTML",
            "hx_confirm": "Reset both forms to their initial values?",
            "uk_tooltip": "Reset both forms to original values",
            "cls": mui.ButtonT.destructive,
        }

        button_attrs.update(kwargs)

        return mui.Button(mui.UkIcon("history"), button_text, **button_attrs)

    def register_routes(self, app):
        """
        Register HTMX routes for the comparison form

        Args:
            app: FastHTML app instance
        """
        # Register routes for both inner forms
        self.left_form.register_routes(app)
        self.right_form.register_routes(app)

        # Register comparison-specific routes
        refresh_route = f"/form/{self.name}/comparison/refresh"
        reset_route = f"/form/{self.name}/comparison/reset"

        @app.route(refresh_route, methods=["POST"])
        async def handle_comparison_refresh(req):
            """Refresh both forms"""
            # Parse form data
            form_data = await req.form()
            form_dict = dict(form_data)

            # Update values in both forms by parsing their respective data
            try:
                left_parsed = self.left_form.parse(form_dict)
                right_parsed = self.right_form.parse(form_dict)

                # Create new comparison form with updated values
                temp_comparison = ComparisonForm(
                    name=self.name,
                    model_class=self.model_class,
                    left_initial=left_parsed,
                    right_initial=right_parsed,
                    comparison=self.comparison,
                    disabled_left=self.left_form.disabled,
                    disabled_right=self.right_form.disabled,
                    left_label=self.left_label,
                    right_label=self.right_label,
                    spacing=self.spacing,
                    exclude_fields=self.left_form.exclude_fields,
                )

                return temp_comparison.render_inputs()
            except Exception as e:
                logger.error(f"Error refreshing comparison form: {e}")
                return mui.Alert(
                    f"Error refreshing form: {str(e)}", cls=mui.AlertT.error
                )

        @app.route(reset_route, methods=["POST"])
        async def handle_comparison_reset(req):
            """Reset both forms to initial values"""
            # Reset to original values
            return self.render_inputs()

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

        return mui.Form(
            fh.Div(content, id=wrapper_id),
            id=form_id,
        )


def simple_diff_comparison(
    left_data: Union[BaseModel, Dict[str, Any]],
    right_data: Union[BaseModel, Dict[str, Any]],
    model_class: Type[BaseModel],
) -> ComparisonMap:
    """
    Simple helper to generate comparison metrics based on equality

    Args:
        left_data: Reference data
        right_data: Data to compare
        model_class: Model class for structure

    Returns:
        ComparisonMap with simple equality-based metrics
    """
    comparison_map = {}

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
            comparison_map[field_name] = ComparisonMetric(
                metric=1.0, color="green", comment="Values match exactly"
            )
        elif left_val is None or right_val is None:
            comparison_map[field_name] = ComparisonMetric(
                metric=0.0, color="orange", comment="One value is missing"
            )
        else:
            # Try to compute similarity for strings
            if isinstance(left_val, str) and isinstance(right_val, str):
                # Simple character overlap ratio
                common = sum(1 for a, b in zip(left_val, right_val) if a == b)
                max_len = max(len(left_val), len(right_val))
                similarity = common / max_len if max_len > 0 else 0

                comparison_map[field_name] = ComparisonMetric(
                    metric=round(similarity, 2),
                    color="orange" if similarity > 0.5 else "red",
                    comment=f"String similarity: {similarity:.0%}",
                )
            else:
                comparison_map[field_name] = ComparisonMetric(
                    metric=0.0,
                    color="red",
                    comment=f"Different values: {left_val} vs {right_val}",
                )

    return comparison_map
