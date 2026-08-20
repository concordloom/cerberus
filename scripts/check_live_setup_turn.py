#!/usr/bin/env python3
"""Fail closed on the user-visible checkpoints in the live setup conversation."""

from __future__ import annotations

import json
import pathlib
import re
import shlex
import sys


LANGUAGE_QUESTION = "Which language would you like me to use: English or Russian?"
SCOPE_QUESTION = (
    "Where should I install Gopnik: for this agent across your projects, "
    "or only in this repository so the team receives it with the project?"
)
SCOPE_QUESTION_RU = (
    "Куда установить Gopnik: для этого агента во всех ваших проектах или "
    "только в этот репозиторий, чтобы команда получала его вместе с проектом?"
)
STAND_QUESTION = (
    "Is there a test or staging environment where Gopnik can verify the "
    "deployed version?"
)
ACCESS_QUESTION = (
    "How does a new version get there, and how can the agent obtain access? "
    "Do not send secrets; just name the existing access method."
)
STAND_QUESTION_RU = (
    "Есть ли стенд, на котором Gopnik сможет проверить уже развёрнутую версию?"
)
STAND_RESPONSE = (
    "Stage 2 checks the built or deployed result where people actually use it. "
    + STAND_QUESTION
)
STAND_RESPONSE_RU = (
    "Stage 2 проверяет собранный или развёрнутый результат там, где им реально пользуются. "
    + STAND_QUESTION_RU
)
ACCESS_QUESTION_RU = (
    "Как новая версия попадает на стенд и как агенту получить к нему доступ? "
    "Секреты присылать не нужно — достаточно назвать существующий способ доступа."
)
CRITIC_COMPLETE_MARKER = "GOPNIK_CRITIC_STATUS: complete"
CRITIC_BLOCKED_MARKER = "GOPNIK_CRITIC_STATUS: blocked"
CRITIC_SURFACES_MARKER = "GOPNIK_CRITIC_SURFACES:"
RAW_INSTALL_URL = (
    "https://raw.githubusercontent.com/concordloom/gopnik/main/docs/install.md"
)
SURFACES_QUESTION = (
    "After delivery, do people use only the command, only the web interface, or both?"
)
SURFACES_QUESTION_RU = (
    "После поставки люди используют только команду, только веб-интерфейс или оба варианта?"
)


def fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


def records(path: pathlib.Path) -> list[object]:
    raw = path.read_text(encoding="utf-8")
    try:
        return [json.loads(raw)]
    except json.JSONDecodeError:
        parsed = []
        for number, line in enumerate(raw.splitlines(), 1):
            if not line.strip():
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {number} is not JSON: {exc}") from exc
        return parsed


def final_result(items: list[object]) -> tuple[int, str]:
    found = [
        (index, " ".join(item["result"].split()))
        for index, item in enumerate(items)
        if isinstance(item, dict) and isinstance(item.get("result"), str)
    ]
    if len(found) != 1 or found[0][0] != len(items) - 1:
        raise ValueError("the transcript must end with exactly one final result event")
    return found[0]


def one_question(result: str) -> bool:
    return result.count("?") == 1


def nested_dicts(value: object):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from nested_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from nested_dicts(item)


