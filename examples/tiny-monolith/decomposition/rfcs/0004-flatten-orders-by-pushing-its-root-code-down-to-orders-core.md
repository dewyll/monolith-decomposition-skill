---
id: 0004
title: Flatten orders by pushing its root code down to orders.core
status: Accepted
phase: 3
date: 2026-10-31
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0004: Flatten orders by pushing its root code down to orders.core

## Context

Phase 1 flagged two root namespaces with code ([inventory](../01-sizing/components.md)):

| Component | Orphan files | Children |
|---|---|---|
| `shopco` | `shopco/__init__.py`, `shopco/app.py` | every other component |
| `shopco.orders` | `shopco/orders/__init__.py`, `shopco/orders/service.py` | `shopco.orders.pricing`, `shopco.orders.notification` |

`shopco/orders/service.py` holds placing, cancelling and querying orders: a
coherent piece of its own, used by `shopco` (entry point), `inventory` and
`reporting`. `shopco.orders.notification` disappears with RFC-0003.

## Decision drivers

- Driver 1 (deploy pricing without the whole shop) needs `orders.pricing` to
  stay a separate leaf.
- The team prefers moving code once, when ordering-service is extracted,
  over two refactors of the same files.

## Options considered

### Option A — Push down `service.py` into `shopco.orders.core`

- Pros: `orders.pricing` stays independent; the orphan becomes a definite component.
- Cons: every import of `shopco.orders.service` changes (3 call sites).

### Option B — Pull up: merge `orders.pricing` into `orders`

- Pros: no file moves.
- Cons: makes the largest component larger and works against driver 1.

### Option C — Distribute `service.py` into the children

- Pros: none here; the functions belong to neither child.
- Cons: scatters one responsibility.

## Decision

We will push `shopco/orders/service.py` down into `shopco.orders.core`
(Option A), as the first commit of the ordering-service extraction, and
keep the application entry point in the root `shopco` namespace. Until the
move lands, both are in `fitness.orphan_allowlist`, each entry naming this
RFC and when it goes away. The plan is in [plan.json](../03-flattening/plan.json).

## Trade-offs and consequences

- Positive: one move instead of two; pricing remains its own leaf.
- Negative: the size and orphan allow-lists stay populated a while longer.
- Risks and how we will notice them: the move never happens. The Phase 6
  extraction order makes it step 1 of ordering-service, and the allow-list
  entries are listed in every guard run.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| F3.1 no root namespace with code except allow-listed | `check_fitness.py --phase 3` | CI guard |
| no module directly in `shopco/orders/` once moved | import-linter / pytest-archon rule (Python adapter) | test suite |

## Evidence

- [01-sizing/components.json](../01-sizing/components.json) (`orphan_file_paths`)
- [03-flattening/plan.json](../03-flattening/plan.json)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-31
