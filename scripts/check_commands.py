#!/usr/bin/env python3
"""Check the slash commands in .claude/commands/.

These two files drive the working cycle and, until #4, had no automated check
of any kind: check_parity.py globs plugins/*/skills/*, CI had no step for the
directory, and `claude plugin validate` accepts frontmatter that is known
broken. That gap is how #1 happened — `$1` used for the first argument, in the
repository's own entry-point command, passing every check the project had.

What this checks, and why each rule earns its place:

1. **Positional placeholders are in range.** `$N` is zero-indexed: `$0` is the
   first argument, `$1` the second. A command declaring one argument and
   writing `$1` binds nothing. The visible form is harmless — the placeholder
   stays literal and the harness appends an `ARGUMENTS:` line an agent can
   recover from. The silent form is not: with `/work 12 rebased`, `$1` binds
   `rebased` and step 1 becomes `gh issue view rebased`, with no literal left
   to notice.

   The rule is deliberately *arity-aware* rather than "forbid `$1`". A command
   that genuinely takes two arguments is correct to use `$1`, and a blanket ban
   would be a rule tightened without the incentive changing — formal compliance,
   not the behaviour.

   Its limit, stated rather than hidden: **arity is a property of the
   invocation, not of the file.** `$N` binds to whatever the user typed, so no
   file-local fact makes `$1` provably wrong. `arguments:` names positions and
   `argument-hint` is autocomplete decoration; both are self-certified, and
   padding the hint silences this rule. It is a lint over the declaration an
   author wrote, and it catches the case that actually shipped.

2. **Declared arguments are used.** `arguments: [issue]` with no `$issue` in the
   body is a declaration that does nothing, which is how a rename half-lands.

3. **Frontmatter parses and is delimited.** `claude plugin validate` does not
   check this; measured before eeec1d9.

4. **Backticked repository paths exist.** Both commands send the reader to
   `plugins/gopnik/skills/*/SKILL.md`; a move that misses them turns a step
   into a dead end.

5. **Named placeholders are declared.** An undeclared `$name` expands to an
   **empty string**, so `Closes #$isue` ships as `Closes #` with nothing to
   notice — #1's silent form, in the line that closes the issue. This was
   skipped in the first round on the grounds that `$CLAUDE_PROJECT_DIR` in an
   example is indistinguishable from a typo. It is distinguishable: argument
   names are lowercase and shell variables are conventionally upper-case, and
   the rule only fires when `arguments:` is present.

Run: python3 scripts/check_commands.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
COMMANDS = ROOT / ".claude" / "commands"

# A backticked token is treated as a repository path when it has a directory
# separator and a known extension. Anything looser starts flagging prose.
#
# URLs and globs are excluded deliberately: both used to be flagged, and the
# glob case was absurd — the rule rejected the very example its own docstring
# uses to describe it.
PATH_LIKE = re.compile(r"`([^`\s]*/[^`\s]*\.(?:md|py|json|ya?ml|sh))`")
NOT_A_REPO_PATH = re.compile(r"^[a-z][a-z0-9+.-]*://|^~|[*?\[]")
POSITIONAL = re.compile(r"\$(\d+)(?!\w)")
# Argument names are lowercase; shell variables are conventionally upper-case,
# which is what makes the two separable after all.
NAMED = re.compile(r"\$([a-z][a-z0-9_]*)\b")
HINT_TOKEN = re.compile(r"<[^>]+>|\[[^\]]+\]")


def parse_frontmatter(text: str, problems: list[str], name: str) -> dict[str, str] | None:
    """Return the frontmatter as raw strings, or None after recording a problem.

    None and {} are different answers and conflating them switched every
    remaining check off: a file whose frontmatter was well formed but empty
    returned {}, which read as "there was a problem, stop" while no problem had
    been recorded, so it passed with nothing checked at all.

    A deliberately small parser rather than PyYAML: this has to run in the same
    job as the hook tests, which install nothing.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        problems.append(f"{name}: no frontmatter — the file must open with ---")
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        problems.append(f"{name}: frontmatter is never closed with ---")
        return None

    data: dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            problems.append(f"{name}: frontmatter line is not `key: value` — {raw!r}")
            continue
        key, _, value = raw.partition(":")
        data[key.strip()] = value.strip()
    return data


def declared_arguments(front: dict[str, str]) -> list[str]:
    """The argument names this command takes, in order.

    `arguments: [issue]` names them. Failing that, the arity is read off
    `argument-hint`, where each <group> or [group] is one argument — that is the
    only signal a command without an `arguments:` key gives.
    """
    raw = front.get("arguments")
    if raw:
        inner = raw.strip()
        if inner.startswith("[") and inner.endswith("]"):
            inner = inner[1:-1]
        return [n.strip() for n in inner.split(",") if n.strip()]
    hint = front.get("argument-hint")
    if hint:
        return [f"<{i}>" for i, _ in enumerate(HINT_TOKEN.findall(hint))]
    return []


def check(path: pathlib.Path, problems: list[str], root: pathlib.Path = ROOT) -> None:
    try:
        name = path.relative_to(root)
    except ValueError:
        name = path.name
    text = path.read_text(encoding="utf-8")
    front = parse_frontmatter(text, problems, str(name))
    if front is None:
        return

    body = text.split("---", 2)[-1]
    args = declared_arguments(front)

    for index in {int(m) for m in POSITIONAL.findall(body)}:
        if index >= len(args):
            plural = "argument" if len(args) == 1 else "arguments"
            problems.append(
                f"{name}: `${index}` but the command declares {len(args)} {plural}. "
                f"$N is zero-indexed: the first argument is `$0`"
                + (f", i.e. `${{{args[0]}}}` here" if args and not args[0].startswith("<") else "")
            )

    for arg in args:
        if arg.startswith("<"):
            continue  # inferred from argument-hint; it has no name to look for
        if f"${arg}" not in body:
            problems.append(f"{name}: declares argument {arg!r} and never uses `${arg}`")

    if args:
        declared = {a for a in args if not a.startswith("<")}
        if declared:
            for placeholder in sorted(set(NAMED.findall(body)) - declared):
                problems.append(
                    f"{name}: `${placeholder}` is not in `arguments:` {sorted(declared)}. "
                    f"An undeclared named placeholder expands to an empty string, "
                    f"so a typo ships silently"
                )

    for ref in PATH_LIKE.findall(body):
        if NOT_A_REPO_PATH.search(ref):
            continue  # a URL, a glob or a home path — not a reference into this tree
        if not (root / ref).exists():
            problems.append(f"{name}: references `{ref}`, which does not exist")


def main(argv: list[str] | None = None) -> int:
    # The directory and the root are arguments so the tests can run this
    # against fixtures. A checker with no test of its own would be one more
    # thing nobody verified.
    argv = sys.argv[1:] if argv is None else argv
    commands = pathlib.Path(argv[0]) if argv else COMMANDS
    root = pathlib.Path(argv[1]) if len(argv) > 1 else ROOT

    if not commands.is_dir():
        print(f"no commands directory at {commands}", file=sys.stderr)
        return 1

    files = sorted(commands.glob("*.md"))
    if not files:
        # An empty glob passing silently is how check_parity.py's own step went
        # green while compiling nothing.
        print(f"no command files found in {commands}", file=sys.stderr)
        return 1

    problems: list[str] = []
    for path in files:
        check(path, problems, root)

    if problems:
        print("\n".join("- " + p for p in problems), file=sys.stderr)
        return 1

    for path in files:
        print(f"commands ok: {path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
