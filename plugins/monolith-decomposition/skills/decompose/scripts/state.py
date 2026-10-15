#!/usr/bin/env python3
"""Read and update the decomposition state machine (state.json).

Each phase moves through:
  not_started -> in_progress -> awaiting_review -> approved
and can be reopened, which bumps its iteration and marks every later
approved phase as `stale` (its artifacts were built on the old result).

Only run `approve` after the user explicitly approved the phase in the
conversation. The gate is the point of the workflow.

Usage:
  python3 state.py --workspace decomposition show
  python3 state.py --workspace decomposition approach component-based|tactical-forking
  python3 state.py --workspace decomposition start 1
  python3 state.py --workspace decomposition review 1 --rfc 0001 --rfc 0002
  python3 state.py --workspace decomposition approve 1 --by "Jane Doe"
  python3 state.py --workspace decomposition reopen 1 --reason "new module discovered"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Workspace, load_json, now_iso, write_json  # noqa: E402

ICON = {"not_started": "·", "in_progress": "…", "awaiting_review": "?", "approved": "✓", "stale": "!"}


def save(ws, state, event):
    state["history"].append({"at": now_iso(), **event})
    write_json(ws.state_path, state)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("show")
    a = sub.add_parser("approach")
    a.add_argument("name", choices=["component-based", "tactical-forking"])
    for name in ("start", "review", "approve", "reopen"):
        p = sub.add_parser(name)
        p.add_argument("phase", type=int, choices=range(0, 7))
        p.add_argument("--rfc", action="append", default=[])
        p.add_argument("--by", default="user")
        p.add_argument("--reason", default="")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    state = load_json(ws.state_path)
    phases = state["phases"]

    if args.cmd == "show":
        print(f"approach: {state.get('approach') or 'not chosen'} · current phase: {state['current_phase']}")
        for k in sorted(phases, key=int):
            p = phases[k]
            rf = f" RFCs: {', '.join(p['rfcs'])}" if p["rfcs"] else ""
            print(f"  [{ICON.get(p['status'], ' ')}] {k}. {p['name']} — {p['status']}"
                  f" (iteration {p['iteration']}){rf}")
        return

    if args.cmd == "approach":
        state["approach"] = args.name
        save(ws, state, {"event": "approach", "value": args.name})
        print(f"approach set to {args.name}")
        return

    key = str(args.phase)
    p = phases[key]
    if args.cmd == "start":
        prev = phases.get(str(args.phase - 1))
        if args.phase > 0 and prev and prev["status"] != "approved":
            print(f"warning: phase {args.phase - 1} is '{prev['status']}', not approved", file=sys.stderr)
        p["status"] = "in_progress"
        p["iteration"] += 1
        state["current_phase"] = args.phase
    elif args.cmd == "review":
        p["status"] = "awaiting_review"
        p["rfcs"] = sorted(set(p["rfcs"]) | {r.zfill(4) for r in args.rfc})
    elif args.cmd == "approve":
        if p["status"] != "awaiting_review":
            sys.exit(f"error: phase {key} is '{p['status']}'; move it to awaiting_review first")
        p["status"] = "approved"
        p["rfcs"] = sorted(set(p["rfcs"]) | {r.zfill(4) for r in args.rfc})
        p["approved_by"] = args.by
        p["approved_at"] = now_iso()
        state["current_phase"] = min(args.phase + 1, 6)
    elif args.cmd == "reopen":
        p["status"] = "in_progress"
        p["iteration"] += 1
        state["current_phase"] = args.phase
        for k, later in phases.items():
            if int(k) > args.phase and later["status"] in ("approved", "awaiting_review", "in_progress"):
                later["status"] = "stale"
    p["updated_at"] = now_iso()
    save(ws, state, {"event": args.cmd, "phase": args.phase, "rfcs": args.rfc,
                     "by": args.by, "reason": args.reason})
    print(json.dumps({"phase": args.phase, "status": p["status"], "iteration": p["iteration"]}))


if __name__ == "__main__":
    main()
