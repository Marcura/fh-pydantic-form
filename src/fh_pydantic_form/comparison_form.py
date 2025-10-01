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
    Dict,
    Generic,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
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
    """JavaScript for comparison: sync accordions and handle JS-only copy operations."""
    return fh.Script("""
// Copy function - no HTMX, pure JS
window.fhpfPerformCopy = function(pathPrefix, currentPrefix, copyTarget) {
  try {
    // Set flag to prevent accordion sync
    window.__fhpfCopyInProgress = true;

    // Save all accordion states before copy
    var accordionStates = [];
    document.querySelectorAll('ul[uk-accordion] > li').forEach(function(li) {
      accordionStates.push({
        element: li,
        isOpen: li.classList.contains('uk-open')
      });
    });

    // Determine source prefix based on target
    // If copying TO left, source is right (the OTHER prefix)
    // If copying TO right, source is left (the OTHER prefix)
    // currentPrefix is the button's form prefix (target side)
    // We need the OTHER side's prefix (source side)
    var sourcePrefix;
    if (copyTarget === 'left') {
      // Copying TO left, so source is right
      sourcePrefix = window.__fhpfRightPrefix;
    } else {
      // Copying TO right, so source is left
      sourcePrefix = window.__fhpfLeftPrefix;
    }

    // Find all inputs with matching data-field-path
    var allInputs = document.querySelectorAll('[data-field-path][name^="' + sourcePrefix + '"]');
    var sourceInputs = Array.from(allInputs).filter(function(el) {
      var fp = el.getAttribute('data-field-path');
      return fp === pathPrefix || fp.startsWith(pathPrefix + '.') || fp.startsWith(pathPrefix + '[');
    });

    sourceInputs.forEach(function(sourceInput) {
      var fp = sourceInput.getAttribute('data-field-path');
      var targetInput = document.querySelector('[data-field-path="' + fp + '"]:not([name^="' + sourcePrefix + '"])');

      if (!targetInput) return;

      var tag = sourceInput.tagName.toUpperCase();
      var type = (sourceInput.type || '').toLowerCase();

      if (type === 'checkbox') {
        targetInput.checked = sourceInput.checked;
      } else if (tag === 'SELECT') {
        targetInput.value = sourceInput.value;
      } else if (tag === 'UK-SELECT') {
        var sourceNativeSelect = sourceInput.querySelector('select');
        var targetNativeSelect = targetInput.querySelector('select');
        if (sourceNativeSelect && targetNativeSelect) {
          // Set the value on the native select
          targetNativeSelect.value = sourceNativeSelect.value;

          // Also need to update the selected option
          var sourceSelectedOption = sourceNativeSelect.options[sourceNativeSelect.selectedIndex];
          if (sourceSelectedOption) {
            // Find matching option in target by value
            for (var i = 0; i < targetNativeSelect.options.length; i++) {
              if (targetNativeSelect.options[i].value === sourceSelectedOption.value) {
                targetNativeSelect.selectedIndex = i;
                break;
              }
            }
          }

          // Update the button display
          var sourceButton = sourceInput.querySelector('button');
          var targetButton = targetInput.querySelector('button');
          if (sourceButton && targetButton) {
            targetButton.innerHTML = sourceButton.innerHTML;
          }
        }
      } else if (tag === 'TEXTAREA') {
        // Just set the value directly, don't clear first
        targetInput.value = sourceInput.value;
        targetInput.textContent = sourceInput.value;
      } else {
        targetInput.value = sourceInput.value;
      }
    });

    // Restore accordion states after a brief delay
    setTimeout(function() {
      var restoredCount = 0;
      accordionStates.forEach(function(state) {
        if (state.isOpen && !state.element.classList.contains('uk-open')) {
          // Use UIkit's toggle API to properly open the accordion
          var accordionParent = state.element.parentElement;
          if (accordionParent && window.UIkit) {
            var accordionComponent = UIkit.accordion(accordionParent);
            if (accordionComponent) {
              var itemIndex = Array.from(accordionParent.children).indexOf(state.element);
              accordionComponent.toggle(itemIndex, true);
              restoredCount++;
            } else {
              // Fallback to manual class manipulation
              state.element.classList.add('uk-open');
              var content = state.element.querySelector('.uk-accordion-content');
              if (content) {
                content.hidden = false;
                content.style.height = 'auto';
              }
            }
          }
        }
      });

      window.__fhpfCopyInProgress = false;
      if (restoredCount > 0) {
        console.log('[fhpf] restored', restoredCount, 'accordion(s)');
      }
    }, 150);

  } catch (e) {
    console.error('[fhpf] copy error', e);
    window.__fhpfCopyInProgress = false;
  }
};

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

    // Skip if copy operation is in progress
    if (window.__fhpfCopyInProgress) {
      return;
    }

    // Skip if this event is from a select/dropdown element
    if (ev.target.closest('uk-select, select, [uk-select]')) {
      return;
    }

    // Skip if this is a nested list item (let mirrorNestedListItems handle it)
    if (sourceLi.closest('[id$="_items_container"]')) {
      return;
    }

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

  // 3) Sync nested list item accordions (individual items within lists)
  UIkit.util.on(
    document,
    'show hide',
    '[id$="_items_container"] > li',  // only list items within items containers
    mirrorNestedListItems
  );

  function mirrorNestedListItems(ev) {
    const sourceLi = ev.target.closest('li');
    if (!sourceLi) return;

    // Skip if copy operation is in progress
    if (window.__fhpfCopyInProgress) {
      return;
    }

    // Skip if this event is from a select/dropdown element
    if (ev.target.closest('uk-select, select, [uk-select]')) {
      return;
    }

    // Skip if this event was triggered by our own sync
    if (sourceLi.dataset.syncDisabled) {
      return;
    }

    // Find the list container (items_container) that contains this item
    const listContainer = sourceLi.closest('[id$="_items_container"]');
    if (!listContainer) return;

    // Find the grid cell wrapper with data-path
    const cell = listContainer.closest('[data-path]');
    if (!cell) return;
    const path = cell.dataset.path;

    // Determine index of this <li> within its list container
    const listAccordion = sourceLi.parentElement;
    const idx = Array.prototype.indexOf.call(listAccordion.children, sourceLi);
    const opening = ev.type === 'show';

    // Mirror on the other side
    document
      .querySelectorAll(`[data-path="${path}"]`)
      .forEach(peerCell => {
        if (peerCell === cell) return;

        // Find the peer's list container
        const peerListContainer = peerCell.querySelector('[id$="_items_container"]');
        if (!peerListContainer) return;

        // The list container IS the accordion itself (not a wrapper around it)
        let peerListAccordion;
        if (peerListContainer.hasAttribute('uk-accordion') && peerListContainer.tagName === 'UL') {
          peerListAccordion = peerListContainer;
        } else {
          peerListAccordion = peerListContainer.querySelector('ul[uk-accordion]');
        }
        
        if (!peerListAccordion || idx >= peerListAccordion.children.length) return;

        const peerLi = peerListAccordion.children[idx];
        const peerContent = peerLi.querySelector('.uk-accordion-content');

        // Prevent event cascading by temporarily disabling our own event listener
        if (peerLi.dataset.syncDisabled) {
          return;
        }

        // Mark this item as being synced to prevent loops
        peerLi.dataset.syncDisabled = 'true';

        // Check current state and only sync if different
        const currentlyOpen = peerLi.classList.contains('uk-open');
        
        if (currentlyOpen !== opening) {
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
        }

        // Re-enable sync after a short delay
        setTimeout(() => {
          delete peerLi.dataset.syncDisabled;
        }, 100);
      });
  }

  // 4) Wrap the list-toggle so ListFieldRenderer accordions sync too
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
        copy_left: bool = False,
        copy_right: bool = False,
    ):
        """
        Initialize the comparison form

        Args:
            name: Unique name for this comparison form
            left_form: Pre-constructed PydanticForm for left column
            right_form: Pre-constructed PydanticForm for right column
            left_label: Label for left column
            right_label: Label for right column
            copy_left: If True, show copy buttons in left column to copy from right
            copy_right: If True, show copy buttons in right column to copy from left

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

            # Get label color for this field if specified
            label_color = (
                form.label_colors.get(field_name)
                if hasattr(form, "label_colors")
                else None
            )

            # Determine comparison copy settings
            # Only enable copy buttons if the TARGET (destination) form is NOT disabled
            is_left_column = form is self.left_form
            comparison_copy_target = "left" if is_left_column else "right"
            target_form = self.left_form if is_left_column else self.right_form

            # Enable copy button if:
            # 1. The feature is enabled for this side (copy_left or copy_right)
            # 2. The TARGET form is NOT disabled (you can't copy into a disabled/read-only form)
            copy_feature_enabled = self.copy_left if is_left_column else self.copy_right
            comparison_copy_enabled = copy_feature_enabled and not target_form.disabled

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
                label_color=label_color,  # Pass the label color if specified
                metrics_dict=form.metrics_dict,  # Use form's own metrics
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

        # Emit prefix globals for the copy registry
        prefix_script = fh.Script(f"""
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

            # Refresh route
            refresh_path = f"/compare/{self.name}/{side}/refresh"
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

        # Create prefix-based selector
        prefix_selector = f"form [name^='{form.base_prefix}']"

        # Set default attributes
        kwargs.setdefault("hx_post", f"/compare/{self.name}/{side}/{action}")
        kwargs.setdefault("hx_target", f"#{form.name}-inputs-wrapper")
        kwargs.setdefault("hx_swap", "innerHTML")
        kwargs.setdefault("hx_include", prefix_selector)
        kwargs.setdefault("hx_preserve", "scroll")

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
