---
name: gopnik-setup
description: Discover and verify this project's real Stage 1 and Stage 2 mechanics, then record them in gopnik.json so Gopnik does not guess. Use during installation, when the config still has placeholders, or when delivery changed.
---

# Setup - learn how this project is really verified

The gate attacks work and the critic attacks claims. Neither should guess how
this repository is tested or how a revision reaches the place where people use
it. Discover those mechanics, verify them, and record only what future runs can
actually execute.

## Select the language once

During first onboarding, the installation guide already selected the
conversation language. Reuse a valid top-level `language` from `gopnik.json`
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
having to understand Gopnik internals.

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

## Reconcile the candidates with what the project really runs

Project instructions name the route. They do not always name everything the
project verifies, and a Stage 1 that is honest about what it ran can still be
silent about what it never looked at.

Before recording anything, enumerate the executable checks this repository
actually contains, then compare that set with the commands you are about to
write. Read what CI invokes job by job, and look for check or test directories
the documented route never reaches: a suite in a second runtime, a browser
suite, contract or migration checks, a linter wired only into a workflow. Place
each one in exactly one of three: the documented command runs it, only CI runs it, or
nothing runs it. Nothing running it is the strongest case for recording it, not
the weakest — Stage 1 would be the only place it ever executes.

Partial coverage is a gap. One file of a suite running in one CI job leaves the
rest unrun, so read what a job invokes rather than whether the suite is
mentioned somewhere in the workflow.

When such a check exists, ask one question before recording Stage 1. Name the
check and the command that misses it, in the selected language:

> The project also has <check>, which <command> never runs. Should Stage 1 run it too?

This is a hard turn boundary. End with it and wait. Ask nothing when the
documented route already runs everything executable in the tree: a question
raised on every project teaches people to ignore it.

After the answer:

- **Include it.** Treat it exactly like any other Stage 1 command. It is
  recorded only if it runs and passes here, which may first need a user-scoped
  dependency install inside the existing autonomy budget, and it is passed with
  the others from fastest to slowest.
- **Leave it out.** Record the gap in the operational notes and continue. A gap
  the person declined is a decision; a gap nobody wrote down is the situation
  this section exists to end.
- **It cannot run on this machine at all.** Do not record it, and note why. Only
  a check that was run and passed may be written.

## Revisit a record an earlier version wrote

Everything above happens once, and the record it produces is only ever as good
as the version that wrote it. Updating the software replaces the skills and
leaves the project record exactly where it was, so a project set up before this
reconciliation existed keeps its gap forever. A configured project is never
re-onboarded and setup still refuses to rewrite it — but it can be *asked* what
has drifted.

Do this when the person asks, when an update guide sends you here, or before
relying on a Stage 1 you did not record yourself. Not during ordinary
onboarding: a project that was configured in this same conversation has nothing
to revisit.

```sh
python3 PATH/gopnik_setup.py --refresh
```

It writes nothing, ever, and it says one of three things. That the record still
matches the tree — then stop, say nothing about it, and do not manufacture a
finding. That a recorded command names a path that no longer exists — a suite
deleted, a wrapper renamed. That an executable check is in the tree which no
recorded command names.

That last one is a candidate, not a verdict. The helper compares the record with
the filenames; it cannot see inside a wrapper, and it does not pretend to. Put
each candidate in exactly one of the same three buckets as above — the recorded
command runs it, only CI runs it, or nothing runs it — by reading what actually
invokes it. Then ask the same question, in the selected language, and end the
turn on it:

> The project also has <check>, which <command> never runs. Should Stage 1 run it too?

After the answer, **include it** by recording it and nothing else:

```sh
python3 PATH/gopnik_setup.py --add-stage1 './ui-tests/run.sh'
```

Repeat `--add-stage1` for each one, fastest to slowest. It runs each command
first and records only what passes, so an answer of "add it" is never enough on
its own. It edits the recorded Stage 1 and leaves every other byte of that file
untouched — a hand-written `stage2`, a `stage2_unreachable` and its reason, an
operational note, a local-override indirection all survive exactly as written.
If it cannot locate the recorded Stage 1 it refuses and changes nothing rather
than rewriting a document it does not understand; say so and let the person edit
by hand. **Leave it out** and **it cannot run here** behave as above: nothing is
written either way, and the reason is recorded in the notes.

