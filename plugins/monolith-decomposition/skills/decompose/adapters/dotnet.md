# .NET adapter — C#, F#, VB.NET

## Components

A component is a **namespace** (`Acme.Billing`), sometimes an **assembly**
(project). Folders usually drop the root namespace, so set it as a prefix:

```json
"source_roots": [{"path": "src/Acme.Web", "namespace_prefix": "Acme.Web"}]
```

For solutions with one project per area, the `explicit` strategy with one
component per project (`"paths": ["src/Acme.Billing/**"]`) is often clearer.
Exclude `obj/`, `bin/`, `*.Designer.cs`, `*.g.cs` and migrations.

## Size

`scc` or the built-in counter. Visual Studio code metrics or other analysis
tools can export per-namespace numbers for `--from-json`.

## Dependencies

`using` directives are a weak signal in .NET: implicit and global usings
hide real ones, and a `using` does not mean a type is used. Prefer reading
type-level dependencies from the compiled assemblies. With ArchUnitNET a
throwaway test can print namespace pairs:

```csharp
// Adjust to the current ArchUnitNET API if names changed.
var architecture = new ArchLoader().LoadAssemblies(typeof(Program).Assembly).Build();
foreach (var type in architecture.Types)
    foreach (var dep in type.Dependencies)
        if (dep.Target.Namespace.FullName.StartsWith("Acme"))
            Console.WriteLine($"{type.Namespace.FullName}\t{dep.Target.Namespace.FullName}");
```

Pipe that output into
`convert_edges.py --kind namespaces --tool archunitnet -`. Without it, the
built-in extractor's `using`-based edges are a usable lower bound.

## Fitness functions

| Library | Notes |
|---|---|
| **NetArchTest** (and the community "eNhancedEdition" fork) | Fluent rules in any test framework. |
| **ArchUnitNET** | Port of ArchUnit, including cycle checks. |
| Project references | Separate projects cannot reference each other unless declared; the compiler enforces it. |

NetArchTest, Phase 5:

```csharp
[Fact] // RFC-0011
public void Ordering_does_not_depend_on_reporting()
{
    var result = Types.InAssembly(typeof(Program).Assembly)
        .That().ResideInNamespace("Acme.Ordering")
        .ShouldNot().HaveDependencyOn("Acme.Reporting")
        .GetResult();

    Assert.True(result.IsSuccessful, "RFC-0011: reporting depends on ordering, never the reverse");
}
```

Moving each domain into its own project is the strongest boundary .NET
offers; suggest it in Phase 5 or 6 when the team is ready.

## Pitfalls

- Partial classes spread one type across folders.
- MediatR/handlers and DI registration hide who calls whom.
- EF Core `DbContext` shared by every area is one big data coupling; list
  the entity sets each component touches in Phase 4.
