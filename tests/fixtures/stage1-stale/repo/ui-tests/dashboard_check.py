"""Drives the rendered dashboard. Nothing in the documented route runs this."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.server import render_rows

page = pathlib.Path(__file__).resolve().parent.parent / "web" / "index.html"
assert page.is_file(), "the dashboard page is missing"
assert 'id="rows"' in page.read_text(encoding="utf-8"), "no table to render into"
assert render_rows(["ok"]) == "<tr><td>ok</td></tr>"
