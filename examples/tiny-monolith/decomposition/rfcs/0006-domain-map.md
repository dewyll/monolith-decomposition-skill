---
id: 0006
title: Domain map
status: Accepted
phase: 5
date: 2026-10-31
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0006: Domain map

## Context

`suggest_domains.py` clustered the import graph with the Phase 2 shared code
left out (modularity Q = 0.1, a weak structure: the codebase is
tiny and `reporting` touches almost everything)
([suggestions](../05-domains/domain-suggestions.md)):

| Suggested | Components | Cohesion |
|---|---|---:|
| `reporting` | `shopco`, `shopco.customers`, `shopco.payments`, `shopco.reporting` | 0.43 |
| `orders` | `shopco.inventory`, `shopco.orders`, `shopco.orders.pricing` | 0.43 |

The clustering puts `orders`, `pricing` and `inventory` together (they share
the only cycle), which matches how the team describes checkout. It glues
`customers` and `payments` to their heaviest neighbours, which does not
match the drivers: payments must release on its own (driver 2) and
customers is a separate capability. Cross-domain edges after the decision
([domain coupling](../05-domains/domain-coupling.md)):

| From | To | Weight |
|---|---|---:|
| `ordering` | `customer` | 1 |
| `ordering` | `platform` | 3 |
| `payment` | `platform` | 2 |
| `reporting` | `customer` | 1 |
| `reporting` | `ordering` | 2 |
| `reporting` | `payment` | 1 |
| `reporting` | `platform` | 1 |
| `shell` | `ordering` | 1 |
| `shell` | `reporting` | 1 |

## Decision drivers

- Driver 1: pricing and inventory deploy without the whole shop.
- Driver 2: payments releases on its own schedule.
- Driver 3: reporting must not slow down checkout.
- No cycle between domains.

## Options considered

### Option A — Take the clusters as they are

- Pros: maximal measured cohesion.
- Cons: payments would sit inside another domain, against driver 2.

### Option B — Six domains along the business capabilities (chosen)

- Pros: matches the drivers and team ownership; no cycle between domains.
- Cons: `ordering` stays the largest domain (48% of the code).

## Decision

We will use six domains: **ordering** (orders, pricing, inventory),
**customer**, **payment**, **reporting**, **platform** (the shared library
from RFC-0003) and **shell** (the entry point). The orders–inventory cycle
stays inside `ordering`. Forbidden dependencies: platform and customer
depend on no domain; ordering and payment never depend on reporting;
payment never depends on ordering.

## Trade-offs and consequences

- Positive: every boundary maps to a driver or a team; domain graph is acyclic.
- Negative: `ordering` is large; it may split later along `pricing`.
- Risks and how we will notice them: new cross-domain calls. F5.4 fails on
  the forbidden ones, F4.4 on any other new component edge.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| F5.1, F5.2 every component in exactly one domain | `check_fitness.py --phase 5` | CI guard |
| F5.4 forbidden domain dependencies | `fitness.forbidden_dependencies` | CI guard |
| domain independence | import-linter `independence` / `layers` contracts | test suite |

## Evidence

- [05-domains/domain-suggestions.md](../05-domains/domain-suggestions.md)
- [05-domains/domains.json](../05-domains/domains.json)
- [05-domains/domain-coupling.md](../05-domains/domain-coupling.md)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-31
