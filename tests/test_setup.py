#!/usr/bin/env python3
"""Tests for cerberus_setup.py.

Two kinds of assertion here, and the second is the unusual one.

The ordinary kind: it detects what it should, writes only what it may, refuses
when it cannot tell, and demonstrates the refusal rather than reporting it.

The unusual kind: **what the user reads is tested**. "Friendly" is normally a
matter of taste and therefore un-gateable, so it is pinned to things a machine
can check — a list of words that must not appear, a line count, and the three
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
HOOKS = ROOT / "plugins" / "cerberus" / "hooks"
SETUP = HOOKS / "cerberus_setup.py"
EXAMPLES = ROOT / "examples" / "settings.json"

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
    three closing statements, and by somebody reading it.
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

# The four keys that REPLACE the built-in lists. A machine must never write
# them: a short guess makes the gate quietly narrower than advertised.
REPLACING_KEYS = ["claim_patterns", "ignore_patterns", "source_extensions", "watch_paths"]


def project(files: dict[str, str], wired: bool = True) -> pathlib.Path:
    """Build a throwaway project with the hooks installed."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / ".claude" / "hooks").mkdir(parents=True)
    for script in HOOKS.glob("*.py"):
        (tmp / ".claude" / "hooks" / script.name).write_text(
            script.read_text(encoding="utf-8"), encoding="utf-8"
        )
    if wired:
        (tmp / ".claude" / "settings.json").write_text(
            EXAMPLES.read_text(encoding="utf-8"), encoding="utf-8"
        )
    for name, text in files.items():
        path = tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp


def run_setup(root: pathlib.Path, *args: str) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(root / ".claude" / "hooks" / "cerberus_setup.py"), *args],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
    )
    return proc.returncode, proc.stdout + proc.stderr


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
    sys.path.insert(0, str(HOOKS))
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


def test_sets_up_a_python_project_and_shows_the_refusal():
    # Deliberately not asserting *which* command: the runner CI uses has no
    # pytest, so the script correctly falls back — and an earlier version of
    # this test pinned "pytest -q" and went red for the right behaviour. The
    # property is that something real was found and the refusal was shown.
    root = project(PY_PROJECT)
    rc, out = run_setup(root)
    assert rc == 0, out
    assert "refused" in out, "the demonstration must appear in the output: " + out
    config = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    assert config["verification"]["stage1"], "nothing was written to check"
    assert config["verification"]["artifact_kind"] == "library", config


def test_never_writes_a_check_it_did_not_run():
    # The failing command must not reach the file, and must be reported.
    root = project({**PY_PROJECT, ".ruff.toml": "line-length = 100\n"})
    rc, out = run_setup(root)
    config = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    for cmd in config["verification"]["stage1"]:
        assert not cmd.startswith("echo "), "a placeholder reached the config: " + cmd
        assert subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True).returncode == 0, cmd


def test_never_writes_the_keys_that_replace_defaults():
    for name, files in {"Python": PY_PROJECT, **OTHER_PROJECTS}.items():
        root = project(files)
        run_setup(root)
        config = root / ".claude" / "cerberus.json"
        if not config.exists():
            continue  # it refused, which is its own kind of correct
        raw = config.read_text(encoding="utf-8")
        for key in REPLACING_KEYS:
            assert key not in raw, f"{key} written for a {name} project"


