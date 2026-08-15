#!/usr/bin/env python3
"""PostToolUse hook — record that executable code changed and is unverified.

Fires after Edit/Write. When the edited file is source code (see
``cerberus_config.py``), append it to a marker file. The marker is cleared only
by a READY verdict from the cerberus skill; while it exists, the Stop hook
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

    tool_input = data.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("path") or ""

    root = pathlib.Path(data.get("cwd") or os.getcwd())
    cfg = Config.load(root)

    if not cfg.is_source_file(file_path):
        return 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
