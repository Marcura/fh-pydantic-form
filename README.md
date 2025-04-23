# fh-pydantic-form

**Generate HTML forms from Pydantic models for your FastHTML applications.**

`fh-pydantic-form` simplifies creating web forms for [FastHTML](https://github.com/AnswerDotAI/fasthtml) by automatically generating the necessary HTML input elements based on your Pydantic model definitions. It integrates seamlessly with  and leverages [MonsterUI](https://github.com/AnswerDotAI/monsterui) components for styling.

<details >
    <summary>show demo screen recording</summary>
<video src="https://private-user-images.githubusercontent.com/27999937/436237879-feabf388-22af-43e6-b054-f103b8a1b6e6.mp4" controls="controls" style="max-width: 730px;">
</video>
</details>

## Purpose

-   **Reduce Boilerplate:** Automatically render form inputs (text, number, checkbox, select, date, time, etc.) based on Pydantic field types and annotations.
-   **Data Validation:** Leverage Pydantic's validation rules directly from form submissions.
-   **Nested Structures:** Support for nested Pydantic models and lists of models/simple types.
-   **Dynamic Lists:** Built-in HTMX endpoints and JavaScript for adding, deleting, and reordering items in lists within the form.
-   **Customization:** Easily register custom renderers for specific Pydantic types or fields.

## Installation

You can install `fh-pydantic-form` using either `pip` or `uv`.

**Using pip:**

```bash
pip install fh-pydantic-form
```

Using uv:
```bash
uv add fh-pydantic-form
```

This will also install necessary dependencies like `pydantic`, `python-fasthtml`, and `monsterui`.


# Basic Usage


```python

# examples/simple_example.py
import fasthtml.common as fh
import monsterui.all as mui
from pydantic import BaseModel, ValidationError

# 1. Import the form renderer
from fh_pydantic_form import PydanticForm

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        # Add list_manipulation_js() if using list fields
        # from fh_pydantic_form import list_manipulation_js
        # list_manipulation_js(),
    ],
    pico=False, # Using MonsterUI, not PicoCSS
    live=True,  # Enable live reload for development
)

# 2. Define your Pydantic model
class SimpleModel(BaseModel):
    """Model representing a simple form"""
    name: str = "Default Name"
    age: int
    is_active: bool = True

# 3. Create a form renderer instance
#    - 'my_form': Unique name for the form (used for prefixes and routes)
#    - SimpleModel: The Pydantic model class
form_renderer = PydanticForm("my_form", SimpleModel)

# (Optional) Register list manipulation routes if your model has List fields
# form_renderer.register_routes(app)

# 4. Define routes
@rt("/")
def get():
    """Display the form"""
    return fh.Div(
        mui.Container(
            mui.Card(
                mui.CardHeader("Simple Pydantic Form"),
                mui.CardBody(
                    # Use MonsterUI Form component for structure
                    mui.Form(
                        # Render the inputs using the renderer
                        form_renderer.render_inputs(),
                        # Add standard form buttons
                        mui.Button("Submit", type="submit", cls=mui.ButtonT.primary),
                        # HTMX attributes for form submission
                        hx_post="/submit_form",
                        hx_target="#result", # Target div for response
                        hx_swap="innerHTML",
                        # Set a unique ID for the form itself for refresh/reset inclusion
                        id=f"{form_renderer.name}-form",
                    )
                ),
            ),
            # Div to display validation results
            fh.Div(id="result"),
        ),
    )

@rt("/submit_form")
async def post_submit_form(req):
    """Handle form submission and validation"""
    try:
        # 5. Validate the request data against the model
        validated_data: SimpleModel = await form_renderer.model_validate_request(req)

        # Success: Display the validated data
        return mui.Card(
            mui.CardHeader(fh.H3("Validation Successful")),
            mui.CardBody(
                fh.Pre(
                    validated_data.model_dump_json(indent=2),
                )
            ),
            cls="mt-4",
        )
    except ValidationError as e:
        # Validation Error: Display the errors
        return mui.Card(
            mui.CardHeader(fh.H3("Validation Error", cls="text-red-500")),
            mui.CardBody(
                fh.Pre(
                    e.json(indent=2),
                )
            ),
            cls="mt-4",
        )

if __name__ == "__main__":
    fh.serve()

```
## Key Features

-   **Automatic Field Rendering:** Handles `str`, `int`, `float`, `bool`, `date`, `time`, `Optional`, `Literal`, nested `BaseModel`s, and `List`s out-of-the-box.
-   **Sensible Defaults:** Uses appropriate HTML5 input types (`text`, `number`, `date`, `time`, `checkbox`, `select`).
-   **Labels & Placeholders:** Generates labels from field names (converting snake_case to Title Case) and basic placeholders.
-   **Descriptions as Tooltips:** Uses `Field(description=...)` from Pydantic to create tooltips (`uk-tooltip` via UIkit).
-   **Required Fields:** Automatically adds the `required` attribute based on field definitions (considering `Optional` and defaults).
-   **Disabled Fields:** Disable the whole form with `disabled=True` or disable specific fields with `disabled_fields`
-   **Collapsible Nested Models:** Renders nested Pydantic models in collapsible details/summary elements for better form organization and space management.
-   **List Manipulation:**
    -   Renders lists of simple types or models in accordion-style cards with an enhanced UI.
    -   Provides HTMX endpoints (registered via `register_routes`) for adding and deleting list items.
    -   Includes JavaScript (`list_manipulation_js()`) for client-side reordering (moving items up/down).
-   **Form Refresh & Reset:**
    -   Provides HTMX-powered "Refresh" and "Reset" buttons (`form_renderer.refresh_button()`, `form_renderer.reset_button()`).
    -   Refresh updates list item summaries or other dynamic parts without full page reload.
    -   Reset reverts the form to its initial values.
-   **Custom Renderers:** Register your own `BaseFieldRenderer` subclasses for specific Pydantic types or complex field logic using `FieldRendererRegistry` or by passing `custom_renderers` during `PydanticForm` initialization.
-   **Form Data Parsing:** Includes logic (`form_renderer.parse` and `form_renderer.model_validate_request`) to correctly parse submitted form data (handling prefixes, list indices, nested structures, boolean checkboxes, etc.) back into a dictionary suitable for Pydantic validation.

## disabled fields

You can disable the full form with `PydanticForm("my_form", FormModel, disabled=True)` or disable specific fields with `PydanticForm("my_form", FormModel, disabled_fields=["field1", "field3"])`.

 
## Manipulating lists fields 

When you have `BaseModels` with fields that are e.g. `List[str]` or even `List[BaseModel]` you want to be able to easily edit the list by adding, deleting and moving items. For this we need a little bit of javascript and register some additional routes:

```python
from fh_pydantic_form import PydanticForm, list_manipulation_js

app, rt = fh.fast_app(
    hdrs=[
        mui.Theme.blue.headers(),
        list_manipulation_js(),
    ],
    pico=False,
    live=True,
)


class ListModel(BaseModel):
    name: str = ""
    tags: List[str] = Field(["tag1", "tag2"])


form_renderer = PydanticForm("list_model", ListModel)
form_renderer.register_routes(app)
```

## Refreshing and resetting the form

You can set the initial values of the form by passing an instantiated BaseModel:

```python
form_renderer = PydanticForm("my_form", ListModel, initial_values=ListModel(name="John", tags=["happy", "joy"]))
```

You can reset the form back to these initial values by adding a `form_render.reset_button()` to your UI:

```python
mui.Form(
    form_renderer.render_inputs(),
    fh.Div(
        mui.Button("Validate and Show JSON",cls=mui.ButtonT.primary,),
        form_renderer.refresh_button(),
        form_renderer.reset_button(),
    ),
    hx_post="/submit_form",
    hx_target="#result",
    hx_swap="innerHTML",
)
```

The refresh button 🔄 refreshes the list item labels. These are rendered initially to summarize the underlying item, but do not automatically update after editing unless refreshed. You can also use the 🔄 icon next to the list field label. 


## Custom renderers

The library is extensible by adding your own input renderers for your types. This can be used to override e.g. the default BaseModelFieldRenderer for nested BaseModels, but also to register types that are not (yet) supported (but submit a PR then as well!)

You can register a renderer based on type, type str, or a predicate function:

```python
from fh_pydantic_form import FieldRendererRegistry

from fh_pydantic_form.field_renderers import BaseFieldRenderer

class CustomDetail(BaseModel):
    value: str = "Default value"
    confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"

    def __str__(self) -> str:
        return f"{self.value} ({self.confidence})"


class CustomDetailFieldRenderer(BaseFieldRenderer):
    """display value input and dropdown side by side"""

    def render_input(self):
        value_input = fh.Div(
            mui.Input(
                value=self.value.get("value", ""),
                id=f"{self.field_name}_value",
                name=f"{self.field_name}_value",
                placeholder=f"Enter {self.original_field_name.replace('_', ' ')} value",
                cls="uk-input w-full",  
            ),
            cls="flex-grow", # apply some custom css
        )

        confidence_options_ft = [
            fh.Option(
                opt, value=opt, selected=(opt == self.value.get("confidence", "MEDIUM"))
            )
            for opt in ["HIGH", "MEDIUM", "LOW"]
        ]

        confidence_select = mui.Select(
            *confidence_options_ft,
            id=f"{self.field_name}_confidence",
            name=f"{self.field_name}_confidence",
            cls_wrapper="w-[110px] min-w-[110px] flex-shrink-0",  # apply some custom css
        )

        return fh.Div(
            value_input,
            confidence_select,
            cls="flex items-start gap-2 w-full",  # apply some custom css
        )


# these are all equivalent. You can either register the type directly
FieldRendererRegistry.register_type_renderer(CustomDetail, CustomDetailFieldRender)
# or just by the name of the type
FieldRendererRegistry.register_type_name_renderer("CustomDetail", CustomDetailFieldRender)
# or register I predicate function
FieldRendererRegistry.register_type_renderer_with_predicate(lambda: x: isinstance(x, CustomDetail), CustomDetailFieldRender)
```

You can also pass these directly to the `PydanticForm` with the custom_renderers argument:

```python

form_renderer = PydanticForm(
    form_name="main_form",
    model_class=ComplexSchema,
    initial_values=initial_values,
    custom_renderers=[
        (CustomDetail, CustomDetailFieldRenderer)
    ],  # Register Detail renderer
)
```

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.





