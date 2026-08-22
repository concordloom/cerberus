# Contributing to Gopnik

Gopnik verifies its own changes. Before claiming that a contribution works,
run the repository checks and then cross the delivery boundary named in
[`gopnik.json`](gopnik.json).

## Development loop

Work starts from a falsifiable claim: what observation would settle the task,
including the result that would prove the proposed change wrong.

The repository ships two Claude commands for its own workflow:

| Command | Purpose |
| --- | --- |
| `/issue` | turn a discussion into a testable work item |
| `/work <n>` | run matrix → work → critic → Gopnik → verdict |

The command is convenience, not enforcement. No hook or daemon runs the cycle
automatically.

For a normal change:

1. State the Stage 0 matrix before editing.
2. Implement the change without overwriting unrelated worktree changes.
3. Run `gopnik-critic` on any important diagnosis or design claim.
4. Run Stage 1.
5. Run the relevant Stage 2 cells on the exact delivered revision.
6. Publish a scoped Gopnik verdict with evidence and anything not proven.

If a blocker is fixed, the old verdict is void. Run a fresh round on the new
fingerprint.

## Stage 1

Run the same commands recorded in `gopnik.json`:

```console
python3 -m compileall -q plugins scripts tests
python3 tests/test_fixtures.py
python3 tests/test_setup.py
python3 tests/test_commands.py
python3 tests/test_readme.py
python3 tests/test_guides.py
python3 tests/test_brand.py
python3 scripts/check_parity.py
sh -n install.sh
```

`git diff --check` should also be clean. Run the skill validator for every
shipped skill after changing its frontmatter or layout.

## Stage 2

This repository ships a plugin. Its delivery boundaries are the native plugin
loader, the repository-local installer, and a real agent session. Static tests
cannot prove those surfaces.

The executable Stage 2 route lives in `gopnik.json`. It authenticates nothing:
an isolated temporary host configuration, asserted empty before the loader runs
and credential-free after, the marketplace and all three skills installed into
it, the raw installer run from a clone pinned to the exact pushed revision over
a file the project already owned, and the fixture pack exercised by its own test
from that clone. Then it removes its temporary state.

Do not call a local clone or unpushed commit full Stage 2: the marketplace and
raw installer consume GitHub. The remote revision must match the local commit
under verdict.

### The one thing Stage 2 does not run

**Stage 2 does not run a live agent session**, so it does not prove that the
skills behave as written when an agent actually follows them. That is the one
surface no static check reaches, and it is deliberately manual.

It is manual because the route used to do it automatically and took the
operator's login to do so — a symlink from `~/.claude/.credentials.json` into
two `CLAUDE_CONFIG_DIR` trees, which reads as isolation and is not. A live run
refreshed the token; an OAuth refresh token is **single-use**, so the operator's
own file kept a credential the server had already invalidated, and every session
using it was logged out mid-work. A verification step that can do that to the
person running it is worse than the coverage it buys.

Run the conversations by hand when a change touches the skills' behaviour, with
a credential issued for verification and **never your working login**:

```console
export CLAUDE_CONFIG_DIR=$(mktemp -d)      # log in separately, in this tree only
cp -r tests/fixtures/stage1-gap/repo /tmp/gap && cd /tmp/gap
claude -p 'Set up Gopnik for this project.' --session-id "$SESSION" \
  --permission-mode bypassPermissions --output-format stream-json --verbose > turn.jsonl
python3 scripts/check_live_setup_turn.py --fixture tests/fixtures/stage1-gap \
  coverage turn.jsonl
```

`scripts/check_live_setup_turn.py` reads a conversation turn — modes `language`,
`scope`, `coverage`, `surfaces`, `stand`, `access` and their `-ru` variants —
and `scripts/check_live_gate_turn.py` reads a whole gate run against a fixture
directory. Both fail closed, and `tests/test_fixtures.py` proves they can fail.

A verdict that has not run these says so, rather than leaving the absence to be
inferred.

## Product identity

The canonical public and runtime identifiers are:

- repository: `concordloom/gopnik`;
- plugin: `gopnik@concordloom`;
- skills: `gopnik`, `gopnik-critic`, `gopnik-setup`;
- configuration: `gopnik.json`;
- setup helper: `gopnik_setup.py`;
- protocol variables and markers: `GOPNIK_*`.

The retired identity is allowed only in the historical changelog and the
version 4 migration guides. `tests/test_brand.py` enforces that boundary.

## English and Russian

English is canonical for code, comments, issues, commits, and release notes.
Public README and skill instructions have full Russian editorial versions.

Change each EN/RU pair together. `scripts/check_parity.py` compares structure,
fences, and checklist length; editorial review must still check meaning and
natural language.

Russian text uses guillemets, em dashes, non-breaking spaces after single-letter
prepositions and conjunctions, and a single-character ellipsis.

## Release

[semantic-release](https://semantic-release.gitbook.io) runs on pushes to
`main`, derives the next version from commit messages, updates both manifests,
writes the changelog, tags the commit, and creates a GitHub Release.

| Commit | Release |
| --- | --- |
| `fix: …` | patch |
| `feat: …` | minor |
| `feat!: …` or `BREAKING CHANGE:` | major |
| `docs:`, `test:`, `ci:`, `chore:` | none |

An identity or installation cutover is a breaking release. A new capability is
minor; a compatible defect fix is patch.

Do not edit only one manifest version. `scripts/set_version.py` owns both.
