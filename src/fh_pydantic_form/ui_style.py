from enum import Enum, auto
from typing import Dict, Literal, Union

import fasthtml.common as fh


class SpacingTheme(Enum):
    NORMAL = auto()
    COMPACT = auto()


# Type alias for spacing values - supports both literal strings and enum values
SpacingValue = Union[Literal["normal", "compact"], SpacingTheme]


def _normalize_spacing(spacing_value: SpacingValue) -> SpacingTheme:
    """Convert literal string or enum spacing value to SpacingTheme enum."""
    if isinstance(spacing_value, str):
        if spacing_value == "compact":
            return SpacingTheme.COMPACT
        elif spacing_value == "normal":
            return SpacingTheme.NORMAL
        else:
            # This case shouldn't happen with proper Literal typing, but included for runtime safety
            raise ValueError(
                f"Invalid spacing value: {spacing_value}. Must be 'compact', 'normal', or SpacingTheme enum"
            )
    elif isinstance(spacing_value, SpacingTheme):
        return spacing_value
    else:
        raise TypeError(
            f"spacing must be Literal['normal', 'compact'] or SpacingTheme, got {type(spacing_value)}"
        )


SPACING_MAP: Dict[SpacingTheme, Dict[str, str]] = {
    SpacingTheme.NORMAL: {
        "outer_margin": "mb-4",
        "outer_margin_sm": "mb-2",
        "inner_gap": "space-y-3",
        "inner_gap_small": "space-y-2",
        "stack_gap": "space-y-3",
        "padding": "p-4",
        "padding_sm": "p-3",
        "padding_card": "px-4 py-3",
        "card_border": "border",
        "section_divider": "border-t border-gray-200",
        "accordion_divider": "uk-accordion-divider",
        "label_gap": "mb-1",
        "card_body_pad": "px-4 py-3",
        "accordion_content": "",
        "input_size": "",
        "input_padding": "",
        "horizontal_gap": "gap-3",
        "label_align": "items-start",
    },
    SpacingTheme.COMPACT: {
        "outer_margin": "mb-0",
        "outer_margin_sm": "mb-0",
        "inner_gap": "space-y-1",
        "inner_gap_small": "space-y-0.5",
        "stack_gap": "space-y-1",
        "padding": "p-1",
        "padding_sm": "p-0.5",
        "padding_card": "px-2 py-1",
        "card_border": "",
        "section_divider": "",
        "accordion_divider": "",
        "label_gap": "mb-0",
        "card_body_pad": "px-2 py-0.5",
        "accordion_content": "uk-padding-remove-vertical",
        "input_size": "uk-form-small",
        "input_padding": "p-1",
        "horizontal_gap": "gap-2",
        "label_align": "items-center",
    },
}


def spacing(token: str, spacing: SpacingValue) -> str:
    """Return a Tailwind utility class for the given semantic token."""
    theme = _normalize_spacing(spacing)
    return SPACING_MAP[theme][token]


# Optional minimal CSS for compact mode - affects only form inputs, not layout
# Host applications can optionally inject this once at app level if desired
COMPACT_EXTRA_CSS = fh.Style("""
/* Compact polish – applies ONLY inside .fhpf-compact ------------------- */
.fhpf-compact {

  /* Accordion chrome: remove border and default 20 px gap */
  .uk-accordion > li,
  .uk-accordion > li + li {          /* second & later items */
        border-top: 0 !important;
        margin-top: 0 !important;
  }
  .uk-accordion-title::after {       /* the hair-line we still see */
        border-top: 0 !important;
  }

  /* Tighter title and content padding */
  li > a.uk-accordion-title,
  .uk-accordion-content {
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
  }

  /* Remove residual card outline */
  .uk-card,
  .uk-card-body { border: 0 !important; }

  /* Small-size inputs */
  input, select, textarea {
        line-height: 1.25rem !important;
        font-size: 0.8125rem !important;
        padding-top: 0.25rem !important;
        padding-bottom: 0.25rem !important;
  }

  /* Legacy uk-form-small support */
  input.uk-form-small,
  select.uk-form-small,
  textarea.uk-textarea-small {
        padding-top: 2px !important;
        padding-bottom: 2px !important;
  }

  /* Kill generic uk-margin utilities inside the form */
  .uk-margin-small-bottom,
  .uk-margin,
  .uk-margin-bottom { margin-bottom: 2px !important; }
}
""")
