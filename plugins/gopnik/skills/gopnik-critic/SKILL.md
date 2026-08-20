---
name: gopnik-critic
description: >
  Adversarial review of a claim before it is published. Use before publishing a
  diagnosis, an explanation of a mechanism, a conclusion that implies work, or
  a retelling of another review, including saying "the cause is X", "this is not
  our bug", "the class is closed", or "this will prevent it".
---

# Critic — adversarial review of claims

A mandatory attempt to **refute the claim**, run before publishing it. The
companion to the gate, and not a substitute for it: the gate examines the
**work**, this examines what you **say about** it.

Use the top-level `language` value from `gopnik.json` (`en` or `ru`) for the
operator-facing review. If it is absent, keep the current conversation
language.

## Why this exists

An engineering culture can be strong and machine-enforced and still have nothing
aimed at its own claims. In the codebase this skill came from, measured on one
day: 25 AST-level census tests policing 833 source files, 2200 incident
references inside the code itself, 63 of 64 rule↔test cross-links resolving, and
zero `FIXME` or `HACK` markers. Every one of those mechanisms points at code.
None of them points at a sentence.

The cost, measured over a single working day: nine claims published without
support, three of them later admitted in commit messages. The rules caught
**none** — they were loaded, known, and about something else.

Meanwhile, in a sample of forty recent tasks, adversarial review overturned
**eight diagnoses**, including one whose mechanism was wrong from end to end and
whose number was right only because two unrelated constants happened to share a
default.

So the one contour with proven catches was the one that was optional, and it
lived in an assistant's personal memory, where the next session cannot reach it.

## When to run it

Before publishing — to an issue tracker, a commit message, a rule, or a person:

1. **A diagnosis.** "The cause is X." Including its inverse: "this is not our
   defect."
2. **An explanation of a mechanism.** "It works like this", "it broke because
   of that."
3. **A conclusion that implies work.** "The class is finite", "this will prevent
   it", "there are roughly N places."
4. **A retelling of someone else's analysis.** Relaying is a link of its own and
   it breaks: one retelling of an adversarial report carried five distortions,
   among them a recommendation inverted into its opposite.

Readiness claims about executable work are a different gate — that is
[gopnik](../gopnik/SKILL.md). Run both; neither covers the other.

## When it is not needed

- Reading a value: "the status in the database is `blocked`", "the log says
  this".
- A mechanical edit with an equivalence test.
- Reporting an action you took, without generalising from it.
- Asking a question.

The boundary is simple: **a fact from a source needs no adversary, a
generalisation over facts does.** Of the errors measured on that day, one
hundred percent were generalisations and none were readings.

## The loop

Four steps. The last two are the ones that get skipped, and skipping either one
returns you to an unverified claim with more ceremony attached.

### Independent adversary mode

If another agent explicitly spawned this agent with a refutation mandate, this
agent already is the independent adversary in step 2. Do not spawn another
adversary or recursively restart this skill. Inspect the primary sources,
attempt the requested refutation directly, and return the requested structured
result to the spawner. The spawner remains responsible for verifying every
load-bearing finding before it turns the result into a claim. A structured
candidate set returned for a later question is not a retelling that requires a
second nested closure loop.

1. **State the claim as an operation, not as a conclusion.** See the next
   section; this is most of the value and it costs nothing.

2. **Spawn an adversary whose mandate is to refute.** Not "please check this" —
   that phrasing reliably produces agreement. The mandate is *prove this is
   wrong*, and the adversary must be independent: a different context, working
   from the sources rather than from your summary of them.

3. **Verify the adversary's load-bearing claim yourself.** It is wrong at a
   comparable rate. In one measured round, three of its five top findings were
   false, and it separately withdrew a number of its own that had been computed
   over two sets that were not comparable. Taking it at its word swaps one
   unverified source for another and calls the swap review.

4. **Close the loop: have the adversary confirm your retelling of it.** This is
   the step that was missing when the five distortions shipped. Without it the
   critique reaches the reader through an unchecked link, and the first three
   steps bought nothing.

## Operational bounds

- Keep every scratch copy under one private directory created with
  `mktemp -d /tmp/gopnik-critic.XXXXXX`. Never use a fixed generic path such as
  `/tmp/c1`, and remove exactly that owned directory before returning.
- Use the host's agent/subagent wait mechanism when it exists. Do not invent
  shell polling by task name or command substring. If only a process is
  available, wait on its exact child PID with a bounded timeout.
- Record the exact agent identifier returned at spawn and use that identifier
  for every follow-up and loop-closure message; never address the role or a
  display name. If the adversary does not confirm the retelling, report the
  critique as blocked rather than claiming the loop completed.
- A new check must challenge a load-bearing claim or resolve contradictory
  evidence. Stop repeated variants once they stop producing new evidence.
- Do not overwrite project files, delete shared paths, or change external
  state while testing a claim.

## How to state a claim

**Name the operation, not the conclusion.** "52 files with `guard` in the name"
is an operation and anyone can repeat it. "52 machine-enforced guards" is a
conclusion, and that particular one was wrong by a factor of three. The gap
between the two is visible in a second, which makes the form a cheap external
check — but it rests entirely on honesty, and the rule requiring exactly this
was in context and violated nine times in a day. Treat it as a habit to build,
not as a safeguard you have.

**Numbers carry the boundary of their sample.** Three independent measurements
of the same window of commits returned 422, 427 and 467, because nobody stated
the dates. A count whose boundary is unstated cannot be reproduced, and a number
that cannot be reproduced is not a measurement.

**Mark a guess as a guess.** "Probably", "usually", "typically" are admissions.
Either go and look, or publish the sentence with the reason you could not.

## What can be checked mechanically, and what cannot

Naming the split is part of the skill, because the same agent that must follow
it is the one that errs.

**Mechanically checkable:** that an adversary was spawned before publication.
That is visible in the session transcript, which the harness writes and the
agent does not.

**Resting on honesty:** the substance of the refutation, the completeness of the
retelling, the willingness to withdraw a conclusion you liked. The *call* can be
made mandatory. Good faith cannot.

Do not build a check that asks the agent to restate, in prose, something already
recorded in its own call log, and then blocks on the mismatch. That is
self-report wearing the costume of verification, and it costs more than it
catches.

## What not to do

- Do not present a retelling as your own conclusion, or your own as a retelling.
- Do not turn "limit this" into "forbid this". Tightening a rule without
  changing the incentive produces formal compliance, not the behaviour.
- Do not substitute self-review. On the day that produced these numbers,
  self-review ran, passed, and missed all nine.
- Do not count agreement as confirmation when the adversary never held the
  thing. Ask what it checked personally and what it took on trust.
- Do not relay a critique without closing the loop.

## Stop condition

If this skill ever demands an adversary for reading a value out of a database,
it has become noise and the triggers need narrowing.

The inverse signal matters as much: if a week goes by and no adversary has
withdrawn a single claim, then either the mandate is worded as "check" instead
of "refute", or the loop is being run for form.

## Self-check before publishing

- [ ] Is this a generalisation over facts rather than a fact read from a
      source — that is, does it need an adversary at all?
- [ ] Is the claim stated as an operation someone else could repeat, rather
      than as a conclusion?
- [ ] Does every number carry the boundary of its sample?
- [ ] Was the adversary's mandate *refute this*, not *check this*?
- [ ] Did I verify the adversary's load-bearing claim myself, rather than
      trusting it?
- [ ] Did the adversary confirm my retelling of what it found?
- [ ] If I am guessing, does the text say so and say why I could not look?
- [ ] If the claim is about executable work, has the gate examined the work
      as well?
