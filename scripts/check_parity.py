#!/usr/bin/env python3
"""Check that the English and Russian skill files still describe the same thing.

Two language versions drift. The drift is silent: nobody notices that a section
was added to one and not the other until someone follows the stale one and
misses a step. This compares the parts that must match regardless of language —
the heading structure, the fenced code blocks, and the number of checklist items
— and says nothing about the prose, which is supposed to differ.

    python3 scripts/check_parity.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILLS = sorted((ROOT / "plugins").glob("*/skills/*"))

HEADING = re.compile(r"^(#{1,6})\s+\S")
CHECKLIST = re.compile(r"^- \[ \]")
FENCE = re.compile(r"^```")


def profile(path: pathlib.Path) -> dict:
    levels: list[int] = []
    checklist = 0
    fences = 0
    in_fence = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            fences += 1
            continue
        if in_fence:
            continue
        if m := HEADING.match(line):
            levels.append(len(m.group(1)))
        elif CHECKLIST.match(line):
            checklist += 1
    return {"headings": levels, "checklist": checklist, "fences": fences // 2}


def compare(skill: pathlib.Path) -> list[str]:
    en, ru = skill / "SKILL.md", skill / "SKILL.ru.md"
    name = skill.name

    if not en.exists():
        return [f"{name}: no SKILL.md"]
    if not ru.exists():
        # A skill shipped without its translation is not a parity failure to
        # paper over — but it is a decision, so it has to be a visible one.
        return [f"{name}: SKILL.md has no SKILL.ru.md beside it"]

    a, b = profile(en), profile(ru)
    problems: list[str] = []

    if a["headings"] != b["headings"]:
        problems.append(
            f"{name}: heading structure differs\n"
            f"  SKILL.md    : {len(a['headings'])} headings, levels {a['headings']}\n"
            f"  SKILL.ru.md : {len(b['headings'])} headings, levels {b['headings']}"
        )
    if a["checklist"] != b["checklist"]:
        problems.append(
            f"{name}: self-check length differs: {a['checklist']} vs {b['checklist']} items"
        )
    if a["fences"] != b["fences"]:
        problems.append(
            f"{name}: number of code blocks differs: {a['fences']} vs {b['fences']}"
        )
    return problems


def compare_pages() -> list[str]:
    """The two README pages, which were never checked at all.

    Eight divergences of meaning had accumulated by #66 — different scope in
    the tagline, a term explained in one language and not the other, an update
    path documented only in English — and nothing looked. Structure is what a
    machine can compare; it would have caught half of them.
    """
    en, ru = ROOT / "README.md", ROOT / "README.ru.md"
    if not ru.exists():
        return ["README.ru.md is missing"]

    a, b = profile(en), profile(ru)
    problems: list[str] = []
    if a["headings"] != b["headings"]:
        problems.append(
            "README: heading structure differs\n"
            f"  README.md    : {len(a['headings'])} headings, levels {a['headings']}\n"
            f"  README.ru.md : {len(b['headings'])} headings, levels {b['headings']}"
        )
    if a["fences"] != b["fences"]:
        problems.append(
            f"README: number of code blocks differs: {a['fences']} vs {b['fences']}"
        )

    # Commands are not prose: a route documented in one language and not the
    # other is a reader who cannot install, and that is exactly how the
    # installer's update path came to exist only in English.
    for token in ("/plugin marketplace add", "/plugin install", "/plugin uninstall",
                  "codex plugin marketplace add", "codex plugin add",
                  "codex plugin remove", "install.sh", "--draft-stage2",
                  "stage2_unreachable", "artifact_kind", "verification"):
        in_en = token in en.read_text(encoding="utf-8")
        in_ru = token in ru.read_text(encoding="utf-8")
        if in_en != in_ru:
            problems.append(
                f"README: {token!r} appears in "
                + ("English only" if in_en else "Russian only")
            )
    return problems


def main() -> int:
    if not SKILLS:
        print("no skills found under plugins/*/skills/*", file=sys.stderr)
        return 1

    problems: list[str] = []
    for skill in SKILLS:
        problems.extend(compare(skill))
    page_problems = compare_pages()
    problems.extend(page_problems)
    if not page_problems:
        print('parity ok: README — same headings, same blocks, same commands named')

    if problems:
        print("Translation parity failed. English is canonical.\n", file=sys.stderr)
        for p in problems:
            print(f"- {p}", file=sys.stderr)
        return 1

    for skill in SKILLS:
        p = profile(skill / "SKILL.md")
        print(
            f"parity ok: {skill.name} — {len(p['headings'])} headings, "
            f"{p['checklist']} checklist items, {p['fences']} code blocks"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