def test_write_config_never_emits_the_replacing_keys_for_any_kind():
    """The rule at the function, not through a project.

    Going through a project skips whenever the toolchain is absent — cargo and
    go are not installed on the CI runner — and "skipped" is exactly where a
    mutant hides. This calls the writer directly for every kind it can produce.
    """
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    for kind in sorted(set(cerberus_setup.STAGE2_HINT_BY_KIND) | {"library", "service"}):
        for seed in ({}, {"//": "note"}, {"verification": {"stage1": ["echo x"]}}):
            with tempfile.TemporaryDirectory() as d:
                root = pathlib.Path(d)
                (root / "Cargo.toml").write_text("[package]\nname='d'\n", encoding="utf-8")
                (root / "go.mod").write_text("module d\n", encoding="utf-8")
                (root / "package.json").write_text("{}", encoding="utf-8")
                cerberus_setup.write_config(root, kind, ["true"], False, dict(seed))
                written = json.loads(
                    (root / ".claude" / "cerberus.json").read_text(encoding="utf-8")
                )
                for key in REPLACING_KEYS:
                    assert key not in written, f"{key} written for kind {kind}"


def test_never_writes_a_check_it_did_not_run_in_any_language():
    for name, files in OTHER_PROJECTS.items():
        root = project(files)
        run_setup(root)
        config = root / ".claude" / "cerberus.json"
        if not config.exists():
            continue
        for cmd in json.loads(config.read_text(encoding="utf-8"))["verification"]["stage1"]:
            code = subprocess.run(cmd, shell=True, cwd=str(root), capture_output=True).returncode
            assert code == 0, f"{name}: wrote a check that does not pass here: {cmd}"


def test_refuses_every_unsupported_build_system_rather_than_guessing():
    # A Makefile is a build system and a Dockerfile is a delivery detail;
    # neither says what the checks are. The Makefile half had a test and the
    # Dockerfile half did not, which is where the fifth mutant lived.
    for name, files in (("Makefile", MAKE_PROJECT), ("Dockerfile", DOCKER_PROJECT)):
        root = project(files)
        rc, out = run_setup(root)
        assert rc == 2, f"{name}: {out}"
        assert "could not tell" in out, out


def test_a_configured_project_reachable_only_by_hand_still_gets_an_answer():
    # Detection does not support Gradle, which is exactly why such a project is
    # configured by hand — and it was the population most needing "is it on?"
    # and the one refused before the question was asked.
    root = project({"build.gradle": "plugins { id 'java' }\n",
                    ".claude/cerberus.json": json.dumps(
                        {"verification": {"artifact_kind": "service", "stage1": ["true"]}})})
    rc, out = run_setup(root)
    assert rc == 0, out
    assert "Tried it:" in out, "it never demonstrated:\n" + out


def test_a_configured_project_runs_its_own_checks():
    # Certifying that the gate fires while the check it points at cannot pass
    # is this issue's split, living in the re-run path.
    root = project({**PY_PROJECT,
                    "tests/test_demo.py": "def test_bad():\n    assert False\n",
                    ".claude/cerberus.json": json.dumps(
                        {"verification": {"artifact_kind": "library", "stage1": ["pytest -q"]}})})
    rc, out = run_setup(root)
    assert "FAILING" in out or "absent" in out, out


def test_a_hand_written_step_is_not_mistaken_for_the_placeholder():
    root = project({**PY_PROJECT, ".claude/cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "library",
                          "stage1": ["echo 'running the suite' && pytest -q --maxfail=1"]}})})
    run_setup(root)
    after = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    assert "--maxfail=1" in after["verification"]["stage1"][0], after


def test_refuses_a_project_it_cannot_recognise():
    root = project({"notes.txt": "hello\n"})
    rc, out = run_setup(root)
    assert rc == 2, out
    assert "could not tell" in out, out
    assert not (root / ".claude" / "cerberus.json").exists(), "it guessed anyway"


def test_a_settings_file_that_only_mentions_the_names_is_not_wiring():
    # A substring check passed this: no hook object at all, just a comment.
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.json").write_text(
        json.dumps({"//": "TODO wire up cerberus_mark.py and cerberus_gate.py", "hooks": {}}),
        encoding="utf-8",
    )
    rc, out = run_setup(root)
    assert rc == 1, out
    assert "nothing here is calling it" in out, out


