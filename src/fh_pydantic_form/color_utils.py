"""
Color utility functions for fh-pydantic-form

This module provides robust color parsing and conversion utilities that support
various color formats including hex, RGB, HSL, named colors, and Tailwind CSS classes.
"""

__all__ = ["robust_color_to_rgba", "get_metric_colors", "DEFAULT_METRIC_GREY"]

import re
from typing import Tuple

DEFAULT_METRIC_GREY = "rgba(200, 200, 200, 0.5)"


def robust_color_to_rgba(color: str, opacity: float = 1.0) -> str:
    """
    Convert any color format to rgba with specified opacity.

    Supports:
    - Hex colors: #FF0000, #F00, #ff0000, #f00
    - RGB colors: rgb(255, 0, 0), rgb(255,0,0)
    - RGBA colors: rgba(255, 0, 0, 0.5)
    - HSL colors: hsl(0, 100%, 50%)
    - HSLA colors: hsla(0, 100%, 50%, 0.5)
    - Named colors: red, blue, green, etc.
    - Tailwind classes: text-red-500, bg-blue-600, etc.

    Args:
        color: The color string in any supported format
        opacity: Opacity value (0.0 to 1.0)

    Returns:
        RGBA color string in format "rgba(r, g, b, opacity)"
    """
    if not color:
        return f"rgba(128, 128, 128, {opacity})"  # Default gray

    color = color.strip()

    # Handle hex colors
    if color.startswith("#"):
        hex_color = color.lstrip("#")
        if len(hex_color) == 3:
            # Convert 3-digit hex to 6-digit (e.g., #f00 -> #ff0000)
            hex_color = "".join([c * 2 for c in hex_color])
        elif len(hex_color) == 6:
            pass  # Already 6-digit hex
        else:
            return f"rgba(128, 128, 128, {opacity})"  # Invalid hex

        try:
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {opacity})"
        except ValueError:
            return f"rgba(128, 128, 128, {opacity})"

    # Handle rgb() and rgba() functions
    if color.startswith(("rgb(", "rgba(")):
        # Extract numbers from rgb/rgba string
        nums = re.findall(r"\d*\.?\d+", color)
        if len(nums) >= 3:
            r, g, b = int(float(nums[0])), int(float(nums[1])), int(float(nums[2]))
            return f"rgba({r}, {g}, {b}, {opacity})"
        return f"rgba(128, 128, 128, {opacity})"

    # Handle hsl() and hsla() functions
    if color.startswith(("hsl(", "hsla(")):
        # For HSL, we'll convert to RGB first
        # Extract numbers from hsl/hsla string
        nums = re.findall(r"\d*\.?\d+", color)
        if len(nums) >= 3:
            h = float(nums[0]) / 360.0  # Convert to 0-1 range
            s = float(nums[1]) / 100.0  # Convert percentage to 0-1
            lightness = float(nums[2]) / 100.0  # Convert percentage to 0-1

            # Convert HSL to RGB using standard algorithm
            r, g, b = _hsl_to_rgb(h, s, lightness)
            return f"rgba({r}, {g}, {b}, {opacity})"
        return f"rgba(128, 128, 128, {opacity})"

    # Handle Tailwind CSS classes (e.g., text-red-500, bg-blue-600, border-green-400)
    tailwind_match = re.match(r"(?:text-|bg-|border-)?(\w+)-(\d+)", color)
    if tailwind_match:
        color_name, intensity = tailwind_match.groups()

        if color_name in TAILWIND_COLORS and intensity in TAILWIND_COLORS[color_name]:
            r, g, b = TAILWIND_COLORS[color_name][intensity]
            return f"rgba({r}, {g}, {b}, {opacity})"

    # Handle named CSS colors
    if color.lower() in NAMED_COLORS:
        r, g, b = NAMED_COLORS[color.lower()]
        return f"rgba({r}, {g}, {b}, {opacity})"

    # Fallback for unrecognized colors
    return f"rgba(128, 128, 128, {opacity})"


