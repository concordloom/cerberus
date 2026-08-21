#!/usr/bin/env python3
"""Tests for the fixture pack and for the oracles that read it.

The pack exists because there was one fixture, it was a `printf` chain inside
`gopnik.json`, and `scripts/check_live_setup_turn.py` held its strings as
literals. Adding a second meant copying a 1179-character cell and forking the
oracle, so for a year nobody did.

Two things are checked here, and neither is "the files exist".

**The fixtures and their expectations agree.** A fixture whose `check.sh` no
longer produces the outcome its `expected.json` claims would make a live cell
unsatisfiable, and the only place that would surface is a billed agent session.

**The oracles can fail.** A gate oracle that returns 0 whatever it reads costs
exactly as much to run and proves nothing, so every rejection it owes is
exercised against a synthetic transcript here. The one that matters most is the
substring: `"READY" in text` is true of `NOT READY`, and an oracle with that bug
passes both halves of the pair while checking neither.

Run with: python3 tests/test_fixtures.py
"""

from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
GATE_ORACLE = ROOT / "scripts" / "check_live_gate_turn.py"
SETUP_ORACLE = ROOT / "scripts" / "check_live_setup_turn.py"


def fixtures(role: str) -> list[pathlib.Path]:
    found = [
        directory
        for directory in sorted(FIXTURES.iterdir())
        if directory.is_dir()
        and json.loads((directory / "expected.json").read_text(encoding="utf-8")).get("role") == role
    ]
    assert found, f"no {role} fixture in the pack"
    return found


def materialise(fixture: pathlib.Path) -> pathlib.Path:
    work = pathlib.Path(tempfile.mkdtemp()) / "repo"
    shutil.copytree(fixture / "repo", work)
    return work


def transcript(
    path: pathlib.Path,
    result: object,
    calls: list[tuple[str, dict, bool]] | None = None,
) -> None:
    events: list[dict] = []
    if calls is None:
        calls = [("Bash", {"command": "./check.sh"}, True)]
    for index, (name, payload, answered) in enumerate(calls):
        tool_id = f"call-{index}"
        events.append({"type": "assistant", "message": {"content": [{
            "type": "tool_use", "id": tool_id, "name": name, "input": payload,
        }]}})
        if answered:
            events.append({"type": "user", "message": {"content": [{
                "type": "tool_result", "tool_use_id": tool_id,
                "is_error": False, "content": "done",
            }]}})
    if result is not None:
        events.append({"type": "result", "result": result})
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")


def gate(fixture: pathlib.Path, path: pathlib.Path, work: pathlib.Path) -> int:
    return subprocess.run(
        [sys.executable, str(GATE_ORACLE), str(fixture), str(path), str(work)],
        capture_output=True,
        text=True,
    ).returncode


# ------------------------------------------------------- the pack itself


def test_every_fixture_declares_what_it_is():
    """A tree with no expectations is dead weight nothing can consume."""
    directories = [d for d in sorted(FIXTURES.iterdir()) if d.is_dir()]
    assert directories, "the pack is empty"
    for directory in directories:
        expected = directory / "expected.json"
        assert expected.is_file(), f"{directory.name}: no expected.json"
        body = json.loads(expected.read_text(encoding="utf-8"))
        assert body.get("role") in ("setup", "gate"), f"{directory.name}: unknown role"
        assert (directory / "repo").is_dir(), f"{directory.name}: no repo/"


def test_each_gate_fixture_produces_the_outcome_it_claims():
    """#73. The claim in `expected.json` is about a program; run the program.

    Without this, an edit to `app/cli.py` that made the red fixture pass would
    be found by a billed agent session rather than here.
    """
    for fixture in fixtures("gate"):
        body = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
        work = materialise(fixture)
        proc = subprocess.run(["./check.sh"], cwd=str(work), capture_output=True, text=True)
        red = body["verdict"] == "NOT READY"
        assert (proc.returncode != 0) == red, (
            f"{fixture.name}: check.sh exited {proc.returncode} but expects "
            f"verdict {body['verdict']}\n{proc.stdout}{proc.stderr}"
        )
        marker = work / body["marker"]["path"]
        assert marker.is_file(), f"{fixture.name}: check.sh left no marker"
        assert marker.read_text(encoding="utf-8") == body["marker"]["value"]


