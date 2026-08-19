---
name: cerberus-setup
description: Discover and verify this project's real Stage 1 and Stage 2 mechanics, then record them in cerberus.json so Cerberus does not guess. Use during installation, when the config still has placeholders, or when delivery changed.
---

# Setup - learn how this project is really verified

The gate attacks work and the critic attacks claims. Neither should guess how
this repository is tested or how a revision reaches the place where people use
it. Discover those mechanics, verify them, and record only what future runs can
actually execute.

## Select the language once

During first onboarding, the installation guide already selected the
conversation language. Reuse a valid top-level `language` from `cerberus.json`
without asking. If setup is invoked on its own and neither the config nor the
conversation provides a language, first ask exactly in English:

> Which language would you like me to use: English or Russian?

Your response must end after that question; use no tools first. Do not ask
twice. After the answer, speak in that language and pass it to the setup script
as `--language en` or `--language ru`.

## Start with a human orientation

Immediately after the language is known, explain the process before doing
internal work:

- **Stage 0** maps what could break for each future change.
- **Stage 1** checks the code inside the repository. Set this up first.
- **Stage 2** checks the built or deployed result where people actually use it.
  Discuss it only after Stage 1 works.

Keep this to three short points, then say you will find and run the project's
own fast Stage 1 check. The person should understand the current step without
having to understand Cerberus internals.

Do not narrate tool or skill selection, raw-guide fetching, marketplace or
version mechanics, installation paths, configuration files, JSON, keys, or
internal CLI syntax. If the host requires an action announcement, combine it
into one short sentence. Mention an internal detail only when the person must
act on it or explicitly asks.

During setup, one user decision should normally produce one substantive
response. Do not emit repeated still-working updates for the same state. Tool
selection, downloads, checksum parsing, shell filters, retries, process
polling, and alternative diagnostic commands are internal work. A retry or a
different diagnostic command is not a human-facing state change. If the host
requires a periodic update during a long operation, give one plain sentence
about the current goal and omit the mechanics.

## Read project rules before choosing checks

Read `AGENTS.md`, `CLAUDE.md`, contribution docs, package scripts, build
wrappers, CI workflows, deployment manifests, and any existing configuration.
Repository instructions outrank toolchain conventions.

Never bypass a project-owned wrapper with generic commands. A `go.mod` does not
authorise `go test ./...` when the repository says to use `app.sh`. If explicit
project instructions exist, the setup script refuses generic detection; pass
the commands you read with `--stage1` instead.

Do not inspect or discuss Stage 2 yet. Finish Stage 1 first.

## Run the mechanical part silently

Use whichever installed path exists:

```sh
python3 "$CLAUDE_PLUGIN_ROOT"/skills/cerberus-setup/cerberus_setup.py
python3 .claude/skills/cerberus-setup/cerberus_setup.py
python3 .agents/skills/cerberus-setup/cerberus_setup.py
```

When the project defines its own checks, pass exactly those commands and the
observed artifact kind:

```sh
python3 PATH/cerberus_setup.py --artifact-kind service \
  --language en \
  --stage1 './app.sh --smoke' \
  --stage1 './app.sh --test'
```

Repeat `--stage1` as needed. `--check` runs and reports without writing.
`--draft-stage2` prints a repository-derived proposal and writes nothing.

Run fast, read-only checks automatically. Ask before a lengthy suite or a
command that mutates shared state. Pass explicit checks from fastest to
slowest; the script stops at the first failure.

The request to install or set up Cerberus authorizes one continuous local setup
goal. Approval attaches to the goal, not to each command. Within that goal,
continue autonomously through local, reversible diagnostics, including:

- user-scoped dependency installation that needs no elevated privileges;
- temporary environments, caches, and diagnostic output;
- bounded reruns of the same project-owned check with safer environment,
  parallelism, cache, or tracing settings;
- read-only inspection that narrows a failure to a dependency, phase, package,
  test, or process.

Do not ask permission to change diagnostic strategy while it stays inside this
scope. Ask only before a system-wide installation or elevated privileges,
editing tracked project files, a lengthy suite outside the agreed budget,
raising a resource limit beyond the current safety envelope, accessing a
secret, or changing shared or external state.

Every first Stage 1 command needs a wall-clock budget. Use
`--timeout-seconds 120`, which is 120 seconds by default, or a smaller
repository-defined limit. Use memory as a host-relative safety signal: watch
available memory, sustained swap pressure, host responsiveness, and repository
evidence instead of enforcing one universal RSS number. A runtime memory
objective is not a compiler memory limit. Stop before the check threatens the
host, and diagnose under an equivalent or safer envelope. Do not rerun a
timed-out command directly without an equivalent limit. Ask before raising
either limit for a check the repository documents as legitimately expensive.

## Diagnose Stage 1 autonomously; stop only at an authority boundary

