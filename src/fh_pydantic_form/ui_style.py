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
        "padding": "p-4",
        "padding_sm": "p-3",
        "padding_card": "px-4 py-3",
        "card_border": "border",
        "section_divider": "border-t border-gray-200",
        "accordion_divider": "uk-accordion-divider",
    },
    SpacingTheme.COMPACT: {
        "outer_margin": "mb-2",
        "outer_margin_sm": "mb-1",
        "inner_gap": "space-y-1",
        "inner_gap_small": "space-y-1",
        "padding": "p-2",
        "padding_sm": "p-1",
        "padding_card": "px-2 py-1",
        "card_border": "",
        "section_divider": "",
        "accordion_divider": "",
    },
}


def spacing(token: str, theme: SpacingTheme) -> str:
    """Return a Tailwind utility class for the given semantic token."""
    return SPACING_MAP[theme][token]


# CSS override to kill any residual borders in compact mode
COMPACT_EXTRA_CSS = fh.Style("""
.compact-form .uk-accordion > li,
.compact-form .uk-accordion .uk-accordion-content {
    border: 0 !important;
}
""")
