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
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
README_RU = ROOT / "README.ru.md"


def flat(text: str) -> str:
    """Whitespace collapsed. A guard that breaks when a paragraph is rewrapped
    is a guard nobody keeps, and three of these broke that way at once."""
    return " ".join(text.lower().split())


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


def test_the_agent_command_is_the_documented_one():
    """The first route is one prompt for any coding agent, not a platform choice."""
    blocks = shell_blocks(install_section(README.read_text(encoding="utf-8")))
    assert len(blocks) == 1, f"expected one agent prompt, found {len(blocks)}"
    lines = [line.strip() for line in blocks[0].splitlines() if line.strip()]
    assert lines == [
        "Before doing anything else, ask me exactly:",
        "Which language would you like me to use: English or Russian?",
        "Wait for my answer. Then install and configure Cerberus from the complete raw guide without summarizing it",
        "(use curl or an equivalent if your web tool summarizes) and follow it:",
        "https://raw.githubusercontent.com/concordloom/cerberus/main/docs/install.md",
    ], lines
    assert "Claude" not in blocks[0] and "Codex" not in blocks[0], blocks[0]


def test_both_languages_send_every_agent_to_the_same_guide():
    for path in (README, README_RU):
        blocks = shell_blocks(install_section(path.read_text(encoding="utf-8")))
        assert len(blocks) == 1, f"{path.name}: {len(blocks)} agent prompts"
        assert blocks[0].splitlines()[-1] == (
            "https://raw.githubusercontent.com/concordloom/cerberus/main/docs/install.md"
        ), blocks[0]
        assert "Claude" not in blocks[0] and "Codex" not in blocks[0], blocks[0]


def test_both_readmes_put_the_language_stop_before_the_install_guide_url():
    question = "Which language would you like me to use: English or Russian?"
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        heading = "## Install" if path == README else "## Установка"
        prompts = shell_blocks(section(text, heading))
        assert len(prompts) == 1, (path.name, heading)
        prompt = prompts[0]
        assert prompt.count(question) == 1, (path.name, heading)
        assert prompt.index(question) < prompt.index("https://"), (path.name, heading)
        assert "Wait for my answer" in prompt or "Дождись ответа" in prompt, (
            path.name, heading)
        assert "summariz" in prompt or "без пересказа" in prompt, (path.name, heading)


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
    assert "Verdict: READY" in body, body
    assert "Verdict: NOT READY" in body, body


