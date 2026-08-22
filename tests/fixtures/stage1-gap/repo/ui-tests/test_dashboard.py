"""Browser coverage for the operator dashboard, against a local instance."""

BASE_URL = "http://localhost:8931"


def test_dashboard_renders(page):
    page.goto(f"{BASE_URL}/")
    assert page.title() == "Operator dashboard"


def test_login_rejects_a_bad_password(page):
    page.goto(f"{BASE_URL}/login")
    page.fill("#password", "wrong")
    page.click("button[type=submit]")
    assert page.locator(".error").is_visible()