What this mode does not do is tell you the installed Gopnik itself is out of
date. Where it was installed as a plugin, the host owns that and the
installation guide already requires the version comparison. Where it was
installed by `install.sh`, nothing does: that route copies the skill directories
and nothing else, so there is no version on disk and no plugin record for a host
or a guide to compare against. This mode does not close that gap — Stage 1 is
offline and stays offline. What it reports is drift in the project's own record,
which is a different kind of stale and the only one visible from here.

## Run the mechanical part silently

Use whichever installed path exists:

```sh
python3 "$CLAUDE_PLUGIN_ROOT"/skills/gopnik-setup/gopnik_setup.py --defer-artifact-kind --language en
python3 .claude/skills/gopnik-setup/gopnik_setup.py --defer-artifact-kind --language en
python3 .agents/skills/gopnik-setup/gopnik_setup.py --defer-artifact-kind --language en
```

When the project defines its own checks, pass exactly those commands and defer
the delivery kind until Stage 1 passes, a critic has challenged the candidate
surfaces, and the person has confirmed how the result is used:

```sh
python3 PATH/gopnik_setup.py --defer-artifact-kind \
  --language en \
  --stage1 './app.sh --smoke' \
  --stage1 './app.sh --test'
```

Run the setup helper as the complete Bash command. Do not append a pipe,
redirect, `tail`, `tee`, `|| true`, or another wrapper: its tool result must
carry the helper's real exit status.

Repeat `--stage1` as needed. `--check` runs and reports without writing.
`--draft-stage2` prints a repository-derived proposal and writes nothing.

Run fast, read-only checks automatically. Ask before a lengthy suite or a
command that mutates shared state. Pass explicit checks from fastest to
slowest; the script stops at the first failure.

The request to install or set up Gopnik authorizes one continuous local setup
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

The script writes the selected language and the passing Stage 1 commands, but
guided setup leaves the delivery kind unset until the confirmation step below.
After the person answers, finalize the primary kind with
`--confirm-artifact-kind KIND`, and record what was confirmed with
`--surfaces <the confirmed surfaces, comma separated>`. Invoke the setup helper
exactly once in this step, with those two options and nothing else: do not probe
`--help`, repeat `--language`, or combine it with any setup option. The selected
language is already stored;
this preserves the Stage 1 evidence without
running it again. The script merges rather than replaces existing data. A
hand-written artifact kind, operational note, or legacy config path must
survive.

Choose that kind from this complete mapping without inspecting the helper or
rediscovering its choices: a deployed web UI, API, or always-on application is
`service`; an installed command is `cli`; an imported package or SDK is
`library`; a cluster or infrastructure bundle is `chart`; a host-loaded
extension is `plugin`; a schema or data transition is `migration`; and a
production model-call boundary is `model-boundary`. For several confirmed
surfaces, select the farthest delivery boundary; for example, a deployed web UI
plus an installed command has primary kind `service`. Reuse the exact helper
path that succeeded for Stage 1 and run the confirmation immediately.

Only Stage 1 commands that were actually run and passed may be written.
`stage2` stays empty until its real route is inferred and confirmed. A comment,
`echo`, or another always-green command is not a check.

`gopnik.json` stores stable project mechanics, not a feature-specific test
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

## Ignore the local override where the install scope requires

An ignored override protects only as far as the file that ignores it travels,
and which file that has to be depends on how Gopnik reaches this project.
Nobody passes you the install scope, and a standalone run has no conversation
to remember it from, so read it off the repository instead. Repository scope
means the team receives Gopnik with the project, so the question is whether
this repository carries a Gopnik skills directory of its own: a
`.claude/skills/gopnik-setup` or `.agents/skills/gopnik-setup` inside the
working tree that git does not ignore. Check both halves — `git ls-files` and
`git check-ignore` answer the second — because a skills directory the
repository ignores reaches nobody, which makes it a user-scope install however
it looks. Everything else is user scope too: a user-level plugin or skills
directory, or a copy belonging to a different project.

The copy you are running is a signal, not the answer. A project can carry a
committed `.claude/skills/gopnik-setup` while the copy in use is the user-level
one, and the team still receives the project's copy. If an answer carried from
the installation conversation disagrees with what the repository shows, the
repository decides.

At repository scope the ignore rule has to end up in a file that travels with
the repository: the project's `.gitignore`, or the nearest tracked ignore file
that already governs the override's directory. `.git/info/exclude` is not
committed, so a rule left only there protects the machine that ran setup and
nobody else — while the point of a repository-scope install is that the team
receives it with the project. The next person clones, creates their own
override, and has nothing stopping them committing private infrastructure paths
and the command that reads a secret.

