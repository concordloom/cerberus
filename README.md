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

**Codex** — one command, in the session:

```
$skill-installer install https://github.com/concordloom/cerberus/tree/main/plugins/cerberus/skills/cerberus
```

Swap `cerberus` at the end for `critic` or `setup` to add the other two.

Either way, then ask it to set the project up. It works out what your checks
are, runs them, and makes the gate refuse a claim in front of you:

```text
Checks I ran here, and will run before anyone says the work is done:
  ok       pytest -q

Tried it: saying the work was done was refused, and it named the edited file
```

Codex has no hook mechanism, so the gate is advisory there: followed when the
skill is invoked, not enforced on every turn. On Claude Code the Stop hook
makes it mechanical.

**Or put the files in your own repository** — the skill, the hooks and a
`cerberus.json` you can commit. Nothing to clone; it detects whether the
project uses `.claude/` or `.agents/`, and is safe to re-run:

```console
curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus/main/install.sh | sh -s -- --setup
```

## What it does to your session

Two hooks and one rule.

**1.** Your agent edits source code — a `.py`, a `.ts`, a `.go`; not a test, not
a doc. A hook writes the path down.

**2.** Your agent tries to end the turn with *"done, it works"*. The second hook
refuses:

```text
Cerberus gate: this message claims the work is ready, but source code was
edited and has not been verified.

Unverified files:
  - app/service.py
```

**3.** The note stays until the agent has run the two stages below and cleared
it. Nothing stops it from deleting the file instead — this is a speed bump
against drift, not a guard against an adversary.

Ordinary work is untouched: *"deployed to dev, running the check now"* ends a
turn fine. Only readiness claims are refused, and only while something is
unverified. A gate that interrupts normal work gets switched off, and a gate
that is off protects nothing.

No model is called and nothing goes over the network — it is two short Python
scripts and a file.

## The three heads

The three heads on the gate are the three stages the agent owes you before that
note comes off.

🟢 **Stage 0** — enumerate the behaviour space before testing any of it.
🟡 **Stage 1** — break the code: consumption paths, completeness, negatives.
🔴 **Stage 2** — break it past the delivery boundary, with a check that can fail.

Skipping the first is the usual failure. The other two verify what you tried to
break; only Stage 0 decides what there was to break in the first place. All of
it, at the length an agent needs, is in
[SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md).

## The one thing to configure

Stage 2 has to cross your **delivery boundary** — the first thing that stops
being under your control once the change ships. Nothing can work that out for
you, so it is the one field `.claude/cerberus.json` leaves to you:

| what you ship | what Stage 2 has to reach |
|---|---|
| a service | a deployed instance, driven to a real result |
| a library | the built package, installed into a clean environment, imported |
| a CLI | the installed binary, real arguments, real exit codes |
| a chart or IaC module | applied to a real cluster or account |
| a migration | a copy of real shape and scale |
| a prompt or parser | a real model call through the production entry point |
| a plugin or codegen | a real downstream project built with it |

If you have nothing to deploy, Stage 2 narrows to consuming the artifact you
built in a clean environment, and everything past that is declared `Not proven`
rather than assumed.

## When it gets in your way

It will. The gate is a regular expression over your agent's last message, and
the default list includes `\bdone\b` — a word people use for things that are
not readiness claims.

Everything is in `.claude/cerberus.json`:

- **it fired when it shouldn't** — narrow `claim_patterns`. Careful: that key
  **replaces** the default list rather than adding to it, so a short list makes
  the gate quietly weaker than it looks. That is the one edit worth making
  slowly;
- **it is holding a note you have dealt with** — the file is
  `.claude/.cerberus-pending`, one path per line, and it survives across
  sessions;
- **you want it off** — remove the two hooks from `.claude/settings.json`, or
  uninstall the plugin. It is a hook, not a daemon.

## The critic, which is not the gate

The same install carries a second skill. The gate asks whether the thing does
what you say it does. The critic asks whether what you *said* is true — a
diagnosis, a mechanism, a claim about the codebase — by spawning an adversary
whose mandate is to refute it.

Neither covers the other: work can be right while its explanation is wrong, and
a right explanation proves nothing ever ran.

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

## License and origin

MIT — see [LICENSE](LICENSE). Extracted from the internal engineering rules of
an AI automation platform, written after the incident above and hardened
against every later way the gate was found to be evadable.