def test_the_quick_start_fits_above_the_fold():
    body = quick_section(README.read_text(encoding="utf-8"))
    lines = [line for line in body.splitlines() if line.strip()]
    # Raised in round two of #66: the section now shows both verdicts. A
    # reader is buying the verdict, and showing only the one where everything
    # passed was a finding — the failing one is the output they actually care
    # about. Still bounded, because this section is the one people skim.
    assert len(lines) <= 40, f"{len(lines)} lines is not a quick start"


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

    for path, heading in ((README, "## Stage 2 and the delivery boundary"),
                          (README_RU, "## Стадия 2 и граница поставки")):
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
    sys.path.insert(0, str(ROOT / "plugins" / "cerberus" / "skills" / "cerberus-setup"))
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
    # Round three of #66: the fact moved into the first paragraph, because a
    # reader who decided on the headline never reached the caveat two hundred
    # lines down — and what it cancels is the property that made the tool look
    # safe. So the check is that it appears early, not merely that it appears.
    for path, phrases in (
        (README, ("may reach for one when you say", "of its own accord")),
        (README_RU, ("может взяться за них сам", "агент может взяться за них сам")),
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
    """The README is one agent prompt; platform mechanics live in the guide."""
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        where = install_section(text)
        assert len(shell_blocks(where)) == 1, path.name
        assert "docs/install.md" in where, path.name
        for old in ("/plugin", "codex plugin", "install.sh", "<details>", ".claude/skills"):
            assert old not in where, f"{path.name}: old install route remains: {old}"


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
    # Anchored on `adversary`, not on the old tagline. Three cold readers
    # showed that tagline was the worst sentence on the page, so the guard
    # cannot hold it — but the rule it protects is still real: the Russian
    # no-calque list must never force the English page into worse English.
    english = README.read_text(encoding="utf-8").lower()
    assert "adversary" in english, (
        "README.md lost the word adversary — the Russian rule has leaked onto "
        "the English page, where these terms are correct")


def test_the_badges_describe_the_routes_the_page_actually_gives():
    """The agent-agnostic entry should not advertise a specific host."""
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        badges = re.findall(r'shields\.io/badge/([^"]+)', text)
        assert not any("Codex" in badge or "Claude" in badge for badge in badges), (
            f"{path.name}: host-specific badge remains: {badges}")


def test_no_path_is_handed_out_without_saying_which_install_it_belongs_to():
    """#58's mixed cell: the recommended route, and the page got it wrong.

    `python3 .claude/skills/cerberus-setup/cerberus_setup.py` exists only after
    `install.sh`. A plugin user has it under the plugin's cache, and that was
    the one sentence telling them how to run setup again.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for n, line in enumerate(lines):
            if ".claude/skills/cerberus-setup" not in line:
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
    for path, needles in ((README, ("--draft-stage2", "gh run watch --exit-status")),
                          (README_RU, ("--draft-stage2", "gh run watch --exit-status"))):
        text = flat(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


def test_someone_who_deploys_from_ci_can_find_the_draft():
    """#58, point 4. The most useful thing here was invisible from the front page."""
    for path, needles in ((README, ("--draft-stage2", "gh run watch --exit-status")),
                          (README_RU, ("--draft-stage2", "gh run watch --exit-status"))):
        text = flat(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


def test_someone_who_deploys_from_ci_can_find_the_draft():
    """#58, point 4. The most useful thing here was invisible from the front page."""
    for path, needles in ((README, ("--draft-stage2", "gh run watch --exit-status")),
                          (README_RU, ("--draft-stage2", "gh run watch --exit-status"))):
        text = flat(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


def test_someone_who_deploys_from_ci_can_find_the_draft():
    """#58, point 4. The most useful thing here was invisible from the front page."""
    for path, needles in ((README, ("--draft-stage2", "gh run watch --exit-status")),
                          (README_RU, ("--draft-stage2", "gh run watch --exit-status"))):
        text = flat(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle.lower() in text, f"{path.name}: {needle!r}"


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
        # The agent-first route adds a two-line explanation and one collapsed
        # manual fallback. Keep the section bounded despite the extra route.
        assert len(prose) <= 12, (
            f"{path.name}: {len(prose)} lines of prose in the install section:\n"
            + "\n".join(prose))


def test_the_quick_start_holds_no_install_commands():
    """#62, point 4. It is what to do *after* installing."""
    for path in (README, README_RU):
        quick = quick_section(path.read_text(encoding="utf-8"))
        for lang, body in fenced(quick):
            assert "plugin" not in body and "install.sh" not in body, (
                f"{path.name}: installing crept back into the quick start:\n{body}")


#: Sections the page may hold, and how long it may be.
#:
#: Raised twice, both times for an addition someone asked for rather than one
#: that crept in — which is the distinction the bound exists to draw. On #64,
#: Uninstall as its own block. On #66, a `cerberus.json` example and a verdict
#: example: three cold readers independently stopped at the same two places,
#: and both gaps were content the page had never had rather than prose that
#: had swollen. Raised again in round two of #66: a fresh reader could write
#: the config but not the commands, so the CI case got three real ones, the
#: example became the Kubernetes one it had always described, and `NOT READY`
#: got shown instead of promised. Two bounds had accumulated by #64, from #58
#: and #62, checking the same thing with different numbers; this is the one.
#: Round three added the fifth config key as a shown example and a paragraph on
#: what `notes` is not — a third reader wrote a wrong config because "All of
#: it:" preceded four keys and the fifth arrived seventy lines later.
#: Agent-led install and uninstall replaced all platform-specific README routes.
MAX_SECTIONS = 11
MAX_LINES = {"README.md": 190, "README.ru.md": 195}


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


def test_uninstalling_is_a_single_agent_prompt_and_not_in_the_install_section():
    """#64. Two orphan sentences about removal, one per install route.

    They sat in the install section explaining how to undo the thing the reader
    had not done yet, which is the register the whole restructure removed.
    """
    for path, heading in (
        (README, "## Uninstall"),
        (README_RU, "## Удаление"),
    ):
        text = path.read_text(encoding="utf-8")
        assert heading in text, f"{path.name}: no {heading}"
        where = section(text, heading)
        prompts = shell_blocks(where)
        assert len(prompts) == 1, f"{path.name}: expected one uninstall prompt"
        assert prompts[0].splitlines()[-1] == (
            "https://raw.githubusercontent.com/concordloom/cerberus/main/docs/uninstall.md"
        ), prompts[0]
        assert "Which language would you like me to use" not in prompts[0]
        assert "cerberus.json" in prompts[0]
        for old in ("/plugin", "codex plugin", ".claude/skills", ".agents/skills", "<details>"):
            assert old not in where, f"{path.name}: old uninstall route remains: {old}"
        installing = install_section(text).lower()
        for word in ("uninstall", "remove", "удал"):
            assert word not in installing, (
                f"{path.name}: the install section still talks about {word!r}")


def test_the_page_shows_the_config_file_it_spends_a_section_describing():
    """#66. Two cold readers independently named this the largest gap.

    A whole section described `cerberus.json` in prose and never showed it, so
    a reader could not learn the wrapper key, the shape of a value, or where
    the file goes. Writing it from the page produced a file the skills do not
    read.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        blocks = [b for lang, b in fenced(text) if lang == "json"]
        assert blocks, f"{path.name}: no config example anywhere"
        body = json.loads(blocks[0])
        assert body["language"] == ("en" if path == README else "ru"), path.name
        assert "verification" in body, (
            f"{path.name}: the example omits the wrapper key, which is the one "
            "thing a reader cannot guess")
        for key in ("artifact_kind", "stage1", "stage2", "notes"):
            assert key in body["verification"], f"{path.name}: example lacks {key}"


def test_the_page_shows_a_verdict():
    """#66. Sold as "a verdict instead of a claim", and never shown one.

    The only verdict line used to be `READY scope: Stage 1`, inside the
    paragraph about the degraded case. I cut the full sample myself on #62,
    aiming at the commentary around it and taking the subject with it.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        samples = [b for lang, b in fenced(text) if lang == "text"]
        verdicts = [b for b in samples if "Verdict:" in b or "READY" in b]
        assert verdicts, f"{path.name}: no verdict shown"
        body = verdicts[0]
        for token in ("Stage 1", "Stage 2", "Not proven", "READY"):
            assert token in body, f"{path.name}: the verdict sample lacks {token!r}"


def test_the_kind_values_sit_in_the_table_not_in_a_positional_list():
    """#66. Both readers counted rows with a finger, and both stopped there.

    "one row each, in that order" asked the reader to join two lists by
    position to learn the only mandatory field. `a prompt or parser` →
    `model-boundary` is not guessable.
    """
    sys.path.insert(0, str(ROOT / "plugins" / "cerberus" / "skills" / "cerberus-setup"))
    import cerberus_setup

    for path, heading in ((README, "## Stage 2 and the delivery boundary"),
                          (README_RU, "## Стадия 2 и граница поставки")):
        body = section(path.read_text(encoding="utf-8"), heading)
        rows = [r for r in body.splitlines() if r.startswith("|") and "---" not in r]
        for kind in cerberus_setup.STAGE2_HINT_BY_KIND:
            on_its_own_row = [r for r in rows if f"`{kind}`" in r]
            assert on_its_own_row, f"{path.name}: {kind!r} is not in a row of its own"
        assert "in that order" not in body and "в том же порядке" not in body, (
            f"{path.name}: the positional join is back")


def test_the_page_tells_the_reader_what_to_type():
    """#66. There was no prompt to copy anywhere, in either language.

    "Ask your agent to set the project up" leaves the reader guessing the
    wording, and the skill is only named sixty lines later.
    """
    for path in (README, README_RU):
        quick = quick_section(path.read_text(encoding="utf-8"))
        prompts = [b for lang, b in fenced(quick) if lang == ""]
        assert len(prompts) == 1, f"{path.name}: {len(prompts)} prompts to copy"
        joined = " ".join(prompts).lower()
        assert "cerberus" in joined, joined


def test_the_draft_says_which_kinds_it_works_for():
    """#66. It returns nothing for five of the seven kinds in the page's own table."""
    sys.path.insert(0, str(ROOT / "plugins" / "cerberus" / "skills" / "cerberus-setup"))
    import cerberus_setup

    for path in (README, README_RU):
        text = flat(path.read_text(encoding="utf-8"))
        for kind in cerberus_setup.DEPLOYED_KINDS:
            assert f"`{kind}`" in text, f"{path.name}: {kind}"
        window = text[text.index("--draft-stage2") - 400:text.index("--draft-stage2") + 400]
        assert all(f"`{k}`" in window for k in cerberus_setup.DEPLOYED_KINDS), (
            f"{path.name}: the draft is offered without saying which kinds it serves")


def test_the_page_does_not_claim_no_model_is_ever_called():
    """#66. It said so three paragraphs above a table row reading "a real model call".

    And both documented installs fetch over the network. The claim is true only
    under an unstated scope, in the paragraph a reader uses to decide about
    privacy and cost.
    """
    for path in (README, README_RU):
        text = flat(path.read_text(encoding="utf-8"))
        for claim in ("no model is called and nothing goes over the network",
                      "ни одна модель не вызывается, в сеть ничего не уходит"):
            assert claim not in text, f"{path.name}: {claim!r}"


def test_the_page_says_the_cycle_wants_an_issue():
    """#66. SKILL.md calls working without one its own worst failure mode.

    The word did not appear on either page, so a reader following the README
    exactly lands in the degraded mode the skill was written to prevent.
    """
    for path, needle in ((README, "issue written before"), (README_RU, "задача, написанная")):
        assert needle in flat(path.read_text(encoding="utf-8")), f"{path.name}: {needle!r}"


def test_the_page_says_whose_credentials_stage_two_runs_with():
    """#66. The cold reader called this a blocker at review, and was right.

    Stage 2 runs commands the reader wrote, against real environments, with
    whatever the shell has. The page said nothing about it.
    """
    # Scoped to the section that answers "what will this do to my machine".
    # Matching the whole page passed on the word `credentials` sitting inside
    # the config example's `notes` string — a guard satisfied by a sample.
    for path, heading, needles in (
        (README, "## What it does to your session", ("credentials", "stage2")),
        (README_RU, "## Что это делает с вашей сессией", ("доступ", "stage2")),
    ):
        body = flat(section(path.read_text(encoding="utf-8"), heading))
        for needle in needles:
            assert needle in body, f"{path.name}: {heading} never mentions {needle!r}"


def test_the_page_shows_the_commands_for_the_case_it_calls_the_main_one():
    """Round two of #66. The paragraph a reader with a deployed service needs,
    and it contained no commands — description where instruction was due.

    A fresh reader wrote the whole config and had to invent `gh run watch` and
    `kubectl rollout status` himself, on a page that hands out `curl … | jq -e`
    elsewhere.
    """
    for path, heading in ((README, "## Stage 2 and the delivery boundary"),
                          (README_RU, "## Стадия 2 и граница поставки")):
        body = section(path.read_text(encoding="utf-8"), heading)
        blocks = "\n".join(b for _, b in fenced(body))
        for command in ("gh run watch --exit-status", "kubectl", "rollout status",
                        "git rev-parse HEAD"):
            assert command in blocks, f"{path.name}: no {command!r} in the CI paragraph"


def test_the_page_answers_deploy_on_merge_only():
    """Half the industry deploys from the default branch, and for them the page's
    own instruction is only possible after the merge — which defeats it."""
    for path, needle in ((README, "only deploys from the default branch"),
                         (README_RU, "катит только с основной ветки")):
        assert needle in flat(path.read_text(encoding="utf-8")), f"{path.name}: {needle!r}"


def test_the_config_example_does_not_contradict_the_boundary_table():
    """The one full example showed `docker compose up` for `artifact_kind: service`,
    whose row in the same page's table demands a deployed instance."""
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        body = json.loads([b for lang, b in fenced(text) if lang == "json"][0])
        v = body["verification"]
        if v["artifact_kind"] in ("service", "chart"):
            joined = " ".join(v["stage2"])
            assert "localhost" not in joined and "docker compose" not in joined, (
                f"{path.name}: a service's example reaches no further than this machine")


def test_the_page_states_the_execution_contract_for_stage2():
    """A fresh reader inferred the exit-code rule from a sample instead of reading it."""
    for path, needles in ((README, ("non-zero exit fails the stage", "from the repository root")),
                          (README_RU, ("ненулевой код возврата валит стадию",
                                       "из корня репозитория"))):
        text = flat(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"


def test_the_page_shows_a_not_ready_verdict_too():
    """It promised one comes back the same way and showed only the happy one.

    That is the output a reader is actually buying.
    """
    for path in (README, README_RU):
        samples = [b for lang, b in fenced(path.read_text(encoding="utf-8")) if lang == "text"]
        assert any("NOT READY" in b and "BLOCKER" in b for b in samples), (
            f"{path.name}: no failing verdict shown")


def test_telling_the_agent_to_stop_has_a_method():
    """"you can tell it not to" named no mechanism, and that is the question
    that gets tools uninstalled."""
    for path, needle in ((README, "don't run cerberus unless i ask"),
                         (README_RU, "не запускай цербера, пока не попрошу")):
        assert needle in flat(path.read_text(encoding="utf-8")), f"{path.name}: {needle!r}"


def test_the_first_paragraph_does_not_promise_more_than_the_page_delivers():
    """Round three of #66. "No hook, no daemon: they run when asked" was
    cancelled two hundred lines later, in a subordinate clause, under a
    reassuring heading.

    A reader who decides from the headline never gets there, and what is
    cancelled is the determinism that made running shell commands with their
    credentials look safe.
    """
    for path, needle in ((README, "may reach for one when you say"),
                         (README_RU, "может взяться за них сам")):
        text = path.read_text(encoding="utf-8")
        first = flat(text.split("## ")[0])
        assert needle.lower() in first, (
            f"{path.name}: the caveat is not in the opening, where the promise is")


def test_the_config_example_does_not_claim_to_be_complete_while_omitting_a_key():
    """Round three. "All of it:" preceded four keys; the fifth was seventy lines
    down, and a reader said he no longer knew what else might exist."""
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        assert "All of it:" not in text and "Целиком:" not in text, (
            f"{path.name}: claims completeness")
        assert "stage2_unreachable" in text
        blocks = [b for lang, b in fenced(text) if lang == "json"]
        assert any("stage2_unreachable" in b for b in blocks), (
            f"{path.name}: the fifth key is described but never shown as JSON")


def test_nothing_in_the_examples_triggers_a_deployment():
    """Round three, and it was mine: the round-two example ran
    `gh workflow run deploy.yml` — verification starting a deploy as a side
    effect, which a platform engineer called a change-management incident.
    """
    for path in (README, README_RU):
        text = path.read_text(encoding="utf-8")
        for lang, body in fenced(text):
            for shape in ("workflow run", "helm upgrade", "kubectl apply",
                          "git push origin"):
                assert shape not in body, (
                    f"{path.name}: an example performs a deployment: {shape!r}")


def test_the_page_says_notes_is_not_a_permission_boundary():
    """Round three. The only stated protection for production was a sentence in
    a free-text field, addressed to a language model."""
    for path, needles in ((README, ("not a permission boundary", "keep secrets out")),
                          (README_RU, ("не граница прав", "секреты в файл не"))):
        text = flat(path.read_text(encoding="utf-8"))
        for needle in needles:
            assert needle in text, f"{path.name}: {needle!r}"


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
