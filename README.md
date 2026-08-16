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

**Claude Code** — two commands:

```
/plugin marketplace add concordloom/cerberus
/plugin install cerberus@concordloom
```

**Codex** — one command, in the session:

```
$skill-installer install https://github.com/concordloom/cerberus/tree/main/plugins/cerberus/skills/cerberus
```

Swap `cerberus` at the end for `critic` or `setup` to add the other two.

**Or put the files in your own repository** — the three skills and a
`cerberus.json` you can commit. Nothing to clone, and safe to re-run:

```console
curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus/main/install.sh | sh -s -- --setup
```

Either way, ask your agent to set the project up. It works out what your checks
are by running them, and writes down the ones that pass:

```text
Set up: Python library — change that if it is wrong.

Checks I ran here and wrote down:
  ok       pytest -q
```

## Now what?

Ask for the cerberus skill when a change deserves it — before a release, after
a fix you are not sure of, whenever "it works" is about to be said out loud.
The agent then runs the three stages against your project's own checks and
comes back with a verdict instead of a claim.

Your agent may also reach for it unasked. The skill's description names the
words "done" and "it works" as the moment it is for, and an agent that has read
that will sometimes act on it — Codex did, on a request that mentioned neither
verification nor cerberus. That is the agent exercising judgement about your
work, not something this project switched on, and you can tell it not to.

Here is a real one, from a session asked to add a function *and report it done*:

```text
Stage 0 — matrix: type {int, float, bool, Decimal, complex} x ordering x
  non-numeric x arity x consumption path. All meaningful cells verified live.
Stage 1 — compileall green, pytest green.
Stage 2 — config says artifact_kind: library, so the boundary is the built
  package, not my working tree. Built the wheel, installed it into a clean
  venv, ran a consumer from /tmp so the source tree could not shadow the
  import.
The oracle can return BROKEN. I mutated the installed file to `return b - a`
  and re-ran: 3 failures, exit 1. Restored: exit 0.
```

It read `artifact_kind: library` out of `cerberus.json` and worked out for
itself that the built wheel was the thing to test, not the working tree. That is
what the file is for.

The cost is real: that took minutes rather than seconds. Which is exactly why
deciding *when* it is worth paying is left to you.

## What it does to your session

Nothing runs. There is no hook, no background process, and no file of yours
that installing edits — the whole delivery is three skill directories and one
config you own. Uninstalling is deleting them.

That is deliberate. A gate that interrupts on its own guess about which turns
matter gets switched off, and a gate that is off protects nothing. So the
judgement is left where it already lives — with you, and with the agent you are
working with, which can weigh what it is about to claim in a way no file
matcher can.

No model is called and nothing goes over the network. The setup step runs your
own checks locally, once, and writes down which ones passed.

## The three heads

The three heads on the gate are the three stages the agent owes you before it
says a change works.

| | Stage | What the agent has to do |
|---|---|---|
| 🟢 | **0** | Enumerate the behaviour space, before testing any of it |
| 🟡 | **1** | Break the code: consumption paths, completeness, negative cases |
| 🔴 | **2** | Break it past the delivery boundary, with a check that can fail |

Skipping the first is the usual failure. The other two verify what you tried to
break; only Stage 0 decides what there was to break in the first place. All of
it, at the length an agent needs, is in
[SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md).

## The one thing to configure

Stage 2 has to cross your **delivery boundary** — the first thing that stops
being under your control once the change ships. Nothing can work that out for
you, so it is the one field `cerberus.json` leaves to you:

| what you ship | what Stage 2 has to reach |
|---|---|
| a service | a deployed instance, driven to a real result |
| a library | the built package, installed into a clean environment, imported |
| a CLI | the installed binary, real arguments, real exit codes |
| a chart or IaC module | applied to a real cluster or account |
| a migration | a copy of real shape and scale |
| a prompt or parser | a real model call through the production entry point |
| a plugin or codegen | a real downstream project built with it |

The value goes in `artifact_kind` — `service`, `library`, `cli`, `chart`,
`migration`, `model-boundary`, `plugin` — one row each, in that order.

If you have nothing to deploy, Stage 2 narrows to consuming the artifact you
built in a clean environment, and everything past that is declared `Not proven`
rather than assumed.

## What goes in cerberus.json

One block, and it is a note rather than a program. `artifact_kind` names your
delivery boundary, `stage1` is the commands to run locally, `stage2` is what has
to be reached past that boundary, and `notes` is anything the agent should know
— which account, which environment, what must never be touched.

No program reads any of it. The skills do, and getting it wrong costs an agent
some wasted work rather than silently weakening anything. Setup writes
`artifact_kind` and `stage1` after running the commands; `stage2` is left empty
on purpose, because a placeholder that exits 0 is worse than an obvious gap.

## The critic, which is not the gate

Three skills ship together. The gate asks whether the thing does what you say it
does. The critic asks whether what you *said* is true — a diagnosis, a
mechanism, a claim about the codebase — by spawning an adversary whose mandate
is to refute it.

Neither covers the other: work can be right while its explanation is wrong, and
a right explanation proves nothing ever ran.

The third, `setup`, is the install step above. It works out what your checks are
by running them, writes them down, and stops. Run it again any time with
`python3 .claude/skills/setup/cerberus_setup.py`, or ask the agent for it by
name.

## Why

An agent built a feature, saw rows appear in the database and activity in the
logs, and reported *"works end to end"*. The credential it had written was
never read by anything at runtime. No real run had ever happened, and a day was
lost.

The method in SKILL.md is what catches that. Making it fire automatically was a
second idea, tried for seven versions and dropped: it could tell that code had
changed, never whether the change mattered, and being wrong about that is how
tools get uninstalled.

## Requirements

Python 3.10+ for the setup script, and nothing else. The skill format is
[Claude Code](https://claude.com/claude-code)'s and Codex's; the method in
[SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md) is not specific to any
agent and can be followed by hand.

## License and origin

MIT — see [LICENSE](LICENSE). Extracted from the internal engineering rules of
an AI automation platform, written after the incident above and hardened
against every later way the gate was found to be evadable.