A tracked ignore file is a tracked project file, so the authority boundary
above applies unchanged: ask before editing it, exactly once, in the selected
language, and wait for the answer.

> Stage 2 here needs values that belong to this machine, so they go into a separate local file. May I add that file to .gitignore, so it stays out of commits for everyone working on this repository?

This ignore question is a hard turn boundary. The visible response is that
question and nothing else: end with it and wait.

If the person agrees, write a pattern that matches the override you actually
created and nothing wider. If the person declines, still ignore the override
where only this machine sees it, and say in one sentence that the protection
now covers this machine only and the next person will not receive it. A decline
is a limitation you report, not a quiet fall back to the machine-local route.

At user scope none of that applies and nothing changes: a personal override
belongs in this repository's own exclude file, which needs no permission
because it is not part of the project. Write it where
`git rev-parse --git-path info/exclude` points rather than to a literal
`.git/info/exclude` — in a linked worktree or a submodule `.git` is a file and
that literal path does not exist. Do not ask the `.gitignore` question there.
It would propose an edit to someone else's project, for a file only you will
ever write.

Ask nothing at either scope when the run needs no override at all, when the
override lives outside the repository, or when a tracked rule already covers
it. An ignore rule that changes no file needs no question.

## Confirm how the project is used after delivery

Only after Stage 1 passes, inspect the candidate delivery surfaces. Treat an
old configuration, previous conversation, and memory as leads, never as
confirmation. Enumerate the product-facing things a person or another system
can consume after delivery: installed commands, packages, libraries, plugins,
HTTP services and APIs, web or mobile interfaces, background jobs, charts, and
migrations. Inspect deployment and release routes as evidence for how those
surfaces arrive, not as product-use choices of their own; the exception is a
reusable workflow or action that consumers invoke directly.

Require a concrete consumption boundary. A declared console entry point,
published package API, protocol/server entry point, renderable UI artifact, or
runnable job can support a candidate even when its route is broken. A filename,
function name, or string such as `server`, `serve`, or `web service` alone does
not prove a service exists.

Do not let the packaging label end the search. One binary can also run a
service and UI; one repository can ship several artifacts. A clean installed
CLI check proves only the CLI surface, not a service deployed from the same
binary.

Form a provisional classification and a compact inventory of its evidence.
Give both to an independent agent using `gopnik-critic`, with the mandate to
refute the classification by finding omitted delivery surfaces or conflicting
evidence. The critic brief must carry the same product-facing boundary: a CI,
deployment, or release route that only transports another artifact is
evidence, not a surviving surface; a reusable workflow/action or a product
background job that a consumer invokes is a surface. Do not leave the critic
to infer this split from the word `job`. Explicitly tell that spawned agent it
already is the independent adversary and must use `gopnik-critic` in independent
adversary mode without spawning another agent. Give that agent an explicit
completion contract: only after it has
inspected the evidence and completed the challenge, its penultimate line must
be `GOPNIK_CRITIC_SURFACES: <comma-separated surviving surface identifiers>`
and its last line must be exactly `GOPNIK_CRITIC_STATUS: complete`; if it
cannot complete the analysis, its last line must instead be
`GOPNIK_CRITIC_STATUS: blocked`. Do not continue to the user question unless
the correlated agent result carries the surfaces line and the complete marker.
Verify every load-bearing inclusion or exclusion against the repository before
using that set. If it does not survive this check, do not silently edit the
critic's set; return a corrected brief to one independent critic or report the
classification as blocked.
Use the surviving surfaces from that line in the question; do not restore a
candidate the critic refuted. The critic does not decide how the product is really operated and
does not question the person directly. Fold its surviving candidates into one
short question. Keep the critic's technical findings internal: this is a
product-use confirmation, not a defect report. Keep that product-use
confirmation to at most two short sentences; the brief stage orientation and
Stage 1 status may precede it.
Before the product-use question, give one plain status sentence that names
`Stage 1` and says its local check passed or is ready, for example:
`Stage 1 is ready — the project's local check passed.`
Name the plausible surfaces in plain language and, when necessary, add only one
brief uncertainty such as `the delivery route does not prove which one ships`.
Do not list packaging errors, missing files, workflow defects, or implementation
details here. Handle a finding separately only when it blocks Stage 1 or leaves
no plausible surface to confirm.

