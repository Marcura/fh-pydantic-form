# Test StringFieldRenderer robustness as fallback renderer
import sys

sys.path.append("src")

from bs4 import BeautifulSoup
from pydantic.fields import FieldInfo

from fh_pydantic_form.field_renderers import StringFieldRenderer

# Test with various non-string types that might be passed as fallback
test_cases = [
    ("integer", 42),
    ("float", 3.14159),
    ("boolean_true", True),
    ("boolean_false", False),
    ("none_value", None),
    ("list_value", [1, 2, 3]),
    ("dict_value", {"key": "value", "number": 42}),
    ("empty_string", ""),
    ("multiline_string", "Line 1\nLine 2\nLine 3"),
]

print("Testing StringFieldRenderer robustness as fallback:")
print("=" * 60)

for test_name, test_value in test_cases:
    try:
        field_info = FieldInfo(annotation=str)  # This is what fallback would have
        renderer = StringFieldRenderer(
            field_name=f"test_{test_name}", field_info=field_info, value=test_value
        )

        # Try to render
        component = renderer.render_input()
        html = (
            component.__html__() if hasattr(component, "__html__") else str(component)
        )

        # Extract content from textarea
        soup = BeautifulSoup(html, "html.parser")
        textarea = soup.find("textarea")
        content = textarea.text if textarea else "NO TEXTAREA FOUND"
        rows = getattr(textarea, "attrs", {}).get("rows", "N/A") if textarea else "N/A"

        print(
            f"✅ {test_name:15} | Value: {test_value!r:25} | Content: {content!r:20} | Rows: {rows}"
        )

    except Exception as e:
        print(f"❌ {test_name:15} | Value: {test_value!r:25} | ERROR: {e}")

print()
print("Key Issues Found:")
print('- Boolean False becomes empty string due to "or \\"\\"\\" logic')
print("- Complex objects show ugly string representations")
print("- Row calculation only works for strings")
print("- Need robust string conversion for all types")
