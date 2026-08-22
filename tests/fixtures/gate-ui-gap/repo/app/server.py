def render_dashboard(rows):
    return "\n".join(f"<tr><td>{row}</td></tr>" for row in rows)
