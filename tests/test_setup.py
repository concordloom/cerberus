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
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = ROOT / "plugins" / "cerberus" / "skills"
SETUP = SKILLS / "setup" / "cerberus_setup.py"
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
    target = tmp / ".claude" / "skills" / "setup"
    target.mkdir(parents=True)
    (target / "cerberus_setup.py").write_text(SETUP.read_text(encoding="utf-8"), encoding="utf-8")
    # `_write` rather than a loop here: some fixtures need a directory, which a
    # signal like `charts` or `k8s` actually is, and writing it as a file made
    # those kinds untestable through this helper.
    _write(tmp, files)
    return tmp


def run_setup(root: pathlib.Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(root / ".claude" / "skills" / "setup" / "cerberus_setup.py"), *args],
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
    assert "already has its own configuration" in out, out


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
    target = tmp / ".claude" / "skills" / "setup"
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
            script = root / where / "setup" / "cerberus_setup.py"
            assert script.exists(), f"{flag}: the setup skill describes a script that was not installed"


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
        # A section telling someone how to remove the old machinery has to name
        # it. Exempted by section rather than by line, because every line in it
        # is about removal and none of them describes anything as present.
        upgrading = False
        for n, line in enumerate(text.splitlines(), 1):
            if line.startswith("#"):
                upgrading = bool(re.search(r"[Uu]pgrad|Обновление", line))
            if upgrading or DENIES.search(line):
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


def test_the_output_fits_one_screen():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    lines = [l for l in out.splitlines() if l.strip()]
    assert len(lines) <= 24, f"{len(lines)} lines of output:\n{out}"


def test_the_closing_message_says_what_it_owes_the_reader():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    low = out.lower()
    assert "nothing here runs by itself" in low, out
    assert "invoke" in low, out
    assert "cerberus.json" in low, out


def test_questions_come_with_concrete_options():
    root = project(MAKE_PROJECT)
    _, out = run_setup(root)
    assert "1." in out and "2." in out, out


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