def _hsl_to_rgb(h: float, s: float, lightness: float) -> Tuple[int, int, int]:
    """
    Convert HSL color values to RGB.

    Args:
        h: Hue (0.0 to 1.0)
        s: Saturation (0.0 to 1.0)
        lightness: Lightness (0.0 to 1.0)

    Returns:
        RGB tuple with values 0-255
    """
    if s == 0:
        r = g = b = lightness  # Achromatic
    else:

        def hue_to_rgb(p: float, q: float, t: float) -> float:
            if t < 0:
                t += 1
            if t > 1:
                t -= 1
            if t < 1 / 6:
                return p + (q - p) * 6 * t
            if t < 1 / 2:
                return q
            if t < 2 / 3:
                return p + (q - p) * (2 / 3 - t) * 6
            return p

        q = lightness * (1 + s) if lightness < 0.5 else lightness + s - lightness * s
        p = 2 * lightness - q
        r = hue_to_rgb(p, q, h + 1 / 3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1 / 3)

    return int(r * 255), int(g * 255), int(b * 255)


# Tailwind CSS color palette with RGB values
TAILWIND_COLORS = {
    "red": {
        "50": (254, 242, 242),
        "100": (254, 226, 226),
        "200": (254, 202, 202),
        "300": (252, 165, 165),
        "400": (248, 113, 113),
        "500": (239, 68, 68),
        "600": (220, 38, 38),
        "700": (185, 28, 28),
        "800": (153, 27, 27),
        "900": (127, 29, 29),
        "950": (69, 10, 10),
    },
    "green": {
        "50": (240, 253, 244),
        "100": (220, 252, 231),
        "200": (187, 247, 208),
        "300": (134, 239, 172),
        "400": (74, 222, 128),
        "500": (34, 197, 94),
        "600": (22, 163, 74),
        "700": (21, 128, 61),
        "800": (22, 101, 52),
        "900": (20, 83, 45),
        "950": (5, 46, 22),
    },
    "blue": {
        "50": (239, 246, 255),
        "100": (219, 234, 254),
        "200": (191, 219, 254),
        "300": (147, 197, 253),
        "400": (96, 165, 250),
        "500": (59, 130, 246),
        "600": (37, 99, 235),
        "700": (29, 78, 216),
        "800": (30, 64, 175),
        "900": (30, 58, 138),
        "950": (23, 37, 84),
    },
    "yellow": {
        "50": (254, 252, 232),
        "100": (254, 249, 195),
        "200": (254, 240, 138),
        "300": (253, 224, 71),
        "400": (250, 204, 21),
        "500": (234, 179, 8),
        "600": (202, 138, 4),
        "700": (161, 98, 7),
        "800": (133, 77, 14),
        "900": (113, 63, 18),
        "950": (66, 32, 6),
    },
    "purple": {
        "50": (250, 245, 255),
        "100": (243, 232, 255),
        "200": (233, 213, 255),
        "300": (216, 180, 254),
        "400": (196, 143, 253),
        "500": (168, 85, 247),
        "600": (147, 51, 234),
        "700": (126, 34, 206),
        "800": (107, 33, 168),
        "900": (88, 28, 135),
        "950": (59, 7, 100),
    },
    "orange": {
        "50": (255, 247, 237),
        "100": (255, 237, 213),
        "200": (254, 215, 170),
        "300": (253, 186, 116),
        "400": (251, 146, 60),
        "500": (249, 115, 22),
        "600": (234, 88, 12),
        "700": (194, 65, 12),
        "800": (154, 52, 18),
        "900": (124, 45, 18),
        "950": (67, 20, 7),
    },
    "pink": {
        "50": (253, 242, 248),
        "100": (252, 231, 243),
        "200": (251, 207, 232),
        "300": (249, 168, 212),
        "400": (244, 114, 182),
        "500": (236, 72, 153),
        "600": (219, 39, 119),
        "700": (190, 24, 93),
        "800": (157, 23, 77),
        "900": (131, 24, 67),
        "950": (80, 7, 36),
    },
    "indigo": {
        "50": (238, 242, 255),
        "100": (224, 231, 255),
        "200": (199, 210, 254),
        "300": (165, 180, 252),
        "400": (129, 140, 248),
        "500": (99, 102, 241),
        "600": (79, 70, 229),
        "700": (67, 56, 202),
        "800": (55, 48, 163),
        "900": (49, 46, 129),
        "950": (30, 27, 75),
    },
    "teal": {
        "50": (240, 253, 250),
        "100": (204, 251, 241),
        "200": (153, 246, 228),
        "300": (94, 234, 212),
        "400": (45, 212, 191),
        "500": (20, 184, 166),
        "600": (13, 148, 136),
        "700": (15, 118, 110),
        "800": (17, 94, 89),
        "900": (19, 78, 74),
        "950": (4, 47, 46),
    },
    # Extended Tailwind colors
    "gray": {
        "50": (249, 250, 251),
        "100": (243, 244, 246),
        "200": (229, 231, 235),
        "300": (209, 213, 219),
        "400": (156, 163, 175),
        "500": (107, 114, 128),
        "600": (75, 85, 99),
        "700": (55, 65, 81),
        "800": (31, 41, 55),
        "900": (17, 24, 39),
        "950": (3, 7, 18),
    },
    "slate": {
        "50": (248, 250, 252),
        "100": (241, 245, 249),
        "200": (226, 232, 240),
        "300": (203, 213, 225),
        "400": (148, 163, 184),
        "500": (100, 116, 139),
        "600": (71, 85, 105),
        "700": (51, 65, 85),
        "800": (30, 41, 59),
        "900": (15, 23, 42),
        "950": (2, 6, 23),
    },
    "zinc": {
        "50": (250, 250, 250),
        "100": (244, 244, 245),
        "200": (228, 228, 231),
        "300": (212, 212, 216),
        "400": (161, 161, 170),
        "500": (113, 113, 122),
        "600": (82, 82, 91),
        "700": (63, 63, 70),
        "800": (39, 39, 42),
        "900": (24, 24, 27),
        "950": (9, 9, 11),
    },
    "neutral": {
        "50": (250, 250, 250),
        "100": (245, 245, 245),
        "200": (229, 229, 229),
        "300": (212, 212, 212),
        "400": (163, 163, 163),
        "500": (115, 115, 115),
        "600": (82, 82, 82),
        "700": (64, 64, 64),
        "800": (38, 38, 38),
        "900": (23, 23, 23),
        "950": (10, 10, 10),
    },
    "stone": {
        "50": (250, 250, 249),
        "100": (245, 245, 244),
        "200": (231, 229, 228),
        "300": (214, 211, 209),
        "400": (168, 162, 158),
        "500": (120, 113, 108),
        "600": (87, 83, 78),
        "700": (68, 64, 60),
        "800": (41, 37, 36),
        "900": (28, 25, 23),
        "950": (12, 10, 9),
    },
    # Additional colors
    "emerald": {
        "50": (236, 253, 245),
        "100": (209, 250, 229),
        "200": (167, 243, 208),
        "300": (110, 231, 183),
        "400": (52, 211, 153),
        "500": (16, 185, 129),
        "600": (5, 150, 105),
        "700": (4, 120, 87),
        "800": (6, 95, 70),
        "900": (6, 78, 59),
        "950": (2, 44, 34),
    },
    "lime": {
        "50": (247, 254, 231),
        "100": (236, 252, 203),
        "200": (217, 249, 157),
        "300": (190, 242, 100),
        "400": (163, 230, 53),
        "500": (132, 204, 22),
        "600": (101, 163, 13),
        "700": (77, 124, 15),
        "800": (63, 98, 18),
        "900": (54, 83, 20),
        "950": (26, 46, 5),
    },
    "cyan": {
        "50": (236, 254, 255),
        "100": (207, 250, 254),
        "200": (165, 243, 252),
        "300": (103, 232, 249),
        "400": (34, 211, 238),
        "500": (6, 182, 212),
        "600": (8, 145, 178),
        "700": (14, 116, 144),
        "800": (21, 94, 117),
        "900": (22, 78, 99),
        "950": (8, 51, 68),
    },
    "sky": {
        "50": (240, 249, 255),
        "100": (224, 242, 254),
        "200": (186, 230, 253),
        "300": (125, 211, 252),
        "400": (56, 189, 248),
        "500": (14, 165, 233),
        "600": (2, 132, 199),
        "700": (3, 105, 161),
        "800": (7, 89, 133),
        "900": (12, 74, 110),
        "950": (8, 47, 73),
    },
    "violet": {
        "50": (245, 243, 255),
        "100": (237, 233, 254),
        "200": (221, 214, 254),
        "300": (196, 181, 253),
        "400": (167, 139, 250),
        "500": (139, 92, 246),
        "600": (124, 58, 237),
        "700": (109, 40, 217),
        "800": (91, 33, 182),
        "900": (76, 29, 149),
        "950": (46, 16, 101),
    },
    "fuchsia": {
        "50": (253, 244, 255),
        "100": (250, 232, 255),
        "200": (245, 208, 254),
        "300": (240, 171, 252),
        "400": (232, 121, 249),
        "500": (217, 70, 239),
        "600": (192, 38, 211),
        "700": (162, 28, 175),
        "800": (134, 25, 143),
        "900": (112, 26, 117),
        "950": (74, 4, 78),
    },
    "rose": {
        "50": (255, 241, 242),
        "100": (255, 228, 230),
        "200": (254, 205, 211),
        "300": (253, 164, 175),
        "400": (251, 113, 133),
        "500": (244, 63, 94),
        "600": (225, 29, 72),
        "700": (190, 18, 60),
        "800": (159, 18, 57),
        "900": (136, 19, 55),
        "950": (76, 5, 25),
    },
    "amber": {
        "50": (255, 251, 235),
        "100": (254, 243, 199),
        "200": (253, 230, 138),
        "300": (252, 211, 77),
        "400": (251, 191, 36),
        "500": (245, 158, 11),
        "600": (217, 119, 6),
        "700": (180, 83, 9),
        "800": (146, 64, 14),
        "900": (120, 53, 15),
        "950": (69, 26, 3),
    },
}

