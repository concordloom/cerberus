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
RUNNER_SKILLS = (
    ROOT / "plugins" / "cerberus" / "skills" / "cerberus" / "SKILL.md",
    ROOT / "plugins" / "cerberus" / "skills" / "cerberus" / "SKILL.ru.md",
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
        "Never say that a configuration file was created, changed, is untracked, or should be committed",
        "do not append notes about files, Git status, cleanup, or what the person should commit",
    ):
        assert phrase in text, phrase


def test_onboarding_progress_reports_state_not_a_terminal_transcript():
    expected = {
        INSTALL: (
            "one user decision should normally produce one substantive response",
            "Do not emit repeated still-working updates for the same state",
            "checksum parsing, shell filters, retries, process polling",
            "A retry or a different diagnostic command is not a human-facing state change",
        ),
        SETUP_SKILLS[0]: (
            "one user decision should normally produce one substantive response",
            "Do not emit repeated still-working updates for the same state",
            "checksum parsing, shell filters, retries, process polling",
            "A retry or a different diagnostic command is not a human-facing state change",
        ),
        SETUP_SKILLS[1]: (
            "на один выбор человека должен приходиться один содержательный ответ",
            "Не отправляй повторные сообщения «ещё работаю» для одного состояния",
            "разбор контрольной суммы, фильтры оболочки, повторы, опрос процессов",
            "Повтор или другая диагностическая команда не меняют состояние для человека",
        ),
    }
    for path, phrases in expected.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


def test_first_stage1_run_has_a_resource_envelope():
    expected = {
        INSTALL: (
            "Every first Stage 1 command needs a wall-clock budget",
            "120 seconds",
            "Do not rerun a timed-out command directly without an equivalent limit",
            "4 GiB",
        ),
        SETUP_SKILLS[0]: (
            "Every first Stage 1 command needs a wall-clock budget",
            "120 seconds",
            "Do not rerun a timed-out command directly without an equivalent limit",
            "4 GiB",
        ),
        SETUP_SKILLS[1]: (
            "Первый запуск каждой команды Stage 1 должен иметь ограничение по времени",
            "120 секунд",
            "Не перезапускай команду после тайм-аута напрямую без равноценного ограничения",
            "4 ГиБ",
        ),
    }
    for path, phrases in expected.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


def test_authenticated_production_read_requires_specific_confirmation():
    runner_skills = {
        RUNNER_SKILLS[0]: (
            "Describing an access method is context, not approval",
            "authenticated production read",
            "reading a secret",
            "one exact read-only probe",
        ),
        RUNNER_SKILLS[1]: (
            "Описание способа доступа — это контекст, а не разрешение",
            "авторизованным чтением production",
            "чтением секрета",
            "одну конкретную проверку только для чтения",
        ),
    }
    setup_surfaces = {
        INSTALL: runner_skills[RUNNER_SKILLS[0]],
        SETUP_SKILLS[0]: runner_skills[RUNNER_SKILLS[0]],
        SETUP_SKILLS[1]: runner_skills[RUNNER_SKILLS[1]],
        **runner_skills,
    }
    for path, phrases in setup_surfaces.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


def test_shared_mechanics_and_local_access_are_two_distinct_layers():
    expected = {
        INSTALL: (
            "stable, portable verification mechanics belong to the project",
            "machine-specific paths, private targets, and credentials stay in an ignored local override",
            "Never put the shared project configuration in `.git/info/exclude`",
            "The local override must be separate from the shared project record",
        ),
        SETUP_SKILLS[0]: (
            "stable, portable verification mechanics belong to the project",
            "machine-specific paths, private targets, and credentials stay in an ignored local override",
            "Never put the shared project configuration in `.git/info/exclude`",
            "The local override must be separate from the shared project record",
        ),
        SETUP_SKILLS[1]: (
            "Устойчивая переносимая механика проверки принадлежит проекту",
            "локальные пути, приватные цели и учётные данные остаются в игнорируемом локальном дополнении",
            "Никогда не добавляй общую конфигурацию проекта в `.git/info/exclude`",
            "Локальное дополнение должно быть отделено от общей записи проекта",
        ),
    }
    for path, phrases in expected.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


def test_setup_final_report_never_surfaces_internal_record_as_repo_work():
    expected = {
        SETUP_SKILLS[0]: (
            "Never say that a configuration file was created, changed, is untracked, or should be committed",
            "Do not include it in a working-tree summary",
            "Did I omit internal files, Git status, and commit advice from the final response?",
        ),
        SETUP_SKILLS[1]: (
            "Никогда не говори, что конфигурационный файл создан, изменён, не отслеживается (`untracked`) или его нужно закоммитить",
            "Не включай его в обзор рабочего дерева",
            "Не упомянул ли я в финале внутренние файлы, статус Git и советы о коммите?",
        ),
    }
    for path, phrases in expected.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


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


def test_ui_browser_question_appears_only_after_stage2_surface_discovery():
    text = _flat(INSTALL)
    phrases = (
        "Do not ask about browser tooling merely because frontend files exist",
        "Only when the deployed UI is real and neither route exists",
        "may I connect Playwright MCP?",
        "This is another hard turn boundary",
        "Do not combine it with the stand, delivery, access, URL, or credentials questions",
    )
    for phrase in phrases:
        assert phrase in text, phrase

    stand_question = text.index("Is there a test or staging environment")
    access_question = text.index("How does a new version get there")
    surface_discovery = text.index("inspect the product surfaces")
    playwright_question = text.index("may I connect Playwright MCP?")
    assert stand_question < access_question < surface_discovery < playwright_question


def test_new_mcp_never_pretends_to_be_loaded_before_restart():
    expected = {
        INSTALL: (
            "Never claim that the current session can use a newly added MCP server",
            "fresh agent session, application restart, or extension restart",
            "tell the person explicitly",
            "Resume Stage 2 setup only after the restarted session can see the browser tool",
        ),
        SETUP_SKILLS[0]: (
            "Never claim that the current session can use a newly added MCP server",
            "fresh agent session, application restart, or extension restart",
            "tell the person explicitly",
            "Resume setup only after the restarted session can see the browser tool",
        ),
        SETUP_SKILLS[1]: (
            "Никогда не утверждай, что текущая сессия уже видит только что добавленный MCP",
            "нужна новая сессия агента, перезапуск приложения или расширения",
            "явно скажи об этом человеку",
            "Продолжай настройку только после того, как перезапущенная сессия увидит браузерный инструмент",
        ),
    }
    for path, phrases in expected.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


def test_ui_changes_require_real_browser_evidence_or_not_ready():
    expected = {
        RUNNER_SKILLS[0]: (
            "ask to connect Playwright MCP",
            "do not substitute HTTP calls or source inspection",
            "mark the UI cells `GAP` and return `NOT READY` for a UI change",
            "A backend-only change does not require browser evidence",
        ),
        RUNNER_SKILLS[1]: (
            "предложить подключить Playwright MCP",
            "не заменять его HTTP-вызовами или чтением исходников",
            "отметить UI-клетки как `GAP` и вернуть `NOT READY` для UI-изменения",
            "Backend-изменению не нужны браузерные доказательства",
        ),
    }
    for path, phrases in expected.items():
        text = _flat(path)
        for phrase in phrases:
            assert phrase in text, (path.name, phrase)


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
