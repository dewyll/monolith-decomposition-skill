# Phase 3 — Flatten components

Iteration 1 · 2026-10-31

## Summary

Two root namespaces hold code. `shopco` is the entry point and stays.
`shopco.orders` gets its `service.py` pushed down into `shopco.orders.core`,
scheduled as the first step of extracting ordering-service so the files
move only once. Until then the allow-list entries name the RFC.

## Key numbers

| Metric | Value |
|---|---|
| Root-with-code components | 2 |
| Orphan files | 4 |
| Call sites affected by the move | 3 (`shopco`, `inventory`, `reporting`) |

## Proposed decisions

| # | Proposal | RFC |
|---|---|---|
| 1 | Push down `orders/service.py`; keep the root entry point | [0004](../rfcs/0004-flatten-orders-by-pushing-its-root-code-down-to-orders-core.md) |

## Fitness functions added in this phase

| Check | Status | Notes |
|---|---|---|
| F3.1 | PASS | both roots allow-listed with RFC-0004 |

## Artifacts

- [plan.md](plan.md), [plan.json](plan.json)