# Named CSS colors (cleaned up to remove duplicates)
NAMED_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 128, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "gray": (128, 128, 128),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "brown": (165, 42, 42),
    "pink": (255, 192, 203),
    "lime": (0, 255, 0),
    "navy": (0, 0, 128),
    "teal": (0, 128, 128),
    "silver": (192, 192, 192),
    "gold": (255, 215, 0),
    "maroon": (128, 0, 0),
    "olive": (128, 128, 0),
    "aqua": (0, 255, 255),
    "fuchsia": (255, 0, 255),
    "coral": (255, 127, 80),
    "crimson": (220, 20, 60),
    "darkblue": (0, 0, 139),
    "darkgreen": (0, 100, 0),
    "darkred": (139, 0, 0),
    "lightblue": (173, 216, 230),
    "lightgreen": (144, 238, 144),
    "lightgray": (211, 211, 211),
    "darkgray": (169, 169, 169),
    "lightcoral": (240, 128, 128),
    "lightyellow": (255, 255, 224),
    "lightpink": (255, 182, 193),
    "lightcyan": (224, 255, 255),
    "darkcyan": (0, 139, 139),
    "darkmagenta": (139, 0, 139),
    "darkorange": (255, 140, 0),
    "darkviolet": (148, 0, 211),
    "indigo": (75, 0, 130),
    "violet": (238, 130, 238),
    "turquoise": (64, 224, 208),
    "slateblue": (106, 90, 205),
    "steelblue": (70, 130, 180),
    "royalblue": (65, 105, 225),
    "mediumblue": (0, 0, 205),
    "dodgerblue": (30, 144, 255),
    "skyblue": (135, 206, 235),
    "paleblue": (175, 238, 238),
    "powderblue": (176, 224, 230),
    "cadetblue": (95, 158, 160),
    "forestgreen": (34, 139, 34),
    "seagreen": (46, 139, 87),
    "mediumseagreen": (60, 179, 113),
    "springgreen": (0, 255, 127),
    "limegreen": (50, 205, 50),
    "yellowgreen": (154, 205, 50),
    "darkolivegreen": (85, 107, 47),
    "olivedrab": (107, 142, 35),
    "lawngreen": (124, 252, 0),
    "chartreuse": (127, 255, 0),
    "greenyellow": (173, 255, 47),
    "darkkhaki": (189, 183, 107),
    "khaki": (240, 230, 140),
    "palegoldenrod": (238, 232, 170),
    "lightgoldenrodyellow": (250, 250, 210),
    "papayawhip": (255, 239, 213),
    "moccasin": (255, 228, 181),
    "peachpuff": (255, 218, 185),
    "sandybrown": (244, 164, 96),
    "navajowhite": (255, 222, 173),
    "wheat": (245, 222, 179),
    "burlywood": (222, 184, 135),
    "tan": (210, 180, 140),
    "rosybrown": (188, 143, 143),
    "darkgoldenrod": (184, 134, 11),
    "goldenrod": (218, 165, 32),
    "salmon": (250, 128, 114),
    "darksalmon": (233, 150, 122),
    "lightsalmon": (255, 160, 122),
    "indianred": (205, 92, 92),
    "firebrick": (178, 34, 34),
    "mediumvioletred": (199, 21, 133),
    "deeppink": (255, 20, 147),
    "hotpink": (255, 105, 180),
    "palevioletred": (219, 112, 147),
    "mediumorchid": (186, 85, 211),
    "darkorchid": (153, 50, 204),
    "blueviolet": (138, 43, 226),
    "mediumpurple": (147, 112, 219),
    "thistle": (216, 191, 216),
    "plum": (221, 160, 221),
    "orchid": (218, 112, 214),
    "mediumslateblue": (123, 104, 238),
    "darkslateblue": (72, 61, 139),
    "lavender": (230, 230, 250),
    "ghostwhite": (248, 248, 255),
    "aliceblue": (240, 248, 255),
    "azure": (240, 255, 255),
    "mintcream": (245, 255, 250),
    "honeydew": (240, 255, 240),
    "ivory": (255, 255, 240),
    "floralwhite": (255, 250, 240),
    "snow": (255, 250, 250),
    "mistyrose": (255, 228, 225),
    "seashell": (255, 245, 238),
    "oldlace": (253, 245, 230),
    "linen": (250, 240, 230),
    "antiquewhite": (250, 235, 215),
    "beige": (245, 245, 220),
    "whitesmoke": (245, 245, 245),
    "lavenderblush": (255, 240, 245),
    "dimgray": (105, 105, 105),
    "gainsboro": (220, 220, 220),
    "lightslategray": (119, 136, 153),
    "slategray": (112, 128, 144),
    "darkslategray": (47, 79, 79),
    "lightsteelblue": (176, 196, 222),
    "cornflowerblue": (100, 149, 237),
}


