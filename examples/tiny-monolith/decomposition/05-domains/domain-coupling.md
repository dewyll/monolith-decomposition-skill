# Domain coupling

Generated 2026-10-31T18:30:34+00:00 from `extract_dependencies.py` (confidence: **low**).

- Nodes: **6** · edges: **9** · density: 0.3
- Mean efferent coupling: 1.5 (σ 1.38)
- Cycles: **0** involving 0 node(s) (0%)
- Coupling level (heuristic): **high**

> Edges come from static import scanning. Dependency injection, events, reflection and shared tables are not visible, so real coupling is likely higher.

## Most coupled

| Node | Ca (in) | Ce (out) | Instability | In cycle |
|---|---:|---:|---:|---|
| `reporting` | 1 | 4 | 0.8 |  |
| `ordering` | 2 | 2 | 0.5 |  |
| `platform` | 3 | 0 | 0.0 |  |
| `customer` | 2 | 0 | 0.0 |  |
| `payment` | 1 | 1 | 0.5 |  |
| `shell` | 0 | 2 | 1.0 |  |

## Dependency matrix

Rows depend on columns; numbers are the count of referencing files.

| | C1 | C2 | C3 | C4 | C5 | C6 |
|---|---:|---:|---:|---:|---:|---:|
| **C1** | · |  |  |  |  |  |
| **C2** | 1 | · |  | 3 |  |  |
| **C3** |  |  | · | 2 |  |  |
| **C4** |  |  |  | · |  |  |
| **C5** | 1 | 2 | 1 | 1 | · |  |
| **C6** |  | 1 |  |  | 1 | · |

Legend: C1 = `customer` · C2 = `ordering` · C3 = `payment` · C4 = `platform` · C5 = `reporting` · C6 = `shell`

## Cohesion

Share of each domain's references that stay inside it.

| Domain | Cohesion |
|---|---:|
| `customer` |  |
| `ordering` | 0.43 |
| `payment` | 0.0 |
| `platform` |  |
| `reporting` | 0.0 |
| `shell` | 0.0 |
