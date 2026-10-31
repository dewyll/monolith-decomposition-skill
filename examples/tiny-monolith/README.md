# tiny-monolith

A deliberately messy ~200-line Python "shop" used to exercise every phase of
the skill. It contains, on purpose:

- a root namespace with code (`shopco/app.py`, `shopco/orders/service.py`)
- a duplicated capability (`shopco/notification` and `shopco/orders/notification`)
- shared concerns (`audit`, `notification`)
- a dependency cycle (`orders` <-> `inventory`)
- a component that depends on almost everything (`reporting`)

## A worked example

[`decomposition/`](decomposition/) is a real workspace produced by the skill on
this code, with **every phase approved, 0 to 6** (see the
[RFC index](decomposition/rfcs/index.md) and
[`state.json`](decomposition/state.json)). Browse it to see what each
artifact looks like:

| Phase | Start here |
|---|---|
| 0 | [assessment](decomposition/00-assessment/assessment.md) |
| 1 | [sizing report](decomposition/01-sizing/report.md) |
| 2 | [common domain report](decomposition/02-common-domain/report.md) |
| 3 | [flattening plan](decomposition/03-flattening/plan.md) |
| 4 | [dependency report](decomposition/04-dependencies/report.md), with the cycle's cheapest cut |
| 5 | [domain suggestions](decomposition/05-domains/domain-suggestions.md) → [domain map](decomposition/05-domains/domains.json) |
| 6 | [service map and extraction order](decomposition/06-services/report.md) |

The code itself is left messy on purpose, so you can run the scripts and
see the problems. The workspace shows how a team *decided* about them:
the refactors (the `orders` push-down, the cycle break) are accepted RFCs
scheduled with the first extraction, held in place by allow-list entries
that name their RFC and by the [baseline](decomposition/fitness/baseline.json),
so the [guard](decomposition/fitness/results-guard.md) is green today and
fails on anything that gets worse.

## Run it yourself

From the repository root (this writes to `examples/tiny-monolith/scratch/`,
leaving the committed example untouched):

```bash
SKILL=plugins/monolith-decomposition/skills/decompose
python3 $SKILL/scripts/init_workspace.py examples/tiny-monolith --dir scratch
python3 $SKILL/scripts/size_components.py --workspace examples/tiny-monolith/scratch
python3 $SKILL/scripts/extract_dependencies.py --workspace examples/tiny-monolith/scratch
python3 $SKILL/scripts/analyze_dependencies.py --workspace examples/tiny-monolith/scratch
python3 $SKILL/scripts/find_common_candidates.py --workspace examples/tiny-monolith/scratch
python3 $SKILL/scripts/suggest_domains.py --workspace examples/tiny-monolith/scratch
python3 $SKILL/scripts/check_fitness.py --workspace examples/tiny-monolith/scratch --phase all
```

The last command is expected to fail: finding those problems is the point.

To see the CI guard on the committed workspace without touching it, copy
the example first:

```bash
cp -r examples/tiny-monolith /tmp/tiny && python3 $SKILL/scripts/run_guard.py --workspace /tmp/tiny/decomposition
```
