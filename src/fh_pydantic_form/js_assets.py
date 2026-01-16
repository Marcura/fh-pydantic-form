from __future__ import annotations

from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=None)
def load_js_asset(filename: str) -> str:
    """Load bundled JavaScript assets for inline script tags."""
    return (
        resources.files("fh_pydantic_form.assets")
        .joinpath(filename)
        .read_text(encoding="utf-8")
    )
