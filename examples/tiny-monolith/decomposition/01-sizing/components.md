# Component inventory

Generated 2026-10-15T11:00:13+00:00 by `size_components.py` (metric: logical-lines, confidence: high).

- Components: **10**
- Files: **20**
- Total size: **87**
- Mean size: 8.7 · standard deviation: 6.33
- Outlier rule: |z| > 1.0; max share per component: 15.0%
- Unassigned files: 0

| Component | Files | Size | % of total | z | Flags |
|---|---:|---:|---:|---:|---|
| `shopco.orders` | 2 | 26 | 29.89 | 2.74 | large, over-max, root-with-code |
| `shopco.inventory` | 2 | 11 | 12.64 | 0.36 |  |
| `shopco.reporting` | 2 | 10 | 11.49 | 0.21 |  |
| `shopco` | 2 | 9 | 10.34 | 0.05 | root-with-code |
| `shopco.payments` | 2 | 9 | 10.34 | 0.05 |  |
| `shopco.audit` | 2 | 5 | 5.75 | -0.58 |  |
| `shopco.orders.pricing` | 2 | 5 | 5.75 | -0.58 |  |
| `shopco.customers` | 2 | 4 | 4.6 | -0.74 |  |
| `shopco.notification` | 2 | 4 | 4.6 | -0.74 |  |
| `shopco.orders.notification` | 2 | 4 | 4.6 | -0.74 |  |

## Root namespaces with code (Phase 3 input)

- `shopco.orders`: 2 orphaned file(s); sub-components: `shopco.orders.notification`, `shopco.orders.pricing`
- `shopco`: 2 orphaned file(s); sub-components: `shopco.audit`, `shopco.customers`, `shopco.inventory`, `shopco.notification`, `shopco.orders`, `shopco.orders.notification`, `shopco.orders.pricing`, `shopco.payments`, `shopco.reporting`
