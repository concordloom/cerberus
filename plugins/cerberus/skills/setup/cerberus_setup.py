#!/usr/bin/env python3
"""Work out this project's checks by running them, and write them down.

Run it from the project root:

    python3 cerberus_setup.py           # find the checks, run them, save them
    python3 cerberus_setup.py --check   # run them and print them, write nothing

Why it exists: the skills need to know two things this repository cannot know —
the commands that check this project, and where the change stops being under
your control once it ships. Guessing either is worse than asking, so this runs
the candidates here and writes down only what actually passed.

Three rules, in order of how much damage breaking them does:

1. **Every command it writes has been run first**, and its exit status is shown.
   A check nobody executed is a placeholder with better wording.
2. **It refuses rather than guesses.** A project it cannot recognise gets an
   honest "I could not tell", not a plausible config. A wrong config is worse
   than the placeholder it replaced: the placeholder is visibly unfinished.
3. **It never removes what it did not write.** A hand-tuned `verification`
   block is merged into, not replaced — including keys this script would never
   produce on its own.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

# Ordered: the first entry whose marker file is present wins for naming the
# project, but every match contributes its checks.
RUNNERS = [
    {
        "name": "Python",
        "files": ["pyproject.toml", "setup.py", "setup.cfg", "tox.ini"],
        "checks": [
            ("pytest -q", ["tests", "test"]),
            ("ruff check .", [".ruff.toml", "ruff.toml"]),
        ],
        "fallback": "python3 -m compileall -q .",
    },
    {
        "name": "Node",
        "files": ["package.json"],
        "checks": [("npm test --silent", None), ("npm run lint --silent", None)],
        "fallback": None,
    },
    {
        "name": "Rust",
        "files": ["Cargo.toml"],
        "checks": [("cargo test --quiet", None), ("cargo clippy --quiet", None)],
        "fallback": "cargo build --quiet",
    },
    {
        "name": "Go",
        "files": ["go.mod"],
        "checks": [("go test ./...", None), ("go vet ./...", None)],
        "fallback": "go build ./...",
    },
]

# What the project ships decides where the last check has to happen. Ordered by
# how specific the signal is.
KIND_SIGNALS = [
    ("chart", ["Chart.yaml", "charts", "main.tf"]),
    ("service", ["Dockerfile", "docker-compose.yml", "k8s", "deploy"]),
    ("cli", []),  # decided from the manifests below, not from a path
    ("library", []),
]

#: Where the configuration is looked for, in order. The first two are where
#: earlier versions put it; new projects get the third, which belongs to no
#: agent in particular — the file is read by whoever is working, not by a hook.
CONFIG_PATHS = (".claude/cerberus.json", ".codex/cerberus.json", "cerberus.json")

# The installer's own copy of cerberus.example.json, identified by the two
# strings it ships. This is the only existing configuration that can be
# rewritten without guessing whether a human chose its values — everything else
# is left alone, because `cerberus.json` records no distinction between "the
# user set this" and "the installer did", and three rounds of proxies for that
# distinction each produced a defect.
#
# tests/test_setup.py asserts these still match the shipped example.
EXAMPLE_MARKER_COMMENT = 'Copy to cerberus.json in your project root. Safe to use as-is: the only key set is the one with no sensible default, and the checks below are placeholders until setup runs.'
EXAMPLE_MARKER_STAGE1 = ["echo 'replace with this project: tests, lint, type check'"]


STAGE2_HINT_BY_KIND = {
    "service": "run it where it actually runs and drive one real request through it",
    "library": "build the package, install it somewhere empty, and import it from there",
    "cli": "install the built command somewhere clean and run it with real arguments",
    "chart": "apply it to a real cluster or account and watch it settle",
    "plugin": "install it into a clean environment and load it there",
    "migration": "run it against a copy of real shape and scale",
    "model-boundary": "make a real model call through the production entry point",
}


def run(cmd: str, cwd: pathlib.Path, timeout: int = 120) -> tuple[int, str]:
    """Run one candidate check.

    stdin is closed rather than inherited: under `curl … | sh` the parent's
    stdin is the pipe carrying the install script, and a check that reads from
    it would block for its whole budget. The process group is killed on
    timeout, because killing the shell leaves anything it forked behind.
    """
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(cwd),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
    except Exception as exc:  # a missing shell is not this script's problem to solve
        return 127, str(exc)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return proc.returncode, (out or "").strip()
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), 9)
        except Exception:
            proc.kill()
        # With its own timeout: a grandchild that left the process group keeps
        # the pipe open, and an unbounded wait here turns the budget into
        # forever — the exact hang the timeout exists to prevent.
        try:
            proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return 124, "timed out"


def detect(root: pathlib.Path) -> tuple[list[dict], str | None]:
    """Which toolchains are here, and what does this project ship?"""
    found = [r for r in RUNNERS if any((root / f).exists() for f in r["files"])]

    kind = None
    for candidate, signals in KIND_SIGNALS:
        if signals and any((root / s).exists() for s in signals):
            kind = candidate
            break

    if kind is None and found:
        kind = "cli" if _looks_like_a_command(root) else "library"
    return found, kind


def _looks_like_a_command(root: pathlib.Path) -> bool:
    pkg = root / "package.json"
    if pkg.exists():
        try:
            if json.loads(pkg.read_text(encoding="utf-8")).get("bin"):
                return True
        except Exception:
            pass
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        try:
            if "[project.scripts]" in pyproject.read_text(encoding="utf-8"):
                return True
        except Exception:
            pass
    return False


def build_checks(runners: list[dict], root: pathlib.Path) -> list[tuple[str, int, str]]:
    """Run every candidate check and report how each one went.

    Nothing reaches the config without having been executed here first, and the
    three ways a check can not-pass are kept apart: it is missing here, it timed
    out, or it ran and failed. Collapsing them into one sentence let a failing
    test suite be reported as one that never ran.
    """
    results = []
    for runner in runners:
        ran_one = False
        for cmd, needs in runner["checks"]:
            if needs and not any((root / n).exists() for n in needs):
                continue
            code, out = run(cmd, root)
            results.append((cmd, code, out))
            ran_one = ran_one or code == 0
        if not ran_one and runner["fallback"]:
            code, out = run(runner["fallback"], root)
            results.append((runner["fallback"], code, out))
    return results


def sort_results(results: list) -> tuple[list, list, list, list]:
    """Split check results into what may be written and what may not.

    A function rather than four comprehensions inside main, because the rule —
    only exit 0 is written — was untestable from outside and a mutant counting
    a timeout as success wrote a hanging command into the config while printing
    "ok" and "too slow" about it in adjacent lines.
    """
    passing = [cmd for cmd, code, _ in results if code == 0]
    missing = [cmd for cmd, code, _ in results if code == 127]
    timed_out = [cmd for cmd, code, _ in results if code == 124]
    broken = [(cmd, out) for cmd, code, out in results if code not in (0, 124, 127)]
    return passing, missing, timed_out, broken


def resolve_config(root: pathlib.Path) -> pathlib.Path:
    """Where this project's configuration is, or should go.

    Whichever exists wins, in CONFIG_PATHS order, so an install from an earlier
    version keeps its file where it is. A project with none of them gets one in
    the root: nothing reads it but the person or agent doing the work, so it
    belongs to the project rather than to an agent's directory.
    """
    for relative in CONFIG_PATHS:
        if (root / relative).exists():
            return root / relative
    return root / "cerberus.json"


def is_the_installers_copy(existing: dict) -> bool:
    """Is this file still exactly what install.sh put there?

    A fact about bytes, not an inference about intent. Every previous attempt to
    tell "the user chose this" from "the installer wrote it" was a proxy — a key
    inventory, then a key-name allowlist, then a flag that was never computed —
    and each one destroyed somebody's configuration in a different way. The
    distinction is not recorded in the file, so only the exactly-known case is
    claimed and everything else is left untouched.
    """
    return (
        str(existing.get("//") or "") == EXAMPLE_MARKER_COMMENT
        and existing.get("verification", {}).get("stage1") == EXAMPLE_MARKER_STAGE1
    )


def write_config(
    root: pathlib.Path,
    kind: str,
    checks: list[str],
    dry: bool,
    existing: dict | None = None,
) -> pathlib.Path:
    """Merge into whatever is there rather than replacing it.

    Replacing the whole document is how a hand-tuned configuration got deleted:
    the keys this script must never write are also keys it must never remove.
    """
    path = resolve_config(root)
    body = dict(existing) if isinstance(existing, dict) else {}
    body["//"] = "Every command in stage1 was run once, in this project, before being written here."
    prior = body.get("verification")
    verification = dict(prior) if isinstance(prior, dict) else {}
    # The rule that top-level keys are not to be removed applies one level down
    # too, and did not: a deliberate `migration` — a kind detect() can never
    # produce — was downgraded to a guess, and notes naming production accounts
    # were destroyed without a word.
    # Reached only for an absent config or the installer's own copy, so these
    # are never anybody's choice.
    verification["artifact_kind"] = kind
    verification["stage1"] = checks
    # Left empty on purpose: a comment line in a list of commands exits 0
    # unconditionally, which is the placeholder this script exists to remove.
    verification["stage2"] = []
    verification["notes"] = (
        "stage2 is still empty. Put here what proves it works where it really runs: "
        + STAGE2_HINT_BY_KIND.get(
            verification["artifact_kind"], STAGE2_HINT_BY_KIND["library"]
        )
        + "."
    )
    body["verification"] = verification
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def report_state(root: pathlib.Path, kind: str = "library", first_run: bool = True) -> int:
    """Say what is still missing, and — the first time only — how to use this.

    Split by run rather than shared, because the two readers are different
    people. Someone who has just installed a thing called a verification gate
    reasonably expects something to start happening, and has to be told nothing
    will. Someone running it a second time already knows, and printing it again
    directly under "nothing was changed" left the only paragraph with content
    followed by one with none.
    """
    config = resolve_config(root)
    where = config.relative_to(root) if config.is_relative_to(root) else config

    if first_run:
        print()
        print("Nothing here runs by itself. The skills are yours to invoke by name —")
        print("ask for the cerberus skill before saying a change works, and it will")
        print(f"read the checks from {where} and run them.")
    try:
        stage2 = json.loads(config.read_text(encoding="utf-8"))["verification"]["stage2"]
    except Exception:
        stage2 = []
    if not stage2:
        print()
        print("One thing is still missing: the last check, the one that runs where")
        print(f"this really ships. Put it in {where} —")
        print(f"{STAGE2_HINT_BY_KIND.get(kind, STAGE2_HINT_BY_KIND['library'])}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the checks and print them, but write no configuration",
    )
    parser.add_argument("--dir", default=".", help="project directory")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.dir).resolve()
    config = resolve_config(root)

    runners, kind = detect(root)

    existing = None
    if config.exists():
        try:
            existing = json.loads(config.read_text(encoding="utf-8"))
        except Exception:
            print(f"{config} exists but is not valid JSON. Fix or delete it, then run this again.")
            return 2
        if not isinstance(existing, dict):
            print(f"{config} is valid JSON but not an object. Fix or delete it, then run this again.")
            return 2
        verification = existing.get("verification")
        if verification is not None and not isinstance(verification, dict):
            print(f"{config} has a 'verification' that is not an object. Fix it, then run this again.")
            return 2
        verification = verification or {}

        if not is_the_installers_copy(existing):
            # Never modified. Its checks are run and reported, the ones found
            # here are printed beside them, and the user decides.
            print("This project already has its own configuration, so nothing was")
            print("changed. Here is how it stands.")
            print()
            listed = verification.get("stage1") or []
            still_failing = not listed
            if listed:
                print("Checks it lists:")
                for cmd in listed:
                    code, out = run(str(cmd), root)
                    if code == 0:
                        print(f"  ok       {cmd}")
                    else:
                        first = out.splitlines()[0][:50] if out else "no output"
                        label = "absent  " if code == 127 else "too slow" if code == 124 else "FAILING "
                        print(f"  {label} {cmd} — {first}")
                        still_failing = True
            else:
                print("It lists no checks at all, so there is nothing to run before a")
                print("claim that the work is done.")
            if runners:
                # Only what the configuration does not already have. Offering a
                # project a check it already lists reads as a suggestion, costs
                # a second run of the command, and on a project with one check
                # printed that check twice under two different headings.
                already = {str(c) for c in listed}
                found = [c for c, code, _ in build_checks(runners, root)
                         if code == 0 and c not in already]
                if found:
                    print()
                    print("Checks I found here that it does not list, and ran:")
                    for cmd in found:
                        print(f"  ok       {cmd}")
            return report_state(root, verification.get("artifact_kind") or kind or "library",
                                first_run=False)

    # Only now, because a project this cannot recognise may already be
    # configured by hand — and those are exactly the projects that most need
    # the answer, since detection is why they are hand-configured.
    if not runners or kind is None:
        print("I could not tell what kind of project this is.")
        print("Nothing was changed. Tell me two things and I can finish:")
        print("  1. the command that runs your tests")
        print("  2. how someone else gets this — a running service, an installed")
        print("     package, a command they type")
        return 2

    results = build_checks(runners, root)
    passing, missing, timed_out, broken = sort_results(results)

    if not passing:
        print(f"I found a {runners[0]['name']} project but none of its checks pass here.")
        for cmd, out in broken[:3]:
            first = out.splitlines()[0][:60] if out else "no output"
            print(f"  {cmd} — failed: {first}")
        for cmd in missing[:3]:
            print(f"  {cmd} — not installed here")
        print("Nothing was changed. Fix one of those, or tell me the right command.")
        return 2

    written = write_config(root, kind, passing, args.check, existing)

    if len(runners) > 1:
        others = ", ".join(r["name"] for r in runners[1:])
        print(f"This project uses several toolchains: {runners[0]['name']}, {others}.")
        print(f"I took it as a {runners[0]['name']} {kind} — change that if it is wrong.")
    else:
        print(f"Set up for this {runners[0]['name']} project.")
        print(f"I took it as a {kind} — change that if it is wrong.")
    print()
    print("Checks I ran here, and that the skill will run before anyone says the")
    print("work is done:")
    for cmd in passing:
        print(f"  ok       {cmd}")
    for cmd, _ in broken:
        print(f"  FAILING  {cmd} — it ran and did not pass, so it was left out")
    for cmd in missing:
        print(f"  absent   {cmd} — not installed here, so it was left out")
    for cmd in timed_out:
        print(f"  too slow {cmd} — gave up waiting, so it was left out")
    if broken:
        # Beside the FAILING line it refers to, not below the advice. It was
        # the fourth thing the reader reached, under a paragraph about how to
        # invoke a skill — the most urgent sentence in the output, buried.
        print("Your own tests are failing right now — that is worth a look first.")

    if args.check:
        print()
        print(f"Nothing was written. Drop --check to save this to {written}.")
        return 0

    return report_state(root, kind, first_run=True)


if __name__ == "__main__":
    sys.exit(main())
