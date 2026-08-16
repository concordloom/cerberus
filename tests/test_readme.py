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


def install_section(text: str) -> str:
    """Wherever installing lives, so a guard survives the page being reordered."""
    return section(text, "## Install" if "## Install" in text else "## Установка")


def quick_section(text: str) -> str:
    return section(text, "## Quick start" if "## Quick start" in text else "## Быстрый старт")


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
    blocks = console_blocks(install_section(README.read_text(encoding="utf-8")))
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
        assert "No hook was installed" in proc.stdout, proc.stdout


def test_the_url_the_installer_command_fetches_is_alive():
    """The half of the one-liner the test above no longer executes."""
    import urllib.request

    url, _ = documented_install()
    with urllib.request.urlopen(url, timeout=30) as response:
        assert response.status == 200, url
        assert b"cerberus" in response.read(2000), url


def test_the_agent_commands_are_the_documented_ones():
    """Neither pair can run here — both need a session and credentials.

    So their text is pinned. The Codex pair used to be a `$skill-installer`
    line with a long URL; it installed one skill per invocation and had no
    version to upgrade from. Codex reads the same marketplace, which was true
    before anyone here checked.
    """
    blocks = shell_blocks(install_section(README.read_text(encoding="utf-8")))
    assert len(blocks) == 2, f"expected two install pairs, found {len(blocks)}"
    plugin = [line.strip() for line in blocks[0].splitlines() if line.strip()]
    assert plugin == [
        "/plugin marketplace add concordloom/cerberus",
        "/plugin install cerberus@concordloom",
    ], plugin
    codex = [line.strip() for line in blocks[1].splitlines() if line.strip()]
    assert codex == [
        "codex plugin marketplace add concordloom/cerberus",
        "codex plugin add cerberus@concordloom",
    ], codex


def test_both_agents_install_the_same_way():
    """The asymmetry was ours, not the tools'.

    A reader comparing two different-looking routes cannot tell whether the
    difference reflects the agents or our ignorance. It reflected ours.
    """
    for path in (README, README_RU):
        blocks = shell_blocks(install_section(path.read_text(encoding="utf-8")))
        assert len(blocks) == 2, f"{path.name}: {len(blocks)} agent blocks"
        for block in blocks:
            lines = [l for l in block.splitlines() if l.strip()]
            assert len(lines) == 2, f"{path.name}: an agent gets {len(lines)} commands"
            assert "marketplace add concordloom/cerberus" in lines[0], lines
            assert "cerberus@concordloom" in lines[1], lines


def test_no_page_asks_anyone_to_install_the_skills_one_at_a_time():
    """One install brings all three, and saying otherwise costs the critic.

    The old Codex route installed one skill per invocation, so the page told
    the reader to run it twice more. Anyone who stopped after the first had the
    gate and not the critic — half the cycle, and the half whose absence nobody
    notices.
    """
    shapes = [
        re.compile(r"swap .{0,20}`?cerberus`? .{0,20}for", re.I),
        re.compile(r"замените `?cerberus`? .{0,30}на `?critic", re.I),
        re.compile(r"to add the other two", re.I),
        re.compile(r"чтобы добавить (?:два других|остальные)", re.I),
    ]
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        for shape in shapes:
            found = shape.search(text)
            assert not found, f"{path.name}: {found.group(0)!r}"


def test_nothing_still_sends_codex_somewhere_else():
    """The previous claim lived in four files.

    "Codex has no hooks" spread exactly this way and needed its own issue to
    pull back out, so this looks at the tree rather than at the two pages.
    """
    offenders = []
    for path in sorted(ROOT.rglob("*.md")) + sorted(ROOT.rglob("*.sh")):
        if ".git" in path.parts or path.name in ("CHANGELOG.md", "test_readme.py"):
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "skill-installer" in line:
                offenders.append(f"{path.relative_to(ROOT)}:{n}")
    assert not offenders, "still routing Codex through skill-installer: " + ", ".join(offenders)


def test_the_quick_start_shows_what_success_looks_like():
    body = quick_section(README.read_text(encoding="utf-8"))
    assert "```text" in body, "the reader is told to run something with no idea what it prints"
    assert "Checks I ran here" in body, body


def test_the_quick_start_fits_above_the_fold():
    body = quick_section(README.read_text(encoding="utf-8"))
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


def test_the_page_says_this_project_installs_nothing_that_runs():
    """#33's claim, stated as the true one.

    Someone deciding whether to install needs to know what it puts in their
    session. The answer is: no hook, no process, no edit to their files — which
    is a fact about this project and stays true regardless of what an agent
    then chooses to do.
    """
    for path, phrases in (
        (README, ("no hook", "no background process")),
        (README_RU, ("ни хука", "ни фонового процесса")),
    ):
        text = path.read_text(encoding="utf-8").lower()
        for phrase in phrases:
            assert phrase in text, f"{path.name}: {phrase!r}"


