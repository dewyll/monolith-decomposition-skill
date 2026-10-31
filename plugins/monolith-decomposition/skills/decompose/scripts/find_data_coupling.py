#!/usr/bin/env python3
"""Phase 4: data coupling, which components touch which database tables.

Shared tables are often the strongest coupling in a monolith and the one
import graphs never show. This scanner finds two kinds of evidence:

  ownership  ORM mappings that *declare* a table in a component
             (SQLAlchemy __tablename__, Django db_table, JPA @Table,
             EF Core [Table]/ToTable, Rails table_name, Laravel $table,
             TypeORM @Entity, Sequelize tableName, GORM TableName(),
             Ecto schema)
  usage      SQL inside string literals: FROM / JOIN / INTO / UPDATE /
             DELETE FROM <table>, only in strings that look like SQL

Optionally pass the schema (--schema db/schema.sql, migrations, a dump)
so CREATE TABLE statements define the set of known tables; usage of
unknown names is then ignored, which removes most false positives.

Outputs in 04-dependencies/:
  data-coupling.json/.md  tables -> owners and users; shared tables
  data-edges.json         neutral edges (kind "database"): every user of a
                          table depends on its owner. Tables with no single
                          owner are listed in the report, not turned into
                          edges, unless --symmetric (edges both ways).

Merge the edges into the analysis with
  analyze_dependencies.py --extra-edges decomposition/04-dependencies/data-edges.json
or list the file under dependencies.extra_edges in config.json.

Confidence is "low": ORMs configured by convention (Rails models without
table_name, Django default table names), query builders and stored
procedures are invisible. Ask the user and the DBA about the rest.

Usage:
  python3 find_data_coupling.py --workspace decomposition [--schema db/schema.sql ...] [--symmetric]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (SCHEMA_VERSION, ComponentMapper, Workspace, comment_style, iter_source_files,  # noqa: E402
                    md_escape, now_iso, posix, strip_comments, write_json, write_text)

Q = r"""['"`]"""
NAME = r"""([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)"""
DECLARATIONS = [
    ("sqlalchemy", re.compile(r"__tablename__\s*=\s*" + Q + NAME + Q)),
    ("django", re.compile(r"\bdb_table\s*=\s*" + Q + NAME + Q)),
    ("jpa", re.compile(r"@Table\s*\([^)]*?\bname\s*=\s*" + Q + NAME + Q)),
    ("ef-attribute", re.compile(r"\[Table\(\s*" + Q + NAME + Q)),
    ("ef-fluent", re.compile(r"\.ToTable\(\s*" + Q + NAME + Q)),
    ("rails", re.compile(r"self\.table_name\s*=\s*" + Q + NAME + Q)),
    ("laravel", re.compile(r"\$table\s*=\s*" + Q + NAME + Q)),
    ("typeorm", re.compile(r"@Entity\(\s*(?:\{[^}]*?\bname\s*:\s*)?" + Q + NAME + Q)),
    ("sequelize", re.compile(r"\btableName\s*:\s*" + Q + NAME + Q)),
    ("gorm", re.compile(r"TableName\(\)\s*string\s*\{\s*return\s*" + Q + NAME + Q)),
    ("ecto", re.compile(r"^\s*schema\s+" + Q + NAME + Q + r"\s*do", re.M)),
]
STRING = re.compile(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'|"((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'|`([^`]*)`', re.S)
SQL_HINT = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|MERGE)\b", re.I)
SQL_TABLE = re.compile(r"\b(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+[`\"\[]?" + NAME + r"[`\"\]]?", re.I)
CREATE = re.compile(r"\bCREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`\"\[]?" + NAME, re.I)
SQL_WORDS = {"select", "where", "set", "values", "lateral", "unnest", "dual", "only", "the", "a"}


def norm(name: str) -> str:
    return name.split(".")[-1].lower()


def scan(ws: Workspace, known):
    mapper = ComponentMapper(ws.config)
    owners = defaultdict(lambda: defaultdict(list))   # table -> component -> [evidence]
    users = defaultdict(lambda: defaultdict(list))
    files = 0
    for rel, lang in iter_source_files(ws.project_root, ws.config):
        mapped = mapper.map(rel)
        if not mapped:
            continue
        comp = mapped[0]
        files += 1
        raw = (ws.project_root / rel).read_text(encoding="utf-8", errors="ignore")
        text = strip_comments(raw, "php" if lang == "php" else comment_style(lang))
        for orm, rx in DECLARATIONS:
            for m in rx.finditer(text):
                owners[norm(m.group(1))][comp].append(f"{rel} ({orm})")
        for sm in STRING.finditer(text):
            body = next(g for g in sm.groups() if g is not None)
            if not SQL_HINT.search(body):
                continue
            for m in SQL_TABLE.finditer(body):
                t = norm(m.group(1))
                if t in SQL_WORDS or (known and t not in known):
                    continue
                seen = users[t][comp]
                if rel not in seen and len(seen) < 5:
                    seen.append(rel)
    return owners, users, files


