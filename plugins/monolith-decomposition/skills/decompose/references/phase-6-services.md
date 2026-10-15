# Phase 6 — Create domain services

## Goal

Turn the approved domains into **domain services**: coarse-grained,
independently deployable units, one per domain (sometimes a few small
domains share one). This is the first service-based shape of the system,
not the final one. Finer granularity, data splitting and sagas come after,
driven by real needs.

## Artifact

`06-services/services.json` (see `schemas/services.schema.json`):

```json
{"services": [
  {"id": "ordering-service", "domains": ["ordering"], "kind": "domain-service",
   "interfaces": [
     {"to": "customer-service", "style": "sync", "purpose": "load customer tier", "rfc": "0014"},
     {"to": "shared-notification", "style": "library", "rfc": "0005"}
   ],
   "data": "shares the monolith database for now (RFC-0015)",
   "extraction_order": 2, "rfc": "0013"}
]}
```

- Every domain belongs to exactly one service.
- Every cross-domain edge from `domain-coupling.json` that crosses a service
  boundary must be declared in `interfaces`, with a communication style:
  `sync` (request/response), `async` (events/messages), `library` (shared
  code compiled in), or `data` (shared tables, to be removed later).
- Shared components from Phase 2 get their reuse decision here: shared
  library, shared service, or deliberate duplication. Each is an RFC with
  the trade-offs (versioning and coordinated releases vs. network calls and
  availability vs. divergence).

## Extraction order

Propose an order and justify it with the numbers:

- start with a domain that has **low afferent coupling** (few callers to
  update), clear value (a driver from Phase 0) and few cycles;
- keep the domains most others depend on for later, or extract them first
  behind a stable interface if they block everyone;
- each extraction should be releasable on its own, with the monolith still
  working (route traffic to the new service step by step).

## Commands

```bash
python3 "$SKILL_DIR/scripts/check_fitness.py" --workspace decomposition --phase 6
python3 "$SKILL_DIR/scripts/check_fitness.py" --workspace decomposition --phase guard
```

## Decisions and RFCs

- RFC per service: scope, interfaces, data situation, deployment, owner.
- RFC "Extraction order".
- RFC per shared component reuse decision.
- Open items that belong to later work (data ownership, splitting further,
  transactions across services) are listed as open questions, each linked
  to the RFC that depends on it.

## Fitness functions

- Generic: F6.1 (each domain in one service), F6.2 (cross-service
  dependencies declared), plus the `guard` set in CI.
- Native: the domain boundary rules from Phase 5 now mean service
  boundaries. Add consumer-driven contract tests for each `sync`/`async`
  interface once the first service is extracted (Pact or the ecosystem's
  equivalent), and a check that only the declared client code calls
  another service.

## Gate

Show the service table (service, domains, size share, interfaces, data
situation), the extraction order with its reasoning, the reuse decisions
for shared code, and the open questions. After approval, the phased
decomposition is complete: summarise the RFC index and the fitness
functions now guarding the architecture, and suggest the first extraction
as the next concrete step.
