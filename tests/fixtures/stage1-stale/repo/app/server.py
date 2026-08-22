"""The operator dashboard. Renders rows into the table the UI suite drives."""

import html


def render_rows(values):
    return "".join(f"<tr><td>{html.escape(v)}</td></tr>" for v in values)
