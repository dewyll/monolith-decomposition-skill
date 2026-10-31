# Phase 1 — Identify and size components

Iteration 1 · 2026-10-15

## Summary

Ten components, every file mapped. `shopco.orders` is the only real
outlier: almost a third of the code, and it sits above two sub-components.
Everything else is between 4.6% and 12.6%. Recommendation: keep the default
thresholds and split `orders` in Phase 3; allow-list it until then, with
the RFC that says when the entry goes away.

## Key numbers

| Metric | Value |
|---|---|
| Components | 10 |
| Total size | 87 logical lines |
| Mean / σ | 8.7 / 6.33 |
| Over max share (15%) | 1 (`shopco.orders`, 29.9%) |
| Size outliers (abs(z) > 1) | 1 (`shopco.orders`, z = 2.74) |
| Root-with-code | 2 (`shopco`, `shopco.orders`) |

## Findings

1. `shopco.orders/service.py` mixes placing orders, cancelling them and
   answering inventory's question about open orders.
2. `shopco/app.py` is the entry point; code in the root is expected there.
3. `shopco.notification` and `shopco.orders.notification` look alike (Phase 2).

## Proposed decisions

| # | Proposal | RFC |
|---|---|---|
| 1 | Keep default thresholds, split `orders` in Phase 3 | [0002](../rfcs/0002-component-inventory-and-sizing-thresholds.md) |

## Fitness functions added in this phase

| Check | Status | Notes |
|---|---|---|
| F1.1 | PASS | all files mapped |
| F1.2 | PASS | `shopco.orders` (29.9%) allow-listed until the Phase 3 push-down |
| F1.3 | PASS | same component, same allow-list entry |

## Artifacts

- [components.json](components.json), [components.md](components.md)
