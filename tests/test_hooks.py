#!/usr/bin/env python3
"""Tests for the cerberus hooks.

A verification gate that is itself unverified would be self-refuting, and the
failure mode that matters is the quiet one: a gate that never fires looks
exactly like a project where nothing is ever wrong.

Run with: python3 -m pytest tests/ -q   (or: python3 tests/test_hooks.py)
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
HOOKS = ROOT / "hooks"
sys.path.insert(0, str(HOOKS))

from cerberus_config import Config  # noqa: E402


def run_hook(script: str, payload: dict) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(HOOKS / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout.strip()


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


def test_marker_accumulates_without_duplicating():
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        for path in ("app/a.py", "app/b.py", "app/a.py"):
            run_hook("cerberus_mark.py", {"cwd": str(tmp), "tool_input": {"file_path": path}})
        lines = (tmp / ".claude" / ".cerberus-pending").read_text(encoding="utf-8").split()
        assert sorted(lines) == ["app/a.py", "app/b.py"]


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
    print(f"\n{'FAILED' if failures else 'all tests passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
