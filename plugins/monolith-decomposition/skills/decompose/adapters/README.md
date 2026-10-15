# Adapters

The workflow and every artifact are language-neutral. An adapter is the
small amount of ecosystem knowledge that plugs a codebase into it. Each
adapter answers the same five questions:

1. **What is a component here?** (package, namespace, module, folder, pack,
   crate...) and how to express that in `config.json`.
2. **How to size it**, if something better than the built-in line counter
   exists.
3. **How to extract dependencies** with a native tool, and how to turn its
   output into `from<TAB>to` pairs for `scripts/convert_edges.py`.
4. **Which fitness-function libraries** exist, with an example rule per
   phase (cycles, domain boundaries, residence/naming rules).
5. **Pitfalls**: where static analysis lies in this ecosystem.

| Adapter | Covers |
|---|---|
| [jvm.md](jvm.md) | Java, Kotlin, Scala, Groovy |
| [dotnet.md](dotnet.md) | C#, F#, VB.NET |
| [typescript.md](typescript.md) | TypeScript, JavaScript, Node.js, front-end apps |
| [python.md](python.md) | Python |
| [go.md](go.md) | Go |
| [php.md](php.md) | PHP |
| [ruby.md](ruby.md) | Ruby, Rails |
| [other.md](other.md) | Rust, Elixir, C/C++, Swift, anything else |

## Before recommending a tool

Tool health changes faster than these files. Before recommending a library,
check its latest release, recent activity, and support for the project's
language/framework version (search the web if you can). Write the choice and
the date checked into the RFC. The libraries listed here were reviewed in
October 2026.

## Universal fallbacks

When an ecosystem has no maintained tool, or the team cannot add one:

- **Size**: built-in logical-line counter, or `scc`/`tokei` (hundreds of languages).
- **Dependencies**: `scripts/extract_dependencies.py` (regex over imports,
  confidence "low"), enriched by hand with runtime and database edges.
- **Fitness**: `scripts/check_fitness.py --phase guard` in CI. Coarser than a
  native rule but it works everywhere.

## Contributing an adapter

Copy the structure of an existing file, keep examples minimal and runnable,
and add an extractor test to `tests/test_scripts.py` with a tiny fixture
project. See `CONTRIBUTING.md` at the repository root.
