# Phase 5 — Create component domains

Iteration 1 · 2026-10-31

## Summary

The clustering gave a useful first cut (Q = 0.1): checkout code belongs
together. The team kept that and separated payments and customers because
of the drivers. Six domains, no cycle between them, five forbidden
dependencies now enforced.

## Key numbers

| Metric | Value |
|---|---|
| Domains | 6 |
| Cross-domain edges | 9 |
| Domain cycles | 0 |
| Largest domain | `ordering`, 48.3% of the code |

## Proposed decisions

| # | Proposal | RFC |
|---|---|---|
| 1 | Six domains along business capabilities; five forbidden dependencies | [0006](../rfcs/0006-domain-map.md) |

## Fitness functions added in this phase

| Check | Status | Notes |
|---|---|---|
| F5.1–F5.2 | PASS | every component in exactly one domain |
| F5.4 | PASS | no forbidden dependency present |

## Artifacts

- [domain-suggestions.md](domain-suggestions.md), [domains.draft.json](domains.draft.json)
- [domains.json](domains.json), [domain-coupling.md](domain-coupling.md), [domain-coupling.mmd](domain-coupling.mmd)