def test_the_gate_pair_differs_only_in_product_code():
    """One variable. Otherwise the opposite verdicts prove nothing in particular."""
    red, ready = FIXTURES / "gate-red-stage1" / "repo", FIXTURES / "gate-ready-scoped" / "repo"
    differ = set()
    for side in (red, ready):
        for path in side.rglob("*"):
            # compileall runs over tests/ before this does, so the fixtures grow
            # a __pycache__ whose contents differ for the very reason the two
            # trees differ. Comparing those would fail for the right reason at
            # the wrong level.
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(side)
            other = (ready if side is red else red) / relative
            if not other.is_file() or other.read_bytes() != path.read_bytes():
                differ.add(str(relative))
    assert differ == {"app/cli.py"}, f"the pair differs in more than the change: {differ}"


def test_stage2_consumes_the_pack_rather_than_rebuilding_it():
    """The relocation is only real if the live route reads these files."""
    stage2 = json.loads((ROOT / "gopnik.json").read_text(encoding="utf-8"))["verification"]["stage2"]
    joined = "\n".join(stage2)
    assert "printf '%s\\n' '[project]'" not in joined, "the printf chain is back"
    for name in ("hybrid", "gate-red-stage1", "gate-ready-scoped"):
        needle = f"tests/fixtures/{name}"
        assert needle in joined, f"stage2 never reaches {needle}"
        assert (FIXTURES / name).is_dir(), f"stage2 names a fixture that is not here: {name}"


# --------------------------------------------- the gate oracle can fail


def test_the_substring_trap_is_handled_in_both_directions():
    """`"READY" in "NOT READY"` is the bug that would disable half the pair."""
    sys.path.insert(0, str(GATE_ORACLE.parent))
    import check_live_gate_turn as oracle

    assert oracle.says_not_ready("NOT READY — Stage 1 is red") is True
    assert oracle.says_ready("NOT READY — Stage 1 is red") is False
    assert oracle.says_ready("READY scope: Stage 1") is True
    assert oracle.says_not_ready("READY scope: Stage 1") is False
    assert oracle.says_not_ready("not ready") is True
    assert oracle.says_not_ready("not-ready") is True
    assert oracle.says_ready("Stage 2 — Not proven: no dev cluster") is False


def test_the_gate_oracle_rejects_everything_it_owes():
    red = FIXTURES / "gate-red-stage1"
    ready = FIXTURES / "gate-ready-scoped"
    root = pathlib.Path(tempfile.mkdtemp())
    path = root / "turn.jsonl"

    good_red = (
        "NOT READY. Stage 1 is red: ./check.sh exits 1 with "
        "FAIL: --json printed 'ok=True', which is not JSON."
    )
    good_ready = (
        "READY scope: Stage 1. ./check.sh passed. Stage 2 — Not proven: "
        "no packaged artifact, so there is nothing built to install."
    )

    def work_for(fixture: pathlib.Path) -> pathlib.Path:
        directory = materialise(fixture)
        body = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
        (directory / body["marker"]["path"]).write_text(body["marker"]["value"], encoding="utf-8")
        return directory

    # The two that must pass. Everything below is a mutation of one of them, so
    # a failure here means the rejections prove nothing.
    transcript(path, good_red)
    assert gate(red, path, work_for(red)) == 0
    transcript(path, good_ready)
    assert gate(ready, path, work_for(ready)) == 0

    # The verdict itself, in both directions.
    transcript(path, good_ready)
    assert gate(red, path, work_for(red)) != 0, "READY passed where NOT READY was due"
    transcript(path, good_red)
    assert gate(ready, path, work_for(ready)) != 0, "NOT READY passed where READY was due"
    transcript(path, "The change looks fine to me.")
    assert gate(red, path, work_for(red)) != 0, "a turn with no verdict passed"

    # The reason behind the verdict.
    transcript(path, "NOT READY. Something is wrong somewhere.")
    assert gate(red, path, work_for(red)) != 0, "a verdict with no reason passed"
    transcript(path, "READY scope: Stage 1. ./check.sh passed.")
    assert gate(ready, path, work_for(ready)) != 0, "READY passed without quoting the reason"
    transcript(path, good_red + " READY scope: Stage 1 would apply otherwise.")
    assert gate(red, path, work_for(red)) != 0, "a forbidden phrase passed"

    # The work behind the verdict: called, answered, and actually executed.
    transcript(path, good_red, calls=[("Bash", {"command": "cat gopnik.json"}, True)])
    assert gate(red, path, work_for(red)) != 0, "a verdict read off the configuration passed"
    transcript(path, good_red, calls=[("Bash", {"command": "./check.sh"}, False)])
    assert gate(red, path, work_for(red)) != 0, "a check that never returned passed"

    bare = materialise(red)
    transcript(path, good_red)
    assert gate(red, path, bare) != 0, "a missing marker passed"
    stale = work_for(red)
    (stale / ".stage1-ran").write_text("something else", encoding="utf-8")
    assert gate(red, path, stale) != 0, "a marker with the wrong value passed"

    # The verifier must not repair the subject it is judging.
    repaired = work_for(red)
    (repaired / "app" / "cli.py").write_text("def render_json(p):\n    return '{}'\n", encoding="utf-8")
    transcript(path, good_red)
    assert gate(red, path, repaired) != 0, "a verifier that rewrote the subject passed"
    removed = work_for(red)
    (removed / "check.sh").unlink()
    assert gate(red, path, removed) != 0, "a verifier that deleted the check passed"

    # The transcript has to be a transcript.
    for broken in ("", "{not json\n"):
        path.write_text(broken, encoding="utf-8")
        assert gate(red, path, work_for(red)) != 0, f"a broken transcript passed: {broken!r}"
    transcript(path, None)
    assert gate(red, path, work_for(red)) != 0, "a transcript with no final result passed"
    path.write_text(
        json.dumps({"type": "result", "result": good_red}) + "\n"
        + json.dumps({"type": "assistant", "message": {"content": []}}) + "\n",
        encoding="utf-8",
    )
    assert gate(red, path, work_for(red)) != 0, "a result that was not last passed"


