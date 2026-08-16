#!/usr/bin/env python3
"""Set a project up, and prove the gate fires before saying so.

Not a hook. It lives beside them because ``install.sh`` copies
``hooks/*.py`` into a project, so this is the one directory that reaches every
installation without a second delivery path.

Run it from the project root:

    python3 .claude/hooks/cerberus_setup.py           # set up, then demonstrate
    python3 .claude/hooks/cerberus_setup.py --check   # run the checks, write nothing

Why it exists: ``install.sh`` copies an example config whose checks are
``echo`` placeholders. The blocking half of the gate then works — a readiness
claim is refused — while the checks it tells you to run pass unconditionally.
Armed and verifying nothing is a worse state than not installed, because it
looks finished.

Three rules this follows, in order of how much damage breaking them does:

1. **It never writes the keys that replace defaults.** ``claim_patterns``,
   ``ignore_patterns``, ``source_extensions`` and ``watch_paths`` each replace
   the built-in list rather than extending it, so a helpful guess makes the gate
   quietly narrower than advertised. Only the ``verification`` block is written.
2. **Every command it writes has been run first**, and its exit status is shown.
   A check nobody executed is the placeholder again with better wording.
3. **It refuses rather than guesses.** A project it cannot recognise gets an
   honest "I could not tell", not a plausible config. A wrong config is worse
   than the placeholder it replaced: the placeholder is visibly unfinished.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

MARK_HOOK = HERE / "cerberus_mark.py"
GATE_HOOK = HERE / "cerberus_gate.py"

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

# What the last check has to reach, per kind. Deliberately NOT commands: this
# script cannot run a deploy or a package build during setup, and writing a
# comment line into a list of commands would be the placeholder again — a `#`
# line exits 0 unconditionally, exactly like the `echo` it replaced. So the
# list is left empty and the sentence is handed to the user instead.
# The installer's own copy of cerberus.example.json, identified by the two
# strings it ships. This is the only existing configuration that can be
# rewritten without guessing whether a human chose its values — everything else
# is left alone, because `cerberus.json` records no distinction between "the
# user set this" and "the installer did", and three rounds of proxies for that
# distinction each produced a defect.
#
# tests/test_setup.py asserts these still match the shipped example.
EXAMPLE_MARKER_COMMENT = 'Copy to .claude/cerberus.json. Safe to use as-is: only the key that has no sensible default is set. Everything else keeps the built-in defaults, so copying this verbatim never narrows the gate by accident.'
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
        existing.get("//") == EXAMPLE_MARKER_COMMENT
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

    Replacing the whole document is how a hand-tuned gate got deleted: the keys
    this script must never write are also keys it must never remove.
    """
    path = root / ".claude" / "cerberus.json"
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
    if True:
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


def demonstrate(root: pathlib.Path) -> tuple[bool, str]:
    """Show the refusal happening, rather than reporting that it would.

    Returns (it worked, what to tell the user). Both halves are exercised: a
    claim while something is unchecked must be refused, and a claim with
    nothing outstanding must go through — a hook that refuses everything is
    just as broken and would otherwise pass this.
    """
    if not MARK_HOOK.exists() or not GATE_HOOK.exists():
        return False, "the two scripts are missing, so nothing could be shown"

    scratch = "cerberus_setup_probe.py"
    transcript = root / ".claude" / "cerberus_setup_probe.jsonl"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text(
        json.dumps({"role": "assistant", "message": {"content": "all done, it works"}}) + "\n",
        encoding="utf-8",
    )

    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
    marker = root / ".claude" / ".cerberus-pending"
    had_marker = marker.exists()
    # Read as bytes and inside the try: a path the mark hook recorded may not be
    # valid UTF-8, and decoding it out here escaped the cleanup entirely — a
    # traceback instead of a sentence, and a probe file left behind.
    saved = None

    def hook(script: pathlib.Path, payload: dict) -> str:
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )
        return proc.stdout.strip()

    try:
        if had_marker:
            saved = marker.read_bytes()
        # The negative sentinel first: with nothing outstanding, a claim goes through.
        if marker.exists():
            marker.unlink()
        quiet = hook(GATE_HOOK, {"cwd": str(root), "transcript_path": str(transcript)})
        if quiet:
            return False, "it refuses even when nothing is outstanding, which would make it noise"

        hook(MARK_HOOK, {"cwd": str(root), "tool_input": {"file_path": scratch}})
        if not marker.exists():
            return False, "editing a file did not register, so nothing would ever be checked"

        out = hook(GATE_HOOK, {"cwd": str(root), "transcript_path": str(transcript)})
        payload = json.loads(out) if out else {}
        if payload.get("decision") != "block":
            return False, "saying the work was done was not refused"
        if scratch not in payload.get("reason", ""):
            return False, "it refused but could not name the file that was edited"
        return True, "saying the work was done was refused, and it named the edited file"
    except Exception as exc:
        return False, f"the check itself failed: {exc}"
    finally:
        transcript.unlink(missing_ok=True)
        if had_marker and saved is not None:
            marker.write_bytes(saved)
        elif marker.exists():
            marker.unlink()


