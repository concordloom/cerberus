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
    "topology", "semantics", "verdict",
]


def jargon_in(text: str) -> list[str]:
    flat = re.sub(r"[-_/]+", " ", text.lower())
    flat = re.sub(r"\s+", " ", flat)
    return [w for w in JARGON if re.search(r"\b" + re.escape(w) + r"\b", flat)]

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
    root = project(PY_PROJECT)
    run_setup(root)
    raw = (root / ".claude" / "cerberus.json").read_text(encoding="utf-8")
    for key in REPLACING_KEYS:
        assert key not in raw, f"{key} must never be written by a machine"


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
    assert "nothing is calling it" in out, out


def test_a_plugin_install_is_recognised_as_wired():
    # Hooks come from the plugin's own hooks.json and the project's settings
    # never name them. The grep version told correctly-installed users that
    # nothing was calling it, and exited 1 — on the install path the README
    # puts first.
    root = project(PY_PROJECT, wired=False)
    hooks_json = HOOKS / "hooks.json"
    if not hooks_json.exists():
        return
    (root / ".claude" / "hooks" / "hooks.json").write_text(
        hooks_json.read_text(encoding="utf-8"), encoding="utf-8"
    )
    rc, out = run_setup(root)
    assert rc == 0, "a plugin install was told it is not wired:\n" + out


def test_says_so_when_nothing_is_calling_it():
    # Scripts installed, settings not naming them: the state that looks
    # installed and guards nothing.
    root = project(PY_PROJECT, wired=False)
    rc, out = run_setup(root)
    assert rc == 1, out
    assert "nothing is calling it" in out, out


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


def test_a_failing_suite_is_called_failing_not_missing():
    # It ran and did not pass. Reporting that as "did not run here" is false,
    # and it is the difference between a project with a broken suite and a
    # project without the tool installed.
    root = project({**PY_PROJECT, "tests/test_demo.py": "def test_bad():\n    assert False\n"})
    rc, out = run_setup(root)
    assert "FAILING" in out, out
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
    # The population #13 exists for: a file is present, and it is the example.
    root = project({**PY_PROJECT, ".claude/cerberus.json": json.dumps(
        {"verification": {"artifact_kind": "service", "stage1": ["echo 'replace me'"]}}
    )})
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
