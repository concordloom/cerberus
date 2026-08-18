#!/usr/bin/env python3
"""Tests for cerberus_setup.py and for what install.sh leaves behind.

Three kinds of assertion here, and the last two are the unusual ones.

The ordinary kind: it detects what it should, writes only what it may, and
refuses when it cannot tell.

The second kind: **what the installer does NOT do**. Since #33 the whole
argument for this tool is that it takes no decisions on the user's behalf, and
"takes no decisions" is only a requirement if something fails when it does. So
the tests assert the absence of wiring, of hook files, and of any edit to a file
the project owns.

The third kind: **what the user reads is tested**. "Friendly" is normally a
matter of taste and therefore un-gateable, so it is pinned to things a machine
can check — a list of words that must not appear, a line count, and the
statements the closing message owes the reader. A requirement that cannot fail
is not a requirement.

Run with: python3 tests/test_setup.py
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "cerberus" / "skills"
SETUP = SKILLS / "cerberus-setup" / "cerberus_setup.py"
INSTALL = ROOT / "install.sh"

# Load-bearing internally, meaningless to someone being set up. The whole point
# of the amendment on #13 is that this list is checked rather than intended.
# Matched with word boundaries and with hyphens and underscores treated as
# spaces: a plain substring list was defeated by writing "Stage-1",
# "artifact kind" and "Blast-radius", which read exactly as badly.
JARGON = [
    "oracle", "delivery boundary", "stage 0", "stage 1", "stage 2",
    "counterexample", "counter example", "blast radius", "artifact kind",
    "adversary", "marker", "cartesian", "sentinel", "predicate", "idempotent",
    "topology", "semantics", "verdict", "cerberus_", "falsifier", "adjudicate",
    "persisted", "vector", "contract",
]


def jargon_in(text: str) -> list[str]:
    """Words from the list, with hyphens folded and plurals stemmed.

    Honest about what this is: a smoke check, not a proof. A denylist of
    surface forms cannot carry "write like a person" — the first version was
    defeated by a hyphen, the second by an `s`, and a third evasion certainly
    exists. It catches the drift that happens by accident, which is the drift
    that actually happens. The requirement is carried by the line count, the
    closing statements, and by somebody reading it.
    """
    flat = re.sub(r"[-_/]+", " ", text.lower())
    flat = re.sub(r"\s+", " ", flat)
    words = [re.sub(r"(ies|es|s)$", "", w) for w in flat.split()]
    flat = " ".join(words)
    found = []
    for term in JARGON:
        stem = " ".join(re.sub(r"(ies|es|s)$", "", w) for w in term.split())
        if re.search(r"\b" + re.escape(stem) + r"\b", flat):
            found.append(term)
    return found


# Keys that no longer have any reader. A config key nobody reads is a lie with a
# schema, so writing one is a failure rather than a harmless leftover.
DEAD_KEYS = [
    "enforce", "claim_patterns", "ignore_patterns", "source_extensions",
    "watch_paths", "marker",
]


def project(files: dict[str, str]) -> pathlib.Path:
    """Build a throwaway project with the setup script beside its skill."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    target = tmp / ".claude" / "skills" / "cerberus-setup"
    target.mkdir(parents=True)
    (target / "cerberus_setup.py").write_text(SETUP.read_text(encoding="utf-8"), encoding="utf-8")
    # `_write` rather than a loop here: some fixtures need a directory, which a
    # signal like `charts` or `k8s` actually is, and writing it as a file made
    # those kinds untestable through this helper.
    _write(tmp, files)
    return tmp


def run_setup(root: pathlib.Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(root / ".claude" / "skills" / "cerberus-setup" / "cerberus_setup.py"), *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
    )
    return proc.returncode, proc.stdout + proc.stderr


