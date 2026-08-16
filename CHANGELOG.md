# Changelog

# [2.0.0](https://github.com/concordloom/cerberus/compare/v1.7.0...v2.0.0) (2026-08-16)


* feat!: ship skills, not automation ([#34](https://github.com/concordloom/cerberus/issues/34)) ([b178539](https://github.com/concordloom/cerberus/commit/b178539908f678483a11a1477796ce12fc5ffa43)), closes [#31](https://github.com/concordloom/cerberus/issues/31) [#33](https://github.com/concordloom/cerberus/issues/33)


### BREAKING CHANGES

* the PostToolUse and Stop hooks are removed, along with the
wiring the installer used to merge into .claude/settings.json and
.codex/hooks.json, and the six cerberus.json keys that only they read. Projects
upgrading from 1.7 or earlier must delete those entries by hand; the README says
how, and does not do it for them, because editing a file the user owns is the
thing this version stopped doing.

Deciding when a change deserves verification was never ours to decide. The hooks
could tell that code had changed and never whether the change mattered, and

# [1.7.0](https://github.com/concordloom/cerberus/compare/v1.6.0...v1.7.0) (2026-08-16)


### Features

* refusals are off until a project asks for them ([#32](https://github.com/concordloom/cerberus/issues/32)) ([7f6e8db](https://github.com/concordloom/cerberus/commit/7f6e8db69ddb979c6ffc7d9dc94d674edf6869fe)), closes [#31](https://github.com/concordloom/cerberus/issues/31)

# [1.6.0](https://github.com/concordloom/cerberus/compare/v1.5.0...v1.6.0) (2026-08-16)


### Features

* **codex:** real hook support, and the bypass the first attempt introduced ([#30](https://github.com/concordloom/cerberus/issues/30)) ([33ae5fb](https://github.com/concordloom/cerberus/commit/33ae5fbcb62a775b03094ae3e7af37189401884e)), closes [#27](https://github.com/concordloom/cerberus/issues/27)

# [1.5.0](https://github.com/concordloom/cerberus/compare/v1.4.1...v1.5.0) (2026-08-16)


### Features

* close the loop after installing ([#26](https://github.com/concordloom/cerberus/issues/26)) ([484c0fe](https://github.com/concordloom/cerberus/commit/484c0fed4c6eb485a70a9694c37c8bcbab465ee3)), closes [#25](https://github.com/concordloom/cerberus/issues/25)

## [1.4.1](https://github.com/concordloom/cerberus/compare/v1.4.0...v1.4.1) (2026-08-15)


### Bug Fixes

* **install:** do not pin the repository name in the tarball path ([#16](https://github.com/concordloom/cerberus/issues/16)) ([e30c292](https://github.com/concordloom/cerberus/commit/e30c292d9615778c3c17afe7d9e02a7f4f1140b9)), closes [#15](https://github.com/concordloom/cerberus/issues/15)

# [1.4.0](https://github.com/concordloom/cerberus-skill/compare/v1.3.0...v1.4.0) (2026-08-15)


### Features

* **setup:** a third head — install it, then watch it refuse something ([#14](https://github.com/concordloom/cerberus-skill/issues/14)) ([80d71b1](https://github.com/concordloom/cerberus-skill/commit/80d71b17b2cf5f5f6e2802d3426405d021422d18)), closes [#13](https://github.com/concordloom/cerberus-skill/issues/13) [#13](https://github.com/concordloom/cerberus-skill/issues/13) [#13](https://github.com/concordloom/cerberus-skill/issues/13) [#13](https://github.com/concordloom/cerberus-skill/issues/13) [#13](https://github.com/concordloom/cerberus-skill/issues/13) [#13](https://github.com/concordloom/cerberus-skill/issues/13)

# [1.3.0](https://github.com/concordloom/cerberus-skill/compare/v1.2.2...v1.3.0) (2026-08-15)


### Bug Fixes

* four regressions the [#3](https://github.com/concordloom/cerberus-skill/issues/3) and [#5](https://github.com/concordloom/cerberus-skill/issues/5) fixes introduced ([#12](https://github.com/concordloom/cerberus-skill/issues/12)) ([02b4e7f](https://github.com/concordloom/cerberus-skill/commit/02b4e7fc203610f833578fa3478bfd9ba5384a1d)), closes [#11](https://github.com/concordloom/cerberus-skill/issues/11) [#11](https://github.com/concordloom/cerberus-skill/issues/11)


### Features

* **ci:** check the slash commands, which nothing checked before ([#9](https://github.com/concordloom/cerberus-skill/issues/9)) ([e5d2c98](https://github.com/concordloom/cerberus-skill/commit/e5d2c981b42a34950974e530930baaefae9d60d0)), closes [#1](https://github.com/concordloom/cerberus-skill/issues/1) [#1](https://github.com/concordloom/cerberus-skill/issues/1) [#4](https://github.com/concordloom/cerberus-skill/issues/4)

## [1.2.2](https://github.com/concordloom/cerberus-skill/compare/v1.2.1...v1.2.2) (2026-08-15)


### Bug Fixes

* **commands:** let the pull request close the issue, not the verdict ([#7](https://github.com/concordloom/cerberus-skill/issues/7)) ([ee85b88](https://github.com/concordloom/cerberus-skill/commit/ee85b8853a0ed50f670ae4f2193626ed0f90ced2)), closes [#3](https://github.com/concordloom/cerberus-skill/issues/3) [#2](https://github.com/concordloom/cerberus-skill/issues/2) [#1](https://github.com/concordloom/cerberus-skill/issues/1)
* **hooks:** only mark files that belong to the project ([#8](https://github.com/concordloom/cerberus-skill/issues/8)) ([4dec65a](https://github.com/concordloom/cerberus-skill/commit/4dec65aa2a7e6610b3d12b924c58e3457364788d)), closes [#5](https://github.com/concordloom/cerberus-skill/issues/5)

## [1.2.1](https://github.com/concordloom/cerberus-skill/compare/v1.2.0...v1.2.1) (2026-08-15)


### Bug Fixes

* **commands:** address the issue by name, not by a zero-indexed placeholder ([#2](https://github.com/concordloom/cerberus-skill/issues/2)) ([7d1d843](https://github.com/concordloom/cerberus-skill/commit/7d1d843860e09734450f3aebe5919152f3e2be5a)), closes [#1](https://github.com/concordloom/cerberus-skill/issues/1)

# [1.2.0](https://github.com/concordloom/cerberus-skill/compare/v1.1.0...v1.2.0) (2026-08-15)


### Features

* **critic:** ship the other half of the cycle as a skill ([8db7c05](https://github.com/concordloom/cerberus-skill/commit/8db7c05e5a2df3a68268404c39f0588c312ee650))

# [1.1.0](https://github.com/concordloom/cerberus-skill/compare/v1.0.1...v1.1.0) (2026-08-15)


### Features

* **install:** install with one command, without cloning first ([1c6eb23](https://github.com/concordloom/cerberus-skill/commit/1c6eb23d0186146ec2397317045e02f9c64169e2))
* **skill:** anchor the gate to an issue written before the work ([dc11fa0](https://github.com/concordloom/cerberus-skill/commit/dc11fa074cbe3e6f871faf30c338c1ebd7c28bda))

## [1.0.1](https://github.com/concordloom/cerberus-skill/compare/v1.0.0...v1.0.1) (2026-08-15)


### Bug Fixes

* **release:** bump past the version that shipped broken ([85730b4](https://github.com/concordloom/cerberus-skill/commit/85730b4c9d2678e712abc07531340a29437ae850))

# 1.0.0 (2026-08-15)

_This entry was rewritten by hand: it was generated from commits predating
the English-only policy and came out in Russian. Later entries are generated._

The first published version. It could not be installed by anyone: two defects in
the manifests passed every static check and were found only by installing for
real. Both are fixed in this tag, which is why `1.0.0` is also the first version
that works — but see `1.0.1`, because the version string never changed while it
was broken, and a marketplace installation updates only when it does.

### Bug Fixes

* **marketplace:** `source` must be an explicit relative path. The entry used
  `"source": "cerberus"` with `metadata.pluginRoot`; the documentation permits
  that form and the loader rejects it with `source: Invalid input`
  ([8fe1e07](https://github.com/concordloom/cerberus-skill/commit/8fe1e07a35c021fdf8913089c073ae5c019c14f0))
* **plugin:** do not declare `skills` and `hooks` in the manifest. Both are
  loaded by convention, so declaring them registered the same files twice and
  the plugin failed to load *after installing successfully*
  ([281c2c0](https://github.com/concordloom/cerberus-skill/commit/281c2c0e80d9dcca45fe57cd4e70466ea967d52b))
* the example configuration silently narrowed the gate: `claim_patterns`
  replaces the defaults rather than extending them, and the example listed three
  of the fifteen
  ([d575d61](https://github.com/concordloom/cerberus-skill/commit/d575d61d1831c8d7b51e1eb9603a00c37e40f563))

### Features

* adversarial verification gate, generalised to any kind of artifact. Stage 2
  crosses whatever the artifact's delivery boundary is, rather than assuming a
  deployment — which is what makes it usable for a library, where the boundary is
  the built package and a consumer's dependency resolution
  ([f6ef861](https://github.com/concordloom/cerberus-skill/commit/f6ef86127166e19a4a59284e572b2953f3d0a86f))
* plugin marketplace, one-command install, header artwork and the mark
  ([faaebf7](https://github.com/concordloom/cerberus-skill/commit/faaebf7c55d8e00ed64ba92aae1a8b57bbbcc1ec))
* the gate runs on this repository, on itself; both loader lessons encoded in CI
  ([5e3c37a](https://github.com/concordloom/cerberus-skill/commit/5e3c37a29aa4c8ed4d497833bdfce9425d866478))
