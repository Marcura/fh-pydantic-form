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
    },
    SpacingTheme.COMPACT: {
        "outer_margin": "mb-0.5",
        "outer_margin_sm": "mb-0.5",
        "inner_gap": "",
        "inner_gap_small": "",
        "stack_gap": "",
        "padding": "p-2",
        "padding_sm": "p-1",
        "padding_card": "px-2 py-1",
        "card_border": "",
        "section_divider": "",
        "accordion_divider": "",
        "label_gap": "mb-0",
        "card_body_pad": "px-2 py-0.5",
        "accordion_content": "uk-padding-remove-vertical",
        "input_size": "uk-form-small",
        "input_padding": "p-1",
    },
}


def spacing(token: str, spacing: SpacingValue) -> str:
    """Return a Tailwind utility class for the given semantic token."""
    theme = _normalize_spacing(spacing)
    return SPACING_MAP[theme][token]


# CSS override to kill any residual borders in compact mode
COMPACT_EXTRA_CSS = fh.Style("""
/* Aggressive margin reduction for all UIkit margin utilities */
.compact-form .uk-margin-small-bottom,
.compact-form .uk-margin,
.compact-form .uk-margin-bottom {
    margin-bottom: 2px !important;
}

/* Remove borders and shrink accordion chrome */
.compact-form .uk-accordion > li,
.compact-form .uk-accordion .uk-accordion-content {
    border: 0 !important;
}

/* Minimize accordion content padding */
.compact-form .uk-accordion-content {
    padding-top: 0.25rem !important;
    padding-bottom: 0.25rem !important;
}

/* Shrink accordion item title padding */
.compact-form li.uk-open > a {
    padding-top: 0.25rem;
    padding-bottom: 0.25rem;
}

/* Apply smaller font and reduced padding to all form inputs */
.compact-form input,
.compact-form select,
.compact-form textarea {
    line-height: 1.25rem !important;   /* ~20px */
    font-size: 0.8125rem !important;   /* 13px */
}

/* Legacy overrides for specific UIkit classes */
.compact-form input.uk-form-small,
.compact-form select.uk-form-small,
.compact-form textarea.uk-textarea-small {
    padding-top: 2px !important;
    padding-bottom: 2px !important;
}
""")
