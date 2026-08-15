#!/bin/sh
# Install the cerberus skill into a project.
#
# Claude Code users do not need this: `/plugin marketplace add
# concordloom/cerberus-skill` followed by `/plugin install cerberus@concordloom`
# does everything, hooks included. This script exists for Codex, for other
# agents, and for anyone who would rather have the files in the repository.
#
# Nothing has to be cloned first. From inside your project:
#
#   curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus-skill/main/install.sh | sh
#
# or, from a clone:
#
#   sh install.sh              # detect what the project uses, install for it
#   sh install.sh --claude     # .claude/skills + hooks + settings wiring
#   sh install.sh --codex      # .agents/skills (no hooks: Codex has no equivalent)
#   sh install.sh --dir PATH   # install into PATH instead of the current directory
#
# Piped through sh, arguments go after -s --, e.g. `| sh -s -- --codex`.
# Set CERBERUS_REF to install from a branch or tag other than main.
#
# Re-running is safe: existing files are overwritten, existing configuration is
# left alone.

set -eu

REF=${CERBERUS_REF:-main}
SRC=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

resolve() {
  SKILL_SRC="$SRC/plugins/cerberus/skills/cerberus"
  HOOKS_SRC="$SRC/plugins/cerberus/hooks"
}
resolve

TARGET=$(pwd)
WANT_CLAUDE=0
WANT_CODEX=0

while [ $# -gt 0 ]; do
  case "$1" in
    --claude) WANT_CLAUDE=1 ;;
    --codex)  WANT_CODEX=1 ;;
    --dir)    shift; TARGET=$1 ;;
    -h|--help) awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

if [ "$WANT_CLAUDE" -eq 0 ] && [ "$WANT_CODEX" -eq 0 ]; then
  # Nothing asked for explicitly: install for whatever the project already uses,
  # and default to Claude Code when the project uses neither.
  [ -d "$TARGET/.claude" ] && WANT_CLAUDE=1
  [ -d "$TARGET/.agents" ] && WANT_CODEX=1
  if [ "$WANT_CLAUDE" -eq 0 ] && [ "$WANT_CODEX" -eq 0 ]; then
    WANT_CLAUDE=1
  fi
fi

say() { printf '  %s\n' "$1"; }

# Piped straight from the network there is no source tree next to the script, so
# fetch one. This is the whole difference between a two-step install and a
# one-liner, and it is the path most people will take.
if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
  TMP=$(mktemp -d)
  trap 'rm -rf "$TMP"' EXIT INT TERM
  URL="https://codeload.github.com/concordloom/cerberus-skill/tar.gz/$REF"

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$TMP/src.tar.gz"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP/src.tar.gz" "$URL"
  else
    echo "need curl or wget to fetch the skill, and found neither" >&2
    exit 1
  fi

  tar -xzf "$TMP/src.tar.gz" -C "$TMP"
  SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d -name 'cerberus-skill-*' | head -n 1)
  resolve

  if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
    echo "fetched $REF but the skill is not in it — report this at" >&2
    echo "https://github.com/concordloom/cerberus-skill/issues" >&2
    exit 1
  fi
fi

echo "Installing cerberus into $TARGET"

if [ "$WANT_CLAUDE" -eq 1 ]; then
  mkdir -p "$TARGET/.claude/skills/cerberus" "$TARGET/.claude/hooks"
  cp "$SKILL_SRC/SKILL.md" "$TARGET/.claude/skills/cerberus/SKILL.md"
  cp "$HOOKS_SRC"/*.py "$TARGET/.claude/hooks/"
  say ".claude/skills/cerberus/SKILL.md"
  say ".claude/hooks/cerberus_{mark,gate,config}.py"

  if [ ! -f "$TARGET/.claude/cerberus.json" ]; then
    cp "$SRC/cerberus.example.json" "$TARGET/.claude/cerberus.json"
    say ".claude/cerberus.json  (edit the verification block to describe this project)"
  else
    say ".claude/cerberus.json  (kept — already present)"
  fi

  # Wiring the hooks means merging into a JSON file the user owns. Do it only
  # when it can be done without guessing, and print the snippet otherwise: a
  # corrupted settings.json is a far worse outcome than a manual paste.
  if python3 - "$TARGET" "$SRC" >/dev/null <<'PY'
import json, pathlib, sys

target, src = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
settings = target / ".claude" / "settings.json"
wanted = json.loads((src / "examples" / "settings.json").read_text(encoding="utf-8"))["hooks"]

data = {}
if settings.exists():
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except Exception:
        sys.exit(1)  # unreadable: do not touch it

hooks = data.setdefault("hooks", {})
changed = False
for event, entries in wanted.items():
    bucket = hooks.setdefault(event, [])
    for entry in entries:
        command = entry["hooks"][0]["command"]
        already = any(
            command in h.get("command", "")
            for existing in bucket
            for h in existing.get("hooks", [])
        )
        if not already:
            bucket.append(entry)
            changed = True

if changed:
    settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

PY
  then
    say ".claude/settings.json  (hooks wired)"
  else
    say ".claude/settings.json  could not be updated automatically — add this yourself:"
    echo
    sed 's/^/      /' "$SRC/examples/settings.json"
    echo
  fi
fi

if [ "$WANT_CODEX" -eq 1 ]; then
  mkdir -p "$TARGET/.agents/skills/cerberus"
  cp "$SKILL_SRC/SKILL.md" "$TARGET/.agents/skills/cerberus/SKILL.md"
  say ".agents/skills/cerberus/SKILL.md"
  say "note: Codex has no hook mechanism, so the gate is advisory there —"
  say "      the skill is followed when invoked, not enforced on every turn."
fi

echo
echo "Done. Invoke the skill before claiming a change works."
