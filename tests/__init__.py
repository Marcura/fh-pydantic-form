import html

import fasthtml.common as fh


def to_html(component) -> str:
    """Render any FastHTML component to full HTML."""
    # fh.render returns the full markup; fall back to str() if not present
    return getattr(fh, "render", str)(component)


def unescaped(text: str) -> str:
    """Convenience to unescape HTML entities including hex-encoded ones."""
    # First unescape standard HTML entities like &quot; &amp; etc.
    text = html.unescape(text)
    # Then handle hex-encoded entities like &#x27; manually
    import re

    # Replace &#x followed by hex digits and semicolon
    text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
    return text
