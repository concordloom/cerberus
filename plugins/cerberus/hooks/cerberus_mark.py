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


# Tools that run things rather than write them. `python3 app/service.py` names
# a source file that was *executed*, and a read tool names one that was *read*;
# marking either arms the gate for work nobody did.
NOT_AN_EDITOR = re.compile(
    r"bash|shell|terminal|exec|run_command|container\.exec|read|view|grep|search"
    r"|list|get_|head_|tail_|stat|info|find|glob|fetch|open",
    re.I,
)

# A named tool has to look like one that writes before a bare `path` is taken
# as an edit. Without this, any unrecognised read tool sending `path` armed the
# gate — `mcp__filesystem__get_file_info` did, and so would anything new.
AN_EDITOR = re.compile(
    r"write|edit|patch|create|update|modify|replace|move|rename|delete|remove|apply|insert",
    re.I,
)

# The envelope a patch tool wraps its files in. Only these headers name a file
# the patch *touched* — scraping every line instead meant a patch that merely
# mentioned `app/service.py` in a README sentence armed the gate for it, which
# is the same trap as marking a file that was run.
PATCH_HEADER = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File: (.+?)\s*$|^\*\*\* Move to: (.+?)\s*$",
    re.M,
)


def edited_paths(data: dict) -> list[str]:
    """Which files did this tool call write?

    Claude Code sends `tool_input.file_path`. Codex documents that Bash and
    `apply_patch` both use `tool_input.command`, so a patch is recognised by its
    envelope rather than by scraping the diff — and a rename records both names,
    since the old one stopped existing and the new one did not exist before.
    """
    name = str(data.get("tool_name") or "")
    if name and NOT_AN_EDITOR.search(name):
        return []

    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        return []

    named = tool_input.get("file_path") or tool_input.get("path")
    if isinstance(named, str) and named:
        return [named]

    found = []
    for key in ("source", "destination", "old_path", "new_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value and value not in found:
            found.append(value)
    if found:
        return found

    for value in tool_input.values():
        if not isinstance(value, str):
            continue
        for add, moved in PATCH_HEADER.findall(value):
            for candidate in (add, moved):
                if candidate and candidate not in found:
                    found.append(candidate)
    return found


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
