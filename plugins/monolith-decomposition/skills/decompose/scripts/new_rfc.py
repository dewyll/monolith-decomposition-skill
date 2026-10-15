#!/usr/bin/env python3
"""Create the next numbered RFC from the template, or rebuild the RFC index.

Usage:
  python3 new_rfc.py --workspace decomposition --title "Component sizing thresholds" --phase 1
  python3 new_rfc.py --workspace decomposition --set-status 0003 Accepted
  python3 new_rfc.py --workspace decomposition --supersede 0003 --by 0007
  python3 new_rfc.py --workspace decomposition --reindex

RFC files carry a small front matter block (id, title, status, phase, date,
supersedes, superseded_by) that the index and the state file rely on.
Statuses: Proposed, Accepted, Rejected, Superseded.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import Workspace, posix, write_text  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "rfc.md"
STATUSES = {"Proposed", "Accepted", "Rejected", "Superseded"}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60] or "rfc"


def parse_front(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    meta = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    meta["_file"] = path.name
    return meta


def set_front(path: Path, key: str, value: str) -> None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        sys.exit(f"error: {path} has no front matter")
    lines = m.group(1).splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.split(":", 1)[0].strip() == key:
            lines[i] = f"{key}: {value}"
            found = True
    if not found:
        lines.append(f"{key}: {value}")
    path.write_text("---\n" + "\n".join(lines) + "\n---\n" + text[m.end():], encoding="utf-8")


def rfcs(ws: Workspace):
    return sorted(p for p in ws.rfc_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))


def find(ws: Workspace, number: str) -> Path:
    number = number.zfill(4)
    for p in rfcs(ws):
        if p.name.startswith(number + "-"):
            return p
    sys.exit(f"error: RFC {number} not found")


def reindex(ws: Workspace) -> Path:
    rows = ["# Architecture RFCs", "",
            "Every architecture decision taken during the decomposition, in order.", "",
            "| # | Title | Status | Phase | Date |", "|---|---|---|---|---|"]
    for p in rfcs(ws):
        m = parse_front(p)
        status = m.get("status", "?")
        if m.get("superseded_by"):
            status += f" by {m['superseded_by']}"
        rows.append(f"| [{m.get('id', '?')}]({p.name}) | {m.get('title', '')} | {status} | "
                    f"{m.get('phase', '')} | {m.get('date', '')} |")
    dest = ws.rfc_dir / "index.md"
    write_text(dest, "\n".join(rows) + "\n")
    return dest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--title")
    ap.add_argument("--phase", default="")
    ap.add_argument("--status", default="Proposed")
    ap.add_argument("--set-status", nargs=2, metavar=("NUMBER", "STATUS"))
    ap.add_argument("--supersede", metavar="OLD")
    ap.add_argument("--by", metavar="NEW")
    ap.add_argument("--reindex", action="store_true")
    args = ap.parse_args()
    ws = Workspace(args.workspace)
    ws.rfc_dir.mkdir(parents=True, exist_ok=True)

    if args.set_status:
        num, status = args.set_status
        if status not in STATUSES:
            sys.exit(f"error: status must be one of {sorted(STATUSES)}")
        set_front(find(ws, num), "status", status)
        print(posix(reindex(ws)))
        return
    if args.supersede:
        if not args.by:
            sys.exit("error: --supersede needs --by NEW")
        old, new = find(ws, args.supersede), find(ws, args.by)
        set_front(old, "status", "Superseded")
        set_front(old, "superseded_by", args.by.zfill(4))
        set_front(new, "supersedes", args.supersede.zfill(4))
        print(posix(reindex(ws)))
        return
    if args.reindex:
        print(posix(reindex(ws)))
        return
    if not args.title:
        sys.exit("error: --title is required")

    existing = [int(p.name[:4]) for p in rfcs(ws)]
    number = f"{(max(existing) + 1) if existing else 1:04d}"
    template = TEMPLATE.read_text(encoding="utf-8")
    body = (template.replace("{{id}}", number).replace("{{title}}", args.title)
            .replace("{{status}}", args.status).replace("{{phase}}", str(args.phase))
            .replace("{{date}}", date.today().isoformat()))
    dest = ws.rfc_dir / f"{number}-{slugify(args.title)}.md"
    write_text(dest, body)
    reindex(ws)
    print(posix(dest))


if __name__ == "__main__":
    main()
