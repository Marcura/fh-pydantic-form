from enum import Enum, auto
from typing import Dict
import fasthtml.common as fh


class SpacingTheme(Enum):
    NORMAL = auto()
    COMPACT = auto()


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


def spacing(token: str, theme: SpacingTheme) -> str:
    """Return a Tailwind utility class for the given semantic token."""
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
