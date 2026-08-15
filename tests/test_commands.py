#!/usr/bin/env python3
"""Tests for scripts/check_commands.py.

The checker exists because `.claude/commands/` had no check at all and a
zero-indexing bug survived there (#1, #4). A checker with no test of its own
would reproduce the same shape one level up.

Both directions are asserted, and the must-stay-green cases carry as much
weight as the must-catch ones: the naive version of this rule — "forbid `$1`" —
catches #1 and breaks any command that genuinely takes two arguments.

Run with: python3 tests/test_commands.py
"""

from __future__ import annotations

import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "check_commands.py"


def run(files: dict[str, str], root: pathlib.Path | None = None) -> tuple[int, str]:
    """Write the given command files to a fixture directory and check them."""
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        commands = tmp / ".claude" / "commands"
        commands.mkdir(parents=True)
        for name, text in files.items():
            (commands / name).write_text(text, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(CHECKER), str(commands), str(root or tmp)],
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout + proc.stderr


def command(front: str, body: str) -> str:
    return f"---\n{front}\n---\n\n{body}\n"


# ------------------------------------------------------- must be caught


def test_catches_the_issue_1_defect():
    # Verbatim shape of what shipped: one declared argument, `$1` in the body.
    rc, out = run({"work.md": command(
        "description: work an issue\nargument-hint: <issue number>",
        "Take issue **$1** and run `gh issue view $1 --comments`.",
    )})
    assert rc == 1, out
    assert "$1" in out and "zero-indexed" in out, out


def test_catches_an_index_past_the_declared_arguments():
    rc, out = run({"c.md": command(
        "description: two\narguments: [a, b]",
        "$a $b and then $2",
    )})
    assert rc == 1, out
    assert "`$2`" in out, out


def test_catches_a_declared_argument_that_is_never_used():
    rc, out = run({"c.md": command(
        "description: x\narguments: [issue]",
        "Work the issue. No placeholder anywhere.",
    )})
    assert rc == 1, out
    assert "never uses" in out, out


def test_catches_unclosed_frontmatter():
    rc, out = run({"c.md": "---\ndescription: x\n\nbody without a closing fence\n"})
    assert rc == 1, out
    assert "never closed" in out, out


def test_catches_a_missing_frontmatter():
    rc, out = run({"c.md": "Just a body.\n"})
    assert rc == 1, out
    assert "no frontmatter" in out, out


def test_catches_a_reference_to_a_file_that_does_not_exist():
    rc, out = run({"c.md": command(
        "description: x",
        "Read `plugins/cerberus/skills/ghost/SKILL.md` before starting.",
    )})
    assert rc == 1, out
    assert "does not exist" in out, out


def test_an_empty_commands_directory_is_a_failure_not_a_pass():
    # check_parity.py's compile step once went green while compiling nothing.
    rc, out = run({})
    assert rc == 1, out
    assert "no command files" in out, out


# -------------------------------------------------------- must stay green


def test_zero_is_the_first_argument():
    rc, out = run({"c.md": command(
        "description: x\nargument-hint: <issue number>",
        "Take issue **$0**.",
    )})
    assert rc == 0, out


def test_positional_one_is_correct_when_two_arguments_are_declared():
    # The trap. A blanket "forbid $1" rule would fail here, and this command is
    # correct.
    rc, out = run({"c.md": command(
        "description: x\narguments: [first, second]",
        "$first is $0 and $second is $1.",
    )})
    assert rc == 0, out


def test_a_command_with_no_placeholder_at_all_is_fine():
    # issue.md's shape: it takes free text and relies on the harness appending
    # an `ARGUMENTS:` line, which was measured working.
    rc, out = run({"issue.md": command(
        "description: x\nargument-hint: [what the discussion was about, optional]",
        "Turn the discussion into an issue.",
    )})
    assert rc == 0, out


def test_arguments_placeholder_is_not_a_positional():
    rc, out = run({"c.md": command("description: x", "All of it: $ARGUMENTS")})
    assert rc == 0, out


def test_the_real_commands_pass():
    proc = subprocess.run([sys.executable, str(CHECKER)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


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
