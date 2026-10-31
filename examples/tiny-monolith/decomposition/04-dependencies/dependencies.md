# Component dependencies

Generated 2026-10-31T18:30:34+00:00 from `extract_dependencies.py` (confidence: **low**).

- Nodes: **10** · edges: **16** · density: 0.178
- Mean efferent coupling: 1.6 (σ 1.91)
- Cycles: **1** involving 2 node(s) (20%)
- Coupling level (heuristic): **medium**

> Edges come from static import scanning. Dependency injection, events, reflection and shared tables are not visible, so real coupling is likely higher.

## Most coupled

| Node | Ca (in) | Ce (out) | Instability | In cycle |
|---|---:|---:|---:|---|
| `shopco.orders` | 3 | 5 | 0.62 | yes |
| `shopco.reporting` | 1 | 5 | 0.83 |  |
| `shopco.audit` | 4 | 0 | 0.0 |  |
| `shopco.inventory` | 2 | 2 | 0.5 | yes |
| `shopco.payments` | 1 | 2 | 0.67 |  |
| `shopco` | 0 | 2 | 1.0 |  |
| `shopco.customers` | 2 | 0 | 0.0 |  |
| `shopco.notification` | 2 | 0 | 0.0 |  |
| `shopco.orders.pricing` | 1 | 0 | 0.0 |  |
| `shopco.orders.notification` | 0 | 0 |  |  |

## Cycles

1. `shopco.inventory`, `shopco.orders`
   - cheapest cut (lightest edges that make this group acyclic): `shopco.inventory` → `shopco.orders` (weight 1)

## Dependency matrix

Rows depend on columns; numbers are the count of referencing files.

| | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | C9 | C10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **C1** | · |  |  |  |  | 1 |  |  |  | 1 |
| **C2** |  | · |  |  |  |  |  |  |  |  |
| **C3** |  |  | · |  |  |  |  |  |  |  |
| **C4** |  | 1 |  | · |  | 1 |  |  |  |  |
| **C5** |  |  |  |  | · |  |  |  |  |  |
| **C6** |  | 1 | 1 | 1 | 1 | · |  | 1 |  |  |
| **C7** |  |  |  |  |  |  | · |  |  |  |
| **C8** |  |  |  |  |  |  |  | · |  |  |
| **C9** |  | 1 |  |  | 1 |  |  |  | · |  |
| **C10** |  | 1 | 1 | 1 |  | 1 |  |  | 1 | · |

Legend: C1 = `shopco` · C2 = `shopco.audit` · C3 = `shopco.customers` · C4 = `shopco.inventory` · C5 = `shopco.notification` · C6 = `shopco.orders` · C7 = `shopco.orders.notification` · C8 = `shopco.orders.pricing` · C9 = `shopco.payments` · C10 = `shopco.reporting`
