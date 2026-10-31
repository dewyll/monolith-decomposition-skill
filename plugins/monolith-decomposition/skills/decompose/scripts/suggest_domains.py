#!/usr/bin/env python3
"""Phase 5: a measured *starting point* for the domain map.

Domains are business decisions, so this script never writes domains.json.
It clusters components that are tightly connected and loosely connected to
the rest, which is what a good domain boundary looks like in the code, and
hands the result to the conversation as a draft.

Signal (an undirected weighted graph over components):
  imports      04-dependencies/dependencies.json edges, both directions summed
  co-change    04-dependencies/change-coupling.json pairs (shared commits),
               when change_coupling.py was run
Each signal is normalised to its total weight, then mixed with
--change-weight (default 0.5 when change coupling exists, else 0).

Components that Phase 2 decided to consolidate as shared code (and their
targets) are left out by default: they are depended on by everyone and
would glue every cluster together. They are listed as "shared". Add more
with --exclude.

Clustering: Louvain modularity optimisation, deterministic (sorted order,
ties keep the current community). Modularity Q above ~0.3 usually means
the structure is real; near 0 means the graph has no clear clusters.

Outputs in 05-domains/:
  domain-suggestions.json/.md   clusters, cohesion, modularity, shared set
  domains.draft.json            with --write-draft: the clusters in the
                                domains.json format, ids to be renamed with
                                the user before it becomes domains.json

Usage:
  python3 suggest_domains.py --workspace decomposition [--change-weight 0.5]
                             [--exclude comp ...] [--resolution 1.0] [--write-draft]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SCHEMA_VERSION, Workspace, md_escape, now_iso, posix, write_json, write_text  # noqa: E402


# --------------------------------------------------------------------------
# Louvain
# --------------------------------------------------------------------------
def _one_level(adj, resolution):
    """Local moving phase. adj: node -> {neighbour: weight} (self-loop allowed). Returns node -> community."""
    nodes = sorted(adj)
    k = {n: sum(w for m, w in adj[n].items() if m != n) + 2 * adj[n].get(n, 0.0) for n in nodes}
    m2 = sum(k.values())  # 2m
    comm = {n: n for n in nodes}
    tot = dict(k)
    if m2 == 0:
        return comm, False
    moved_any, improved = False, True
    passes = 0
    while improved and passes < 100:
        improved = False
        passes += 1
        for n in nodes:
            c0 = comm[n]
            links = defaultdict(float)
            for m, w in adj[n].items():
                if m != n:
                    links[comm[m]] += w
            tot[c0] -= k[n]
            best, best_gain = c0, links.get(c0, 0.0) - resolution * tot[c0] * k[n] / m2
            for c in sorted(links):
                gain = links[c] - resolution * tot[c] * k[n] / m2
                if gain > best_gain + 1e-12:
                    best, best_gain = c, gain
            tot[best] += k[n]
            if best != c0:
                comm[n] = best
                improved = moved_any = True
    return comm, moved_any


def louvain(nodes, weights, resolution=1.0):
    """weights: {(a, b): w} undirected with a < b. Returns {node: cluster index}."""
    adj = {n: {} for n in nodes}
    for (a, b), w in weights.items():
        adj[a][b] = adj[a].get(b, 0.0) + w
        adj[b][a] = adj[b].get(a, 0.0) + w
    member = {n: n for n in nodes}       # original node -> current super-node
    while True:
        comm, moved = _one_level(adj, resolution)
        if not moved:
            break
        member = {n: comm[s] for n, s in member.items()}
        new = defaultdict(lambda: defaultdict(float))
        for a, nbrs in adj.items():
            for b, w in nbrs.items():
                ca, cb = comm[a], comm[b]
                if a == b:
                    new[ca][ca] += w
                elif ca == cb:
                    new[ca][ca] += w / 2   # each internal edge is seen from both ends
                else:
                    new[ca][cb] += w
        adj = {c: dict(v) for c, v in new.items()}
        for c in set(comm.values()):
            adj.setdefault(c, {})
    groups = defaultdict(list)
    for n, s in member.items():
        groups[s].append(n)
    ordered = sorted((sorted(g) for g in groups.values()), key=lambda g: (-len(g), g[0]))
    return {n: i for i, g in enumerate(ordered) for n in g}


def modularity(clusters, weights, resolution=1.0):
    m = sum(weights.values())
    if m == 0:
        return 0.0
    deg = defaultdict(float)
    inside = defaultdict(float)
    for (a, b), w in weights.items():
        deg[a] += w
        deg[b] += w
        if clusters[a] == clusters[b]:
            inside[clusters[a]] += w
    tot = defaultdict(float)
    for n, d in deg.items():
        tot[clusters[n]] += d
    return round(sum(inside[c] / m - resolution * (tot[c] / (2 * m)) ** 2 for c in tot), 3)


# --------------------------------------------------------------------------
def common_prefix_name(ids, sep="."):
    parts = [i.split(sep) for i in ids]
    prefix = []
    for seg in zip(*parts):
        if len(set(seg)) != 1:
            break
        prefix.append(seg[0])
    return prefix


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--dependencies", help="default: 04-dependencies/dependencies.json")
    ap.add_argument("--change-coupling", help="default: 04-dependencies/change-coupling.json if present")
    ap.add_argument("--change-weight", type=float, help="0..1 share of the co-change signal")
    ap.add_argument("--exclude", action="append", default=[], help="component to leave out (shared code)")
    ap.add_argument("--keep-shared", action="store_true", help="do not exclude Phase 2 consolidated components")
    ap.add_argument("--resolution", type=float, default=1.0, help=">1 gives more, smaller clusters")
    ap.add_argument("--write-draft", action="store_true", help="also write 05-domains/domains.draft.json")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    dep_path = Path(args.dependencies) if args.dependencies else ws.artifact(4, "dependencies.json")
    if not dep_path.exists():
        sys.exit("error: no dependencies.json; run analyze_dependencies.py first")
    deps = json.loads(dep_path.read_text(encoding="utf-8"))
    nodes = sorted(c["id"] for c in deps["components"])

    shared = set(args.exclude)
    cd_path = ws.artifact(2, "common-domain.json")
    if cd_path.exists() and not args.keep_shared:
        for d in json.loads(cd_path.read_text(encoding="utf-8")).get("decisions", []):
            if d.get("decision") == "consolidate":
                shared.add(d["component"])
                if d.get("target"):
                    shared.add(d["target"])
    shared &= set(nodes) | set(args.exclude)
    nodes = [n for n in nodes if n not in shared]
    keep = set(nodes)

    imp = defaultdict(float)
    for e in deps["edges"]:
        a, b = e["from"], e["to"]
        if a in keep and b in keep and a != b:
            imp[tuple(sorted((a, b)))] += e.get("weight", 1)

    cc_path = Path(args.change_coupling) if args.change_coupling else ws.artifact(4, "change-coupling.json")
    cc = defaultdict(float)
    if cc_path.exists():
        for p in json.loads(cc_path.read_text(encoding="utf-8")).get("pairs", []):
            if p["a"] in keep and p["b"] in keep:
                cc[tuple(sorted((p["a"], p["b"])))] += p["shared_commits"]
    alpha = args.change_weight if args.change_weight is not None else (0.5 if cc else 0.0)
    ti, tc = sum(imp.values()) or 1.0, sum(cc.values()) or 1.0
    weights = defaultdict(float)
    for k, w in imp.items():
        weights[k] += (1 - alpha) * w / ti
    for k, w in cc.items():
        weights[k] += alpha * w / tc

    clusters = louvain(nodes, weights, args.resolution)
    q = modularity(clusters, weights, args.resolution)
    sizes = {}
    for path in (ws.artifact(3, "components.json"), ws.artifact(1, "components.json")):
        if path.exists():
            sizes = {c["id"]: c.get("percent", 0) for c in json.loads(path.read_text(encoding="utf-8"))["components"]}
            break

    groups = defaultdict(list)
    for n, c in clusters.items():
        groups[c].append(n)
    inside, outside = defaultdict(float), defaultdict(float)
    for (a, b), w in weights.items():
        if clusters[a] == clusters[b]:
            inside[clusters[a]] += w
        else:
            outside[clusters[a]] += w
            outside[clusters[b]] += w
    sep = (ws.config.get("components") or {}).get("separator", ".")
    # name clusters below the prefix every component shares (com.acme., shopco., ...)
    glob = common_prefix_name(nodes, sep) if len(nodes) > 1 else []

    def rel(m):
        return m.split(sep)[len(glob):]

    suggestions, used = [], set()
    for c in sorted(groups):
        members = sorted(groups[c])
        named = [m for m in members if rel(m)] or members
        prefix = common_prefix_name([sep.join(rel(m)) for m in named], sep) if len(named) > 1 else []
        biggest = max(named, key=lambda m: (sizes.get(m, 0), m))
        base = prefix[-1] if prefix and prefix[-1] else ((rel(biggest) or biggest.split(sep))[-1])
        base = base or "domain"
        sid, i = base, 2
        while sid in used:
            sid, i = f"{base}-{i}", i + 1
        used.add(sid)
        total = inside[c] + outside[c]
        suggestions.append({
            "id": sid, "components": members,
            "size_percent": round(sum(sizes.get(m, 0) for m in members), 2) if sizes else None,
            "cohesion": round(inside[c] / total, 2) if total else None,
            "isolated": total == 0,
        })

    data = {
        "schema_version": SCHEMA_VERSION, "generated_at": now_iso(),
        "generator": {"tool": "suggest_domains.py", "method": "louvain", "resolution": args.resolution,
                      "signals": {"imports": bool(imp), "co_change": bool(cc)}, "change_weight": alpha},
        "modularity": q,
        "shared": sorted(shared),
        "suggestions": suggestions,
    }
    out = ws.phase_dir(5)
    write_json(out / "domain-suggestions.json", data)
    md = ["# Domain suggestions", "",
          f"Generated {data['generated_at']} by Louvain clustering over "
          + " + ".join(k.replace("_", "-") for k, v in data["generator"]["signals"].items() if v)
          + f" (co-change weight {alpha}). Modularity **Q = {q}** "
          + ("(clear structure)." if q >= 0.3 else "(weak structure: treat the clusters with care)."), "",
          "> A starting point for the conversation, not a domain map. Rename, merge and split with the "
          "people who know the business, then write domains.json.", "",
          "| Suggested id | Components | Size % | Cohesion |", "|---|---|---:|---:|"]
    for s in suggestions:
        md.append(f"| `{s['id']}` | {', '.join(f'`{md_escape(m)}`' for m in s['components'])} | "
                  f"{'' if s['size_percent'] is None else s['size_percent']} | "
                  f"{'isolated' if s['isolated'] else s['cohesion']} |")
    if shared:
        md += ["", "**Left out as shared code** (Phase 2 decisions or --exclude): "
               + ", ".join(f"`{x}`" for x in sorted(shared))
               + ". Give them a shared domain or assign each to its main user."]
    write_text(out / "domain-suggestions.md", "\n".join(md) + "\n")
    written = [posix(out / "domain-suggestions.json"), posix(out / "domain-suggestions.md")]
    if args.write_draft:
        draft = {"domains": [{"id": s["id"], "components": s["components"],
                              "description": "DRAFT from suggest_domains.py: rename and confirm with the user"}
                             for s in suggestions]}
        if shared:
            draft["domains"].append({"id": "shared", "components": sorted(shared),
                                     "description": "DRAFT: shared code left out of clustering"})
        write_json(out / "domains.draft.json", draft)
        written.append(posix(out / "domains.draft.json"))
    print(json.dumps({"written": written, "modularity": q, "clusters": len(suggestions),
                      "shared": sorted(shared)}, indent=2))


if __name__ == "__main__":
    main()
