---
name: setup
description: Work out this project's checks by running them, and write them into cerberus.json so the other two skills stop guessing. Use when asked to install or configure cerberus, or when its config still holds the example placeholders.
when_to_use: On a first install; when cerberus.json still holds the example placeholders; when the checks it lists no longer match what this project actually runs.
---

# Setup — find this project's checks by running them

The gate checks work and the critic checks claims. Neither can know what
`pytest -q` means in *this* repository, or where a change stops being under
your control once it ships. This finds out, by running things, and writes down
only what actually passed.

## Why this exists

A fresh install ships a `cerberus.json` whose checks are `echo` placeholders.
An `echo` exits 0 unconditionally, so a verification that runs one is
indistinguishable from a verification that ran nothing — and it looks finished.
That is the same failure the gate exists to catch, arriving through its own
front door.

## Run it

```sh
python3 "$CLAUDE_PLUGIN_ROOT"/skills/setup/cerberus_setup.py   # installed as a plugin
python3 .claude/skills/setup/cerberus_setup.py                 # installed by install.sh
python3 .agents/skills/setup/cerberus_setup.py                 # Codex and anything reading .agents
```

Whichever exists. `--check` runs the checks and writes nothing. The config it
writes belongs to the project, not to an agent: an existing
`.claude/cerberus.json` or `.codex/cerberus.json` is kept where it is, and a
project with neither gets `cerberus.json` in its root.

## What it writes, and what it never touches

It writes the `verification` block: `artifact_kind`, `stage1`, `stage2`,
`notes`. Nothing else, and nothing it did not run first — a command that was
never executed is the placeholder again with better wording.

It merges rather than replaces, one level down as well as at the top. A
hand-written `artifact_kind: migration` — a value detection can never produce —
and notes naming production accounts have both been destroyed by a version that
rewrote the block wholesale.

`stage2` is left empty on purpose. This script cannot run a deploy or build a
package during setup, and writing a comment line into a list of commands would
be the placeholder again, since a `#` line also exits 0. The sentence is handed
to the reader instead.

## When it refuses to guess

A project it cannot recognise gets an honest refusal and two plain questions,
not a plausible configuration. This is deliberate and it is not a failure mode:
a confident wrong configuration is worse than the placeholder it replaced,
because the placeholder is visibly unfinished and the wrong one is not.

The same applies when the checks it found do not pass here. That is a fact
about the project, and it is reported rather than quietly dropped so the
configuration can look tidy.

## Say it in ordinary words

Whoever is being set up did not ask for vocabulary. Tell them what was written,
what is still missing, and that nothing runs by itself — the skills are theirs
to invoke by name, and choosing when is their call, not ours. Everything else
belongs in the other two skills.

## Self-check before saying it is set up

- [ ] Was every check written into the configuration actually run first, with
      its result shown?
- [ ] Was an existing configuration merged into rather than replaced, including
      keys this script would never produce?
- [ ] Is `stage2` either genuinely filled in or reported as still missing,
      rather than padded with something that exits 0?
- [ ] Does the closing message say what was written, what is missing, and that
      invoking the skills is the reader's own call?
