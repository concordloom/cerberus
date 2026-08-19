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
SETUP_SKILLS = (
    ROOT / "plugins" / "cerberus" / "skills" / "cerberus-setup" / "SKILL.md",
    ROOT / "plugins" / "cerberus" / "skills" / "cerberus-setup" / "SKILL.ru.md",
)
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


def test_install_opens_with_the_exact_english_language_question():
    text = INSTALL.read_text(encoding="utf-8")
    first_step = text[: text.index("## 2.")]
    assert "always ask this exact question in English" in first_step
    assert first_step.count(LANGUAGE_QUESTION) == 1
    assert "response must end after that question" in first_step
    assert "Unless" not in first_step


def test_uninstall_reuses_the_saved_language_without_asking_again():
    text = _flat(UNINSTALL)
    assert LANGUAGE_QUESTION not in text
    for phrase in (
        "top-level `language` is `ru`",
        "English when it is `en`",
        "language of the current conversation",
        "Never ask a dedicated language question during uninstall",
    ):
        assert phrase in text, phrase


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
        "--language en",
        "record only Stage 1 commands that actually passed",
        "Ask before a lengthy suite",
        "Do not inspect or discuss the Stage 2 route yet",
    ):
        assert phrase in text, phrase


def test_install_persists_the_language_once_for_future_runs_and_uninstall():
    text = _flat(INSTALL)
    for phrase in (
        "`--language en` or `--language ru`",
        "selected once and retained",
        "Record the stable mechanics and selected language",
    ):
        assert phrase in text, phrase


def test_install_explains_stages_without_mislabeling_prerequisites():
    text = _flat(INSTALL)
    for phrase in (
        "**Stage 0** decides what could break",
        "**Stage 1** checks the code inside the repository",
        "**Stage 2** checks the built or deployed result",
        "This is what you will set up first",
        "Stage 2 prerequisite, not Stage 2 itself",
    ):
        assert phrase in text, phrase


def test_install_asks_about_a_stand_before_inferring_stage2():
    text = _flat(INSTALL)
    for phrase in (
        "do not infer and present its infrastructure first",
        "Is there a test or staging environment where Cerberus can verify the deployed version?",
        "Есть ли стенд, на котором Cerberus сможет проверить уже развёрнутую версию?",
        "How does a new version get there, and how can the agent obtain access?",
        "Do not send secrets",
        "After the answer, inspect CI triggers",
        "trigger or observe delivery for the exact revision",
        "prove the running artifact is that revision",
        "prove the check can fail",
    ):
        assert phrase in text, phrase


def test_stage2_confirmation_is_a_hard_turn_boundary():
    text = _flat(INSTALL)
    for phrase in (
        "availability question is a hard turn boundary",
        "End the response with it and wait",
        "Then wait again",
        "before the person answers",
    ):
        assert phrase in text, phrase


def test_default_branch_delivery_becomes_an_explicit_post_merge_gate():
    text = _flat(INSTALL)
    for phrase in (
        "full Cerberus run is post-merge",
        "gate moving the task to Done or releasing it",
        "cannot honestly gate that merge",
        "Combine repository evidence with what the person said",
        "ask one question about it",
    ):
        assert phrase in text, phrase


def test_install_keeps_setup_status_separate_from_product_verdicts():
    text = _flat(INSTALL)
    for phrase in (
        "Installation and setup do not receive a product verdict",
        "belong only to a Cerberus run against a concrete product change",
        "before the tracker task moves to Done",
        "`NOT READY` keeps the task open",
    ):
        assert phrase in text, phrase


def test_stage1_blocker_is_a_hard_turn_boundary_before_stage2():
    text = _flat(INSTALL)
    for phrase in (
        "If a required Stage 1 check fails, this is a hard turn boundary",
        "Do not inspect, infer, present, or ask about Stage 2 while Stage 1 is blocked",
        "Offer one recommended next action",
        "End with exactly one short question",
        "Resume only after the person answers",
    ):
        assert phrase in text, phrase


def test_normal_onboarding_hides_internal_configuration_and_tool_theatre():
    text = _flat(INSTALL)
    for phrase in (
        "Keep the internal work internal",
        "do not narrate tool or skill selection",
        "configuration files, JSON",
        "Never expose its filename, format, keys, or contents",
        "Do not report the configuration path",
        "marketplace mechanics",
    ):
        assert phrase in text, phrase


def test_stage2_is_a_progressive_conversation_not_a_batched_questionnaire():
    text = _flat(INSTALL)
    for phrase in (
        "Explain Stage 2 in one sentence",
        "do not infer and present its infrastructure first",
        "ask one related follow-up",
        "ask one question about it",
        "Wait for the answer before asking the next one",
        "Never batch a URL, cluster, namespace, credentials, revision proof",
    ):
        assert phrase in text, phrase


def test_the_loomwatch_regression_example_stops_at_the_go_blocker():
    text = INSTALL.read_text(encoding="utf-8")
    example = text[text.index("For LoomWatch with a missing Go toolchain"):
                   text.index("After Stage 1 succeeds")]
    assert "Go is missing" in example
    assert "May I run that and repeat the fast check?" in example
    for leaked in ("cerberus.json", "Kubernetes", "namespace", "token", "Helm"):
        assert leaked not in example, (leaked, example)


def test_install_recommends_the_three_gate_development_loop():
    text = _flat(INSTALL)
    for phrase in (
        "three-gate development loop",
        "run `cerberus-critic` on the task formulation before work begins",
        "run `cerberus-critic` on the proposed solution before implementation",
        "run `cerberus` on the completed change and exact delivered revision",
        "Give one short copyable prompt for each gate",
    ):
        assert phrase in text, phrase


def test_installed_setup_skills_enforce_the_same_progressive_flow():
    for path in SETUP_SKILLS:
        text = _flat(path)
        required = (
            "Stage 2" in text,
            "Stage 1" in text,
            "JSON" in text,
            "one question" in text or "один вопрос" in text,
            "configuration files" in text or "конфигурационные файлы" in text,
        )
        assert all(required), (path.name, required)
        stage1_gate = text.index("Stage 1")
        stage2_intro = text.rindex("Stage 2")
        assert stage1_gate < stage2_intro, path.name


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


def test_uninstall_confirmation_is_a_hard_turn_boundary():
    text = _flat(UNINSTALL)
    for phrase in (
        "initial request to follow this guide authorizes discovery, not deletion",
        "Confirmation is a hard turn boundary",
        "end the discovery response with a short question naming the exact targets",
        "do not run any removal command in that turn",
        "only after the user explicitly confirms those targets",
    ):
        assert phrase in text, phrase


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
