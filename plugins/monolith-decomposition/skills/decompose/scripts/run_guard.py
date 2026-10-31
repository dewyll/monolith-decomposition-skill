#!/usr/bin/env python3
"""One-command architecture guard for CI: regenerate the artifacts, then check them.

Checking committed artifacts proves nothing about the code in a pull
request, so this script re-measures first and only then runs the guard
set of fitness functions (with the baseline ratchet when one exists):

  1. size_components.py   into 03-flattening/ when that phase produced an
                          inventory, otherwise into 01-sizing/
  2. extract_dependencies.py  (skip with --skip-extract when a native
                          extractor already wrote 04-dependencies/edges.json
                          in an earlier CI step)
  3. analyze_dependencies.py  (+ dependencies.extra_edges from config, and
                          --domains when 05-domains/domains.json exists)
  4. check_fitness.py --phase guard

It rewrites artifacts in the workspace. In CI that is what you want; on a
laptop, review or discard the diff afterwards.

Usage:
  python3 run_guard.py --workspace decomposition [--skip-extract] [--strict] [--no-baseline]
Exit code is the one from check_fitness.py (1 when a check fails).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import Workspace  # noqa: E402


def step(name: str, *args: str) -> None:
    print(f"$ {name} {' '.join(args)}", flush=True)
    proc = subprocess.run([sys.executable, str(HERE / name), *args],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.stderr.strip():
        print(proc.stderr.rstrip(), file=sys.stderr)
    if proc.returncode != 0:
        sys.exit(f"error: {name} failed with exit code {proc.returncode}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--skip-extract", action="store_true",
                    help="keep the existing 04-dependencies/edges.json (native extractor ran before)")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failures")
    ap.add_argument("--no-baseline", action="store_true", help="absolute checks only")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    w = str(ws.dir)
    sizing = ws.phase_dir(3) if ws.artifact(3, "components.json").exists() else ws.phase_dir(1)
    step("size_components.py", "--workspace", w, "--out-dir", str(sizing))
    if not args.skip_extract:
        step("extract_dependencies.py", "--workspace", w)
    elif not ws.artifact(4, "edges.json").exists():
        sys.exit("error: --skip-extract given but 04-dependencies/edges.json does not exist")
    analyze = ["--workspace", w]
    domains = ws.artifact(5, "domains.json")
    if domains.exists():
        analyze += ["--domains", str(domains)]
    step("analyze_dependencies.py", *analyze)

    check = [sys.executable, str(HERE / "check_fitness.py"), "--workspace", w, "--phase", "guard"]
    if args.strict:
        check.append("--strict")
    if args.no_baseline:
        check.append("--no-baseline")
    print(f"$ check_fitness.py {' '.join(check[2:])}\n", flush=True)
    sys.exit(subprocess.run(check).returncode)


if __name__ == "__main__":
    main()