When a required Stage 1 check is red, diagnose it inside the autonomy budget
before presenting a blocker. Each retry must test a materially different
hypothesis and preserve or tighten the current safety envelope. Continue while
the evidence narrows the cause. If two consecutive attempts reproduce the same
blocker twice without materially new evidence, stop rather than churn.

A Stage 1 failure becomes a hard turn boundary only when the next useful action
crosses an authority boundary above, requires a product or workflow choice, or
the bounded diagnostic loop has stopped making progress. Then:

1. Explain in plain language what the check was trying to prove.
2. Name the concrete cause and impact. Diagnose the useful underlying error; a
   missing program inside a project wrapper does not mean the wrapper is absent.
3. Offer one recommended next action grounded in the repository. Give one
   alternative only when it is genuinely useful.
4. End with exactly one short question about that next action.

Do not inspect, infer, present, or ask about Stage 2 while Stage 1 is blocked.
Do not give a setup summary, infrastructure questionnaire, raw command chain,
large terminal excerpt, configuration path, JSON, or internal state. Resume
only after the person answers.

For a project wrapper with a missing nested dependency, good behaviour is:

> Stage 1 needs a tool that is not available here. The system route requires
> elevated privileges, so I will first try a user-local or project-declared
> route and repeat the project check. Those steps are local and reversible, so
> I will continue without another question. If the only remaining route
> requires elevated privileges, I will stop and ask.

After Stage 1 succeeds, report the result in one short sentence.

## Preserve internal configuration without exposing it

The script writes the selected language as the top-level `language` value and
writes the `verification` block: `artifact_kind`, `stage1`, `stage2`, and
`notes`. It merges rather than replaces existing data. A hand-written artifact
kind, operational note, or legacy config path must survive.

Only Stage 1 commands that were actually run and passed may be written.
`stage2` stays empty until its real route is inferred and confirmed. A comment,
`echo`, or another always-green command is not a check.

`cerberus.json` stores stable project mechanics, not a feature-specific test
plan. Never mention this file, its path, format, keys, or contents during normal
onboarding. Reveal those details only if the person explicitly asks or a
malformed hand-written file requires manual repair. Never store credentials.

The stable, portable verification mechanics belong to the project;
machine-specific paths, private targets, and credentials stay in an ignored
local override. The local override must be separate from the shared project
record and the shared route must refer to local values through environment
variables or another project-owned indirection. Never put the shared project
configuration in `.git/info/exclude`. Never copy a private target or an
absolute home-directory path into a file intended for the team.

A package smoke test, build, or `--version` call is only a Stage 2 prerequisite
unless it crosses the actual delivery boundary.

## Ask whether Stage 2 has somewhere real to run

Only after Stage 1 passes, explain in one sentence that Stage 2 checks the built
or deployed result where people actually use it.

For a deployed service or application, do not inspect and present its
infrastructure first. Ask only:

> Is there a test or staging environment where Cerberus can verify the deployed version?

This availability question is a hard turn boundary. End with it and wait.

If the answer is yes, ask one related follow-up:

> How does a new version get there, and how can the agent obtain access? Do not send secrets; just name the existing access method.

Then wait again. Do not ask for infrastructure fields or present a command
route before the person answers.

For a package, CLI, plugin, or another artifact that can be checked safely in a
clean consumer environment, create that environment yourself instead of asking
an irrelevant staging question. Ask only when the real consumer environment
cannot be created or reached automatically.

After the answer, inspect CI triggers, deploy jobs, manifests, release scripts,
service URLs, and version metadata. Combine repository evidence with what the
person said. Verify access and all read-only prerequisites you can, then silently
record only a route a future Cerberus run can execute.

During that investigation, inspect the real product surfaces Stage 2 must
exercise. Do not ask about browser tooling merely because frontend files exist.
If the deployed product has a UI, first look for a project-owned browser route
such as Playwright or Cypress against the stand, then for a browser or
computer-use tool already available to the agent.

Only when the deployed UI is real and neither route exists, explain the missing
capability and ask one contextual question:

> The stand has a user interface, but this agent has no browser tool for Stage 2. To open it, exercise the flow, inspect console and network errors, and capture screenshots, may I connect Playwright MCP?

This is a hard turn boundary. Do not combine it with the stand, delivery,
access, URL, or credentials questions. Wait for the answer.

If the person agrees, determine and use the current host's supported MCP setup
route rather than guessing a command. The approval covers only connecting
Playwright MCP, not changing the project or exercising a state-changing UI
flow.

Never claim that the current session can use a newly added MCP server. Check
the host's restart behaviour and visible tool inventory. If a fresh agent
session, application restart, or extension restart is required, tell the person
explicitly, give the exact resume phrase, and stop. Resume setup only after the
restarted session can see the browser tool. Then perform a safe read-only probe:
open the stand UI, inspect the rendered state plus console and network errors,
and capture a screenshot. Ask separately before a state-changing browser action.

