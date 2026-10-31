#!/usr/bin/env python3
"""Phase 0/4/5: churn and change coupling (co-change) from git history.

Imports show who *can* call whom; history shows what *actually changes
together*. Two components that keep landing in the same commits are
coupled whether or not one imports the other (shared tables, copy-paste,
a protocol both sides must follow, a feature that cuts across them). That
is exactly the coupling a service boundary will make expensive.

For every component it reports churn (commits, file changes, distinct
authors). For every pair it reports how many commits touched both and a
degree of coupling:

  degree = shared commits / average commits of the two components

Pairs that change together but have no static dependency in either
direction (when 04-dependencies/edges.json exists) are flagged as
*hidden coupling*: the import graph alone would have missed them.

Bulk commits (formatting, renames, mass refactors) are skipped with
--max-files, merges are ignored.

Usage:
  python3 change_coupling.py --workspace decomposition \
      [--since "18 months ago"] [--max-files 40] [--min-shared 3] [--min-degree 0.2] \
      [--edges 04-dependencies/edges.json] [--out-dir 04-dependencies]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (SCHEMA_VERSION, ComponentMapper, Workspace, in_scope, md_escape,  # noqa: E402
                    now_iso, posix, write_json, write_text)

MARK = "\x1e"  # record separator: never appears in a path


def git_log(project_root: Path, since: str, until: str = None):
    """Yield (sha, author, [paths relative to project_root]) for non-merge commits."""
    cmd = ["git", "-C", str(project_root), "log", "--no-merges", "--no-renames", "--relative",
           "--name-only", f"--format={MARK}%H%x09%ae"]
    if since:
        cmd.append(f"--since={since}")
    if until:
        cmd.append(f"--until={until}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        sys.exit("error: git is not installed")
    if proc.returncode != 0:
        sys.exit(f"error: git log failed (is {project_root} inside a git repository?)\n{proc.stderr.strip()}")
    for chunk in proc.stdout.split(MARK)[1:]:
        lines = [x for x in chunk.splitlines() if x.strip()]
        if not lines:
            continue
        sha, _, author = lines[0].partition("\t")
        yield sha, author, lines[1:]


def analyse(commits, ws: Workspace, max_files: int, min_shared: int, min_degree: float, static_pairs):
    mapper = ComponentMapper(ws.config)
    churn = defaultdict(lambda: {"commits": 0, "file_changes": 0, "authors": set()})
    shared = defaultdict(int)
    stats = {"commits_read": 0, "commits_used": 0, "skipped_bulk": 0, "skipped_out_of_scope": 0}
    for sha, author, paths in commits:
        stats["commits_read"] += 1
        files = [p for p in paths if in_scope(p, ws.config)]
        if not files:
            stats["skipped_out_of_scope"] += 1
            continue
        if len(files) > max_files:
            stats["skipped_bulk"] += 1
            continue
        stats["commits_used"] += 1
        per_comp = defaultdict(int)
        for f in files:
            mapped = mapper.map(f)
            if mapped:
                per_comp[mapped[0]] += 1
        for comp, n in per_comp.items():
            churn[comp]["commits"] += 1
            churn[comp]["file_changes"] += n
            churn[comp]["authors"].add(author.lower())
        for a, b in combinations(sorted(per_comp), 2):
            shared[(a, b)] += 1

    pairs = []
    for (a, b), n in shared.items():
        avg = (churn[a]["commits"] + churn[b]["commits"]) / 2
        degree = round(n / avg, 2) if avg else 0.0
        if n < min_shared or degree < min_degree:
            continue
        pair = {"a": a, "b": b, "shared_commits": n, "degree": degree}
        if static_pairs is not None:
            pair["static_dependency"] = (a, b) in static_pairs or (b, a) in static_pairs
        pairs.append(pair)
    pairs.sort(key=lambda p: (-p["degree"], -p["shared_commits"], p["a"], p["b"]))
    comps = [{"id": c, "commits": v["commits"], "file_changes": v["file_changes"],
              "authors": len(v["authors"])} for c, v in churn.items()]
    comps.sort(key=lambda c: (-c["commits"], c["id"]))
    return comps, pairs, stats


def render_md(data) -> str:
    g, s = data["generator"], data["stats"]
    lines = [
        "# Change coupling", "",
        f"Generated {data['generated_at']} from git history"
        f"{' since ' + g['since'] if g.get('since') else ''}. "
        f"{s['commits_used']} commits used ({s['skipped_bulk']} bulk commits with more than "
        f"{g['max_files']} files skipped, {s['skipped_out_of_scope']} touched no analysed file).", "",
        "Degree = shared commits / average commits of the pair. "
        f"Pairs shown: at least {g['min_shared']} shared commits and degree ≥ {g['min_degree']}.", "",
    ]
    hidden = [p for p in data["pairs"] if p.get("static_dependency") is False]
    if hidden:
        lines += [f"**{len(hidden)} pair(s) change together without any static dependency** "
                  "(hidden coupling: shared data, duplicated logic, a protocol, or a feature that spans "
                  "both). Check them before trusting the import graph.", ""]
    lines += ["## Pairs that change together", "",
              "| A | B | Shared commits | Degree | Static dependency |", "|---|---|---:|---:|---|"]
    for p in data["pairs"][:50]:
        dep = {True: "yes", False: "**no**", None: "?"}[p.get("static_dependency")]
        lines.append(f"| `{md_escape(p['a'])}` | `{md_escape(p['b'])}` | {p['shared_commits']} | "
                     f"{p['degree']} | {dep} |")
    if not data["pairs"]:
        lines.append("| (none above the thresholds) | | | | |")
    lines += ["", "## Churn per component", "", "| Component | Commits | File changes | Authors |",
              "|---|---:|---:|---:|"]
    for c in data["components"][:40]:
        lines.append(f"| `{md_escape(c['id'])}` | {c['commits']} | {c['file_changes']} | {c['authors']} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--since", default="18 months ago", help='git date, e.g. "2 years ago" ("" = all history)')
    ap.add_argument("--until")
    ap.add_argument("--max-files", type=int, default=40, help="skip commits touching more analysed files")
    ap.add_argument("--min-shared", type=int, default=3)
    ap.add_argument("--min-degree", type=float, default=0.2)
    ap.add_argument("--edges", help="edges.json used to flag hidden coupling (default: 04-dependencies)")
    ap.add_argument("--out-dir", help="default: 04-dependencies")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    edges_path = Path(args.edges) if args.edges else ws.artifact(4, "edges.json")
    static_pairs = None
    if edges_path.exists():
        static_pairs = {(e["from"], e["to"]) for e in
                        json.loads(edges_path.read_text(encoding="utf-8")).get("edges", [])}

    comps, pairs, stats = analyse(git_log(ws.project_root, args.since, args.until), ws,
                                  args.max_files, args.min_shared, args.min_degree, static_pairs)
    data = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "generator": {"tool": "change_coupling.py", "method": "git-log-co-change", "since": args.since or None,
                      "until": args.until, "max_files": args.max_files, "min_shared": args.min_shared,
                      "min_degree": args.min_degree,
                      "static_edges": posix(os.path.relpath(edges_path.resolve(), ws.dir)) if static_pairs is not None else None},
        "stats": stats,
        "components": comps,
        "pairs": pairs,
    }
    out_dir = ws.dir / (args.out_dir or ws.PHASE_DIRS[4])
    write_json(out_dir / "change-coupling.json", data)
    write_text(out_dir / "change-coupling.md", render_md(data))
    print(json.dumps({"written": [posix(out_dir / "change-coupling.json"), posix(out_dir / "change-coupling.md")],
                      **stats, "pairs": len(pairs),
                      "hidden_pairs": sum(1 for p in pairs if p.get("static_dependency") is False)}, indent=2))


if __name__ == "__main__":
    main()
