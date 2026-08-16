#!/usr/bin/env python3
"""Tests for the cerberus hooks.

A verification gate that is itself unverified would be self-refuting, and the
failure mode that matters is the quiet one: a gate that never fires looks
exactly like a project where nothing is ever wrong.

Run with: python3 -m pytest tests/ -q   (or: python3 tests/test_hooks.py)
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "plugins" / "cerberus" / "hooks"
sys.path.insert(0, str(HOOKS))

from cerberus_config import Config  # noqa: E402


def run_hook(script: str, payload: dict) -> tuple[int, str]:
    # CLAUDE_PROJECT_DIR is read by the hooks in preference to the payload's
    # cwd, so an inherited one makes every fixture below address the real
    # project instead of its temporary directory — the suite then fails, and
    # writes fixture paths into the real marker on the way. GitHub Actions does
    # not set the variable, so leaving it inherited kept CI green while the
    # suite was broken for anyone running it inside a session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    cwd = payload.get("cwd")
    if cwd:
        env["CLAUDE_PROJECT_DIR"] = str(cwd)
    proc = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, proc.stdout.strip()


def test_an_inherited_project_dir_does_not_leak_into_a_fixture():
    # The regression this guard exists for: with CLAUDE_PROJECT_DIR pointing at
    # a different project, a hook run against a fixture must still act on the
    # fixture, and must leave the other project untouched.
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as other:
        tmp, elsewhere = pathlib.Path(d), pathlib.Path(other)
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(elsewhere)}
        subprocess.run(
            [sys.executable, str(HOOKS / "cerberus_mark.py")],
            input=json.dumps({"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}}),
            capture_output=True,
            text=True,
            env={**env, "CLAUDE_PROJECT_DIR": str(tmp)},
        )
        assert (tmp / ".claude" / ".cerberus-pending").exists()
        assert not (elsewhere / ".claude" / ".cerberus-pending").exists(), (
            "a hook must never write into a project it was not pointed at"
        )


def transcript(tmp: pathlib.Path, text: str) -> str:
    path = tmp / "transcript.jsonl"
    path.write_text(
        json.dumps({"role": "assistant", "message": {"content": text}}) + "\n",
        encoding="utf-8",
    )
    return str(path)


# ---------------------------------------------------------------- marking


def test_marks_source_file():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        rc, _ = run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}})
        assert rc == 0
        marker = tmp / ".claude" / ".cerberus-pending"
        assert marker.exists(), "editing source code must set the marker"
        assert "app/service.py" in marker.read_text(encoding="utf-8")


def test_does_not_mark_tests_docs_or_agent_config():
    # These cannot change runtime behaviour, and marking them would make the
    # gate fire during ordinary work until people learn to ignore it.
    for path in (
        "app/tests/test_service.py",
        "src/service.test.ts",
        "docs/architecture.md",
        ".claude/settings.json",
        "README.md",
    ):
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": path}})
            assert not (tmp / ".claude" / ".cerberus-pending").exists(), path


def test_does_not_mark_files_outside_the_project():
    # Reproduced 2026-08-15: writing a note to a scratch directory armed this
    # project's gate, because nothing asked whether the path was in the project.
    #
    # Every path below is one that the *old* code marked. An earlier version of
    # this test also listed a `.md` under a `.claude/` directory; that assertion
    # was inert — the default ignore patterns already contain "/.claude/", so it
    # could not fail under either implementation. An assertion that cannot fail
    # is worse than no assertion, because it reads as coverage.
    #
    # Every assertion runs against a marker that already has an entry, and the
    # in-project write is re-checked afterwards, so a hook that marks nothing at
    # all cannot pass this.
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as elsewhere:
        tmp = pathlib.Path(d)
        marker = tmp / ".claude" / ".cerberus-pending"

        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}})
        assert marker.exists(), "sentinel: an in-project edit must still mark"
        before = marker.read_text(encoding="utf-8")

        outside = [
            str(pathlib.Path(elsewhere) / "note.py"),
            str(pathlib.Path(elsewhere) / "nested" / "deep.py"),
            "../escaped.py",
            "../../also_escaped.py",
            "C:/windows/style.py",
        ]
        cfg_old_would_mark = Config(tmp)
        for path in outside:
            run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": path}})
            assert marker.read_text(encoding="utf-8") == before, path
            assert not cfg_old_would_mark.is_source_file(path), path

        # And the hook is still alive at the end, rather than having been
        # switched off by the change under test.
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/other.py"}})
        assert "app/other.py" in marker.read_text(encoding="utf-8")


def test_a_symlinked_package_inside_the_project_still_marks():
    # The vendored layout: proj/packages/foo is a symlink to a shared directory
    # outside the tree. The file is part of the project and editing it changes
    # what the project ships, so it must mark. Resolving the path and comparing
    # only that would call it foreign — this is the cell issue #5's matrix said
    # had to be picked and justified, and it is the one a purely resolved
    # implementation gets wrong.
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        root = base / "proj"
        (root / "packages").mkdir(parents=True)
        shared = base / "shared" / "foo"
        shared.mkdir(parents=True)
        (shared / "x.py").write_text("", encoding="utf-8")
        (root / "packages" / "foo").symlink_to(shared)

        cfg = Config(root)
        assert cfg.is_source_file(str(root / "packages" / "foo" / "x.py"))
        assert cfg.is_source_file("packages/foo/x.py")


def test_a_project_reached_through_a_symlink_still_marks():
    # The mirror case: the root itself is a symlink. Comparing only lexically
    # would call the entire tree foreign — which is why neither comparison is
    # used alone.
    with tempfile.TemporaryDirectory() as d:
        base = pathlib.Path(d)
        real = base / "real"
        (real / "app").mkdir(parents=True)
        (real / "app" / "x.py").write_text("", encoding="utf-8")
        link = base / "link"
        link.symlink_to(real)

        assert Config(link).is_source_file(str(real / "app" / "x.py"))
        assert Config(real).is_source_file(str(link / "app" / "x.py"))


def test_marks_an_absolute_path_inside_the_project():
    # The harness sends absolute paths. Rejecting anything absolute would be an
    # easy way to pass the test above while disabling the gate entirely.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        inside = tmp / "app" / "service.py"
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": str(inside)}})
        marker = tmp / ".claude" / ".cerberus-pending"
        assert marker.exists(), "an absolute path inside the project must mark"
        assert str(inside) in marker.read_text(encoding="utf-8")


def test_marker_accumulates_without_duplicating():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        for path in ("app/a.py", "app/b.py", "app/a.py"):
            run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": path}})
        lines = (tmp / ".claude" / ".cerberus-pending").read_text(encoding="utf-8").split()
        assert sorted(lines) == ["app/a.py", "app/b.py"]


# ------------------------------------------------------------- other agents


def test_a_codex_edit_is_recorded():
    # Codex routes edits through apply_patch and the payload shape is not
    # documented, so the path is scraped and then corroborated against disk.
    # Unverified against a real Codex session — see #27.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / "app").mkdir()
        (tmp / "app" / "service.py").write_text("x = 1\n", encoding="utf-8")
        run_hook("cerberus_mark.py", {
            "cwd": str(tmp),
            "hook_event_name": "PostToolUse",
            "tool_name": "apply_patch",
            "tool_input": {"input": "*** Update File: app/service.py\n@@\n-x = 1\n+x = 2\n"},
        })
        marker = tmp / ".claude" / ".cerberus-pending"
        assert marker.exists() and "app/service.py" in marker.read_text(encoding="utf-8")


def test_running_a_file_is_not_editing_it():
    # The trap in scraping: `python3 app/service.py` in a Bash command names a
    # source file that was RUN. Marking it would arm the gate for work nobody
    # did, so extraction is gated on the tool name.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / "app").mkdir()
        (tmp / "app" / "service.py").write_text("x = 1\n", encoding="utf-8")
        run_hook("cerberus_mark.py", {
            "cwd": str(tmp),
            "tool_name": "Bash",
            "tool_input": {"command": "python3 app/service.py"},
        })
        assert not (tmp / ".claude" / ".cerberus-pending").exists()


def test_a_path_that_is_only_prose_is_not_recorded():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {
            "cwd": str(tmp),
            "tool_name": "apply_patch",
            "tool_input": {"input": "see also legacy/gone.py, removed last year"},
        })
        assert not (tmp / ".claude" / ".cerberus-pending").exists()


def test_the_claim_can_come_from_the_payload():
    # Codex hands the Stop hook `last_assistant_message`; Claude Code does not.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/x.py"}})
        _, out = run_hook("cerberus_gate.py", {
            "cwd": str(tmp),
            "hook_event_name": "Stop",
            "last_assistant_message": "done, it works",
        })
        # Asserted before parsing: an empty result is a gap, not a pass, and
        # letting json.loads raise turned a clear failure into a traceback that
        # took the rest of the run down with it.
        assert out, "nothing was returned — the payload's message was not read"
        assert json.loads(out)["decision"] == "block"


def test_a_continued_turn_is_not_blocked_again():
    # Blocking a Stop on Codex feeds a continuation prompt back as new user
    # input. Blocking again from there loops forever, so the flag saying the
    # turn was already continued has to end it.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/x.py"}})
        rc, out = run_hook("cerberus_gate.py", {
            "cwd": str(tmp),
            "hook_event_name": "Stop",
            "last_assistant_message": "done, it works",
            "stop_hook_active": True,
        })
        assert rc == 0 and out == "", "a continued turn was blocked again — that is the loop"


def test_a_codex_project_keeps_its_state_in_codex():
    # A Codex-only project should not have a .claude directory created for it.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / ".codex").mkdir()
        (tmp / "app").mkdir()
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/x.py"}})
        assert (tmp / ".codex" / ".cerberus-pending").exists(), "state went somewhere else"
        assert not (tmp / ".claude").exists(), "a .claude directory was invented"


# ------------------------------------------------------------------ gate


def test_gate_is_silent_without_a_marker():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        rc, out = run_hook(
            "cerberus_gate.py",
            {"cwd": str(tmp), "transcript_path": transcript(tmp, "it works, all green")},
        )
        assert rc == 0 and out == "", "nothing unverified — the turn must end freely"


def test_gate_does_not_block_ongoing_work():
    # The single most important property: a gate that interrupts normal work
    # gets switched off, and a gate that is off protects nothing.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}})
        rc, out = run_hook(
            "cerberus_gate.py",
            {
                "cwd": str(tmp),
                "transcript_path": transcript(
                    tmp, "Deployed to dev, now running the end-to-end check."
                ),
            },
        )
        assert rc == 0 and out == "", "mid-work turns must not be blocked"


def test_gate_blocks_a_readiness_claim():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}})
        rc, out = run_hook(
            "cerberus_gate.py",
            {"cwd": str(tmp), "transcript_path": transcript(tmp, "Fixed — it works now.")},
        )
        payload = json.loads(out)
        assert payload["decision"] == "block"
        assert "app/service.py" in payload["reason"], "the block must name what is unverified"


def test_gate_blocks_the_russian_claim_too():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}})
        _, out = run_hook(
            "cerberus_gate.py",
            {"cwd": str(tmp), "transcript_path": transcript(tmp, "Готово, всё зелёное.")},
        )
        assert json.loads(out)["decision"] == "block"


def test_clearing_the_marker_lets_the_claim_through():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": "app/service.py"}})
        (tmp / ".claude" / ".cerberus-pending").unlink()
        rc, out = run_hook(
            "cerberus_gate.py",
            {"cwd": str(tmp), "transcript_path": transcript(tmp, "it works")},
        )
        assert rc == 0 and out == ""


# ---------------------------------------------------------------- config


def test_config_narrows_watched_paths():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / ".claude").mkdir()
        (tmp / ".claude" / "cerberus.json").write_text(
            json.dumps({"watch_paths": ["backend/"]}), encoding="utf-8"
        )
        cfg = Config.load(tmp)
        assert cfg.is_source_file("backend/app/service.py")
        assert not cfg.is_source_file("frontend/app/service.py")


def test_malformed_config_falls_back_to_defaults_rather_than_disabling():
    # A typo in configuration must not silently switch verification off.
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / ".claude").mkdir()
        (tmp / ".claude" / "cerberus.json").write_text("{not json", encoding="utf-8")
        cfg = Config.load(tmp)
        assert cfg.is_source_file("app/service.py")
        assert cfg.claims_readiness("it works")


def test_claim_patterns_can_be_replaced():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / ".claude").mkdir()
        (tmp / ".claude" / "cerberus.json").write_text(
            json.dumps({"claim_patterns": [r"\bshipped\b"]}), encoding="utf-8"
        )
        cfg = Config.load(tmp)
        assert cfg.claims_readiness("shipped")
        assert not cfg.claims_readiness("it works")


def test_shipped_example_config_does_not_narrow_the_gate():
    """Copying cerberus.example.json verbatim must not weaken anything.

    The example is the first thing a new project copies. If it sets the tuning
    keys, the gate silently becomes narrower than the documented defaults - and
    a gate that is quietly weaker than advertised is the failure this whole
    skill is about.
    """
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        (tmp / ".claude").mkdir()
        example = (ROOT / "cerberus.example.json").read_text(encoding="utf-8")
        (tmp / ".claude" / "cerberus.json").write_text(example, encoding="utf-8")
        cfg = Config.load(tmp)

        defaults = Config(tmp)
        assert cfg.claim_patterns == defaults.claim_patterns, "example must not replace claim_patterns"
        assert cfg.source_extensions == defaults.source_extensions, "example must not narrow source_extensions"
        assert cfg.ignore_patterns == defaults.ignore_patterns, "example must not replace ignore_patterns"
        assert cfg.watch_paths == [], "example must not restrict watched paths"
        # And it still behaves: a Russian claim is caught with the example in place.
        assert cfg.claims_readiness("готово")
        assert cfg.is_source_file("app/service.rb")


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
