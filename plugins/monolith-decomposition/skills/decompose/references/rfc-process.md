# RFC process

Every architecture decision taken during the decomposition is written down
as a numbered RFC in `decomposition/rfcs/`. Together they explain, months
later, why the system looks the way it does. (They are close cousins of
Architecture Decision Records; teams that already use ADRs can point
`workspace.rfc_dir` at their ADR folder and keep the same template.)

## When to write one

Write an RFC when the decision:

- is hard to reverse (a boundary, a service split, a data ownership choice);
- trades one quality for another;
- someone would reasonably question later;
- adds or relaxes a fitness function (thresholds, allow-lists, forbidden
  dependencies).

Do not write RFCs for mechanical work (running a script, fixing the
component mapping typo). Small related decisions can share one RFC.

## Lifecycle

```
Proposed ──(user approves at the gate)──▶ Accepted
    │                                         │
    └──(user rejects)──▶ Rejected             └──(a later RFC replaces it)──▶ Superseded
```

Commands:

```bash
python3 "$SKILL_DIR/scripts/new_rfc.py" --workspace decomposition --title "Domain map" --phase 5
python3 "$SKILL_DIR/scripts/new_rfc.py" --workspace decomposition --set-status 0009 Accepted
python3 "$SKILL_DIR/scripts/new_rfc.py" --workspace decomposition --supersede 0009 --by 0014
```

Never edit an Accepted RFC's decision. If it changes, write a new RFC that
supersedes it. Fixing typos and adding links is fine.

## What a good RFC contains

The template (`templates/rfc.md`) has the sections. The ones that matter most:

- **Context with numbers** from the artifacts, linked by relative path.
- **At least two options**, including "do nothing" when it is real.
- **Trade-offs**: name what the team gives up. A decision without a
  downside usually means the analysis is not done.
- **Fitness functions**: the generic check id and/or the native rule that
  will keep this decision true, and where it runs.
- **Deciders and date**, filled at the gate.

Keep it short: one or two screens. Detail lives in the artifacts.

## Tie to the state file

When a phase goes to review, pass its RFC numbers to
`state.py review N --rfc 0007 --rfc 0008`. The index (`rfcs/index.md`) is
rebuilt automatically by `new_rfc.py`.