def test_a_narrowed_verdict_still_has_to_name_the_boundary():
    """#73/#74. What is left after dropping the label must still be a check.

    `gate-ready-scoped` no longer asserts `READY scope:`, because a live gate
    does not emit it (#74). Dropping an assertion is how a cell quietly stops
    checking anything, so what remains is pinned here: a clean-reading `READY`
    that never mentions the boundary is still rejected, which is the failure the
    label existed to prevent.
    """
    fixture = FIXTURES / "gate-ready-scoped"
    body = json.loads((fixture / "expected.json").read_text(encoding="utf-8"))
    assert "#74" in body["//not_asserted"], (
        "the dropped assertion must name the issue that owns it")
    assert "ready[^.]{0,40}scope" in body["//not_asserted"], (
        "the dropped assertion must be written down verbatim")

    root = pathlib.Path(tempfile.mkdtemp())
    path = root / "turn.jsonl"

    def work() -> pathlib.Path:
        directory = materialise(fixture)
        (directory / body["marker"]["path"]).write_text(
            body["marker"]["value"], encoding="utf-8")
        return directory

    transcript(path, "Verdict: ready to ship. The check passed and I am happy with it.")
    assert gate(fixture, path, work()) != 0, "a bare READY with no boundary named passed"
    transcript(path, "Verdict: ready to ship. Stage 1 passed; ./check.sh is green.")
    assert gate(fixture, path, work()) != 0, "a READY that never reaches Stage 2 passed"
    transcript(
        path,
        "Verdict: ready to ship. Stage 1 passed. Stage 2 is not applicable: "
        "no packaged artifact, so there is nothing built to install.",
    )
    assert gate(fixture, path, work()) == 0, "the narrowed verdict this fixture accepts failed"


def test_a_gate_fixture_missing_its_expectations_fails_loudly():
    """Silence here would turn a broken cell into a green one."""
    root = pathlib.Path(tempfile.mkdtemp())
    empty = root / "nothing"
    empty.mkdir()
    path = root / "turn.jsonl"
    transcript(path, "NOT READY. ./check.sh Stage 1 is red.")
    assert gate(empty, path, root) != 0, "a fixture with no expected.json passed"

    partial = root / "partial"
    (partial / "repo").mkdir(parents=True)
    (partial / "expected.json").write_text(json.dumps({"role": "gate"}), encoding="utf-8")
    assert gate(partial, path, root) != 0, "a fixture missing required keys passed"

    wrong = root / "wrong-role"
    (wrong / "repo").mkdir(parents=True)
    (wrong / "expected.json").write_text(json.dumps({"role": "setup"}), encoding="utf-8")
    assert gate(wrong, path, root) != 0, "a setup fixture passed as a gate fixture"


