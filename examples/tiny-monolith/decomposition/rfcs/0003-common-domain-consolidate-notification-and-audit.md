---
id: 0003
title: Common domain: consolidate notification and audit
status: Accepted
phase: 2
date: 2026-10-31
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0003: Common domain: consolidate notification and audit

## Context

`find_common_candidates.py` flagged five candidates ([candidates](../02-common-domain/candidates.md)):

| Component | Signals | Share |
|---|---|---:|
| `shopco.audit` | fan-in (4 components), keyword | 5.75% |
| `shopco.notification` | duplicate, keyword | 4.6% |
| `shopco.orders.notification` | duplicate, keyword | 4.6% |
| `shopco.orders` | fan-in (3 components) | 29.89% |
| `shopco.reporting` | keyword | 11.49% |

`shopco.orders.notification` has Ca = 0 and Ce = 0 in the Phase 0 probe:
nothing imports it, so it is a dead copy of `shopco.notification`.

## Decision drivers

- Driver 2 (payments releases on its own) means shared code must not force
  coordinated deployments.
- Notification and audit have no business rules of their own; they change
  rarely and in the same way for every caller.

## Options considered

### Option A — Platform library (audit + notification), versioned

- Pros: no network hop, no new service to run; one place to fix bugs.
- Cons: a breaking change needs every service to bump the version.

### Option B — Shared notification/audit service

- Pros: deploys independently from its callers.
- Cons: a new runtime dependency on the checkout path; too much for 10 lines of code.

### Option C — Duplicate into each service later

- Pros: no coupling at all.
- Cons: audit records must look the same everywhere; duplicates would drift.

## Decision

We will consolidate `shopco.orders.notification` into `shopco.notification`
(deleting the dead copy) and treat `shopco.notification` and `shopco.audit`
as one shared **platform library** (Option A). `shopco.orders` and
`shopco.reporting` are not common: they are business domains.

## Trade-offs and consequences

- Positive: one implementation of each concern; the duplicate disappears.
- Negative: library changes need a version bump in every service.
- Risks and how we will notice them: business logic creeping into the
  library; the Phase 5 rule "platform depends on no domain" catches it.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| F2.1 every candidate has a decision | `check_fitness.py --phase 2` | locally, at the gate |
| platform depends on no domain | F5.4 (`forbidden_dependencies`), added in Phase 5 | CI guard |

## Evidence

- [02-common-domain/candidates.md](../02-common-domain/candidates.md)
- [02-common-domain/common-domain.json](../02-common-domain/common-domain.json)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-31
