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


def test_the_installer_command_runs():
    """The one command on this page a shell can run, extracted and executed.

    It fetches over the network by design: that is what the reader will do, and
    the difference between the script beside the page and the script the page
    points at is exactly where an install breaks.
    """
    blocks = console_blocks(section(README.read_text(encoding="utf-8"), "## Quick start"))
    assert len(blocks) == 1, f"expected one runnable command, found {len(blocks)}"
    command = blocks[0]
    assert command.count("\n") == 0, "it must be one line to copy: " + command

    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "tests").mkdir()
        (root / "pyproject.toml").write_text(
            '[project]\nname = "d"\nversion = "1"\n', encoding="utf-8"
        )
        (root / "tests" / "test_demo.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8"
        )
        proc = subprocess.run(
            command, shell=True, cwd=str(root), capture_output=True, text=True, timeout=600,
            env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
        )
        assert proc.returncode == 0, command + "\n" + proc.stdout + proc.stderr
        assert (root / ".claude" / "cerberus.json").exists(), proc.stdout
        assert "was refused" in proc.stdout, proc.stdout


def test_the_agent_commands_are_the_documented_ones():
    """Neither of these can run here.

    The plugin pair needs credentials and a session. `$skill-installer` exists
    only inside Codex and is not a program on any machine that runs these
    tests — it has never been executed by anything in this repository, and the
    URL it is given is asserted to resolve rather than assumed to.

    So their text is pinned, and the verdict says they are unverified rather
    than letting a shape check read as coverage.
    """
    blocks = shell_blocks(section(README.read_text(encoding="utf-8"), "## Quick start"))
    assert len(blocks) == 2, f"expected the plugin pair and the Codex line, found {len(blocks)}"
    plugin = [line.strip() for line in blocks[0].splitlines() if line.strip()]
    assert plugin == [
        "/plugin marketplace add concordloom/cerberus",
        "/plugin install cerberus@concordloom",
    ], plugin
    codex = blocks[1].strip()
    assert codex.startswith("$skill-installer install https://github.com/concordloom/cerberus/"), codex


def test_the_url_the_codex_command_is_given_resolves():
    """The half of the Codex line that *can* be checked.

    Whether `$skill-installer` accepts it is unknown here; whether the thing it
    is pointed at exists is not, and a dead URL is the likelier of the two
    failures — the repository was renamed today.
    """
    import urllib.request

    blocks = shell_blocks(section(README.read_text(encoding="utf-8"), "## Quick start"))
    url = blocks[1].split()[-1]
    raw = url.replace("https://github.com/", "https://raw.githubusercontent.com/").replace(
        "/tree/", "/"
    ) + "/SKILL.md"
    with urllib.request.urlopen(raw, timeout=30) as response:
        assert response.status == 200, raw
        assert b"name: cerberus" in response.read(400), raw


def test_the_quick_start_shows_what_success_looks_like():
    body = section(README.read_text(encoding="utf-8"), "## Quick start")
    assert "```text" in body, "the reader is told to run something with no idea what it prints"
    assert "refused" in body, body


def test_the_quick_start_fits_above_the_fold():
    body = section(README.read_text(encoding="utf-8"), "## Quick start")
    lines = [line for line in body.splitlines() if line.strip()]
    # It carries three install paths now, so the bound is about staying
    # scannable rather than about fitting a terminal.
    assert len(lines) <= 35, f"{len(lines)} lines is not a quick start"


def test_three_heads_means_one_thing():
    # The stages own the phrase: the hero image colours three heads green, amber
    # and red, which are Stage 0, 1 and 2. A section claiming it for the three
    # skills left the picture illustrating nothing.
    for path, pattern in ((README, r"^## .*[Tt]hree heads"), (README_RU, r"^## .*[Тт]ри головы")):
        text = path.read_text(encoding="utf-8")
        found = re.findall(pattern, text, re.M)
        assert len(found) == 1, f"{path.name}: {found}"


