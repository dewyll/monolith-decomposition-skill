# Phase 3 — Flatten components

## Goal

Make every component a leaf. When a namespace has sub-namespaces *and*
code of its own (`orders` with files next to `orders/pricing`), those files
are orphaned: they belong to no clear component, so nobody can say which
service they will end up in. Flattening moves them somewhere definite.

## Commands

The inventory from Phase 1 already flags them (`root-with-code`). Read
`01-sizing/components.md`, section "Root namespaces with code", and the
`orphan_file_paths` of each flagged component in `components.json`.

After any refactor, re-measure into this phase's folder:

```bash
python3 "$SKILL_DIR/scripts/size_components.py" --workspace decomposition --out-dir 03-flattening
python3 "$SKILL_DIR/scripts/check_fitness.py"   --workspace decomposition --phase 3
```

Later phases read `03-flattening/components.json` when it exists.

## Options for each flagged component

1. **Push down**: move the orphaned files into a new leaf beside the
   existing ones (`orders.core`, `orders.workflow`). Good when the orphans
   form a coherent piece of their own.
2. **Distribute**: move each orphaned file into the existing child it
   belongs with. Good when the orphans are helpers of specific children.
3. **Pull up**: merge the children into the parent so it becomes one leaf.
   Good when the children are tiny and always change together.
4. **Extract as shared**: orphans used by every child may be common
   functionality; send them back to the Phase 2 decision list.

Look at what each orphaned file does and who imports it before proposing.
The root component of the whole tree (often the app's entry point) is a
legitimate exception; put it in `fitness.orphan_allowlist` with a reason.

## Outputs

- `03-flattening/plan.md`: per flagged component, the option chosen and the
  file moves.
- `03-flattening/plan.json`:
  `{"moves": [{"files": ["src/orders/service.ts"], "to_component": "orders.core", "rfc": "0006"}]}`
- `03-flattening/components.json/.md`: re-measured inventory after the moves.
- RFC per non-obvious flattening decision.

## Fitness functions

- Generic: F3.1 (no root-with-code except allow-listed).
- Native: a rule that no class/module lives directly in the flattened
  parents. Examples are in each adapter.

## Gate

Show each flagged component, its orphan files, the option you recommend and
why. After approval, refactoring is the user's call: offer to carry out the
moves with language-aware refactoring (update imports, run the tests after
each step, one commit per component). Re-run the commands above and show
F3.1 passing before approving the phase.
