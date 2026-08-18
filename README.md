<p align="center">
  <img src="docs/assets/hero.jpg" alt="Cerberus: a three-headed hound standing over a gate of fire, one head green, one amber, one red" width="100%">
</p>

<p align="center">
  <a href="https://github.com/concordloom/cerberus/actions/workflows/ci.yml"><img src="https://github.com/concordloom/cerberus/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT">
</p>

# cerberus

**Your agent has to try to break its own change before it can tell you it
works.** Three skills it reads and follows. No hook and no daemon — though an
agent that has read them may reach for one when you say "done", which you can
tell it not to.

[Русская версия](README.ru.md) · [The gate's own instructions](plugins/cerberus/skills/cerberus/SKILL.md) ([ru](plugins/cerberus/skills/cerberus/SKILL.ru.md))

## Install

Paste this into any coding agent working in your project:

```
Before doing anything else, ask me exactly:
Which language would you like me to use: English or Russian?
Wait for my answer. Then install and configure Cerberus for this project by following:
https://raw.githubusercontent.com/concordloom/cerberus/main/docs/install.md
```

It installs all three skills, learns the project's checks and delivery path,
and leaves a short setup report.

## Uninstall

```
Before doing anything else, ask me exactly:
Which language would you like me to use: English or Russian?
Wait for my answer. Then uninstall Cerberus by following:
https://raw.githubusercontent.com/concordloom/cerberus/main/docs/uninstall.md
```

The removal guide finds every installed scope and preserves `cerberus.json`
unless you separately ask to delete it.

## Quick start

Installation includes project setup. Before you believe "it works":

```
Run the cerberus skill on this change.
```

It works better from an issue written before the change: without one, the agent
enumerates what to test from the diff, which is the failure it exists to catch.
What comes back:

```text
Stage 1 — pytest 24 passed, ruff clean.
Stage 2 — built the wheel, installed it into a clean venv, ran a consumer
  from /tmp so the source tree could not shadow the import. Correct for
  0.5, negative amounts and zero.
  Old HEAD's wheel returned 12.6 for the same input and the check rejected
  it, so the check can fail.
Not proven: behaviour at exactly 0.5 — no rule was agreed.

Verdict: READY
```

`NOT READY` comes back the same way, with the reproduction attached:

```text
BLOCKER — rounding is applied twice for orders with a discount.
  Reproduce: POST /orders with {"items":[…],"discount":0.1} gives total 23.94,
  expected 23.95. Introduced by the change; old HEAD returns 23.95.
Stage 2 not reached: Stage 1 has a blocker.

Verdict: NOT READY
```

## cerberus.json

One file, and the skills are its only readers. New projects get it in the root;
installs from before 2.1 keep theirs in `.claude/cerberus.json` or
`.codex/cerberus.json` and are still read there. The four keys, and `stage2_unreachable` below is the fifth and last:

```json
{
  "verification": {
    "artifact_kind": "service",
    "stage1": ["go build ./...", "go test ./... -race", "golangci-lint run"],
    "stage2": [
      "gh run watch --exit-status $(gh run list --commit $(git rev-parse HEAD) --limit 1 --json databaseId --jq '.[0].databaseId')",
      "kubectl -n dev rollout status deploy/orders --timeout=5m",
      "curl -fsS https://orders.dev.internal/version | jq -e --arg sha \"$(git rev-parse HEAD)\" '.commit == $sha'",
      "curl -fsS https://orders.dev.internal/orders -d @testdata/order.json | jq -e '.status == \"accepted\"'"
    ],
    "notes": "kube context dev-eu1 only, never prod. Deploy workflow takes ~8 min."
  }
}
```

Every entry is a shell command run from the repository root, in order, and a
non-zero exit fails the stage — which is why each line above ends in something
that *can* return non-zero. A stage stops at its first failure.

`cerberus-setup` writes `artifact_kind` and `stage1` after running the commands. `stage2`
is yours — see below. `notes` is anything the agent should know and cannot read
off the disk.

## The three heads

The three heads over the gate are the three stages.

| | Stage | What the agent has to do |
|---|---|---|
| 🟢 | **0** | Enumerate what could break, before testing any of it |
| 🟡 | **1** | Break the code: how it is used from outside, completeness, negative cases |
| 🔴 | **2** | Break it where it really runs, with a check that can fail |

Stage 0 is the one that gets skipped. The other two verify what you thought to
try; only Stage 0 decides what there was to try. The full method, at the length
an agent needs, is in [SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md).

## Stage 2 and the delivery boundary

Stage 2 has to reach past the first thing that stops being under your control
once the change ships:

| `artifact_kind` | what Stage 2 has to reach |
|---|---|
| `service` — a service or application | a deployed instance, driven to a real result |
| `library` — a package | the built package, installed somewhere clean, imported |
| `cli` — a command | the installed binary, real arguments, real exit codes |
| `chart` — a chart or IaC module | applied to a real cluster or account |
| `migration` — a schema change | a copy of real shape and scale |
| `model-boundary` — a prompt or parser | a real model call through the production entry point |
| `plugin` — a plugin or codegen | a real downstream project built with it |

**If CI deploys for you**, Stage 2 has three parts, and the third is the one
people skip:

```
gh run watch --exit-status $(gh run list --commit $(git rev-parse HEAD) --limit 1 --json databaseId --jq '.[0].databaseId')
kubectl -n dev rollout status deploy/orders --timeout=5m
curl -fsS https://orders.dev.internal/version | jq -e --arg sha "$(git rev-parse HEAD)" '.commit == $sha'
```

Wait for the pipeline *for this commit* with a command that goes red when it
does; wait for the rollout; then prove the instance answering you is this
commit. Without the third line you can go green against the build that was
already running. If there is no `/version` endpoint, compare the image digest:
`kubectl -n dev get deploy/orders -o jsonpath='{.spec.template.spec.containers[0].image}'`.

**If your pipeline only deploys from the default branch**, there is no honest
Stage 2 before the merge. Deploy the branch to a preview namespace, or run the
verdict after the merge and before the task moves to Done or the release begins.
Default-branch delivery is not by itself a reason for `stage2_unreachable`.

For `service` and `chart` the setup script can draft those commands from your
`helm/`, manifests, compose file or deploy job — ask the agent to run
`cerberus-setup` with `--draft-stage2`. It prints a draft with blanks to fill in and the traps
named, and writes nothing. For the other five kinds there is no draft; the table
above is the specification.

**If there is genuinely nowhere to deploy**, leave `stage2` as `[]` and add a
fifth key next to it inside `verification`:

```json
"stage2": [],
"stage2_unreachable": "The supported target is customer-owned hardware; this team has no representative device or emulator"
```

Every verdict then narrows to `READY scope: Stage 1` and quotes your reason.
Once `stage2` *is* filled in, running it is no longer optional.

## What it does to your session

No hook, no background process, no file of yours edited by installing. The
skills are text your agent reads when you ask for them, and — as the first
paragraph says — an agent may reach for them on "done" of its own accord. Tell
it not to the way you tell it anything else: "don't run cerberus unless I ask".

What does execute: `cerberus-setup` reads project rules, then runs their checks
or safe candidates to find out which pass. Stage 2 runs the commands
**you** put in `stage2`, with whatever credentials your shell has. `notes` is a
note to the agent, not a permission boundary: if your kubeconfig can reach
production, so can a command in `stage2`. Point them at a throwaway environment,
and keep secrets out of the file — it is committed.

The tooling calls no model and fetches nothing at runtime, though installing
downloads from GitHub and a Stage 2 for a `model-boundary` artifact is a real
model call by definition. The agent's own three stages cost tokens and take
minutes rather than seconds. That is the trade; deciding when to pay it is why
none of this fires by itself.

## The critic, which is not the gate

Three skills ship together: `cerberus`, `cerberus-critic`, `cerberus-setup`. `cerberus` asks
whether the change does what you say it does. `cerberus-critic` asks whether what you
*said* is true — a diagnosis, a mechanism, a claim about the code — by spawning
an adversary told to refute it. Neither covers the other: work can be right
while its explanation is wrong, and an explanation being right proves nothing
ever ran.

## Why

An agent built a feature, saw rows appear in the database and activity in the
logs, and reported "works end to end". The credential it had written was never
read by anything at runtime. No real run had ever happened, and a day was lost.

Making the check fire automatically was tried and dropped: a hook can tell that
code changed, never whether the change mattered, and interrupting on the wrong
guess is how a tool gets uninstalled.

## Requirements

An agent that can read the repository and install skills. The
[installation guide](docs/install.md) detects the host and lists any
route-specific tools. The method in
[SKILL.md](plugins/cerberus/skills/cerberus/SKILL.md) is agent-independent.

## License and origin

MIT — see [LICENSE](LICENSE). Extracted from the internal engineering rules of an
AI automation platform, written after the incident above.