def run_install(target: pathlib.Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["sh", str(INSTALL), *args],
        cwd=str(target),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def config_of(root: pathlib.Path) -> dict:
    for relative in (".claude/cerberus.json", ".codex/cerberus.json", "cerberus.json"):
        if (root / relative).exists():
            return json.loads((root / relative).read_text(encoding="utf-8"))
    raise AssertionError(f"no configuration anywhere under {root}")


PY_PROJECT = {
    "pyproject.toml": '[project]\nname = "demo"\nversion = "0.1"\n',
    "tests/test_demo.py": "def test_ok():\n    assert True\n",
}

# A mutant got through every round by being wrong only for projects the tests
# never built. The "never" rules are checked against these too.
MAKE_PROJECT = {"Makefile": "test:\n\t@true\n"}
DOCKER_PROJECT = {"Dockerfile": "FROM scratch\n"}


def _every_runner() -> dict:
    """One fixture per entry in RUNNERS, built from RUNNERS itself.

    A hand-listed subset is why the fourth mutant died and the fifth did not:
    the list said Node and Go, the code also supports Rust, and the mutant was
    wrong only there. Deriving the fixtures from the code means adding a runner
    cannot leave a hole.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    seeds = {
        "pyproject.toml": '[project]\nname = "d"\nversion = "1"\n',
        "package.json": json.dumps({"name": "d", "scripts": {"test": "exit 0"}}),
        "Cargo.toml": '[package]\nname = "d"\nversion = "0.1.0"\nedition = "2021"\n',
        "go.mod": "module example.com/d\n\ngo 1.21\n",
    }
    out = {}
    for runner in cerberus_setup.RUNNERS:
        marker = next((f for f in runner["files"] if f in seeds), None)
        assert marker, f"no fixture seed for runner {runner['name']} — add one"
        out[runner["name"]] = {marker: seeds[marker]}
    return out


OTHER_PROJECTS = {k: v for k, v in _every_runner().items() if k != "Python"}


# --------------------------------------------------------------- behaviour


def test_sets_up_a_python_project():
    root = project(PY_PROJECT)
    code, out = run_setup(root)
    assert code == 0, out
    cfg = config_of(root)["verification"]
    assert cfg["artifact_kind"] == "library", cfg
    assert cfg["stage1"], "no checks were written at all"
    assert not any("replace with" in c for c in cfg["stage1"]), cfg["stage1"]


def test_never_writes_a_check_it_did_not_run():
    root = project(PY_PROJECT)
    run_setup(root)
    for cmd in config_of(root)["verification"]["stage1"]:
        assert subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True).returncode == 0, cmd


def test_never_writes_a_check_it_did_not_run_in_any_language():
    for name, files in OTHER_PROJECTS.items():
        root = project(files)
        code, _ = run_setup(root)
        if code != 0:
            continue  # the toolchain is absent here; nothing was written
        for cmd in config_of(root)["verification"]["stage1"]:
            got = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True)
            assert got.returncode == 0, f"{name}: wrote {cmd!r}, which exits {got.returncode}"


def test_never_writes_a_key_that_nothing_reads():
    """#33: the hooks are gone, so their keys are no longer configuration.

    Asserted at write_config rather than end-to-end, because a project where
    detection fails writes nothing at all and would pass this vacuously.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        for kind in list(cerberus_setup.STAGE2_HINT_BY_KIND) + ["library"]:
            path = cerberus_setup.write_config(root, kind, ["true"], dry=False)
            body = json.loads(path.read_text(encoding="utf-8"))
            for key in DEAD_KEYS:
                assert key not in body, f"{kind}: wrote dead key {key}"
                assert key not in body["verification"], f"{kind}: wrote dead key {key}"


def test_refuses_every_unsupported_build_system_rather_than_guessing():
    for files in (MAKE_PROJECT, DOCKER_PROJECT):
        root = project(files)
        code, out = run_setup(root)
        assert code == 2, out
        assert "could not tell" in out.lower(), out
        assert not (root / "cerberus.json").exists(), "wrote a config for a project it did not recognise"


def test_refuses_a_project_it_cannot_recognise():
    root = project({"README.md": "hello\n"})
    code, out = run_setup(root)
    assert code == 2, out
    assert "Nothing was changed" in out, out


def test_project_instructions_block_generic_toolchain_guesses():
    root = project({
        "go.mod": "module example.com/loomwatch\n\ngo 1.25\n",
        "AGENTS.md": (
            "Always use `app.sh` for build and test - never run `go build` "
            "or `go test` directly.\n"
        ),
        "app.sh": "#!/bin/sh\nprintf 'wrapper ran\\n' >> wrapper.log\n",
    })
    code, out = run_setup(root)
    assert code == 2, out
    assert "Project instructions found: AGENTS.md" in out, out
    assert "--stage1 COMMAND" in out, out
    assert not (root / "wrapper.log").exists(), "ran a command before reading project rules"
    assert not (root / "cerberus.json").exists(), "configured from a forbidden generic guess"


def test_explicit_project_owned_checks_replace_generic_go_commands():
    root = project({
        "go.mod": "module example.com/loomwatch\n\ngo 1.25\n",
        "Dockerfile": "FROM scratch\n",
        "AGENTS.md": "Always use `app.sh` for build and test.\n",
        "app.sh": "#!/bin/sh\nprintf '%s\\n' \"$1\" >> wrapper.log\n",
    })
    (root / "app.sh").chmod(0o755)
    code, out = run_setup(
        root,
        "--stage1", "./app.sh --smoke",
        "--artifact-kind", "service",
    )
    assert code == 0, out
    assert (root / "wrapper.log").read_text(encoding="utf-8") == "--smoke\n"
    stage1 = config_of(root)["verification"]["stage1"]
    assert stage1 == ["./app.sh --smoke"], stage1
    assert not any(command.startswith("go ") for command in stage1), stage1


def test_one_red_project_owned_check_blocks_setup_instead_of_writing_a_subset():
    root = project({
        "go.mod": "module example.com/loomwatch\n\ngo 1.25\n",
        "Dockerfile": "FROM scratch\n",
        "AGENTS.md": "Always use `app.sh` for build and test.\n",
        "app.sh": "#!/bin/sh\n[ \"$1\" = --smoke ]\n",
    })
    (root / "app.sh").chmod(0o755)
    code, out = run_setup(
        root,
        "--stage1", "./app.sh --smoke",
        "--stage1", "./app.sh --test",
        "--artifact-kind", "service",
    )
    assert code == 2, out
    assert "setup is blocked" in out, out
    assert "ok       ./app.sh --smoke" in out, out
    assert "FAILING  ./app.sh --test" in out, out
    assert not (root / "cerberus.json").exists(), "wrote a partial required baseline"


def test_a_red_smoke_check_stops_before_the_long_project_owned_suite():
    root = project({
        "go.mod": "module example.com/loomwatch\n\ngo 1.25\n",
        "Dockerfile": "FROM scratch\n",
        "AGENTS.md": "Always use `app.sh`; smoke before the full suite.\n",
        "app.sh": (
            "#!/bin/sh\n"
            "if [ \"$1\" = --smoke ]; then exit 1; fi\n"
            "touch long-suite-ran\n"
        ),
    })
    (root / "app.sh").chmod(0o755)
    code, out = run_setup(
        root,
        "--stage1", "./app.sh --smoke",
        "--stage1", "./app.sh --test",
        "--artifact-kind", "service",
    )
    assert code == 2, out
    assert "FAILING  ./app.sh --smoke" in out, out
    assert "./app.sh --test" not in out, out
    assert not (root / "long-suite-ran").exists(), "ran the full suite after red smoke"


def test_a_configured_project_runs_its_own_checks():
    root = project({**PY_PROJECT, "cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "service", "stage1": ["true"], "stage2": ["true"]}})})
    code, out = run_setup(root)
    assert code == 0, out
    assert "ok       true" in out, out


def test_a_configured_project_reachable_only_by_hand_still_gets_an_answer():
    root = project({**MAKE_PROJECT, "cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "cli", "stage1": ["true"], "stage2": ["true"]}})})
    code, out = run_setup(root)
    assert code == 0, out
    assert "Already configured" in out, out


def test_a_hand_written_step_is_not_mistaken_for_the_placeholder():
    hand = {"//": "mine", "verification": {"artifact_kind": "migration", "stage1": ["true"], "stage2": ["true"],
                                           "notes": "prod account 1234"}}
    root = project({**PY_PROJECT, "cerberus.json": json.dumps(hand)})
    run_setup(root)
    assert config_of(root) == hand, "rewrote a hand-written configuration"


def test_leaves_a_hand_written_configuration_alone():
    hand = {"verification": {"artifact_kind": "migration", "stage1": ["true"], "stage2": ["true"]},
            "something_else": {"kept": True}}
    root = project({**PY_PROJECT, "cerberus.json": json.dumps(hand)})
    before = (root / "cerberus.json").read_bytes()
    run_setup(root)
    assert (root / "cerberus.json").read_bytes() == before


def test_replaces_the_example_placeholders():
    example = (ROOT / "cerberus.example.json").read_text(encoding="utf-8")
    root = project({**PY_PROJECT, "cerberus.json": example})
    code, out = run_setup(root)
    assert code == 0, out
    stage1 = config_of(root)["verification"]["stage1"]
    assert not any("replace with" in c for c in stage1), stage1


def test_the_example_markers_still_match_the_shipped_file():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    example = json.loads((ROOT / "cerberus.example.json").read_text(encoding="utf-8"))
    assert cerberus_setup.is_the_installers_copy(example), (
        "cerberus.example.json drifted from the strings setup recognises it by, "
        "so a fresh install would be treated as hand-configured and left with placeholders"
    )


def test_an_existing_configuration_is_never_modified_where_it_was_not_asked():
    example = json.loads((ROOT / "cerberus.example.json").read_text(encoding="utf-8"))
    example["mine"] = {"keep": "this"}
    root = project({**PY_PROJECT, "cerberus.json": json.dumps(example)})
    run_setup(root)
    assert config_of(root)["mine"] == {"keep": "this"}


def test_stage2_never_holds_something_that_was_not_run():
    root = project(PY_PROJECT)
    run_setup(root)
    assert config_of(root)["verification"]["stage2"] == []


def test_check_mode_changes_nothing():
    root = project(PY_PROJECT)
    code, out = run_setup(root, "--check")
    assert code == 0, out
    assert not (root / "cerberus.json").exists(), "wrote a config in --check mode"


def test_check_names_the_file_the_real_run_would_write():
    root = project(PY_PROJECT)
    _, out = run_setup(root, "--check")
    assert "cerberus.json" in out, out
    _, _ = run_setup(root)
    assert (root / "cerberus.json").exists(), "the real run wrote somewhere else"


def test_a_failing_check_is_called_failing_not_absent():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    passing, missing, timed_out, broken = cerberus_setup.sort_results(
        [("a", 0, ""), ("b", 1, "boom"), ("c", 127, ""), ("d", 124, "")])
    assert passing == ["a"] and missing == ["c"] and timed_out == ["d"]
    assert broken == [("b", "boom")]


def test_a_failing_check_is_reported_as_failing_end_to_end():
    root = project({**PY_PROJECT, "tests/test_demo.py": "def test_bad():\n    assert False\n"})
    code, out = run_setup(root)
    written = config_of(root)["verification"]["stage1"] if code == 0 else []
    assert "pytest -q" not in written, "wrote a check that fails here"


def test_only_a_passing_check_is_ever_written():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        passing, _, _, _ = cerberus_setup.sort_results(
            [("ok", 0, ""), ("fails", 1, ""), ("slow", 124, ""), ("gone", 127, "")])
        path = cerberus_setup.write_config(root, "library", passing, dry=False)
        assert json.loads(path.read_text(encoding="utf-8"))["verification"]["stage1"] == ["ok"]


def test_a_timed_out_check_is_never_written():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        code, _ = cerberus_setup.run("sleep 5", pathlib.Path(d), timeout=1)
        assert code == 124


def test_a_timed_out_check_does_not_leave_the_tree_running():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        stamp = root / "still-alive"
        cerberus_setup.run(f"sh -c 'sleep 3; touch {stamp}' &  sleep 5", root, timeout=1)
        subprocess.run(["sleep", "4"])
        assert not stamp.exists(), "a grandchild outlived the timeout"


def test_a_check_never_inherits_stdin():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        code, out = cerberus_setup.run("cat", pathlib.Path(d), timeout=5)
        assert code == 0 and out == "", f"a check read from stdin: {code} {out!r}"


def test_a_project_path_with_a_space_is_still_recognised():
    tmp = pathlib.Path(tempfile.mkdtemp()) / "a project"
    tmp.mkdir()
    target = tmp / ".claude" / "skills" / "cerberus-setup"
    target.mkdir(parents=True)
    (target / "cerberus_setup.py").write_text(SETUP.read_text(encoding="utf-8"), encoding="utf-8")
    for name, text in PY_PROJECT.items():
        path = tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    code, out = run_setup(tmp)
    assert code == 0, out
    assert (tmp / "cerberus.json").exists(), out


# --------------------------------------------------------- where it writes


def test_an_earlier_installs_config_is_kept_where_it_is():
    """Both older locations, and .claude wins when a project has both.

    Reversing the search order passed the whole suite until a project was built
    with both, because setup then wrote to a file the reader would not find.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for present, expected in (
        ([".claude"], ".claude"),
        ([".codex"], ".codex"),
        ([".claude", ".codex"], ".claude"),
    ):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            for agent in present:
                (root / agent).mkdir()
                (root / agent / "cerberus.json").write_text("{}", encoding="utf-8")
            got = cerberus_setup.resolve_config(root)
            assert got.parent.name == expected, f"{present} resolved to {got}"


def test_a_project_with_no_earlier_config_gets_one_in_its_root():
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / ".claude").mkdir()  # an agent directory is not a config location
        got = cerberus_setup.resolve_config(root)
        assert got == root / "cerberus.json", got


# --------------------------------------------------------- which kind it is


def _kind_fixtures() -> list[tuple[str, str, dict]]:
    """One project per kind the code can return, derived from the code.

    Hand-listing is why a mutant survived once already: the list named Node and
    Go, the code also supported Rust, and the mutant was wrong only there. Here
    the denominator is KIND_SIGNALS plus the two branches of
    _looks_like_a_command, so adding a signal without a fixture fails the test
    below rather than quietly widening the gap.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    base = {"pyproject.toml": '[project]\nname = "d"\nversion = "1"\n'}
    # A seed per signal file, chosen so the file is the ONLY thing that differs.
    seeds = {
        "Chart.yaml": "name: d\nversion: 0.1.0\n",
        "charts": None,          # a directory
        "main.tf": 'resource "null_resource" "d" {}\n',
        "Dockerfile": "FROM scratch\n",
        "docker-compose.yml": "services: {}\n",
        "k8s": None,
        "deploy": None,
    }
    out = []
    for kind, signals in cerberus_setup.KIND_SIGNALS:
        for signal in signals:
            assert signal in seeds, f"no fixture seed for KIND_SIGNALS entry {signal!r} — add one"
            files = dict(base)
            files[signal] = seeds[signal]
            out.append((f"{kind} via {signal}", kind, files))
    # The two branches that make a project a command. Not in KIND_SIGNALS —
    # its "cli" row is deliberately empty and decided from the manifests.
    out.append(("cli via [project.scripts]", "cli", {
        "pyproject.toml": '[project]\nname = "d"\nversion = "1"\n\n[project.scripts]\nd = "d:main"\n'}))
    out.append(("cli via package.json bin", "cli", {
        "package.json": json.dumps({"name": "d", "bin": {"d": "cli.js"},
                                    "scripts": {"test": "exit 0"}})}))
    out.append(("library, no signal at all", "library", dict(base)))
    return out


def _write(root: pathlib.Path, files: dict) -> None:
    for name, text in files.items():
        path = root / name
        if text is None:
            path.mkdir(parents=True, exist_ok=True)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def test_every_kind_the_code_can_return_is_pinned():
    """#35. The mutant that started it: CLI detection disabled, 0 failures."""
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for label, expected, files in _kind_fixtures():
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            _write(root, files)
            _, kind = cerberus_setup.detect(root)
            assert kind == expected, f"{label}: detected {kind!r}, expected {expected!r}"


def test_the_kind_reaches_the_configuration_and_the_reader():
    """A kind that stops at the return value helps nobody.

    It has to reach `artifact_kind` in the file, and the sentence about where
    the last check has to happen has to be the one for that kind — that
    sentence is the whole reason the field exists.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for label, expected, files in _kind_fixtures():
        root = project(files)
        code, out = run_setup(root)
        if code != 0:
            continue  # that toolchain is not installed here; nothing was written
        got = config_of(root)["verification"]["artifact_kind"]
        assert got == expected, f"{label}: config says {got!r}, expected {expected!r}"
        hint = cerberus_setup.STAGE2_HINT_BY_KIND[expected]
        # The hint has to survive the draft offer. It said what stage2 is FOR;
        # an offer to draft one is not a substitute, and replacing it was
        # caught here rather than by reading.
        assert hint in out, f"{label}: the reader was given the wrong advice\n{out}"


def test_a_project_that_is_two_things_at_once_resolves_the_documented_way():
    """A Python CLI in a container is both, and the order decides.

    Pinned rather than argued: KIND_SIGNALS puts `service` ahead of the
    manifest check, so a Dockerfile wins. That is the current answer and it is
    defensible — what is not defensible is nothing recording it, so that
    reordering the table changes somebody's Stage 2 advice in silence.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        _write(root, {
            "pyproject.toml": '[project]\nname = "d"\nversion = "1"\n\n[project.scripts]\nd = "d:main"\n',
            "Dockerfile": "FROM scratch\n",
        })
        _, kind = cerberus_setup.detect(root)
        assert kind == "service", f"a containerised CLI resolved as {kind!r}"

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        _write(root, {"pyproject.toml": '[project]\nname = "d"\nversion = "1"\n',
                      "Dockerfile": "FROM scratch\n", "Chart.yaml": "name: d\n"})
        _, kind = cerberus_setup.detect(root)
        assert kind == "chart", f"the more specific signal lost: {kind!r}"


def test_a_manifest_that_cannot_be_read_is_not_a_command():
    """Both branches swallow their exception, so both need a case.

    A malformed manifest reading as a CLI would be a guess dressed as a fact,
    and the swallowed exception means nothing else would ever say so.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for name, text in (("package.json", "{not json"),
                       ("pyproject.toml", "[project\nbroken")):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / name).write_text(text, encoding="utf-8")
            assert cerberus_setup._looks_like_a_command(root) is False, name


# ------------------------------------------------------ what a re-run says


#: Lines that teach rather than report. Repeating one on a second run is the
#: defect in #39; repeating a check result or a named gap is not, because
#: those are measured again each time.
TEACHING = re.compile(r"invoke|yours to|ask for the|before saying", re.I)


def _two_runs(files: dict) -> tuple[str, str]:
    root = project(files)
    _, first = run_setup(root)
    _, second = run_setup(root)
    return first, second


def test_a_second_run_repeats_no_instruction():
    """#39, point 1 as amended: state may repeat, advice may not."""
    first, second = _two_runs(PY_PROJECT)
    lines_first = {l.rstrip() for l in first.splitlines() if l.strip()}
    repeated = [l.rstrip() for l in second.splitlines()
                if l.strip() and l.rstrip() in lines_first]
    teaching = [l for l in repeated if TEACHING.search(l)]
    assert not teaching, "a second run repeated instructions:\n  " + "\n  ".join(teaching)


def test_a_second_run_still_reports_what_is_outstanding():
    """The other half, or the fix above would pass by printing nothing.

    A re-run that says only "nothing changed" is worse than the noise it
    replaced: the gap it exists to surface is the empty stage2.
    """
    _, second = _two_runs(PY_PROJECT)
    assert "Still missing" in second, second
    assert "Checks it lists" in second, second


def test_a_first_run_still_says_what_was_and_was_not_installed():
    """#39 point 4, reworded by #43.

    It used to promise that nothing would happen, which was false: an agent
    that reads the skill's description may reach for it unasked, and one did.
    What is true, and what the reader needs, is that no hook was installed.
    """
    first, _ = _two_runs(PY_PROJECT)
    assert "No hook was installed" in first, first
    assert "runs by itself" not in first, f"promising silence again:\n{first}"


def test_a_check_the_configuration_already_lists_is_not_offered_back():
    """#39, point 2. One check, printed under two headings, ran twice."""
    _, second = _two_runs(PY_PROJECT)
    commands = [l.strip() for l in second.splitlines() if l.strip().startswith("ok ")]
    assert len(commands) == len(set(commands)), f"a check was shown twice:\n{second}"


def test_a_check_the_configuration_lacks_is_still_offered():
    """The mixed cell: the block has to shrink, not vanish.

    A project configured with a check that is not the one detection finds must
    still be told about the other one, or point 2 is satisfied by deleting the
    feature.
    """
    hand = {"verification": {"artifact_kind": "library", "stage1": ["true"], "stage2": ["true"]}}
    root = project({**PY_PROJECT, "cerberus.json": json.dumps(hand)})
    _, out = run_setup(root)
    assert "not in its list" in out, out
    assert "compileall" in out or "pytest" in out, out


def _project_with_a_failing_check() -> pathlib.Path:
    """A project where some check RUNS and fails — not one that is absent.

    The first version used a deliberately failing pytest, and pytest is not
    installed on every runner: there it came back 127, which is "absent", the
    warning never printed, and the test failed for a reason that had nothing to
    do with what it checks. So the toolchain is probed rather than assumed, and
    if none of them can produce the state the test needs it says so out loud
    instead of passing quietly.
    """
    if shutil.which("pytest"):
        return project({**PY_PROJECT,
                        "tests/test_demo.py": "def test_bad():\n    assert False\n"})
    if shutil.which("npm"):
        return project({"package.json": json.dumps(
            {"name": "d", "scripts": {"test": "exit 1", "lint": "exit 0"}})})
    raise AssertionError(
        "no toolchain here can run a check and fail it — install pytest or npm; "
        "skipping silently would report coverage this test does not have")


def test_a_failing_check_is_named_once_and_not_explained_twice():
    """#41. It used to be said twice: once as FAILING, once as a warning.

    The second was the "worth a look first" line #39 moved next to the list.
    Moving it was the right fix for where it sat; deleting it is the right fix
    for it existing, and the list still carries the fact.
    """
    root = _project_with_a_failing_check()
    _, out = run_setup(root)
    assert "FAILING" in out, out
    assert "worth a look" not in out, f"the same fact, twice:\n{out}"
    named = [l for l in out.splitlines() if "failing" in l.lower()]
    assert len(named) == 1, f"the failure is mentioned {len(named)} times:\n{out}"


# --------------------------------------------------------- drafting stage2


DEPLOYED_PROJECT = {
    **PY_PROJECT,
    "Dockerfile": "FROM scratch\n",
    "helm/Chart.yaml": "name: d\nversion: 0.1.0\n",
}


def _draft(root: pathlib.Path) -> str:
    return run_setup(root, "--draft-stage2")[1]


def test_a_draft_is_offered_when_the_repository_says_how_it_deploys():
    """#45, point 1. The default run stays short and points at the draft."""
    root = project(DEPLOYED_PROJECT)
    _, out = run_setup(root)
    assert "--draft-stage2" in out, out
    assert "Dockerfile" in out or "helm" in out, "it did not say what it read"


def test_no_draft_and_no_guess_when_nothing_says_how_it_deploys():
    """#45, point 4. A repository that gave no grounds gets no plausible answer."""
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    assert "--draft-stage2" not in out, out
    drafted = _draft(root)
    assert "kubectl" not in drafted and "helm upgrade" not in drafted, drafted


def test_a_service_with_no_deployment_evidence_gets_no_draft():
    """#45, point 4, on the path detection cannot reach.

    `service` is detected FROM a Dockerfile, so this case only arises when a
    person writes the kind by hand — and then there is nothing in the tree to
    derive a deploy from. Dropping the evidence guard passed the whole suite
    until this existed, because every fixture that reached the guard was a
    library.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for kind in cerberus_setup.DEPLOYED_KINDS:
        assert cerberus_setup.draft_stage2(kind, []) == [], (
            f"{kind} with no evidence was given a draft anyway")

    root = project({**PY_PROJECT, "cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "service", "stage1": ["true"], "stage2": []}})})
    out = _draft(root)
    assert "will not invent" in out, out
    assert "curl" not in out.split("Whatever you write")[0], out


def test_a_dockerfile_does_not_make_a_library_a_deployment():
    """#45's mixed cell. A repo can hold a Dockerfile for CI and ship a library.

    Drafting a deploy here would be a confident wrong answer, which this
    project treats as worse than saying nothing.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    evidence = [("image", "Dockerfile"), ("helm", "helm/")]
    assert cerberus_setup.draft_stage2("library", evidence) == []
    assert cerberus_setup.draft_stage2("cli", evidence) == []
    assert cerberus_setup.draft_stage2("service", evidence), "a service got nothing"


def test_the_draft_is_never_written_to_the_configuration():
    """#45, point 2. The rule that keeps setup's output trustworthy.

    It cannot run a deploy, so it may not record one. Proposing is not writing.
    """
    root = project(DEPLOYED_PROJECT)
    run_setup(root)
    before = (root / "cerberus.json").read_bytes()
    _draft(root)
    assert (root / "cerberus.json").read_bytes() == before, "the draft was written"
    assert config_of(root)["verification"]["stage2"] == []


def test_no_line_of_the_draft_could_pass_on_a_broken_deploy():
    """#45, point 3. Every proposed command must be able to exit non-zero.

    Checked against the shapes the script itself refuses, so a line added to
    the draft that cannot fail is caught by the same rule it teaches.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for kind in cerberus_setup.DEPLOYED_KINDS:
        for evidence in ([("helm", "helm/"), ("image", "Dockerfile")],
                         [("k8s", "k8s/")],
                         [("compose", "docker-compose.yml")],
                         [("ci", ".github/workflows/deploy.yml")]):
            for line in cerberus_setup.draft_stage2(kind, evidence):
                why = cerberus_setup.unfailable(line)
                assert why is None, f"{kind}/{evidence[0][0]}: {line!r} — {why}"


def test_the_draft_names_the_traps_rather_than_only_avoiding_them():
    """Avoiding them silently teaches nothing; the reader edits these lines."""
    root = project(DEPLOYED_PROJECT)
    out = _draft(root)
    for trap in ("-f on curl", "grep -q", "jq -e"):
        assert trap in out, f"the draft never explains {trap}:\n{out}"
    assert "before your change" in out, "it never says to prove the draft can fail"


def test_the_trap_detector_actually_catches_each_trap():
    """The detector is what the test above leans on, so it is checked directly."""
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for command in ("curl https://x/health",
                    "echo deployed",
                    "true",
                    "# deploy it",
                    "logcli query '{app=\"x\"}' --since=5m",
                    "YOUR_LOG_QUERY --since=5m"):
        assert cerberus_setup.unfailable(command), f"missed: {command!r}"
    for command in ("curl -f https://x/health",
                    "kubectl -n dev rollout status deploy/x",
                    "logcli query '{app=\"x\"}' | grep -q abc"):
        assert cerberus_setup.unfailable(command) is None, f"false alarm: {command!r}"


# ----------------------------------------------- a boundary declared unreachable


def _with_unreachable(reason) -> pathlib.Path:
    root = project(PY_PROJECT)
    run_setup(root)
    path = root / "cerberus.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["verification"]["stage2_unreachable"] = reason
    path.write_text(json.dumps(body, ensure_ascii=False, indent=2), encoding="utf-8")
    return root


def test_a_declared_reason_is_reported_and_quoted():
    """#45, point 6. Optional, but never invisible."""
    root = _with_unreachable("no dev cluster; run by hand")
    code, out = run_setup(root)
    assert code == 0, out
    assert "no dev cluster; run by hand" in out, out
    assert "Stage 1" in out, "it never says what the verdict narrows to"


def test_a_declared_key_with_no_reason_is_refused():
    """#45, point 7. Blank is an unfinished configuration, not consent.

    Accepted silently it produces a verdict that narrows itself and cannot say
    why — the invisible gap this key exists to make visible.
    """
    for blank in ("", "   ", None, 3):
        root = _with_unreachable(blank)
        code, out = run_setup(root)
        assert code == 2, f"{blank!r} was accepted:\n{out}"
        assert "no reason" in out, out


def test_declaring_it_unreachable_silences_the_draft_offer():
    """Two answers to the same question, printed together, is one too many."""
    root = project(DEPLOYED_PROJECT)
    run_setup(root)
    path = root / "cerberus.json"
    body = json.loads(path.read_text(encoding="utf-8"))
    body["verification"]["stage2_unreachable"] = "no cluster of any kind"
    path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    _, out = run_setup(root)
    assert "--draft-stage2" not in out, out


# ------------------------------------------------ stage2 when CI does the deploy


CI_PROJECT = {
    **PY_PROJECT,
    ".github/workflows/deploy.yml":
        "name: deploy\njobs:\n  deploy:\n    steps:\n      - run: kubectl apply -f k8s/\n",
    "cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "service", "stage1": ["true"], "stage2": []}}),
}


def test_a_ci_deployed_project_gets_commands_not_prose():
    """#47, point 1. The commonest shape used to get a paragraph and no list."""
    root = project(CI_PROJECT)
    out = _draft(root)
    assert "gh run watch" in out, out
    assert "git push" in out, out


def test_the_draft_proves_the_running_instance_is_this_commit():
    """#47, point 2 — the whole reason this issue exists.

    Waiting for a pipeline proves it ran. It does not prove the pod answering
    you was replaced, that the run watched was yours, or that the ref deployed
    was this one. Without this line Stage 2 goes green against yesterday's
    build.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for evidence, forge in (
        ([("ci", ".github/workflows/deploy.yml")], ("github", "gh run watch --exit-status X")),
        ([("helm", "helm/"), ("image", "Dockerfile")], None),
        ([("k8s", "k8s/")], None),
    ):
        draft = cerberus_setup.draft_stage2("service", evidence, forge)
        assert any("rev-parse HEAD" in line and "version" in line for line in draft), (
            f"{evidence[0][0]}: nothing ties the running instance to this commit:\n" +
            "\n".join(draft))


def test_waiting_for_a_pipeline_is_a_command_that_can_fail():
    """#47, point 3. A wait that cannot go red makes the whole stage green."""
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    draft = cerberus_setup.draft_stage2(
        "service", [("ci", ".github/workflows/deploy.yml")], cerberus_setup.FORGES[0][1:])
    for line in draft:
        why = cerberus_setup.unfailable(line)
        assert why is None, f"{line!r} — {why}"
    for cannot in ("sleep 120",
                   "gh run watch 123",
                   "gh run list --limit 1"):
        assert cerberus_setup.unfailable(cannot), f"missed: {cannot!r}"
    assert cerberus_setup.unfailable("gh run watch --exit-status 123") is None
    # The correct form uses `gh run list` to pick the run for this commit. A
    # rule that condemns it pushes the reader toward watching whatever ran last.
    assert cerberus_setup.unfailable(
        "gh run watch --exit-status $(gh run list --commit $(git rev-parse HEAD) "
        "--limit 1 --json databaseId --jq '.[0].databaseId')") is None


def test_the_forge_decides_the_wait_and_an_unknown_one_says_so():
    """The one command that cannot be guessed across forges."""
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        assert cerberus_setup.forge_of(root) is None
        (root / ".gitlab-ci.yml").write_text("stages: [deploy]\n", encoding="utf-8")
        name, wait = cerberus_setup.forge_of(root)
        assert name == "gitlab"
        assert "YOUR_" in wait, "it invented a gitlab command instead of asking"
        assert "non-zero" in wait, "the placeholder never says what it must do"


def test_the_wrong_revision_trap_is_explained_not_only_avoided():
    """#47, point 5. The reader edits these lines; a silent guard teaches nothing."""
    root = project(CI_PROJECT)
    out = _draft(root)
    assert "yesterday's" in out or "not that the pod" in out, out


def test_the_skill_states_the_three_answers_to_merge_only_deployment():
    """#47, point 4. Choosing silently is how a verdict covers an undeployed revision."""
    for path in (SKILLS / "cerberus-setup" / "SKILL.md", SKILLS / "cerberus-setup" / "SKILL.ru.md"):
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for needle in ("preview", "stage2_unreachable") if path.name.endswith("ru.md") is False \
                else ("превью", "stage2_unreachable"):
            assert needle in text, f"{path.name}: {needle!r}"
        assert "merge" in text or "мерж" in text, path.name


def test_the_skill_asks_about_access_before_writing_commands():
    """A stage2 nobody can run returns Not proven forever, for a mechanical reason."""
    for path, needles in ((SKILLS / "cerberus-setup" / "SKILL.md", ("access", "credentials")),
                          (SKILLS / "cerberus-setup" / "SKILL.ru.md", ("доступ", "учётные"))):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"


def test_the_skill_requires_reading_the_commands_back_before_writing_them():
    """What they said and what you understood diverge silently."""
    for path, needle in ((SKILLS / "cerberus-setup" / "SKILL.md", "say back what you understood"),
                         (SKILLS / "cerberus-setup" / "SKILL.ru.md", "перескажи, что ты понял")):
        assert needle in path.read_text(encoding="utf-8").lower(), path.name


def test_setup_cannot_finish_in_the_same_turn_as_stage2_confirmation():
    for path, needles in (
        (SKILLS / "cerberus-setup" / "SKILL.md",
         ("hard turn boundary", "end that response with the confirmation question",
          "cannot be `configured` before")),
        (SKILLS / "cerberus-setup" / "SKILL.ru.md",
         ("жёсткая граница хода", "закончи ответ вопросом о подтверждении",
          "не может получить статус `configured` до")),
    ):
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"


# ------------------------------------- Not proven has to carry an attempt (#49)


def test_the_skill_requires_an_attempt_behind_every_not_proven():
    """#49. The clause written for honesty was the quietest way to skip work.

    Three verdicts in this repository declared a boundary unreachable while the
    tool to reach it was installed. Prose alone did not hold it, so the rule is
    pinned here and named in the self-check.
    """
    for path, needles in (
        (SKILLS / "cerberus" / "SKILL.md",
         ("not proven needs an attempt", "command -v", "carries the attempt")),
        (SKILLS / "cerberus" / "SKILL.ru.md",
         ("требует попытки", "command -v", "несёт попытку")),
    ):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"


def test_the_rule_names_the_case_that_produced_it():
    """A general rule already covered this and did not stop it.

    "It depends on what an agent does" reads as a property of the world rather
    than as a command anyone could type, so the case is named outright.
    """
    for path, needle in ((SKILLS / "cerberus" / "SKILL.md", "claude -p"),
                         (SKILLS / "cerberus" / "SKILL.ru.md", "claude -p")):
        assert needle in path.read_text(encoding="utf-8"), path.name


def test_the_self_check_asks_for_it_at_verdict_time():
    """A rule nobody reads at the moment of writing a verdict is decoration."""
    for path, needle in ((SKILLS / "cerberus" / "SKILL.md", "does every `not proven` carry"),
                         (SKILLS / "cerberus" / "SKILL.ru.md", "каждое `not proven` несёт")):
        text = path.read_text(encoding="utf-8").lower()
        assert needle in text, path.name
        checklist = [l for l in text.splitlines() if l.startswith("- [ ]")]
        assert any(needle in l for l in checklist), f"{path.name}: it is prose, not a check"


def test_this_repository_verifies_it_with_a_live_session():
    """#49, point 4. The only part that is mechanical rather than well-meant.

    Every earlier fix here was text asking an agent to behave. This one is a
    command in our own stage2, so the claim cannot be waved through again
    without someone deleting a line.
    """
    body = json.loads((ROOT / "cerberus.json").read_text(encoding="utf-8"))
    stage2 = body["verification"]["stage2"]
    live = [c for c in stage2 if "claude -p" in c]
    assert live, f"stage2 has no live agent session:\n" + "\n".join(stage2)
    assert any("--continue" in c for c in live), (
        "a single prompt cannot show a conversation happening; the readback and "
        "the follow-up questions are the part #49 is about")
    for command in live:
        assert "jq -e" in command or "grep -q" in command, (
            f"this cannot fail, so it proves nothing: {command}")


# ------------------------------------- a filled stage2 has to be ready (#51)


def _with_stage2(commands: list) -> pathlib.Path:
    return project({**PY_PROJECT, "cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "service", "stage1": ["true"],
                          "stage2": commands}})})


