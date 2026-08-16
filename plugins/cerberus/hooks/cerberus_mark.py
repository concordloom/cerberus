#!/usr/bin/env python3
"""PostToolUse hook — record that executable code changed and is unverified.

Fires after Edit/Write. When the edited file is source code (see
``cerberus_config.py``), append it to a marker file. The marker is meant to be cleared only
on a READY verdict from the cerberus skill; while it exists, the Stop hook
(``cerberus_gate.py``) refuses to let a readiness claim end the turn.

Edits to tests, docs and agent configuration do not set the marker: they are
not what the two stages verify.

Wire it up in ``.claude/settings.json``:

    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Write|Edit",
            "hooks": [
              {
                "type": "command",
                "command": "python3 \\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/cerberus_mark.py"
              }
            ]
          }
        ]
      }
    }
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from cerberus_config import Config  # noqa: E402


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        # A hook that crashes the agent is worse than a hook that misses one
        # edit; the Stop gate is the part that must be reliable.
        return 0

    for file_path in edited_paths(data):
        record(file_path, data)
    return 0


# Bash is excluded on purpose. `python3 app/service.py` in a command string
# names a source file that was *run*, not edited, and marking it would arm the
# gate for work nobody did. Codex reports the tool name; Claude Code restricts
# by matcher in settings, and sends no tool_name at all.
NOT_AN_EDITOR = {"bash", "shell", "run_command", "terminal"}

# Enough of a path to be worth asking the config about. The config decides
# whether it counts; this only has to stop prose being mistaken for a path.
PATH_LIKE = re.compile(r"[\w./~-]*[\w-]+\.[A-Za-z][\w]*")


def edited_paths(data: dict) -> list[str]:
    """Which files did this tool call write?

    Claude Code sends `tool_input.file_path`. Codex routes edits through
    `apply_patch`, and the shape of that payload is not documented — so rather
    than assume a schema, any path-like string in the tool input is offered to
    the config, which already knows what counts as source. Unverified against a
    real Codex session; see issue #27.
    """
    if str(data.get("tool_name") or "").lower() in NOT_AN_EDITOR:
        return []

    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return []

    named = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(named, str) and named:
        # Explicitly named: authoritative, taken as given.
        return [named]

    found = []
    for value in tool_input.values():
        if isinstance(value, str):
            found.extend(PATH_LIKE.findall(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    found.extend(PATH_LIKE.findall(item))
                elif isinstance(item, dict):
                    for inner in item.values():
                        if isinstance(inner, str):
                            found.extend(PATH_LIKE.findall(inner))
    # Scraped, not named — so it has to be corroborated. A path that exists is
    # a file the patch touched; one that does not is prose that happened to
    # contain a dot. The named branch above is exempt: there the tool told us.
    root = pathlib.Path(data.get("cwd") or ".")
    seen, unique = set(), []
    for candidate in found:
        if candidate in seen:
            continue
        seen.add(candidate)
        if (root / candidate).exists() or pathlib.Path(candidate).exists():
            unique.append(candidate)
    return unique


def record(file_path: str, data: dict) -> None:

    # CLAUDE_PROJECT_DIR first: cwd can be a subdirectory, and since the
    # containment check landed a wrong root no longer merely misplaces the
    # marker — it drops entries and the gate silently disarms.
    root = pathlib.Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    )
    cfg = Config.load(root)

    if not cfg.is_source_file(file_path):
        return

    marker = cfg.marker_path()
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        existing = marker.read_text(encoding="utf-8") if marker.exists() else ""
        # Keep the touched paths so the gate can name them back. Cheap dedup:
        # the list only has to be useful, not canonical.
        if file_path not in existing:
            marker.write_text(existing + file_path + "\n", encoding="utf-8")
    except Exception:
        pass


if __name__ == "__main__":
    sys.exit(main())
