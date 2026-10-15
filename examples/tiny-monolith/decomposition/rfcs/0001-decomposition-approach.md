---
id: 0001
title: Decomposition approach
status: Accepted
phase: 0
date: 2026-10-15
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0001: Decomposition approach

## Context

The shop is a single Python package of 87 logical lines across 10
components ([assessment](../00-assessment/assessment.md)). Folders already
follow business areas. One dependency cycle (`orders` ↔ `inventory`) and
two parent namespaces holding code are the main structural problems.

## Decision drivers

- Independent deployment of pricing/inventory (driver 1).
- Payments team autonomy (driver 2).
- Reporting load isolated from checkout (driver 3).

## Options considered

### Option A — Component-based decomposition

- Pros: builds on the existing folder structure; every step is measurable
  and reversible; no duplicated code.
- Cons: slower start; each refactor needs the (thin) test suite.

### Option B — Tactical forking

- Pros: three teams could start immediately.
- Cons: audit and notification copied into every fork; there is only one
  team, so the parallelism buys nothing.

## Decision

We will use component-based decomposition, following phases 1–6.

## Trade-offs and consequences

- Positive: shared concerns are consolidated once instead of copied.
- Negative: the first service ships later than it would with forking.
- Risks: refactors with low test coverage. We will add characterisation
  tests before each move outside `orders`.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| Phase checks F1–F6 as each phase is approved | `check_fitness.py` | CI from Phase 5 on (`--phase guard`) |

## Evidence

- [00-assessment/assessment.md](../00-assessment/assessment.md)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-15