def test_the_page_admits_an_agent_may_invoke_it_unasked():
    """#43. Codex did, on a prompt that named neither cerberus nor verification.

    The page promised silence three times and the skill's own description is
    what broke the promise — it names "done" and "it works" as the moment the
    skill is for, which is exactly what makes an agent reach for it.
    """
    for path, phrases in (
        (README, ("reach for it unasked", "judgement")),
        (README_RU, ("взяться за него и сам", "суждение")),
    ):
        # Collapsed, because these phrases wrap across lines and a guard that
        # breaks when a paragraph is rewrapped is a guard nobody keeps.
        text = " ".join(path.read_text(encoding="utf-8").lower().split())
        for phrase in phrases:
            assert phrase in text, f"{path.name}: {phrase!r}"


def test_nothing_promises_that_the_skill_stays_quiet():
    """#43, as a shape rather than as the three strings edited that day.

    Pinning the old wording would have pinned the redaction, not the
    requirement — the same mistake as a line limit set where nothing could
    reach it. What must not come back is any sentence promising that this will
    not act until asked.
    """
    shapes = [
        re.compile(r"nothing\s+(?:happens|runs|will happen)\s+(?:on its own|by itself|until)", re.I),
        re.compile(r"nothing\s+invokes?\s+this", re.I),
        re.compile(r"(?:stays?|remains?)\s+(?:quiet|silent)\s+until", re.I),
        re.compile(r"nothing,?\s+until you ask", re.I),
        re.compile(r"(?:само по себе|сам[оа]?)\s+ничего\s+не\s+(?:происходит|запускается)", re.I),
        re.compile(r"никто\s+не\s+вызовет", re.I),
        re.compile(r"ничего,?\s+пока вы не попросите", re.I),
    ]
    offenders = []
    for path in sorted(ROOT.rglob("*.md")):
        if ".git" in path.parts or path.name in ("CHANGELOG.md",):
            continue
        if path.name == "test_readme.py":
            continue
        text = path.read_text(encoding="utf-8")
        for shape in shapes:
            found = shape.search(text)
            if found:
                offenders.append(f"{path.relative_to(ROOT)}: {found.group(0)!r}")
    assert not offenders, "promising silence again:\n  " + "\n  ".join(offenders)


def test_the_skill_does_not_contradict_its_own_description():
    """#43, point 4. The two lines sat four lines apart and argued.

    `description` names the trigger words that make an agent pick this up;
    `when_to_use` said nothing would pick it up. Whichever an agent believed,
    the file was wrong.
    """
    for path in (ROOT / "plugins/cerberus/skills/cerberus/SKILL.md",
                 ROOT / "plugins/cerberus/skills/cerberus/SKILL.ru.md"):
        head = path.read_text(encoding="utf-8").split("---")[1]
        assert re.search(r"when_to_use:", head), path.name
        assert not re.search(r"[Nn]othing invokes|[Нн]икто не вызовет", head), (
            f"{path.name}: when_to_use denies what description is written to cause")


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
            if re.search(r"/plugin install |codex plugin add|install\.sh \|", commands):
                installing.append(sec.splitlines()[0])
        assert len(installing) == 1, f"{path.name}: installing explained in {installing}"
        where = install_section(text)
        assert "plugin install" in where and "codex plugin add" in where, path.name


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


#: Words that are English spelled in Cyrillic. A test for "does this read like
#: Russian" cannot be written; a test for "did this specific calque come back"
#: can, and the calque is what actually returns.
CALQUES = ["адверсариальн", "гейт", "артефакт", "оракул", "контрпример",
           # #60: not a transliteration but an invention — `file matcher` taken
           # apart and reassembled, in the sentence carrying the argument.
           "сопоставител", "проект-потребител", "реальной формы"]


def test_the_russian_page_uses_no_transliterated_english():
    """#54. The page opened with three of them in a row, on line one.

    "Адверсариальный гейт проверки" is `adversarial verification gate` written
    in Cyrillic letters: it sounds technical and means nothing, at the moment
    someone decides whether to keep reading.
    """
    text = README_RU.read_text(encoding="utf-8").lower()
    found = [w for w in CALQUES if w in text]
    assert not found, f"calques are back: {found}"


