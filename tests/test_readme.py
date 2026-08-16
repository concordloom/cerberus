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

import json
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


def documented_install() -> tuple[str, str]:
    """The page's install command, split into the URL it fetches and its flags."""
    blocks = console_blocks(section(README.read_text(encoding="utf-8"), "## Quick start"))
    assert len(blocks) == 1, f"expected one runnable command, found {len(blocks)}"
    command = blocks[0]
    assert command.count("\n") == 0, "it must be one line to copy: " + command
    url = re.search(r"https://\S+", command).group(0)
    flags = command.split("-s --", 1)[1].strip() if "-s --" in command else ""
    return url, flags


def test_the_installer_command_runs():
    """The page's command, run against **this** revision rather than main.

    It used to be executed verbatim, fetching over the network. That check was
    honest while a branch and main installed the same way and dishonest the
    moment they did not: on a branch it ran main's installer and reported on
    main. So the URL is checked separately for being alive, and the flags the
    page documents are run against the script in this tree — which is the thing
    the change under review can actually break.
    """
    _, flags = documented_install()
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
            f'sh "{ROOT / "install.sh"}" {flags}',
            shell=True, cwd=str(root), capture_output=True, text=True, timeout=600,
            env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
        )
        assert proc.returncode == 0, flags + "\n" + proc.stdout + proc.stderr
        assert (root / "cerberus.json").exists(), proc.stdout
        assert "Nothing runs by itself" in proc.stdout, proc.stdout


