"""The dashboard the operator opens, and the rows it renders."""

import html
import http.server

TEMPLATE_PATH = "web/index.html"
ROWS = ["anthropic", "openai", "mistral"]


def render_rows(rows):
    return "".join(f"<tr><td>{html.escape(str(row))}</td></tr>" for row in rows)


def render_dashboard(rows=None):
    with open(TEMPLATE_PATH, encoding="utf-8") as handle:
        page = handle.read()
    return page.replace("<!--ROWS-->", render_rows(ROWS if rows is None else rows))


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = render_dashboard().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def serve(port):
    return http.server.HTTPServer(("127.0.0.1", port), Handler)
