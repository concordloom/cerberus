---
name: setup
description: Set this project up for the verification gate and prove it fires, before telling anyone it is installed. Use when asked to install, configure or enable cerberus, or when the gate is present but checking nothing.
when_to_use: On a first install; when .claude/cerberus.json still holds the example placeholders; when someone asks whether the gate is actually on.
---

# Setup — install it, then watch it refuse something

The third head. The gate checks work, the critic checks claims, and this puts
both in place — then makes the gate refuse a claim in front of you, because
"installed" and "working" are different words and only one of them is worth
saying.

## Why this exists

The installer copies an example configuration whose checks are `echo`
placeholders. The refusing half then works — a claim that the work is done gets
blocked — while the checks it points at pass unconditionally. Armed and
checking nothing is worse than not installed at all, because it looks finished.
That is the same failure the gate exists to catch, arriving through its own
front door.

## Run it

```sh
python3 .claude/hooks/cerberus_setup.py           # set up, then demonstrate
python3 .claude/hooks/cerberus_setup.py --check   # run the checks, write nothing
```

That path exists after `install.sh`. Installed as a plugin the scripts live
under the plugin directory instead, and on Codex they are not installed at all
— there are no hooks there, so there is nothing to set up and the gate is
advisory. Find the script rather than assuming the path.

It finds the toolchain, runs each candidate check **here** before writing it
down, saves the ones that pass, and finishes by marking a scratch file,
claiming the work is done, and showing the refusal. Then it clears up after
itself.

## What it must never do

It writes only the `verification` block. The four tuning keys —
`claim_patterns`, `ignore_patterns`, `source_extensions`, `watch_paths` —
**replace** the built-in lists rather than extending them, so a helpful guess
makes the gate quietly narrower than advertised. A weakened gate that nobody
knows is weakened is the worst artifact this project could ship, so those keys
are never written by a machine.

Nor does it write a check it has not run. A command that was never executed is
the placeholder again with better wording.

## When it refuses to guess

A project it cannot recognise gets an honest refusal and two plain questions,
not a plausible configuration. This is deliberate and it is not a failure mode:
a confident wrong configuration is worse than the placeholder it replaced,
because the placeholder is visibly unfinished and the wrong one is not.

The same applies when the checks it found do not pass here. That is a fact
about the project, and it is reported rather than quietly dropped so the
configuration can look tidy.

## If nothing is calling it

Running the scripts directly proves they work and nothing else. They only run
by themselves when the project's settings name them, and a project where they
are installed but unnamed behaves exactly like a project where they are absent
— except that it looks installed. Setup checks the settings separately and says
so plainly when the wiring is missing.

## Say it in ordinary words

Whoever is being set up did not ask for vocabulary. Tell them what changed,
what happens the next time they say the work is done, and how to switch it off.
Everything else belongs in the other two skills.

## Self-check before saying it is set up

- [ ] Was every check written into the configuration actually run first, with
      its result shown?
- [ ] Was the refusal demonstrated, rather than described — and did a claim
      with nothing outstanding still go through?
- [ ] Are the four replacing keys absent from anything that was written?
- [ ] Does the closing message say what changed, what happens next time, and
      how to turn it off, without borrowing words from the other skills?