def text_values(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_values(item)


def tool_results(items: list[object], tool_use_id: str) -> list[tuple[int, dict]]:
    found = []
    for index, item in enumerate(items):
        for value in nested_dicts(item):
            if (
                value.get("type") == "tool_result"
                and value.get("tool_use_id") == tool_use_id
            ):
                found.append((index, value))
    return found


def tool_uses(items: list[object]) -> list[dict]:
    return [
        value
        for item in items
        for value in nested_dicts(item)
        if value.get("type") == "tool_use"
    ]


def raw_guide_fetch(value: dict) -> bool:
    name = str(value.get("name") or "").lower()
    payload = value.get("input")
    serialized = json.dumps(payload, ensure_ascii=False)
    if serialized.count(RAW_INSTALL_URL) != 1:
        return False
    if name in {"webfetch", "web_fetch"}:
        return (
            isinstance(payload, dict)
            and payload.get("url") == RAW_INSTALL_URL
            and set(payload) <= {"url", "prompt"}
        )
    if name != "bash" or not isinstance(payload, dict):
        return False
    command = payload.get("command")
    if not isinstance(command, str) or re.search(r"[;#|&<>\n\r`]", command) or "$(" in command:
        return False
    try:
        argv = shlex.split(command)
    except ValueError:
        return False
    if not argv or argv[-1] != RAW_INSTALL_URL:
        return False
    if argv[0] == "curl":
        allowed = {
            "-f", "-s", "-S", "-L", "-fsSL", "-sSL", "-sSfL",
            "--fail", "--silent", "--show-error", "--location",
        }
        return all(item in allowed for item in argv[1:-1])
    if argv[0] == "wget":
        options = argv[1:-1]
        return options in (
            ["-qO-"],
            ["-O", "-"],
            ["-q", "-O", "-"],
            ["--output-document=-"],
            ["--quiet", "--output-document=-"],
        )
    return False


def raw_guide_tool_discovery(value: dict) -> bool:
    payload = value.get("input")
    return (
        str(value.get("name") or "").lower() == "toolsearch"
        and isinstance(payload, dict)
        and payload.get("query") == "select:WebFetch"
        and set(payload) <= {"query", "max_results"}
    )


def pure_python_helper_argv(command: object) -> list[str] | None:
    if not isinstance(command, str):
        return None
    if re.search(r"[;#|&<>\n\r`]", command) or "$(" in command:
        return None
    try:
        argv = shlex.split(command)
    except ValueError:
        return None
    if (
        len(argv) < 2
        or argv[0] != "python3"
        or pathlib.PurePosixPath(argv[1]).name != "gopnik_setup.py"
    ):
        return None
    return argv


def stage1_events(items: list[object], expected_language: str) -> list[tuple[int, str]]:
    found = []
    for index, item in enumerate(items):
        for value in nested_dicts(item):
            if value.get("type") != "tool_use":
                continue
            name = str(value.get("name") or "").lower()
            payload = value.get("input")
            command = payload.get("command") if isinstance(payload, dict) else None
            argv = pure_python_helper_argv(command)
            if argv is None:
                continue
            stage1_indexes = [i for i, item in enumerate(argv) if item == "--stage1"]
            language_indexes = [i for i, item in enumerate(argv) if item == "--language"]
            if (
                name == "bash"
                and len(argv) == 7
                and argv.count("--defer-artifact-kind") == 1
                and len(stage1_indexes) == 1
                and stage1_indexes[0] + 1 < len(argv)
                and argv[stage1_indexes[0] + 1] == "./check.sh"
                and len(language_indexes) == 1
                and language_indexes[0] + 1 < len(argv)
                and argv[language_indexes[0] + 1] == expected_language
                and isinstance(value.get("id"), str)
            ):
                found.append((index, value["id"]))
    return found


def confirmation_events(items: list[object]) -> list[tuple[int, str]]:
    found = []
    for index, item in enumerate(items):
        for value in nested_dicts(item):
            if value.get("type") != "tool_use":
                continue
            name = str(value.get("name") or "").lower()
            payload = value.get("input")
            command = payload.get("command") if isinstance(payload, dict) else None
            argv = pure_python_helper_argv(command)
            if (
                name == "bash"
                and argv is not None
                and len(argv) == 4
                and argv[2:] == ["--confirm-artifact-kind", "service"]
                and isinstance(value.get("id"), str)
            ):
                found.append((index, value["id"]))
    return found


def critic_agent_events(items: list[object]) -> list[tuple[int, str]]:
    found = []
    for index, item in enumerate(items):
        for value in nested_dicts(item):
            if value.get("type") != "tool_use":
                continue
            name = str(value.get("name") or "").lower()
            payload = value.get("input")
            serialized = json.dumps(payload, ensure_ascii=False).lower()
            if (
                name in ("agent", "task")
                and "gopnik-critic" in serialized
                and CRITIC_COMPLETE_MARKER.lower() in serialized
                and CRITIC_BLOCKED_MARKER.lower() in serialized
                and CRITIC_SURFACES_MARKER.lower() in serialized
                and isinstance(value.get("id"), str)
            ):
                found.append((index, value["id"]))
    return found


def successful_result(value: dict, required: str | None = None) -> bool:
    if value.get("is_error") is True:
        return False
    payload = value.get("content")
    if payload in (None, "", [], {}):
        return False
    content = json.dumps(payload, ensure_ascii=False).lower()
    return (
        required is None or required.lower() in content
    )


def candidate_is_named(candidate: str, result: str, russian: bool) -> bool:
    candidate = candidate.replace("_", "-").strip().lower()
    patterns = {
        "command": r"\b(?:command|command-line|cli)\b" if not russian else r"\b(?:команд\w*|cli)\b",
        "command-line": r"\b(?:command|command-line|cli)\b" if not russian else r"\b(?:команд\w*|cli)\b",
        "cli": r"\b(?:command|command-line|cli)\b" if not russian else r"\b(?:команд\w*|cli)\b",
        "web": r"\b(?:web interface|web ui|dashboard)\b" if not russian else r"\b(?:веб-интерфейс\w*|интерфейс\w*|web ui|dashboard)\b",
        "web-ui": r"\b(?:web interface|web ui|dashboard)\b" if not russian else r"\b(?:веб-интерфейс\w*|интерфейс\w*|web ui|dashboard)\b",
        "web-interface": r"\b(?:web interface|web ui|dashboard)\b" if not russian else r"\b(?:веб-интерфейс\w*|интерфейс\w*|web ui|dashboard)\b",
        "dashboard": r"\b(?:web interface|web ui|dashboard)\b" if not russian else r"\b(?:веб-интерфейс\w*|интерфейс\w*|web ui|dashboard)\b",
        "ui": r"\b(?:web interface|web ui|dashboard|ui)\b" if not russian else r"\b(?:веб-интерфейс\w*|интерфейс\w*|web ui|dashboard|ui)\b",
        "migration": r"\bmigration\w*\b" if not russian else r"\bмиграц\w*\b",
        "package": r"\bpackage\w*\b" if not russian else r"\bпакет\w*\b",
        "library": r"\blibrar\w*\b" if not russian else r"\bбиблиотек\w*\b",
        "plugin": r"\bplugin\w*\b" if not russian else r"\bплагин\w*\b",
        "service": r"\bservice\w*\b" if not russian else r"\bсервис\w*\b",
        "api": r"\bapi\b",
        "mobile-ui": r"\bmobile\b" if not russian else r"\bмобильн\w*\b",
        "job": r"\b(?:job|background)\b" if not russian else r"\b(?:задач\w*|фонов\w*)\b",
        "chart": r"\bchart\w*\b" if not russian else r"\bчарт\w*\b",
        "release": r"\brelease\w*\b" if not russian else r"\bрелиз\w*\b",
    }
    pattern = patterns.get(candidate)
    if pattern is not None:
        return re.search(pattern, result.lower()) is not None
    return candidate.replace("-", " ") in result.lower()


def completed_fixture_critic_result(value: dict, result: str, russian: bool) -> bool:
    if not successful_result(value):
        return False
    lines = [
        line.strip()
        for line in "\n".join(text_values(value.get("content"))).splitlines()
        if line.strip()
    ]
    if len(lines) < 2 or lines[-1] != CRITIC_COMPLETE_MARKER:
        return False
    if not lines[-2].startswith(CRITIC_SURFACES_MARKER):
        return False
    if any(line.startswith(CRITIC_SURFACES_MARKER) for line in lines[:-2]):
        return False
    surfaces = lines[-2][len(CRITIC_SURFACES_MARKER):].strip().lower()
    candidates = {item.strip() for item in surfaces.split(",") if item.strip()}
    canonical = set()
    for candidate in candidates:
        if candidate in {"command", "command-line", "cli"}:
            canonical.add("command")
        elif candidate in {"web", "web-ui", "web-interface", "dashboard", "ui"}:
            canonical.add("web")
        else:
            canonical.add(candidate)
    if canonical != {"command", "web"}:
        return False
    if not result.endswith("?"):
        return False
    question = re.split(r"(?<=[.!?])\s+", result)[-1]
    return all(
        candidate_is_named(candidate, question, russian) for candidate in candidates
    )


def main(argv: list[str]) -> int:
    if len(argv) not in (3, 4):
        return fail(
            "usage: check_live_setup_turn.py "
            "LANGUAGE|SCOPE|SURFACES|STAND|ACCESS and -RU variants "
            "TRANSCRIPT [STAGE1_MARKER]"
        )

    mode = argv[1].lower()
    path = pathlib.Path(argv[2])
    try:
        items = records(path)
        result_index, result = final_result(items)
    except (OSError, ValueError) as exc:
        return fail(str(exc))

    if mode == "language":
        calls = tool_uses(items)
        if result != LANGUAGE_QUESTION:
            return fail(result)
        safe_bootstrap = (
            not calls
            or (len(calls) == 1 and raw_guide_fetch(calls[0]))
            or (
                len(calls) == 2
                and raw_guide_tool_discovery(calls[0])
                and raw_guide_fetch(calls[1])
            )
        )
        if not safe_bootstrap:
            return fail("tool activity occurred before the language hard boundary")
        return 0

    if mode == "scope":
        if tool_uses(items):
            return fail("tool activity occurred before the installation-scope answer")
        return 0 if result == SCOPE_QUESTION else fail(result)

    if mode == "scope-ru":
        if tool_uses(items):
            return fail("tool activity occurred before the Russian installation-scope answer")
        return 0 if result == SCOPE_QUESTION_RU else fail(result)

    lower = result.lower()
    if mode in ("surfaces", "surfaces-ru"):
        russian = mode.endswith("-ru")
        if len(argv) != 4:
            return fail("Stage 1 marker is absent")
        try:
            marker = pathlib.Path(argv[3]).read_text(encoding="utf-8")
        except OSError:
            return fail("Stage 1 marker is absent")
        if marker != "stage1-ran":
            return fail("Stage 1 marker has the wrong value")
        stage1_calls = stage1_events(items, "ru" if russian else "en")
        if not stage1_calls:
            return fail("the live trace does not show the Stage 1 setup command")
        stage1_call_index, stage1_id = stage1_calls[0]
        stage1_results = [
            (index, value)
            for index, value in tool_results(items, stage1_id)
            if successful_result(
                value, "Stage 1 set up. Delivery surfaces still need confirmation."
            )
        ]
        if not stage1_results:
            return fail("the Stage 1 helper has no successful result")
        stage1_result_index = stage1_results[0][0]

        critic_calls = critic_agent_events(items)
        if not critic_calls:
            return fail("the live trace does not show an independent gopnik-critic agent")
        critic_call_index, critic_id = critic_calls[0]
        critic_results = [
            (index, value)
            for index, value in tool_results(items, critic_id)
            if completed_fixture_critic_result(value, result, russian)
        ]
        if not critic_results:
            return fail("the independent critic has no completed surface analysis")
        critic_result_index = critic_results[0][0]
        if not (
            stage1_call_index
            < stage1_result_index
            < critic_call_index
            < critic_result_index
            < result_index
        ):
            return fail("Stage 1, independent critic, and user question are out of order")
        banned_terms = [
            "gopnik.json",
            "artifact_kind",
            "setuptools",
            "package discovery",
            "workflow has no checkout",
            "missing deploy",
            "deploy.sh",
        ]
        if russian:
            banned_terms.extend(("ошибк", "отсутствующ", "дефект workflow"))
        for banned in banned_terms:
            if banned in lower:
                return fail(f"internal defect detail leaked: {banned}")
        stages = [lower.find(label) for label in ("stage 0", "stage 1", "stage 2")]
        if any(index < 0 for index in stages) or stages != sorted(stages):
            return fail("the three-stage orientation is absent or out of order")
        bounded = "после" in lower if russian else "after stage 1" in lower
        if lower.count("stage 2") != 1 or not bounded:
            return fail("Stage 2 was not bounded behind Stage 1")
        green = (
            re.search(r"(?:^|[.!?]\s+)stage 1 (?:готова|прошла)(?:[.!?:]|$)", lower)
            if russian
            else re.search(r"(?:^|[.!?]\s+)stage 1 (?:passed|is ready)(?:[.!?]|$)", lower)
        )
        if not green:
            return fail("the response does not report the green Stage 1 result")
        question_shape = (
            r"только .+только .+или оба"
            if russian
            else r"only .+only .+(?:or )?both"
        )
        if not re.search(question_shape, lower):
            return fail("the response does not ask one concrete surfaces question")
        command_shape = r"\b(команд\w*|cli)\b" if russian else r"\b(command|command-line|cli)\b"
        if not re.search(command_shape, lower):
            return fail("the fixture's command surface is absent")
        web_shape = r"\b(веб-интерфейс\w*|интерфейс\w*|web ui)\b" if russian else r"\b(web interface|dashboard|web ui)\b"
        if not re.search(web_shape, lower):
            return fail("the fixture's web surface is absent")
        if not one_question(result):
            return fail("the surfaces turn must contain exactly one question")
        if not result.endswith("?"):
            return fail("the surfaces turn must end with its hard-boundary question")
        expected_question = SURFACES_QUESTION_RU if russian else SURFACES_QUESTION
        question = re.split(r"(?<=[.!?])\s+", result)[-1]
        if question != expected_question:
            return fail("the hybrid fixture's canonical surfaces question is absent")
        extra_surface_terms = (
            r"\b(?:миграц\w*|пакет\w*|библиотек\w*|плагин\w*|сервис\w*|"
            r"api|http|мобильн\w*|фонов\w*|задач\w*|чарт\w*|релиз\w*|"
            r"разв[её]рт\w*)\b"
            if russian
            else r"\b(?:migration\w*|package\w*|librar\w*|plugin\w*|service\w*|"
                 r"api|http|mobile\w*|background\w*|job\w*|chart\w*|release\w*|"
                 r"deploy\w*)\b"
        )
        if re.search(extra_surface_terms, lower):
            return fail("a non-surviving fixture surface leaked into the user turn")
        if len(result.split()) > 140:
            return fail("the surfaces turn is too long")
        if russian:
            letters = [character for character in result if character.isalpha()]
            cyrillic = [
                character
                for character in letters
                if ("а" <= character.lower() <= "я") or character.lower() == "ё"
            ]
            if not letters or len(cyrillic) / len(letters) < 0.65:
                return fail("the Russian turn contains too much non-Russian prose")
            for english in ("here is", "checks the", "after delivery", "i found"):
                if english in lower:
                    return fail(f"English onboarding leaked into the Russian turn: {english}")
        return 0

    if mode == "stand":
        expected_stand = STAND_RESPONSE
    elif mode == "stand-ru":
        expected_stand = STAND_RESPONSE_RU
    else:
        expected_stand = None

    if expected_stand is not None:
        if result != expected_stand:
            return fail("the stand turn is not the one focused question")
        if len(tool_uses(items)) != 1:
            return fail("the stand turn contains tool activity beyond kind confirmation")
        calls = confirmation_events(items)
        if len(calls) != 1:
            return fail("the stand turn does not show one exact artifact-kind confirmation")
        call_index, tool_id = calls[0]
        completed = [
            (index, value)
            for index, value in tool_results(items, tool_id)
            if successful_result(
                value,
                "Confirmed artifact kind 'service' in gopnik.json. "
                "Stage 1 checks were preserved and not rerun.",
            )
        ]
        if len(completed) != 1 or not (call_index < completed[0][0] < result_index):
            return fail("artifact-kind confirmation did not complete before the stand question")
        return 0

    if mode == "access":
        if tool_uses(items):
            return fail("tool activity occurred before the delivery/access answer")
        return 0 if result == ACCESS_QUESTION else fail(
            "the delivery/access turn is not the safe focused question"
        )

    if mode == "access-ru":
        if tool_uses(items):
            return fail("tool activity occurred before the Russian delivery/access answer")
        return 0 if result == ACCESS_QUESTION_RU else fail(
            "the Russian delivery/access turn is not the safe focused question"
        )

    return fail(f"unknown mode: {mode}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
