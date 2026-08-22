"""Keep pytest out of the fixture pack.

`tests/fixtures/*/repo` holds whole miniature projects, including files that
look like tests to pytest and are not: they are the subject a live session is
pointed at, and some of them need dependencies this repository does not have.
Collecting them turned `pytest tests/` into a collection error the moment two
fixtures happened to carry the same basename.

The project's own Stage 1 runs each `tests/test_*.py` directly, so this file is
about the other way in — anyone who types `pytest`, and CI if it ever does.
"""

collect_ignore_glob = ["fixtures/*"]
