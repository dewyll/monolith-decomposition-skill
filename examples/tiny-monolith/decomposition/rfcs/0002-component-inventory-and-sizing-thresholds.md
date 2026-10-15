---
id: 0002
title: Component inventory and sizing thresholds
status: Accepted
phase: 1
date: 2026-10-15
deciders: Example reviewer
supersedes:
superseded_by:
---

# RFC-0002: Component inventory and sizing thresholds

## Context

`size_components.py` found 10 components, all files mapped
([inventory](../01-sizing/components.md)). Mean size 8.7 lines, σ 6.3.
`shopco.orders` holds 29.9% of the code (z = 2.74) and also has two
sub-components with code of their own. Tests are excluded from sizing.

## Decision drivers

- Components of comparable size make domain grouping easier.
- Thresholds must be strict enough to catch growth, loose enough not to
  fire on a 10-component codebase every week.

## Options considered

### Option A — Keep defaults (|z| > 1, max 15% per component)

- Pros: sensitive; catches `orders` immediately.
- Cons: in a small codebase a single new file moves percentages a lot.

### Option B — Loosen to |z| > 2 and 25%

- Pros: fewer warnings.
- Cons: `orders` would pass F1.2 while clearly mixing responsibilities.

## Decision

We will keep the default thresholds (|z| > 1, max 15%) and the directory
mapping with no depth limit. `shopco.orders` will be split in Phase 3 by
pushing `service.py` down into `shopco.orders.core`; it is not allow-listed,
so F1.2 keeps failing until that happens. The entry point `shopco` (root)
is allow-listed for F3.1 in Phase 3.

## Trade-offs and consequences

- Positive: size drift is visible on every run.
- Negative: F1.2 stays red until Phase 3 lands.

## Fitness functions

| Check | Tool | Where it runs |
|---|---|---|
| F1.1, F1.2, F1.3 | `check_fitness.py --phase 1` | locally now, CI from Phase 5 |

## Evidence

- [01-sizing/components.json](../01-sizing/components.json)
- [01-sizing/report.md](../01-sizing/report.md)

## Approval

- Approved by: Example reviewer
- Date: 2026-10-15
