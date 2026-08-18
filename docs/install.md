# Install and configure Cerberus

You are the installation agent. Complete the installation and project setup;
do not stop after copying files.

## 1. Ask for the conversation language

Before any other onboarding text, always ask this exact question in English:

> Which language would you like me to use: English or Russian?

Your response must end after that question. Do not inspect, fetch another
resource, install, explain the stages, or announce a plan before the user
answers. Then use the selected language for every explanation, question, and
the final report. Keep commands, paths, configuration keys, skill names, and
status names unchanged.

## 2. Inspect before asking or changing

Confirm the project root. Read repository instructions such as `AGENTS.md`,
`CLAUDE.md`, contribution docs, package scripts, build wrappers, CI workflows,
deployment manifests, and the existing `cerberus.json`. Inspect the working
tree and preserve unrelated changes.

Infer the agent host, installation route, toolchain, artifact kind, Stage 1
commands, and likely delivery route from repository evidence. Do not ask the
user for facts the repository already answers. In particular, never bypass a
project-owned wrapper with generic commands such as `go test`, `npm test`, or
`pytest` when the project tells agents to use something else.

Keep onboarding light: two interactions are normally mandatory - the language
question and confirmation of the inferred Stage 2 route. If important facts
remain, ask at most one short, batched follow-up.

## 3. Install all three skills

One installation must provide this complete bundle:

- `cerberus` attacks a completed change;
- `cerberus-critic` attacks an important claim;
- `cerberus-setup` records this project's verification mechanics.

Prefer the current host's native plugin or skill mechanism. Do not install into
every detected agent merely because several CLIs exist.

### Claude Code

```sh
claude plugin marketplace add concordloom/cerberus
claude plugin marketplace update concordloom
claude plugin install cerberus@concordloom
claude plugin update cerberus@concordloom
```

### Codex

```sh
codex plugin marketplace add concordloom/cerberus
codex plugin marketplace upgrade concordloom
codex plugin add cerberus@concordloom
```

### Any other agent

Use that host's documented plugin or skills mechanism. Install the three
directories under `plugins/cerberus/skills/` together, including every file in
them. Verify that the host discovers all three skills; do not assume it reads a
Claude- or Codex-specific directory.

### Repository-local fallback

If native skills are unavailable or the team should receive them through Git,
run this from the project root:

```sh
curl -fsSL https://raw.githubusercontent.com/concordloom/cerberus/main/install.sh | sh
```

This needs Python 3.10+, `sh`, `tar`, and `curl` or `wget`. It installs under
`.claude/skills/`, or `.agents/skills/` when that directory already exists.
Re-running updates the skills and preserves existing configuration.

An existing installation is not proof that it is current. Refresh the
marketplace snapshot, update or reinstall the plugin, and verify that its
reported version matches the current marketplace entry. Then verify that
`cerberus`, `cerberus-critic`, and `cerberus-setup` are present.

If the host needs a restart to load an update, say so and continue setup by
reading the newly installed files directly. Never pretend the current session
loaded a new skill or keep following the older cached copy.

## 4. Explain the three stages briefly

Use the selected language and keep this to three short points:

- **Stage 0** maps what can break before testing begins.
- **Stage 1** attacks the code locally: tests, negative cases, and the real
  consumption path.
- **Stage 2** attacks the built or deployed result where people actually use
  it.

Stage 0 is rebuilt for each change. Stage 1 is mostly discoverable from the
repository. Stage 2 needs the repository evidence plus confirmation from the
person who knows the real delivery path.

## 5. Configure Stage 1 from project rules

Read and follow the installed `cerberus-setup` skill. Use its script only after
reading the repository's instructions.

When the repository defines its own commands, pass exactly those commands to
the script instead of letting it guess. Repeat `--stage1` for each command:

```sh
python3 PATH/cerberus_setup.py --artifact-kind service \
  --stage1 './app.sh --smoke' \
  --stage1 './app.sh --test'
```