def test_a_stage2_still_holding_the_drafts_blanks_is_refused():
    """#51, point 1. Pasted verbatim, a draft reads as configuration.

    It then fails on a hostname nobody set, at the moment a verdict was due —
    and the tempting way to write that up is the honest-looking `Not proven`
    #49 was about.
    """
    root = _with_stage2(["curl -fsS YOUR_URL/version | jq -e .",
                         "YOUR_LOG_QUERY --since=5m | grep -q x"])
    code, out = run_setup(root)
    assert code == 2, out
    assert "YOUR_URL" in out and "YOUR_LOG_QUERY" in out, "it did not name the blanks"


def test_a_finished_stage2_is_not_called_unfinished():
    """The other side, or the rule is satisfied by refusing everything."""
    root = _with_stage2(["curl -fsS https://svc.dev/version | jq -e .revision"])
    code, out = run_setup(root)
    assert code == 0, out
    assert "blanks" not in out, out


def test_the_blank_detector_does_not_fire_on_ordinary_shell():
    """Env vars and real hosts are uppercase too; a loose rule would refuse them."""
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    assert cerberus_setup.unfinished([
        "PYTHONPATH=src python3 -m pytest -q",
        "RID=cerb-$(git rev-parse --short HEAD)",
        "curl -fsS https://API.EXAMPLE.COM/v1 | jq -e .",
        "kubectl -n prod rollout status deploy/svc",
    ]) == []
    assert cerberus_setup.unfinished(["helm upgrade YOUR_APP ./charts"]) == ["YOUR_APP"]


