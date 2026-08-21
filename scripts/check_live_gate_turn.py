#!/usr/bin/env python3
"""Fail closed on what a live `gopnik` run must have done to a fixture.

The gate is the product, and until this script existed nothing executed it.
Its text was well guarded: thirteen content assertions in `tests/test_setup.py`,
EN/RU structural parity, brand and frontmatter checks, and three tests in
`tests/test_guides.py`. Every one of them reads what the file *says*. None
observes what a session *does* with it, and no live cell pointed at the gate at
all — so a revision that left the wording intact and made a real run answer
`READY` to everything would have passed every check in the repository.

What makes this a check rather than a keyword search is the pair. Reading the
verdict alone is satisfied by a constant: `gate-red-stage1` passes for a gate
stuck on `NOT READY`, `gate-ready-scoped` passes for one stuck on `READY`. So
each fixture also has to show *the work behind its verdict* — that the gate was
the thing that produced it, that the project's own check really ran, proven from
outside the transcript, and that the verifier did not quietly repair the subject
it was judging.

The first of those was learned the hard way. The first version of this file
checked everything except whether the skill ran, and passed two live sessions
that never invoked it: a capable model, handed the fixture, reached the right
verdicts on its own. A cell that cannot tell the gate from the model is not
measuring the gate.

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
REQUIRED = ("role", "prompt", "verdict", "runs", "marker", "unchanged", "invokes")


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


#: `NOT READY` first, so the alternation never matches the tail of it. The
#: negative lookbehind on the second branch is belt and braces for the same
#: thing: `"READY" in text` is true of `NOT READY`, and an oracle with that bug
#: passes both halves of the pair while checking neither.
VERDICT = re.compile(r"\bnot[\s_-]*ready\b|(?<!not[\s_-])\bready\b", re.IGNORECASE)


def first_verdict(text: str) -> str | None:
    """The verdict this run reached, which is the first one it states.

    Not "does the word appear anywhere". A correct `NOT READY` may go on to
    explain what a passing run would have looked like — a real one said "a
    passing run here would have been `READY scope: Stage 1` at best. It is moot:
    Stage 1 has a blocker" — and a rule that bans the phrase outright rejects
    the right answer for using a counterfactual. Position is what carries the
    verdict; later mentions are prose.
    """
    found = VERDICT.search(text)
    if found is None:
        return None
    return "NOT READY" if found.group(0).lower().startswith("not") else "READY"


def invoked_the_skill(items: list[object], skill: str) -> bool:
    """Whether the run actually loaded the gate, rather than reasoning unaided.

    This is the check the first version of this file did not have, and the run
    that taught it: against the same fixture, through an installed plugin, a
    session produced a well-argued verdict with the right answer and never
    invoked the skill at all. Everything else here passed it. A cell that cannot
    tell the gate from a capable model reading a fixture is testing the model.
    """
    for item in items:
        for value in nested_dicts(item):
            if value.get("type") != "tool_use":
                continue
            if str(value.get("name") or "").lower() != "skill":
                continue
            payload = value.get("input")
            if not isinstance(payload, dict):
                continue
            # A plugin qualifies the name: the marketplace install answers to
            # `gopnik:gopnik`, a project-local one to `gopnik`. Both are the same
            # skill, and requiring the bare form failed a run that had just
            # executed it.
            named = str(payload.get("skill") or "").rsplit(":", 1)[-1]
            if named == skill:
                return True
    return False


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
    reached = first_verdict(result)
    if reached is None:
        return fail(f"the run reached no verdict at all:\n{result}")
    if reached != expected["verdict"]:
        return fail(f"the run returned {reached} where {expected['verdict']} was due:\n{result}")

    # 2. The reason. A verdict without it cannot be told from a coin toss that
    #    landed the right way up.
    for shape in expected.get("must_match", []):
        if not re.search(shape, result):
            return fail(f"the verdict does not carry {shape!r}:\n{result}")
    for shape in expected.get("must_not_match", []):
        if re.search(shape, result):
            return fail(f"the verdict carries {shape!r}, which this fixture forbids:\n{result}")

    # 3. The gate itself ran. Without this the cell measures the model.
    if not invoked_the_skill(items, expected["invokes"]):
        return fail(f"the run never invoked the {expected['invokes']} skill")

    # 4. The check was called, and correlated to a result — so a verdict read
    #    off the configuration file is not mistaken for one that ran anything.
    calls = ran_the_check(items, expected["runs"])
    if not calls:
        return fail(f"nothing in the transcript ran {expected['runs']}")
    if not any(tool_results(items, tool_id) for tool_id in calls):
        return fail(f"{expected['runs']} was called but never returned")

    # 5. …and it really executed, proven outside the transcript. A tool call is
    #    an intent; the marker is the state that intent reached.
    marker = expected["marker"]
    marker_path = workdir / marker["path"]
    try:
        got = marker_path.read_text(encoding="utf-8")
    except OSError:
        return fail(f"the fixture's check left no marker at {marker_path}")
    if got != marker["value"]:
        return fail(f"the marker holds {got!r}, expected {marker['value']!r}")

    # 6. The verifier did not repair the subject. Without this, a gate that
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
