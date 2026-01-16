"""
Shared constants and sentinel values used across the library.
"""


class _Unset:
    """Sentinel class to indicate an unset value."""

    pass


_UNSET = _Unset()

# HTML data attributes used for JavaScript interactions
# These constants ensure consistency between Python renderers and JS handlers
ATTR_FIELD_PATH = "data-field-path"
ATTR_FIELD_NAME = "data-field-name"
ATTR_INPUT_PREFIX = "data-input-prefix"
ATTR_ALL_CHOICES = "data-all-choices"
ATTR_PILL_FIELD = "data-pill-field"
ATTR_COMPARE_GRID = "data-fhpf-compare-grid"
ATTR_COMPARE_NAME = "data-fhpf-compare-name"
ATTR_LEFT_PREFIX = "data-fhpf-left-prefix"
ATTR_RIGHT_PREFIX = "data-fhpf-right-prefix"
