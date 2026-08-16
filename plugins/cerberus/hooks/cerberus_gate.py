#!/usr/bin/env python3
"""Stop hook — refuse to end a turn that claims readiness without verification.

Blocks only when BOTH hold:

  1. the marker exists, meaning source code was edited and no READY verdict has
     cleared it, AND
  2. the agent's final message claims the work is done or working.

Turns that do not claim readiness are never blocked. The gate is aimed at one
moment — the over-claim — and not at ongoing work. A gate that interrupts
normal work gets switched off, and a gate that is off protects nothing.

The claim patterns are tunable through ``.claude/cerberus.json``. If this cries
wolf, narrow them there rather than deleting the hook.

Wire it up in ``.claude/settings.json``:

    {
      "hooks": {
        "Stop": [
          {
            "hooks": [
              {
                "type": "command",
                "command": "python3 \\"$CLAUDE_PROJECT_DIR\\"/.claude/hooks/cerberus_gate.py"
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

REASON = (
    "Cerberus gate: this message claims the work is ready, but source code was "
    "edited and has not been verified.\n"
    "\n"
    "Run the cerberus skill and complete both stages:\n"
    "  Stage 1 — try to break the code locally: build, tests, lint, consumption "
    "path for every value the change writes, completeness for the bug class, "
    "negative cases.\n"
    "  Stage 2 — try to break it on a live environment: a real end-to-end run, "
    "UI through a browser, API through real calls, and a counterexample per "
    "mechanism whose failure oracle can actually return BROKEN.\n"
    "\n"
    "Clear the marker only on a READY verdict. Nothing here prevents you "
    "deleting it early — that is on you.\n"
    "\n"
)

FILES_HEADER = "\nUnverified files:\n"

# Naming the file is the difference between an agent inventing its stages and
# an agent running this project's. The pointer used to live at SKILL.md:257,
# of 530 lines, and the refusal never mentioned it.
CONFIG_LINE = (
    "\nThe commands for both stages are in {path}, under `verification`.\n"
    "That block is for you to run; the other keys change what this hook does.\n"
)


def _last_assistant_text(transcript_path: str) -> str:
    """Return the text of the most recent assistant message in the transcript."""
    text = ""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if (event.get("role") or event.get("type")) != "assistant":
                    continue
                message = event.get("message") or event
                content = message.get("content")
                if isinstance(content, str):
                    text = content
                elif isinstance(content, list):
                    text = " ".join(
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
    except Exception:
        return ""
    return text


def main() -> int:
    # Blocking a Stop on Codex does not end the turn — it feeds a continuation
    # prompt back as new user input, and `stop_hook_active` says the turn has
    # already been continued that way. Blocking again from there is a loop:
    # block, continue, block, forever. Claude Code has no such semantics and
    # never sends the field, so this is inert there.
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    # CLAUDE_PROJECT_DIR first: cwd can be a subdirectory, and since the
    # containment check landed a wrong root no longer merely misplaces the
    # marker — it drops entries and the gate silently disarms.
    root = pathlib.Path(
        os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or os.getcwd()
    )
    cfg = Config.load(root)

    marker = cfg.marker_path()
    if not marker.exists():
        return 0  # nothing unverified — let the turn end

    # Codex hands the message to the Stop hook directly; Claude Code does not,
    # so the transcript is parsed only when it has to be. Reading a field beats
    # parsing a file, and the transcript format is the likelier of the two to
    # differ between agents.
    if data.get("stop_hook_active"):
        return 0

    text = data.get("last_assistant_message")
    if not isinstance(text, str) or not text:
        text = _last_assistant_text(data.get("transcript_path", ""))
    if not text or not cfg.claims_readiness(text):
        return 0  # mid-work, not claiming readiness

    try:
        pending = marker.read_text(encoding="utf-8").strip().splitlines()
    except Exception:
        pending = []
    listed = "\n".join(f"  - {p}" for p in pending[:20]) or "  (marker present)"
    if len(pending) > 20:
        listed += f"\n  ... and {len(pending) - 20} more"

    config = root / ".claude" / "cerberus.json"
    pointer = CONFIG_LINE.format(path=".claude/cerberus.json") if config.exists() else ""
    print(json.dumps({"decision": "block", "reason": REASON + pointer + FILES_HEADER + listed}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