Do not ask the person to choose an internal `artifact_kind`. Name only the
concrete surfaces found in this repository. When several are plausible, ask:

> I found <A> and <B>. After delivery, do people use only <A>, only <B>, or both?

When only one is visible, ask:

> I found <A>. Is that the only way people use the project after delivery, or should I include another deployed or consumed surface?

This confirmation question is a hard turn boundary. End with it and wait.
Until the answer arrives, do not finalize the delivery kind, inspect or present
infrastructure, draft or run Stage 2, or ask about a stand, access, or browser
tooling.

After the answer, finalize the primary kind. For a hybrid project, choose the
kind at the farthest confirmed delivery boundary, then cover every confirmed
surface in Stage 2 and the operational notes. Never discard the other surfaces
because the internal record has one primary kind: `artifact_kind` holds one
word, `--surfaces` holds the set, and a verdict that has to decide whether
Stage 2 covered every surface has nowhere else to read it.

## Ask whether Stage 2 has somewhere real to run

After the person confirms the delivery surfaces, explain in one sentence that
Stage 2 checks the built or deployed result where people actually use it.

For a deployed service or application, do not inspect and present its
infrastructure first. Ask only:

> Is there a test or staging environment where Gopnik can verify the deployed version?

The visible response must combine the explanation and question exactly:

> Stage 2 checks the built or deployed result where people actually use it. Is there a test or staging environment where Gopnik can verify the deployed version?

This availability question is a hard turn boundary. End with it and wait.

If the answer is yes, ask one related follow-up:

> How does a new version get there, and how can the agent obtain access? Do not send secrets; just name the existing access method.

Then wait again. Do not ask for infrastructure fields or present a command
route before the person answers.

For a package, CLI, plugin, or another artifact used only through a clean
consumer environment, create that environment yourself instead of asking an
irrelevant staging question. If any confirmed surface is deployed, ask the
stand question; a clean consumer check may remain another Stage 2 cell, but it
does not cover the deployment.

After the answer, inspect CI triggers, deploy jobs, manifests, release scripts,
service URLs, and version metadata. Combine repository evidence with what the
person said. Verify access and all read-only prerequisites you can, then silently
record only a route a future Gopnik run can execute.

During that investigation, inspect the real product surfaces Stage 2 must
exercise. Do not ask about browser tooling merely because frontend files exist.
If the deployed product has a UI, first look for a project-owned browser route
such as Playwright or Cypress against the stand, then for a browser or
computer-use tool already available to the agent. A route counts only when it
can target the stand without tracked-file edits. A test hard-coded to loopback
proves local UI coverage, not a browser route against the stand — and local UI
coverage is exactly what Stage 1 is for. A suite that could be pointed at the
stand but is configured for loopback here counts as loopback until something
shows otherwise. When such a suite exists and Stage 1 does not already run it,
reconcile it as above instead of discarding it: the loopback rule disqualifies
it from this stage, not from the project.

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

A recorded route never authenticates as the person running it. Do not read,
copy, link, or write the operator's own session state — an agent's credential
file, a browser profile, a cloud CLI's cached login, a `kubectl` context they
are working in. A symlink is the file, not a copy of it, and a directory around
a shared credential is not isolation. Refreshable credentials make this worse
than it looks: an OAuth refresh token is single-use, so a verification run that
borrows one logs the operator out of everything else using it, mid-work.
Record a route that takes its own credential from the environment, and when
none exists, say so as a setup blocker rather than reaching for theirs.

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

## Close with a human-sized status and recommendation, not a verdict

Installation has `installed` or `not installed`. Project setup has `configured`
or `setup blocked`. `READY` and `NOT READY` belong only to a Gopnik run against
a concrete product change.

Setup cannot be `configured` until the Stage 2 target and access are verified,
or the absence of a project-level target is confirmed and recorded. Before
that, setup is still in progress.

If setup is blocked, do not use the configured closing flow below. End with the
single blocker question described above. Do not append the recommendation or
tracker example to a `setup blocked` response.

Only after setup reaches `configured`, give the status report and recommendation
below. Keep them as two distinct parts: finish the status report first, then
start the recommendation as a separate paragraph. Do not merge the
recommendation into a status bullet.

Use at most three short points: whether Gopnik is installed; whether the
project's local check is ready and what was observed; and whether the real
delivery path is ready or the one remaining blocker. Mention a restart only if
required.

