# Tactical forking

Use this path when Phase 0 concluded the code has no structure worth
refactoring in place. Instead of extracting pieces *out* of the monolith,
each target service starts as a full copy of it and deletes what it does
not need. Deleting code you do not need is usually easier and safer than
untangling code you do.

## Trade-offs to state in the RFC

- Teams can start in parallel right away; nothing waits on a shared refactor.
- Each fork carries dead code and duplication until it is cleaned up; some
  never get fully clean.
- Shared logic is now copied N times; fixes must be applied in several
  places until it is extracted.
- Naming and structure inside each fork still reflect the old monolith.

## Steps

### T1 — Plan the forks

Agree on the target services (use the drivers from Phase 0 and the user's
knowledge of the business). Write `00-assessment/fork-plan.md` and an RFC
per fork: what the service owns, which entry points (routes, jobs,
consumers, UI screens) it keeps, which team owns it.

### T2 — Fork and keep only the entry points

Each fork deletes the entry points that belong to other services, then
follows the compiler, the tests and dependency tools to delete code that
became unreachable. In each fork, run the same scripts to measure progress:

```bash
python3 "$SKILL_DIR/scripts/init_workspace.py" <fork>
python3 "$SKILL_DIR/scripts/size_components.py" --workspace <fork>/decomposition
python3 "$SKILL_DIR/scripts/extract_dependencies.py" --workspace <fork>/decomposition
python3 "$SKILL_DIR/scripts/analyze_dependencies.py" --workspace <fork>/decomposition
```

Track per fork in `fork-log.md`: total size over time, components removed,
components still present that belong to another fork (they are the
residual coupling).

### T3 — Find what is shared

Components that survive in several forks are shared code. Compare the
`components.json` of the forks: anything kept by two or more is a candidate
for a shared library, a shared service, or accepted duplication. This is
the Phase 2 decision list for this path; record each decision as an RFC.

### T4 — Protect each fork

Once a fork has removed what it does not own, add fitness functions so the
deleted parts do not come back:

- `fitness.forbidden_dependencies` in the fork's config, using `"*"` for
  "no dependency on components owned by other forks";
- a size trend check in CI (fail if total size grows beyond an agreed
  budget without an RFC);
- the native boundary rules from the adapter.

### T5 — Cut over

Route traffic to each fork-service, retire the corresponding parts of the
monolith, and record the cutover plan as an RFC per service.

## Gate per step

Same discipline as the component-based phases: measured numbers, proposed
decisions as RFCs, explicit approval before the next step. Use
`state.py` phases 1–6 loosely mapped (1 = T1, 2 = T2, 3 = T3, 5 = T4,
6 = T5) and say so in the first RFC, so the state file still tells the story.
