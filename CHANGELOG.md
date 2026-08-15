# Changelog

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
