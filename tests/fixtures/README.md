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

## The surface pair

`gate-surface-gap` and `gate-surface-covered` are one project with two confirmed
delivery surfaces — an installed command and a chart somebody else applies —
recorded in `verification.surfaces`. The gap side crosses only the command, and
its chart really is broken in the way an uncrossed surface gets broken: the image
tag it ships sits three minor versions behind its own `appVersion`, which no step
in that configuration would ever read. The covered side crosses both and is
clean.

The pair exists because neither side alone is a check. A gate that answers
`NOT READY` whenever a configuration names more than one surface passes the gap
side; one that treats a filled `stage2` as "run it and stop" passes the covered
side, since the run is green. Only the two together separate those.

What the pair does **not** prove is that a run read `verification.surfaces`. An
adversary scored six strategies against both sides and three passed without ever
touching the key: reading the answer out of `notes`, comparing `stage2` against
the directory listing, and simply checking whether the prompt was true. The first
and the third were accidents of how the fixtures were written and are gone — the
`notes` are identical on both sides now, and neither chart is defective. The
second is not an accident and stays: a run can re-derive coverage from the tree,
which the skill forbids and which no pair of fixtures can make impossible,
because the tree is where surfaces come from in the first place.

## The gate pair

`gate-red-stage1` and `gate-ready-scoped` differ by one line of `app/cli.py`.
Everything else — `check.sh`, `AGENTS.md`, `gopnik.json` — is identical, so the
opposite verdicts they must produce cannot come from anything else.

One alone proves nothing. A gate that answers `NOT READY` to everything passes
`gate-red-stage1`; one that answers `READY` to everything passes
`gate-ready-scoped`. Only the pair is a check.
