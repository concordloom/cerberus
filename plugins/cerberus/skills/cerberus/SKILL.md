---
name: cerberus
description: Adversarial verification before claiming a change works. Use before saying "done", "it works", "deployed and working" or "all green" about anything that executes — backend, runtime, UI, data schema.
when_to_use: Before any readiness claim about an executable change; when the .claude/.cerberus-pending marker is set; on explicit invocation.
---

# Cerberus — adversarial verification gate

A mandatory attempt to **prove the change is broken**, run before telling anyone
it works. This is not a happy-path check. Readiness is what is left over when a
serious attempt to break the thing has failed.

## Why this exists

An agent built a feature, saw rows appear in the database and activity in the
logs, and reported "works end to end". The credential it had written was never
resolved at runtime by anything: the poller, the tests, the execution path and
the supervisor all read an empty value. No real run had ever happened. A day was
lost.

The five failure modes behind that report are what this skill is built to catch:

1. **A proxy was checked instead of the result.** "There is a row in the
   database" is not "it works".
2. **The consumption path was never traced.** The form *wrote* the credential.
   Nobody asked what *reads* it at runtime.
3. **Only the happy path was exercised.** No broken token, no connection test on
   a fresh configuration, no deletion of an in-use entity.
4. **The fix was sampled, not covered.** A bug class was fixed, grepped with a
   filter that quietly excluded half the call sites.
5. **The author verified their own work.** No independent adversarial look.

Written rules already forbade all five. They were known and it happened anyway.
Hence an executable step with evidence, rather than one more paragraph of
advice.

## When to run it

Before any readiness claim, if the change touches:

- backend code, runtime paths, schedulers, engines;
- frontend behaviour or UI;
- data schema, migrations, handoff contracts;
- anything that **executes**, not merely anything that was written.

Not required for: documentation, agent configuration, comments, or a refactor
with an equivalence test. Those change nothing that can be observed to run.

## The working cycle

The gate is stronger when it is anchored to a claim written **before** the work.
An issue is that anchor, and its value is not bookkeeping: without it Stage 0
enumerates from the diff, which is the change-focused failure this whole skill
exists to prevent. An issue written first says what should become true
independently of what you happened to build.

1. **The issue states what would settle it.** Not just the symptom — the
   observation that decides. If nobody can say what result would prove the thing
   fixed, there is no oracle, and Stage 2 will have nothing to aim at. Write that
   down before writing code, or admit the issue is not ready to be worked.

2. **Stage 0 is derived from the issue, and posted to it before the work.** The
   thread then shows who enumerated the cells. This is what makes the tell
   checkable rather than a matter of memory: *if someone adds cases to the issue
   after your matrix, you skipped Stage 0.*

3. **Do the work.**

4. **A [critic](../critic/SKILL.md) examines the claims — if the work produced any.** A diagnosis
   ("the cause is X"), an explanation of a mechanism, a statement about the
   codebase ("every writer does this", "the class is closed") is a claim, and it
   needs an independent adversary whose mandate is to *refute* it. Changes that
   assert nothing beyond "this now behaves as the issue asked" skip this step.

5. **Cerberus examines the work.** Both stages, evidence per item.

   These two are not interchangeable and neither covers the other. The critic
   asks whether what you *said* is true. The gate asks whether the thing *does*
   what you say it does, past its delivery boundary. Work can be correct while
   its explanation is wrong, and a correct explanation proves nothing ran.

6. **The verdict goes back to the issue**, with the evidence: `READY` closes it,
   `NOT READY` keeps it open with the reproductions attached. Putting the
   evidence in the thread rather than in a chat log is the difference between a
   record and a memory — the next person to touch this reads the issue.

7. **A `BLOCKER` fix voids the verdict**, so an issue does not close on a
   superseded one. The new round is a new comment against the new revision, and
   the findings-dynamics line makes the sequence legible.