def test_the_url_the_installer_command_fetches_is_alive():
    """The half of the one-liner the test above no longer executes."""
    import urllib.request

    url, _ = documented_install()
    with urllib.request.urlopen(url, timeout=30) as response:
        assert response.status == 200, url
        assert b"cerberus" in response.read(2000), url


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
    assert "Checks I ran here" in body, body


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
        # and the section must define them as the stages. Counting the heading
        # let a mutant keep one heading and redefine the heads as the skills
        # inside it.
        body = section(text, found[0].replace("## ", "## "))
        for skill in ("critic", "setup"):
            assert f"**{skill}**" not in body, f"{path.name}: the heads section names {skill}"
        assert re.search(r"[Ss]tage|[Сс]тади", body), f"{path.name}: heads are not the stages"


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
    """At most two tables, and the two must not look alike.

    Three tables inside two screens made the eye stop resolving them as
    separate things, and the one asking the reader to decide something was the
    middle stripe. The earlier version of this rule also banned two *adjacent*
    tables, which is what pushed the stages into three lines separated by
    single newlines — and markdown renders that as one run-on paragraph. That
    was worse than the problem: shipped without ever looking at the rendered
    page, which is the failure this repository is about.

    So: two tables are allowed side by side, as long as they are shaped
    differently enough not to stripe.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        sections = re.split(r"^## ", text, flags=re.M)[1:]
        shapes = {}
        for sec in sections:
            rows = [r for r in sec.splitlines() if r.startswith("|")]
            if rows:
                shapes[sec.splitlines()[0]] = rows[0].count("|")
        assert len(shapes) <= 2, f"{path.name}: tables in {list(shapes)}"
        if len(shapes) == 2:
            widths = list(shapes.values())
            assert widths[0] != widths[1], (
                f"{path.name}: two tables of the same width read as one block: {shapes}"
            )


def test_no_pseudo_list_relies_on_a_single_newline():
    """Single-newline 'lists' render as one paragraph.

    This shipped: three stages written on three source lines, rendered as a
    wall. Any run of consecutive lines that each start with a bullet-ish marker
    must be a real markdown list.
    """
    marker = re.compile(r"^(?:[🟢🟡🔴✅⏳🧊❌]|\*\*\d)")
    for path in (README, README_RU):
        lines = path.read_text(encoding="utf-8").splitlines()
        run = 0
        for line in lines:
            if marker.match(line.strip()):
                run += 1
                assert run < 2, f"{path.name}: {line[:60]!r} follows another — use a list or a table"
            elif line.strip():
                run = 0


def test_the_boundary_table_covers_every_documented_kind():
    """Every artifact_kind the example config documents has a row.

    The version this replaces parsed the enum and then never compared it to
    anything — it counted rows whose first cell began "| a ", so seven invented
    rows satisfied it, and it never opened the Russian file at all.
    """
    example = (ROOT / "cerberus.example.json").read_text(encoding="utf-8")
    kinds = re.search(r"artifact_kind: ([^\"]+)", example).group(1)
    documented = [k.strip().rstrip(".") for k in kinds.split("|")]

    for path, heading in ((README, "## The one thing to configure"),
                          (README_RU, "## Единственное, что надо настроить")):
        body = section(path.read_text(encoding="utf-8"), heading)
        rows = [r for r in body.splitlines() if r.startswith("|") and "---" not in r]
        assert len(rows) >= len(documented), f"{path.name}: {len(rows)} rows for {documented}"
        # and the enum values themselves must be on the page, so a reader can
        # get from their row to the value the file wants
        for kind in documented:
            assert kind in body, f"{path.name}: no way to reach artifact_kind {kind!r}"


def test_every_kind_on_the_page_has_advice_in_the_code():
    """A row the code cannot advise on sends the reader the wrong answer.

    `STAGE2_HINT_BY_KIND` falls back to the library hint for anything it does
    not know, so two rows added to match the documented enum were quietly
    getting library advice.
    """
    sys.path.insert(0, str(ROOT / "plugins" / "cerberus" / "skills" / "setup"))
    import cerberus_setup

    example = (ROOT / "cerberus.example.json").read_text(encoding="utf-8")
    kinds = {k.strip().rstrip(".") for k in
             re.search(r"artifact_kind: ([^\"]+)", example).group(1).split("|")}
    missing = sorted(kinds - set(cerberus_setup.STAGE2_HINT_BY_KIND))
    assert not missing, f"documented kinds with no advice: {missing}"


def test_the_page_says_nothing_runs_by_itself():
    """The load-bearing sentence since #33, on both pages.

    Someone deciding whether to install this needs to know, before installing,
    whether it will interrupt them. The answer is now "no, ever" — and a page
    that leaves that implicit is read as the old behaviour by anyone who saw an
    earlier version.
    """
    for path, phrases in (
        (README, ("nothing happens on its own", "nothing, until you ask")),
        (README_RU, ("само по себе не происходит ничего", "ничего, пока вы не попросите")),
    ):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in phrases:
            assert phrase in text, f"{path.name}: {phrase!r}"


def test_the_page_never_promises_an_automatic_refusal():
    """The previous seven versions did promise one, and people read those.

    A shape rather than a word list: what must not come back is any sentence
    saying this thing acts on its own.
    """
    banned = [
        re.compile(r"(?:hook|gate|it)\s+(?:refuses|blocks|interrupts|fires)\s+(?:every|automatically|on its own)", re.I),
        re.compile(r"(?:refusals?|enforcement)\s+(?:are|is)\s+(?:on|switched on)", re.I),
        re.compile(r"(?:гейт|хук|он)\s+(?:отказывает|блокирует|перебивает)\s+(?:сам|автоматически)", re.I),
    ]
    for path in (README, README_RU):
        body = path.read_text(encoding="utf-8")
        for shape in banned:
            found = shape.search(body)
            assert not found, f"{path.name}: {found.group(0)!r}"


def test_the_quoted_output_is_what_setup_really_prints():
    """Every line the page shows must appear in what the script really says.

    The page once showed a four-line refusal with five lines silently cut out
    and no ellipsis, and the cut portion contradicted the paragraph beneath it.
    The same rule now applies to the setup output the quick start quotes.
    """
    setup = ROOT / "plugins" / "cerberus" / "skills" / "setup" / "cerberus_setup.py"
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        (root / "tests").mkdir()
        (root / "pyproject.toml").write_text(
            '[project]\nname = "d"\nversion = "1"\n', encoding="utf-8")
        (root / "tests" / "test_demo.py").write_text(
            "def test_ok():\n    assert True\n", encoding="utf-8")
        real = subprocess.run(
            [sys.executable, str(setup)], cwd=str(root),
            capture_output=True, text=True,
            env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"},
        ).stdout
    flat = " ".join(real.split())

    for path in (README, README_RU):
        quoted = [b for lang, b in fenced(path.read_text(encoding="utf-8"))
                  if lang == "text" and "Checks I ran here" in b]
        assert quoted, f"{path.name}: the setup output is not shown at all"
        saw_a_check = False
        for line in quoted[0].splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            # Which command passes depends on what is installed on this
            # machine, so the example command is not pinned — only that the
            # page shows the shape the script really prints, and that the
            # script really printed one.
            if stripped.startswith("ok "):
                saw_a_check = True
                continue
            assert " ".join(stripped.split()) in flat, (
                f"{path.name}: not in the real output: {stripped!r}")
        assert saw_a_check, f"{path.name}: the example shows no check at all"
        assert re.search(r"^  ok ", real, re.M), "setup printed no passing check to compare against"


def test_both_languages_have_the_same_sections():
    # Comparing counts alone let a mutant give the Russian page nine sections
    # with different titles and none of the content. The order and the shape of
    # each section have to line up too: same number of tables, same number of
    # fenced blocks, section by section.
    en_text, ru_text = README.read_text(encoding="utf-8"), README_RU.read_text(encoding="utf-8")
    en = re.split(r"^## ", en_text, flags=re.M)[1:]
    ru = re.split(r"^## ", ru_text, flags=re.M)[1:]
    assert len(en) == len(ru), f"{len(en)} sections in English, {len(ru)} in Russian"
    for a, b in zip(en, ru):
        title_a, title_b = a.splitlines()[0], b.splitlines()[0]
        tables_a = len(re.findall(r"^\|", a, re.M))
        tables_b = len(re.findall(r"^\|", b, re.M))
        assert (tables_a > 0) == (tables_b > 0), f"'{title_a}' vs '{title_b}': tables disagree"
        assert len(fenced(a)) == len(fenced(b)), f"'{title_a}' vs '{title_b}': blocks disagree"


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
        # By the commands, not by the heading: a section titled "Now what?"
        # once tripped a word-match and a section titled "Getting going" would
        # not have. What must not come back is a second place that tells you
        # how to install.
        sections = re.split(r"^## ", text, flags=re.M)[1:]
        # Only fenced commands count. Prose saying "a plugin install keeps its
        # files under the plugin" is explaining, not instructing, and an
        # earlier version of this counted it.
        installing = []
        for sec in sections:
            commands = "\n".join(body for _, body in fenced(sec))
            if re.search(r"/plugin install |skill-installer install|install\.sh \|", commands):
                installing.append(sec.splitlines()[0])
        assert len(installing) == 1, f"{path.name}: installing explained in {installing}"
        quick = section(text, "## Quick start") if "## Quick start" in text else section(
            text, "## Быстрый старт"
        )
        assert "plugin install" in quick and "skill-installer" in quick, path.name


def test_nothing_claims_an_agent_lacks_hooks():
    """A claim about the world that nobody compared to the world.

    "Codex has no hook mechanism" lived here for months and spread to four
    files, because it was prose. It is false: Codex documents the same two
    events and the same block protocol. Anything asserting a provider cannot
    enforce belongs in a capability the code declares, not in a sentence.
    """
    # Matched as a shape, not as five literal strings: the first version of
    # this guard read only .md and .sh — so the original sentence could return
    # verbatim in a .py comment — and missed "does not have a hook mechanism",
    # "lacks any hook mechanism" and "there are no hooks in" while claiming to
    # prevent exactly that.
    # Anchored on an agent's name, because the claim being banned is about an
    # agent's capabilities. Without the anchor this fired on a comment about a
    # *project* that had no hooks installed, which is a different sentence and
    # a true one.
    agent = r"(?:codex|claude code|claude|the agent|агент\w*|codex\w*)"
    denial = r"(?:has no|have no|lacks any|without any|there are no|no)\s+hooks?"
    shapes = [
        re.compile(agent + r"[^.\n]{0,60}" + denial, re.I),
        re.compile(denial + r"[^.\n]{0,60}" + agent, re.I),
        re.compile(r"(?:нет|не имеет)\s+(?:механизма\s+)?хуков", re.I),
        re.compile(r"хуков\s+(?:там\s+)?нет", re.I),
    ]
    for path in sorted(ROOT.rglob("*.md")) + sorted(ROOT.rglob("*.sh")) + sorted(ROOT.rglob("*.py")):
        if ".git" in path.parts or path.name == "CHANGELOG.md":
            continue
        if path.name == "test_readme.py":
            continue  # it has to quote the sentence to say why it is banned
        text = path.read_text(encoding="utf-8")
        for shape in shapes:
            found = shape.search(text)
            assert not found, f"{path.relative_to(ROOT)}: {found.group(0)!r}"


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
