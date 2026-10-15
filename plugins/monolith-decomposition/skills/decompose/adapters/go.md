# Go adapter

## Components

A component is a **package** (a folder). `init_workspace.py` reads the
module path from `go.mod` and uses it as the namespace prefix, so import
paths resolve to components:

```json
"source_roots": [{"path": ".", "namespace_prefix": "github.com/acme/shop"}]
```

Most monoliths keep business code under `internal/`; `cmd/` holds entry
points (usually small, often allow-listed in Phase 1).

## Size

`scc` or the built-in counter. `*_test.go` is excluded by default.

## Dependencies

The toolchain gives exact package imports:

```bash
go list -f '{{$p := .ImportPath}}{{range .Imports}}{{$p}}{{"\t"}}{{.}}{{"\n"}}{{end}}' ./... \
  | python3 "$SKILL_DIR/scripts/convert_edges.py" --workspace decomposition \
      --kind namespaces --tool "go list" -
```

Standard library and third-party imports map to no component and are
dropped. Interfaces satisfied implicitly mean the code depends on an
interface while the runtime wires a concrete type from another package:
check `main` / the wiring package.

## Fitness functions

| Mechanism | Notes |
|---|---|
| **The compiler** | Import cycles between packages do not compile. Phase 4 cycles cannot exist at package level. |
| **`internal/` directories** | A package under `x/internal/` can only be imported from within `x/`. Moving a domain's private packages under its own `internal/` is a compiler-enforced boundary. |
| **go-arch-lint** | Declares components and which may depend on which (`.go-arch-lint.yml`). |
| **depguard** (golangci-lint) | Deny lists per file glob. |

go-arch-lint, Phase 5:

```yaml
version: 3
workdir: internal
components:
  ordering:  { in: ordering/** }
  customer:  { in: customer/** }
  reporting: { in: reporting/** }
deps:
  ordering:
    mayDependOn: [customer]
  reporting:
    mayDependOn: [ordering, customer]
```

depguard through golangci-lint (v2 config format):

```yaml
version: "2"
linters:
  enable: [depguard]
  settings:
    depguard:
      rules:
        ordering-not-reporting:      # RFC-0011
          files: ["**/internal/ordering/**"]
          deny:
            - pkg: "github.com/acme/shop/internal/reporting"
              desc: "RFC-0011: reporting depends on ordering, never the reverse"
```

## Pitfalls

- Package-level cycles are impossible, but **domain-level** cycles are not:
  `ordering/a` → `customer/b` → `ordering/c` compiles fine. The generic
  F4.1 on domain-coupling and go-arch-lint catch it.
- Large shared `models`/`types` packages are a common hidden hub; they show
  up with very high Ca in Phase 4.