The cycle survives the parts being skipped, but says which was skipped and why.
An issue closed without a verdict is a claim nobody checked; say so in the
thread rather than leaving the absence to be inferred.

## Stage 0 — Behaviour matrix (blocking, before both stages)

Stages 1 and 2 verify what you tried to break. First you have to know *what
there is to break*.

The most common hole in this gate is not a weak break attempt. It is **failing
to enumerate the cells of the feature's behaviour** and checking only the
obvious ones, or the ones the user pointed at.

> **If the user is adding test cases for you, you skipped Stage 0.**

That is the tell. It means verification was change-focused ("break this diff")
rather than feature-focused ("enumerate the whole behaviour space").

**Every new mechanism gets its own matrix**, not just the axes of the diff's
state machine. If the change introduces a mechanism with its own input domain —
a secret, a validation, a presence check, a new input type — enumerate *its*
cells explicitly, **even when the mechanism is a small part of a large diff**. A
large state-machine diff tempts you to matrix only the top-level automaton and
dissolve the sub-mechanism into "the flow works". That is exactly how a
sub-feature ships unverified.

Example, for a secret-handling mechanism:
`{no secret / declared but absent from the cluster / declared with a wrong key /
declared and present}`.

Mandatory when the change touches a **state machine** (statuses, transitions) or
**several entities** (N repositories, N requests, provider/consumer pairs):

1. **Write down the axes.** The independent dimensions of the feature. Typical
   ones:
   - entity count: `{1, N}`
   - per-entity outcome: `{success, failed, blocked, cancelled, degraded}`
   - aggregate transition: `{all X, mixed — some X, some Y}`
   - operator action: `{answered one / all, narrow / broad scope, merged one /
     closed some}`
   - configuration branches: `{flag on/off, value set / null}`
   - **external dependency:** `{happy path does not touch the integration /
     touches it — present / absent / forbidden (RBAC) / unreachable}`, against
     the *real* external system.

2. **Generate the cartesian product.** Each meaningful combination is a cell.
   Discard impossible ones, with a reason. Pay particular attention to **mixed**
   cells — some entities in one outcome, some in another. **Bugs live there**,
   not in "everything succeeded" or "everything failed".

3. **Mark coverage per cell:** ✅ verified live / ⏳ in flight / 🧊 covered by
   code only, not end to end / ❌ unverified. **An unverified cell of a
   meaningful combination is a finding** until it is closed or explicitly
   discarded with a reason. A 🧊 cell is weaker than ✅ — mark it honestly. A
   cell proven only by a mock is 🧊, never ✅.

4. **The matrix is part of the report, produced before Stage 2.** The user
   should see the plan of cells, not supply them one at a time.

Smell test: if you describe behaviour as "when X and also Y", those are two axes
— enumerate their product. One failed repository, one closed request, one
unanswered question are separate cells, not "an edge case, later".

### Extra axes by subject matter

Before the first round, add the axes that match the risk of what changed:

- **concurrent writes, locks, shared mutable state** — every writer of the same
  keys, the lock ordering, and a live counterexample of a race or mixed state;
- **cost and idempotency** — repeat, duplicate, retry, and the source of the
  actual cost;
- **external integration** — the real `present / absent / forbidden /
  unreachable` cells;
- **structured model output** (prompt, parser, schema validator, retry feedback,
  serialized handoff) — attempt `{initial, retry}`, mode `{strict,
  compatibility}`, violations `{single, mixed}`, consumption path `{prompt
  example, parser, validator, persistence, downstream consumer}`, and evidence
  `{positive example, invalid mutation, repair round-trip, live adverse path}`.

High cost on its own proves nothing about progress and does not substitute for
these axes with more happy-path runs.

## Stage 1 — Break the code

Statically and locally, try to break it:

1. **Build, tests, lint** over the affected areas. Your own run, not "a subagent
   said so".