def build(owners, users, symmetric: bool):
    tables, edges = {}, defaultdict(lambda: {"weight": 0, "samples": []})
    for t in sorted(set(owners) | set(users)):
        own = sorted(owners.get(t, {}))
        use = sorted(set(users.get(t, {})) - set(own))
        touching = sorted(set(own) | set(use))
        tables[t] = {"owners": own, "users": use, "shared": len(touching) > 1,
                     "evidence": {c: (owners.get(t, {}).get(c, []) + users.get(t, {}).get(c, []))[:5]
                                  for c in touching}}
        if len(touching) < 2:
            continue
        if len(own) == 1:
            pairs = [(u, own[0]) for u in use]
        elif symmetric:
            pairs = [(a, b) for a in touching for b in touching if a != b]
        else:
            pairs = []
        for a, b in pairs:
            e = edges[(a, b)]
            e["weight"] += 1
            if len(e["samples"]) < 5:
                e["samples"].append(f"table {t}")
    return tables, edges


def render_md(data) -> str:
    tables = data["tables"]
    shared = {t: v for t, v in tables.items() if v["shared"]}
    unowned = [t for t, v in shared.items() if len(v["owners"]) != 1]
    lines = ["# Data coupling", "",
             f"Generated {data['generated_at']} (confidence: **low**). {len(tables)} table(s) seen, "
             f"**{len(shared)} touched by more than one component**, {len(data['edges'])} database edge(s).", "",
             "> Ownership comes from ORM mappings, usage from SQL in string literals. Convention-based "
             "ORM mappings, query builders and stored procedures are invisible: confirm with the team.", ""]
    if data["generator"].get("known_tables"):
        lines += [f"Known tables from schema files: {data['generator']['known_tables']}.", ""]
    lines += ["## Shared tables", "", "| Table | Owner(s) | Other users |", "|---|---|---|"]
    for t, v in shared.items():
        lines.append(f"| `{md_escape(t)}` | {', '.join(f'`{c}`' for c in v['owners']) or '—'} | "
                     f"{', '.join(f'`{c}`' for c in v['users'])} |")
    if not shared:
        lines.append("| (none found) | | |")
    if unowned:
        lines += ["", f"**{len(unowned)} shared table(s) without a single owner:** "
                  + ", ".join(f"`{t}`" for t in unowned)
                  + ". No edges were generated for them; decide an owner (an RFC) or rerun with --symmetric."]
    lines += ["", "## All tables", "", "| Table | Owner(s) | Users |", "|---|---|---|"]
    for t, v in tables.items():
        lines.append(f"| `{md_escape(t)}` | {', '.join(v['owners']) or '—'} | {', '.join(v['users']) or '—'} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--schema", action="append", default=[],
                    help="SQL file(s) with CREATE TABLE statements (relative to the current folder)")
    ap.add_argument("--symmetric", action="store_true",
                    help="also emit edges both ways for shared tables without a single owner")
    ap.add_argument("--out-dir", help="default: 04-dependencies")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    known = set()
    for s in args.schema:
        p = Path(s)
        if not p.exists():
            sys.exit(f"error: schema file not found: {s}")
        known |= {norm(m.group(1)) for m in CREATE.finditer(p.read_text(encoding="utf-8", errors="ignore"))}
    owners, users, files = scan(ws, known)
    tables, edges = build(owners, users, args.symmetric)
    out_dir = ws.dir / (args.out_dir or ws.PHASE_DIRS[4])
    generator = {"tool": "find_data_coupling.py", "method": "orm-mappings+sql-strings", "confidence": "low",
                 "kind": "database", "known_tables": len(known) or None,
                 "schema_files": [posix(os.path.relpath(Path(s).resolve(), ws.dir)) for s in args.schema],
                 "blind_spots": ["convention-based ORM table names", "query builders", "stored procedures",
                                 "views and triggers", "other applications sharing the database"]}
    data = {"schema_version": SCHEMA_VERSION, "generated_at": now_iso(), "generator": generator,
            "files": files, "tables": tables,
            "edges": [{"from": a, "to": b, "weight": e["weight"], "kinds": ["database"], "samples": e["samples"]}
                      for (a, b), e in sorted(edges.items())]}
    write_json(out_dir / "data-coupling.json", data)
    write_text(out_dir / "data-coupling.md", render_md(data))
    write_json(out_dir / "data-edges.json", {"schema_version": SCHEMA_VERSION, "generated_at": data["generated_at"],
                                             "generator": generator, "edges": data["edges"]})
    print(json.dumps({"written": [posix(out_dir / f) for f in ("data-coupling.json", "data-coupling.md",
                                                                 "data-edges.json")],
                      "tables": len(tables), "shared_tables": sum(1 for v in tables.values() if v["shared"]),
                      "edges": len(data["edges"])}, indent=2))


if __name__ == "__main__":
    main()