def test_every_blank_the_draft_emits_is_one_the_detector_catches():
    """The rule has to cover what this script itself prints.

    Twice now a guard has been written for other people's commands and missed
    its own: the log-query placeholder, and the `gh run list` form. Derived
    from the draft rather than hand-listed so it cannot happen a third time.
    """
    sys.path.insert(0, str(SETUP.parent))
    import cerberus_setup

    for kind in cerberus_setup.DEPLOYED_KINDS:
        for evidence, forge in (([("helm", "helm/"), ("image", "Dockerfile")], None),
                                ([("k8s", "k8s/")], None),
                                ([("ci", ".github/workflows/deploy.yml")],
                                 cerberus_setup.FORGES[0][1:])):
            draft = cerberus_setup.draft_stage2(kind, evidence, forge)
            blanks = [w for line in draft for w in line.split()
                      if w.isupper() and len(w) > 3 and w.strip("'\"$(){}|") == w]
            missed = [b for b in blanks if not cerberus_setup.unfinished([b])]
            assert not missed, f"the draft emits blanks the detector misses: {missed}"


def test_the_skill_states_that_a_filled_stage2_is_not_optional():
    """#51, point 2. Implied everywhere, written nowhere."""
    for path, needles in (
        (SKILLS / "cerberus" / "SKILL.md",
         ("three states of stage2", "removed the choice", "**run it**")),
        (SKILLS / "cerberus" / "SKILL.ru.md",
         ("три состояния stage2", "снял выбор", "**выполнить**")),
    ):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


