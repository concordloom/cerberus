# Contributing

## This repository runs its own gate

Cerberus is enabled here, on itself. `.claude/settings.json` wires the hooks
straight into `plugins/cerberus/hooks/` — there is one copy of each script, not a
vendored duplicate that could drift from the published one.

That is not a gimmick. A verification tool nobody verifies is the thing it warns
about, and the two worst defects this project has shipped so far were both
readiness claims made without crossing the boundary.

Before saying a change works, run the skill and finish both stages. The commands
for this repository are declared in [`.claude/cerberus.json`](.claude/cerberus.json).

## Stage 1 — what the working tree can prove

```console
python3 -m compileall -q plugins scripts tests
python3 tests/test_hooks.py
python3 scripts/check_parity.py
sh -n install.sh
```

## Stage 2 — what only the loader can prove

The delivery boundary of this artifact is the **plugin loader**, not a server.
No static check reaches it: validating the manifests confirms one reading of the
documentation, and the loader has its own.

Both defects found on 2026-08-15 passed every static check.

- `"source": "cerberus"` with `metadata.pluginRoot` — a form the documentation
  permits and the loader rejects with `source: Invalid input`.
- `"hooks": "./hooks/hooks.json"` in the manifest — `hooks/hooks.json` is loaded
  by convention, so declaring it registered the same file twice and the plugin
  failed to load *after installing successfully*.

So:

```console
export CLAUDE_CONFIG_DIR=$(mktemp -d)     # never the real one: it changes your own session
claude plugin marketplace add concordloom/cerberus-skill
claude plugin install cerberus@concordloom
claude plugin list                        # Status must read: ✔ enabled
claude plugin details cerberus            # Skills (1), Hooks (2)
```

Two traps worth stating, because both have already cost time:

- The marketplace installs **from GitHub**. Verifying an unpushed fix proves
  nothing. Push first.
- Run `claude plugin marketplace update` before reinstalling, or you are testing
  the cached copy of the previous version.

Then check the installer, which is a second and independent boundary — it does
not go through the loader at all:

```console
git clone https://github.com/concordloom/cerberus-skill /tmp/src
mkdir /tmp/proj && cd /tmp/proj && sh /tmp/src/install.sh
```

…and drive the installed gate: mark a source edit, claim readiness, and confirm
the hook answers `decision: block`. A gate that installs but does not fire is
indistinguishable from no gate.

## Russian text

The Russian documents are translations of the English ones, which are canonical.
CI checks that their structure matches; it cannot check that they are well
written.

Run Russian text through [`ru-text`](https://github.com/talkstream/ru-text)
before committing it. At minimum, the typography rules it enforces:

- guillemets `«…»` for quotes, `„…“` nested;
- em dash `—` in prose, en dash `–` in ranges, hyphen only in compounds;
- a non-breaking space after the single-letter prepositions and conjunctions
  `в к с о у и а`, so they do not end up stranded at the end of a line;
- `…` as one character.

The last one is not cosmetic at this length: the skill text runs to several
hundred lines, and a stranded preposition on every third line reads as
carelessness in a document whose whole subject is care.

## Changing the skill text

Both language versions must change together. `scripts/check_parity.py` compares
heading structure, checklist length and code-block count — it will fail the build
if one version grows a section the other does not have.

It deliberately says nothing about the prose. Two translations should differ in
wording; they must not differ in what they require.
