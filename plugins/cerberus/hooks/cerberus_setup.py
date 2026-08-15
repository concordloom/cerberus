#!/usr/bin/env python3
"""Set a project up, and prove the gate fires before saying so.

Not a hook. It lives beside them because ``install.sh`` copies
``hooks/*.py`` into a project, so this is the one directory that reaches every
installation without a second delivery path.

Run it from the project root:

    python3 .claude/hooks/cerberus_setup.py           # set up, then demonstrate
    python3 .claude/hooks/cerberus_setup.py --check   # say what it would do

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

STAGE2_BY_KIND = {
    "service": [
        "# Run the real thing where it actually runs, and drive one request end to end.",
        "# Then make it fail on purpose and check the failure shows up.",
    ],
    "library": [
        "# Build the package, install it into an empty environment,",
        "# and import it there the way somebody else would.",
    ],
    "cli": [
        "# Install the built command somewhere clean and run it with real arguments.",
        "# Check the exit codes, not just the output.",
    ],
    "chart": [
        "# Apply it to a real cluster or account and watch it settle.",
    ],
    "plugin": [
        "# Install it into a clean environment and load it there.",
    ],
}


def run(cmd: str, cwd: pathlib.Path, timeout: int = 120) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd, shell=True, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except Exception as exc:  # a missing shell is not this script's problem to solve
        return 127, str(exc)


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

    Nothing reaches the config without having been executed here first.
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


def write_config(root: pathlib.Path, kind: str, checks: list[str], dry: bool) -> pathlib.Path:
    path = root / ".claude" / "cerberus.json"
    body = {
        "//": "Written by cerberus_setup.py. Every command below was run once, here, before being written.",
        "verification": {
            "artifact_kind": kind,
            "stage1": checks,
            "stage2": STAGE2_BY_KIND.get(kind, STAGE2_BY_KIND["library"]),
            "notes": "Replace the stage2 lines with the real commands for this project.",
        },
    }
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
    saved = marker.read_text(encoding="utf-8") if had_marker else None

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
            marker.write_text(saved, encoding="utf-8")
        elif marker.exists():
            marker.unlink()


def wiring(root: pathlib.Path) -> tuple[bool, bool]:
    """Is anything actually going to call these scripts?

    ``demonstrate`` runs them directly, which proves they work and nothing
    else. Claude Code only runs them if they are named in settings, and a
    project where they are installed but unnamed behaves exactly like a project
    where they are absent — the difference being that it looks installed. That
    is the whole failure this script exists to catch, so it must not be the one
    thing this script takes on faith.
    """
    settings = root / ".claude" / "settings.json"
    try:
        text = settings.read_text(encoding="utf-8")
    except Exception:
        return False, False
    return "cerberus_mark.py" in text, "cerberus_gate.py" in text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--check", action="store_true", help="say what would happen, change nothing")
    parser.add_argument("--dir", default=".", help="project directory")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.dir).resolve()
    config = root / ".claude" / "cerberus.json"

    runners, kind = detect(root)
    if not runners or kind is None:
        print("I could not tell what kind of project this is.")
        print("Nothing was changed. Tell me two things and I can finish:")
        print("  1. the command that runs your tests")
        print("  2. how someone else gets this — a running service, an installed")
        print("     package, a command they type")
        return 2

    existing = None
    if config.exists():
        try:
            existing = json.loads(config.read_text(encoding="utf-8"))
        except Exception:
            print(f"{config} exists but is not valid JSON. Fix or delete it, then run this again.")
            return 2
        stage1 = existing.get("verification", {}).get("stage1", [])
        untouched = all(str(c).startswith("echo ") for c in stage1) if stage1 else True
        if not untouched:
            print("This project is already set up, and the checks are yours, not the")
            print("example ones. Nothing was changed.")
            return 0

    results = build_checks(runners, root)
    passing = [cmd for cmd, code, _ in results if code == 0]
    failing = [(cmd, out) for cmd, code, out in results if code != 0]

    if not passing:
        print(f"I found a {runners[0]['name']} project but none of its checks ran here.")
        for cmd, out in failing[:3]:
            print(f"  {cmd} — {out.splitlines()[0][:60] if out else 'no output'}")
        print("Nothing was changed. Fix one of those, or tell me the right command.")
        return 2

    write_config(root, kind, passing, args.check)

    print(f"Set up for this {runners[0]['name']} project.")
    print()
    print("Checks I ran here, and will run before anyone says the work is done:")
    for cmd in passing:
        print(f"  ok   {cmd}")
    for cmd, _ in failing:
        print(f"  n/a  {cmd} — did not run here, so it was left out")
    print()

    if args.check:
        print(f"Nothing was written. Drop --check to save this to {config}.")
        return 0

    worked, detail = demonstrate(root)
    print("Tried it:", detail)
    if not worked:
        print()
        print("So it is not guarding anything yet, and the reason is above.")
        return 1

    marked, gated = wiring(root)
    if not (marked and gated):
        print()
        print("But nothing is calling it yet: this project's settings do not mention")
        print("it, so the check above only happened because I ran it by hand.")
        print("Re-run the installer, or paste the snippet it prints, then try again.")
        return 1

    print()
    print("From now on, when the work is claimed to be done and code has changed,")
    print("that claim is refused until the checks above have been run.")
    print(f"To change the checks or switch it off, edit {config.relative_to(root)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
