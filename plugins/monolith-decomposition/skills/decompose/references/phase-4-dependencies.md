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

For every cycle, `dependencies.json/.md` also lists **cut candidates**: the
lightest set of edges whose removal makes that group acyclic (a greedy
feedback arc set over the file-count weights). They are usually the
cheapest place to break the cycle; open the `samples` of those edges in
`edges.json` to see the exact imports. Confirm with the user before
treating them as the plan: a light edge can still be a hard one to cut.

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

Static imports miss a lot. Two scripts measure the biggest gaps:

```bash
# components that change together in git history (needs a git repository)
python3 "$SKILL_DIR/scripts/change_coupling.py" --workspace decomposition [--since "18 months ago"]
# tables declared (ORM mappings) and queried (SQL strings) per component
python3 "$SKILL_DIR/scripts/find_data_coupling.py" --workspace decomposition [--schema db/schema.sql]
```

- `change-coupling.json/.md`: churn per component and pairs that keep
  changing together. Pairs marked **no static dependency** are hidden
  coupling: shared data, duplicated logic, a protocol, or a feature that
  cuts across both. Co-change is undirected, so it is not merged into the
  dependency graph; it feeds `suggest_domains.py` in Phase 5 and the
  conversation here.
- `data-coupling.json/.md` and `data-edges.json`: shared tables, their
  owner (the component whose ORM mapping declares them) and their other
  users. Users depend on the owner (kind `database`). Shared tables
  without a single owner are listed, not turned into edges: deciding the
  owner is an RFC. Pass `--schema` with the DDL or migrations to cut false
  positives. Merge the edges with
  `analyze_dependencies.py --extra-edges decomposition/04-dependencies/data-edges.json`,
  or list the file once in `config.json` under `dependencies.extra_edges`.

Then ask the user about and, where possible, look for:

- dependency injection containers and service locators;
- events, messages, observers, hooks, callbacks registered at runtime;
- reflection, string-based class or route lookups, framework autoloading;
- **shared database tables** (often the strongest coupling of all: grep
  table names across components, or use the ORM mappings);
- runtime evidence: tracing spans, call logs, APM service maps.

Add what you find by hand as a small edge file in the neutral format
(`"kinds": ["runtime"]`, `["event"]` or `["database"]`), list it under
`dependencies.extra_edges`, and re-run the analysis. The report says which
file each extra edge came from, so measured and hand-made edges stay
distinguishable.

## Decisions and RFCs

- RFC "Coupling assessment": the numbers, the feasibility call, effort
  estimate in broad terms, and whether to continue component-based.
- One RFC per cycle to break, choosing a technique: invert the dependency
  behind an interface, replace a call with an event, move the shared piece
  to one side, or merge the components. Cycles kept on purpose go into
  `fitness.allowed_cycles` with the RFC number.
- Optionally set `thresholds.max_efferent_coupling` to cap new coupling.
- Record the **baseline** once the coupling RFC is agreed:
  `check_fitness.py --update-baseline`. Cycles and edges that exist today are
  frozen (F4.1 reports frozen cycles as warnings), and from now on F4.4
  fails on every new component dependency. Run it again whenever a cycle
  or edge is removed, so the improvement cannot be undone.

## Fitness functions

- Generic: F4.1 (no cycles beyond the allowed or baselined ones), F4.2 (Ce
  cap), F4.3 (data confidence), F4.4 (no new dependency since the baseline).
- Native: a "no cycles between components" rule in the team's architecture
  test library, which runs on every build (see the adapter). Go forbids
  package import cycles at compile time, so the compiler is the check there.

## Gate

Show the summary block, the cycles with their cut candidates and your
recommended technique for each, the five most coupled components, the
confidence of the data, the hidden coupling found (co-change pairs without
a static edge, shared tables) and what the baseline will freeze. Ask: proceed with component-based decomposition, and
which cycles to break first? Breaking cycles is refactoring; same rule as
the earlier phases.
