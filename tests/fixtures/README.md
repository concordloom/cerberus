# Fixture repositories

Each directory here is one project the skills are pointed at, plus the
expectations for what they must do with it.

```
<name>/repo/           the project tree, materialised into a scratch directory
<name>/expected.json    what a run against it must produce
```

Two consumers read the same pair, which is the point of the layout:

- `tests/test_fixtures.py` — cheap, no agent. It checks the tree and the
  expectations agree with each other, so a fixture cannot rot into something no
  live cell could ever satisfy.
- `verification.stage2` in `gopnik.json` — the live cells. They copy `repo/`
  into a scratch directory, run a real agent session against it, and hand
  `expected.json` to the matching oracle.

Before this directory existed the only fixture was a 1179-character `printf`
chain inside `gopnik.json`, and `scripts/check_live_setup_turn.py` held its
strings as literals. A second fixture meant copying the cell and forking the
oracle, which is why for a year there was exactly one.

## What lives in `expected.json`

Facts about *this project*: the command its Stage 1 runs, the delivery surfaces
it really has, the marker its check writes, the internal defects a critic finds
in it that must never be read aloud to the person being onboarded.

Not product rules. That the two-surface question is worded
`only <A>, only <B>, or both` is a rule from `SKILL.md` and stays in the oracle;
that *this* project's two surfaces are a command and a web interface is a fact
about the fixture and stays here.

## The gate pair

`gate-red-stage1` and `gate-ready-scoped` differ by one line of `app/cli.py`.
Everything else — `check.sh`, `AGENTS.md`, `gopnik.json` — is identical, so the
opposite verdicts they must produce cannot come from anything else.

One alone proves nothing. A gate that answers `NOT READY` to everything passes
`gate-red-stage1`; one that answers `READY` to everything passes
`gate-ready-scoped`. Only the pair is a check.
