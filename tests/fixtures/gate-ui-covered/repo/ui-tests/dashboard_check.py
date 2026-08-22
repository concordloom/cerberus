"""Browser-facing checks for the dashboard, against a local instance.

Starts the app on loopback, fetches the page a person would open, and asserts
on what comes back. Hard-coded to 127.0.0.1: this proves the interface locally
and is not a route to any deployed stand.
"""

import re
import sys
import threading
import urllib.request

sys.path.insert(0, ".")
from app.server import serve  # noqa: E402

PORT = 8931
BASE_URL = f"http://127.0.0.1:{PORT}"


def fetch(server):
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    with urllib.request.urlopen(f"{BASE_URL}/", timeout=5) as response:
        return response.read().decode("utf-8")


def main():
    server = serve(PORT)
    try:
        page = fetch(server)
    finally:
        server.server_close()

    failures = []
    if "<h1>Operator dashboard</h1>" not in page:
        failures.append("the dashboard heading is missing")
    rows = re.findall(r"<tr><td>(.*?)</td></tr>", page)
    if len(rows) < 3:
        failures.append(f"the table rendered {len(rows)} rows, expected the three accounts")
    if not re.search(r'<button id="refresh"[^>]*onclick=', page):
        failures.append("the refresh button has no handler bound")
    if "<!--ROWS-->" in page:
        failures.append("the row placeholder was never substituted")

    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