def test_the_skill_calls_missing_access_a_blocker_not_a_narrowing():
    """#51, point 3. "We could not log in today" must not lower the bar for good."""
    for path, needles in ((SKILLS / "cerberus" / "SKILL.md",
                           ("no access to run it", "not a narrowing")),
                          (SKILLS / "cerberus" / "SKILL.ru.md",
                           ("нет доступа выполнить", "не сужение"))):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"


def test_the_three_states_are_named_in_one_place():
    """#51, point 4. Scattered across three sections, nobody sees which they are in."""
    for path in (SKILLS / "cerberus" / "SKILL.md", SKILLS / "cerberus" / "SKILL.ru.md"):
        text = path.read_text(encoding="utf-8")
        section = re.search(r"^### .*(?:three states|Три состояния).*?(?=^### )",
                            text, re.M | re.S)
        assert section, f"{path.name}: no single section naming the states"
        body = section.group(0)
        for needle in ("stage2_unreachable", "`Not proven`"):
            assert needle in body, f"{path.name}: the section never mentions {needle}"
        assert body.count("|") > 8, f"{path.name}: the three are not set out together"


def test_the_self_check_asks_whether_a_filled_stage2_was_run():
    for path, needle in ((SKILLS / "cerberus" / "SKILL.md", "if `stage2` was filled in, was it run"),
                         (SKILLS / "cerberus" / "SKILL.ru.md", "если `stage2` был заполнен")):
        checklist = [l for l in path.read_text(encoding="utf-8").lower().splitlines()
                     if l.startswith("- [ ]")]
        assert any(needle in l for l in checklist), f"{path.name}: not in the checklist"


