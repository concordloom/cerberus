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

## A Stage 1 blocker ends the turn

If a required Stage 1 check is red:

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

For LoomWatch with a missing Go toolchain, a good response is:

> Stage 1 checks whether LoomWatch can pass its own fast project check. It is
> not ready yet because that check starts through `app.sh`, but Go is missing
> from this environment. The project can install its dependencies with its own
> setup command. May I run that and repeat the fast check?

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

A package smoke test, build, or `--version` call is only a Stage 2 prerequisite
unless it crosses the actual delivery boundary.

## Introduce Stage 2 only after Stage 1 works

Only after Stage 1 passes, inspect CI triggers, deploy jobs, Dockerfiles, charts,
manifests, release scripts, service URLs, and version metadata. Explain in
product language that Stage 2 proves the exact change reached the place where
people use it and still works there.

Present the most likely route in one or two sentences, without an infrastructure
or shell-command chain, then ask one short confirmation question. Do not make
the person describe infrastructure the repository already shows and do not
begin with an infrastructure questionnaire.

For a service deployed from the main branch by CI, prefer:

> It looks like pushes to the main branch are deployed by CI and the service is
> then available at its normal URL. Is that the real path we should verify?

If repository evidence is insufficient, ask:

> How does this change get to where it really runs, and how would you know it
> arrived?

Confirmation is a hard turn boundary. End with the question and wait.

After confirmation, find remaining facts in the repository first. If one
important fact is missing, explain why it matters and ask one question about
it. Wait for the answer before asking another. Never batch the URL, cluster,
namespace, credentials, revision proof, negative check, dependency installation,
and long-suite permission into one message.

Internally, the route must trigger or observe delivery for the exact revision,
wait with a check that can fail, prove the deployed revision, exercise a real
consumer path, and prove the check can fail safely.

If CI deploys only from the default branch, there is no honest pre-merge Stage
2. Record a preview environment or a post-merge run before Done or release.
Use `stage2_unreachable` only when the project truly has no reachable delivery
boundary.

Validate read-only prerequisites. Show the exact target and ask before any
deploy, apply, migration, or other shared write. Missing access, credentials,
VPN, a URL, or revision proof is a setup blocker. Discuss only that blocker with
the same one-problem, one-next-step, one-question pattern.

## Close with a human-sized status, not a verdict

Installation has `installed` or `not installed`. Project setup has `configured`
or `setup blocked`. `READY` and `NOT READY` belong only to a Cerberus run against
a concrete product change.

Setup cannot be `configured` before the inferred Stage 2 route is confirmed.
Before that answer, it is still in progress.

Use at most four short points: whether Cerberus is installed; whether the
project's local check is ready and what was observed; whether the real delivery
path is ready or the one remaining blocker; and the short phrase that invokes
Cerberus on a completed change. Mention a restart only if required.

Do not report configuration paths, the saved language, artifact kinds, internal
keys, JSON, raw command routes, marketplace mechanics, or every installed file.

Recommend running `cerberus` against the exact revision before a tracker task
moves to Done. A `NOT READY` verdict keeps that task open.

## Self-check before saying configured

- [ ] Did I read project instructions before choosing or running commands?
- [ ] Did I use project-owned wrappers instead of generic commands?
- [ ] Did I explain the three stages before internal work?
- [ ] Was every recorded Stage 1 command run and shown passing?
- [ ] If Stage 1 failed, did I stop before inspecting or discussing Stage 2?
- [ ] Did a blocker response contain one problem, one next step, and one question?
- [ ] Did I ask before lengthy or shared-state-changing work?
- [ ] Did I describe Stage 2 in product language and get it confirmed?
- [ ] Did I avoid batching unrelated Stage 2 questions?
- [ ] Can the future runner access the target and prove the exact revision?
- [ ] Can the Stage 2 check fail safely?
- [ ] Is `stage2_unreachable` reserved for a true project-level absence?
- [ ] Did I keep configuration files and JSON out of normal user-facing text?
- [ ] Did I report setup status without issuing a product verdict?
