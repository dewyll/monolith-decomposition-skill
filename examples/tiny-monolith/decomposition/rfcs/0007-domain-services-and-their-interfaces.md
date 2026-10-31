---
id: 0007
title: Domain services and their interfaces
status: Accepted
phase: 6
date: 2026-10-31
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0007: Domain services and their interfaces

## Context

Six domains from RFC-0006 and nine cross-domain edges
([domain coupling](../05-domains/domain-coupling.md)). Every edge that
crosses a service boundary needs a declared interface and a style.
Open question from Phase 0, now answered by the team: `reporting` only
reads `charge.__name__`; it never charges anyone.

## Decision drivers

- Drivers 1–3 from Phase 0.
- Fewest synchronous calls on the checkout path.
- The shared database stays until data decomposition (out of scope here).

## Options considered

### Option A — One service per domain, shared code as a library (chosen)

- Pros: deployable units follow the drivers; no shared runtime service.
- Cons: platform library versions must be managed.

### Option B — Merge customer into ordering

- Pros: one sync call fewer.
- Cons: reporting would then depend on ordering for customer data.

## Decision

We will create four domain services (payment, reporting, customer,
ordering), a **platform library** for audit and notification (RFC-0003) and
keep the entry point as the **shop shell**, which routes calls to services
as they are extracted. Reporting consumes order and payment **events**
instead of reading their data (driver 3); the only synchronous calls are
shell → ordering/reporting, ordering → customer and reporting → customer.
Every cross-service edge is declared in
[services.json](../06-services/services.json).

## Trade-offs and consequences

- Positive: checkout depends on one synchronous call (customer).
- Negative: reports become eventually consistent; an event pipeline is needed.
- Risks and how we will notice them: undeclared calls between services.
  F6.2 fails on them; contract tests guard the declared ones.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| F6.1 every domain in one service | `check_fitness.py --phase 6` | CI guard |
| F6.2 cross-service dependencies declared | `check_fitness.py --phase 6` | CI guard |
| consumer-driven contracts for sync/async interfaces | Pact (after the first extraction) | CI |

## Evidence

- [06-services/services.json](../06-services/services.json)
- [05-domains/domain-coupling.md](../05-domains/domain-coupling.md)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-31