def test_a_plugin_install_is_not_called_broken():
    # No scripts in the project and no wiring in its settings is what a plugin
    # install looks like from inside, and it cannot be told apart from here.
    # Earlier attempts got this wrong in both directions: first denying it
    # (exit 1 on the install the README puts first), then asserting it from a
    # hooks.json next to the *script*, which certified projects with no hooks
    # at all whenever setup was run from a clone with --dir.
    #
    # So it is neither denied nor asserted: it is named, and the run does not
    # fail on it.
    # The scripts live outside the project, exactly as a plugin install has
    # them, so this runs the repository's own copy against the project.
    root = project(PY_PROJECT, wired=False)
    for stray in (root / ".claude" / "hooks").glob("*.py"):
        stray.unlink()
    proc = subprocess.run(
        [sys.executable, str(SETUP), "--dir", str(root)],
        cwd=str(root),
        capture_output=True,
        text=True,
        env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
    )
    rc, out = proc.returncode, proc.stdout + proc.stderr
    assert rc == 3, out
    assert "as a plugin" in out, out
    # And it must not then say the opposite: the caveat used to be followed by
    # the closing "from now on, claims are refused", which is the sentence the
    # user takes away and was false.
    assert "From now on" not in out, "it said it could not tell, then said it was on:\n" + out


def test_scripts_copied_here_but_unwired_is_a_failure():
    # The other half: the files are in this project and nothing runs them.
    # That is not the plugin case and must not be excused as one.
    root = project(PY_PROJECT, wired=False)
    rc, out = run_setup(root)
    assert rc == 1, out
    assert "nothing here is calling it" in out, out


def test_a_prompt_hook_is_not_wiring():
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "prompt",
            "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_mark.py'}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_gate.py'}]}],
    }}), encoding="utf-8")
    rc, out = run_setup(root)
    assert rc == 1, out


def test_a_cd_prefixed_command_is_still_wiring():
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command",
            "command": f"cd {root} && python3 .claude/hooks/cerberus_mark.py"}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": f"cd {root} && python3 .claude/hooks/cerberus_gate.py"}]}],
    }}), encoding="utf-8")
    rc, out = run_setup(root)
    assert rc == 0, "a cd-prefixed wiring read as unwired:\n" + out


def test_an_edit_lookalike_matcher_is_not_wiring():
    # MultiEdit and NotebookEdit contain "Edit" and never fire on an ordinary
    # Write or Edit.
    for matcher in ("MultiEdit", "NotebookEdit"):
        root = project(PY_PROJECT, wired=False)
        (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
            "PostToolUse": [{"matcher": matcher, "hooks": [{"type": "command",
                "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_mark.py'}]}],
            "Stop": [{"hooks": [{"type": "command",
                "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_gate.py'}]}],
        }}), encoding="utf-8")
        rc, out = run_setup(root)
        assert rc == 1, f"{matcher}: {out}"


def test_settings_local_json_is_read():
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.local.json").write_text(
        (ROOT / "examples" / "settings.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    rc, out = run_setup(root)
    assert rc == 0, "wiring in settings.local.json was ignored:\n" + out


def test_a_commented_out_entry_is_not_wiring():
    # How a person disables a hook, since JSON has no comments.
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command",
            "command": '# python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_mark.py'}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_gate.py'}]}],
    }}), encoding="utf-8")
    rc, out = run_setup(root)
    assert rc == 1, out


def test_an_entry_under_the_wrong_matcher_is_not_wiring():
    # Well formed, points at the real file, and fires on Bash — so nothing is
    # ever recorded and the gate never has anything to hold.
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command",
            "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_mark.py'}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/cerberus_gate.py'}]}],
    }}), encoding="utf-8")
    rc, out = run_setup(root)
    assert rc == 1, out