# ------------------------------------------------- what installing does NOT do


def test_installing_writes_no_file_the_project_owns():
    """#33, item 1. The absence is the feature, so it is the assertion."""
    for flag in ("--claude", "--codex"):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / ".claude").mkdir()
            settings = root / ".claude" / "settings.json"
            mine = json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "mine"}]}]}})
            settings.write_text(mine, encoding="utf-8")
            code, out = run_install(root, flag)
            assert code == 0, out
            assert settings.read_text(encoding="utf-8") == mine, f"{flag} edited settings.json"
            assert not (root / ".codex" / "hooks.json").exists(), f"{flag} wrote codex wiring"
            for stray in (".claude/hooks", ".codex/hooks"):
                assert not (root / stray).exists(), f"{flag} installed {stray}"


def test_installing_leaves_no_hook_script_anywhere():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        code, out = run_install(root, "--claude")
        assert code == 0, out
        strays = [p for p in root.rglob("*.py") if p.name in ("cerberus_gate.py", "cerberus_mark.py",
                                                              "cerberus_config.py")]
        assert not strays, strays


def test_installing_brings_every_skill_and_the_script_beside_its_own():
    for flag, where in (("--claude", ".claude/skills"), ("--codex", ".agents/skills")):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            code, out = run_install(root, flag)
            assert code == 0, out
            installed = {p.name for p in (root / where).iterdir()} if (root / where).is_dir() else set()
            expected = {p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists()}
            assert installed == expected, f"{flag}: installed {installed}, expected {expected}"
            script = root / where / "cerberus-setup" / "cerberus_setup.py"
            assert script.exists(), f"{flag}: the cerberus-setup skill describes a script that was not installed"
            # `cp -R` of a source tree that has been run carries its byte cache,
            # stamped with this machine's Python version, into the user's repo.
            junk = [str(p.relative_to(root)) for p in root.rglob("__pycache__")]
            junk += [str(p.relative_to(root)) for p in root.rglob("*.pyc")]
            assert not junk, f"{flag}: installed this machine's leftovers: {junk}"