def test_the_guard_leaves_the_english_page_alone():
    """The mirror, and it is not decoration.

    On README.md these are correct English terms. A guard that spread to it
    would force the English page into worse English to satisfy a rule about
    Russian — so the guard is checked for staying on its own side.
    """
    # The tagline specifically, not the word anywhere: "a gate of fire" lives in
    # the hero image's alt text, and matching that made this pass while the
    # sentence it protects had been rewritten away.
    english = README.read_text(encoding="utf-8").lower()
    assert "adversarial verification gate" in english, (
        "README.md's tagline lost its terms — the Russian rule has leaked onto "
        "the English page, where they are correct English")


def test_each_install_route_says_who_it_is_for():
    """#54, point 6. Three blocks, no word on how they differ, so people pick by length.

    Two of them install for you; the third installs into the repository, where
    it can be committed and the whole team gets it.
    """
    for path, needles in ((README, ("for yourself", "whole team", "committed")),
                          (README_RU, ("себе", "всей команде", "закоммиченными"))):
        where = install_section(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle.lower() in where.lower(), f"{path.name}: {needle!r}"


def test_the_russian_page_explains_why_the_sample_output_is_english():
    """#54, point 7. Left bare it reads as an unfinished translation.

    The output stays English by the decision on #41 — an agent retells it in
    the reader's language, which is why string tables were not worth it. That
    reasoning has to reach the reader, not only the issue tracker.
    """
    text = README_RU.read_text(encoding="utf-8").lower()
    assert "вывод английский" in text, "the English block sits there unexplained"
    assert "пересказ" in text, "it never says the agent retells it"


def test_the_badges_describe_the_routes_the_page_actually_gives():
    """#58. `Codex — skill` outlived the route it named, at the top of the page."""
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        badges = re.findall(r'shields\.io/badge/([^"]+)', text)
        assert any("Codex-plugin" in b for b in badges), f"{path.name}: {badges}"
        assert not any("Codex-skill" in b for b in badges), (
            f"{path.name}: the badge still names the removed route")


def test_no_path_is_handed_out_without_saying_which_install_it_belongs_to():
    """#58's mixed cell: the recommended route, and the page got it wrong.

    `python3 .claude/skills/setup/cerberus_setup.py` exists only after
    `install.sh`. A plugin user has it under the plugin's cache, and that was
    the one sentence telling them how to run setup again.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for n, line in enumerate(lines):
            if ".claude/skills/setup" not in line:
                continue
            # The same sentence, not a nearby paragraph: a four-line window
            # matched the word "install" from "the install step above" and
            # passed on a bare `Run it again with <path>`.
            here = (line + " " + (lines[n + 1] if n + 1 < len(lines) else "")).lower()
            assert "installer" in here or "установщик" in here, (
                f"{path.name}:{n + 1}: a path given with no word about which route has it")


def test_the_page_knows_stage2_can_be_declared_unreachable():
    """#58, point 3. The page described the world before #51.

    Following it, a reader leaves `stage2` empty and meets a `Not proven` that
    could have been a recorded decision with a reason.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        assert "stage2_unreachable" in text, f"{path.name}: never mentions the key"
        assert "READY scope: Stage 1" in text, f"{path.name}: never says what it does to a verdict"


def test_the_page_says_a_filled_stage2_is_no_longer_optional():
    for path, needle in ((README, "no longer optional"),
                         (README_RU, "уже обязательно")):
        assert needle in path.read_text(encoding="utf-8").lower(), path.name


def test_someone_who_deploys_from_ci_can_find_the_draft():
    """#58, point 4. The most useful thing here was invisible from the front page."""
    for path, needles in ((README, ("--draft-stage2", "waiting is not verifying")),
                          (README_RU, ("--draft-stage2", "ожидание проверкой не является"))):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


def test_someone_who_deploys_from_ci_can_find_the_draft():
    """#58, point 4. The most useful thing here was invisible from the front page."""
    for path, needles in ((README, ("--draft-stage2", "waiting is not verifying")),
                          (README_RU, ("--draft-stage2", "ожидание проверкой не является"))):
        text = path.read_text(encoding="utf-8").lower()
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


def test_the_fix_did_not_grow_the_page():
    """A correction made by appending is a different failure with the same name.

    Eleven sections already compete for attention; a twelfth beats the ones
    that work. So the bound is on sections, and on how far the line count may
    move for four corrections.
    """
    for path, lines in ((README, 160), (README_RU, 162)):
        text = path.read_text(encoding="utf-8")
        assert len(re.findall(r"^## ", text, re.M)) <= MAX_SECTIONS, (
            f"{path.name}: a section was added")
        body = [l for l in text.splitlines() if l.strip()]
        assert len(body) <= lines, f"{path.name}: {len(body)} lines, bound {lines}"


def test_no_command_on_either_page_has_a_blank_left_in_it():
    """#60. A placeholder in a line someone will copy is a line that will not run.

    This project refuses that everywhere else — #51 rejects a `stage2` still
    holding the draft's blanks — and then put one in its own quick start, on
    both pages, in the fix landed for #58.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        for lang, body in fenced(text):
            for line in body.splitlines():
                assert not re.search(r"<[a-zа-я][^>]*>", line, re.I), (
                    f"{path.name}: a command with a blank in it: {line.strip()!r}")
        # And inline commands, which is where this one actually was. Fenced
        # blocks are removed first: scanning the whole document for `…` pairs
        # walks straight through ``` fences and pairs the wrong backticks, so
        # the first version of this found zero commands and passed on both
        # mutants.
        prose = re.sub(r"```.*?```", "", text, flags=re.S)
        for inline in re.findall(r"`([^`\n]+)`", prose):
            if not inline.startswith(("python3 ", "sh ", "curl ", "codex ", "claude ")):
                continue
            assert not re.search(r"<[a-zа-я][^>]*>", inline, re.I), (
                f"{path.name}: a command with a blank in it: {inline!r}")


def test_the_install_section_contains_only_installing():
    """#62. Someone who came to install should read commands, not paragraphs.

    The complaint was that the two commands were buried in prose about setup,
    sample output, and why that output is English. So the section is bounded:
    every line in it is a command, a heading, a badge of who it is for, or one
    short line saying where the skills land.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        where = install_section(text)
        prose = []
        in_fence = False
        for line in where.splitlines():
            if line.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or not line.strip() or line.startswith(("#", "**", "|")):
                continue
            prose.append(line)
        # Two destinations, two lines each at most: what lands where, and how
        # to undo it.
        assert len(prose) <= 6, (
            f"{path.name}: {len(prose)} lines of prose in the install section:\n"
            + "\n".join(prose))


def test_the_two_destinations_are_separate_and_labelled():
    """#62, point 2. A reader must not have to infer which one they want."""
    for path, needles in ((README, ("### For yourself", "### Into the repository")),
                          (README_RU, ("### Себе", "### В репозиторий"))):
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"
        assert text.index(needles[0]) < text.index(needles[1]), (
            f"{path.name}: the personal route should come first")


def test_the_quick_start_holds_no_install_commands():
    """#62, point 4. It is what to do *after* installing."""
    for path in (README, README_RU):
        quick = quick_section(path.read_text(encoding="utf-8"))
        for lang, body in fenced(quick):
            assert "plugin" not in body and "install.sh" not in body, (
                f"{path.name}: installing crept back into the quick start:\n{body}")


#: Sections the page may hold, and how long it may be. Raised once, on #64,
#: when the owner asked for Uninstall as its own block — an addition that was
#: requested rather than one that crept in, which is the distinction the bound
#: exists to draw. Two bounds had accumulated by then, from #58 and #62,
#: checking the same thing with different numbers; this is the one.
MAX_SECTIONS = 11
MAX_LINES = {"README.md": 150, "README.ru.md": 152}


def test_the_page_does_not_grow_on_its_own():
    """#58 and #62: a fix made by appending is a different failure with the same name.

    Every section here competes with the ones that work, so growth has to be a
    decision someone took, not a side effect of answering a question.
    """
    for path, lines in ((README, MAX_LINES["README.md"]),
                        (README_RU, MAX_LINES["README.ru.md"])):
        text = path.read_text(encoding="utf-8")
        assert len(re.findall(r"^## ", text, re.M)) <= MAX_SECTIONS, (
            f"{path.name}: a section was added")
        body = [l for l in text.splitlines() if l.strip()]
        assert len(body) <= lines, f"{path.name}: {len(body)} lines, bound {lines}"


def test_uninstalling_is_a_section_and_removing_is_not_mentioned_anywhere_else():
    """#64. Two orphan sentences about removal, one per install route.

    They sat in the install section explaining how to undo the thing the reader
    had not done yet, which is the register the whole restructure removed.
    """
    for path, heading, commands in (
        (README, "## Uninstall", ("/plugin uninstall", "codex plugin remove")),
        (README_RU, "## Удаление", ("/plugin uninstall", "codex plugin remove")),
    ):
        text = path.read_text(encoding="utf-8")
        assert heading in text, f"{path.name}: no {heading}"
        where = section(text, heading)
        for command in commands:
            assert command in where, f"{path.name}: {command!r} is not in {heading}"
        installing = install_section(text).lower()
        for word in ("uninstall", "remove", "удал"):
            assert word not in installing, (
                f"{path.name}: the install section still talks about {word!r}")


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