def test_an_entry_pointing_at_a_path_that_does_not_exist_is_not_wiring():
    # The check exists and nothing asserted it, so a mutant dropping it passed.
    root = project(PY_PROJECT, wired=False)
    (root / ".claude" / "settings.json").write_text(json.dumps({"hooks": {
        "PostToolUse": [{"matcher": "Write|Edit", "hooks": [{"type": "command",
            "command": "python3 /nonexistent/elsewhere/cerberus_mark.py"}]}],
        "Stop": [{"hooks": [{"type": "command",
            "command": "python3 /nonexistent/elsewhere/cerberus_gate.py"}]}],
    }}), encoding="utf-8")
    rc, out = run_setup(root)
    assert rc == 1, out


def test_a_project_path_with_a_space_is_still_recognised():
    root = project(PY_PROJECT)
    spaced = root.parent / (root.name + " with space")
    root.rename(spaced)
    rc, out = run_setup(spaced)
    assert rc == 0, "a space in the path read as unwired:\n" + out


def test_says_so_when_nothing_is_calling_it():
    # Scripts installed, settings not naming them: the state that looks
    # installed and guards nothing.
    root = project(PY_PROJECT, wired=False)
    rc, out = run_setup(root)
    assert rc == 1, out
    assert "nothing here is calling it" in out, out


def test_leaves_a_hand_written_configuration_alone():
    root = project({**PY_PROJECT, ".claude/cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "service", "stage1": ["make test"]}}
    )})
    rc, out = run_setup(root)
    assert rc == 0, out
    config = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    assert config["verification"]["stage1"] == ["make test"], "it overwrote real configuration"


def test_never_deletes_settings_it_cannot_write():
    # It writes only the verification block — but an earlier version replaced
    # the whole document, so a config that merely tuned the gate was deleted,
    # custom marker and all, silently, and the gate reverted to defaults.
    root = project({**PY_PROJECT, ".claude/cerberus.json": json.dumps({
        "//": "hand tuned",
        "claim_patterns": ["\\bshipped\\b"],
        "watch_paths": ["src/"],
        "marker": ".claude/mine-pending",
    })})
    rc, out = run_setup(root)
    after = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    for key in ("claim_patterns", "watch_paths", "marker"):
        assert key in after, f"{key} was deleted:\n{out}"


def test_a_failing_check_is_called_failing_not_absent():
    # It ran and did not pass. Reporting that as "did not run here" is false,
    # and it is the difference between a project with a broken suite and a
    # project without the tool installed.
    #
    # Driven through build_checks with synthetic commands rather than through a
    # real runner: CI has no pytest, so an earlier version of this asserted on
    # a suite that was absent rather than failing, and went red for the wrong
    # reason. Exit codes are the rule; the toolchain is not.
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    runner = {
        "name": "Synthetic",
        "files": [],
        "checks": [
            ("sh -c 'exit 0'", None),
            ("sh -c 'exit 1'", None),
            ("definitely-not-a-real-command-here", None),
        ],
        "fallback": None,
    }
    with tempfile.TemporaryDirectory() as d:
        results = cerberus_setup.build_checks([runner], pathlib.Path(d))
    codes = {cmd: code for cmd, code, _ in results}
    assert codes["sh -c 'exit 0'"] == 0
    assert codes["sh -c 'exit 1'"] == 1, "a check that ran and failed must not be 0 or 127"
    assert codes["definitely-not-a-real-command-here"] == 127, codes


def test_a_failing_check_is_reported_as_failing_end_to_end():
    # The same rule through the whole script, using a command that cannot be
    # missing: a Python file that does not compile makes the fallback fail.
    # Both, so the assertion holds whether or not pytest exists here: with it,
    # the suite runs and fails; without it, the compile fallback runs and fails
    # on the unparseable file.
    root = project({"pyproject.toml": '[project]\nname = "d"\nversion = "1"\n',
                    "tests/test_demo.py": "def test_bad():\n    assert False\n",
                    "broken.py": "def (\n"})
    rc, out = run_setup(root)
    assert "FAILING" in out or "none of its checks pass" in out, out
    assert "did not run here" not in out, out


