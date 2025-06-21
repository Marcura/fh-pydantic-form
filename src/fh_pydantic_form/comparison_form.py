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
)

import fasthtml.common as fh
import monsterui.all as mui
from fastcore.xml import FT
from pydantic import BaseModel

from fh_pydantic_form.field_renderers import BaseFieldRenderer
from fh_pydantic_form.form_renderer import PydanticForm
from fh_pydantic_form.registry import FieldRendererRegistry
from fh_pydantic_form.type_helpers import ComparisonMap, ComparisonMetric

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

    The ComparisonForm is a view-only composition helper; state management
    lives in the underlying PydanticForm instances.
    """

    def __init__(
        self,
        name: str,
        left_form: PydanticForm[ModelType],
        right_form: PydanticForm[ModelType],
        *,
        left_metrics: Optional[ComparisonMap] = None,
        right_metrics: Optional[ComparisonMap] = None,
        left_label: str = "Reference",
        right_label: str = "Generated",
    ):
        """
        Initialize the comparison form

        Args:
            name: Unique name for this comparison form
            left_form: Pre-constructed PydanticForm for left column
            right_form: Pre-constructed PydanticForm for right column
            left_metrics: Mapping of field paths to comparison metrics for left form
            right_metrics: Mapping of field paths to comparison metrics for right form
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
        self.left_metrics = left_metrics or {}
        self.right_metrics = right_metrics or {}
        self.left_label = left_label
        self.right_label = right_label

        # Use spacing from left form (or could add override parameter if needed)
        self.spacing = left_form.spacing

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
            # Skip fields that are excluded in either form
            if field_name in (self.left_form.exclude_fields or []) or field_name in (
                self.right_form.exclude_fields or []
            ):
                logger.debug(
                    f"Skipping field '{field_name}' - excluded in one or both forms"
                )
                continue

            # Get values from each form
            left_value = self.left_form.values_dict.get(field_name)
            right_value = self.right_form.values_dict.get(field_name)

            # Get the path string for comparison lookup
            path_str = field_name
            left_comparison_metric = self.left_metrics.get(path_str)
            right_comparison_metric = self.right_metrics.get(path_str)

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
                spacing=self.left_form.spacing,
                field_path=[field_name],
                form_name=self.left_form.name,
                comparison=left_comparison_metric,
                comparison_map=self.left_metrics,  # Pass the full comparison map
            )

            # Create right renderer
            right_renderer = renderer_cls(
                field_name=field_name,
                field_info=field_info,
                value=right_value,
                prefix=self.right_form.base_prefix,
                disabled=self.right_form.disabled,
                spacing=self.right_form.spacing,
                field_path=[field_name],
                form_name=self.right_form.name,
                comparison=right_comparison_metric,
                comparison_map=self.right_metrics,  # Pass the full comparison map
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

    def register_routes(self, app):
        """
        Register HTMX routes for the comparison form

        Args:
            app: FastHTML app instance
        """
        # Simply delegate to the individual forms
        self.left_form.register_routes(app)
        self.right_form.register_routes(app)

        # No comparison-specific routes needed anymore

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


def simple_diff_comparison(
    left_data: BaseModel | Dict[str, Any],
    right_data: BaseModel | Dict[str, Any],
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
                    comment=f"String similarity: {similarity:.0%}",
                )
            else:
                comparison_map[field_name] = ComparisonMetric(
                    metric=0.0,
                    comment=f"Different values: {left_val} vs {right_val}",
                )

    return comparison_map
