# How Gopnik works

Gopnik verifies a claim about a completed change. It does not award confidence
for activity; it asks what observation would prove the claim wrong, then tries
to produce that observation.

## The verification cycle

### Stage 0 — define the attack surface

Before running commands, Gopnik turns the task and diff into a behavioural
matrix. The axes come from the change: inputs, states, permissions, consumers,
delivery surfaces, old versus new revisions, and any other dimension that can
change the result.

Every material claim needs a failure oracle. “The command ran” is not enough;
the oracle must distinguish the intended behaviour from a plausible defect.

### Stage 1 — attack the repository

Stage 1 uses project-owned checks and focused probes against the current code.
It inspects call sites, boundary values, negative paths, configuration, and
failure behaviour. A build, package smoke test, or `--version` output remains a
prerequisite when the actual product is consumed elsewhere.

A Stage 1 blocker stops the cycle. Gopnik does not skip ahead to a deployment
demo while the code-level claim is already broken.

### Stage 2 — cross the delivery boundary

Stage 2 verifies the product from the far side of the boundary where it is
delivered:

| Product surface | Evidence beyond Stage 1 |
| --- | --- |
| CLI | clean install, real invocation, exit/output contract |
| Package or library | isolated consumer outside the source tree |
| Service or API | exact deployed revision, real request, safe negative case |
| Web UI | real browser flow, console/network inspection, screenshot |
| Plugin | native host install, discovery, invocation, update path |
| Job or migration | real runner, observable effect, bounded rollback or counterexample |

Stage 2 must prove the exact revision under test. A healthy endpoint or a page
that opens is not evidence if it may belong to yesterday's deployment.

## Prove the proof can fail

At least one load-bearing check must demonstrate sensitivity. Depending on the
change, Gopnik may use an old revision, a safe input mutation, a known-bad
fixture, or another counterfactual. The point is not to manufacture red output;
it is to show that the chosen oracle detects the defect it claims to detect.

## Scoped verdicts

`READY` never means “nothing can be wrong.” It means the stated cells passed
within a named scope and against a recorded fingerprint or revision.

A verdict includes:

- the scope and revision;
- checks that ran and evidence they produced;
- reproduced blockers, if any;
- counterevidence or sensitivity proof;
- anything material that remains unproven.

If a required surface is reachable but untested, the verdict is `NOT READY`.
If the surface is genuinely unreachable, Gopnik may report a narrower scope,
but it must name the missing proof.

## Configuration

`gopnik-setup` records stable project mechanics in `gopnik.json`. See
[`gopnik.example.json`](../gopnik.example.json) for the schema.

- `stage1` contains fast repository checks that setup actually ran.
- `stage2` contains executable checks past the delivery boundary.
- `artifact_kind` identifies the primary delivery boundary; hybrid products
  still need coverage for every confirmed surface.
- `surfaces` is where those confirmed surfaces are kept — the set a critic
  challenged and a person confirmed during setup. A verdict owes each of them a
  `stage2` step or an explicit `Not proven` naming it. A configuration written
  before the key existed has none, and is read exactly as it stands.
- `notes` describe constraints and prerequisites. They do not grant authority.

Private targets, credentials, and machine-specific paths do not belong in the
shared file. Keep them in an ignored local override or existing credential
provider and reference them through project-owned indirection.

## Execution and authority

Gopnik is a skill invoked by an agent. Installing it does not wire a hook,
daemon, or automatic release gate into the repository. The agent may invoke a
discovered skill when it judges the request relevant; the operator can also ask
for it explicitly.

The skill does not grant permission to deploy, push, read secrets, mutate
production, or run an unbounded suite. Normal project and operator authority
still applies.

## The accompanying critic

`gopnik-critic` attacks an important claim before implementation or
publication. It separates evidence from inference, searches for a surviving
counterexample, and reports `CONTINUE`, `REVISE`, or `BLOCK`.

A practical development loop is:

1. critic on the task formulation;
2. critic on the proposed solution;
3. Gopnik on the completed, delivered change.

This is a recommendation, not an automatic workflow mutation. Teams decide
where the loop belongs and what authority each verdict carries.
