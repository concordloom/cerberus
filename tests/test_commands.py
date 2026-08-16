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
import re
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


def test_catches_an_undeclared_named_placeholder():
    # The silent one. An undeclared name expands to an empty string, so this
    # ships `Closes #` with nothing to notice — #1's failure mode in the line
    # that closes the issue. The first round of the checker waved it through.
    rc, out = run({"work.md": command(
        "description: work an issue\narguments: [issue]",
        "1. Read it: `gh issue view $issue --comments`.\n2. `Closes #$isue`",
    )})
    assert rc == 1, out
    assert "$isue" in out and "empty string" in out, out


def test_catches_a_frontmatter_line_that_is_not_key_value():
    # Discriminates the `":" not in raw` branch, which no test exercised: a
    # mutant deleting it passed the whole suite.
    rc, out = run({"c.md": "---\ndescription: x\nthis line has no colon\n---\n\nbody\n"})
    assert rc == 1, out
    assert "not `key: value`" in out, out


def test_catches_a_missing_path_outside_plugins():
    # Discriminates a mutant that only existence-checked paths under plugins/.
    rc, out = run({"c.md": command("description: x", "Read `nope/gone.py` first.")})
    assert rc == 1, out
    assert "nope/gone.py" in out, out


def test_counts_every_group_in_the_argument_hint():
    # Discriminates a mutant that hard-coded arity 1 instead of counting.
    rc, out = run({"c.md": command(
        "description: x\nargument-hint: <a> <b> <c>",
        "$0 $1 $2 are fine but $3 is not",
    )})
    assert rc == 1, out
    assert "`$3`" in out and "3 arguments" in out, out


def test_an_empty_frontmatter_block_does_not_switch_the_checks_off():
    # A well-formed but empty block used to return {}, which read as "there was
    # a problem, stop" while no problem had been recorded — so every remaining
    # check was skipped and the file passed with three defects in it.
    rc, out = run({"c.md": "---\n---\n\nTake **$1** and read `nope/gone.py`.\n"})
    assert rc == 1, out
    assert "`$1`" in out and "nope/gone.py" in out, out


# -------------------------------------------------------- must stay green


def test_a_positional_followed_by_a_word_character_is_not_a_placeholder():
    # Discriminates the (?!\w) guard, which no test exercised. `$1abc` is not
    # positional 1, and a mutant dropping the guard flagged it.
    rc, out = run({"c.md": command("description: x", "The literal $1abc is not an argument.")})
    assert rc == 0, out


def test_urls_and_globs_are_not_treated_as_repository_paths():
    # Both used to be flagged. The glob case rejected the very example the
    # checker's own docstring uses to describe the rule.
    rc, out = run({"c.md": command(
        "description: x",
        "See `https://example.com/docs/guide.md` and `plugins/*/skills/*/SKILL.md`.",
    )})
    assert rc == 0, out


def test_an_uppercase_shell_variable_is_not_an_argument_name():
    rc, out = run({"c.md": command(
        "description: x\narguments: [issue]",
        "Run `python3 \"$CLAUDE_PROJECT_DIR\"/hook.py` for issue $issue.",
    )})
    assert rc == 0, out


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


def test_no_command_declares_a_tool_its_steps_never_use():
    """#6, the half that is settled whichever way the field works.

    `issue.md` declared `gh issue view` and `gh label list`; neither appeared in
    its steps. Under every reading of `allowed-tools` — grant, decoration, or
    the restriction it demonstrably is not — declaring something unused is
    either a pointless pre-approval or a lie about what the command does.
    """
    for path in sorted((ROOT / ".claude" / "commands").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        head, body = text.split("---", 2)[1], text.split("---", 2)[2]
        line = re.search(r"^allowed-tools:.*$", head, re.M)
        if not line:
            continue
        declared = re.findall(r"Bash\(([a-z][^:)]*)", line.group(0))
        unused = [d.strip() for d in declared if d.strip() not in body]
        assert not unused, f"{path.name}: declares but never uses {unused}"


def test_a_command_that_spawns_an_adversary_declares_the_tool_for_it():
    """#6, the other half. `work.md` step 4 requires an adversary and declared no Agent.

    Safe under both open readings: if the field grants, this is required; if it
    is decoration, it costs nothing. What is not safe is a command whose steps
    need a tool its own header does not mention.
    """
    for path in sorted((ROOT / ".claude" / "commands").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        head, body = text.split("---", 2)[1], text.split("---", 2)[2]
        if not re.search(r"adversary|spawn", body, re.I):
            continue
        assert re.search(r"^allowed-tools:.*\bAgent\b", head, re.M), (
            f"{path.name}: its steps require spawning an adversary, and Agent is not declared")


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
            except Exception as exc:
                # Not just AssertionError: a test that raises anything else
                # used to crash the whole run, so the remaining tests never
                # executed and the report was a traceback rather than a list of
                # failures. One broken test must not hide the others.
                failures += 1
                print(f"  ERROR {name}: {type(exc).__name__}: {exc}")
    print(f"\n{'FAILED' if failures else 'all tests passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