def test_installing_leaves_a_config_and_setup_completes_it():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        for name, text in PY_PROJECT.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        code, out = run_install(root, "--claude", "--setup")
        assert code == 0, out
        body = config_of(root)
        assert body["verification"]["stage1"], out
        assert not any("replace with" in c for c in body["verification"]["stage1"]), body
        # An allowlist, because the named list missed `//verification` — a
        # comment key carried over from the example — and CI caught what this
        # test did not. Comment keys are allowed; DEAD_KEYS are named too, so a
        # failure says which one came back rather than only that one did.
        for key in DEAD_KEYS:
            assert key not in body, f"install left a dead key: {key}"
        extra = {k for k in body if k != "verification" and not k.startswith("//")}
        assert not extra, f"install left keys nothing reads: {extra}"


def test_an_existing_config_from_an_earlier_version_is_not_duplicated():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / ".claude").mkdir()
        (root / ".claude" / "cerberus.json").write_text('{"verification": {"stage1": ["true"]}}',
                                                        encoding="utf-8")
        code, out = run_install(root, "--claude")
        assert code == 0, out
        assert not (root / "cerberus.json").exists(), "wrote a second config beside the existing one"


# ------------------------------------------------------------ repository state


#: A line naming dead machinery in order to assert it is absent is the opposite
#: of the failure this looks for, and CI is full of them on purpose. Matched on
#: the line rather than the file, so a genuine description sitting next to an
#: assertion is still caught.
DENIES = re.compile(r"test !|test -z|not in |assert not|must not|no longer|-name '")


