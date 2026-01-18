import json

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.playwright]


def _copy_button_selector(path: str) -> str:
    return f"button[onclick*=\"fhpfPerformCopy('{path}',\"]"


def _field_selector(name: str) -> str:
    return f"[name='{name}']"


def _field_prefix_selector(prefix: str, suffix: str) -> str:
    return f"[name^='{prefix}'][name$='{suffix}']"


def _fill(page, name: str, value: str) -> None:
    page.fill(_field_selector(name), value)


def _read_value(page, name: str) -> str:
    return page.locator(_field_selector(name)).input_value()


def _wait_for_value(page, selector: str, expected: str) -> None:
    page.wait_for_function(
        """(args) => {
          const el = document.querySelector(args.selector);
          return el && el.value === args.expected;
        }""",
        arg={"selector": selector, "expected": expected},
    )


def _click_copy(page, path: str) -> None:
    page.locator(_copy_button_selector(path)).first.click()


def _open_entry_item(page, form_name: str, idx: int) -> None:
    item_id = f"{form_name}_{form_name}_entries_{idx}_card"
    page.locator(f"#{item_id} > .uk-accordion-title").click()


def _is_entry_open(page, form_name: str, idx: int) -> bool:
    item_id = f"{form_name}_{form_name}_entries_{idx}_card"
    return page.locator(f"#{item_id}").evaluate(
        "el => el.classList.contains('uk-open')"
    )


def test_copy_scalar_field(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(_field_selector("left_form_title"))

    _fill(page, "left_form_title", "Updated Title")
    _click_copy(page, "title")

    assert _read_value(page, "right_form_title") == "Updated Title"


def test_copy_list_item_adds_and_copies(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(
        _field_selector("left_form_entries_1_title"), state="attached"
    )

    _click_copy(page, "entries[1]")

    page.wait_for_selector(
        _field_prefix_selector("right_form_entries_new_", "_title"),
        state="attached",
    )
    _wait_for_value(
        page, _field_prefix_selector("right_form_entries_new_", "_title"), "Entry One"
    )


def test_copy_nested_list_item_with_subfields(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(
        _field_selector("left_form_entries_0_notes_0_text"), state="attached"
    )

    _open_entry_item(page, "left_form", 0)
    _click_copy(page, "entries[0].notes[0]")

    page.wait_for_selector(
        _field_prefix_selector("right_form_entries_0_notes_new_", "_text"),
        state="attached",
    )
    _wait_for_value(
        page,
        _field_prefix_selector("right_form_entries_0_notes_new_", "_text"),
        "Left Note A",
    )


def test_copy_pill_fields(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("#left_form_labels_pills_container")

    _click_copy(page, "labels")

    page.wait_for_selector("#right_form_labels_pills_container")
    alpha = page.locator("#right_form_labels_pills_container span[data-value='Alpha']")
    gamma = page.locator("#right_form_labels_pills_container span[data-value='Gamma']")
    beta = page.locator("#right_form_labels_pills_container span[data-value='Beta']")

    assert alpha.count() == 1
    assert gamma.count() == 1
    assert beta.count() == 0


def test_full_list_copy_aligns_lengths(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(
        _field_selector("left_form_entries_1_title"), state="attached"
    )

    _click_copy(page, "entries")

    _wait_for_value(page, _field_selector("right_form_entries_0_title"), "Entry Zero")
    _wait_for_value(
        page, _field_prefix_selector("right_form_entries_new_", "_title"), "Entry One"
    )


def test_accordion_state_preserved_on_copy(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(
        _field_selector("left_form_entries_0_title"), state="attached"
    )

    _open_entry_item(page, "left_form", 0)
    assert _is_entry_open(page, "left_form", 0) is True

    _click_copy(page, "title")
    assert _is_entry_open(page, "left_form", 0) is True


def test_submit_after_copy_parses_new_items(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(_field_selector("left_form_title"))

    _fill(page, "left_form_title", "Submit Title")

    _click_copy(page, "title")
    _click_copy(page, "entries[1]")
    _open_entry_item(page, "left_form", 0)
    _click_copy(page, "entries[0].notes[0]")
    _click_copy(page, "labels")

    page.wait_for_selector(
        _field_prefix_selector("right_form_entries_new_", "_title"),
        state="attached",
    )
    _wait_for_value(
        page, _field_prefix_selector("right_form_entries_new_", "_title"), "Entry One"
    )
    page.wait_for_selector(
        _field_prefix_selector("right_form_entries_0_notes_new_", "_text"),
        state="attached",
    )
    _wait_for_value(
        page,
        _field_prefix_selector("right_form_entries_0_notes_new_", "_text"),
        "Left Note A",
    )

    page.locator("#comparison-form").evaluate("form => form.submit()")
    page.wait_for_url("**/submit", wait_until="domcontentloaded")
    page.wait_for_selector("#submit-result", state="attached")

    payload = page.locator("#submit-result").inner_text()
    data = json.loads(payload)

    right = data["right"]
    assert right["title"] == "Submit Title"
    assert len(right["entries"]) == 2
    assert right["entries"][1]["title"] == "Entry One"
    assert right["entries"][0]["notes"][0]["text"] == "Left Note A"
    assert set(right["labels"]) == {"Alpha", "Gamma"}
