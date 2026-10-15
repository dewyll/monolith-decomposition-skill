# Phase 2 — Gather common domain components

## Goal

Find functionality that many parts of the system need (auditing,
notifications, formatting, validation, document generation...) and
especially functionality that has been **implemented more than once** in
different places. Consolidating it early avoids carrying duplicates into
several services later, and makes the eventual reuse decision (shared
library, shared service, or duplication on purpose) explicit.

## Commands

```bash
python3 "$SKILL_DIR/scripts/find_common_candidates.py" --workspace decomposition
```

The fan-in signal needs dependency edges. If Phase 4's `edges.json` does
not exist yet, run the extractor once now; it is cheap and the result is
replaced in Phase 4:

```bash
python3 "$SKILL_DIR/scripts/extract_dependencies.py" --workspace decomposition
```

Writes `02-common-domain/candidates.json` and `candidates.md`.

## Reading the signals

- **keyword**: the name contains a shared-concern word
  (`config.common_keywords`, extend it with the team's vocabulary).
- **duplicate**: the same leaf name appears under different parents
  (`billing.notification`, `orders.notification`). Strongest signal for
  consolidation, but confirm by reading the code: same name can mean
  different things.
- **fan-in**: many components depend on it. This also flags core domain
  entities (`orders` used by everyone), which are *not* shared utilities.
  Separate the two explicitly.

Look beyond the script too: grep for similar class names (`*Notifier`,
`*Mailer`, `*AuditLog`), copy-pasted helpers, and similar function
signatures in different folders.

## Decisions

For every candidate, one of:

- **consolidate** into a target component (name it, e.g. `shared.notification`);
- **keep separate** (looks similar, serves different domains, will diverge);
- **not common** (false positive, often a core domain entity).

Record them in `02-common-domain/common-domain.json`:

```json
{"decisions": [
  {"component": "billing.notification", "decision": "consolidate",
   "target": "shared.notification", "rfc": "0004"},
  {"component": "orders", "decision": "not common", "note": "core domain entity, high fan-in"}
]}
```

Write one RFC per consolidation (what moves where, which variant wins,
behavioural differences to reconcile) or one RFC for a batch of small ones.
It is fine to leave "shared library vs. shared service" open; Phase 6
decides that.

## Fitness functions

- Generic: F2.1 (every candidate has a decision).
- After consolidation: re-run `find_common_candidates.py`; the duplicate
  group must disappear. Add a native rule so the duplicate cannot come back,
  e.g. "classes named `*Notifier` reside only in `shared.notification`"
  (see the adapter for the syntax).

## Gate

Show the candidate table with your proposed decision per row, the duplicate
groups with what you saw in the code, and the RFCs. Ask the user to confirm
or change each decision. Consolidation refactors follow the same rule as
Phase 1: offer, do it in small steps if asked, re-measure afterwards.
