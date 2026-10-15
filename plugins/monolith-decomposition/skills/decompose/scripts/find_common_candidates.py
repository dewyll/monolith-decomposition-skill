#!/usr/bin/env python3
"""Phase 2: find candidates for common (shared) domain functionality.

Three signals, each reported separately so a human can weigh them:

  keyword      the component name contains a typical shared-concern word
               (audit, notification, logging, util, ...; config.common_keywords)
  duplicate    the same leaf name appears under different parents
               (billing.notification and orders.notification): likely the
               same capability implemented twice
  fan-in       many components depend on it (needs edges.json; optional)

Writes 02-common-domain/candidates.json and candidates.md. The decisions
(consolidate / keep separate / not common) are made with the user and
recorded in 02-common-domain/common-domain.json plus an RFC.

Usage:
  python3 find_common_candidates.py --workspace decomposition [--edges path]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SCHEMA_VERSION, Workspace, md_escape, now_iso, posix, write_json, write_text  # noqa: E402


def tokens(cid: str):
    return [t for t in re.split(r"[^a-z0-9]+", re.sub(r"([a-z])([A-Z])", r"\1 \2", cid).lower()) if t]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--components")
    ap.add_argument("--edges", help="optional edges.json for the fan-in signal")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    comp_path = Path(args.components) if args.components else ws.artifact(1, "components.json")
    comps = json.loads(comp_path.read_text(encoding="utf-8"))["components"]
    keywords = {k.lower() for k in ws.config.get("common_keywords", [])}
    sep = (ws.config.get("components") or {}).get("separator", ".")

    cands = defaultdict(lambda: {"reasons": [], "signals": set()})

    for c in comps:
        hit = sorted(set(tokens(c["id"].split(":")[-1])) & keywords)
        if hit:
            cands[c["id"]]["reasons"].append(f"name matches shared-concern keyword(s): {', '.join(hit)}")
            cands[c["id"]]["signals"].add("keyword")

    by_leaf = defaultdict(list)
    for c in comps:
        leaf = c["id"].split(":")[-1].split(sep)[-1].lower()
        if leaf not in ("(root)",):
            by_leaf[leaf].append(c["id"])
    groups = []
    for leaf, ids in sorted(by_leaf.items()):
        if len(ids) > 1:
            groups.append({"leaf": leaf, "components": sorted(ids)})
            for i in ids:
                others = [o for o in ids if o != i]
                cands[i]["reasons"].append(f"same leaf name as {', '.join(others)}")
                cands[i]["signals"].add("duplicate")

    edges_path = Path(args.edges) if args.edges else ws.artifact(4, "edges.json")
    fan_in_used = False
    if edges_path.exists():
        fan_in_used = True
        edges = json.loads(edges_path.read_text(encoding="utf-8")).get("edges", [])
        inc = defaultdict(set)
        for e in edges:
            if e["from"] != e["to"]:
                inc[e["to"]].add(e["from"])
        ratio = float(ws.thresholds().get("common_fan_in_ratio") or 0.3)
        limit = max(3, int(round(ratio * len(comps))))
        for cid, srcs in inc.items():
            if len(srcs) >= limit:
                cands[cid]["reasons"].append(f"used by {len(srcs)} components (threshold {limit})")
                cands[cid]["signals"].add("fan-in")

    size = {c["id"]: c for c in comps}
    result = []
    for cid, v in cands.items():
        result.append({"component": cid, "signals": sorted(v["signals"]), "reasons": v["reasons"],
                       "size": size.get(cid, {}).get("size"), "percent": size.get(cid, {}).get("percent"),
                       "decision": None})
    result.sort(key=lambda r: (-len(r["signals"]), r["component"]))

    out = {
        "schema_version": SCHEMA_VERSION, "generated_at": now_iso(),
        "generator": {"tool": "find_common_candidates.py", "confidence": "medium",
                      "fan_in_signal": fan_in_used},
        "candidates": result,
        "duplicate_groups": groups,
    }
    d = ws.phase_dir(2)
    write_json(d / "candidates.json", out)
    lines = ["# Common domain candidates", "",
             "Signals are hints, not verdicts. Each candidate needs a decision with the user: "
             "**consolidate** (into a shared component or a future shared service/library), "
             "**keep separate** (looks alike but serves different domains), or **not common**.", "",
             f"Fan-in signal: {'on' if fan_in_used else 'off (run extract_dependencies.py first to enable)'}",
             "", "| Component | Signals | % | Why |", "|---|---|---:|---|"]
    for r in result:
        lines.append(f"| `{md_escape(r['component'])}` | {', '.join(r['signals'])} | "
                     f"{'' if r['percent'] is None else r['percent']} | {md_escape('; '.join(r['reasons']))} |")
    if groups:
        lines += ["", "## Possible duplicated capabilities", ""]
        for g in groups:
            lines.append(f"- **{g['leaf']}**: " + ", ".join(f"`{c}`" for c in g["components"]))
    write_text(d / "candidates.md", "\n".join(lines) + "\n")
    print(json.dumps({"written": [posix(d / "candidates.json"), posix(d / "candidates.md")],
                      "candidates": len(result), "duplicate_groups": len(groups)}, indent=2))


if __name__ == "__main__":
    main()
