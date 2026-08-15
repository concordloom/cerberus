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

## From discussion to issue to work

Work here starts from an issue, and the issue is written **before** the work.
That is not process for its own sake: the gate is only as good as the claim it
is aimed at, and a claim written afterwards is whatever the change happened to
do.

The mechanics are two commands, both of which read the skills rather than
repeating them:

| | |
|---|---|
| `/issue` | ends a discussion by opening the issue it was heading towards |
| `/work <n>` | takes that issue through matrix → work → critic → gate → verdict |

[The issue form](.github/ISSUE_TEMPLATE/work.yml) requires one field that the
rest of the cycle depends on: **what would settle it** — the observation that
decides, stated so it could come back negative. An issue that cannot answer it
is not ready to be worked, and saying so is a real answer. Blank issues are
disabled so nothing skips the field; questions belong in Discussions.

Two things then happen in the open, on the issue itself:

- **the Stage 0 matrix is posted before the work.** This is what makes the tell
  checkable rather than a matter of memory — if someone adds cases after your
  matrix, you skipped Stage 0;
- **the verdict is posted after it**, with the evidence. An issue closed without
  one is a claim nobody checked.

One caveat worth knowing, because it bit this repository. The hooks in
`.claude/settings.json` are loaded from the project the session is working in.
Editing this repository from a session rooted somewhere else means they never
fire — the gate is not in the loop at all, and the dogfooding above is nominal.
Work on this repository from this repository.

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
claude plugin marketplace add concordloom/cerberus
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
git clone https://github.com/concordloom/cerberus /tmp/src
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

## Language

The project is English. Code, comments, documentation, CI, issues and **commit
messages** are written in English.

The one exception is the translated skill: `SKILL.ru.md` and `README.ru.md`
exist so the method is usable by people who work in Russian, and they are the
only Russian prose here. Russian also appears as *data* — the claim patterns the
gate matches, and the fixtures that test them — which is not the same thing.

Commit messages are not a matter of taste in this repository: the changelog and
the release notes are **generated from them**, so a Russian commit would put
Russian into an English changelog.

Commits before the policy was set are in Russian. History is not being rewritten
for it — a force-push over published commits costs more than the inconsistency.

## Releasing

Releases are automatic. [semantic-release](https://semantic-release.gitbook.io)
runs on every push to `main`, works out the next version from the commit
messages, writes the changelog, tags, and publishes a GitHub Release.

Which means the commit type decides the version:

| Commit | Version |
|---|---|
| `fix: …` | patch |
| `feat: …` | minor |
| `feat!: …` or a `BREAKING CHANGE:` footer | major |
| `docs:`, `chore:`, `test:`, `ci:`, `refactor:` | no release |

What deserves which, for this project:

- **major** — the verdict contract changes, or an installation stops working
  without manual steps.
- **minor** — the skill gains a requirement, a stage or an axis; the hooks gain
  behaviour.
- **patch** — wording, typography, packaging and defect fixes that leave what the
  gate demands unchanged.

The release writes the new version into **both** manifests
(`scripts/set_version.py`) and commits them back. That is not bookkeeping: a
marketplace plugin is pinned to the `version` in its entry, so an existing
installation receives an update **only when that string changes**. A release that
merely tagged would reach nobody, silently.

## Changing the skill text

Both language versions must change together. `scripts/check_parity.py` compares
heading structure, checklist length and code-block count — it will fail the build
if one version grows a section the other does not have.

It deliberately says nothing about the prose. Two translations should differ in
wording; they must not differ in what they require.
