# Fitness functions

A fitness function is an automated, objective check that some architectural
characteristic still holds. In this workflow every approved decision should
end up guarded by one, so the boundaries you agreed on survive the next
thousand commits.

Two layers work together:

1. **Generic checks** (`check_fitness.py`) read the neutral artifacts, so
   they work for every language. They are coarse but always available.
2. **Native rules** in the team's own architecture-test library or linter
   (listed per ecosystem in `adapters/`). They run in the normal test
   suite, give precise error messages and are what developers will see.

Use both. Generic checks prove the process; native rules keep it alive.

## Generic checks by phase

| Check | Phase | Guards | Config |
|---|---|---|---|
| F1.1 | 1 | every file belongs to a component | `components`, `exclude` |
| F1.2 | 1 | no component above a share of the codebase | `thresholds.max_component_percent`, `fitness.size_allowlist` |
| F1.3 | 1 | size outliers are justified | `thresholds.size_outlier_stddev`, `fitness.size_allowlist` |
| F2.1 | 2 | every common-domain candidate has a decision | `02-common-domain/common-domain.json` |
| F3.1 | 3 | no orphaned code in parent namespaces | `fitness.orphan_allowlist` |
| F4.1 | 4 | no dependency cycles | `fitness.allowed_cycles`, baseline |
| F4.2 | 4 | efferent coupling cap | `thresholds.max_efferent_coupling` |
| F4.3 | 4 | dependency data is better than low confidence | (native extractor) |
| F4.4 | 4 | no new component dependency since the baseline | `fitness/baseline.json` |
| F5.1–F5.2 | 5 | every component in exactly one domain | `05-domains/domains.json` |
| F5.3 | 5 | domain cohesion floor | `thresholds.min_domain_cohesion` |
| F5.4 | 5 | forbidden dependencies absent | `fitness.forbidden_dependencies` |
| F6.1–F6.2 | 6 | services cover domains; cross-service calls declared | `06-services/services.json` |

`--phase guard` runs the subset that should keep running after the gates
(1, 3, 4, 5, 6). `--strict` turns warnings into failures.

## The baseline: a ratchet, not a wall

A real monolith starts with cycles and tangled edges. Absolute rules make
the guard red on day one, and a guard that is always red gets switched
off. Record the current state once the Phase 4 RFC is agreed:

```bash
python3 $SKILL/scripts/check_fitness.py --workspace decomposition --update-baseline
```

`fitness/baseline.json` holds the component edges and cycles of that
moment. From then on:

- a cycle whose members all sit inside a baselined cycle is a **warning**;
  a new cycle, or a baselined one that grew, **fails** F4.1;
- any component dependency not in the baseline **fails** F4.4;
- edges that disappeared are reported; run `--update-baseline` again to
  lock the improvement in, so it cannot quietly come back.

Commit the baseline and review changes to it like code: a pull request
that updates it is accepting new coupling. `--no-baseline` shows the
absolute picture.

## Wiring the guard into CI

Checking the committed artifacts proves nothing about the code in a pull
request, so the guard must re-measure first. `run_guard.py` does it in one
command: sizing (into `03-flattening/` when that phase produced an
inventory), dependency extraction, analysis (with `dependencies.extra_edges`
and the domain map when present), then `check_fitness.py --phase guard`.

```bash
SKILL=path/to/skills/decompose      # vendored copy or a git submodule
python3 $SKILL/scripts/run_guard.py --workspace decomposition
```

When a native extractor produces the edges, run it and its converter
first, then `run_guard.py --skip-extract`.

GitHub Actions example:

```yaml
name: architecture
on: [pull_request]
jobs:
  fitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with: { python-version: "3.13" }
      - run: python3 tools/decompose/scripts/run_guard.py --workspace decomposition
```

(Keep the action versions in step with your other workflows.)
`run_guard.py` rewrites the artifacts in the workspace, which is what CI
needs; on a laptop, review or discard that diff afterwards.

## Choosing a native library

The adapters list well-known options, but this landscape changes. Before
recommending one, check (with web search if available):

- last release within roughly the past 12 months, and recent commits;
- support for the project's language and framework versions;
- the rule types needed: forbidden dependencies, cycles, layers or
  independence, naming/residence rules;
- how it runs (test framework, CLI, linter plugin) and whether that fits the
  team's pipeline.

State the choice and the date checked in the RFC. If nothing maintained
exists, fall back to the generic checks and say so.

## Writing a good rule

- One rule per decision, named after it, with the RFC id in the message:
  `"ordering must not depend on reporting (RFC-0011)"`.
- Fail the build, do not just warn, once the team approved the decision.
  Use a baseline/freeze feature (many tools have one) when existing
  violations must be burned down gradually; record the baseline in the RFC.
- Keep rules close to the code they protect and run them on every pull
  request.