Use the actual installed path and inferred artifact kind. When no authoritative
project instructions exist, the script may detect and run candidates itself.
It must write only Stage 1 commands that actually passed.

Run fast, read-only checks without making the user supervise them. Ask before a
lengthy suite or any command that mutates shared state. If a fast required check
is already red, do not start a long suite without permission and do not run
Stage 2 as a verification attempt. Installation may still be successful, but
project setup is blocked. You may still infer and discuss the future Stage 2
route.

Order explicit `--stage1` commands from fastest to slowest. The setup script
stops at the first failure, so a red smoke check never falls through into the
full suite.

A build, package smoke test, or `--version` check is a Stage 2 prerequisite,
not Stage 2 itself.

## 6. Infer Stage 2, then confirm it

Inspect CI triggers, deploy jobs, Dockerfiles, charts, manifests, release
scripts, service endpoints, and version metadata. Build the most likely route
from that evidence and present it in ordinary language. Ask the user to confirm
or correct your proposal; do not begin with an infrastructure questionnaire.

This confirmation is a hard turn boundary. End that response with the
confirmation question. Do not report `configured`, give the final setup
summary, or continue into invocation and lifecycle advice until the user has
answered.

For example, if a repository contains a single binary, Docker support, and a
Helm chart, ask which of those observed routes is used in reality and propose
the corresponding daemon, API, and dashboard checks. If repository evidence is
insufficient, only then ask the open question: "How does this change get to
where it really runs, and how would you know it arrived?"

Translate the confirmed answer into an exact route:

1. trigger delivery for the exact revision;
2. wait for the matching pipeline or rollout with a command that can fail;
3. prove the running artifact is that revision;
4. exercise a real API, UI, consumer, or operational path;
5. prove the oracle can fail with a safe negative or counterfactual check.

If deployment happens only after a push or merge to the default branch, say
plainly that a full Cerberus verdict is post-merge. It can gate moving the task
to Done or releasing it, but it cannot honestly gate that merge unless the
project adds a preview environment.

After the route is confirmed, ask one batched follow-up only for facts still
missing: the exact URL or target, how the deployed revision is proven, whether
the agent has access, and whether safe negative checks are allowed. Never put
credentials in `cerberus.json`.

Record delivery mechanics in `cerberus.json`: artifact kind, executable Stage
1 and Stage 2 commands, and operational notes. Do not put a feature-specific
test plan there; Cerberus derives that from the task during Stage 0.

Validate Stage 2 prerequisites with read-only checks. Show the exact target and
obtain explicit confirmation before a deploy, migration, apply, or other shared
write. A missing tool, VPN, token, permission, URL, or revision proof is a setup
blocker, not `stage2_unreachable`. Use `stage2_unreachable` only when the project
truly has no reachable delivery boundary, and record the project-level reason.

## 7. Report the result without a product verdict

Keep the final report short and separate these statuses:

- **Installation:** `installed` or `not installed`.
- **Project setup:** `configured` or `setup blocked`.
- **Change verdict:** `READY` or `NOT READY` - never use these during
  installation because no product change is under test.

Project setup cannot be `configured` before the inferred Stage 2 route has been
confirmed. If the user has not answered that question, setup is still in
progress, not complete.

Report the installation scope, verification of all three skills, config path,
Stage 1 commands and observed results, confirmed Stage 2 route, access and
revision proof, any blocker, and whether a restart is required.

Then give three copyable prompts in the selected language:

- run `cerberus-setup` to refresh project setup;
- run `cerberus` against a completed change;
- run `cerberus-critic` against an important diagnosis or claim.

Recommend integrating Cerberus into the existing lifecycle: before a tracker
task moves to Done, run `cerberus` against the exact revision and attach its
evidence; `NOT READY` keeps the task open. Offer to add that rule to the
repository or tracker workflow, but do not edit those files unless asked.
