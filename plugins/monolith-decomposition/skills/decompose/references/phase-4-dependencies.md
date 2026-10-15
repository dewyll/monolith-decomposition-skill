# Phase 4 — Determine component dependencies

## Goal

Measure how components depend on each other, find the cycles, and judge
whether a migration is feasible and how much it will cost. Loosely coupled
components can be moved into domains (and later services) with little
friction; a dense web of dependencies means expensive untangling first, and
sometimes means tactical forking is the better path after all.

## Commands

Prefer a native extractor (see the adapter) and convert its output to
`schemas/edges.schema.json`. Otherwise use the built-in scanner:

```bash
python3 "$SKILL_DIR/scripts/extract_dependencies.py" --workspace decomposition
python3 "$SKILL_DIR/scripts/analyze_dependencies.py" --workspace decomposition
python3 "$SKILL_DIR/scripts/check_fitness.py"        --workspace decomposition --phase 4
```

Outputs in `04-dependencies/`:

- `edges.json` — neutral edge list (`from`, `to`, `weight` = number of files
  in `from` that reference `to`), with the generator and its confidence.
- `dependencies.json` — per component Ca, Ce, instability, cycle membership;
  graph summary; cycles.
- `dependencies.md` — readable report with a dependency matrix (≤ 40
  components) or the heaviest edges.
- `dependencies.mmd` — Mermaid graph; cycles drawn in red.

## Reading the numbers

- **Ca (afferent)**: how many components depend on this one. High Ca means
  changing it ripples widely; it is a natural candidate for a stable API or
  a shared component.
- **Ce (efferent)**: how many components this one depends on. High Ce makes
  it hard to move anywhere on its own.
- **Instability** `Ce / (Ca + Ce)`: near 0 is depended-upon and stable; near
  1 depends on others and is easy to change.
- **Cycles**: components that reach each other. Members of a cycle cannot
  land in different services without a synchronous loop between them.
- **Coupling level hint**: low / medium / high from cycle share and density.
  It is a heuristic to start the conversation, not a verdict.

## Hidden coupling: check before trusting the graph

Static imports miss a lot. Before the gate, ask the user about and, where
possible, look for:

- dependency injection containers and service locators;
- events, messages, observers, hooks, callbacks registered at runtime;
- reflection, string-based class or route lookups, framework autoloading;
- **shared database tables** (often the strongest coupling of all: grep
  table names across components, or use the ORM mappings);
- runtime evidence: tracing spans, call logs, APM service maps.

Add what you find as extra edges (with `"kinds": ["runtime"]` or
`["database"]`) to `edges.json` and re-run the analysis. Say in the report
which edges are measured and which were added by hand.

## Decisions and RFCs

- RFC "Coupling assessment": the numbers, the feasibility call, effort
  estimate in broad terms, and whether to continue component-based.
- One RFC per cycle to break, choosing a technique: invert the dependency
  behind an interface, replace a call with an event, move the shared piece
  to one side, or merge the components. Cycles kept on purpose go into
  `fitness.allowed_cycles` with the RFC number.
- Optionally set `thresholds.max_efferent_coupling` to cap new coupling.

## Fitness functions

- Generic: F4.1 (no cycles beyond the allowed ones), F4.2 (Ce cap), F4.3
  (data confidence).
- Native: a "no cycles between components" rule in the team's architecture
  test library, which runs on every build (see the adapter). Go forbids
  package import cycles at compile time, so the compiler is the check there.

## Gate

Show the summary block, the cycles with your recommended technique for
each, the five most coupled components, the confidence of the data and the
hidden coupling found. Ask: proceed with component-based decomposition, and
which cycles to break first? Breaking cycles is refactoring; same rule as
the earlier phases.
