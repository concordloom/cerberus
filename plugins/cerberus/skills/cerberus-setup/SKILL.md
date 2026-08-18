---
name: cerberus-setup
description: Discover and verify this project's real Stage 1 and Stage 2 mechanics, then record them in cerberus.json so Cerberus does not guess. Use during installation, when the config still has placeholders, or when delivery changed.
---

# Setup - learn how this project is really verified

The gate attacks work and the critic attacks claims. Neither should guess how
this repository is tested or how a revision reaches the place where people use
it. Discover those mechanics, verify them, and record only what future runs can
actually execute.

## Start with project rules

Read `AGENTS.md`, `CLAUDE.md`, contribution docs, package scripts, build
wrappers, CI workflows, deployment manifests, and any existing
`cerberus.json`. Repository instructions outrank toolchain conventions.

Never bypass a project-owned wrapper with generic commands. A `go.mod` does not
authorise `go test ./...` when the repository says to use `app.sh`. If explicit
project instructions exist, the setup script refuses generic detection; pass
the commands you read with `--stage1` instead.

During first onboarding, the installation guide already selected the
conversation language. If setup is invoked on its own and no language has been
selected, first ask exactly in English:

> Which language would you like me to use: English or Russian?

Do not ask twice. After the answer, speak in that language.

## Run the mechanical part

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
  --stage1 './app.sh --smoke' \
  --stage1 './app.sh --test'
```

Repeat `--stage1` as needed. `--check` runs and reports without writing.
`--draft-stage2` prints a repository-derived proposal and writes nothing.

Run fast, read-only checks automatically. Ask before a lengthy suite or a
command that mutates shared state. If a required fast check is red, do not
start the long suite without permission and do not execute Stage 2 as a
verification run. Report `setup blocked`; you may still discuss the future
Stage 2 route.

## Preserve the configuration

The script writes the `verification` block: `artifact_kind`, `stage1`,
`stage2`, and `notes`. It merges rather than replaces existing data. A
hand-written artifact kind, operational note, or legacy config path must
survive.

Only Stage 1 commands that were actually run and passed may be written.
`stage2` stays empty until its real route is inferred and confirmed. A comment,
`echo`, or another always-green command is not a check.

`cerberus.json` stores stable project mechanics: what ships, executable checks,
the delivery route, and operational notes. Do not put a feature-specific test
plan there; Cerberus creates that from the task during Stage 0.

## Explain the stages briefly

Use three short points, not a lecture:

- **Stage 0** maps what can break before testing begins. It is rebuilt for each
  change.
- **Stage 1** attacks the code locally: tests, negative cases, and its real
  consumption path. Most of it is visible in the repository.
- **Stage 2** attacks the built or deployed result where it is actually used.
  Repository evidence can propose this route; the operator confirms reality.

A package smoke test, build, or `--version` call is only a Stage 2 prerequisite
unless it crosses the actual delivery boundary.

## Infer Stage 2 before asking

Inspect CI triggers, deploy jobs, Dockerfiles, charts, manifests, release
scripts, service URLs, and version metadata. Present the most likely route and
the evidence behind it, then ask the operator to confirm or correct it. Do not
make them describe infrastructure the repository already shows.

For a service with binary, Docker, and Helm routes, name those observed routes
and ask which one is used in reality. Propose the corresponding daemon, API,
dashboard, rollout, and revision checks. Only when repository evidence is
insufficient ask:

> How does this change get to where it really runs, and how would you know it
> arrived?

Then **say back what you understood as the exact command route** before writing
it. Ask at most one batched follow-up for gaps that remain:

- exact URL, cluster, consumer, or other target;
- access and credentials needed by the future runner;
- proof that the running artifact is the exact commit;
- permission for safe negative checks and never-touch targets.

The route normally has five parts: trigger delivery for the exact revision,
wait with a command that can fail, prove the deployed revision, exercise a real
consumer path, and prove the oracle can fail.

If CI deploys only from the default branch, there is no honest pre-merge Stage
2. Record a preview environment or a post-merge verdict before Done or release.
Use `stage2_unreachable` only when the project truly has no reachable delivery
boundary.

Validate read-only prerequisites. Show the exact target and ask before any
deploy, apply, migration, or other shared write. No access to run it is a setup
blocker, not a narrowing of future verdicts. Missing credentials, VPN, a URL,
or revision proof does not justify `stage2_unreachable`.

## Close with setup status, not a verdict

Installation has `installed` or `not installed`. Project setup has `configured`
or `setup blocked`. `READY` and `NOT READY` belong only to a Cerberus run against
a concrete product change; never use them for installation or setup.

Report the config path, artifact kind, Stage 1 commands and results, confirmed
Stage 2 route, access and revision proof, remaining blockers, and any required
agent restart. Remind the operator how to invoke `cerberus-setup`, `cerberus`,
and `cerberus-critic`.

Recommend running `cerberus` against the exact revision before a tracker task
moves to Done. A `NOT READY` verdict keeps that task open.

## Self-check before saying configured

- [ ] Did I read project instructions before choosing or running commands?
- [ ] Did I use project-owned wrappers instead of forbidden generic commands?
- [ ] Was every recorded Stage 1 command run and shown passing?
- [ ] Did I ask before lengthy or shared-state-changing work?
- [ ] Did I explain the three stages briefly in the selected language?
- [ ] Did I infer Stage 2 from repository evidence before asking the operator?
- [ ] Did I say back the proposed route and get it confirmed?
- [ ] Can the future runner access the target and prove the exact revision?
- [ ] Can the Stage 2 oracle fail safely?
- [ ] Is `stage2_unreachable` reserved for a true project-level absence?
- [ ] Did I report setup status without issuing a product verdict?