def test_stage2_never_holds_something_that_was_not_run():
    # Comment lines in a list of commands exit 0 unconditionally — the
    # placeholder this whole issue is about, one field over.
    root = project(PY_PROJECT)
    run_setup(root)
    config = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    assert config["verification"]["stage2"] == [], config
    assert "still empty" in config["verification"]["notes"], config


def test_replaces_the_example_placeholders():
    # The population #13 exists for. Loads the *shipped* example rather than a
    # stand-in: a synthetic `{"verification": {...}}` missed that the real file
    # carries seven `//` reference keys, and a guard counting those as
    # hand-tuning made the documented one-liner leave the placeholders in place
    # and report success — this issue's own title, caused by its own fix.
    example = (ROOT / "cerberus.example.json").read_text(encoding="utf-8")
    root = project({**PY_PROJECT, ".claude/cerberus.json": example})
    rc, out = run_setup(root)
    assert rc == 0, out
    config = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    stage1 = config["verification"]["stage1"]
    assert stage1 and not any(str(c).startswith("echo ") for c in stage1), stage1


def test_check_mode_changes_nothing():
    root = project(PY_PROJECT)
    rc, out = run_setup(root, "--check")
    assert rc == 0, out
    assert not (root / ".claude" / "cerberus.json").exists(), "--check wrote a file"


def test_a_broken_gate_is_not_reported_as_working():
    # THE test. An earlier version of this greped the source for a string, so
    # replacing the whole demonstration with `return True, "...refused..."`
    # passed every test in this file — the one thing #13 declares must be
    # impossible, for the price of one line.
    #
    # This breaks the gate instead and demands that setup notice. Nothing that
    # returns a constant can survive it.
    root = project(PY_PROJECT)
    (root / ".claude" / "hooks" / "cerberus_gate.py").write_text(
        "import sys\nsys.exit(0)\n", encoding="utf-8"
    )
    rc, out = run_setup(root)
    assert rc != 0, "a gate that refuses nothing was reported as working:\n" + out
    assert "not guarding" in out, out


def test_a_gate_that_refuses_everything_is_not_reported_as_working():
    # The other half, and the reason the demonstration checks both directions:
    # a hook that blocks unconditionally would pass a block-only proof and
    # would be just as broken — it makes ordinary work impossible.
    root = project(PY_PROJECT)
    (root / ".claude" / "hooks" / "cerberus_gate.py").write_text(
        "import json, sys\n"
        "sys.stdin.read()\n"
        "print(json.dumps({'decision': 'block', 'reason': 'no'}))\n",
        encoding="utf-8",
    )
    rc, out = run_setup(root)
    assert rc != 0, "a gate that refuses everything was reported as working:\n" + out


def test_a_missing_mark_hook_is_not_reported_as_working():
    root = project(PY_PROJECT)
    (root / ".claude" / "hooks" / "cerberus_mark.py").unlink()
    rc, out = run_setup(root)
    assert rc != 0, "a missing hook was reported as working:\n" + out


def test_the_demonstration_requires_the_block_to_name_the_file():
    # M3's evidence row. A gate that refuses but cannot say what for is broken,
    # and a mutant dropping this check was invisible to the whole suite.
    # The fixture has to behave correctly in every other respect, or it fails
    # for the wrong reason: quiet when nothing is outstanding, blocking when
    # something is — and blocking with a reason that names nothing. A first
    # version blocked unconditionally and so was caught by the other test
    # instead, which made this one pass against a mutant that removed the
    # check it is named after.
    root = project(PY_PROJECT)
    (root / ".claude" / "hooks" / "cerberus_gate.py").write_text(
        "import json, os, pathlib, sys\n"
        "data = json.loads(sys.stdin.read() or '{}')\n"
        "root = pathlib.Path(os.environ.get('CLAUDE_PROJECT_DIR') or data.get('cwd') or '.')\n"
        "if (root / '.claude' / '.cerberus-pending').exists():\n"
        "    print(json.dumps({'decision': 'block', 'reason': 'something is unverified'}))\n",
        encoding="utf-8",
    )
    rc, out = run_setup(root)
    assert rc != 0, "a gate that cannot name what it blocked was reported as working:\n" + out


