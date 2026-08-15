<p align="center">
  <img src="docs/assets/hero.jpg" alt="Cerberus: a three-headed hound standing over a gate of fire, one head green, one amber, one red" width="100%">
</p>

<p align="center">
  <a href="https://github.com/concordloom/cerberus/actions/workflows/ci.yml"><img src="https://github.com/concordloom/cerberus/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-8a6cff" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex-skill-10a37f" alt="Codex skill">
</p>

# cerberus

**An adversarial verification gate for AI coding agents.** Before an agent tells
you a change works, it has to seriously try to prove it is broken — and fail.

[Русская версия](README.ru.md) · [The skill itself](plugins/cerberus/skills/cerberus/SKILL.md) ([ru](plugins/cerberus/skills/cerberus/SKILL.ru.md))

## Quick start

**Claude Code** — two commands, and the hooks are wired:

```
/plugin marketplace add concordloom/cerberus
/plugin install cerberus@concordloom
```

Then ask it to set the project up. It works out what your checks are, runs them,
and makes the gate refuse a claim in front of you:

```text
Checks I ran here, and will run before anyone says the work is done:
  ok       pytest -q

Tried it: saying the work was done was refused, and it named the edited file
```

**Codex**, and everything else reading `.agents/skills` — one command:

```console
gh skill install concordloom/cerberus --all --agent codex
```

Codex has no hook mechanism, so the gate is advisory there: followed when the
skill is invoked, not enforced on every turn.

Prefer the files committed in your own repository? See [Install](#install).

## What it does to your session

Two hooks and one rule.

**1.** Your agent edits source code. A hook writes the path down.

**2.** Your agent tries to end the turn with *"done, it works"*. The second hook
refuses:

```text
Cerberus gate: this message claims the work is ready, but source code was
edited and has not been verified.

Unverified files:
  - app/service.py
```

**3.** That record is cleared by one thing: a `READY` verdict, which costs
evidence.

Ordinary work is untouched — *"deployed to dev, running the check now"* ends a
turn fine. Only readiness claims are refused, and only while something is
unverified. A gate that interrupts normal work gets switched off, and a gate
that is off protects nothing.

## Three skills

| | refuses to let you say | until |
|---|---|---|
| **cerberus** | *"it works"* | a serious attempt to break the change has failed |
| **critic** | *"the cause is X"* | an independent adversary has tried to refute it |
| **setup** | *"it's installed"* | you have watched it refuse something |

The first two do not cover each other: work can be right while its explanation
is wrong, and a right explanation proves nothing ever ran.

## Install

**Claude Code, as a plugin.** Skill and hooks, wired, nothing to edit:

```
/plugin marketplace add concordloom/cerberus
/plugin install cerberus@concordloom
```

**Into your repository.** Files you can commit and a `cerberus.json` you can
edit. Nothing to clone — piped through `sh` the script fetches what it needs,
detects whether the project uses `.claude/` or `.agents/`, and is safe to
re-run:

```console
curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus/main/install.sh | sh -s -- --setup
```

**Codex, and everything else reading `.agents/skills`** — a directory it shares
with Copilot, Cursor, Gemini CLI and a dozen others, so one install serves them
all:

```console
gh skill install concordloom/cerberus cerberus --agent codex
```

Codex has no hook mechanism, so the gate is advisory there: followed when
invoked, not enforced on every turn. On Claude Code the Stop hook makes it
mechanical.

## The one thing to configure

`.claude/cerberus.json` declares your **delivery boundary** — what has to be
crossed before a change counts as checked. `setup` fills in everything it can
verify by running it, and leaves this field to you, because nothing can work it
out on your behalf:

| what you ship | the boundary Stage 2 has to cross |
|---|---|
| a service | a deployed instance, driven to a real result |
| a library | the built package, installed into a clean environment, imported |
| a CLI | the installed binary, real arguments, real exit codes |
| a chart or IaC module | applied to a real cluster or account |

Everything else has a working default. A gate that stays inert until someone
configures it is indistinguishable from no gate at all.

## The three heads

Each head is a stage, and its eye colour is that stage throughout the project.

| | Stage | |
|---|---|---|
| 🟢 | **Stage 0** | Enumerate the behaviour space before testing any of it |
| 🟡 | **Stage 1** | Break the code: consumption paths, completeness, negatives |
| 🔴 | **Stage 2** | Break it past the delivery boundary, with a check that can fail |

Skipping the first is the usual failure. The other two verify what you tried to
break; only Stage 0 decides what there was to break in the first place.

In practice that means four things:

- **Enumerate before testing.** Axes, their product, coverage marked per cell.
  Bugs live in the mixed cells — some entities succeeded, some failed. The tell
  for skipping it: *if the user is adding test cases for you, you skipped it.*
- **Trace the consumption path.** For everything the change writes, find
  everything that reads it at runtime. *"The endpoint returned 200"* is not
  *"the runtime uses this"*.
- **Make the check falsifiable.** Before the first real call, write down what
  would refute the fix. *"The logs looked quiet"* closes nothing, and an empty
  result set is a gap rather than a pass.
- **Report findings, not worries.** A finding is a reproduced failure with
  evidence. *"This could break"* is not one.

## Why

An agent built a feature, saw rows appear in the database and activity in the
logs, and reported *"works end to end"*. The credential it had written was
never read by anything at runtime. No real run had ever happened, and a day was
lost.

Every rule forbidding that already existed and was known. Which is the whole
argument for a hook rather than one more paragraph of advice.

## Requirements

Python 3.10+ for the hooks, and nothing else. The skill format and hook events
are [Claude Code](https://claude.com/claude-code)'s; the method in
[SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md) is not specific to any
agent and can be followed by hand.

MIT — see [LICENSE](LICENSE). Extracted from the internal engineering rules of
an AI automation platform, written after the incident above and hardened
against every later way the gate was found to be evadable.