def test_nothing_in_the_repository_still_describes_the_hooks():
    """#33, item 4. Documentation that describes machinery that is gone ships.

    "Describes" is the requirement, not "mentions": the check below skips lines
    that name the machinery in order to assert its absence.
    """
    dead = re.compile(r"cerberus_gate|cerberus_mark|cerberus_config|cerberus-pending"
                      r"|PostToolUse|\benforce\b|claim_patterns|watch_paths")
    skip_dirs = {".git", "__pycache__", "node_modules", ".venv"}
    # CHANGELOG is generated history and describes versions where these existed.
    # tests/ names them on purpose — this test is in it.
    skip_files = {"CHANGELOG.md"}
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in (".md", ".json", ".py", ".sh", ".yml", ".yaml"):
            continue
        if set(path.relative_to(ROOT).parts) & skip_dirs or path.name in skip_files:
            continue
        if path.relative_to(ROOT).parts[0] == "tests":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            if DENIES.search(line):
                continue
            if dead.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()[:70]}")
    assert not offenders, "still describing machinery that was removed:\n  " + "\n  ".join(offenders)


# ------------------------------------------------------------ what it reads like


def test_the_output_uses_no_internal_vocabulary():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    found = jargon_in(out)
    assert not found, f"jargon reached the user: {found}\n{out}"


#: Non-empty lines the longest output may take — a first install with a check
#: that ran and failed. Set AT the current output rather than above it: the
#: previous bound was 24 against an actual 13, which no drift could ever reach,
#: so it read as a limit while being decoration.
MAX_LINES = 8


def test_the_output_fits_in_a_glance():
    """Measured on the longest case there is, not on the tidiest."""
    root = _project_with_a_failing_check()
    _, out = run_setup(root)
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) <= MAX_LINES, f"{len(lines)} lines of output:\n{out}"


def test_the_bound_is_one_the_output_could_actually_cross():
    """A limit nothing can reach is not a limit.

    This is the guard on the guard: raising MAX_LINES back out of reach is the
    cheapest way to pass the test above, and it would leave the suite green
    while the requirement was gone.
    """
    root = _project_with_a_failing_check()
    _, out = run_setup(root)
    lines = len([l for l in out.splitlines() if l.strip()])
    assert MAX_LINES - lines <= 2, (
        f"the bound is {MAX_LINES} and the output is {lines} — "
        "slack that wide means nothing will ever fail this")


def test_shortening_did_not_drop_any_of_the_facts():
    """#41, point 1. The cheapest way to pass a length test is to say less.

    Each of the six is asserted separately, against the longest output, so a
    fact removed fails by name rather than by a count nobody reads.
    """
    root = _project_with_a_failing_check()
    _, out = run_setup(root)
    facts = {
        "which toolchain": r"Python|Node|Rust|Go",
        "which kind": r"\b(cli|library|service|chart|migration|model-boundary|plugin)\b",
        "what was written": r"^  ok ",
        "what failed": r"FAILING",
        "what was not installed": r"[Nn]o hook was installed",
        "what is still missing": r"[Ss]till missing",
    }
    absent = [name for name, shape in facts.items() if not re.search(shape, out, re.M)]
    assert not absent, f"shortening dropped: {absent}\n{out}"


def test_the_closing_message_says_what_it_owes_the_reader():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    low = out.lower()
    assert "no hook was installed" in low, out
    assert "cerberus skill" in low, out
    assert "cerberus.json" in low, out


def test_questions_come_with_concrete_options():
    root = project(MAKE_PROJECT)
    _, out = run_setup(root)
    assert "1." in out and "2." in out, out


#: Words another plugin will also use for a skill. Skill names are one flat
#: namespace across everything a person has installed, and a collision is
#: silent: two directories answer to the name, both load, and the agent picks
#: by description. Reproduced on #69 with a foreign `setup`.
GENERIC_NAMES = {
    "setup", "critic", "review", "test", "tests", "check", "verify", "docs",
    "build", "deploy", "release", "lint", "format", "install", "config",
    "gate", "audit", "plan", "commit", "debug",
}


def test_no_skill_is_named_something_another_plugin_would_use():
    """#69, point 5. Fixed once and left to judgement is fixed until the next skill.

    `cerberus` keeps its name: it is the product, and a distinctive one. The
    other two were named for their role inside this repository, as though this
    repository were the only thing installed.
    """
    for skill in sorted(SKILLS.iterdir()):
        if not (skill / "SKILL.md").exists():
            continue
        head = (skill / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        declared = re.search(r"^name:\s*(\S+)", head, re.M).group(1)
        assert declared == skill.name, (
            f"{skill.name}: frontmatter says {declared!r}")
        if declared == "cerberus":
            continue
        assert declared not in GENERIC_NAMES, (
            f"{declared!r} is a name another plugin will use — prefix it")
        assert declared.startswith("cerberus-"), (
            f"{declared!r} does not say whose it is")


def test_the_product_keeps_its_own_name():
    """#69, point 4. Renaming everything for symmetry helps nobody."""
    names = {p.name for p in SKILLS.iterdir() if (p / "SKILL.md").exists()}
    assert "cerberus" in names, f"the product lost its name: {names}"
    assert "cerberus-cerberus" not in names


def test_both_languages_declare_the_same_skill_name():
    """A rename that touches one file of a pair is a skill with two names."""
    for skill in sorted(SKILLS.iterdir()):
        ru = skill / "SKILL.ru.md"
        if not ru.exists():
            continue
        head = ru.read_text(encoding="utf-8").split("---")[1]
        declared = re.search(r"^name:\s*(\S+)", head, re.M).group(1)
        assert declared == skill.name, f"{skill.name}: SKILL.ru.md says {declared!r}"


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
            except AssertionError as exc:
                print(f"  FAIL {name}: {exc}")
                failures += 1
            except Exception as exc:  # a broken test is a failing test
                print(f"  ERROR {name}: {type(exc).__name__}: {exc}")
                failures += 1
    print("all tests passed" if not failures else f"{failures} failing")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