def test_the_skills_do_not_claim_to_be_heads():
    # This guard used to read only the READMEs, so it enforced one meaning while
    # `setup/SKILL.md` opened with "The third head" and shipped the other. Both
    # definitions were in the product at once, and the test that existed to
    # prevent exactly that could not see half of it.
    for skill in sorted((ROOT / "plugins").glob("*/skills/*/SKILL*.md")):
        text = skill.read_text(encoding="utf-8").lower()
        for phrase in ("third head", "second head", "first head", "третья голова",
                       "вторая голова", "первая голова"):
            assert phrase not in text, f"{skill}: '{phrase}' — heads are the stages"


def test_the_page_does_not_read_as_a_list_of_lists():
    # Three tables inside two screens made the eye stop resolving them as
    # separate things: the one that asks the reader to decide something was the
    # middle stripe, which gets the least attention.
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        sections = re.split(r"^## ", text, flags=re.M)[1:]
        with_tables = [s.splitlines()[0] for s in sections if re.search(r"^\|.*\|$", s, re.M)]
        assert len(with_tables) <= 2, f"{path.name}: tables in {with_tables}"
        titles = [s.splitlines()[0] for s in sections]
        for a, b in zip(titles, titles[1:]):
            assert not (a in with_tables and b in with_tables), (
                f"{path.name}: consecutive tables in '{a}' and '{b}'"
            )


def test_the_boundary_table_matches_the_documented_kinds():
    # The README listed four of the seven artifact kinds the example config
    # documents, so a reader shipping a migration or a prompt concluded the tool
    # was not for them.
    example = (ROOT / "cerberus.example.json").read_text(encoding="utf-8")
    kinds = re.search(r"artifact_kind: ([^\"]+)", example).group(1)
    documented = {k.strip().rstrip(".") for k in kinds.split("|")}
    rows = section(README.read_text(encoding="utf-8"), "## The one thing to configure")
    listed = re.findall(r"^\| a[n]? ([^|]+?) *\|", rows, re.M)
    assert len(listed) >= len(documented) - 1, f"{len(listed)} rows for {len(documented)} kinds: {listed}"


def test_the_page_says_how_to_switch_it_off():
    # tests/test_setup.py already demands this of the setup output. The front
    # door — where someone decides whether to install a thing that intercepts
    # every turn — did not say it at all.
    for path, phrases in (
        (README, ("switch it off", "turn it off", "uninstall")),
        (README_RU, ("выключить", "удалите")),
    ):
        text = path.read_text(encoding="utf-8").lower()
        assert any(p in text for p in phrases), path.name


def test_the_page_does_not_claim_a_mechanism_that_does_not_exist():
    # It said the record is "cleared by one thing: a READY verdict". Nothing in
    # the hooks clears it — the agent deletes the file. Claiming a mechanism
    # this project does not have, on the page that argues against exactly that,
    # was the worst sentence here.
    hooks = (ROOT / "plugins" / "cerberus" / "hooks")
    clears = [h.name for h in hooks.glob("cerberus_*.py")
              if h.name != "cerberus_setup.py" and "unlink" in h.read_text(encoding="utf-8")]
    assert not clears, f"a hook clears the marker now — the README may say so: {clears}"
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8").lower()
        assert "cleared by one thing" not in text, path.name


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


def test_installing_is_explained_in_exactly_one_place():
    # The page had install instructions in two places sixty lines apart, with
    # the skills described twice between them. There is now no separate install
    # section at all: everything that installs anything is in the quick start,
    # and this fails if a second home for it reappears.
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", text, re.M)
        installish = [h for h in headings if re.search(r"[Ii]nstall|[Уу]станов", h)]
        assert not installish, f"{path.name}: installing has its own section again: {installish}"
        quick = section(text, "## Quick start") if "## Quick start" in text else section(
            text, "## Быстрый старт"
        )
        assert "plugin install" in quick and "skill-installer" in quick, path.name


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
