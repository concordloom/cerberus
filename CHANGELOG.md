# Changelog

# 1.0.0 (2026-08-15)


### Bug Fixes

* **marketplace:** source должен быть явным относительным путём ([8fe1e07](https://github.com/concordloom/cerberus-skill/commit/8fe1e07a35c021fdf8913089c073ae5c019c14f0))
* **plugin:** не объявлять skills и hooks в манифесте — они грузятся по соглашению ([281c2c0](https://github.com/concordloom/cerberus-skill/commit/281c2c0e80d9dcca45fe57cd4e70466ea967d52b))
* пример конфигурации молча сужал гейт ([d575d61](https://github.com/concordloom/cerberus-skill/commit/d575d61d1831c8d7b51e1eb9603a00c37e40f563))


### Features

* адверсариальный гейт готовности, обобщённый под любой артефакт ([f6ef861](https://github.com/concordloom/cerberus-skill/commit/f6ef86127166e19a4a59284e572b2953f3d0a86f))
* площадка плагинов, простая установка, шапка и знак ([faaebf7](https://github.com/concordloom/cerberus-skill/commit/faaebf7c55d8e00ed64ba92aae1a8b57bbbcc1ec))
* цербер включён на самом себе, уроки загрузчика закодированы в CI ([5e3c37a](https://github.com/concordloom/cerberus-skill/commit/5e3c37a29aa4c8ed4d497833bdfce9425d866478))

## 1.0.1 — 2026-08-15

The first version that actually installs. `1.0.0` was published and could not be
installed by anyone; both reasons passed every static check and were found only
by installing for real.

### Fixed

- Marketplace entry used `"source": "cerberus"` with `metadata.pluginRoot`. The
  documentation permits that form; the loader rejects it with
  `source: Invalid input`. The source is now an explicit relative path.
- `plugin.json` declared `skills` and `hooks`. Both are loaded by convention, so
  declaring them registered the same files twice and the plugin failed to load
  **after installing successfully** — which reads as a working install until the
  first hook should have fired and did not.
- The example configuration, copied verbatim as documented, silently narrowed
  the gate: `claim_patterns` replaces the defaults rather than extending them,
  and the example listed three of the fifteen. It now sets only the key that has
  no sensible default.
- CI compiled nothing: after the restructure the step still pointed at the old
  `hooks/` path, and `compileall` prints a complaint and exits 0 on a missing
  directory, so the job stayed green while checking nothing.

### Added

- Install as a Claude Code plugin: `/plugin marketplace add
  concordloom/cerberus-skill` then `/plugin install cerberus@concordloom`. The
  hooks travel with the skill; nothing to copy, no settings file to edit.
- `install.sh` for Codex and for anyone who wants the files in their repository.
  Detects `.claude` or `.agents`, merges the hooks into an existing
  `settings.json` without clobbering it, and is safe to re-run.
- The gate runs on this repository, on itself, with its Stage 2 recorded in
  `.claude/cerberus.json`: the delivery boundary here is the plugin loader, and
  no static check can reach it.
- Header artwork and the mark, with the stage palette sampled from the eyes in
  the artwork rather than chosen to look similar.

### Changed

- Russian documents passed through `ru-text`: 223 non-breaking spaces after
  single-letter prepositions, one bureaucratic construction removed.

## 1.0.0 — 2026-08-15

Initial publication of the skill, the two hooks and the translation-parity
check. Not installable; see 1.0.1.

Stage 2 was generalised in this version from "deploy it and poke it" to crossing
whatever the artifact's delivery boundary is — which is what makes the skill
usable for a library, where the boundary is the built package and a consumer's
dependency resolution rather than a server.
