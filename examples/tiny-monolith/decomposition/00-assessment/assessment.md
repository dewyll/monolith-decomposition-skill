# Phase 0 — Assessment

Iteration 1 · 2026-10-15

## Drivers (ranked by the team)

1. Deploy pricing and inventory changes without redeploying the whole shop.
2. Let the payments team release on its own schedule.
3. Isolate reporting so heavy queries cannot slow down checkout.

## Constraints

- One team of four developers; no freeze possible during the migration.
- Unit tests exist for orders; little coverage elsewhere.
- Single database shared by every module.

## Probe numbers

| Signal | Value |
|---|---|
| Components | 10 |
| Files mapped to a component | 20 / 20 |
| Root-with-code components | 2 (`shopco`, `shopco.orders`) |
| Largest component share | 29.9% (`shopco.orders`) |
| Components in cycles | 2 of 10 (20%) |
| Graph density | 0.18 |

## Recommendation

Component-based decomposition. The code already has folders that match the
business (orders, inventory, payments, customers, reporting) and only one
cycle. Tactical forking would duplicate audit and notification code into
every fork for little gain at this size.

## Open questions

- Is `reporting` read-only, or does it trigger charges? (It imports `payments.charge`.)
