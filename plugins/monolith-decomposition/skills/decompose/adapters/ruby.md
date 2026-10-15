# Ruby / Rails adapter

## Components

Plain Ruby gems and libraries: a component is a folder under `lib/`
(`lib/billing`), and `require`/`require_relative` show dependencies.

Rails: autoloading (Zeitwerk) means files reference constants without any
`require`, and the default layout groups by type (`app/models`,
`app/controllers`). Two ways to get meaningful components:

- **Packs** (Packwerk): the codebase is split into `packs/<name>` folders,
  each with a `package.yml`. Use the `explicit` strategy with one component
  per pack: `{"name": "billing", "paths": ["packs/billing/**"]}`.
- **Explicit mapping** of the type folders by naming convention
  (`app/models/billing/**`, `app/controllers/billing/**`) when there are
  no packs yet. Proposing packs is a natural Phase 1/3 outcome.

## Size

`scc` or the built-in counter. Exclude `db/`, `vendor/`, `tmp/`, `spec/`, `test/`.

## Dependencies

The built-in extractor only sees `require` calls, which is nearly nothing
in a Rails app. Packwerk resolves constant references properly. A useful
trick to obtain the full pack-to-pack graph: enable `enforce_dependencies:
true` in every `package.yml` with empty `dependencies`, run
`bin/packwerk update-todo`, and read the generated `package_todo.yml`
files. Each lists, per pack, which other packs it references. Write them
as `04-dependencies/edges.json` with pack names as component ids
(`{"generator": {"tool": "packwerk", "confidence": "high"}, "edges": [{"from": "billing", "to": "ordering", "weight": 1}]}`)
and run `analyze_dependencies.py`. Then restore the real configuration.

## Fitness functions

| Library | Notes |
|---|---|
| **Packwerk** | Dependency checks between packs, with `package_todo.yml` as the baseline of known violations. |
| **packwerk-extensions** | Privacy (public API) and other checkers, extracted from Packwerk. |
| **Rubocop custom cops** | Naming/residence rules when packs are not adopted. |

Packwerk, Phase 5 (`packs/reporting/package.yml`):

```yaml
enforce_dependencies: true
dependencies:          # RFC-0011: reporting may read ordering and customer
  - packs/ordering
  - packs/customer
```

`packs/ordering/package.yml` sets `enforce_dependencies: true` with no
dependency on `packs/reporting`, so a reference from ordering to reporting
fails `bin/packwerk check` in CI.

## Pitfalls

- ActiveRecord associations and callbacks across packs are coupling through
  the database.
- `ActiveSupport::Notifications`, ActiveJob jobs enqueued by class name and
  `constantize` calls are runtime edges.
- Concerns mixed into models from other areas blur ownership; list them in
  Phase 2 as common candidates.
