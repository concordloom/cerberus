#!/bin/sh
# Install the cerberus skill into a project.
#
# Most people do not need this script.
#
#   Claude Code: `/plugin marketplace add concordloom/cerberus` then
#                `/plugin install cerberus@concordloom` — hooks included.
#   Codex, and everything else reading .agents/skills:
#                `gh skill install concordloom/cerberus cerberus --agent codex`
#                or `$skill-installer install <this repo>/tree/main/plugins/cerberus/skills/cerberus`
#
# What those do not do is put the files in your repository, wire the hooks into
# settings, or leave you a cerberus.json to edit. That is what this is for.
#
# Nothing has to be cloned first. From inside your project:
#
#   curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus/main/install.sh | sh
#
# or, from a clone:
#
#   sh install.sh              # detect what the project uses, install for it
#   sh install.sh --claude     # .claude/skills + hooks + settings wiring
#   sh install.sh --codex      # .agents/skills + hooks + .codex/hooks.json
#   sh install.sh --setup      # and run the setup step immediately afterwards
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
  SKILLS_SRC="$SRC/plugins/cerberus/skills"
  SKILL_SRC="$SKILLS_SRC/cerberus"
  HOOKS_SRC="$SRC/plugins/cerberus/hooks"
}

# Every skill under the plugin, not just the gate: the critic is the other half
# of the same cycle, and installing one of them is worse than installing
# neither, because the missing half is the one nobody notices is missing.
copy_skills() {
  for dir in "$SKILLS_SRC"/*/; do
    [ -f "$dir/SKILL.md" ] || continue
    name=$(basename "$dir")
    mkdir -p "$1/$name"
    cp "$dir/SKILL.md" "$1/$name/SKILL.md"
    say "${1#"$TARGET/"}/$name/SKILL.md"
  done
}
resolve

TARGET=$(pwd)
WANT_CLAUDE=0
WANT_CODEX=0
RUN_SETUP=0

while [ $# -gt 0 ]; do
  case "$1" in
    --claude) WANT_CLAUDE=1 ;;
    --codex)  WANT_CODEX=1 ;;
    --setup)  RUN_SETUP=1 ;;
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
  URL="https://codeload.github.com/concordloom/cerberus/tar.gz/$REF"

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$TMP/src.tar.gz"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP/src.tar.gz" "$URL"
  else
    echo "need curl or wget to fetch the skill, and found neither" >&2
    exit 1
  fi

  tar -xzf "$TMP/src.tar.gz" -C "$TMP"
  # Not `-name 'cerberus-*'`: GitHub names the extracted directory after
  # the repository, so pinning the repository name here means renaming the
  # repository breaks the one-liner — the install path the README puts first —
  # while the redirect works and every static check passes. There is exactly
  # one directory in the extraction; take it.
  SRC=$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)
  resolve

  if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
    echo "fetched $REF but the skill is not in it — report this at" >&2
    echo "https://github.com/concordloom/cerberus/issues" >&2
    exit 1
  fi
fi

echo "Installing cerberus into $TARGET"

if [ "$WANT_CLAUDE" -eq 1 ]; then
  mkdir -p "$TARGET/.claude/skills" "$TARGET/.claude/hooks"
  copy_skills "$TARGET/.claude/skills"
  cp "$HOOKS_SRC"/*.py "$TARGET/.claude/hooks/"
  say ".claude/hooks/cerberus_{mark,gate,config}.py"

  if [ ! -f "$TARGET/.claude/cerberus.json" ]; then
    cp "$SRC/cerberus.example.json" "$TARGET/.claude/cerberus.json"
    say ".claude/cerberus.json  (edit the verification block to describe this project)"
  else
    say ".claude/cerberus.json  (kept — already present)"
  fi

  # The marker is session state, not source. Left untracked and unignored it
  # shows up in `git status` for as long as it is set, which is most of the time
  # during real work. Read the marker path out of the config rather than
  # assuming the default, since it is a configurable key.
  # Unguarded, this exits the whole script under `set -e` when python3 is
  # missing — after the hooks are copied and before they are wired, which is
  # the worst state a gate can be left in: present and silent. The settings
  # block below is guarded for the same reason.
  MARKER=$(python3 - "$TARGET" 2>/dev/null <<'PY' || true
import json, pathlib, sys
target = pathlib.Path(sys.argv[1])
default = ".claude/.cerberus-pending"
try:
    raw = json.loads((target / ".claude" / "cerberus.json").read_text(encoding="utf-8"))
    print(raw.get("marker", default))
except Exception:
    print(default)
PY
)
  [ -n "$MARKER" ] || MARKER=".claude/.cerberus-pending"

  if [ ! -f "$TARGET/.gitignore" ] || ! grep -qxF "$MARKER" "$TARGET/.gitignore"; then
    # A .gitignore whose last line has no newline is common, and appending
    # blindly merges the marker onto that line — destroying both patterns and
    # leaving a second run unable to see its own entry.
    if [ -s "$TARGET/.gitignore" ] && [ -n "$(tail -c 1 "$TARGET/.gitignore")" ]; then
      printf '\n' >> "$TARGET/.gitignore"
    fi
    printf '%s\n%s\n' "$MARKER" "$MARKER.refusals" >> "$TARGET/.gitignore"
    say ".gitignore  (+ $MARKER)"
  else
    say ".gitignore  (kept — $MARKER already ignored)"
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
  mkdir -p "$TARGET/.agents/skills" "$TARGET/.codex/hooks"
  copy_skills "$TARGET/.agents/skills"
  cp "$HOOKS_SRC"/*.py "$TARGET/.codex/hooks/"
  say ".codex/hooks/cerberus_{mark,gate,config,setup}.py"

  # Codex reads .codex/hooks.json. Same events as Claude Code and the same
  # block protocol, so the hooks themselves are unchanged — only the wiring
  # lives somewhere else. Written whole rather than merged: unlike
  # settings.json this file is ours by convention, and clobbering somebody
  # else's hooks would be worse than refusing.
  if [ -f "$TARGET/.codex/hooks.json" ]; then
    say ".codex/hooks.json  (kept — already present; merge this yourself:)"
    echo
    sed 's/^/      /' "$SRC/examples/codex-hooks.json"
    echo
  else
    cp "$SRC/examples/codex-hooks.json" "$TARGET/.codex/hooks.json"
    say ".codex/hooks.json  (hooks declared — see below)"
  fi

  if [ ! -f "$TARGET/.claude/cerberus.json" ] && [ ! -f "$TARGET/.codex/cerberus.json" ]; then
    mkdir -p "$TARGET/.codex"
    sed 's|Copy to .claude/cerberus.json|Copy to .codex/cerberus.json|; s|".claude/.cerberus-pending"|".codex/.cerberus-pending"|' \
      "$SRC/cerberus.example.json" > "$TARGET/.codex/cerberus.json"
    say ".codex/cerberus.json  (edit the verification block to describe this project)"
  fi

  # The marker is session state on this agent too.
  if [ ! -f "$TARGET/.gitignore" ] || ! grep -qxF ".codex/.cerberus-pending" "$TARGET/.gitignore"; then
    if [ -s "$TARGET/.gitignore" ] && [ -n "$(tail -c 1 "$TARGET/.gitignore")" ]; then
      printf '\n' >> "$TARGET/.gitignore"
    fi
    printf '%s\n%s\n' ".codex/.cerberus-pending" ".codex/.cerberus-pending.refusals" >> "$TARGET/.gitignore"
    say ".gitignore  (+ .codex/.cerberus-pending)"
  fi

  echo
  echo "One more step, and it is not optional: Codex does not run a project's"
  echo "hooks until you trust them. Run /hooks in Codex and approve these two."
  echo "It asks again whenever they change."
  if [ "$RUN_SETUP" -eq 1 ]; then
    echo
    echo "Then set the checks up — --setup does not run for Codex yet:"
    echo "    python3 .codex/hooks/cerberus_setup.py"
  fi
fi

echo
if [ "$WANT_CLAUDE" -eq 1 ]; then
  # The example configuration's checks are placeholders, so at this point the
  # gate refuses claims while checking nothing. Setup is what closes that, and
  # it is the difference between installed and working — so it is offered as
  # the next step rather than left to be discovered.
  if [ "$RUN_SETUP" -eq 1 ] && command -v python3 >/dev/null 2>&1; then
    # Not `|| true`: that turned a refusal into a silent success and left the
    # gate installed and unwired with exit 0 — a third route to the state this
    # whole project is about.
    if python3 "$TARGET/.claude/hooks/cerberus_setup.py" --dir "$TARGET"; then
      :
    else
      echo
      echo "Setup did not finish — see above. The files are installed; what is"
      echo "missing is the part setup reports."
      exit 1
    fi
  else
    if [ "$RUN_SETUP" -eq 1 ]; then
      echo "No python3 here, so the setup step was skipped."
      echo
    fi
    echo "One more step — it sets up the checks and shows you it working:"
    echo
    echo "    python3 .claude/hooks/cerberus_setup.py"
    echo
    echo "Until then it will refuse claims without checking anything."
  fi
else
  echo "Done. Invoke the skill before claiming a change works."
fi
