#!/usr/bin/env python3
"""Fail closed on what a live `gopnik` run must have done to a fixture.

The gate is the product, and until this script existed nothing executed it.
`plugins/gopnik/skills/gopnik/SKILL.md` was checked as prose — three of the
forty tests in `tests/test_guides.py` touch it, all of them reading wording it
shares with setup — so a revision that made the gate answer `READY` to
everything would have passed every check in the repository.

What makes this a check rather than a keyword search is the pair. Reading the
verdict alone is satisfied by a constant: `gate-red-stage1` passes for a gate
stuck on `NOT READY`, `gate-ready-scoped` passes for one stuck on `READY`. So
each fixture also has to show *the work behind its verdict* — that the project's
own check really ran, proven from outside the transcript, and that the verifier
did not quietly repair the subject it was judging.

usage: check_live_gate_turn.py FIXTURE_DIR TRANSCRIPT WORKDIR
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

from check_live_setup_turn import (
    fail,
    final_result,
    nested_dicts,
    records,
    tool_results,
)

#: Keys every gate fixture owes. A fixture missing one would silently weaken the
#: cell rather than fail it, which is the failure mode this whole file is about.
REQUIRED = ("role", "prompt", "verdict", "runs", "marker", "unchanged")


def expectations(directory: pathlib.Path) -> dict:
    body = json.loads((directory / "expected.json").read_text(encoding="utf-8"))
    if body.get("role") != "gate":
        raise ValueError(f"{directory}: expected.json is not a gate fixture")
    missing = [key for key in REQUIRED if key not in body]
    if missing:
        raise ValueError(f"{directory}: expected.json is missing {missing}")
    if body["verdict"] not in ("READY", "NOT READY"):
        raise ValueError(f"{directory}: verdict must be READY or NOT READY")
    return body


def says_not_ready(text: str) -> bool:
    return re.search(r"\bnot[\s_-]*ready\b", text, re.IGNORECASE) is not None


def says_ready(text: str) -> bool:
    """`READY` on its own.

    The negative lookbehind is the whole point. `"READY" in text` is true of
    `NOT READY`, so the obvious implementation makes the READY fixture
    unfalsifiable while reading green — the one bug that would disable half of
    this pair without failing anything.
    """
    return re.search(r"(?<!not[\s_-])\bready\b", text, re.IGNORECASE) is not None


def ran_the_check(items: list[object], command: str) -> list[str]:
    """Ids of shell tool calls that invoked the fixture's own Stage 1."""
    needle = command.lstrip("./")
    found = []
    for item in items:
        for value in nested_dicts(item):
            if value.get("type") != "tool_use":
                continue
            if str(value.get("name") or "").lower() != "bash":
                continue
            payload = value.get("input")
            if not isinstance(payload, dict):
                continue
            if needle in str(payload.get("command") or "") and isinstance(
                value.get("id"), str
            ):
                found.append(value["id"])
    return found


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        return fail("usage: check_live_gate_turn.py FIXTURE_DIR TRANSCRIPT WORKDIR")

    fixture = pathlib.Path(argv[1])
    transcript = pathlib.Path(argv[2])
    workdir = pathlib.Path(argv[3])

    try:
        expected = expectations(fixture)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return fail(str(exc))

    try:
        items = records(transcript)
        _, result = final_result(items)
    except (OSError, ValueError) as exc:
        return fail(str(exc))

    # 1. The verdict itself, with the substring trap handled in both directions.
    if expected["verdict"] == "NOT READY":
        if not says_not_ready(result):
            return fail(f"the run did not return NOT READY:\n{result}")
    else:
        if says_not_ready(result):
            return fail(f"the run returned NOT READY where READY was due:\n{result}")
        if not says_ready(result):
            return fail(f"the run returned no READY verdict:\n{result}")

    # 2. The reason. A verdict without it cannot be told from a coin toss that
    #    landed the right way up.
    for shape in expected.get("must_match", []):
        if not re.search(shape, result):
            return fail(f"the verdict does not carry {shape!r}:\n{result}")
    for shape in expected.get("must_not_match", []):
        if re.search(shape, result):
            return fail(f"the verdict carries {shape!r}, which this fixture forbids:\n{result}")

    # 3. The check was called, and correlated to a result — so a verdict read
    #    off the configuration file is not mistaken for one that ran anything.
    calls = ran_the_check(items, expected["runs"])
    if not calls:
        return fail(f"nothing in the transcript ran {expected['runs']}")
    if not any(tool_results(items, tool_id) for tool_id in calls):
        return fail(f"{expected['runs']} was called but never returned")

    # 4. …and it really executed, proven outside the transcript. A tool call is
    #    an intent; the marker is the state that intent reached.
    marker = expected["marker"]
    marker_path = workdir / marker["path"]
    try:
        got = marker_path.read_text(encoding="utf-8")
    except OSError:
        return fail(f"the fixture's check left no marker at {marker_path}")
    if got != marker["value"]:
        return fail(f"the marker holds {got!r}, expected {marker['value']!r}")

    # 5. The verifier did not repair the subject. Without this, a gate that
    #    fixed the red fixture and then reported READY would pass its pair by
    #    destroying the thing that made them different.
    for relative in expected["unchanged"]:
        before = (fixture / "repo" / relative).read_bytes()
        after_path = workdir / relative
        try:
            after = after_path.read_bytes()
        except OSError:
            return fail(f"the run removed {relative}")
        if before != after:
            return fail(f"the verifier modified {relative}, which it was told not to touch")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
