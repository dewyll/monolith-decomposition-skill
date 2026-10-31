# Python adapter

## Components

A component is a **package** (a folder of modules, `acme/billing`). The
source root is the folder that contains the top-level package: `.` for a
flat layout, `src` for a src layout. Django apps map naturally to
components; set `max_depth` so `migrations/`, `templatetags/` and similar
stay inside their app (and keep `**/migrations/**` excluded).

## Size

`scc` or the built-in counter (docstrings count as code with the built-in
counter; scc treats them the same way).

## Dependencies

The built-in scanner parses Python files with the standard library `ast`
module, so multi-line imports, imports inside functions and
`if TYPE_CHECKING:` blocks are all seen and docstrings are ignored. Files
the running interpreter cannot parse (Python 2, newer syntax) fall back to
the regex scanner. It still cannot see `importlib`, plugins loaded by
entry points or Django's string references (`"app.Model"`, `INSTALLED_APPS`).

**grimp** (the engine behind import-linter) builds the import graph from the
installed package:

```bash
pip install grimp
python3 - <<'PY' | python3 "$SKILL_DIR/scripts/convert_edges.py" --workspace decomposition \
    --kind namespaces --tool grimp -
import grimp
graph = grimp.build_graph("acme")          # your top-level package
for module in graph.modules:
    for imported in graph.find_modules_directly_imported_by(module):
        print(f"{module}\t{imported}")
PY
```

Imports inside functions are included; `importlib.import_module("...")`,
plugin entry points and signal receivers are not.

## Fitness functions

| Library | Notes |
|---|---|
| **import-linter** | Contracts: `forbidden`, `independence`, `layers`. CLI `lint-imports`. |
| **Tach** | Module boundaries and public interfaces, written in Rust, fast on big codebases. |
| **pytest-archon** | ArchUnit-style rules inside pytest. |

import-linter, Phase 5 (`.importlinter`):

```ini
[importlinter]
root_package = acme

[importlinter:contract:domains-independent]
name = Domains are independent (RFC-0009)
type = independence
modules =
    acme.ordering
    acme.customer
    acme.payment

[importlinter:contract:ordering-not-reporting]
name = Ordering must not import reporting (RFC-0011)
type = forbidden
source_modules =
    acme.ordering
forbidden_modules =
    acme.reporting
```

`independence` contracts also rule out cycles between the listed packages.
For a general cycle check use the generic F4.1 in CI, or Tach's option to
forbid circular dependencies between modules (see its docs for the current
setting name).

## Pitfalls

- `__init__.py` files that import their children make the parent depend on
  everything below it; reading them explains a lot of root-with-code flags.
- Django: models referenced by string (`"billing.Invoice"`) in foreign keys
  and signals are invisible to import scanners but are real coupling.
- Celery tasks called by name are runtime edges.
