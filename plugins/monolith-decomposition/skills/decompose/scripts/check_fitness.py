#!/usr/bin/env python3
"""Tool-agnostic fitness functions over the decomposition artifacts.

These checks work for every language because they only read the neutral
JSON artifacts. Each phase adds guards; `--phase guard` runs the ones that
should keep running in CI after the migration starts (see
references/fitness-functions.md for wiring it into a pipeline).

  F1.1  every source file belongs to a component                (warn)
  F1.2  no component above thresholds.max_component_percent     (fail)
  F1.3  size outliers are allow-listed with a justification     (warn)
  F2.1  every common-domain candidate has a recorded decision   (fail)
  F3.1  no root namespace with code (orphaned files)            (fail)
  F4.1  no dependency cycles except fitness.allowed_cycles      (fail)
  F4.2  efferent coupling <= thresholds.max_efferent_coupling   (fail)
  F4.3  dependency data has better than "low" confidence        (warn)
  F5.1  every component belongs to exactly one domain           (fail)
  F5.2  domains only reference known components                 (fail)
  F5.3  domain cohesion >= thresholds.min_domain_cohesion       (warn)
  F5.4  no forbidden dependencies (fitness.forbidden_dependencies) (fail)
  F6.1  every domain belongs to exactly one service             (fail)
  F6.2  cross-service dependencies are declared as interfaces   (fail)

Usage:
  python3 check_fitness.py --workspace decomposition --phase 1|2|3|4|5|6|all|guard [--strict]
Exit code 1 when any check fails.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Workspace, md_escape, now_iso, posix, write_json, write_text  # noqa: E402

PASS, FAIL, WARN, SKIP = "PASS", "FAIL", "WARN", "SKIP"


class Checker:
    def __init__(self, ws: Workspace):
        self.ws = ws
        self.results = []

    def add(self, cid, status, message, details=None):
        self.results.append({"id": cid, "status": status, "message": message, "details": details or []})

    def load(self, phase, name):
        p = self.ws.artifact(phase, name)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def latest_components(self):
        return self.load(3, "components.json") or self.load(1, "components.json")

    # ---------------------------------------------------------------- phase 1
    def phase1(self):
        comps = self.latest_components()
        if not comps:
            for c in ("F1.1", "F1.2", "F1.3"):
                self.add(c, SKIP, "components.json not found")
            return
        n = comps.get("unassigned_count", 0)
        self.add("F1.1", PASS if n == 0 else WARN,
                 "all source files mapped to a component" if n == 0 else f"{n} file(s) not mapped",
                 comps.get("unassigned_files", [])[:20])
        allow = self.ws.fitness().get("size_allowlist") or {}
        over = [c for c in comps["components"] if "over-max" in c["flags"] and c["id"] not in allow]
        self.add("F1.2", FAIL if over else PASS,
                 f"{len(over)} component(s) above the max share" if over else "no component above the max share",
                 [f"{c['id']}: {c['percent']}%" for c in over])
        outl = [c for c in comps["components"]
                if ({"large", "small"} & set(c["flags"])) and c["id"] not in allow]
        self.add("F1.3", WARN if outl else PASS,
                 f"{len(outl)} size outlier(s) without justification" if outl
                 else "every size outlier is justified",
                 [f"{c['id']}: z={c['z_score']}" for c in outl])

    # ---------------------------------------------------------------- phase 2
    def phase2(self):
        cands = self.load(2, "candidates.json")
        if not cands:
            self.add("F2.1", SKIP, "candidates.json not found")
            return
        decisions = self.load(2, "common-domain.json") or {"decisions": []}
        decided = {d["component"] for d in decisions.get("decisions", []) if d.get("decision")}
        missing = [c["component"] for c in cands["candidates"] if c["component"] not in decided]
        self.add("F2.1", FAIL if missing else PASS,
                 f"{len(missing)} candidate(s) without a decision" if missing
                 else "every candidate has a decision", missing)

    # ---------------------------------------------------------------- phase 3
    def phase3(self):
        comps = self.latest_components()
        if not comps:
            self.add("F3.1", SKIP, "components.json not found")
            return
        allow = self.ws.fitness().get("orphan_allowlist") or {}
        bad = [c for c in comps["components"] if "root-with-code" in c["flags"] and c["id"] not in allow]
        self.add("F3.1", FAIL if bad else PASS,
                 f"{len(bad)} root namespace(s) still hold code" if bad else "no orphaned files in root namespaces",
                 [f"{c['id']}: {c['orphan_files']} file(s)" for c in bad])

    # ---------------------------------------------------------------- phase 4
    def phase4(self):
        deps = self.load(4, "dependencies.json")
        if not deps:
            for c in ("F4.1", "F4.2", "F4.3"):
                self.add(c, SKIP, "dependencies.json not found")
            return
        cyc = [c["members"] for c in deps["cycles"] if not c["allowed"]]
        self.add("F4.1", FAIL if cyc else PASS,
                 f"{len(cyc)} dependency cycle(s)" if cyc else "no dependency cycles",
                 [" <-> ".join(c) for c in cyc])
        max_ce = self.ws.thresholds().get("max_efferent_coupling")
        if max_ce is None:
            self.add("F4.2", SKIP, "thresholds.max_efferent_coupling not set")
        else:
            over = [c for c in deps["components"] if c["ce"] > int(max_ce)]
            self.add("F4.2", FAIL if over else PASS,
                     f"{len(over)} component(s) with Ce > {max_ce}" if over else f"all Ce <= {max_ce}",
                     [f"{c['id']}: Ce={c['ce']}" for c in over])
        conf = deps.get("generator", {}).get("confidence", "unknown")
        self.add("F4.3", WARN if conf in ("low", "unknown") else PASS,
                 f"dependency data confidence: {conf}")

    # ---------------------------------------------------------------- phase 5
    def phase5(self):
        doms = self.load(5, "domains.json")
        comps = self.latest_components()
        if not doms or not comps:
            for c in ("F5.1", "F5.2", "F5.3"):
                self.add(c, SKIP, "domains.json or components.json not found")
        else:
            known = {c["id"] for c in comps["components"]}
            counts = Counter(c for d in doms["domains"] for c in d.get("components", []))
            missing = sorted(known - set(counts))
            dup = sorted(c for c, n in counts.items() if n > 1)
            self.add("F5.1", FAIL if (missing or dup) else PASS,
                     "every component in exactly one domain" if not (missing or dup)
                     else f"{len(missing)} without a domain, {len(dup)} in several domains",
                     [f"no domain: {m}" for m in missing] + [f"several domains: {d}" for d in dup])
            unknown = sorted(set(counts) - known)
            self.add("F5.2", FAIL if unknown else PASS,
                     f"{len(unknown)} unknown component id(s)" if unknown else "all ids known", unknown)
            dc = self.load(5, "domain-coupling.json")
            minc = self.ws.thresholds().get("min_domain_cohesion")
            if not dc or minc is None:
                self.add("F5.3", SKIP, "domain-coupling.json or thresholds.min_domain_cohesion missing")
            else:
                low = [f"{d}: {v}" for d, v in dc.get("cohesion", {}).items() if v is not None and v < float(minc)]
                self.add("F5.3", WARN if low else PASS,
                         f"{len(low)} domain(s) below cohesion {minc}" if low else f"cohesion >= {minc}", low)
        self.forbidden()

    def forbidden(self):
        rules = self.ws.fitness().get("forbidden_dependencies") or []
        if not rules:
            self.add("F5.4", SKIP, "no forbidden_dependencies configured")
            return
        deps = self.load(4, "dependencies.json")
        dc = self.load(5, "domain-coupling.json")
        comp_edges = {(e["from"], e["to"]) for e in (deps or {}).get("edges", [])}
        dom_edges = {(e["from"], e["to"]) for e in (dc or {}).get("edges", [])}
        hits = []
        for r in rules:
            edges = dom_edges if r.get("level", "domain") == "domain" else comp_edges
            for (a, b) in edges:
                if (a == r["from"] or (r["from"] == "*")) and (b == r["to"] or r["to"] == "*") and a != b:
                    hits.append(f"{a} -> {b}" + (f" (RFC {r['rfc']})" if r.get("rfc") else ""))
        self.add("F5.4", FAIL if hits else PASS,
                 f"{len(hits)} forbidden dependency(ies) present" if hits else "no forbidden dependencies", hits)

    # ---------------------------------------------------------------- phase 6
    def phase6(self):
        svcs = self.load(6, "services.json")
        doms = self.load(5, "domains.json")
        if not svcs or not doms:
            for c in ("F6.1", "F6.2"):
                self.add(c, SKIP, "services.json or domains.json not found")
            return
        known = {d["id"] for d in doms["domains"]}
        counts = Counter(d for s in svcs["services"] for d in s.get("domains", []))
        missing = sorted(known - set(counts))
        dup = sorted(d for d, n in counts.items() if n > 1)
        self.add("F6.1", FAIL if (missing or dup) else PASS,
                 "every domain in exactly one service" if not (missing or dup)
                 else f"{len(missing)} domain(s) without a service, {len(dup)} in several",
                 [f"no service: {m}" for m in missing] + [f"several services: {d}" for d in dup])
        dc = self.load(5, "domain-coupling.json")
        if not dc:
            self.add("F6.2", SKIP, "domain-coupling.json not found (run analyze_dependencies.py --domains)")
            return
        owner = {d: s["id"] for s in svcs["services"] for d in s.get("domains", [])}
        declared = {(s["id"], i["to"]) for s in svcs["services"] for i in s.get("interfaces", [])}
        undeclared = sorted({(owner.get(e["from"]), owner.get(e["to"])) for e in dc["edges"]
                             if owner.get(e["from"]) and owner.get(e["to"])
                             and owner[e["from"]] != owner[e["to"]]} - declared)
        self.add("F6.2", FAIL if undeclared else PASS,
                 f"{len(undeclared)} undeclared cross-service dependency(ies)" if undeclared
                 else "every cross-service dependency is declared",
                 [f"{a} -> {b}" for a, b in undeclared])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--phase", default="all")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    ch = Checker(ws)
    plan = {
        "1": [ch.phase1], "2": [ch.phase2], "3": [ch.phase3], "4": [ch.phase4],
        "5": [ch.phase5], "6": [ch.phase6],
        "all": [ch.phase1, ch.phase2, ch.phase3, ch.phase4, ch.phase5, ch.phase6],
        # what keeps running in CI once boundaries are agreed
        "guard": [ch.phase1, ch.phase3, ch.phase4, ch.phase5, ch.phase6],
    }
    if args.phase not in plan:
        sys.exit(f"error: unknown phase {args.phase}")
    for fn in plan[args.phase]:
        fn()

    if args.strict:
        for r in ch.results:
            if r["status"] == WARN:
                r["status"] = FAIL
    failed = [r for r in ch.results if r["status"] == FAIL]
    out = {"generated_at": now_iso(), "phase": args.phase, "strict": args.strict,
           "passed": not failed, "results": ch.results}
    dest = ws.fitness_dir / f"results-{args.phase}.json"
    write_json(dest, out)
    md = [f"# Fitness functions: phase {args.phase}", "", f"Run {out['generated_at']}. "
          f"Result: **{'PASS' if not failed else 'FAIL'}**", "",
          "| Check | Status | Result |", "|---|---|---|"]
    for r in ch.results:
        md.append(f"| {r['id']} | {r['status']} | {md_escape(r['message'])} |")
    write_text(ws.fitness_dir / f"results-{args.phase}.md", "\n".join(md) + "\n")

    for r in ch.results:
        print(f"[{r['status']:4}] {r['id']}  {r['message']}")
        for d in r["details"][:10]:
            print(f"         - {d}")
        if len(r["details"]) > 10:
            print(f"         … {len(r['details']) - 10} more")
    print(f"\nwritten: {posix(dest)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
