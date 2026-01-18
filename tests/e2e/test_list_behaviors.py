import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.playwright]


def _pill_container(form_name: str, field: str) -> str:
    return f"#{form_name}_{field}_pills_container"


def _pill_selector(form_name: str, field: str, value: str) -> str:
    return f"{_pill_container(form_name, field)} span[data-value='{value}']"


def test_pill_add_remove_interactions(page, app_server):
    page.goto(app_server)
    page.wait_for_selector(_pill_container("left_form", "labels"))

    page.select_option("#left_form_labels_pills_container_dropdown", "Beta")
    page.wait_for_selector(_pill_selector("left_form", "labels", "Beta"))

    page.locator(_pill_selector("left_form", "labels", "Alpha")).locator(
        "button"
    ).click()
    page.wait_for_selector(
        _pill_selector("left_form", "labels", "Alpha"), state="detached"
    )


def test_list_add_and_delete_item(page, app_server):
    page.goto(app_server)
    page.wait_for_selector("[name='left_form_entries_0_title']", state="attached")

    page.locator("#left_form_left_form_entries_0_card > .uk-accordion-title").click()
    page.locator(
        "#left_form_left_form_entries_0_card button[hx-post='/form/left_form/list/add/entries']"
    ).click()
    page.wait_for_selector("[name^='left_form_entries_new_'][name$='_title']")

    page.once("dialog", lambda dialog: dialog.accept())
    page.locator(
        "#left_form_left_form_entries_0_card button[hx-delete='/form/left_form/list/delete/entries']"
    ).first.click()
    page.wait_for_selector("#left_form_left_form_entries_0_card", state="detached")
