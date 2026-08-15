<p align="center">
  <img src="docs/assets/hero.jpg" alt="Cerberus: a three-headed hound standing over a gate of fire, one head green, one amber, one red" width="100%">
</p>

<p align="center">
  <a href="https://github.com/concordloom/cerberus-skill/actions/workflows/ci.yml"><img src="https://github.com/concordloom/cerberus-skill/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
  <img src="https://img.shields.io/badge/Claude%20Code-plugin-8a6cff" alt="Claude Code plugin">
  <img src="https://img.shields.io/badge/Codex-skill-10a37f" alt="Codex skill">
</p>

# cerberus-skill

**An adversarial verification gate for AI coding agents.** Before an agent tells
you a change works, it has to seriously try to prove it is broken — and fail.

[Русская версия](README.ru.md) · [The skill itself](plugins/cerberus/skills/cerberus/SKILL.md) ([ru](plugins/cerberus/skills/cerberus/SKILL.ru.md))

## The problem

An agent builds a feature, sees rows appear in the database and activity in the
logs, and reports "works end to end". The credential it wrote was never resolved
at runtime by anything. No real run had ever happened.

That is not a model being careless. It is a structural property of how
verification usually goes: the author checks their own work, along the path they
already have in mind, and everything they look at agrees with them. Written
instructions do not fix it — the rules forbidding all of it already existed and
were known.

## What this is

Four things that work together:

1. **A skill** ([SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md)) describing what verification has to
   consist of: enumerate the behaviour space before testing it, trace what reads
   the values you write, and then try to break the change past its delivery
   boundary with a check that could actually come back `BROKEN`.
2. **A second skill, [the critic](plugins/cerberus/skills/critic/SKILL.md)**, for the other half of the
   cycle. The gate asks whether the thing does what you say it does; the critic
   asks whether what you *said* is true — a diagnosis, a mechanism, a claim
   about the codebase — by spawning an adversary whose mandate is to refute it.
   Work can be right while its explanation is wrong, and a right explanation
   proves nothing ran, so neither covers the other.
3. **Two hooks** that make it mechanical rather than a matter of memory. One
   records that executable code changed; the other refuses to let a turn end
   with a readiness claim while that record stands.
4. **A verdict** that is either `READY` with evidence, or `NOT READY` with
   reproductions. Only `READY` clears the record.

## The three heads

Each head is a stage, and its eye colour is that stage throughout the project —
in the mark, in the documentation, everywhere.

| | Stage | What it does |
|---|---|---|
| 🟢 | **Stage 0** | Enumerate the behaviour space before testing any of it |
| 🟡 | **Stage 1** | Break the code: consumption paths, completeness, negatives |
| 🔴 | **Stage 2** | Break it past the delivery boundary, with a falsifiable check |

Skipping the first is the usual failure. The other two verify what you tried to
break; only Stage 0 decides what there was to break in the first place.

## Install

### Claude Code — two commands

```
/plugin marketplace add concordloom/cerberus-skill
/plugin install cerberus@concordloom
```

That is all. The skill and both hooks are installed and wired; there is nothing
to copy and no settings file to edit.

### Codex — one command

```console
gh skill install concordloom/cerberus-skill cerberus --agent codex
```

Nothing special is needed for this: the repository is laid out the way the
ecosystem expects, `gh skill` finds the skill on its own — *"found 1 skill using
the plugins/ convention"* — and pins the install to the latest release tag.
Inside Codex, `$skill-installer` takes the same thing as a URL:

```console
$skill-installer install https://github.com/concordloom/cerberus-skill/tree/main/plugins/cerberus/skills/cerberus
```

Both land in `.agents/skills`, which Codex shares with Copilot, Cursor, Gemini
CLI and a dozen others, so the same install serves them too.

They install the skill and nothing else, which on Codex is the whole story: it
has no hook mechanism, so the gate is advisory there — followed when invoked
rather than enforced on every turn. On Claude Code the Stop hook makes it
mechanical.

### Or commit the files to your repository

When you would rather have the thing in the project — the skill, the hooks and a
`cerberus.json` to edit — the installer does that, and wires the hooks into
settings where they exist:

```console
curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus-skill/main/install.sh | sh
```

There is nothing to clone: piped through `sh`, the script fetches what it needs.
It detects whether the project uses `.claude/` or `.agents/`, installs into the
right place, and is safe to re-run.

Nothing needs configuring to start. Every key has a working default, because a
gate that stays inert until someone configures it is indistinguishable from no
gate at all. When you are ready, describe your project's delivery boundary in
`.claude/cerberus.json` so Stage 2 is a fact rather than a guess.

## What it actually asks for

**Enumerate before you test.** Write down the axes of the feature and their
cartesian product, mark coverage per cell, and pay attention to the mixed cells —
some entities succeeded, some failed. Bugs live there. There is a tell for
skipping this step: *if the user is adding test cases for you, you skipped it.*

**Trace the consumption path.** For everything the change writes, find
everything that reads it at runtime. "The endpoint returned 200" is not "the
runtime uses this".

**Cross the delivery boundary.** Verification on your own terms — your tree,
your fixtures, your imports — cannot see what only breaks elsewhere. Find the
boundary by asking *what is the first thing that stops being under my control*,
and verify from its far side, using the artifact as produced.

For a service that is a deployed instance. For a library it is the built package
installed into a clean environment and imported as a consumer would — which is
where a missing export or an incompatible dependency range lives, invisible to
every in-repo test, because those import from source.

**Make the check falsifiable.** Before the first real call, write down what would
refute the fix: the incompleteness hypothesis, the adverse precondition, the
evidence that the adverse path was actually reached, and a failure oracle that
can return `BROKEN`. "The logs looked quiet" proves nothing and closes nothing.
An empty result set is a gap, not a pass.

**Report findings, not worries.** A finding is a reproduced failure with
evidence. "This could break" is not one. A gate that cries wolf gets switched
off, and a gate that is off protects nothing.

## Requirements

Python 3.10+ for the hooks. Nothing else.

The skill format and hook events are those of [Claude
Code](https://claude.com/claude-code); the method in `SKILL.md` is not specific
to any agent and can be followed by hand.

## Origin and license

Extracted from the internal engineering rules of an AI automation platform,
where it was written after the incident described above and hardened against
every subsequent way the gate was found to be evadable. MIT — see
[LICENSE](LICENSE).
