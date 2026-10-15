# PHP adapter

## Components

A component is a **namespace** (`App\Billing`). `init_workspace.py` reads
`composer.json` PSR-4 autoload entries and sets source roots and namespace
prefixes from them, so `use App\Billing\Invoice;` resolves to the `Billing`
component.

Laravel apps often group by technical type (`app/Http/Controllers`,
`app/Models`). Then the folder tree does not show the domains; use the
`explicit` strategy or treat Phase 1 as the moment to propose
domain-oriented folders.

## Size

`scc` or the built-in counter. Exclude `vendor/`, `storage/`, `bootstrap/cache`.

## Dependencies

`use` statements are explicit in modern PHP, so the built-in extractor is a
reasonable start. It misses fully-qualified names written inline
(`new \App\Billing\Invoice()`), facades and container lookups by string.
For per-package coupling metrics (Ca, Ce, instability), PDepend's summary
report gives a second opinion.

## Fitness functions

| Library | Notes |
|---|---|
| **Deptrac** | Layers defined by collectors (directory, namespace, class name) and an allowed ruleset. Supports a baseline. |
| **PHPat** | Architecture rules as a PHPStan extension. |
| **PHPArkitect** | ArchUnit-style rules with a CLI. |

Deptrac, Phase 5 (`deptrac.yaml`):

```yaml
deptrac:
  paths: ["./src"]
  layers:
    - name: Ordering
      collectors: [{ type: directory, value: src/Ordering/.* }]
    - name: Customer
      collectors: [{ type: directory, value: src/Customer/.* }]
    - name: Reporting
      collectors: [{ type: directory, value: src/Reporting/.* }]
  ruleset:
    Ordering: [Customer]          # RFC-0009
    Customer: ~
    Reporting: [Ordering, Customer]
```

Run `vendor/bin/deptrac analyse --config-file=deptrac.yaml` in CI.

PHPat (verify the current API in its docs):

```php
final class ArchitectureTest
{
    public function test_ordering_does_not_depend_on_reporting(): Rule  // RFC-0011
    {
        return PHPat::rule()
            ->classes(Selector::inNamespace('App\Ordering'))
            ->shouldNotDependOn()
            ->classes(Selector::inNamespace('App\Reporting'));
    }
}
```

## Pitfalls

- Laravel facades, `app('service')` and container bindings hide real edges.
- Eloquent relations (`hasMany(Invoice::class)`) are coupling through the
  database as well as code.
- Event listeners registered in service providers are runtime edges.
