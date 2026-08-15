#!/usr/bin/env python3
"""Tests for the README, which is where a stranger meets this project.

The one that matters extracts the quick start's command **from the file** and
runs it. A test that retypes the command proves the command works; it does not
prove the page is right, and the page is the artifact. A quick start whose
commands were never run is the failure this repository is about, printed on its
own front door.

Run with: python3 tests/test_readme.py
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
README_RU = ROOT / "README.ru.md"


def section(text: str, heading: str) -> str:
    """The body of one `## heading`, up to the next one."""
    start = text.index(heading)
    rest = text[start + len(heading):]
    end = rest.find("\n## ")
    return rest if end == -1 else rest[:end]


def fenced(text: str) -> list[tuple[str, str]]:
    """(language, body) for each fenced block, parsed rather than matched.

    A regex over fences cannot tell an opening fence from a closing one: an
    earlier version matched from the *closing* fence of a tagged block to the
    opening of the next, and counted the prose between them as a command.
    """
    blocks, language, buffer, inside = [], "", [], False
    for line in text.splitlines():
        if line.startswith("```"):
            if inside:
                blocks.append((language, "\n".join(buffer).strip()))
                language, buffer, inside = "", [], False
            else:
                language, inside = line[3:].strip(), True
            continue
        if inside:
            buffer.append(line)
    return blocks


def shell_blocks(text: str) -> list[str]:
    """Untagged blocks: what the reader types into an agent, not into a shell."""
    return [body for lang, body in fenced(text) if lang == ""]


def console_blocks(text: str) -> list[str]:
    """Blocks a shell can run, and therefore blocks a test can run."""
    return [body for lang, body in fenced(text) if lang in ("console", "sh")]


def test_the_codex_quick_start_command_runs():
    """Extracted from README.md, not retyped, and executed for real.

    It fetches over the network by design: that is what the reader will do, and
    the difference between what the page says and what the registry serves is
    exactly where an install breaks.
    """
    blocks = console_blocks(section(README.read_text(encoding="utf-8"), "## Quick start"))
    assert len(blocks) == 1, f"expected one runnable command, found {len(blocks)}"
    command = blocks[0]
    assert command.count("\n") == 0, "it must be one line to copy: " + command

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        proc = subprocess.run(
            command, shell=True, cwd=str(root), capture_output=True, text=True, timeout=600,
        )
        assert proc.returncode == 0, command + "\n" + proc.stdout + proc.stderr
        installed = sorted(p.parent.name for p in (root / ".agents" / "skills").rglob("SKILL.md"))
        assert installed == ["cerberus", "critic", "setup"], installed


def test_the_claude_quick_start_is_the_documented_plugin_pair():
    """The plugin commands cannot run here — they need credentials and a
    session — so their shape is asserted instead, and the verdict says they are
    verified by hand rather than pretending this covers them."""
    blocks = shell_blocks(section(README.read_text(encoding="utf-8"), "## Quick start"))
    assert len(blocks) == 1, f"expected one plugin block, found {len(blocks)}"
    lines = [line.strip() for line in blocks[0].splitlines() if line.strip()]
    assert lines == [
        "/plugin marketplace add concordloom/cerberus",
        "/plugin install cerberus@concordloom",
    ], lines


def test_the_quick_start_shows_what_success_looks_like():
    body = section(README.read_text(encoding="utf-8"), "## Quick start")
    assert "```text" in body, "the reader is told to run something with no idea what it prints"
    assert "refused" in body, body


def test_the_quick_start_fits_above_the_fold():
    body = section(README.read_text(encoding="utf-8"), "## Quick start")
    lines = [line for line in body.splitlines() if line.strip()]
    assert len(lines) <= 25, f"{len(lines)} lines is not a quick start"


def test_three_heads_means_one_thing():
    # The stages own the phrase: the hero image colours three heads green,
    # amber and red, which are Stage 0, 1 and 2. A second section claiming it
    # for the three skills left the picture illustrating nothing.
    for path, pattern in ((README, r"^## .*[Tt]hree heads"), (README_RU, r"^## .*[Тт]ри головы")):
        text = path.read_text(encoding="utf-8")
        found = re.findall(pattern, text, re.M)
        assert len(found) == 1, f"{path.name}: {found}"


def test_both_languages_have_the_same_sections():
    # check_parity.py compares the skills, not the READMEs, so these two can
    # drift with nothing noticing — which is how one language gets a fix.
    en = re.findall(r"^## ", README.read_text(encoding="utf-8"), re.M)
    ru = re.findall(r"^## ", README_RU.read_text(encoding="utf-8"), re.M)
    assert len(en) == len(ru), f"{len(en)} sections in English, {len(ru)} in Russian"


def test_the_russian_text_has_no_stray_scripts():
    # A CJK character reached the Russian README through a bad edit and read as
    # a word. Nothing would have caught it: it is valid UTF-8 in a prose file.
    text = README_RU.read_text(encoding="utf-8")
    allowed = set("—…«»🟢🟡🔴\u00a0")
    stray = sorted({c for c in text if ord(c) > 0x2100 and c not in allowed})
    assert not stray, f"characters from another script: {stray}"


def test_the_install_section_is_the_only_one():
    # The page had install instructions in two places, sixty lines apart, with
    # the skills described twice between them.
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", text, re.M)
        installish = [h for h in headings if re.search(r"[Ii]nstall|[Уу]станов", h)]
        assert len(installish) == 1, f"{path.name}: {installish}"


def test_no_link_points_at_the_old_repository_name():
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        assert "cerberus-skill" not in text, path.name


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