def get_metric_colors(metric_value: float | int | str) -> Tuple[str, str]:
    """
    Get background and text colors based on a metric value (0.0 to 1.0).

    Uses a LangSmith-style color system where:
    - 0.0: Bright red (failure)
    - 0.0 < x < 0.5: Dark red (poor)
    - 0.5 <= x < 0.9: Medium/Forest green (moderate to high)
    - 0.9 <= x < 1.0: Medium green (high)
    - 1.0: Bright green (perfect)

    Args:
        metric_value: The metric value as a float, int, or string

    Returns:
        Tuple of (background_color, text_color) as hex color strings
    """
    if not isinstance(metric_value, (float, int, str)):
        # Fallback for non-numeric values
        return DEFAULT_METRIC_GREY, "white"  # unified fallback

    # Try to convert to float if it's a string
    try:
        value = float(metric_value)
    except (ValueError, TypeError):
        # Fallback for non-convertible strings
        return DEFAULT_METRIC_GREY, "white"  # unified fallback

    if value == 0.0:
        # Bright red bullet/white text for failure values
        return "#D32F2F", "white"  # Crimson
    elif value > 0.0 and value < 0.5:
        # Dark red bullet/light red text for poor values
        return "#8B0000", "#fca5a5"  # Dark Red, light red
    elif value >= 0.5 and value < 1.0:
        # Medium green bullet/light green text for moderate values
        return "#2E7D32", "#86efac"  # Forest Green, light green
    elif value == 1.0:
        # Bright green bullet/white text for perfect values
        return "#00C853", "white"  # Vivid Green
    else:
        # Fallback for edge cases (negative values, > 1.0, etc.)
        return DEFAULT_METRIC_GREY, "white"  # unified fallback
