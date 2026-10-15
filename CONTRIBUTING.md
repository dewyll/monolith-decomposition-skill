# Contributing

Thanks for helping make monolith decomposition less of a guessing game.

## Ways to help

- **Adapters**: improve an ecosystem guide or add a new one (Elixir, Rust,
  Kotlin Multiplatform, Dart, Scala-specific tooling...).
- **Extractors**: better import patterns in `extract_dependencies.py`, or
  converters for native tools.
- **Field reports**: ran the skill on a real monolith? Open an issue with
  what worked, what was confusing, and which numbers misled you (no
  proprietary code needed).
- **Docs**: clearer phase guides, better examples, translations of the README.

## Ground rules

- The scripts stay **Python 3.9+ standard library only**, so the skill runs
  anywhere without installing anything.
- Every artifact change updates its schema in `schemas/` and keeps
  `schema_version` compatible, or bumps it with a migration note.
- New extractor behaviour comes with a test in `tests/test_scripts.py`
  using a tiny fixture project.
- Phase guides describe the process in our own words. Do not paste text
  from the books; cite them instead.
- Keep `SKILL.md` short. Detail belongs in `references/` and `adapters/`,
  which the agent reads only when needed.

## Development

```bash
python3 -m unittest discover -s tests -v           # run the tests
pip install jsonschema                               # optional: also validates artifacts against schemas
claude plugin validate .                             # check the plugin manifests
```

To try local changes in Claude Code:

```bash
claude plugin marketplace add ./
claude plugin install monolith-decomposition@dewyll-skills
```

## Pull requests

- One topic per pull request, with a short description of the why.
- `main` is protected: pull requests need a passing CI run and an approval
  from the maintainer.
- By contributing you agree that your contribution is licensed under the
  MIT License of this repository.
