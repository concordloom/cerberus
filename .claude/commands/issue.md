---
description: End a discussion by opening the issue it was heading towards.
argument-hint: [what the discussion was about, optional]
allowed-tools: Bash(gh issue create:*)
---

A discussion has produced enough to be worked. Turn it into an issue, in the
shape `.github/ISSUE_TEMPLATE/work.yml` requires, and open it with `gh`.

Write the issue from what was actually said in this conversation. Do not invent
scope, and do not smooth over disagreement that was never resolved — if two
readings survived the discussion, the issue says which one it takes and notes
the other.

The body carries four things:

**What is wrong** — the symptom and how it shows up, with whatever sources came
up in the discussion: a log line, a version, a command that fails.

**What would settle it** — the observation that decides, stated so it could
come back negative. This is the field the whole form exists for. If the
discussion never produced one, do not manufacture it: write *"no oracle yet"*
and say what would have to be learned first. An issue that admits this is more
useful than one that pretends.

**Delivery boundary** — the first thing that stops being under our control once
this ships. Omit it only when the change executes nothing.

**Axes, if known** — dimensions the behaviour varies along, as far as the
discussion got. These become the first row of the matrix; anything captured now
is a cell nobody has to rediscover.

Then:

1. Open it: `gh issue create --title … --body …`. Use the template's headings so
   the issue reads like the form, since `gh` does not apply the form itself.
2. Print the URL, and say in one line what the next step is — usually
   `/work <number>`.

Do not start the work in the same turn. The point of the issue is that it exists
**before** the work, and a claim written after the fact is the failure this
whole repository is about.