def test_the_demonstration_leaves_the_project_as_it_found_it():
    # M3's cleanup row. Setup runs while somebody is working: their pending
    # list must survive, and the probe must not be left behind.
    root = project(PY_PROJECT)
    marker = root / ".claude" / ".cerberus-pending"
    marker.write_text("src/payments.py\nsrc/ledger.py\n", encoding="utf-8")
    run_setup(root)
    assert marker.read_text(encoding="utf-8") == "src/payments.py\nsrc/ledger.py\n", (
        "the user's pending work was replaced by the probe"
    )
    leftovers = [p.name for p in (root / ".claude").glob("*probe*")]
    assert not leftovers, leftovers


def test_the_documented_one_liner_leaves_a_complete_configuration():
    """Run install.sh --claude --setup and assert the WHOLE resulting file.

    Three rounds of blockers shipped because each fix was checked against a
    fixture narrower than the artifact: a synthetic config instead of the
    shipped example, a path without a space, a test asserting only stage1. Each
    one would have failed here on the first run.
    """
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d) / "a project with a space"
        (root / "tests").mkdir(parents=True)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "d"\nversion = "1"\n', encoding="utf-8"
        )
        (root / "tests" / "test_demo.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )
        proc = subprocess.run(
            ["sh", str(ROOT / "install.sh"), "--claude", "--setup"],
            cwd=str(root), capture_output=True, text=True,
            env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        config = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
        v = config["verification"]

        assert v["stage1"], "no checks were written"
        assert not is_placeholder_text(v["stage1"]), v["stage1"]
        assert v["stage2"] == [], v["stage2"]
        assert v["artifact_kind"] == "library", (
            "the example ships artifact_kind 'service'; a Python library is not one"
        )
        assert not str(v["notes"]).startswith("Free text"), (
            "the example's own notes survived: " + str(v["notes"])
        )
        for key in REPLACING_KEYS:
            assert key not in config, key
        # and the closing advice must match the label in the file it points at
        assert "import it from there" in proc.stdout, proc.stdout


def is_placeholder_text(commands) -> bool:
    return all(str(c).startswith("echo ") for c in commands)


def test_the_example_markers_still_match_the_shipped_file():
    # The one decidable member of the existing-config population is identified
    # by two strings copied out of cerberus.example.json. If that file changes
    # and these do not, the installer's own copy stops being recognised and the
    # one-liner silently stops finishing. This is the drift guard.
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    example = json.loads((ROOT / "cerberus.example.json").read_text(encoding="utf-8"))
    assert cerberus_setup.EXAMPLE_MARKER_COMMENT == example["//"]
    assert cerberus_setup.EXAMPLE_MARKER_STAGE1 == example["verification"]["stage1"]


def test_an_existing_configuration_is_never_modified():
    # Whatever is in it. Three rounds tried to tell "the user chose this" from
    # "the installer wrote it" and each proxy destroyed somebody's work, so the
    # question is no longer asked of anything but the installer's exact copy.
    original = {
        "verification": {
            "artifact_kind": "migration",
            "stage1": [],
            "stage2": [],
            "notes": "Prod creds in vault/eu-prod. NEVER run stage2 against eu.",
        }
    }
    root = project({**PY_PROJECT, ".claude/cerberus.json": json.dumps(original)})
    run_setup(root)
    after = json.loads((root / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    assert after == original, after


def test_a_timed_out_check_is_never_written():
    # Round two hardened run() and nothing asserted any of it: a mutant that
    # counted 124 as success wrote a hanging command into the config and
    # printed "ok" and "too slow" about it in adjacent lines.
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    runner = {"name": "Synthetic", "files": [], "checks": [("sleep 30", None)], "fallback": None}
    with tempfile.TemporaryDirectory() as d:
        original = cerberus_setup.run
        cerberus_setup.run = lambda cmd, cwd, timeout=1: original(cmd, cwd, timeout=1)
        try:
            results = cerberus_setup.build_checks([runner], pathlib.Path(d))
        finally:
            cerberus_setup.run = original
    assert results and results[0][1] == 124, results


def test_only_a_passing_check_is_ever_written():
    # The rule the config depends on, at the function. A timeout, a missing
    # command and a failure are each their own outcome and none of them is
    # writable — a mutant treating 124 as success wrote a hanging command into
    # stage1 and nothing noticed.
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    results = [("green", 0, ""), ("slow", 124, "timed out"), ("gone", 127, ""), ("red", 1, "boom")]
    passing, missing, timed_out, broken = cerberus_setup.sort_results(results)
    assert passing == ["green"], passing
    assert missing == ["gone"] and timed_out == ["slow"], (missing, timed_out)
    assert [c for c, _ in broken] == ["red"], broken


def test_a_check_never_inherits_stdin():
    # Under `curl … | sh` the parent's stdin is the install script itself, and a
    # check that reads it blocked for its whole budget.
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    read, write = os.pipe()
    try:
        proc = subprocess.run(
            [sys.executable, "-c",
             "import sys, pathlib; sys.path.insert(0, %r); import cerberus_setup as c;"
             "print(c.run('read x', pathlib.Path('.'), timeout=8)[0])" % str(HOOKS)],
            stdin=read, capture_output=True, text=True, timeout=30,
        )
    finally:
        os.close(read)
        os.close(write)
    # The point is that it returns at once rather than blocking for its whole
    # budget; `read` with no input exits non-zero, which is fine.
    assert proc.stdout.strip() != "124", proc.stdout + proc.stderr


def test_a_timed_out_check_does_not_leave_the_tree_running():
    sys.path.insert(0, str(HOOKS))
    import cerberus_setup

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        stamp = root / "still-running"
        code, _ = cerberus_setup.run(
            f"(sleep 4; touch {stamp}) & sleep 30", root, timeout=1
        )
    assert code == 124, code
    import time

    time.sleep(5)
    assert not stamp.exists(), "the process group outlived the timeout"


# ------------------------------------------------------- what the user reads


def test_the_output_uses_no_internal_vocabulary():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    found = jargon_in(out)
    assert not found, f"{found} means nothing to the reader:\n{out}"


def test_the_refusal_message_is_also_plain():
    # The user meets this text at the moment they are blocked, which is the
    # least forgiving moment for vocabulary.
    root = project({"notes.txt": "hi\n"})
    _, out = run_setup(root)
    found = jargon_in(out)
    assert not found, f"{found} in the refusal:\n{out}"


def test_the_output_fits_one_screen():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    lines = [line for line in out.splitlines() if line.strip()]
    assert len(lines) <= 25, f"{len(lines)} lines is a wall of text:\n{out}"


def test_the_closing_message_says_the_three_things():
    root = project(PY_PROJECT)
    _, out = run_setup(root)
    assert "Set up for this" in out, "what changed"
    assert "refused until" in out, "what happens next time"
    assert "switch it off" in out, "how to turn it off"


def test_questions_come_with_concrete_options():
    # A refusal must ask for specific things, not "describe your project".
    root = project({"notes.txt": "hi\n"})
    _, out = run_setup(root)
    assert "1." in out and "2." in out, "the questions must be enumerable: " + out
    # No assertion about question marks: an earlier one failed on output that
    # satisfied the requirement *better* — offering options with a question and
    # a default — which made it an accident rather than a property.


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ok   {name}")
            except AssertionError as exc:
                failures += 1
                print(f"  FAIL {name}: {exc}")
    print(f"\n{'FAILED' if failures else 'all tests passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
