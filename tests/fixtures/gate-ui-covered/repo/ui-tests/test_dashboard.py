"""Browser coverage for the operator dashboard, against a local instance."""

BASE_URL = "http://localhost:8931"


def test_refresh_repaints_the_table(page):
    page.goto(f"{BASE_URL}/")
    page.click("#refresh")
    assert page.locator("#rows tr").count() > 0