Do not report configuration paths, the saved language, artifact kinds, internal
keys, JSON, raw command routes, marketplace mechanics, or every installed file.

Treat the internal project record as already handled, not as a user-facing
repository change. Never say that a configuration file was created, changed,
is untracked, or should be committed. Do not include it in a working-tree
summary. After the recommendation and tracker example, stop: do not append notes
about files, Git status, cleanup, or what the person should commit.

After the configured status report, give one universal recommendation. Keep it
separate from the example. Do not qualify it with project-specific process or
artifact details. Use the exact first sentence for the selected language:

- English: `We recommend integrating Gopnik into the development cycle.`
- Russian: `Рекомендуем встроить Gopnik в цикл разработки.`

Then give the tracker flow separately as an example in the selected language:

English:

> For example, when work is managed through tasks in a tracker:
>
> 1. After the task is defined, `gopnik-critic` checks its wording and completion criteria.
> 2. After the solution is prepared, `gopnik-critic` checks the chosen approach.
> 3. After implementation, `gopnik` checks the completed change before the task moves to `Done`.

Russian:

> Например, если работа ведётся через задачи в трекере:
>
> 1. После постановки задачи `gopnik-critic` проверяет её формулировку и критерии готовности.
> 2. После подготовки решения `gopnik-critic` проверяет выбранный подход.
> 3. После реализации `gopnik` проверяет готовое изменение перед переводом задачи в `Done`.

Do not turn the recommendation into a mandatory workflow or add command-style
prompts for the person to copy.

## Self-check before saying configured

- [ ] Did I read project instructions before choosing or running commands?
- [ ] Did I use project-owned wrappers instead of generic commands?
- [ ] Did I explain the three stages before internal work?
- [ ] Was every recorded Stage 1 command run and shown passing?
- [ ] Did I compare the recorded Stage 1 against what CI and the tree really
      run, and ask about every executable check the documented route misses?
- [ ] On a record an earlier version wrote, did I revisit it rather than trust
      it — and stay silent when there was nothing to report?
- [ ] Did a loopback browser suite end up assigned to Stage 1 rather than
      dropped for failing the stand test?
- [ ] If Stage 1 failed, did I stop before inspecting or discussing Stage 2?
- [ ] Did a blocker response contain one problem, one next step, and one question?
- [ ] Did I ask before lengthy or shared-state-changing work?
- [ ] Did I treat approval as applying to the setup goal rather than each safe command?
- [ ] Did I continue safe local diagnostics without repeated permission questions?
- [ ] Did every first Stage 1 command have time and memory safety limits?
- [ ] Did I defer the delivery kind until Stage 1 passed, the critic challenged it, and the person confirmed it?
- [ ] Did `gopnik-critic` try to find omitted or conflicting delivery surfaces?
- [ ] For a hybrid project, does Stage 2 cover every confirmed surface rather than only the primary kind?
- [ ] For a deployed service, did I first ask only whether a stand is available?
- [ ] If yes, did I ask how delivery and access work without requesting secrets?
- [ ] Before an authenticated production read or secret access, did I obtain
      target-specific confirmation for one read-only probe?
- [ ] Did any project-owned browser route actually target the stand without tracked-file edits?
- [ ] If a deployed UI had no browser route, did I offer Playwright MCP only after discovering that gap?
- [ ] After connecting MCP, did I state and respect the host's restart boundary?
- [ ] Did I avoid batching unrelated Stage 2 questions?
- [ ] Can the future runner access the target and prove the exact revision?
- [ ] Can the Stage 2 check fail safely?
- [ ] Does the recorded route take its own credential, rather than reading,
      copying or linking the operator's own session state?
- [ ] Is `stage2_unreachable` reserved for a true project-level absence?
- [ ] Is shared verification portable, with private local values kept separate?
- [ ] Did I read the install scope off the repository rather than assume it?
- [ ] At repository scope, did the override's ignore rule reach a file the team
      receives, after exactly one question — and at user scope did I ignore it
      where only this machine sees it, and ask nothing?
- [ ] Did I keep configuration files and JSON out of normal user-facing text?
- [ ] Did I omit internal files, Git status, and commit advice from the final response?
- [ ] If setup was blocked, did I stop before the recommendation and tracker example?
- [ ] Did I keep the universal recommendation separate from the tracker example?
- [ ] Did I report setup status without issuing a product verdict?
