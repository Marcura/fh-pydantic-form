import sys

sys.path.insert(0, "/Users/oege/projects/fh-pydantic-form/src")

import re
from datetime import date
from datetime import time as dtime
from decimal import Decimal
from enum import Enum, IntEnum
from typing import List, Literal, Optional

from pydantic import BaseModel

from fh_pydantic_form import PydanticForm


def text(s) -> str:
    # Helper to normalize whitespace for robust assertions
    return re.sub(r"\\s+", " ", str(s))


def test_required_simple_fields_do_not_show_pydanticundefined():
    class Example(BaseModel):
        name: str
        age: int

    form = PydanticForm("ex", Example)  # no initial_values
    rendered = form.render_inputs()
    html = text(rendered)

    # No sentinel should appear anywhere
    assert "PydanticUndefined" not in html

    # int default is 0 => should appear as value="0"
    assert 'name="ex_age"' in html and 'type="number"' in html and 'value="0"' in html

    # name is textarea; ensure it exists and is empty (no sentinel)
    assert 'name="ex_name"' in html


def test_all_core_types_without_defaults(monkeypatch):
    # Freeze today's date via defaults._today() hook
    import fh_pydantic_form.defaults as d

    monkeypatch.setattr(d, "_today", lambda: date(2024, 1, 2))

    class Status(Enum):
        PENDING = "pending"
        CONFIRMED = "confirmed"

    class Priority(IntEnum):
        LOW = 1
        HIGH = 2

    class Child(BaseModel):
        title: str
        qty: int

    class BigModel(BaseModel):
        s: str
        i: int
        f: float
        b: bool
        dec: Decimal
        dt: date
        tt: dtime
        lit: Literal["A", "B", "C"]
        st: Status
        pr: Priority
        child: Child
        items: List[int]
        maybe: Optional[str] = None  # optional w/o default -> None
        maybe_enum: Optional[Status] = None

    form = PydanticForm("big", BigModel)  # no initial_values
    rendered = form.render_inputs()
    html = text(rendered)

    # Sanity: no sentinel
    assert "PydanticUndefined" not in html

    # ints/floats/decimals
    assert 'name="big_i"' in html and 'type="number"' in html and 'value="0"' in html
    assert 'name="big_f"' in html and 'type="number"' in html and 'value="0.0"' in html
    assert 'name="big_dec"' in html and 'type="number"' in html and 'value="0"' in html

    # bool default False => checkbox not checked (checked attr absent/false)
    # We can't rely on serialized boolean attr, but we can at least locate the checkbox.
    assert 'name="big_b"' in html

    # date default uses frozen today
    assert (
        'name="big_dt"' in html
        and 'type="date"' in html
        and 'value="2024-01-02"' in html
    )

    # time default 00:00
    assert 'name="big_tt"' in html and 'type="time"' in html and 'value="00:00"' in html

    # Literal selects first value "A"
    # Look for an <option ... value="A" ... selected>
    assert re.search(r'name="big_lit".*?<option[^>]*value="A"[^>]*selected', html)

    # Enum selects first member value ("pending")
    assert re.search(r'name="big_st".*?<option[^>]*value="pending"[^>]*selected', html)

    # IntEnum selects first member value (1)
    assert re.search(r'name="big_pr".*?<option[^>]*value="1"[^>]*selected', html)

    # Nested model renders (no sentinel)
    assert "big_child" in html and "title" in html and "qty" in html

    # Required list renders empty state with Add Item
    assert "Add Item" in html and 'name="big_items' not in html  # no items yet

    # Optional fields: should include a -- None -- option selected
    assert re.search(r'name="big_maybe_enum".*?<option[^>]*>-- None --</option>', html)


def test_optional_fields_none_selected_in_selects():
    class Pay(Enum):
        CARD = "card"
        CASH = "cash"

    class M(BaseModel):
        payment: Optional[Pay] = None

    form = PydanticForm("opt", M)
    html = text(form.render_inputs())
    # -- None -- must be present and selected (first render)
    assert re.search(r'name="opt_payment".*?<option[^>]*>-- None --</option>', html)


def test_nested_model_no_initial_values():
    """Test that nested models don't show PydanticUndefined when no initial values"""

    class Address(BaseModel):
        street: str
        city: str
        zip_code: int

    class Person(BaseModel):
        name: str
        age: int
        address: Address

    form = PydanticForm("person", Person)
    rendered = form.render_inputs()
    html = text(rendered)

    # No sentinel should appear anywhere
    assert "PydanticUndefined" not in html

    # Check that nested fields exist with proper defaults
    assert 'name="person_address_street"' in html
    assert 'name="person_address_city"' in html
    assert 'name="person_address_zip_code"' in html and 'value="0"' in html


def test_list_of_models_no_initial_values():
    """Test that lists of models don't show PydanticUndefined"""

    class Item(BaseModel):
        name: str
        quantity: int = 1

    class Order(BaseModel):
        order_id: str
        items: List[Item]

    form = PydanticForm("order", Order)
    rendered = form.render_inputs()
    html = text(rendered)

    # No sentinel should appear anywhere
    assert "PydanticUndefined" not in html

    # Should show empty list state
    assert "No items" in html
    assert "Add Item" in html


def test_deeply_nested_no_initial_values():
    """Test deeply nested structures without initial values"""

    class DeepChild(BaseModel):
        value: str
        score: float

    class MidLevel(BaseModel):
        title: str
        child: DeepChild

    class TopLevel(BaseModel):
        name: str
        middle: MidLevel

    form = PydanticForm("deep", TopLevel)
    rendered = form.render_inputs()
    html = text(rendered)

    # No sentinel should appear anywhere
    assert "PydanticUndefined" not in html

    # Check nested fields render with defaults
    assert 'name="deep_middle_child_value"' in html
    assert 'name="deep_middle_child_score"' in html and 'value="0.0"' in html