def _hooked(data: dict, event: str, script: str, root: pathlib.Path) -> bool:
    """Does this settings document actually run `script` on `event`?

    Parsed, never searched. A substring check certified a file whose only
    mention of the scripts was a TODO comment, and certified entries filed
    under an event name that never fires.
    """
    for entry in (data.get("hooks") or {}).get(event) or []:
        if not isinstance(entry, dict):
            continue
        # The event is checked; so is the matcher, which is the same mistake one
        # field down. An entry filed under PostToolUse with matcher "Bash" is
        # well formed and never sees a file being written, so nothing is ever
        # recorded and the gate has nothing to hold.
        if event == "PostToolUse":
            matcher = entry.get("matcher")
            if matcher is not None:
                # Whole alternatives, not substrings: `MultiEdit` and
                # `NotebookEdit` contain "Edit" and never fire on an ordinary
                # Write or Edit, so the entry records nothing.
                parts = {a.strip() for a in str(matcher).split("|")}
                if not (parts & {"Write", "Edit", "*", ""}):
                    continue
        for hook in entry.get("hooks") or []:
            if not isinstance(hook, dict):
                continue
            if hook.get("type") not in (None, "command"):
                continue  # a prompt hook runs no command at all
            cmd = hook.get("command")
            if not isinstance(cmd, str) or script not in cmd:
                continue
            # The command must point at a file that is there. An entry aimed at
            # a path that does not exist runs nothing.
            # Quotes are removed rather than replaced by spaces: the shipped
            # wiring is `python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/…`, and
            # splitting on the quote leaves an absolute `/.claude/hooks/…`
            # that exists nowhere — which read as "not wired" on the one path
            # the installer itself produces.
            bare = cmd.replace('"', "").replace("'", "")
            bare = bare.replace("${CLAUDE_PROJECT_DIR}", str(root))
            bare = bare.replace("$CLAUDE_PROJECT_DIR", str(root))
            # No single extraction rule survives every shape this takes:
            # splitting on whitespace loses paths containing a space, and
            # anchoring on the project path latches onto the argument of a
            # `cd <root> && …` prefix. Both were shipped, one per round. So
            # both readings are tried, and the entry counts as wiring if either
            # resolves to a file that is there.
            end = bare.index(script) + len(script)
            candidates = []
            if str(root) in bare[:end]:
                candidates.append(bare[bare.rindex(str(root), 0, end):end])
            token = next((w for w in bare[:end].split() if script in w), "")
            if token:
                candidates.append(token)
            # A mention is not an invocation. A whitelist of interpreters was
            # tried and collided with project paths containing spaces, so this
            # is a narrow list of forms that provably run nothing: a commented
            # out entry — which is how a person disables a hook inside JSON —
            # and the path handed to echo or printf. `false && python3 X` and
            # the script appearing as an argument to a real command are not
            # caught, and are written down as known limits rather than guessed
            # at: deciding whether a command would execute is a different and
            # much larger problem than whether it names a file that exists.
            stripped = bare.strip()
            if stripped.startswith("#"):
                continue
            if stripped.split(" ")[0] in ("echo", "printf", ":", "true", "false"):
                continue
            for candidate in candidates:
                path = pathlib.Path(candidate)
                if not path.is_absolute():
                    path = root / candidate
                if path.exists():
                    return True
    return False


def wiring(root: pathlib.Path) -> tuple[bool, str]:
    """Is anything actually going to call these scripts *for this project*?

    ``demonstrate`` runs them directly, which proves they work and nothing
    else. This asks the target project, and only the target project. An earlier
    version asked the directory the script happened to be sitting in, so
    running it from a clone with ``--dir`` — which is what ``install.sh`` does —
    certified a project that had no hooks at all.

    A plugin install is the one case where a correctly wired project says
    nothing in its own settings, because the hooks come from the plugin. That
    cannot be observed from here, so it is named as the one benign explanation
    rather than assumed.
    """
    # A plugin install is the one case a project cannot show from inside — its
    # settings never name the hooks. But when this script is running out of the
    # plugin, the harness says so, and the plugin's own hooks.json is right
    # there: that is evidence rather than the guess an earlier version made
    # from a file sitting next to the script.
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        declared = pathlib.Path(plugin_root) / "hooks" / "hooks.json"
        try:
            events = json.loads(declared.read_text(encoding="utf-8")).get("hooks") or {}
            wired = json.dumps(events)
            if "cerberus_mark.py" in wired and "cerberus_gate.py" in wired:
                return True, "the plugin declares both hooks, so they run in every project"
        except Exception:
            pass

    found = []
    for name in ("settings.json", "settings.local.json"):
        path = root / ".claude" / name
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            continue
        except Exception:
            return False, f"the .claude/{name} here is not valid JSON"
        if not isinstance(data, dict):
            continue
        found.append(name)
        if _hooked(data, "PostToolUse", "cerberus_mark.py", root) and _hooked(
            data, "Stop", "cerberus_gate.py", root
        ):
            return True, f".claude/{name} runs both of them"

    if not found:
        return False, "this project has no .claude/settings.json"
    return False, f"nothing in .claude/{found[0]} runs both of them"