2. **Consumption path (the key step).** For everything the change *writes* — a
   field, a flag, a column, an artifact, a status — find **every** place that
   *reads* it at runtime and prove the new value is actually consumed. Not "the
   endpoint returned 200", but "the runtime uses this".

3. **Completeness for the bug class.** If you are fixing a class — "every place
   that builds client X" — enumerate all of them and check each. Verify the
   search filter did not silently exclude call sites, and quote the search
   output as evidence of completeness.

4. **Negative cases in code.** Missing fields, empty and malformed values,
   removed dependencies, and *both* branches of every fallback. A fallback whose
   primary path is only ever mocked as empty has never been tested.

### Circular tests do not count

A green test proves nothing if it assumes the result it is verifying. Before
counting a test, answer: **which production code creates the state this test
sets up by hand?**

- A test may prepare the input premise directly. It must then invoke the real
  production transition and observe its result.
- If the test creates — by assignment, by writing to the database, or through a
  helper — exactly the final state the product code is supposed to produce, it
  proves its own fixture and nothing else.
- Deliberately disabling the mechanism strengthens the proof but is not
  required. A test is non-circular once only the input is hand-made, the result
  comes from real production code, and the assertion observes that result
  through the intended path.

If Stage 1 fails, do not deploy. Fix it.

## Stage 2 — Break it past the delivery boundary

Stage 2 is not a repeat of an acceptance smoke test, and it is not proof by
absence of errors. It must create the conditions under which **an incomplete fix
would reveal itself**. A happy path is a useful baseline and never closes this
stage.

### Finding the boundary

Stage 1 verifies the code on your terms: your working tree, your fixtures, your
imports. Stage 2 must verify it **where it actually runs**, because that is
where the things Stage 1 cannot fake are real — permissions, configuration,
packaging, dependency resolution, someone else's environment.

Deploying is one instance of that, not the meaning of it. Find the right one by
asking:

> **What is the first thing that stops being under my control?**

That is the boundary, and Stage 2 must be performed from its far side, using the
artifact **as produced** rather than as it exists in your working tree.

| Artifact | Stage 2 crosses the boundary by |
|---|---|
| Service, application | a deployed instance: real end-to-end run, UI, API, logs |
| Library, SDK | installing the **built** package into a clean environment and importing it as a consumer would, across the supported version matrix |
| CLI tool | running the installed binary from a clean environment: real arguments, real files, exit codes |
| Chart, IaC module | applying to a real cluster or account and observing convergence |
| Data migration | running against a copy of real shape and scale |
| Model boundary (prompt, parser, schema) | a real model call through the production entry point |
| Plugin, compiler, codegen | building a real downstream project with it |

For a library this matters more than it looks. Tests inside the repository
import from source; users import from the published artifact. Between those two
lives an entire class of defects that no in-repo test can see: a file missing
from the package, a forgotten export, a wrong entry point, an incompatible
dependency range, absent type definitions. It is the same shape as the failure
that motivated this gate — everything green inside, and it does not work for the
consumer, because nobody walked the consumption path from outside.

Declare the boundary for your project in `.claude/cerberus.json` so this is a
fact rather than a guess each time:

```json
{
  "verification": {
    "artifact_kind": "library",
    "stage1": ["pytest -q", "ruff check ."],
    "stage2": [
      "python3 -m build",
      "python3 -m venv /tmp/consumer && /tmp/consumer/bin/pip install dist/*.whl",
      "/tmp/consumer/bin/python examples/consume.py"
    ],
    "notes": "Minimum supported dependency versions live in constraints-min.txt"
  }
}
```

If the boundary genuinely cannot be crossed — no environment exists, no consumer
can be run — Stage 2 narrows to consuming the produced artifact in a clean
environment, and everything beyond is declared `Not proven`. It is not replaced
by more Stage 1.

### Counterexample contract (blocking)

Before the first live call, write down, per mechanism being verified:

1. **Claim** — what behaviour counts as fixed.
2. **Incompleteness hypothesis** — which specific part of the fix might be
   missing, wired into only some call sites, or ineffective at runtime.
