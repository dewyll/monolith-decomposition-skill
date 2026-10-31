# Phase 2 — Gather common domain components

Iteration 1 · 2026-10-31

## Summary

Five candidates, two of them real shared concerns. `notification` exists
twice and one copy is dead code; `audit` is used by four components.
Both become a versioned platform library. `orders` and `reporting` were
flagged by fan-in and keyword only and stay business domains.

## Key numbers

| Metric | Value |
|---|---|
| Candidates | 5 |
| Duplicate groups | 1 (`notification`) |
| Highest fan-in among shared concerns | `shopco.audit`, 4 components |
| Dead duplicate | `shopco.orders.notification` (Ca = 0) |

## Proposed decisions

| # | Proposal | RFC |
|---|---|---|
| 1 | Consolidate notification + audit into a platform library; delete the dead copy | [0003](../rfcs/0003-common-domain-consolidate-notification-and-audit.md) |

## Fitness functions added in this phase

| Check | Status | Notes |
|---|---|---|
| F2.1 | PASS | all five candidates decided in `common-domain.json` |

## Artifacts

- [candidates.md](candidates.md), [common-domain.json](common-domain.json)
