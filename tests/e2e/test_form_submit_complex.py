import json

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.playwright]


def _wait_for_value(page, selector: str, expected: str) -> None:
    page.wait_for_function(
        """(args) => {
          const el = document.querySelector(args.selector);
          return el && el.value === args.expected;
        }""",
        arg={"selector": selector, "expected": expected},
    )


def test_complex_form_submit_success(page, complex_form_server):
    page.goto(complex_form_server)
    page.wait_for_selector("[name='complex_form_name']", state="attached")

    page.fill("[name='complex_form_name']", "Updated User")
    page.fill("[name='complex_form_age']", "42")
    page.fill("[name='complex_form_score']", "91.2")

    page.select_option("#complex_form_categories_pills_container_dropdown", "Beta")
    page.wait_for_selector(
        "#complex_form_categories_pills_container span[data-value='Beta']"
    )

    page.locator("#complex_form_complex_form_tags_0_card > .uk-accordion-title").click()
    page.locator(
        "#complex_form_complex_form_tags_0_card button[hx-post='/form/complex_form/list/add/tags']"
    ).click()
    page.fill("[name^='complex_form_tags_new_']", "added-tag")

    page.locator(
        "#complex_form_complex_form_addresses_0_card > .uk-accordion-title"
    ).click()
    page.locator(
        "#complex_form_complex_form_addresses_0_card button[hx-post='/form/complex_form/list/add/addresses']"
    ).click()
    new_street = page.locator(
        "[name^='complex_form_addresses_new_'][name$='_street']"
    ).first
    new_street.fill("987 Elm St")
    page.locator("[name^='complex_form_addresses_new_'][name$='_city']").first.fill(
        "Dallas"
    )

    address_card = new_street.locator("xpath=ancestor::li[1]")
    address_card.locator("button[hx-post*='/tags']").first.click()
    page.fill(
        "[name^='complex_form_addresses_new_'][name*='_tags_new_']",
        "office",
    )

    page.locator(
        "#complex_form_complex_form_contacts_0_card > .uk-accordion-title"
    ).click()
    page.locator(
        "#complex_form_complex_form_contacts_0_card button[hx-post='/form/complex_form/list/add/contacts']"
    ).click()
    new_contact = page.locator(
        "[name^='complex_form_contacts_new_'][name$='_name']"
    ).first
    new_contact.fill("Sam Smith")
    page.locator("[name^='complex_form_contacts_new_'][name$='_email']").first.fill(
        "sam@example.com"
    )

    contact_card = new_contact.locator("xpath=ancestor::li[1]")
    contact_card.locator("button[hx-post*='/phones']").first.click()
    page.fill(
        "[name^='complex_form_contacts_new_'][name*='_phones_new_']",
        "555-0202",
    )

    page.locator("#complex-form").evaluate("form => form.submit()")
    page.wait_for_url("**/submit", wait_until="domcontentloaded")
    page.wait_for_selector("#submit-result", state="attached")

    payload = page.locator("#submit-result").inner_text()
    data = json.loads(payload)

    assert data["name"] == "Updated User"
    assert data["age"] == 42
    assert "added-tag" in data["tags"]
    assert "Beta" in data["categories"]

    assert len(data["addresses"]) == 2
    assert data["addresses"][1]["street"] == "987 Elm St"
    assert data["addresses"][1]["city"] == "Dallas"
    assert "office" in data["addresses"][1]["tags"]

    assert len(data["contacts"]) == 2
    assert data["contacts"][1]["name"] == "Sam Smith"
    assert data["contacts"][1]["email"] == "sam@example.com"
    assert "555-0202" in data["contacts"][1]["phones"]


def test_complex_form_refresh_preserves_changes(page, complex_form_server):
    page.goto(complex_form_server)
    page.wait_for_selector("[name='complex_form_name']", state="attached")

    page.fill("[name='complex_form_name']", "Refreshed User")
    page.locator("button[uk-tooltip^='Update the form display']").click()

    _wait_for_value(page, "[name='complex_form_name']", "Refreshed User")


def test_complex_form_reset_restores_initial_values(page, complex_form_server):
    page.goto(complex_form_server)
    page.wait_for_selector("[name='complex_form_name']", state="attached")

    page.fill("[name='complex_form_name']", "Reset Me")
    page.once("dialog", lambda dialog: dialog.accept())
    page.locator("button[uk-tooltip^='Reset the form fields']").click()

    _wait_for_value(page, "[name='complex_form_name']", "Initial User")


def test_complex_form_validation_error(page, complex_form_server):
    page.goto(complex_form_server)
    page.wait_for_selector("[name='complex_form_age']", state="attached")

    page.fill("[name='complex_form_age']", "")
    page.locator("#complex-form").evaluate("form => form.submit()")
    page.wait_for_url("**/submit", wait_until="domcontentloaded")
    page.wait_for_selector("#submit-result", state="attached")

    payload = page.locator("#submit-result").inner_text()
    assert "Input should be a valid integer" in payload
