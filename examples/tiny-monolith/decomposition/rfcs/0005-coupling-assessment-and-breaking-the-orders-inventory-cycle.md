---
id: 0005
title: Coupling assessment and breaking the orders-inventory cycle
status: Accepted
phase: 4
date: 2026-10-31
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0005: Coupling assessment and breaking the orders-inventory cycle

## Context

`analyze_dependencies.py` on the regex import scan (confidence **low**,
[report](../04-dependencies/dependencies.md)):

| Metric | Value |
|---|---|
| Components / edges | 10 / 16 |
| Density | 0.178 |
| Cycles | 1 (`shopco.inventory` ↔ `shopco.orders`) |
| Coupling level hint | medium |
| Highest Ce | `shopco.reporting`, 5 (orders, inventory, customers, payments, audit) |

The cycle exists because `inventory.pending_demand()` calls
`orders.service.open_orders_for()`. The analyser's cheapest cut is
`shopco.inventory` → `shopco.orders` (weight 1): one function in one file.

Hidden coupling checked with the team: no DI container, no events, no
reflection. The **single shared database** (Phase 0 constraint) couples
everything; the example code keeps state in module globals, so
`find_data_coupling.py` has nothing to find here. `reporting` reads
`ORDERS`, `STOCK` and `CUSTOMERS` directly, which in the real system are
tables.

## Decision drivers

- Driver 1 needs orders and inventory to deploy without each other eventually.
- Driver 3 needs reporting off the checkout path.
- Low coupling overall: feasible to continue component-based (RFC-0001).

## Options considered

### Option A — Invert: orders pushes demand to inventory (event `order.placed` / `order.cancelled`)

- Pros: removes the cut edge; inventory keeps its own demand counter.
- Cons: eventual consistency for `pending_demand`.

### Option B — Move `open_orders_for` into inventory

- Pros: no new mechanism.
- Cons: inventory would read order data it does not own.

### Option C — Merge orders and inventory

- Pros: no cycle by definition.
- Cons: works against driver 1.

## Decision

We will continue with component-based decomposition and break the cycle
with Option A, replacing the `shopco.inventory` → `shopco.orders` call by
order events. Until that refactor lands, the cycle is frozen in the
[baseline](../fitness/baseline.json): it may not grow, and no new
component dependency may appear (F4.4). `reporting` keeps its outgoing
edges for now; Phase 6 turns them into read-only interfaces.

## Trade-offs and consequences

- Positive: the guard can run in CI today, green, and still fail on anything new.
- Negative: `pending_demand` becomes eventually consistent.
- Risks and how we will notice them: the cycle stays forever. F4.1 reports
  it as a warning on every run until it is gone; then `--update-baseline`
  locks the improvement in.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| F4.1 no cycles beyond the baseline | `check_fitness.py --phase 4` / `run_guard.py` | CI guard |
| F4.4 no new component dependency | baseline ratchet | CI guard |
| inventory must not import orders (after the refactor) | import-linter `forbidden` contract | test suite |

## Evidence

- [04-dependencies/dependencies.md](../04-dependencies/dependencies.md)
- [04-dependencies/edges.json](../04-dependencies/edges.json)
- [fitness/baseline.json](../fitness/baseline.json)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-31
