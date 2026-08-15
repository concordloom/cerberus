---
description: Work an issue through the full cycle — matrix, work, critic, gate, verdict.
argument-hint: <issue number>
allowed-tools: Bash(gh issue view:*), Bash(gh issue comment:*), Bash(gh issue close:*), Bash(gh pr create:*)
---

Take issue **$1** through the cycle in `plugins/cerberus/skills/cerberus/SKILL.md`.
Read that skill before starting; what follows is the order of operations, not a
replacement for it.

1. **Read the issue.** `gh issue view $1 --comments`. If it has no answer to
   *what would settle it*, stop and say so: the work has no oracle, and Stage 2
   would have nothing to aim at. Ask for one rather than inventing it.

2. **Post the Stage 0 matrix as a comment, before touching anything.** Axes and
   their cartesian product, coverage marked per cell, mixed cells called out
   explicitly. Posting it first is what makes the tell checkable — if someone
   adds cases to the issue after your matrix, you skipped the step.

3. **Do the work.**

4. **Run the critic if the work produced a claim** — a diagnosis, an explanation
   of a mechanism, a statement about the codebase. Follow
   `plugins/cerberus/skills/critic/SKILL.md`: an adversary whose mandate is to
   refute, then verify its load-bearing claim yourself, then have it confirm
   your retelling. A change that asserts nothing beyond "this now behaves as the
   issue asked" skips this.

5. **Run the gate.** Both stages, evidence per item. Stage 2 crosses the
   boundary named in the issue, using the artifact as produced — for this
   repository that is usually the plugin loader on a pushed commit, or the
   published tag through `gh skill install`, neither of which a working tree can
   stand in for.

6. **Post the verdict to the issue** with the evidence: what was run, what came
   back, and what a broken version would have produced instead. `READY` closes
   it; `NOT READY` leaves it open with the reproductions attached.

7. **If a `BLOCKER` was fixed, the verdict is void.** Start a fresh round on the
   new revision, as a new comment, and carry the findings-dynamics line so the
   sequence stays readable.

Then open the pull request, `Closes #$1`, with the verdict linked rather than
restated.

If you skip a step, say which and why in the issue. A step skipped in the open
is a decision; a step skipped quietly is the thing this repository refuses.
