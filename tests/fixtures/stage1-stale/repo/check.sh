#!/bin/sh
# The fast local check named in AGENTS.md, and the whole of the Stage 1 that an
# earlier setup recorded. Unit level only: it never opens the dashboard, and it
# never invokes the browser suite that lives beside it.
cd "$(dirname "$0")" || exit 1
python3 - <<'PY' || exit 1
from app.server import render_rows

assert render_rows(["a", "b"]) == "<tr><td>a</td></tr><tr><td>b</td></tr>"
assert "&lt;script&gt;" in render_rows(["<script>"]), "row content is not escaped"
assert render_rows([]) == ""
PY
printf stage1-ran > .stage1-ran
