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
SKILLS = ROOT / "plugins" / "cerberus" / "skills" / "cerberus"
EN = SKILLS / "SKILL.md"
RU = SKILLS / "SKILL.ru.md"

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


def main() -> int:
    if not EN.exists() or not RU.exists():
        print("both SKILL.md and SKILL.ru.md must exist", file=sys.stderr)
        return 1

    en, ru = profile(EN), profile(RU)
    problems: list[str] = []

    if en["headings"] != ru["headings"]:
        problems.append(
            "heading structure differs\n"
            f"  SKILL.md    : {len(en['headings'])} headings, levels {en['headings']}\n"
            f"  SKILL.ru.md : {len(ru['headings'])} headings, levels {ru['headings']}"
        )
    if en["checklist"] != ru["checklist"]:
        problems.append(
            f"self-check length differs: {en['checklist']} vs {ru['checklist']} items"
        )
    if en["fences"] != ru["fences"]:
        problems.append(
            f"number of code blocks differs: {en['fences']} vs {ru['fences']}"
        )

    if problems:
        print("Translation parity failed. English is canonical.\n", file=sys.stderr)
        for p in problems:
            print(f"- {p}", file=sys.stderr)
        return 1

    print(
        f"parity ok: {len(en['headings'])} headings, "
        f"{en['checklist']} checklist items, {en['fences']} code blocks"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