3. **Controlled adverse precondition** — the inputs, state, timing, dependency
   failure or mixed state that would make that incompleteness show.
4. **Trigger evidence** — what proves the adverse path was actually reached: a
   specific log event, a trace or conversation id, server-side state, a fault
   response, a transition, a screenshot. "We sent bad input" without evidence
   that the branch executed does not count.
5. **Failure oracle** — the observable result that would refute the fix. The
   oracle must be able to return `BROKEN`. "The logs looked quiet" is
   unfalsifiable and closes nothing.
6. **Counterfactual** — why this scenario distinguishes the fix from the old or
   incomplete behaviour. Where possible, back it with a pre-fix replay, a
   mutation test, or a previously reproduced failure signature.
7. **Blast radius and cleanup** — why the effect is confined to a fixture or
   test entity, and how state is restored. Never cause a shared outage, corrupt
   real data, or leave a weakened configuration behind.

### Oracle integrity (blocking)

Before the verdict, verify the measuring apparatus itself. An empty, stale or
mis-correlated query cannot prove the absence of a failure.

**The impact scenario must confirm the state it reached.** For every API call,
script or command used to create the adverse precondition, the report owes two
distinguishable facts: "the command was accepted" and "the state was reached".
The second may come from a separate read of the source of truth, or from an
event showing entry into the real execution branch. An HTTP 2xx, an echo of the
input, or a recorded intent confirm acceptance only. Without confirmation of
state the result is a `GAP`, and a failure to create the precondition cannot be
attributed to the change under test.

1. Take correlation, run, conversation and entity ids from confirmed trigger
   evidence or persisted state. Do not guess them and do not substitute an
   unrelated proxy id.
2. Before every negative assertion, require a positive sentinel from the same
   source, run, time window and runtime instance. **An empty result set is a
   `GAP`, not a pass.**
3. Check status codes, expected schema and non-emptiness of the evidence before
   asserting on it.
4. Run the failure oracle as a pass/fail check that returns a non-zero status
   when the invariant is violated.
5. After cleanup, re-read persisted state and runtime resources, so that a late
   callback or retry has not overwritten the terminal outcome.

**Read a negative conclusion from the source, not from a projection.** "The
field is absent", "no decision exists", "the state was not persisted" are proven
by reading the source of truth. A detail API, a DTO, a UI or any other
representation is admissible only when the claim is about that projection, or
when it has separately been shown not to filter the value in question. A
truncated allow-list does not prove data is missing upstream.

### Past the boundary

The items below are written for a deployed service because that is the richest
case. For another artifact kind, substitute the equivalent from the boundary
table and keep the requirement identical: the real thing, driven to a real
result, with evidence.

1. **A real end-to-end run, not a proxy.** Drive the real flow to a real result:
   a real task producing a real run, a real click producing a real change. Not
   "a row appeared".

   For a library this is a consumer program that imports the installed package
   and exercises the changed surface. For a CLI, the installed binary invoked
   with real arguments. In every case the artifact is the produced one, not the
   working tree.

2. **UI through a browser.** Open the page, screenshot it, look at the render
   and at console errors. The screenshot is the evidence.
3. **API through real calls**, with authentication, against the deployment. For
   a library, the equivalent is the public surface called from outside the
   package — including what your own tests never import, because they import
   from source.
4. **Negative cases live** — malformed input, missing required values, deletion
   of an in-use entity, timing, race and mixed-state edges. Each needs its
   adverse precondition, trigger evidence and failure oracle from the contract
   above. Sending a bad request is not, by itself, a negative test.
5. **Logs and state** — confirm the real run is free of auth and runtime errors,
   and that any block is for a legitimate reason rather than your own bug. Every
   negative assertion needs a positive sentinel from the same query.