# ------------------------------- the setup oracle reads the fixture, not itself


def test_the_setup_oracle_takes_its_strings_from_the_fixture():
    """#73. The claim is parameterisation, so a second fixture has to move it.

    A fixture with different surfaces and a different kind must accept the turn
    that suits *it* and reject the one that suits the hybrid — otherwise the
    strings are still effectively hardcoded and the `--fixture` option is
    decoration.
    """
    root = pathlib.Path(tempfile.mkdtemp())
    other = root / "library-only"
    (other / "repo").mkdir(parents=True)
    (other / "expected.json").write_text(json.dumps({
        "role": "setup",
        "stage1": ["make check"],
        "artifact_kind": "library",
        "surfaces": ["library", "migration"],
        "marker": {"path": ".stage1-ran", "value": "ran"},
        "internal_details": {"en": ["broken wheel"], "ru": ["сломанное колесо"]},
    }), encoding="utf-8")

    marker = root / ".stage1-ran"
    path = root / "turn.jsonl"

    def check(fixture: pathlib.Path, stage1: str, surfaces: str, result: str) -> int:
        events = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text":
                "Stage 0 maps possible failures. Stage 1 checks the code. "
                "Stage 2 checks the delivered result only after Stage 1."}]}},
            {"type": "assistant", "message": {"content": [{
                "type": "tool_use", "id": "s1", "name": "Bash",
                "input": {"command":
                    "python3 gopnik_setup.py --defer-artifact-kind --language en "
                    f"--stage1 '{stage1}'"}}]}},
            {"type": "user", "message": {"content": [{
                "type": "tool_result", "tool_use_id": "s1", "is_error": False,
                "content": "Stage 1 set up. Delivery surfaces still need confirmation."}]}},
            {"type": "assistant", "message": {"content": [{
                "type": "tool_use", "id": "critic", "name": "Agent",
                "input": {"prompt":
                    "Use gopnik-critic. End with GOPNIK_CRITIC_STATUS: complete or "
                    "GOPNIK_CRITIC_STATUS: blocked, after GOPNIK_CRITIC_SURFACES:."}}]}},
            {"type": "user", "message": {"content": [{
                "type": "tool_result", "tool_use_id": "critic", "is_error": False,
                "content": f"Surviving.\nGOPNIK_CRITIC_SURFACES: {surfaces}\n"
                           "GOPNIK_CRITIC_STATUS: complete"}]}},
            {"type": "result", "result": result},
        ]
        path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SETUP_ORACLE), "--fixture", str(fixture),
             "surfaces", str(path), str(marker)],
            capture_output=True, text=True,
        ).returncode

    hybrid_turn = (
        "Stage 0 maps what could break. Stage 1 checks the code. Stage 2 checks "
        "the delivered result only after Stage 1 works. Stage 1 passed. "
        "After delivery, do people use only the command, only the web interface, or both?"
    )
    other_turn = (
        "Stage 0 maps what could break. Stage 1 checks the code. Stage 2 checks "
        "the delivered result only after Stage 1 works. Stage 1 passed. "
        "After delivery, do people use only the library, only the migration, or both?"
    )

    marker.write_text("stage1-ran", encoding="utf-8")
    assert check(FIXTURES / "hybrid", "./check.sh", "command, web", hybrid_turn) == 0

    marker.write_text("ran", encoding="utf-8")
    assert check(other, "make check", "library, migration", other_turn) == 0, (
        "the second fixture cannot drive the oracle — the strings are still its own")
    assert check(other, "./check.sh", "library, migration", other_turn) != 0, (
        "the fixture's Stage 1 command is not being read")
    assert check(other, "make check", "command, web", hybrid_turn) != 0, (
        "the fixture's surfaces are not being read")

    marker.write_text("stage1-ran", encoding="utf-8")
    assert check(other, "make check", "library, migration", other_turn) != 0, (
        "the fixture's marker value is not being read")


def _run_all() -> int:
    failures = []
    for name, function in sorted(globals().items()):
        if name.startswith("test_") and callable(function):
            try:
                function()
                print(f"  ok   {name}")
            except AssertionError as exc:
                failures.append((name, exc))
                print(f"  FAIL {name}: {exc}")
    if failures:
        print(f"{len(failures)} failing")
        return 1
    print("all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
