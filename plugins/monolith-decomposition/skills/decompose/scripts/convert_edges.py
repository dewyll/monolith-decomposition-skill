#!/usr/bin/env python3
"""Turn a native tool's dependency output into the neutral edges.json.

Most extractors can be reduced to a two-column list with one `jq`/shell
line (the adapters show how). This script maps those pairs to component
ids with the workspace's own rules and aggregates them.

Input: a TSV file (or stdin with "-"), one dependency per line:

  <from>\t<to>

where both columns are either
  --kind files       file paths relative to the project root
  --kind namespaces  package / module / namespace names (com.acme.billing,
                     github.com/acme/app/internal/billing, Acme\\Billing)

Lines whose target maps to no component (external libraries) are ignored.

Usage:
  depcruise src -T json | jq -r '.modules[] | .source as $s | .dependencies[] | [$s, .resolved] | @tsv' \
    | python3 convert_edges.py --workspace decomposition --kind files --tool dependency-cruiser -
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import SCHEMA_VERSION, Workspace, now_iso, posix, write_json  # noqa: E402
from extract_dependencies import Resolver  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="TSV file, or - for stdin")
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--kind", choices=["files", "namespaces"], required=True)
    ap.add_argument("--tool", required=True, help="name of the tool that produced the pairs")
    ap.add_argument("--confidence", default="high", choices=["high", "medium", "low"])
    ap.add_argument("--components")
    ap.add_argument("--out")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    comp_path = Path(args.components) if args.components else next(
        (p for p in [ws.artifact(3, "components.json"), ws.artifact(1, "components.json")] if p.exists()),
        None)
    if comp_path is None:
        sys.exit("error: no components.json yet. Run size_components.py first.")
    components = json.loads(comp_path.read_text(encoding="utf-8"))
    res = Resolver(ws, components)

    def to_component(value: str):
        value = value.strip()
        if args.kind == "files":
            p = Path(value)
            if p.is_absolute():
                try:
                    value = posix(p.resolve().relative_to(ws.project_root))
                except ValueError:
                    return None
            value = value[2:] if value.startswith("./") else value
            mapped = res.mapper.map(value)
            return mapped[0] if mapped else res.by_path(value.rsplit(".", 1)[0])
        return res.by_ns(value)

    stream = sys.stdin if args.input == "-" else open(args.input, encoding="utf-8")
    pairs = defaultdict(set)   # (from comp, to comp) -> set of source items
    internal = defaultdict(int)
    total = mapped = 0
    for line in stream:
        if not line.strip() or "\t" not in line:
            continue
        a, b = line.rstrip("\n").split("\t", 1)
        total += 1
        ca, cb = to_component(a), to_component(b)
        if not ca or not cb:
            continue
        mapped += 1
        if ca == cb:
            internal[ca] += 1
        else:
            pairs[(ca, cb)].add(a)

    out = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "generator": {"tool": args.tool, "method": f"converted-{args.kind}", "confidence": args.confidence},
        "components_source": posix(os.path.relpath(Path(comp_path).resolve(), ws.dir)),
        "stats": {"pairs": total, "mapped": mapped},
        "internal_references": dict(sorted(internal.items())),
        "edges": [{"from": s, "to": d, "weight": len(srcs), "kinds": ["static"],
                   "samples": sorted(srcs)[:5]} for (s, d), srcs in sorted(pairs.items())],
    }
    dest = Path(args.out) if args.out else ws.artifact(4, "edges.json")
    write_json(dest, out)
    print(json.dumps({"written": posix(dest), "edges": len(out["edges"]), **out["stats"]}, indent=2))


if __name__ == "__main__":
    main()
