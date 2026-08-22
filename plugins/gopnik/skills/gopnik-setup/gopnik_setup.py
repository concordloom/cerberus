#!/usr/bin/env python3
"""Work out this project's checks by running them, and write them down.

Run it from the project root:

    python3 gopnik_setup.py           # find the checks, run them, save them
    python3 gopnik_setup.py --check   # run them and print them, write nothing
    python3 gopnik_setup.py --defer-artifact-kind  # save Stage 1, wait for confirmation
    python3 gopnik_setup.py --refresh # compare the record with the tree, write nothing
    python3 gopnik_setup.py --add-stage1 './ui-tests/run.sh'  # answer the refresh
    python3 gopnik_setup.py --confirm-artifact-kind service --surfaces service,chart

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
import re
import shlex
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

# These files outrank toolchain guesses. If a repository has written agent
# instructions, a generic `go test`, `npm test`, or equivalent may be forbidden
# even though the manifest makes it look obvious. The script cannot interpret
# prose safely, so it stops and lets the agent pass the commands it read via
# `--stage1` instead of violating the project while trying to configure it.
PROJECT_INSTRUCTION_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
)

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
CONFIG_PATHS = (".claude/gopnik.json", ".codex/gopnik.json", "gopnik.json")

# The installer's own copy of gopnik.example.json, identified by the two
# strings it ships. This is the only existing configuration that can be
# rewritten without guessing whether a human chose its values — everything else
# is left alone, because `gopnik.json` records no distinction between "the
# user set this" and "the installer did", and three rounds of proxies for that
# distinction each produced a defect.
#
# tests/test_setup.py asserts these still match the shipped example.
EXAMPLE_MARKER_COMMENT = 'Copy to gopnik.json in your project root. Safe to use as-is: the only key set is the one with no sensible default, and the checks below are placeholders until setup runs.'
EXAMPLE_MARKER_STAGE1 = ["echo 'replace with this project: tests, lint, type check'"]

SETUP_MARKER_COMMENT = (
    "Every command in stage1 was run once, in this project, before being written here."
)
PENDING_KIND_COMMENT = (
    "Pending confirmation of how people use this project after delivery."
)
PENDING_KIND_NOTES = (
    "Stage 1 is configured. Delivery surfaces still need user confirmation before Stage 2."
)


STAGE2_HINT_BY_KIND = {
    "service": "run it where it actually runs and drive one real request through it",
    "library": "build the package, install it somewhere empty, and import it from there",
    "cli": "install the built command somewhere clean and run it with real arguments",
    "chart": "apply it to a real cluster or account and watch it settle",
    "plugin": "install it into a clean environment and load it there",
    "migration": "run it against a copy of real shape and scale",
    "model-boundary": "make a real model call through the production entry point",
}


#: Evidence that this project is deployed somewhere, and what each file is
#: worth knowing for. Ordered from the most specific to the least: a chart says
#: more about how this ships than a Dockerfile does.
DEPLOY_EVIDENCE = [
    ("helm", ["helm", "chart", "charts", "Chart.yaml"]),
    ("k8s", ["k8s", "kubernetes", "manifests", "deploy"]),
    ("ci", [".github/workflows", ".gitlab-ci.yml"]),
    ("compose", ["docker-compose.yml", "docker-compose.yaml", "compose.yaml"]),
    ("image", ["Dockerfile"]),
]

#: The one visible trace of "pasted from the draft rather than agreed". The
#: draft uses a single prefix so this rule can be exact rather than a guess at
#: what looks unfinished; an env var or a real host is never matched.
PLACEHOLDER = re.compile(r"\bYOUR_[A-Z][A-Z_]*\b")


def unfinished(stage2: list) -> list[str]:
    """Placeholders still in the configuration, in the order they appear."""
    left = []
    for command in stage2:
        left += [m for m in PLACEHOLDER.findall(str(command)) if m not in left]
    return left


def parse_surfaces(value: str) -> list[str]:
    """The confirmed delivery surfaces, in the order they were confirmed.

    Deduplicated and stripped, and nothing else: these identifiers come from a
    critic and a person, not from a vocabulary this script owns. Normalising
    them further would mean deciding that `web` and `dashboard` are the same
    surface, which is a judgement about somebody else's product.
    """
    found = []
    for part in value.split(","):
        name = part.strip()
        if name and name not in found:
            found.append(name)
    return found


#: Returned when the key is present but says nothing. Distinct from None,
#: which means the project never claimed the boundary was unreachable.
UNREACHABLE_WITHOUT_REASON = object()


def unreachable_reason(body: dict):
    """The declared reason, None if not declared, or the sentinel if blank."""
    if "stage2_unreachable" not in body.get("verification", {}):
        return None
    reason = body["verification"]["stage2_unreachable"]
    if not isinstance(reason, str) or not reason.strip():
        return UNREACHABLE_WITHOUT_REASON
    return reason.strip()


#: Kinds whose boundary is a running instance, and therefore the only ones a
#: deployment draft can be right for. A repository can hold a Dockerfile for CI
#: and still ship a library — drafting a deploy for that would be a confident
#: wrong answer, which this project treats as worse than saying nothing.
DEPLOYED_KINDS = ("service", "chart")

#: Shapes that cannot return a non-zero exit, and so cannot fail. A stage2
#: entry built from one of these passes on a broken deploy, which is the
#: placeholder problem on the stage where it costs the most.
CANNOT_FAIL = [
    (r"\bcurl\b(?!.*(?:-f|--fail))", "curl without -f exits 0 on a 500"),
    (r"^\s*(?:echo|true|:)\b", "always exits 0"),
    (r"^\s*#", "a comment is not a check"),
    # The placeholder belongs in this list too: the rule has to cover what this
    # script itself emits, or the draft can teach a trap while containing one.
    (r"\b(?:logcli|kubectl logs|YOUR_LOG_QUERY)\b(?!.*(?:grep|jq|rg|\bawk\b))",
     "a log query usually exits 0 when it finds nothing"),
    (r"^\s*sleep\b", "sleeping is not waiting for anything in particular"),
    (r"\bgh run watch\b(?!.*--exit-status)",
     "gh run watch exits 0 even when the run it watched went red"),
    # Only when nothing on the line can go red. `gh run list` picking the run
    # for `watch --exit-status` is the fix, not the trap — the first version of
    # this rule condemned the correct form, which is how a guard teaches the
    # wrong lesson.
    (r"^(?!.*--exit-status).*\bgh run list\b",
     "listing runs succeeds whoever's run it lists"),
]

#: What CI is in use, decided from the file that configures it. The command
#: that waits for a pipeline is the one thing that cannot be guessed across
#: forges, and guessing it would produce a line that looks right and waits for
#: nothing.
FORGES = [
    ("github", [".github/workflows"], "gh run watch --exit-status $(gh run list "
                                      "--commit $(git rev-parse HEAD) --limit 1 "
                                      "--json databaseId --jq '.[0].databaseId')"),
    ("gitlab", [".gitlab-ci.yml"], "YOUR_PIPELINE_WAIT  # must exit non-zero when "
                                   "the pipeline fails"),
]


def deploy_evidence(root: pathlib.Path) -> list[tuple[str, str]]:
    """What in this repository says it gets deployed, and which file said so."""
    found = []
    for name, paths in DEPLOY_EVIDENCE:
        for relative in paths:
            target = root / relative
            if not target.exists():
                continue
            if name == "ci" and target.is_dir():
                # A workflows directory proves nothing on its own; the word
                # that matters is in the files.
                hits = [f for f in sorted(target.glob("*.y*ml"))
                        if re.search(r"deploy|kubectl|helm|rollout",
                                     f.read_text(encoding="utf-8", errors="ignore"), re.I)]
                if not hits:
                    continue
                found.append((name, str(hits[0].relative_to(root))))
                break
            found.append((name, relative + ("/" if target.is_dir() else "")))
            break
    return found


def forge_of(root: pathlib.Path) -> tuple[str, str] | None:
    """Which CI runs here, and the command that waits for it."""
    for name, paths, wait in FORGES:
        if any((root / p).exists() for p in paths):
            return name, wait
    return None


#: Ways to prove the instance answering you is the commit under test. Without
#: one of these, waiting for a pipeline and calling the URL verifies whichever
#: build happened to be there — green, and about nothing.
REVISION_PROOF = (
    "curl -fsS YOUR_URL/version | jq -e --arg sha \"$(git rev-parse HEAD)\" "
    "'.revision == $sha'"
)


def draft_stage2(kind: str, evidence: list[tuple[str, str]],
                 forge: tuple[str, str] | None = None) -> list[str]:
    """Propose commands. Never write them — this cannot run a deploy.

    Proposing is not writing: the rule that setup never records a check it has
    not executed is what keeps its output trustworthy, and a draft printed for
    a person to read, edit and paste does not touch it.
    """
    if kind not in DEPLOYED_KINDS or not evidence:
        return []
    names = {name for name, _ in evidence}
    tag = "$(git rev-parse --short HEAD)"
    lines = []
    if "image" in names or "helm" in names or "k8s" in names:
        lines.append(f"docker build -t YOUR_REGISTRY/YOUR_APP:{tag} . "
                     f"&& docker push YOUR_REGISTRY/YOUR_APP:{tag}")
    if "helm" in names:
        lines.append(f"helm upgrade --install YOUR_APP ./helm --namespace YOUR_NS "
                     f"--set image.tag={tag} --wait --atomic")
    elif "k8s" in names:
        lines.append(f"kubectl -n YOUR_NS set image deploy/YOUR_APP "
                     f"YOUR_APP=YOUR_REGISTRY/YOUR_APP:{tag}")
    if "helm" in names or "k8s" in names:
        lines.append("kubectl -n YOUR_NS rollout status deploy/YOUR_APP --timeout=120s")
    if not lines and "compose" in names:
        lines.append("docker compose up -d --build --wait")
    if not lines and "ci" in names and forge:
        # Nothing here can deploy, so Stage 2 starts by making the pipeline do
        # it and then proving it did — for THIS commit, which is the whole
        # difference between verifying and waiting.
        lines.append("git push   # the pipeline deploys; this is the trigger")
        lines.append(forge[1])
    if lines and ("ci" in names or "helm" in names or "k8s" in names):
        lines.append(REVISION_PROOF)
    lines.append("curl -fsS -H \"X-Request-Id: $RID\" YOUR_URL/YOUR_ENDPOINT "
                 "| jq -e 'YOUR_ASSERTION_ON_THE_VALUE'")
    lines.append("YOUR_LOG_QUERY --since=5m | grep -q \"$RID\"")
    return lines


def unfailable(command: str) -> str | None:
    """Why this command could never report a failure, or None if it could."""
    for shape, why in CANNOT_FAIL:
        if re.search(shape, command):
            return why
    return None


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


def detect(
    root: pathlib.Path,
    detect_kind: bool = True,
) -> tuple[list[dict], str | None]:
    """Find toolchains and, unless guided setup deferred it, a shipped kind."""
    found = [r for r in RUNNERS if any((root / f).exists() for f in r["files"])]

    if not detect_kind:
        return found, None

    kind = None
    for candidate, signals in KIND_SIGNALS:
        if signals and any((root / s).exists() for s in signals):
            kind = candidate
            break

    if kind is None and found:
        kind = "cli" if _looks_like_a_command(root) else "library"
    return found, kind


def project_instructions(root: pathlib.Path) -> list[pathlib.Path]:
    """Authoritative project instruction files present at this project root."""
    return [root / relative for relative in PROJECT_INSTRUCTION_FILES
            if (root / relative).is_file()]


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


def build_checks(
    runners: list[dict],
    root: pathlib.Path,
    timeout: int = 120,
) -> list[tuple[str, int, str]]:
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
            code, out = run(cmd, root, timeout=timeout)
            results.append((cmd, code, out))
            ran_one = ran_one or code == 0
        if not ran_one and runner["fallback"]:
            code, out = run(runner["fallback"], root, timeout=timeout)
            results.append((runner["fallback"], code, out))
    return results


def run_explicit_checks(
    commands: list[str],
    root: pathlib.Path,
    timeout: int = 120,
) -> list[tuple[str, int, str]]:
    """Run project-owned checks in order, stopping at the first red baseline."""
    results = []
    for command in commands:
        result = (command, *run(command, root, timeout=timeout))
        results.append(result)
        if result[1] != 0:
            break
    return results


def sort_results(results: list, *, explicit: bool = False) -> tuple[list, list, list, list]:
    """Split check results into what may be written and what may not.

    A function rather than four comprehensions inside main, because the rule —
    only exit 0 is written — was untestable from outside and a mutant counting
    a timeout as success wrote a hanging command into the config while printing
    "ok" and "too slow" about it in adjacent lines.
    """
    passing = [cmd for cmd, code, _ in results if code == 0]
    # Exit 127 from an auto-detected candidate normally means that tool is not
    # installed. For an explicit project-owned wrapper it can instead mean a
    # nested dependency failed (`app.sh: go: command not found`). Calling the
    # wrapper absent hides the useful error and sends the operator down the
    # wrong path, so explicit commands are always reported as failed.
    missing = [cmd for cmd, code, _ in results if code == 127 and not explicit]
    timed_out = [cmd for cmd, code, _ in results if code == 124]
    broken = [(cmd, out) for cmd, code, out in results
              if code not in (0, 124, 127) or (explicit and code == 127)]
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
    return root / "gopnik.json"


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


def is_pending_kind_config(existing: dict) -> bool:
    """Return true only when setup explicitly marked the kind as provisional."""
    verification = existing.get("verification")
    return (
        isinstance(verification, dict)
        and verification.get("//artifact_kind") == PENDING_KIND_COMMENT
        and isinstance(verification.get("stage1"), list)
        and bool(verification["stage1"])
    )


def write_config(
    root: pathlib.Path,
    kind: str | None,
    checks: list[str],
    dry: bool,
    existing: dict | None = None,
    language: str | None = None,
    defer_artifact_kind: bool = False,
) -> pathlib.Path:
    """Merge into whatever is there rather than replacing it.

    Replacing the whole document is how a hand-tuned configuration got deleted:
    the keys this script must never write are also keys it must never remove.
    """
    path = resolve_config(root)
    body = dict(existing) if isinstance(existing, dict) else {}
    if language is not None:
        body["language"] = language
    body["//"] = SETUP_MARKER_COMMENT
    prior = body.get("verification")
    verification = dict(prior) if isinstance(prior, dict) else {}
    # The rule that top-level keys are not to be removed applies one level down
    # too, and did not: a deliberate `migration` — a kind detect() can never
    # produce — was downgraded to a guess, and notes naming production accounts
    # were destroyed without a word.
    # Reached only for an absent config or the installer's own copy, so these
    # are never anybody's choice.
    verification["stage1"] = checks
    # Left empty on purpose: a comment line in a list of commands exits 0
    # unconditionally, which is the placeholder this script exists to remove.
    verification["stage2"] = []
    if defer_artifact_kind:
        verification.pop("artifact_kind", None)
        verification["//artifact_kind"] = PENDING_KIND_COMMENT
        verification["notes"] = PENDING_KIND_NOTES
    else:
        verification["artifact_kind"] = kind
        verification.pop("//artifact_kind", None)
        verification["notes"] = (
            "stage2 is still empty. Put here what proves it works where it really runs: "
            + STAGE2_HINT_BY_KIND.get(kind, STAGE2_HINT_BY_KIND["library"])
            + "."
        )
    body["verification"] = verification
    if not dry:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def confirm_artifact_kind(
    root: pathlib.Path,
    kind: str,
    dry: bool = False,
    surfaces: list[str] | None = None,
) -> pathlib.Path:
    """Finalize the provisional kind and the surfaces behind it.

    `artifact_kind` is one word for the farthest boundary. A project that
    delivers through several had nowhere to say so, and the requirement that
    Stage 2 cover every confirmed surface therefore had no data behind it:
    the critic's surviving set was used to phrase one question and then thrown
    away. `surfaces` is that set, after the person confirmed it.

    Written only when this step was given one. `None` means the question was
    not asked in this run, and an existing set is then left exactly as it
    stands — including one a person wrote by hand.
    """
    path = resolve_config(root)
    try:
        body = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError("no readable provisional configuration to confirm") from exc
    if not is_pending_kind_config(body):
        raise ValueError(
            "artifact kind can only be confirmed for a setup that explicitly deferred it"
        )

    verification = dict(body["verification"])
    fresh_setup = (
        body.get("//") == SETUP_MARKER_COMMENT
        and "artifact_kind" not in verification
        and verification.get("stage2") == []
        and verification.get("notes") == PENDING_KIND_NOTES
    )
    verification["artifact_kind"] = kind
    verification.pop("//artifact_kind", None)
    if surfaces is not None:
        verification["surfaces"] = list(surfaces)
    if fresh_setup:
        verification["notes"] = (
            "stage2 is still empty. Put here what proves it works where it really runs: "
            + STAGE2_HINT_BY_KIND.get(kind, STAGE2_HINT_BY_KIND["library"])
            + "."
        )
    body["verification"] = verification
    if not dry:
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


# ----------------------------------------------------------------- refresh
#
# Why this is a mode of its own rather than more of `--check`, honestly.
#
# The first version of this comment argued that `--check` could not host the
# refresh because "a flag whose contract is writes-nothing cannot host the step
# that writes". A critic pointed out that this justifies nothing: `--refresh`
# never writes either, the write lives in `--add-stage1`, and `--add-stage1`
# would be a separate flag under either design — it already reuses `--check` as
# its own dry-run modifier. The argument conflated two flags.
#
# The real reasons are smaller, and are ergonomics rather than impossibility:
#
# 1. `--check` already means "what would a *setup* run write here", and on a
#    configured project it prints "Already configured, so nothing was changed".
#    Hanging drift reporting off it gives one flag two unrelated questions, and
#    the answer people want — has this record gone stale — is not discoverable
#    under a name that reads as a dry run.
# 2. Refresh has a state `--check` has no answer for: no configuration at all.
#    That needs its own exit and its own sentence, not "nothing to dry-run".
#
# `--check` genuinely could have carried the report, and on one point it would
# have been better: it *runs* each recorded command, so it detects a broken
# check by its exit status rather than by a path lookup. That is why the path
# rule below is so conservative — it is the weaker instrument of the two and it
# is only allowed to speak when it is certain.
#
# So `--refresh` reports and never writes, and `--add-stage1` is the only way an
# answer reaches the file. `--add-stage1` edits exactly one key and leaves every
# other byte of the document alone.

#: Names that make an executable look like a project check. Deliberately short:
#: a name this does not recognise is not reported at all, because a mode that
#: finds something on every project is one people stop reading.
CHECK_NAME_HINTS = frozenset((
    "test", "tests", "check", "checks", "spec", "specs", "e2e", "integration",
    "smoke", "lint", "contract", "acceptance", "qa", "verify", "verification",
))

#: Directories whose executables are test *data* rather than this project's
#: checks. Without this, every fixture repository in this project's own pack was
#: offered back as a candidate Stage 1 command — including a fixture that fails
#: on purpose, proposed as something to record and run.
DATA_DIRS = frozenset((
    "fixtures", "fixture", "testdata", "test-data", "__fixtures__",
    "examples", "example", "samples", "sample", "mocks", "golden", "snapshots",
))

#: How deep an entry point is looked for. A project's own check sits at the top
#: or one directory down — `./check.sh`, `./ui-tests/run.sh`. Deeper than this
#: and it is a file inside somebody's test tree, not the command Stage 1 would
#: run, and offering it is noise.
MAX_CHECK_DEPTH = 3

#: Never walked when looking for checks: not this project's own code.
SKIPPED_DIRS = frozenset((
    "node_modules", "vendor", "venv", "target", "dist", "build", "__pycache__",
    "site-packages", "coverage", "htmlcov", "third_party", "Pods",
))


def _tokens(command: str) -> list[str]:
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


#: A command containing any of these runs more than one thing, or runs it
#: somewhere other than here. Which of its paths is missing is not visible from
#: the string, so no claim is made about any of them.
SHELL_OPERATORS = ("&&", "||", "|", ";", "`", "$(", ">", "<", "\n")

#: Programs whose next argument is the script they run. `sh ./check.sh` names a
#: path the same way `./check.sh` does.
INTERPRETERS = frozenset((
    "sh", "bash", "zsh", "dash", "ksh", "python", "python3", "node", "ruby",
    "perl", "pwsh",
))


def recorded_path_token(command: str) -> str | None:
    """The explicit path a recorded command runs, if it names one at all.

    Deliberately almost always None. Only the documented-wrapper shape is
    claimed: `./check.sh`, `./app.sh --test`, `sh ./ui-tests/run.sh`. Everything
    else is refused, because the first version of this was far too eager and
    every case it got wrong was a false alarm on an ordinary project:

    - `go test ./...` — the most common Stage 1 command in the Go ecosystem —
      was read as a path `./...` and reported as deleted, on every Go project.
    - `cd frontend && ./test.sh` names a path relative to `frontend`, not here.
    - `sh -c './check.sh && ./lint.sh'` is one token that is not a filename.
    - `docker run -v /tmp/cache:/cache …` has a mount spec, not a path.

    A missing check reported as present is a quiet gap; a present check reported
    as missing is a mode people stop reading. This errs at the first.
    """
    text = str(command)
    if any(operator in text for operator in SHELL_OPERATORS):
        return None
    tokens = _tokens(text)
    if not tokens:
        return None
    candidates = [tokens[0]]
    if tokens[0] in INTERPRETERS and len(tokens) > 1:
        candidates.append(tokens[1])
    for token in candidates:
        if not token.startswith(("./", "../", "/")):
            continue
        # A glob is not a filename, and `:` means a mount or a host, not a path.
        if token.endswith("...") or any(ch in token for ch in "*?:"):
            continue
        return token
    return None


def missing_recorded(commands: list[str], root: pathlib.Path) -> list[tuple[str, str]]:
    """Recorded commands whose own path is no longer in the tree."""
    gone: list[tuple[str, str]] = []
    for command in commands:
        token = recorded_path_token(str(command))
        if token is None:
            continue
        target = pathlib.Path(token)
        target = target if target.is_absolute() else root / token
        try:
            here = target.exists()
        except OSError:
            continue
        if not here:
            gone.append((str(command), token))
    return gone


def named_paths(commands: list[str], root: pathlib.Path) -> set[pathlib.Path]:
    """Every existing path any recorded command names, however loosely.

    Generous on purpose, and in the opposite direction to `recorded_path_token`:
    here a bare `tests` that happens to be a real directory does count. The two
    asymmetries point the same way — one refuses to call something gone, the
    other refuses to call something unaccounted for — and both err into silence.
    """
    named: set[pathlib.Path] = set()
    for command in commands:
        for token in _tokens(str(command)):
            if not token or token.startswith("-") or "://" in token:
                continue
            candidate = pathlib.Path(token)
            candidate = candidate if candidate.is_absolute() else root / token
            try:
                if candidate.exists():
                    named.add(candidate.resolve())
            except OSError:
                continue
    return named


def _check_shaped(name: str) -> bool:
    stem = name.rsplit(".", 1)[0].lower() if "." in name else name.lower()
    if stem in CHECK_NAME_HINTS:
        return True
    return any(word in CHECK_NAME_HINTS
               for word in re.split(r"[^a-z0-9]+", stem) if word)


def _walk(root: pathlib.Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d not in SKIPPED_DIRS)
        for name in sorted(filenames):
            yield pathlib.Path(dirpath) / name


def unnamed_checks(commands: list[str], root: pathlib.Path) -> list[str]:
    """Executable checks in the tree that no recorded command names.

    Bounded twice over, because the first version was silent on this project
    only by accident. Its own `stage1` happens to contain the bare word `tests`
    in a `compileall` line, which resolved to a real directory and covered the
    whole fixture pack. For any ordinary Stage 1 — `make test`, `npm test`,
    `./check.sh` — the same tree produced ten candidates, all of them test data.
    A property that holds by coincidence is not a property.

    Not "nothing runs it", and the wording of the report says so. This cannot
    see inside a wrapper and must not pretend to: the #76 fixture's `check.sh`
    carries a comment saying it never invokes `ui-tests/`, so a helper that
    inferred invocation from a substring would read that very sentence as proof
    of the opposite. Deciding what actually runs a check is the agent's job, and
    SKILL.md gives it the three buckets to put each one in.
    """
    named = named_paths(commands, root)
    found: list[str] = []
    for path in _walk(root):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if relative.name.startswith(".") or path.is_symlink() or not path.is_file():
            continue
        if not os.access(path, os.X_OK):
            continue
        if len(relative.parts) > MAX_CHECK_DEPTH:
            continue
        if any(part.lower() in DATA_DIRS for part in relative.parts):
            continue
        if not any(_check_shaped(part) for part in relative.parts):
            continue
        here, covered = path, False
        while True:
            try:
                if here.resolve() in named:
                    covered = True
                    break
            except OSError:
                pass
            if here == root or here.parent == here:
                break
            here = here.parent
        if not covered:
            found.append("./" + relative.as_posix())
    return found


def _scan_string(text: str, i: int) -> int:
    """Index just past the JSON string starting at `text[i] == '\"'`."""
    i += 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == '"':
            return i + 1
        i += 1
    raise ValueError("unterminated string")


def _find_key(text: str, start: int, key: str) -> int | None:
    """Index of the colon after the next `"key":` at or after `start`.

    Comparison is on the decoded literal, so the `//stage1` comment key that
    this project's own configuration carries can never be mistaken for
    `stage1`.
    """
    i = start
    while i < len(text):
        if text[i] == '"':
            end = _scan_string(text, i)
            try:
                decoded = json.loads(text[i:end])
            except ValueError:
                decoded = None
            if decoded == key:
                j = end
                while j < len(text) and text[j] in " \t\r\n":
                    j += 1
                if j < len(text) and text[j] == ":":
                    return j
            i = end
            continue
        i += 1
    return None


def _array_span(text: str, i: int) -> tuple[int, int]:
    """`(index of '[', index of its matching ']')`, strings skipped."""
    while i < len(text) and text[i] in " \t\r\n":
        i += 1
    if i >= len(text) or text[i] != "[":
        raise ValueError("the recorded stage1 is not a list")
    opened, depth = i, 0
    while i < len(text):
        char = text[i]
        if char == '"':
            i = _scan_string(text, i)
            continue
        if char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
            if depth == 0:
                return opened, i
        i += 1
    raise ValueError("unterminated list")


def splice_stage1(text: str, additions: list[str]) -> str:
    """Add commands to `verification.stage1`, leaving every other byte alone.

    A `json.loads`/`json.dumps` round-trip is what the rest of this script does,
    and it is the wrong tool here. `json.dumps` escapes non-ASCII by default, so
    an operator's Russian note comes back as `\\uXXXX` — equal as a value,
    mangled as a file — and it reformats a document nobody asked it to touch.
    This mode edits one key, so it edits one key and nothing else moves.
    """
    verification = _find_key(text, 0, "verification")
    if verification is None:
        raise ValueError("no verification block to add to")
    stage1 = _find_key(text, verification, "stage1")
    if stage1 is None:
        raise ValueError("no recorded stage1 to add to")
    opened, closed = _array_span(text, stage1 + 1)

    encoded = [json.dumps(command, ensure_ascii=False) for command in additions]
    if not text[opened + 1:closed].strip():
        return text[:opened + 1] + ", ".join(encoded) + text[closed:]

    last = closed - 1
    while last > opened and text[last] in " \t\r\n":
        last -= 1
    if "\n" in text[opened:closed]:
        # Match the file's own line ending. Inserting an LF into a CRLF
        # document leaves it mixed, which is not corruption but is somebody
        # else's diff noise on the next commit.
        newline = "\r\n" if "\r\n" in text[opened:closed] else "\n"
        line_start = text.rfind("\n", 0, last) + 1
        indent = ""
        cursor = line_start
        while cursor < len(text) and text[cursor] in " \t":
            indent += text[cursor]
            cursor += 1
        insertion = "".join(f",{newline}{indent}{item}" for item in encoded)
    else:
        insertion = "".join(f", {item}" for item in encoded)
    return text[:last + 1] + insertion + text[last + 1:]


def add_stage1(
    root: pathlib.Path,
    additions: list[str],
    dry: bool = False,
) -> pathlib.Path:
    """Grow the recorded Stage 1, and refuse if the edit reached anything else.

    The splice can only insert, so the byte guarantee holds by construction.
    The re-parse below is the second lock: if the resulting document differs
    from the original in any way other than those commands appended to
    `stage1`, nothing is written at all. Failing closed is the only acceptable
    failure here — the alternative is a rewrite of somebody's hand-written
    delivery route, which is worse than never refreshing.
    """
    path = resolve_config(root)
    # Bytes, not text. `read_text`/`write_text` default to universal newlines,
    # so a configuration checked out with CRLF endings — every Windows working
    # tree with `core.autocrlf=true` — came back with every line ending
    # rewritten, under a message saying nothing else had been touched. The
    # re-parse guard below could never catch it: the values are equal, and it
    # is the file that was mangled.
    text = path.read_bytes().decode("utf-8")
    before = json.loads(text)
    recorded = [str(command) for command in before["verification"]["stage1"]]

    spliced = splice_stage1(text, additions)
    after = json.loads(spliced)

    expected = dict(before)
    verification = dict(before["verification"])
    verification["stage1"] = recorded + list(additions)
    expected["verification"] = verification
    if after != expected:
        raise ValueError("the edit would have changed more than stage1")

    if not dry:
        path.write_bytes(spliced.encode("utf-8"))
    return path


def _recorded_stage1(path: pathlib.Path) -> tuple[dict, list[str]]:
    body = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(body, dict):
        raise ValueError("not an object")
    verification = body.get("verification")
    if not isinstance(verification, dict):
        raise ValueError("no verification block")
    recorded = verification.get("stage1")
    if not isinstance(recorded, list):
        raise ValueError("no recorded stage1")
    return body, [str(command) for command in recorded]


def report_refresh(root: pathlib.Path) -> int:
    """Compare the recorded Stage 1 with the tree. Write nothing, ever."""
    path = resolve_config(root)
    where = path.relative_to(root) if path.is_relative_to(root) else path
    if not path.exists():
        print("There is no configuration here to refresh, so nothing was compared.")
        print("Run setup first; refresh only ever revisits a record that exists.")
        return 2
    try:
        _, recorded = _recorded_stage1(path)
    except Exception as exc:
        print(f"{where} cannot be read as a configuration ({exc}).")
        print("Fix it by hand, then run this again. Nothing was changed.")
        return 2

    gone = missing_recorded(recorded, root)
    unnamed = unnamed_checks(recorded, root)

    if not gone and not unnamed:
        print(f"The Stage 1 recorded in {where} still matches this tree: nothing "
              "it lists has gone missing, and no check here is unaccounted for.")
        return 0

    print(f"The Stage 1 recorded in {where}, against this tree:")
    if gone:
        print()
        print("Recorded, and no longer here:")
        for command, token in gone:
            print(f"  gone     {command} — {token} does not exist")
    if unnamed:
        print()
        print("Here, and named by no recorded command:")
        for candidate in unnamed:
            print(f"  unnamed  {candidate}")
        print()
        print("Whether something else already runs these is not visible from the")
        print("configuration. Read them, then add only the ones Stage 1 should run:")
        print("  --add-stage1 "
              + " --add-stage1 ".join(shlex.quote(c) for c in unnamed))
    print()
    print("Nothing was changed.")
    return 0


def apply_stage1(
    root: pathlib.Path,
    commands: list[str],
    timeout: int = 120,
    dry: bool = False,
) -> int:
    """Record the answer to the refresh question, once each command passes."""
    path = resolve_config(root)
    where = path.relative_to(root) if path.is_relative_to(root) else path
    if not path.exists():
        print("There is no configuration here to add a check to.")
        print("Run setup first. Nothing was changed.")
        return 2
    try:
        _, recorded = _recorded_stage1(path)
    except Exception as exc:
        print(f"{where} cannot be read as a configuration ({exc}).")
        print("Fix it by hand, then run this again. Nothing was changed.")
        return 2

    wanted: list[str] = []
    already: list[str] = []
    for command in commands:
        if command in recorded or command in wanted:
            already.append(command)
        else:
            wanted.append(command)

    if not wanted:
        print(f"Already recorded in {where}, so nothing was changed:")
        for command in already:
            print(f"  already  {command}")
        return 0

    # The same screen the stage2 draft has always had, applied here because a
    # command typed in answer to an offer reaches the record the same way. An
    # empty string runs as `sh -c ''`, exits 0, and would be written down as a
    # green Stage 1 check that can never go red.
    cannot_fail = []
    for command in wanted:
        if not command.strip():
            cannot_fail.append((command, "an empty command is not a check"))
            continue
        why = unfailable(command)
        if why:
            cannot_fail.append((command, why))
    if cannot_fail:
        print("A check that cannot report a failure is not a check, "
              "so nothing was added.")
        for command, why in cannot_fail:
            print(f"  cannot fail  {command!r} — {why}")
        return 2

    results = run_explicit_checks(wanted, root, timeout=timeout)
    passing, missing, timed_out, broken = sort_results(results, explicit=True)
    if missing or timed_out or broken or len(passing) != len(wanted):
        print("A check offered for Stage 1 did not pass here, so nothing was added.")
        for command in passing:
            print(f"  ok       {command}")
        for command, out in broken:
            first = out.splitlines()[0][:60] if out else "no output"
            print(f"  FAILING  {command} — {first}")
        for command in timed_out:
            print(f"  too slow {command} — gave up waiting")
        ran = {result[0] for result in results}
        for command in wanted:
            if command not in ran:
                print(f"  not run  {command} — an earlier command failed first")
        print("Only a check that ran and passed here may be recorded.")
        return 2

    try:
        add_stage1(root, wanted, dry=dry)
    except Exception as exc:
        print(f"Cannot add to the recorded Stage 1: {exc}.")
        print("Nothing was changed. Add the command by hand instead.")
        return 2

    print(f"{'Would add' if dry else 'Added'} to Stage 1 in {where}, "
          "after running each one here:")
    for command in already:
        print(f"  already  {command}")
    for command in wanted:
        print(f"  ok       {command}")
    print()
    if dry:
        print(f"Nothing was written. Drop --check to save this to {where}.")
    else:
        print("Nothing else in that file was touched.")
    return 0


def report_state(root: pathlib.Path, kind: str = "library", first_run: bool = True) -> int:
    """Say what is still missing, and — the first time only — how to use this.

    Split by run rather than shared, because the two readers are different
    people. Someone who has just installed a thing called a verification gate
    reasonably expects something to start happening, and has to be told what
    was and was not installed — no hook, and a skill to call. Someone running it a second time already knows, and printing it again
    directly under "nothing was changed" left the only paragraph with content
    followed by one with none.
    """
    config = resolve_config(root)
    where = config.relative_to(root) if config.is_relative_to(root) else config

    if first_run:
        print()
        print("No hook was installed — ask for the gopnik skill by name when it matters.")
    try:
        body = json.loads(config.read_text(encoding="utf-8"))
        stage2 = body["verification"]["stage2"]
    except Exception:
        body, stage2 = {}, []
    if stage2:
        # Non-empty is not the same as ready. A draft pasted verbatim reads as
        # configuration and fails later on a hostname nobody set, at the moment
        # a verdict was due.
        left = unfinished(stage2)
        if left:
            print(f"stage2 in {where} still has the draft's blanks in it: "
                  + ", ".join(left[:4]) + ("…" if len(left) > 4 else ""))
            print("Fill them in or remove those lines — as it stands it cannot run.")
            return 2
        return 0

    declared = unreachable_reason(body)
    if declared is UNREACHABLE_WITHOUT_REASON:
        # Not consent. An empty reason produces a verdict that narrows itself
        # and cannot say why, which is the invisible gap this key exists to
        # make visible.
        print(f'"stage2_unreachable" in {where} has no reason. Write why the '
              "boundary cannot be crossed, or remove the key.")
        return 2
    if declared:
        print(f"Stage 2 is declared unreachable: {declared}")
        print("Verdicts will say so and narrow themselves to Stage 1.")
        return 0

    hint = STAGE2_HINT_BY_KIND.get(kind, STAGE2_HINT_BY_KIND["library"])
    evidence = deploy_evidence(root)
    if draft_stage2(kind, evidence, forge_of(root)):
        seen = ", ".join(sorted({found for _, found in evidence}))
        print(f"Still missing — stage2 in {where}: {hint}. "
              f"I can draft it from {seen} — run this again with --draft-stage2.")
    else:
        print(f"Still missing — stage2 in {where}: {hint}.")
    # The kind names one boundary; a project can have been confirmed to deliver
    # through several, and this is the moment somebody is about to write the
    # steps. Saying nothing here is how the set stayed a fact nobody acted on.
    # `isinstance` rather than a truth test: this file is hand-editable, and a
    # `"surfaces": "command"` written by a person would otherwise be iterated
    # one character at a time and reported as seven surfaces.
    recorded = (body.get("verification") or {}).get("surfaces")
    confirmed = [str(s) for s in recorded] if isinstance(recorded, list) else []
    if len(confirmed) > 1:
        print("It has to cover all of: " + ", ".join(confirmed) + ".")
    return 0


def print_draft(root: pathlib.Path, config: pathlib.Path, detected: str | None) -> int:
    """Print a stage2 draft and the traps in it. Writes nothing, by design.

    Behind a flag rather than in the default output because the draft does not
    fit in a glance, and the run that reports what was set up has to. The
    default output offers it in one line; this is the reader taking it up.
    """
    kind = detected or "library"
    if config.exists():
        try:
            existing = json.loads(config.read_text(encoding="utf-8"))
            if is_pending_kind_config(existing):
                print("Delivery surfaces still need confirmation. Nothing was drafted.")
                return 2
            kind = existing["verification"].get("artifact_kind") or kind
        except Exception:
            pass

    evidence = deploy_evidence(root)
    draft = draft_stage2(kind, evidence, forge_of(root))
    if not draft:
        if kind not in DEPLOYED_KINDS:
            print(f"This is a {kind}, so stage2 is not a deploy: "
                  f"{STAGE2_HINT_BY_KIND.get(kind, STAGE2_HINT_BY_KIND['library'])}.")
        else:
            print("Nothing here says how this gets deployed — no chart, no manifests,")
            print("no compose file, no deploy job. I will not invent one.")
        print("Whatever you write, every line has to be able to exit non-zero.")
        return 0

    print("A draft, from " + ", ".join(f"{w}" for _, w in evidence) + ".")
    print("Nothing was written. Read it, fix the CAPITALS, then paste it into")
    print(f"{config.name} under verification.stage2:")
    print()
    for line in draft:
        print(f"  {line}")
    print()
    print("Why each line is shaped that way — these are the ways a stage 2")
    print("passes while checking nothing:")
    print("  -f on curl        without it, curl exits 0 on a 500")
    print("  jq -e on the body asserting a reply arrived passes on any reply")
    print("  grep -q on logs   a log query exits 0 when it finds nothing")
    print("  rollout status    fails when the pod never came up")
    if any(REVISION_PROOF.split()[0] in line and "revision" in line for line in draft):
        print("  the /version line  the one that stops you verifying yesterday's")
        print("                    build: waiting for a pipeline proves it ran,")
        print("                    not that the pod answering you is your commit")
    print()
    print("Then prove the whole thing can fail: run it against the version")
    print("before your change and check that it does.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the checks and print them, but write no configuration",
    )
    parser.add_argument(
        "--draft-stage2",
        action="store_true",
        help="print a stage2 draft derived from this repository, and write nothing",
    )
    parser.add_argument(
        "--stage1",
        action="append",
        metavar="COMMAND",
        help="run this project-owned Stage 1 command; repeat for more commands",
    )
    parser.add_argument(
        "--artifact-kind",
        choices=sorted(STAGE2_HINT_BY_KIND),
        help="override artifact detection after inspecting how this project ships",
    )
    parser.add_argument(
        "--defer-artifact-kind",
        action="store_true",
        help="save passing Stage 1 checks but wait for critic and user confirmation before choosing the delivery kind",
    )
    parser.add_argument(
        "--confirm-artifact-kind",
        choices=sorted(STAGE2_HINT_BY_KIND),
        metavar="KIND",
        help="finalize a kind previously deferred by guided setup without rerunning Stage 1",
    )
    parser.add_argument(
        "--surfaces",
        metavar="A,B",
        help="the delivery surfaces confirmed in this run, comma separated; "
             "pass with --confirm-artifact-kind",
    )
    parser.add_argument(
        "--language",
        choices=("en", "ru"),
        help="persist the selected operator-facing language in gopnik.json",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        metavar="SECONDS",
        help="wall-clock limit for each Stage 1 command (default: 120)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="compare the recorded Stage 1 with this tree and report; write nothing",
    )
    parser.add_argument(
        "--add-stage1",
        action="append",
        metavar="COMMAND",
        help="run this command and, if it passes, add it to the recorded Stage 1",
    )
    parser.add_argument("--dir", default=".", help="project directory")
    args = parser.parse_args(argv)

    if args.timeout_seconds < 1:
        parser.error("--timeout-seconds must be at least 1")

    root = pathlib.Path(args.dir).resolve()
    config = resolve_config(root)

    if args.refresh or args.add_stage1:
        if args.refresh and args.add_stage1:
            parser.error(
                "--refresh writes nothing by contract; --add-stage1 is how an "
                "answer reaches the file. Run them one after the other"
            )
        # `--surfaces` joins this list because it arrived on the same merge:
        # it is a setup option, and revisiting an existing record is not setup.
        if (args.stage1 or args.artifact_kind or args.defer_artifact_kind
                or args.draft_stage2 or args.language or args.confirm_artifact_kind
                or args.surfaces):
            parser.error(
                "--refresh and --add-stage1 revisit an existing record; "
                "do not combine them with setup options"
            )
        if args.refresh:
            return report_refresh(root)
        return apply_stage1(
            root, args.add_stage1, timeout=args.timeout_seconds, dry=args.check
        )

    surfaces = None
    if args.surfaces is not None:
        if not args.confirm_artifact_kind:
            parser.error(
                "--surfaces records what the confirmation step confirmed; "
                "pass it with --confirm-artifact-kind"
            )
        surfaces = parse_surfaces(args.surfaces)
        if not surfaces:
            parser.error("--surfaces was given without a surface in it")

    if args.confirm_artifact_kind:
        incompatible = (
            args.stage1
            or args.artifact_kind
            or args.defer_artifact_kind
            or args.draft_stage2
            or args.language
        )
        if incompatible:
            parser.error(
                "--confirm-artifact-kind is a separate finalization step; "
                "do not combine it with setup options"
            )
        try:
            confirmed = confirm_artifact_kind(
                root, args.confirm_artifact_kind, dry=args.check, surfaces=surfaces
            )
        except ValueError as exc:
            print(f"Cannot confirm artifact kind: {exc}.")
            return 2
        action = "Would confirm" if args.check else "Confirmed"
        print(
            f"{action} artifact kind '{args.confirm_artifact_kind}' in {confirmed.name}. "
            "Stage 1 checks were preserved and not rerun."
        )
        if surfaces:
            print(
                f"{action} delivery surfaces: " + ", ".join(surfaces) + ". "
                "stage2 owes each of them a step, or a written reason why it "
                "has none."
            )
        return 0

    if args.defer_artifact_kind and args.artifact_kind:
        parser.error(
            "--defer-artifact-kind and --artifact-kind are mutually exclusive"
        )

    runners, kind = detect(root, detect_kind=not args.defer_artifact_kind)
    kind = args.artifact_kind or kind

    if args.draft_stage2:
        return print_draft(root, config, kind)

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

        # Setup is not finished while the delivery kind is still pending, and a
        # check the documented route misses is often only found later — while
        # classifying surfaces, which happens after this point. #76: until this
        # existed the skill told a run to go back and add it, and the helper
        # answered "Stage 1 already set up", exit 0, changing nothing. An
        # instruction that fails green is worse than no instruction. Extending
        # is allowed only while the kind is pending: once it is confirmed the
        # configuration belongs to the project, and this is not the way to edit
        # it.
        extending_pending_stage1 = False
        if is_pending_kind_config(existing):
            recorded = [str(command) for command in verification.get("stage1") or []]
            asked = [str(command) for command in args.stage1 or []]
            extending_pending_stage1 = bool(asked) and asked != recorded
            if not extending_pending_stage1:
                language_saved = (
                    args.language is not None
                    and existing.get("language") != args.language
                )
                if language_saved and not args.check:
                    existing = dict(existing)
                    existing["language"] = args.language
                    config.write_text(
                        json.dumps(existing, indent=2) + "\n", encoding="utf-8"
                    )
                print("Stage 1 already set up. Delivery surfaces still need confirmation.")
                return 0

        if not extending_pending_stage1 and not is_the_installers_copy(existing):
            language_saved = args.language is not None and existing.get("language") != args.language
            if language_saved and not args.check:
                existing = dict(existing)
                existing["language"] = args.language
                config.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
            # Verification is never modified. An explicitly selected language
            # is independent onboarding state, so it may be updated without
            # claiming ownership of the hand-written verification block.
            if language_saved and not args.check:
                print(f"Already configured; saved language '{args.language}'. Verification was not changed.")
            else:
                print("Already configured, so nothing was changed. How it stands:")
            print()
            listed = verification.get("stage1") or []
            still_failing = not listed
            if listed:
                print("Checks it lists:")
                for cmd in listed:
                    code, out = run(str(cmd), root, timeout=args.timeout_seconds)
                    if code == 0:
                        print(f"  ok       {cmd}")
                    else:
                        first = out.splitlines()[0][:50] if out else "no output"
                        label = "too slow" if code == 124 else "FAILING "
                        print(f"  {label} {cmd} — {first}")
                        still_failing = True
            else:
                print("It lists no checks at all, so there is nothing to run.")
            if args.defer_artifact_kind:
                if still_failing:
                    print()
                    print("Stage 1 is not green, so delivery surfaces were not classified.")
                    return 2
                if not args.check:
                    body = dict(existing)
                    pending = dict(verification)
                    pending["//artifact_kind"] = PENDING_KIND_COMMENT
                    body["verification"] = pending
                    config.write_text(
                        json.dumps(body, indent=2) + "\n", encoding="utf-8"
                    )
                print()
                print("Stage 1 already set up. Delivery surfaces still need confirmation.")
                return 0
            if runners and not project_instructions(root):
                # Only what the configuration does not already have. Offering a
                # project a check it already lists reads as a suggestion, costs
                # a second run of the command, and on a project with one check
                # printed that check twice under two different headings.
                already = {str(c) for c in listed}
                found = [c for c, code, _ in build_checks(
                    runners, root, timeout=args.timeout_seconds
                )
                         if code == 0 and c not in already]
                if found:
                    print()
                    print("Found here and ran, not in its list:")
                    for cmd in found:
                        print(f"  ok       {cmd}")
            return report_state(root, verification.get("artifact_kind") or kind or "library",
                                first_run=False)

    # Only now, because a project this cannot recognise may already be
    # configured by hand — and those are exactly the projects that most need
    # the answer, since detection is why they are hand-configured.
    explicit = args.stage1 or []
    instructions = project_instructions(root)

    if instructions and not explicit:
        names = ", ".join(str(path.relative_to(root)) for path in instructions)
        print(f"Project instructions found: {names}.")
        print("Nothing was run or changed. Read those rules, then pass only their")
        print("project-owned checks with --stage1 COMMAND (repeat as needed).")
        return 2

    if not runners and not explicit:
        print("I could not find this project's Stage 1 check.")
        print("Nothing was changed. Tell me the project-owned fast local check command.")
        return 2

    if kind is None and not args.defer_artifact_kind:
        print("I could not tell what kind of project this is.")
        print("Nothing was changed. Tell me how someone else gets this — a running")
        print("service, an installed package, or a command they type.")
        return 2

    results = (
        run_explicit_checks(explicit, root, timeout=args.timeout_seconds)
        if explicit
        else build_checks(runners, root, timeout=args.timeout_seconds)
    )
    passing, missing, timed_out, broken = sort_results(results, explicit=bool(explicit))

    if explicit and (missing or timed_out or broken):
        print("A project-owned Stage 1 command did not pass, so setup is blocked.")
        for cmd in passing:
            print(f"  ok       {cmd}")
        for cmd, out in broken:
            first = out.splitlines()[0][:60] if out else "no output"
            print(f"  FAILING  {cmd} — {first}")
        for cmd in missing:
            print(f"  absent   {cmd} — not installed here")
        for cmd in timed_out:
            print(f"  too slow {cmd} — gave up waiting")
        print("Nothing was changed. Fix the baseline, or confirm a different command set.")
        return 2

    if not passing:
        found_as = "project-defined" if explicit else runners[0]["name"]
        print(f"I found a {found_as} project but none of its checks pass here.")
        for cmd, out in broken[:3]:
            first = out.splitlines()[0][:60] if out else "no output"
            print(f"  {cmd} — failed: {first}")
        for cmd in missing[:3]:
            print(f"  {cmd} — not installed here")
        print("Nothing was changed. Fix one of those, or tell me the right command.")
        return 2

    written = write_config(
        root,
        kind,
        passing,
        args.check,
        existing,
        args.language,
        defer_artifact_kind=args.defer_artifact_kind,
    )

    if args.defer_artifact_kind:
        print("Stage 1 set up. Delivery surfaces still need confirmation.")
    elif explicit:
        print(f"Set up: project-defined {kind} — change that if it is wrong.")
    elif len(runners) > 1:
        others = ", ".join(r["name"] for r in runners[1:])
        print(f"Set up: {runners[0]['name']} {kind} (also here: {others}) — change that if it is wrong.")
    else:
        print(f"Set up: {runners[0]['name']} {kind} — change that if it is wrong.")
    print()
    print("Checks I ran here and wrote down:")
    for cmd in passing:
        print(f"  ok       {cmd}")
    for cmd, _ in broken:
        print(f"  FAILING  {cmd} — ran and did not pass, left out")
    for cmd in missing:
        print(f"  absent   {cmd} — not installed here, left out")
    for cmd in timed_out:
        print(f"  too slow {cmd} — gave up waiting, left out")
    if args.check:
        print()
        print(f"Nothing was written. Drop --check to save this to {written}.")
        return 0

    if args.defer_artifact_kind:
        return 0

    return report_state(root, kind, first_run=True)


if __name__ == "__main__":
    sys.exit(main())
