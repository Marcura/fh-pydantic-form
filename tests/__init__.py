import html

import fasthtml.common as fh


def to_html(component) -> str:
    """Render any FastHTML component to full HTML."""
    # Use to_xml for proper HTML serialization, fall back to __html__ or str()
    if hasattr(fh, "to_xml"):
        return fh.to_xml(component)
    if hasattr(component, "__html__"):
        return component.__html__()
    return str(component)


def unescaped(text: str) -> str:
    """Convenience to unescape HTML entities including hex-encoded ones."""
    # First unescape standard HTML entities like &quot; &amp; etc.
    text = html.unescape(text)
    # Then handle hex-encoded entities like &#x27; manually
    import re

    # Replace &#x followed by hex digits and semicolon
    text = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), text)
    return text
