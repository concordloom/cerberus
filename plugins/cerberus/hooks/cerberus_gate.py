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

#: How many times to refuse before ending the turn instead of asking again.
#: Enough for an agent that intends to verify; short of a loop for one that
#: does not.
REFUSAL_LIMIT = 3


def _bump_refusals(cfg) -> int:
    """Count this hook's own refusals for the current marker.

    Kept beside the marker and removed with it, so clearing on a READY verdict
    resets the count too. The alternative — reading `stop_hook_active` — asks a
    different question: whether *any* Stop hook continued the turn.
    """
    path = cfg.marker_path().with_name(cfg.marker_path().name + ".refusals")
    try:
        count = int(path.read_text(encoding="utf-8").strip() or 0)
    except Exception:
        count = 0
    count += 1
    try:
        path.write_text(str(count), encoding="utf-8")
    except Exception:
        pass
    return count

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

    # Both agents hand the last assistant message to the Stop hook, and both
    # recommend it over the transcript: the transcript is written asynchronously
    # and may not yet carry the final message when the hook fires. The parse is
    # the fallback, not the other way round.
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

    # Whichever one this project has. Hardcoding .claude meant a Codex project
    # was never told where its own commands were — the exact gap this line was
    # added to close.
    pointer = ""
    for relative in Config.CONFIG_PATHS:
        if (root / relative).exists():
            pointer = CONFIG_LINE.format(path=relative)
            break
    reason = REASON + pointer + FILES_HEADER + listed

    # A blocked Stop does not always end the turn: on some agents the reason is
    # fed back as a new prompt and the turn continues, with no documented cap.
    # Refusing forever would be a loop; going silent was worse and shipped once
    # — the claim went through on the second attempt.
    #
    # So it counts its own refusals. `stop_hook_active` cannot do this: it means
    # *some* Stop hook already continued the turn, not this one, so any other
    # hook — `/goal`, for instance — made cerberus's very first refusal a hard
    # stop and the agent never got the continuation it needs to go and verify.
    refusals = _bump_refusals(cfg)
    if refusals > REFUSAL_LIMIT:
        print(json.dumps({
            "continue": False,
            "stopReason": reason,
            "systemMessage": (
                f"Cerberus refused {refusals - 1} times and the work is still "
                "unverified. Ending the turn rather than asking again."
            ),
        }))
        return 0

    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
