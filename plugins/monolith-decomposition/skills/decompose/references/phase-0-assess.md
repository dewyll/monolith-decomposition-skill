# Phase 0 — Assess the monolith and choose an approach

## Goal

Decide, with evidence, how this monolith will be broken apart:

- **Component-based decomposition**: refactor the existing code base in
  place, phase by phase, until it is a set of well-bounded domains that can
  be lifted out as services. Works when the code already has a recognisable
  structure (packages, namespaces, modules, folders that mean something).
- **Tactical forking**: copy the whole monolith once per target service and
  let each copy delete what it does not need. Works when the code has no
  usable internal structure (a "big ball of mud") and refactoring in place
  would mean rewriting most of it anyway.

The choice changes every later step, so it is the first RFC.

## Steps

1. `init_workspace.py <project>` if not done. Review `config.json` with the user.
2. Take a quick, cheap reading of the structure. These runs are throwaway
   probes; Phase 1 and Phase 4 redo them properly:

   ```bash
   python3 "$SKILL_DIR/scripts/size_components.py"      --workspace decomposition --out-dir 00-assessment/probe
   python3 "$SKILL_DIR/scripts/extract_dependencies.py" --workspace decomposition \
       --components decomposition/00-assessment/probe/components.json \
       --out decomposition/00-assessment/probe/edges.json
   python3 "$SKILL_DIR/scripts/analyze_dependencies.py" --workspace decomposition \
       --edges decomposition/00-assessment/probe/edges.json \
       --components decomposition/00-assessment/probe/components.json \
       --out-dir decomposition/00-assessment/probe
   ```

   If the project is a git repository, add churn and change coupling to the
   probe; it shows where the work actually happens and which parts move
   together:

   ```bash
   python3 "$SKILL_DIR/scripts/change_coupling.py" --workspace decomposition \
       --edges decomposition/00-assessment/probe/edges.json --out-dir 00-assessment/probe
   ```

3. Ask the user about **why** they are migrating. The drivers decide what a
   good boundary looks like later on. Typical drivers: independent
   deployability, scaling one part differently, fault isolation, team
   autonomy, technology change, time to market. Ask them to rank the top
   three and keep that ranking in the RFC.
4. Ask about constraints: team size and structure, deadlines, test coverage,
   whether the business can tolerate a freeze, shared database realities.
5. Write `00-assessment/assessment.md` and draft the RFC.

## Signals

| Signal (from the probe) | Leans component-based | Leans tactical forking |
|---|---|---|
| Share of files mapped to meaningful components | high | low, or one giant folder |
| Root-with-code components | few | the norm |
| Share of components in cycles | under ~10% | over ~30% |
| Graph density | low | high |
| Size distribution | a few outliers | one component holds most of the code |
| Test coverage | decent (refactoring is safe) | poor (moving code is risky) |
| Change coupling (if measured) | changes stay inside components | most commits touch many components |
| Team need | steady, controlled extraction | many teams must start in parallel now |

These are heuristics. A codebase can sit in the middle; say so, and choose
based on the drivers and the team's appetite for refactoring.

## Outputs

- `00-assessment/assessment.md`: drivers (ranked), constraints, probe
  numbers, recommendation, open questions.
- `00-assessment/probe/*`: raw probe artifacts.
- RFC "Decomposition approach" with both options, the trade-offs, and the
  recommendation.

## Fitness functions

None are enforced yet. Record in the RFC which checks the team commits to
running from Phase 1 onwards (at minimum `check_fitness.py --phase guard` in
CI once Phase 5 is approved).

## Gate

Show: the ranked drivers, five or six probe numbers, the recommendation and
its main trade-off. Ask the user to confirm the approach. Then:

```bash
python3 "$SKILL_DIR/scripts/state.py" --workspace decomposition approach component-based   # or tactical-forking
python3 "$SKILL_DIR/scripts/state.py" --workspace decomposition approve 0 --by "<name>"
```

If tactical forking is chosen, continue with `tactical-forking.md`.
