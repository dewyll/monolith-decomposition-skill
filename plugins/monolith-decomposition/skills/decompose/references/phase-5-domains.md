# Phase 5 — Create component domains

## Goal

Group the components into **domains**: cohesive areas of the business that
will become services. A good domain keeps most of its references inside
itself and talks to other domains through a few well-understood paths.

## Proposing domains

Combine three sources and say which one drove each grouping:

1. **Names and namespaces**: `customer.profile`, `customer.billing` hint at a
   customer domain.
2. **Coupling**: components with heavy mutual dependencies want to live
   together; components in a cycle must, unless the cycle is broken first.
3. **The business**: ask the user how the organisation talks about its work,
   which teams own what, and which parts change or scale together. This
   source wins when it disagrees with the other two; record the
   disagreement in the RFC.

Start with fewer, larger domains. Splitting a domain later is cheaper than
merging two services.

## Artifact

`05-domains/domains.json` (see `schemas/domains.schema.json`):

```json
{"domains": [
  {"id": "ordering", "name": "Ordering",
   "description": "Takes, prices and tracks orders",
   "components": ["orders.core", "orders.pricing", "inventory"],
   "owner": "team-checkout", "rfc": "0009"}
]}
```

Every component appears in exactly one domain. Shared components agreed in
Phase 2 can form their own `shared` domain for now.

## Commands

```bash
python3 "$SKILL_DIR/scripts/analyze_dependencies.py" --workspace decomposition \
    --domains decomposition/05-domains/domains.json
python3 "$SKILL_DIR/scripts/check_fitness.py" --workspace decomposition --phase 5
```

Adds `05-domains/domain-coupling.json/.md/.mmd`: domain-to-domain edges,
cycles between domains, and **cohesion** per domain (share of a domain's
references that stay inside it). Iterate on `domains.json` with the user
until cohesion is high and the cross-domain edges make business sense.

Optionally, restructure namespaces so the code reflects the domains
(`ordering.pricing` instead of `orders.pricing`). This makes the boundaries
visible to every developer and makes native rules simpler. It is a refactor:
propose, then do it only if asked.

## Decisions and RFCs

- RFC "Domain map": the domains, their components, owners, the evidence.
- One RFC per contested boundary (a component that could sit in two
  domains), with the options and why one won.
- `fitness.forbidden_dependencies`: for each pair of domains that must not
  talk directly, add `{"from": "a", "to": "b", "level": "domain", "rfc": "..."}`.
  Use `"*"` as a wildcard.

## Fitness functions

- Generic: F5.1 (each component in exactly one domain), F5.2 (no unknown ids),
  F5.3 (cohesion floor via `thresholds.min_domain_cohesion`), F5.4 (forbidden
  dependencies).
- Native: domain boundary rules in the team's tool. This is the most
  valuable fitness function of the whole process; the adapter shows how
  (independence contracts, layer rules, module verification, packs).
- From here on, recommend running `check_fitness.py --phase guard` in CI,
  together with the extract and analyze scripts, so new code cannot appear
  outside a domain or cross a forbidden boundary. See `fitness-functions.md`.

## Gate

Show the domain map (Mermaid from `domain-coupling.mmd`), cohesion per
domain, cross-domain edges with weights, any domain cycles, and the
contested boundaries with your recommendation. Ask the user to confirm the
map and the forbidden dependencies.
