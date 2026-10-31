# Domain suggestions

Generated 2026-10-31T18:30:34+00:00 by Louvain clustering over imports (co-change weight 0.0). Modularity **Q = 0.1** (weak structure: treat the clusters with care).

> A starting point for the conversation, not a domain map. Rename, merge and split with the people who know the business, then write domains.json.

| Suggested id | Components | Size % | Cohesion |
|---|---|---:|---:|
| `reporting` | `shopco`, `shopco.customers`, `shopco.payments`, `shopco.reporting` | 36.77 | 0.43 |
| `orders` | `shopco.inventory`, `shopco.orders`, `shopco.orders.pricing` | 48.28 | 0.43 |

**Left out as shared code** (Phase 2 decisions or --exclude): `shopco.audit`, `shopco.notification`, `shopco.orders.notification`. Give them a shared domain or assign each to its main user.
