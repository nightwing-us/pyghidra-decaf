# Changelog

All notable changes to **pyghidra-decaf** are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — targeting v0.3.1

A reliability release focused on plugin installation and multi-version Ghidra support.

### Fixed

- **Plugins that declare no extra Java imports now install correctly.** Previously a
  plugin that didn't specify any `plugin_imports` generated a Java stub missing its
  required Decaf base-class import, failing to compile with
  `cannot find symbol: class DecafProgramPlugin` (or `DecafPlugin`) and never
  installing. The generated stub now always includes the mandatory base-class import.
- **`pyghidra_decaf_bootstrap` is reliable on machines with multiple Ghidra versions
  installed.** It previously located Ghidra's extensions directory by name-matching
  `GHIDRA_INSTALL_DIR`, which could resolve to the wrong version's directory — or none
  — and silently compile nothing. It now uses the extension path that pyghidra itself
  resolves, and fails with a clear, actionable error if the directory can't be
  determined.

### Improved

- **Clearer plugin load-failure diagnostics.** When a plugin's Java class fails to
  load, Decaf now recompiles the generated stub and surfaces the *real* Java compiler
  error (e.g. `cannot find symbol …`) in Ghidra's console via `Msg.error`, instead of
  leaving you with an opaque `ClassNotFoundException`. The propagated
  `DecafLoadException` carries the underlying cause.

### Other

- License metadata migrated to the PEP 639 form (`license = "Apache-2.0"`). No license
  change — still Apache-2.0 — but packaging tools now see the standardized SPDX
  expression.
- Dependency lockfile regenerated (dead deps removed, compatible updates).
- Expanded automated test coverage for the fixes above (no runtime impact).
- README: added a "Projects using pyghidra-decaf" section.

### Upgrade

Drop-in upgrade from v0.3.0 — no API or breaking changes. If you previously worked
around the import-less-plugin install failure by adding a dummy `plugin_imports`
entry, that workaround is no longer needed.

## [0.3.0]

Initial public release.

[Unreleased]: https://github.com/nightwing-us/pyghidra-decaf/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/nightwing-us/pyghidra-decaf/releases/tag/v0.3.0
