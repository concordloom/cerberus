<p align="center">
  <img src="docs/assets/hero.jpg" alt="Cerberus: a three-headed hound standing over a gate of fire, one head green, one amber, one red" width="100%">
</p>

<p align="center">
  <a href="https://github.com/concordloom/cerberus/actions/workflows/ci.yml"><img src="https://github.com/concordloom/cerberus/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-8a6cff" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex-plugin-10a37f" alt="Codex plugin">
</p>

# cerberus

**An adversarial verification gate for AI coding agents.** Before an agent tells
you a change works, it has to seriously try to prove it is broken — and fail.

[Русская версия](README.ru.md) · [The skill itself](plugins/cerberus/skills/cerberus/SKILL.md) ([ru](plugins/cerberus/skills/cerberus/SKILL.ru.md))

## Install

### For yourself

Installs for you, in every project you open. Nothing is written to the repository.

**Claude Code**

```
/plugin marketplace add concordloom/cerberus
/plugin install cerberus@concordloom
```

**Codex**

```
codex plugin marketplace add concordloom/cerberus
codex plugin add cerberus@concordloom
```

### Into the repository

Copies the skills into the project, so the whole team and CI get them from git,
committed.

```console
curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus/main/install.sh | sh -s -- --setup
```

## Uninstall

**Claude Code**

```
/plugin uninstall cerberus@concordloom
```

**Codex**

```
codex plugin remove cerberus@concordloom
```

**Installed into the repository** — delete `.claude/skills/cerberus`, `critic`
and `setup`, and `cerberus.json` if you no longer want it.

## Quick start

**1. Ask your agent to set the project up.** It finds your checks, runs them and
writes down the ones that pass. The output is English — the agent reads it and
tells you in yours.

```text
Set up: Python library — change that if it is wrong.

Checks I ran here and wrote down:
  ok       pytest -q
```

**2. Ask for the cerberus skill before saying a change works.** It runs the three
stages against those checks and comes back with a verdict instead of a claim,
which takes minutes rather than seconds. Your agent may also reach for it
unasked: the skill names "done" and "it works" as the moment it is for, and one
that has read that sometimes acts on it.

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

If your deploy runs in CI, Stage 2 is push, wait for the pipeline, and then
prove the instance answering you is *this* commit — waiting is not verifying.
Ask the agent to run `setup` with `--draft-stage2`: it reads your `helm/`,
manifests, compose file or deploy job and prints those commands, with the traps
in them named.

If there is genuinely nowhere to deploy, do not leave `stage2` empty: write
`stage2_unreachable` with the reason. Every verdict then narrows to
`READY scope: Stage 1` and quotes it. Empty reads as nobody got round to it; a
reason reads as a decision.

## What goes in cerberus.json

One block, and it is a note rather than a program. `artifact_kind` names your
delivery boundary, `stage1` is the commands to run locally, `stage2` is what has
to be reached past that boundary, and `notes` is anything the agent should know
— which account, which environment, what must never be touched.

No program reads any of it. The skills do, and getting it wrong costs an agent
some wasted work rather than silently weakening anything. Setup writes
`artifact_kind` and `stage1` after running the commands; `stage2` it drafts but
never writes, because a placeholder that exits 0 is worse than an obvious gap.
Once you do fill it in, running it is no longer optional — that is the point of
writing it down.

Upgrading and removing are the plugin commands you installed with: `/plugin` or
`codex plugin`, by name. The installer route is the files themselves.

## The critic, which is not the gate

Three skills ship together. The gate asks whether the thing does what you say it
does. The critic asks whether what you *said* is true — a diagnosis, a
mechanism, a claim about the codebase — by spawning an adversary whose mandate
is to refute it.

Neither covers the other: work can be right while its explanation is wrong, and
a right explanation proves nothing ever ran.

The third, `setup`, is the install step above. It works out what your checks are
by running them, writes them down, and stops. Ask the agent for it by name to
run it again — it knows where its own script is, which differs by how you
installed: inside the plugin, or in `.claude/skills/setup/` if you used the
installer.

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
