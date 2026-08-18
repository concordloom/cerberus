#!/usr/bin/env python3
"""Contract tests for the agent-led installation and removal guides."""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INSTALL = ROOT / "docs" / "install.md"
UNINSTALL = ROOT / "docs" / "uninstall.md"
README = ROOT / "README.md"
README_RU = ROOT / "README.ru.md"
LANGUAGE_QUESTION = "Which language would you like me to use: English or Russian?"


def _flat(path: pathlib.Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


def test_readme_urls_resolve_to_the_guides_in_this_tree():
    for page in (README, README_RU):
        text = page.read_text(encoding="utf-8")
        urls = re.findall(
            r"https://raw\.githubusercontent\.com/concordloom/cerberus/main/(docs/(?:install|uninstall)\.md)",
            text,
        )
        assert urls == ["docs/install.md", "docs/uninstall.md"], (page.name, urls)
        for relative in urls:
            assert (ROOT / relative).is_file(), f"{page.name}: missing {relative}"


def test_both_guides_always_open_with_the_exact_english_language_question():
    for path in (INSTALL, UNINSTALL):
        text = path.read_text(encoding="utf-8")
        first_step = text[: text.index("## 2.")]
        assert "always ask this exact question in English" in first_step, path.name
        assert first_step.count(LANGUAGE_QUESTION) == 1, path.name
        assert "response must end after that question" in first_step, path.name
        assert "Unless" not in first_step, path.name


def test_install_is_agent_agnostic_and_brings_the_complete_bundle():
    text = INSTALL.read_text(encoding="utf-8")
    for skill in ("`cerberus`", "`cerberus-critic`", "`cerberus-setup`"):
        assert skill in text, skill
    for route in (
        "claude plugin marketplace update concordloom",
        "claude plugin install cerberus@concordloom",
        "claude plugin update cerberus@concordloom",
        "codex plugin marketplace upgrade concordloom",
        "codex plugin add cerberus@concordloom",
        "Any other agent",
        "install.sh | sh",
    ):
        assert route in text, route
    assert "Do not install them one at a time" not in text


def test_install_refreshes_an_existing_plugin_instead_of_accepting_stale_presence():
    text = _flat(INSTALL)
    for phrase in (
        "existing installation is not proof that it is current",
        "reported version matches the current marketplace entry",
        "reading the newly installed files directly",
        "older cached copy",
    ):
        assert phrase in text, phrase


def test_install_reads_repository_rules_before_running_checks():
    text = _flat(INSTALL)
    for phrase in (
        "Do not ask the user for facts the repository already answers",
        "project-owned wrapper",
        "--stage1 './app.sh --smoke'",
        "write only Stage 1 commands that actually passed",
        "Ask before a lengthy suite",
        "project setup is blocked",
    ):
        assert phrase in text, phrase


def test_install_explains_stages_without_mislabeling_prerequisites():
    text = _flat(INSTALL)
    for phrase in (
        "**Stage 0** maps what can break",
        "**Stage 1** attacks the code locally",
        "**Stage 2** attacks the built or deployed result",
        "Stage 0 is rebuilt for each change",
        "Stage 2 prerequisite, not Stage 2 itself",
    ):
        assert phrase in text, phrase


def test_install_infers_stage2_before_it_asks():
    text = _flat(INSTALL)
    for phrase in (
        "Build the most likely route from that evidence",
        "confirmation of the inferred Stage 2 route",
        "do not begin with an infrastructure questionnaire",
        "only then ask the open question",
        "trigger delivery for the exact revision",
        "prove the running artifact is that revision",
        "prove the oracle can fail",
    ):
        assert phrase in text, phrase


def test_stage2_confirmation_is_a_hard_turn_boundary():
    text = _flat(INSTALL)
    for phrase in (
        "confirmation is a hard turn boundary",
        "End that response with the confirmation question",
        "Do not report `configured`",
        "until the user has answered",
        "cannot be `configured` before the inferred Stage 2 route has been confirmed",
    ):
        assert phrase in text, phrase


def test_default_branch_delivery_becomes_an_explicit_post_merge_gate():
    text = _flat(INSTALL)
    for phrase in (
        "full Cerberus verdict is post-merge",
        "gate moving the task to Done or releasing it",
        "cannot honestly gate that merge",
        "exact URL or target",
        "whether the agent has access",
        "safe negative checks are allowed",
    ):
        assert phrase in text, phrase


def test_install_keeps_setup_status_separate_from_product_verdicts():
    text = _flat(INSTALL)
    for phrase in (
        "**Installation:** `installed` or `not installed`",
        "**Project setup:** `configured` or `setup blocked`",
        "**Change verdict:** `READY` or `NOT READY`",
        "never use these during installation",
        "before a tracker task moves to Done",
        "`NOT READY` keeps the task open",
    ):
        assert phrase in text, phrase


def test_uninstall_preserves_configuration_unless_separately_confirmed():
    text = _flat(UNINSTALL)
    for phrase in (
        "preserve project verification knowledge by default",
        "Configuration is preserved by default",
        "separate explicit confirmation",
        "cerberus.json",
        ".claude/cerberus.json",
        ".codex/cerberus.json",
    ):
        assert phrase in text, phrase


def test_uninstall_is_narrow_and_verifiable():
    text = UNINSTALL.read_text(encoding="utf-8")
    for command in (
        "claude plugin uninstall cerberus@concordloom",
        "codex plugin remove cerberus@concordloom",
    ):
        assert command in text, command
    for root in (".claude/skills", ".agents/skills"):
        for skill in ("cerberus", "cerberus-critic", "cerberus-setup"):
            assert f"{root}/{skill}/" in text, (root, skill)
    for phrase in (
        "remove only the link",
        "Do not use broad globs",
        "Verify that each selected plugin entry",
        "what was preserved",
    ):
        assert phrase in text, phrase
    assert "rm -rf" not in text
    assert "docs/install.md" in text


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
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