If the person declines or the host cannot connect a browser tool, continue with
reachable non-UI surfaces and record the UI capability as missing. Do not ask
again during normal setup. A future UI change cannot receive `READY` until its
UI cells have browser evidence; a backend-only change does not need a browser
merely because the service also has a UI.

If one important fact is still missing, explain why it matters and ask one
question about it. Wait for the answer before asking another. Never batch the
URL, cluster, namespace, credentials, revision proof, negative check, dependency
installation, and long-suite permission into one message.

Internally, the route must trigger or observe delivery for the exact revision,
wait with a check that can fail, prove the deployed revision, exercise a real
consumer path, and prove the check can fail safely.

If CI deploys only from the default branch, there is no honest pre-merge Stage
2. Record a preview environment or a post-merge run before Done or release.
Use `stage2_unreachable` only when the project truly has no reachable delivery
boundary.

If no test or staging environment exists, record the missing project-level
target and finish with an honest Stage 1 scope. If it exists but the agent lacks
access, treat access as the one setup blocker. If the answer is ambiguous, ask
one short clarification instead of guessing.

Validate public and anonymous read-only prerequisites automatically.
Describing an access method is context, not approval. Before an authenticated
production read or reading a secret, name the production target, explain the
intended observation in plain language, and ask for explicit confirmation for
one exact read-only probe. Keep the credential only in process memory and never
print or persist it. That confirmation does not authorize another endpoint, a
state-changing UI flow, deploy, apply, migration, or other shared write; ask
separately. Missing access, credentials, VPN, a URL, or revision proof is a
setup blocker. Discuss only that blocker with the same one-problem,
one-next-step, one-question pattern.

## Close with a human-sized status, not a verdict

Installation has `installed` or `not installed`. Project setup has `configured`
or `setup blocked`. `READY` and `NOT READY` belong only to a Cerberus run against
a concrete product change.

Setup cannot be `configured` until the Stage 2 target and access are verified,
or the absence of a project-level target is confirmed and recorded. Before
that, setup is still in progress.

Use at most four short points: whether Cerberus is installed; whether the
project's local check is ready and what was observed; whether the real delivery
path is ready or the one remaining blocker; and the short phrase that invokes
Cerberus on a completed change. Mention a restart only if required.

Do not report configuration paths, the saved language, artifact kinds, internal
keys, JSON, raw command routes, marketplace mechanics, or every installed file.

Treat the internal project record as already handled, not as a user-facing
repository change. Never say that a configuration file was created, changed,
is untracked, or should be committed. Do not include it in a working-tree
summary. After the three-gate loop, stop: do not append notes about files, Git
status, cleanup, or what the person should commit.

Recommend a three-gate loop adapted to the project's existing workflow:

1. run `cerberus-critic` on the task formulation before work begins;
2. run `cerberus-critic` on the proposed solution before implementation;
3. run `cerberus` on the completed change and exact delivered revision before
   the tracker task moves to Done. A `NOT READY` verdict keeps it open.

Give one short copyable prompt for each gate in the selected language.

## Self-check before saying configured

- [ ] Did I read project instructions before choosing or running commands?
- [ ] Did I use project-owned wrappers instead of generic commands?
- [ ] Did I explain the three stages before internal work?
- [ ] Was every recorded Stage 1 command run and shown passing?
- [ ] If Stage 1 failed, did I stop before inspecting or discussing Stage 2?
- [ ] Did a blocker response contain one problem, one next step, and one question?
- [ ] Did I ask before lengthy or shared-state-changing work?
- [ ] Did I treat approval as applying to the setup goal rather than each safe command?
- [ ] Did I continue safe local diagnostics without repeated permission questions?
- [ ] Did every first Stage 1 command have time and memory safety limits?
- [ ] For a deployed service, did I first ask only whether a stand is available?
- [ ] If yes, did I ask how delivery and access work without requesting secrets?
- [ ] Before an authenticated production read or secret access, did I obtain
      target-specific confirmation for one read-only probe?
- [ ] If a deployed UI had no browser route, did I offer Playwright MCP only after discovering that gap?
- [ ] After connecting MCP, did I state and respect the host's restart boundary?
- [ ] Did I avoid batching unrelated Stage 2 questions?
- [ ] Can the future runner access the target and prove the exact revision?
- [ ] Can the Stage 2 check fail safely?
- [ ] Is `stage2_unreachable` reserved for a true project-level absence?
- [ ] Is shared verification portable, with private local values kept separate?
- [ ] Did I keep configuration files and JSON out of normal user-facing text?
- [ ] Did I omit internal files, Git status, and commit advice from the final response?
- [ ] Did I recommend critic of task, critic of solution, then Cerberus?
- [ ] Did I report setup status without issuing a product verdict?
