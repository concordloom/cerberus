# Uninstall Gopnik

You are the removal agent. Remove only the selected Gopnik installation,
preserve project verification knowledge by default, and prove what is gone.

## 1. Reuse the saved language without asking

Read the first existing project configuration from `gopnik.json`,
`.claude/gopnik.json`, or `.codex/gopnik.json`. Use Russian when its
top-level `language` is `ru` and English when it is `en`.

For an older installation with no valid saved language, continue in the
language of the current conversation; if there is no signal, default to
English. Never ask a dedicated language question during uninstall. The choice
was onboarding state and should not become uninstall ceremony.

## 2. Discover installed scopes

Inspect before deleting. Look for:

- `gopnik@concordloom` in the current agent's plugin registry;
- repository copies of `gopnik/`, `gopnik-critic/`, and `gopnik-setup/`
  under `.claude/skills/` or `.agents/skills/`;
- project configuration at `gopnik.json`, `.claude/gopnik.json`, or
  `.codex/gopnik.json`.

If Gopnik exists in more than one scope, show the scopes and ask which ones
to remove. Do not infer "all" merely because several installations exist.

## 3. Confirm exact destructive targets

Show every plugin selector and filesystem path that will be removed. Resolve
paths explicitly. Do not use broad globs, unresolved variables, recursive
deletion of an agent directory, or deletion of a shared symlink target. If a
skill path is a symlink, remove only the link.

The initial request to follow this guide authorizes discovery, not deletion.
Confirmation is a hard turn boundary: end the discovery response with a short
question naming the exact targets, and do not run any removal command in that
turn. Continue only after the user explicitly confirms those targets.

Configuration is preserved by default because it contains the project's Stage
1 and Stage 2 delivery mechanics. Ask for separate explicit confirmation before
deleting any Gopnik configuration.

## 4. Remove only the selected installation

For Claude Code:

```sh
claude plugin uninstall gopnik@concordloom
```

For Codex:

```sh
codex plugin remove gopnik@concordloom
```

For repository installation, remove only the exact discovered skill paths:

```text
.claude/skills/gopnik/
.claude/skills/gopnik-critic/
.claude/skills/gopnik-setup/
.agents/skills/gopnik/
.agents/skills/gopnik-critic/
.agents/skills/gopnik-setup/
```

Do not remove a marketplace registration by default because it may provide
other plugins. Offer that as a separate cleanup only after inspecting it.

Delete `gopnik.json`, `.claude/gopnik.json`, or `.codex/gopnik.json` only
after the separate confirmation above.

## 5. Verify and report

Verify that each selected plugin entry or exact skill directory is absent and
that unselected scopes and configuration remain. If the agent caches plugins,
state that a restart is required.

Finish with what was removed, what was preserved, whether a restart is needed,
and any scope that could not be removed. Include the reinstall guide:
`https://raw.githubusercontent.com/concordloom/gopnik/main/docs/install.md`.

If configuration was deleted, say plainly that ordinary uninstall does not
restore it.
