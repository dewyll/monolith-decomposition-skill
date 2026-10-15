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
this code, frozen mid-way: Phase 0 and Phase 1 approved (see the
[RFC index](decomposition/rfcs/index.md)), Phase 2 in progress. Browse it to
see what each artifact looks like.

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
python3 $SKILL/scripts/check_fitness.py --workspace examples/tiny-monolith/scratch --phase all
```

The last command is expected to fail: finding those problems is the point.