6. **External integrations, by real call (blocking).** If the feature depends on
   an external system — a cluster API, permissions, secrets, network, database
   grants, a file backend — Stage 2 **must** exercise that integration with a
   real call against the real environment. Not a mock, and not a happy-path flow
   that bypasses it.

   Mocked tests plus a live run that never touches the path leave an entire
   class of deployment, permission and configuration bugs invisible: the tests
   are green, the flow is green, and the feature does not work in the cluster.

   > **Precedent.** A secret-presence check failed with a permission error every
   > time, because the service account lacked read access to secrets. The unit
   > tests mocked the call, and the live run happened on a fixture that had no
   > secret configured, so the real call was never made. Unit tests green,
   > end-to-end green; the hole surfaced only in a manual run with a real
   > secret. Both cells of that mechanism had been 🧊, and nobody had said so.

Safe impacts to reach an adverse path: a fixture-scoped short deadline or delay;
missing, invalid or stale input; a dangling reference to a synthetic entity;
isolated permission denial; mixed statuses across N entities; a repeat,
duplicate or race; a slow or failing test dependency; a UI refresh or double
action. The impact must travel the real runtime consumption path rather than a
mock. System-wide chaos injection is not required.

For an artifact consumed rather than operated, the adverse preconditions are
different but the contract is the same: the **minimum** supported version of
each dependency rather than the latest; installation without optional extras; a
consumer on the oldest supported language runtime; import from a directory that
is not the repository root; a clean environment with no development tooling
present. Each of these has a failure oracle that can return `BROKEN`, which is
what makes them Stage 2 material rather than opinion.

If an adverse precondition cannot be created safely, that is a `GAP`: narrow the
verdict or return `NOT READY`. Do not substitute a smoke test.

## Report discipline — do not cry wolf

Hard in effort, disciplined in reporting.

- **A finding is a reproduced failure with evidence.** "This could break" is not
  a finding. "I broke it — here is the request, the screenshot, the log line,
  and how to repeat it" is.
- Symmetry: "broken" demands a reproduction exactly as "works" demands a live
  run.
- **Severity.** A reproduced failure is a `BLOCKER` and gates readiness. An
  uncovered edge is a note. A nitpick is optional. Only blockers gate.
- **Scope is the change and its consumption path**, not the whole codebase.
  Auditing everything is where false findings breed.
- **Calibration.** If review keeps showing the findings were empty, raise the
  bar on "must reproduce".

## An independent adversary

Delegate the heavy part to a subagent with an explicit mandate: **prove it is
broken**. Not "check that it works" — that phrasing produces agreement, and it
will happy-path exactly as the author did. Give it real access. It returns, per
item, either `BROKEN` with a reproduction and evidence, or `OK` with evidence.
The implementer and the verifier are different parties.

### Claims made by the verifier

This gate verifies **work**. Claims *about* the work — a diagnosis, an
explanation of a mechanism, a conclusion about a property of the codebase — need
their own scrutiny, and an adversary of the work does not automatically become
an adversary of its own claims.

- **Name the operation and the boundary of the set**, not just the conclusion.
  "Every match of this pattern under this directory was checked" is an
  operation. "This is the canonical order" is a conclusion, and the gap between
  them is visible in a second.
- A claim of the form "all writers do X", "this is the only ordering" or "the
  class is closed" requires enumerating the whole declared set. One sample
  supports that sample; a sample must be called a sample.
- A locally reproduced defect stays a finding **in the exact area checked**. An
  unverified generalisation does not widen it into a property of the class, and
  is not grounds for changing the other places.
- Numbers carry the boundary of their sample. A measurement without a stated
  boundary is not reproducible and therefore is not a measurement.

## Rounds, fixes, and when to stop

Each round is bound to an exact revision and its own body of evidence.

**Fixing any `BLOCKER` voids the previous verdict.** Changed code is a new
subject. After a fix, run a new full round against the new revision, updating
Stage 0 and repeating the applicable parts of Stages 1 and 2. A `READY`, or any
part of an earlier verdict covering the changed path, cannot be inherited just
because the fix was small.

