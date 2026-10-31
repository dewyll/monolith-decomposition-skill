# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-10-31

### Added

- `change_coupling.py`: churn per component and co-change pairs from git
  history; pairs that change together without any static dependency are
  flagged as hidden coupling.
- `find_data_coupling.py`: shared tables per component from ORM mappings
  (SQLAlchemy, Django, JPA, EF Core, Rails, Laravel, TypeORM, Sequelize,
  GORM, Ecto) and SQL in string literals, with `database` edges from users
  to the owning component. `--schema` restricts it to tables from the DDL.
- `suggest_domains.py`: deterministic Louvain clustering over imports and
  co-change as a measured starting point for Phase 5. Writes suggestions
  and an optional `domains.draft.json`, never `domains.json`.
- `run_guard.py`: one command for CI that re-measures, analyses and runs
  the guard set, so the guard checks the code in the pull request rather
  than stale artifacts.
- Baseline ratchet in `check_fitness.py` (`--update-baseline`,
  `fitness/baseline.json`): existing cycles become warnings, new or grown
  cycles fail F4.1, and the new check F4.4 fails on any component
  dependency not in the baseline.
- Cut candidates per cycle in `analyze_dependencies.py`: the lightest
  edges whose removal makes the group acyclic.
- `analyze_dependencies.py --extra-edges` and `dependencies.extra_edges` in
  `config.json` to merge database, runtime or hand-made edges; edge kinds
  are kept and shown in the report.
- Behaviour evals for `claude plugin eval` (`plugins/monolith-decomposition/evals/`):
  stopping at the gate, numbers from scripts, resuming, no unrequested
  refactors, no firing on unrelated tasks.
- Schemas for `change-coupling`, `data-coupling`, `domain-suggestions` and
  `baseline`.
- The worked example now runs through all phases (0–6) with eight RFCs, a
  domain map, a service map, a baseline and a passing guard.

### Changed

- `state.py` enforces the gates: `start` requires the previous phase
  approved (and refuses phases 1–6 under tactical forking), `review`
  requires the phase in progress, `approve` requires every attached RFC to
  be Accepted and, for phases 1–6, a passing fitness run newer than the
  phase start. `--force --reason` overrides and is recorded in the history.
- Python imports are parsed with the standard library `ast` module, with
  a regex fallback for files the interpreter cannot parse.
- Other languages: comments are stripped before scanning (string-aware,
  so `"http://..."` survives); C/C++ `#include` is resolved once (relative
  first, then source roots) instead of being counted twice.
- `SKILL.md` uses `${CLAUDE_SKILL_DIR}` for script paths; the description
  leads with the trigger phrases.
- Phase 0, 4, 5 and 6 guides, the fitness-function guide and the
  workspace reference cover the new scripts, the baseline and `run_guard.py`;
  the CI example uses the same action versions as this repository.

### Fixed

- Parenthesised multi-line Python imports (`from x import (\n a,\n b)`,
  the black/isort style) produced no edge at all.
- `import x  # comment` was ignored.
- Imports inside docstrings, `//` and `/* */` comments, Ruby `=begin`
  blocks and PHP `#` comments were counted as dependencies.

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

