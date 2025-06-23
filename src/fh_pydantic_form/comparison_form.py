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
    Type,
    TypeVar,
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel

from fh_pydantic_form.form_renderer import PydanticForm
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import MetricEntry, MetricsDict

logger = logging.getLogger(__name__)

# TypeVar for generic model typing
ModelType = TypeVar("ModelType", bound=BaseModel)


def comparison_form_js():
    """JavaScript for comparison: sync top-level and list accordions."""
    return fh.Script("""
window.fhpfInitComparisonSync = function initComparisonSync(){
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
};

// Initial run
window.fhpfInitComparisonSync();

// Re-run after HTMX swaps to maintain sync
document.addEventListener('htmx:afterSwap', function(event) {
  // Re-initialize the comparison sync
  window.fhpfInitComparisonSync();
});
""")


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
    ):
        """
        Initialize the comparison form

        Args:
            name: Unique name for this comparison form
            left_form: Pre-constructed PydanticForm for left column
            right_form: Pre-constructed PydanticForm for right column
            left_label: Label for left column
            right_label: Label for right column

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
        self.left_form = left_form
        self.right_form = right_form
        self.model_class = left_form.model_class  # Convenience reference
        self.left_label = left_label
        self.right_label = right_label

        # Use spacing from left form (or could add override parameter if needed)
        self.spacing = left_form.spacing

    def _get_field_path_string(self, field_path: List[str]) -> str:
        """Convert field path list to dot-notation string for comparison lookup"""
        return ".".join(field_path)

    def _render_column(
        self,
        *,
        form: PydanticForm[ModelType],
        header_label: str,
        start_order: int,
        wrapper_id: str,
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

            # Get value from form
            value = form.values_dict.get(field_name)

            # Get path string for data-path attribute
            path_str = field_name

            # Get renderer class
            renderer_cls = registry.get_renderer(field_name, field_info)
            if not renderer_cls:
                from fh_pydantic_form.field_renderers import StringFieldRenderer

                renderer_cls = StringFieldRenderer

            # Determine comparison-specific refresh endpoint
            comparison_refresh = f"/compare/{self.name}/{'left' if form is self.left_form else 'right'}/refresh"

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
                metrics_dict=form.metrics_dict,  # Use form's own metrics
                refresh_endpoint_override=comparison_refresh,  # Pass comparison-specific refresh endpoint
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

    # def _create_field_pairs(
    #     self,
    # ) -> List[Tuple[str, BaseFieldRenderer, BaseFieldRenderer]]:
    #     """
    #     Create pairs of renderers (left, right) for each field path

    #     Returns:
    #         List of (path_string, left_renderer, right_renderer) tuples
    #     """
    #     pairs = []
    #     registry = FieldRendererRegistry()

    #     # Walk through model fields to create renderer pairs
    #     for field_name, field_info in self.model_class.model_fields.items():
    #         # Skip fields that are excluded in either form
    #         if field_name in (self.left_form.exclude_fields or []) or field_name in (
    #             self.right_form.exclude_fields or []
    #         ):
    #             logger.debug(
    #                 f"Skipping field '{field_name}' - excluded in one or both forms"
    #             )
    #             continue

    #         # Get values from each form
    #         left_value = self.left_form.values_dict.get(field_name)
    #         right_value = self.right_form.values_dict.get(field_name)

    #         # Get the path string for comparison lookup
    #         path_str = field_name
    #         left_comparison_metric = self.left_metrics.get(path_str)
    #         right_comparison_metric = self.right_metrics.get(path_str)

    #         # Get renderer class
    #         renderer_cls = registry.get_renderer(field_name, field_info)
    #         if not renderer_cls:
    #             from fh_pydantic_form.field_renderers import StringFieldRenderer

    #             renderer_cls = StringFieldRenderer

    #         # Create left renderer
    #         left_renderer = renderer_cls(
    #             field_name=field_name,
    #             field_info=field_info,
    #             value=left_value,
    #             prefix=self.left_form.base_prefix,
    #             disabled=self.left_form.disabled,
    #             spacing=self.left_form.spacing,
    #             field_path=[field_name],
    #             form_name=self.left_form.name,
    #             comparison=left_comparison_metric,
    #             comparison_map=self.left_metrics,  # Pass the full comparison map
    #         )

    #         # Create right renderer
    #         right_renderer = renderer_cls(
    #             field_name=field_name,
    #             field_info=field_info,
    #             value=right_value,
    #             prefix=self.right_form.base_prefix,
    #             disabled=self.right_form.disabled,
    #             spacing=self.right_form.spacing,
    #             field_path=[field_name],
    #             form_name=self.right_form.name,
    #             comparison=right_comparison_metric,
    #             comparison_map=self.right_metrics,  # Pass the full comparison map
    #         )

    #         pairs.append((path_str, left_renderer, right_renderer))

    #     return pairs

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
        )

        # Render right column with wrapper
        right_wrapper = self._render_column(
            form=self.right_form,
            header_label=self.right_label,
            start_order=1,
            wrapper_id=f"{self.right_form.name}-inputs-wrapper",
        )

        # Create the grid container with both wrappers
        grid_container = fh.Div(
            left_wrapper,
            right_wrapper,
            cls="fhpf-compare grid grid-cols-2 gap-x-6 gap-y-2 items-start",
            id=f"{self.name}-comparison-grid",
        )

        return fh.Div(grid_container, cls="w-full")

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
            side: str,
            label: str,
        ):
            """Factory function to create reset handler with proper closure"""

            async def handler(req):
                """Reset one side of the comparison form"""
                # Reset the form state
                await form.handle_reset_request()

                # Render the entire column with proper ordering
                start_order = 0 if side == "left" else 1
                wrapper = self._render_column(
                    form=form,
                    header_label=label,
                    start_order=start_order,
                    wrapper_id=f"{form.name}-inputs-wrapper",
                )
                return wrapper

            return handler

        def create_refresh_handler(
            form: PydanticForm[ModelType],
            side: str,
            label: str,
        ):
            """Factory function to create refresh handler with proper closure"""

            async def handler(req):
                """Refresh one side of the comparison form"""
                # Refresh the form state and capture any warnings
                refresh_result = await form.handle_refresh_request(req)

                # Render the entire column with proper ordering
                start_order = 0 if side == "left" else 1
                wrapper = self._render_column(
                    form=form,
                    header_label=label,
                    start_order=start_order,
                    wrapper_id=f"{form.name}-inputs-wrapper",
                )

                # If refresh returned a warning, include it in the response
                if isinstance(refresh_result, tuple) and len(refresh_result) == 2:
                    alert, _ = refresh_result
                    # Return both the alert and the wrapper
                    return fh.Div(alert, wrapper)
                else:
                    # No warning, just return the wrapper
                    return wrapper

            return handler

        for side, form, label in [
            ("left", self.left_form, self.left_label),
            ("right", self.right_form, self.right_label),
        ]:
            assert form is not None

            # Reset route
            reset_path = f"/compare/{self.name}/{side}/reset"
            reset_handler = create_reset_handler(form, side, label)
            app.route(reset_path, methods=["POST"])(reset_handler)
            logger.debug(f"Registered comparison reset route: {reset_path}")

            # Refresh route
            refresh_path = f"/compare/{self.name}/{side}/refresh"
            refresh_handler = create_refresh_handler(form, side, label)
            app.route(refresh_path, methods=["POST"])(refresh_handler)
            logger.debug(f"Registered comparison refresh route: {refresh_path}")

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

        # Create prefix-based selector
        prefix_selector = f"form [name^='{form.base_prefix}']"

        # Set default attributes
        kwargs.setdefault("hx_post", f"/compare/{self.name}/{side}/{action}")
        kwargs.setdefault("hx_target", f"#{form.name}-inputs-wrapper")
        kwargs.setdefault("hx_swap", "innerHTML")
        kwargs.setdefault("hx_include", prefix_selector)

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
