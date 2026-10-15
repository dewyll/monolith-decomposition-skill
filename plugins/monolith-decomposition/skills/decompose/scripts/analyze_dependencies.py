#!/usr/bin/env python3
"""Phase 4/5: coupling metrics, cycles, matrix and graph from neutral edges.

Input edges can come from extract_dependencies.py or from any language-native
tool converted to the neutral format (see schemas/edges.schema.json):

  {"generator": {"tool": "...", "confidence": "high"},
   "edges": [{"from": "billing", "to": "shipping", "weight": 3}]}

Per component it computes:
  ca  afferent coupling   (distinct components that depend on it)
  ce  efferent coupling   (distinct components it depends on)
  instability  ce / (ca + ce)   0 = stable, 1 = unstable
and for the whole graph: strongly connected components (cycles), density,
the share of components caught in cycles, and a feasibility hint.

With --domains it also aggregates edges to domain level and reports
cohesion (share of a domain's references that stay inside the domain).

Usage:
  python3 analyze_dependencies.py --workspace decomposition \
      [--edges 04-dependencies/edges.json] [--components ...] [--domains 05-domains/domains.json]
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (SCHEMA_VERSION, Workspace, md_escape, mean_stddev, now_iso,  # noqa: E402
                    posix, write_json, write_text)


def tarjan(nodes, adj):
    """Iterative Tarjan SCC. Returns list of SCCs (lists of nodes)."""
    index, low, on_stack, stack, result = {}, {}, set(), [], []
    counter = 0
    for root in nodes:
        if root in index:
            continue
        work = [(root, iter(adj.get(root, ())))]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        while work:
            node, it = work[-1]
            advanced = False
            for nxt in it:
                if nxt not in index:
                    index[nxt] = low[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(adj.get(nxt, ()))))
                    advanced = True
                    break
                if nxt in on_stack:
                    low[node] = min(low[node], index[nxt])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                low[parent] = min(low[parent], low[node])
            if low[node] == index[node]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    scc.append(w)
                    if w == node:
                        break
                result.append(sorted(scc))
    return result


def mermaid_id(name: str) -> str:
    return "n_" + "".join(ch if ch.isalnum() else "_" for ch in name)


def analyse(nodes, edges, generator, allowed_cycles, max_ce):
    adj = defaultdict(set)
    weights = {}
    for e in edges:
        if e["from"] == e["to"]:
            continue
        adj[e["from"]].add(e["to"])
        weights[(e["from"], e["to"])] = weights.get((e["from"], e["to"]), 0) + int(e.get("weight", 1))
    nodes = sorted(set(nodes) | {e["from"] for e in edges} | {e["to"] for e in edges})
    inc = defaultdict(set)
    for s, ds in adj.items():
        for d in ds:
            inc[d].add(s)
    sccs = [s for s in tarjan(nodes, adj) if len(s) > 1]
    allowed = [sorted(c) for c in (allowed_cycles or [])]
    cyc_members = {n for s in sccs for n in s}
    metrics = []
    for n in nodes:
        ca, ce = len(inc[n]), len(adj[n])
        metrics.append({
            "id": n, "ca": ca, "ce": ce,
            "instability": round(ce / (ca + ce), 2) if (ca + ce) else None,
            "weighted_in": sum(weights.get((s, n), 0) for s in inc[n]),
            "weighted_out": sum(weights.get((n, d), 0) for d in adj[n]),
            "in_cycle": n in cyc_members,
            "over_max_ce": max_ce is not None and ce > int(max_ce),
        })
    n = len(nodes)
    m_ce, sd_ce = mean_stddev([x["ce"] for x in metrics])
    cyc_share = round(len(cyc_members) / n, 2) if n else 0.0
    density = round(len(weights) / (n * (n - 1)), 3) if n > 1 else 0.0
    if cyc_share > 0.3 or density > 0.25:
        hint = "high"
    elif cyc_share > 0.1 or density > 0.1:
        hint = "medium"
    else:
        hint = "low"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "generator": generator,
        "summary": {
            "components": n, "edges": len(weights), "density": density,
            "mean_ce": round(m_ce, 2), "stddev_ce": round(sd_ce, 2),
            "cycles": len(sccs), "components_in_cycles": len(cyc_members),
            "share_in_cycles": cyc_share,
            "coupling_level_hint": hint,
        },
        "cycles": [{"members": s, "allowed": s in allowed} for s in sccs],
        "components": sorted(metrics, key=lambda x: (-(x["ca"] + x["ce"]), x["id"])),
        "edges": [{"from": s, "to": d, "weight": w} for (s, d), w in sorted(weights.items())],
    }


def render_md(data, title, max_matrix=40):
    s = data["summary"]
    g = data["generator"]
    lines = [
        f"# {title}", "",
        f"Generated {data['generated_at']} from `{g.get('tool', '?')}` "
        f"(confidence: **{g.get('confidence', 'unknown')}**).", "",
        f"- Nodes: **{s['components']}** · edges: **{s['edges']}** · density: {s['density']}",
        f"- Mean efferent coupling: {s['mean_ce']} (σ {s['stddev_ce']})",
        f"- Cycles: **{s['cycles']}** involving {s['components_in_cycles']} node(s) "
        f"({int(s['share_in_cycles'] * 100)}%)",
        f"- Coupling level (heuristic): **{s['coupling_level_hint']}**", "",
    ]
    if g.get("confidence") == "low":
        lines += ["> Edges come from static import scanning. Dependency injection, events, reflection "
                  "and shared tables are not visible, so real coupling is likely higher.", ""]
    lines += ["## Most coupled", "", "| Node | Ca (in) | Ce (out) | Instability | In cycle |",
              "|---|---:|---:|---:|---|"]
    for c in data["components"][:30]:
        lines.append(f"| `{md_escape(c['id'])}` | {c['ca']} | {c['ce']} | "
                     f"{'' if c['instability'] is None else c['instability']} | "
                     f"{'yes' if c['in_cycle'] else ''} |")
    if data["cycles"]:
        lines += ["", "## Cycles", ""]
        for i, cyc in enumerate(data["cycles"], 1):
            mark = " (allowed by config)" if cyc["allowed"] else ""
            lines.append(f"{i}. {', '.join('`'+m+'`' for m in cyc['members'])}{mark}")
    ids = [c["id"] for c in sorted(data["components"], key=lambda c: c["id"])]
    if 1 < len(ids) <= max_matrix:
        w = {(e["from"], e["to"]): e["weight"] for e in data["edges"]}
        short = {cid: f"C{i+1}" for i, cid in enumerate(ids)}
        lines += ["", "## Dependency matrix", "",
                  "Rows depend on columns; numbers are the count of referencing files.", "",
                  "| | " + " | ".join(short[c] for c in ids) + " |",
                  "|---|" + "---:|" * len(ids)]
        for r in ids:
            lines.append(f"| **{short[r]}** | " + " | ".join(
                ("·" if r == c else str(w.get((r, c), ""))) for c in ids) + " |")
        lines += ["", "Legend: " + " · ".join(f"{short[c]} = `{md_escape(c)}`" for c in ids)]
    else:
        lines += ["", "## Heaviest edges", "", "| From | To | Weight |", "|---|---|---:|"]
        for e in sorted(data["edges"], key=lambda e: -e["weight"])[:40]:
            lines.append(f"| `{md_escape(e['from'])}` | `{md_escape(e['to'])}` | {e['weight']} |")
    return "\n".join(lines) + "\n"


def render_mermaid(data, max_nodes=80):
    nodes = [c["id"] for c in data["components"]]
    if len(nodes) > max_nodes:
        return f"%% {len(nodes)} nodes: too many to draw. Use the domain-level graph instead.\n"
    lines = ["graph LR"]
    for n in nodes:
        lines.append(f'  {mermaid_id(n)}["{n}"]')
    for e in data["edges"]:
        lines.append(f"  {mermaid_id(e['from'])} -->|{e['weight']}| {mermaid_id(e['to'])}")
    cyc = sorted({m for c in data["cycles"] for m in c["members"]})
    if cyc:
        lines.append("  classDef cycle stroke:#d9534f,stroke-width:3px")
        lines.append("  class " + ",".join(mermaid_id(m) for m in cyc) + " cycle")
    return "\n".join(lines) + "\n"


def domain_level(comp_data, domains, internal_refs):
    owner = {}
    for d in domains["domains"]:
        for c in d.get("components", []):
            owner[c] = d["id"]
    agg = defaultdict(int)
    intra = defaultdict(int)
    for cid, n in (internal_refs or {}).items():
        if cid in owner:
            intra[owner[cid]] += n
    unmapped = set()
    for e in comp_data["edges"]:
        a, b = owner.get(e["from"]), owner.get(e["to"])
        if a is None:
            unmapped.add(e["from"])
        if b is None:
            unmapped.add(e["to"])
        if a is None or b is None:
            continue
        if a == b:
            intra[a] += e["weight"]
        else:
            agg[(a, b)] += e["weight"]
    edges = [{"from": a, "to": b, "weight": w} for (a, b), w in agg.items()]
    out = defaultdict(int)
    inn = defaultdict(int)
    for (a, b), w in agg.items():
        out[a] += w
        inn[b] += w
    cohesion = {}
    for d in domains["domains"]:
        total = intra[d["id"]] + out[d["id"]]
        cohesion[d["id"]] = round(intra[d["id"]] / total, 2) if total else None
    return edges, cohesion, sorted(unmapped), dict(intra)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--edges")
    ap.add_argument("--components")
    ap.add_argument("--domains")
    ap.add_argument("--out-dir")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    edges_path = Path(args.edges) if args.edges else ws.artifact(4, "edges.json")
    if not edges_path.exists():
        sys.exit(f"error: {edges_path} not found. Run extract_dependencies.py or convert a native tool's output.")
    edges_doc = json.loads(edges_path.read_text(encoding="utf-8"))
    comp_path = Path(args.components) if args.components else next(
        (p for p in [ws.artifact(3, "components.json"), ws.artifact(1, "components.json")] if p.exists()),
        None)
    nodes = []
    if comp_path and comp_path.exists():
        nodes = [c["id"] for c in json.loads(comp_path.read_text(encoding="utf-8"))["components"]]

    th = ws.thresholds()
    generator = edges_doc.get("generator", {"tool": "external", "confidence": "unknown"})
    data = analyse(nodes, edges_doc.get("edges", []), generator,
                   ws.fitness().get("allowed_cycles"), th.get("max_efferent_coupling"))
    data["internal_references"] = edges_doc.get("internal_references", {})
    out_dir = Path(args.out_dir) if args.out_dir else ws.phase_dir(4)
    write_json(out_dir / "dependencies.json", data)
    write_text(out_dir / "dependencies.md", render_md(data, "Component dependencies"))
    write_text(out_dir / "dependencies.mmd", render_mermaid(data))
    written = [posix(out_dir / f) for f in ("dependencies.json", "dependencies.md", "dependencies.mmd")]

    if args.domains:
        domains = json.loads(Path(args.domains).read_text(encoding="utf-8"))
        d_edges, cohesion, unmapped, intra = domain_level(data, domains, data["internal_references"])
        ddata = analyse([d["id"] for d in domains["domains"]], d_edges, generator,
                        ws.fitness().get("allowed_cycles"), None)
        ddata["cohesion"] = cohesion
        ddata["intra_domain_references"] = intra
        ddata["unmapped_components"] = unmapped
        ddir = Path(args.domains).resolve().parent
        md = render_md(ddata, "Domain coupling")
        md += "\n## Cohesion\n\nShare of each domain's references that stay inside it.\n\n" \
              "| Domain | Cohesion |\n|---|---:|\n" + "".join(
                  f"| `{d}` | {'' if v is None else v} |\n" for d, v in sorted(cohesion.items()))
        if unmapped:
            md += "\n**Components without a domain:** " + ", ".join(f"`{u}`" for u in unmapped) + "\n"
        write_json(ddir / "domain-coupling.json", ddata)
        write_text(ddir / "domain-coupling.md", md)
        write_text(ddir / "domain-coupling.mmd", render_mermaid(ddata))
        written += [posix(ddir / f) for f in ("domain-coupling.json", "domain-coupling.md",
                                               "domain-coupling.mmd")]

    print(json.dumps({"written": written, "summary": data["summary"]}, indent=2))


if __name__ == "__main__":
    main()
