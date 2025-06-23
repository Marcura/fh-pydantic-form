from enum import Enum, auto
from typing import Dict, Literal, Union


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
        "card_border_thin": "",
        "section_divider": "border-t border-gray-200",
        "metric_badge_gap": "ml-2",
        "accordion_divider": "uk-accordion-divider",
        "accordion_title_pad": "",
        "accordion_content_pad": "",
        "accordion_item_margin": "uk-margin-small-bottom",
        "label_gap": "mb-1",
        "card_body_pad": "px-4 py-3",
        "accordion_content": "",
        "input_size": "",
        "input_padding": "",
        "input_line_height": "",
        "input_font_size": "",
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
        "card_border_thin": "",
        "section_divider": "",
        "metric_badge_gap": "ml-1",
        "accordion_divider": "",
        "accordion_title_pad": "py-1",
        "accordion_content_pad": "py-1",
        "accordion_item_margin": "mb-0",
        "label_gap": "mb-0",
        "card_body_pad": "px-2 py-0.5",
        "accordion_content": "uk-padding-remove-vertical",
        "input_size": "uk-form-small",
        "input_padding": "py-0.5 px-1",
        "input_line_height": "leading-tight",
        "input_font_size": "text-sm",
        "horizontal_gap": "gap-2",
        "label_align": "items-start",
    },
}


def spacing(token: str, spacing: SpacingValue) -> str:
    """Return a Tailwind utility class for the given semantic token."""
    theme = _normalize_spacing(spacing)
    return SPACING_MAP[theme][token]


def spacing_many(tokens: list[str], spacing: SpacingValue) -> str:
    """
    Return combined Tailwind utility classes for multiple semantic tokens.

    Args:
        tokens: List of spacing token names
        spacing: Spacing theme to use

    Returns:
        String of space-separated CSS classes
    """
    theme = _normalize_spacing(spacing)
    classes = []
    for token in tokens:
        class_value = SPACING_MAP[theme].get(token, "")
        if class_value:  # Only add non-empty class values
            classes.append(class_value)
    return " ".join(classes)
