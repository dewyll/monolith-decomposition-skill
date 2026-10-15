# Other ecosystems

## Rust

- **Components**: modules (folders/files under `src/`), or crates in a
  Cargo workspace.
- **Dependencies**: the built-in extractor understands `use crate::`,
  `use super::` and `use self::` paths. `cargo-modules` can print the module
  dependency graph for a closer look.
- **Fitness**: the strongest boundary is a **workspace crate per domain**:
  Cargo forbids cycles between crates and a crate can only use what another
  crate declares `pub`. Until then, rely on the generic F4.1 and F5.4 checks.

## Elixir

- **Components**: modules grouped by namespace (`MyApp.Billing.*`), usually
  one folder per context in Phoenix.
- **Dependencies**: `mix xref graph` (DOT or plain output) gives
  compile-time and runtime references between files; map file pairs with
  `convert_edges.py --kind files`.
- **Fitness**: the **Boundary** library declares each boundary's
  dependencies and exports and reports violations at compile time:

  ```elixir
  defmodule MyApp.Reporting do
    use Boundary, deps: [MyApp.Ordering, MyApp.Customer], exports: []   # RFC-0011
  end
  ```

## C and C++

- **Components**: directories, or build targets (CMake libraries).
- **Dependencies**: the built-in extractor reads quoted `#include`s.
  For target-level edges, `cmake --graphviz=deps.dot` describes which
  targets link which.
- **Fitness**: one CMake library per domain with `PRIVATE`/`PUBLIC`
  dependencies makes the linker enforce boundaries; include-what-you-use
  keeps includes honest. Otherwise use the generic checks.

## Swift

- **Components**: Swift Package Manager targets or folders.
- **Fitness**: separate SwiftPM targets cannot import each other unless
  declared in `Package.swift`; that is the native boundary check.

## Anything else

- Size: `scc` or `tokei`.
- Dependencies: if the language has an import statement, add a pattern to
  `extract_dependencies.py` (and a test), or produce `from<TAB>to` pairs with
  any tool and use `convert_edges.py`.
- Fitness: `check_fitness.py --phase guard` in CI, plus whatever module or
  package boundary the build system enforces.

Contributions of a dedicated adapter are welcome.
