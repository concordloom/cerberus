#!/usr/bin/env python3
"""Keep Gopnik's public and runtime identity free of the retired brand."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OLD = "cer" + "berus"
OLD_CYRILLIC = "цер" + "бер"
ALLOWED_HISTORY = {
    "CHANGELOG.md",
    "docs/migration-v4.md",
    "docs/migration-v4.ru.md",
    "tests/test_brand.py",
}


def repository_files() -> list[pathlib.Path]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return [ROOT / raw.decode() for raw in proc.stdout.split(b"\0") if raw]


def test_public_identity_has_no_legacy_brand() -> None:
    leaks: list[str] = []
    for path in repository_files():
        relative = path.relative_to(ROOT).as_posix()
        if relative in ALLOWED_HISTORY or not path.exists():
            continue
        if path.is_symlink():
            text = str(path.readlink())
        else:
            data = path.read_bytes()
            if b"\0" in data:
                continue
            text = data.decode("utf-8", errors="ignore")
        lowered = text.lower()
        if OLD in lowered or OLD_CYRILLIC in lowered:
            leaks.append(relative)
    assert not leaks, f"legacy brand leaked outside migration/history: {leaks}"


def test_canonical_product_surface_exists() -> None:
    expected = [
        "gopnik.json",
        "gopnik.example.json",
        "plugins/gopnik/.claude-plugin/plugin.json",
        "plugins/gopnik/skills/gopnik/SKILL.md",
        "plugins/gopnik/skills/gopnik-critic/SKILL.md",
        "plugins/gopnik/skills/gopnik-setup/SKILL.md",
        "plugins/gopnik/skills/gopnik-setup/gopnik_setup.py",
    ]
    missing = [path for path in expected if not (ROOT / path).exists()]
    assert not missing, f"canonical Gopnik files missing: {missing}"


def test_manifests_publish_only_gopnik() -> None:
    marketplace = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
    assert [entry["name"] for entry in marketplace["plugins"]] == ["gopnik"]
    assert marketplace["plugins"][0]["source"] == "./plugins/gopnik"
    plugin = json.loads(
        (ROOT / "plugins/gopnik/.claude-plugin/plugin.json").read_text()
    )
    assert plugin["name"] == "gopnik"
    assert plugin["displayName"] == "Gopnik"


def test_skill_names_and_ui_metadata_match_their_directories() -> None:
    skills = ROOT / "plugins/gopnik/skills"
    for skill in sorted(path for path in skills.iterdir() if path.is_dir()):
        body = (skill / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = body.split("---", 2)[1]
        assert f"name: {skill.name}\n" in frontmatter, skill.name
        metadata = (skill / "agents/openai.yaml").read_text(encoding="utf-8")
        for key in ("display_name:", "short_description:", "default_prompt:"):
            assert key in metadata, (skill.name, key)
        assert f"${skill.name}" in metadata, skill.name


def _main() -> int:
    failures = 0
    for name, fn in sorted(globals().items()):
        if not name.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  ok   {name}")
        except Exception as exc:
            failures += 1
            print(f"  FAIL {name}: {exc}")
    print(f"\n{'FAILED' if failures else 'all tests passed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
