# Phase 1 — Identify and size components

## Goal

Build an accurate inventory of the logical components (the building blocks
whose role is identified by their namespace, package or folder) and measure
how big each one is. Components that are much larger than the rest usually
hide several responsibilities and should be split; very small ones may
belong inside a neighbour. Roughly even component sizes make the later
phases far easier.

## Getting the mapping right

What a component is depends on the language; the adapter guide says what
to use. In `config.json`:

- `source_roots` — where the code lives. Set `namespace_prefix` when the
  folder layout drops part of the namespace (C# projects, Go modules, PHP
  PSR-4).
- `components.strategy: "directory"` — every folder that holds source files
  is a component, named by its path below the source root. `max_depth`
  collapses deeper folders into their ancestor when the tree is too fine.
- `components.strategy: "explicit"` — list components with path globs when
  the folder tree does not reflect the architecture (Rails apps, Nx/Maven
  multi-module builds, packs).
- `exclude` — tests, generated code, migrations, vendored code. Tests are
  excluded by default because they distort size; mention this to the user.

Re-run sizing after every mapping change until the inventory reads like the
system the user knows. Ask them: "Does this list match how you'd describe
the system on a whiteboard?"

## Commands

```bash
python3 "$SKILL_DIR/scripts/size_components.py" --workspace decomposition
```

Writes `01-sizing/components.json` and `components.md`. If `scc` is
installed, its code counts and complexity are used; otherwise logical lines
(non-blank, non-comment). A native metric (statements per package, for
example) can be fed in with `--from-json`; see the adapter.

## Reading the numbers

- **percent** of total size, and **z-score** (how many standard deviations
  from the mean). The default outlier rule is |z| > 1, deliberately
  sensitive; tune `thresholds.size_outlier_stddev` with the user.
- **over-max**: above `thresholds.max_component_percent` (default 15%).
- **root-with-code**: a component that has sub-components *and* code of its
  own. Phase 3 resolves these; note them now, do not fix them yet.
- **unassigned files**: fix the mapping until this is zero or explained.

For each large component, look inside (file names, classes, folder
structure) and propose how it could split. For each tiny one, propose
whether it stands alone or merges.

## Decisions and RFCs

- RFC "Component inventory and sizing thresholds": the mapping rules, the
  thresholds, and the list of components the team agreed on.
- One RFC per non-trivial split or merge, or one RFC grouping them if they
  are small.
- Outliers the team keeps on purpose go into `fitness.size_allowlist` with
  a one-line reason and RFC number, e.g.
  `"orders": "RFC-0003: core domain, split after Phase 5"`.

## Fitness functions

- Generic: F1.1 (every file mapped), F1.2 (no component above max share),
  F1.3 (outliers justified). Run `check_fitness.py --phase 1`.
- Native: most architecture-test libraries do not measure size, so keep the
  generic check in CI. Some teams add a complexity budget with their
  linter; mention it as optional.

## Gate

Show: number of components, the top five by size with percent and z, the
flagged outliers with your split/merge proposal, root-with-code count, and
the thresholds. Ask the user to confirm the inventory, the thresholds and
each split/merge.

If splits or merges were approved, they are refactors in the user's code.
Offer to do them (in small, separately committed steps, tests green after
each) or let the team do them; re-run sizing afterwards and update the RFC.