def report_state(root: pathlib.Path, kind: str = "library", failing: bool = False) -> int:
    """Show whether the gate is on, and what is still missing.

    Shared by the fresh path and the already-configured one, because skipping
    it on a re-run answered "is it on?" without looking.
    """
    config = root / ".claude" / "cerberus.json"
    worked, detail = demonstrate(root)
    print("Tried it:", detail)
    if not worked:
        print()
        print("So it is not guarding anything yet, and the reason is above.")
        return 1

    connected, why = wiring(root)
    if not connected:
        # Two very different situations, and guessing either way is wrong.
        # Scripts sitting in this project mean somebody copied them here and
        # the wiring is genuinely missing. No scripts here means they come from
        # somewhere else — a plugin — which cannot be seen from inside the
        # project, so it is named rather than assumed or denied.
        copied_here = (root / ".claude" / "hooks" / "cerberus_mark.py").exists()
        print()
        if copied_here:
            print(f"But nothing here is calling it: {why}.")
            print("The files are in this project and nothing runs them. Re-run the")
            print("installer, or paste the snippet it prints, and try again.")
            return 1
        print(f"I cannot see this project calling it: {why}.")
        print("If you installed it as a plugin, that is expected — the plugin runs it")
        print("everywhere and this cannot be seen from inside a project. If you did")
        print("not, run the installer here.")
        # Falling through printed this caveat and then the closing line saying
        # claims are refused from now on — two adjacent paragraphs contradicting
        # each other, with the false one last.
        return 3

    print()
    print("From now on, when the work is claimed to be done and code has changed,")
    print("that claim is refused until the checks above have been run.")
    if failing:
        print("Your own tests are failing right now — that is worth a look first.")
    try:
        stage2 = json.loads(config.read_text(encoding="utf-8"))["verification"]["stage2"]
    except Exception:
        stage2 = []
    if not stage2:
        print("One thing is still missing: the last check, the one that runs where")
        print(f"this really ships. Put it in {config.relative_to(root)} —")
        print(f"{STAGE2_HINT_BY_KIND.get(kind, STAGE2_HINT_BY_KIND['library'])}.")
    print("To change the checks or switch it off, edit the same file.")
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
    config = root / ".claude" / "cerberus.json"

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
                found = [c for c, code, _ in build_checks(runners, root) if code == 0]
                if found:
                    print()
                    print("Checks I found here and ran, if you want them:")
                    for cmd in found:
                        print(f"  ok       {cmd}")
            print()
            return report_state(root, verification.get("artifact_kind") or kind or "library", still_failing)

    # Only now, because a project this cannot recognise may already be
    # configured by hand — and those are exactly the projects that most need
    # the "is it on?" answer, since detection is why they are hand-configured.
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

    write_config(root, kind, passing, args.check, existing)

    if len(runners) > 1:
        others = ", ".join(r["name"] for r in runners[1:])
        print(f"This project uses several toolchains: {runners[0]['name']}, {others}.")
        print(f"I took it as a {runners[0]['name']} {kind} — change that if it is wrong.")
    else:
        print(f"Set up for this {runners[0]['name']} project.")
        print(f"I took it as a {kind} — change that if it is wrong.")
    print()
    print("Checks I ran here, and will run before anyone says the work is done:")
    for cmd in passing:
        print(f"  ok       {cmd}")
    for cmd, _ in broken:
        print(f"  FAILING  {cmd} — it ran and did not pass, so it was left out")
    for cmd in missing:
        print(f"  absent   {cmd} — not installed here, so it was left out")
    for cmd in timed_out:
        print(f"  too slow {cmd} — gave up waiting, so it was left out")
    print()

    if args.check:
        print(f"Nothing was written. Drop --check to save this to {config}.")
        return 0

    return report_state(root, kind, bool(broken))


if __name__ == "__main__":
    sys.exit(main())
