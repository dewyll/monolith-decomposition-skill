# Phase 4 — Determine component dependencies

Iteration 1 · 2026-10-31

## Summary

Coupling is medium by the heuristic (density 0.178, one cycle with two
members). The cycle is one function call from inventory back into orders;
we break it with order events. `reporting` depends on five components and
is handled in Phase 6. The baseline freezes today's graph so CI can start
guarding now.

## Key numbers

| Metric | Value |
|---|---|
| Components / edges | 10 / 16 |
| Density | 0.178 |
| Cycles | 1 (20% of components) |
| Cheapest cut | `shopco.inventory` → `shopco.orders` (weight 1) |
| Data confidence | low (regex import scan) |
| Change coupling | not run: the example has no meaningful git history |

## Proposed decisions

| # | Proposal | RFC |
|---|---|---|
| 1 | Continue component-based; break the cycle with order events; freeze the graph in a baseline | [0005](../rfcs/0005-coupling-assessment-and-breaking-the-orders-inventory-cycle.md) |

## Fitness functions added in this phase

| Check | Status | Notes |
|---|---|---|
| F4.1 | WARN | cycle frozen in the baseline |
| F4.3 | WARN | regex extractor; a grimp-based extractor would raise it |
| F4.4 | PASS | no new edges since the baseline |

## Artifacts

- [dependencies.md](dependencies.md), [dependencies.mmd](dependencies.mmd), [edges.json](edges.json)
- [../fitness/baseline.json](../fitness/baseline.json)
