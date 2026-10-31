# Phase 6 — Create domain services

Iteration 1 · 2026-10-31

## Summary

Four domain services, one shared library and the shell. Reporting moves
to events, which leaves one synchronous call on the checkout path.
Extraction starts with payment (fewest callers) and ends with ordering,
whose first commits are the pending push-down and cycle break.

## Service map

| Service | Domains | Size share | Interfaces | Data | Order |
|---|---|---:|---|---|---:|
| payment-service | payment | 10.3% | platform-lib (library) | own schema | 1 |
| reporting-service | reporting | 11.5% | ordering, payment (async); customer (sync); platform-lib | event read model | 2 |
| customer-service | customer | 4.6% | — | owns customers | 3 |
| ordering-service | ordering | 48.3% | customer (sync); platform-lib | shared DB for now | 4 |
| platform-lib | platform | 15.0% | — | none | — |
| shop-shell | shell | 10.3% | ordering, reporting (sync) | none | — |

## Proposed decisions

| # | Proposal | RFC |
|---|---|---|
| 1 | Services and interfaces | [0007](../rfcs/0007-domain-services-and-their-interfaces.md) |
| 2 | Extraction order | [0008](../rfcs/0008-extraction-order.md) |

## Fitness functions added in this phase

| Check | Status | Notes |
|---|---|---|
| F6.1 | PASS | every domain in one service |
| F6.2 | PASS | every cross-service edge declared |
| guard | see [results-guard.md](../fitness/results-guard.md) | wired with `run_guard.py` |

## Open questions (later work)

- Data ownership of `orders`, `stock` and `customers` tables (RFC-0007, RFC-0005).
- Whether `pricing` becomes its own service after ordering is out (RFC-0006).

## Artifacts

- [services.json](services.json)
