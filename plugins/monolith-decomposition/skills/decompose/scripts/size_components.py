#!/usr/bin/env python3
"""Phase 1/3: identify components and measure their size.

Maps every source file to a component (see config.components), measures
size, and flags components that deserve attention:

  * large / small   size is more than k standard deviations from the mean
  * over-max        size exceeds thresholds.max_component_percent of the codebase
  * root-with-code  the component has sub-components *and* code of its own
                    (orphaned files that Phase 3 should flatten)

Size metric: logical lines of code (non-blank, non-comment). If `scc` is
installed and metrics.size is "auto" or "scc", scc's per-file Code count and
complexity are used instead. Any other tool can feed sizes through
--from-json (see schemas/components.schema.json, "raw input" section).

Usage:
  python3 size_components.py --workspace decomposition [--out-dir 01-sizing]
  python3 size_components.py --workspace decomposition --from-json raw.json
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (C_STYLE, HASH_STYLE, LANGUAGES, LUA_STYLE, RUBY_STYLE,  # noqa: E402
                    SCHEMA_VERSION, ComponentMapper, Workspace, iter_source_files,
                    md_escape, mean_stddev, now_iso, posix, write_json, write_text)


# --------------------------------------------------------------------------
# Built-in logical-line counter
# --------------------------------------------------------------------------
def count_lloc(path: Path, style: str) -> int:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    count, in_block = 0, False
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if style == C_STYLE:
            if in_block:
                if "*/" in line:
                    in_block = False
                    rest = line.split("*/", 1)[1].strip()
                    if rest and not rest.startswith("//"):
                        count += 1
                continue
            if line.startswith("//"):
                continue
            if line.startswith("/*"):
                if "*/" not in line[2:]:
                    in_block = True
                    continue
                rest = line.split("*/", 1)[1].strip()
                if not rest or rest.startswith("//"):
                    continue
            count += 1
        elif style == HASH_STYLE:
            if not line.startswith("#"):
                count += 1
        elif style == RUBY_STYLE:
            if line.startswith("=begin"):
                in_block = True
                continue
            if in_block:
                if line.startswith("=end"):
                    in_block = False
                continue
            if not line.startswith("#"):
                count += 1
        elif style == LUA_STYLE:
            if not line.startswith("--"):
                count += 1
        else:
            count += 1
    return count


def scc_sizes(project_root: Path) -> dict:
    """Return {relative path: (code, complexity)} using scc, or {} on failure."""
    exe = shutil.which("scc")
    if not exe:
        return {}
    try:
        out = subprocess.run([exe, "--by-file", "--format", "json", "."], cwd=project_root,
                             capture_output=True, text=True, check=True, timeout=900).stdout
        data = json.loads(out)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        print(f"warning: scc failed ({exc}); falling back to built-in counter", file=sys.stderr)
        return {}
    sizes = {}
    for lang in data:
        for f in lang.get("Files") or []:
            loc = posix(f.get("Location", "")).lstrip("./") if f.get("Location", "").startswith("./") \
                else posix(f.get("Location", ""))
            sizes[loc] = (int(f.get("Code", 0)), int(f.get("Complexity", 0)))
    return sizes


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------
def analyse(raw_components: list, unassigned: list, ws: Workspace, generator: dict) -> dict:
    th = ws.thresholds()
    k = float(th.get("size_outlier_stddev") or 1.0)
    max_pct = th.get("max_component_percent")
    total = sum(c["size"] for c in raw_components) or 1
    m, sd = mean_stddev([c["size"] for c in raw_components])

    paths = {c["id"]: c.get("path", "") for c in raw_components}
    result = []
    for c in raw_components:
        pct = round(100.0 * c["size"] / total, 2)
        z = round((c["size"] - m) / sd, 2) if sd else 0.0
        children = sorted(
            other for other, p in paths.items()
            if other != c["id"] and c.get("path") not in (None, "", ".")
            and p.startswith(c["path"] + "/")
        ) if c.get("path") else []
        if c.get("path") in (".",):
            children = sorted(o for o in paths if o != c["id"])
        flags = []
        if sd and z > k:
            flags.append("large")
        if sd and z < -k:
            flags.append("small")
        if max_pct is not None and pct > float(max_pct):
            flags.append("over-max")
        if children and c["files"] > 0:
            flags.append("root-with-code")
        entry = {
            "id": c["id"],
            "path": c.get("path"),
            "language": c.get("language"),
            "files": c["files"],
            "size": c["size"],
            "percent": pct,
            "z_score": z,
            "complexity": c.get("complexity"),
            "children": children,
            "orphan_files": c["files"] if "root-with-code" in flags else 0,
            "flags": flags,
        }
        if "root-with-code" in flags and c.get("file_list"):
            entry["orphan_file_paths"] = c["file_list"][:200]
        result.append(entry)
    result.sort(key=lambda e: (-e["size"], e["id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "generator": generator,
        "parameters": {"size_outlier_stddev": k, "max_component_percent": max_pct},
        "totals": {"components": len(result), "files": sum(e["files"] for e in result),
                   "size": sum(e["size"] for e in result)},
        "stats": {"mean": round(m, 2), "stddev": round(sd, 2)},
        "components": result,
        "unassigned_files": unassigned[:500],
        "unassigned_count": len(unassigned),
    }


def render_markdown(data: dict) -> str:
    g = data["generator"]
    lines = [
        "# Component inventory",
        "",
        f"Generated {data['generated_at']} by `{g['tool']}` (metric: {g['metric']}, "
        f"confidence: {g['confidence']}).",
        "",
        f"- Components: **{data['totals']['components']}**",
        f"- Files: **{data['totals']['files']}**",
        f"- Total size: **{data['totals']['size']}**",
        f"- Mean size: {data['stats']['mean']} · standard deviation: {data['stats']['stddev']}",
        f"- Outlier rule: |z| > {data['parameters']['size_outlier_stddev']}; "
        f"max share per component: {data['parameters']['max_component_percent']}%",
        f"- Unassigned files: {data['unassigned_count']}",
        "",
        "| Component | Files | Size | % of total | z | Flags |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for c in data["components"]:
        lines.append(f"| `{md_escape(c['id'])}` | {c['files']} | {c['size']} | {c['percent']} | "
                     f"{c['z_score']} | {', '.join(c['flags'])} |")
    flagged = [c for c in data["components"] if "root-with-code" in c["flags"]]
    if flagged:
        lines += ["", "## Root namespaces with code (Phase 3 input)", ""]
        for c in flagged:
            lines.append(f"- `{c['id']}`: {c['orphan_files']} orphaned file(s); "
                         f"sub-components: {', '.join('`'+x+'`' for x in c['children'][:10])}"
                         + (" …" if len(c["children"]) > 10 else ""))
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--out-dir", default=None,
                    help="phase folder to write into (default: 01-sizing; use 03-flattening "
                         "to re-measure after flattening)")
    ap.add_argument("--from-json", help="raw component sizes produced by another tool")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    out_dir = ws.dir / (args.out_dir or ws.PHASE_DIRS[1])

    if args.from_json:
        raw = json.loads(Path(args.from_json).read_text(encoding="utf-8"))
        comps = [{"id": c["id"], "path": c.get("path"), "language": c.get("language"),
                  "files": int(c.get("files", 0)), "size": int(c["size"]),
                  "complexity": c.get("complexity"), "file_list": c.get("file_list")}
                 for c in raw["components"]]
        generator = {"tool": raw.get("tool", "external"), "metric": raw.get("metric", "external"),
                     "confidence": raw.get("confidence", "high")}
        data = analyse(comps, raw.get("unassigned_files", []), ws, generator)
    else:
        mapper = ComponentMapper(ws.config)
        mode = (ws.config.get("metrics") or {}).get("size", "auto")
        sccmap = scc_sizes(ws.project_root) if mode in ("auto", "scc") else {}
        if mode == "scc" and not sccmap:
            print("warning: metrics.size is 'scc' but scc is unavailable", file=sys.stderr)
        agg = defaultdict(lambda: {"files": 0, "size": 0, "complexity": 0, "langs": defaultdict(int),
                                   "file_list": [], "path": None})
        unassigned = []
        for rel, lang in iter_source_files(ws.project_root, ws.config):
            mapped = mapper.map(rel)
            if not mapped:
                unassigned.append(rel)
                continue
            cid, cpath = mapped
            if rel in sccmap:
                size, cx = sccmap[rel]
            else:
                style = LANGUAGES[Path(rel).suffix.lower()][1]
                size, cx = count_lloc(ws.project_root / rel, style), 0
            a = agg[cid]
            a["path"] = cpath
            a["files"] += 1
            a["size"] += size
            a["complexity"] += cx
            a["langs"][lang] += size or 1
            a["file_list"].append(rel)
        comps = [{"id": cid, "path": a["path"], "files": a["files"], "size": a["size"],
                  "complexity": a["complexity"] if sccmap else None,
                  "language": max(a["langs"], key=a["langs"].get) if a["langs"] else None,
                  "file_list": a["file_list"]}
                 for cid, a in agg.items()]
        generator = {"tool": "size_components.py",
                     "metric": "scc-code-lines" if sccmap else "logical-lines",
                     "confidence": "high"}
        data = analyse(comps, unassigned, ws, generator)

    write_json(out_dir / "components.json", data)
    write_text(out_dir / "components.md", render_markdown(data))
    flagged = {f: sum(1 for c in data["components"] if f in c["flags"])
               for f in ("large", "small", "over-max", "root-with-code")}
    print(json.dumps({"written": [posix(out_dir / "components.json"), posix(out_dir / "components.md")],
                      "components": data["totals"]["components"], "flags": flagged,
                      "unassigned": data["unassigned_count"]}, indent=2))


if __name__ == "__main__":
    main()
