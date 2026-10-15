# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-10-15

### Added

- `decompose` skill: phases 0–6 of component-based decomposition plus a
  tactical forking path, each with artifacts, RFCs, fitness functions and an
  approval gate.
- Scripts (Python 3.9+, stdlib only): workspace init, component sizing,
  common-domain candidates, regex dependency extraction for 15+ languages,
  edge conversion from native tools, coupling analysis with cycles and
  domain cohesion, generic fitness checks with a CI guard mode, RFC and
  state management.
- Adapters for JVM, .NET, TypeScript/JavaScript, Python, Go, PHP, Ruby and
  other ecosystems.
- JSON schemas for every artifact.
- Worked example (`examples/tiny-monolith`) and test suite.
- Claude Code plugin marketplace manifest.