Every report carries a line of finding counts and classes:

```text
Findings: R1@<rev> — 2 BLOCKER [concurrency, verification loop], 1 note [coverage]
        → R2@<rev> — 1 BLOCKER [execution path], 0 note
        → R3@<rev> — 0 BLOCKER, 0 note
```

`<rev>` is a commit or tree hash, or an explicitly named fingerprint of the diff
under test. Mark separately any defect introduced by the previous round's fixes.

This dynamic gives data about convergence — it does not prove it. A sequence
`{A} → {B} → {A}` oscillates while changing every time. Compare the identity and
recurrence of problems, movement of the `BLOCKER` count toward zero, and the
appearance of new classes.

If two consecutive rounds reproduce the same `BLOCKER` set without a meaningful
change in evidence or fix, stop and report the exact reproduction, what was
tried, and what input is needed. Returning to an already-seen set, or a growing
new class, is not convergence without a separate explanation. Continue to a zero
round, or honestly narrow the claim and list what is `Not proven`.

## Verdict

One of two, with evidence for every item of both stages:

- **NOT READY** — blockers exist. List them with reproductions. The marker stays.
- **READY** — both stages passed, zero `BLOCKER`, evidence provided, and the
  last round covers the current exact revision. Clear the marker.

Only after `READY` may you tell the user it works.

When the verdict is narrower than the whole change, say so explicitly: state the
`READY scope` — the cells actually verified — and list what is `Not proven`. A
verdict about one ticket must not be presented as readiness of a whole stage.

## Self-check before the verdict

- [ ] Cycle: does the issue state the observation that would settle it, and was
      the matrix posted there before the work rather than after?
- [ ] Cycle: if the work asserts a diagnosis, a mechanism or a property of the
      codebase, did an independent critic try to refute that claim — separately
      from this gate, which examines the work?
- [ ] Stage 0: matrix built (axes × cells), mixed cells enumerated, coverage
      marked per cell (✅/⏳/🧊/❌)?
- [ ] Stage 0: did *I* generate the cells, rather than the user supplying them?
- [ ] Stage 0: did every **new mechanism** get its own matrix instead of
      dissolving into "the flow works"?
- [ ] Stage 1: build, tests and lint — my own run, green?
- [ ] Stage 1: consumption path traced for every value written — is the runtime
      proven to read the new value?
- [ ] Stage 1: for a bug class — every call site, with search output as proof
      the filter excluded nothing?
- [ ] Stage 1: negative cases run, both fallback branches?
- [ ] Stage 1: does each test invoke production code rather than hand-building
      the state it claims to prove?
- [ ] Stage 2: deployed, healthy?
- [ ] Stage 2: real end-to-end run driven to a real result, not a proxy?
- [ ] Stage 2: per mechanism, were the incompleteness hypothesis, adverse
      precondition, trigger evidence, failure oracle, counterfactual and cleanup
      written down *first*?
- [ ] Stage 2: does the evidence prove the adverse path was reached, and could
      the oracle have returned `BROKEN`? Was a happy path passed off as a break
      attempt?
- [ ] Stage 2: did the impact scenario separately confirm acceptance and the
      state actually reached?
- [ ] Were negative conclusions read from the source rather than a filtering
      projection?
- [ ] Stage 2: UI screenshotted, API called for real, negatives run live?
- [ ] Stage 2: external integrations exercised by real call — not mocked, not
      bypassed (a mocked cell is 🧊, never ✅)?
- [ ] Is every finding reproduced, with evidence, rather than hypothesised?
- [ ] For the verifier's own claims: was the operation named, the set boundary
      stated, and no local finding widened beyond what was enumerated?
- [ ] After each `BLOCKER` fix, was a new round run on the new revision, and does
      the report carry the findings-dynamics line?
- [ ] Was the marker cleared only on `READY`?
