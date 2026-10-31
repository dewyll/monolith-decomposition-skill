#!/usr/bin/env python3
"""Read and update the decomposition state machine (state.json).

Each phase moves through:
  not_started -> in_progress -> awaiting_review -> approved
and can be reopened, which bumps its iteration and marks every later
approved phase as `stale` (its artifacts were built on the old result).

Only run `approve` after the user explicitly approved the phase in the
conversation. The gate is the point of the workflow, so the script enforces
it as well:

  start    the previous phase must be approved; phases 1-6 cannot start
           when the approach is tactical forking
  review   the phase must be in progress
  approve  the phase must be awaiting review, every RFC attached to it must
           exist and be Accepted, and (phases 1-6) the latest
           `check_fitness.py --phase N` run must have passed after the
           phase was started

`--force --reason "..."` overrides a guard; the override is recorded in
the history so reviewers can see it.

Usage:
  python3 state.py --workspace decomposition show
  python3 state.py --workspace decomposition approach component-based|tactical-forking
  python3 state.py --workspace decomposition start 1
  python3 state.py --workspace decomposition review 1 --rfc 0001 --rfc 0002
  python3 state.py --workspace decomposition approve 1 --by "Jane Doe"
  python3 state.py --workspace decomposition reopen 1 --reason "new module discovered"
  python3 state.py --workspace decomposition start 3 --force --reason "phase 2 skipped: no candidates"
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Workspace, load_json, now_iso, write_json  # noqa: E402
from new_rfc import parse_front, rfcs as list_rfcs  # noqa: E402

ICON = {"not_started": "·", "in_progress": "…", "awaiting_review": "?", "approved": "✓", "stale": "!"}


def save(ws, state, event):
    state["history"].append({"at": now_iso(), **event})
    write_json(ws.state_path, state)


def last_start(state, phase: int):
    """Timestamp of the most recent start/reopen of a phase."""
    for ev in reversed(state.get("history", [])):
        if ev.get("phase") == phase and ev.get("event") in ("start", "reopen"):
            return ev.get("at")
    return None


def approval_problems(ws, state, phase: int, rfc_ids) -> list:
    problems = []
    by_id = {parse_front(p).get("id", p.name[:4]).zfill(4): p for p in list_rfcs(ws)}
    for rid in rfc_ids:
        path = by_id.get(rid)
        if path is None:
            problems.append(f"RFC-{rid} not found in {ws.rfc_dir}")
            continue
        status = parse_front(path).get("status", "")
        if status != "Accepted":
            problems.append(f"RFC-{rid} is '{status}', not Accepted "
                            f"(new_rfc.py --set-status {rid} Accepted once the user agreed)")
    if not rfc_ids:
        print(f"warning: phase {phase} has no RFC attached; every decision should have one", file=sys.stderr)
    if phase >= 1:
        res_path = ws.fitness_dir / f"results-{phase}.json"
        if not res_path.exists():
            problems.append(f"no fitness results for phase {phase}: run check_fitness.py --phase {phase}")
        else:
            res = load_json(res_path)
            started = last_start(state, phase)
            if not res.get("passed"):
                failed = [r["id"] for r in res.get("results", []) if r.get("status") == "FAIL"]
                problems.append(f"fitness checks for phase {phase} failed: {', '.join(failed) or '?'}")
            elif started and res.get("generated_at", "") < started:
                problems.append(f"fitness results for phase {phase} predate the phase start; run them again")
    return problems


def guard(problems, args) -> None:
    if not problems:
        return
    if args.force:
        if not args.reason:
            sys.exit("error: --force needs --reason so the override is explained in the history")
        for p in problems:
            print(f"override: {p}", file=sys.stderr)
        return
    sys.exit("error: " + "\n       ".join(problems) + "\n(use --force --reason \"...\" to override)")


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
        p.add_argument("--force", action="store_true", help="override a guard (needs --reason)")
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
    problems = []
    if args.cmd == "start":
        prev = phases.get(str(args.phase - 1))
        if args.phase > 0 and prev and prev["status"] != "approved":
            problems.append(f"phase {args.phase - 1} is '{prev['status']}', not approved")
        if args.phase > 0 and state.get("approach") == "tactical-forking":
            problems.append("the approach is tactical forking; follow references/tactical-forking.md "
                            "instead of phases 1-6")
        if p["status"] == "awaiting_review":
            problems.append(f"phase {key} is awaiting review; approve it or reopen it")
        guard(problems, args)
        p["status"] = "in_progress"
        p["iteration"] += 1
        state["current_phase"] = args.phase
    elif args.cmd == "review":
        if p["status"] != "in_progress":
            problems.append(f"phase {key} is '{p['status']}'; start it first")
        guard(problems, args)
        p["status"] = "awaiting_review"
        p["rfcs"] = sorted(set(p["rfcs"]) | {r.zfill(4) for r in args.rfc})
    elif args.cmd == "approve":
        if p["status"] != "awaiting_review":
            sys.exit(f"error: phase {key} is '{p['status']}'; move it to awaiting_review first")
        rfc_ids = sorted(set(p["rfcs"]) | {r.zfill(4) for r in args.rfc})
        guard(approval_problems(ws, state, args.phase, rfc_ids), args)
        p["status"] = "approved"
        p["rfcs"] = rfc_ids
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
    event = {"event": args.cmd, "phase": args.phase, "rfcs": args.rfc, "by": args.by, "reason": args.reason}
    if args.force:
        event["forced"] = True
    save(ws, state, event)
    print(json.dumps({"phase": args.phase, "status": p["status"], "iteration": p["iteration"]}))


if __name__ == "__main__":
    main()
