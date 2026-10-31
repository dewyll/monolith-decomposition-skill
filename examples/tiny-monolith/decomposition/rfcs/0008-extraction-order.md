---
id: 0008
title: Extraction order
status: Accepted
phase: 6
date: 2026-10-31
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0008: Extraction order

## Context

Afferent coupling per domain ([domain coupling](../05-domains/domain-coupling.md)):
`payment` is called only by `reporting`; `reporting` only by the shell;
`customer` by ordering and reporting; `ordering` by the shell and reporting,
and it still contains the frozen cycle (RFC-0005) and the pending push-down
(RFC-0004).

## Decision drivers

- Start where few callers must change and value is clear.
- Each extraction is releasable on its own with the monolith still working.

## Options considered

### Option A — Ordering first (driver 1 is ranked first)

- Pros: earliest value for the top driver.
- Cons: largest domain, cycle and push-down still open; highest risk as the first move.

### Option B — Payment, reporting, customer, ordering (chosen)

- Pros: lowest afferent coupling first; the team learns the extraction path on small domains.
- Cons: driver 1 waits for the fourth step.

## Decision

We will extract in this order: **1. payment-service** (Ca 1, driver 2),
**2. reporting-service** (Ca 1, driver 3, needs the event feed),
**3. customer-service** (Ca 2, no outgoing edges), **4. ordering-service**.
Step 4 starts with the RFC-0004 push-down and the RFC-0005 cycle break,
then removes the allow-list entries and updates the baseline.

## Trade-offs and consequences

- Positive: risk grows with experience.
- Negative: pricing/inventory independence (driver 1) arrives last.
- Risks and how we will notice them: the order is skipped under pressure.
  `extraction_order` in services.json and this RFC are reviewed at each release.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| guard set (F1, F3, F4 incl. baseline, F5, F6) | `run_guard.py` | CI on every pull request |

## Evidence

- [06-services/services.json](../06-services/services.json)
- [04-dependencies/dependencies.md](../04-dependencies/dependencies.md)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-31
