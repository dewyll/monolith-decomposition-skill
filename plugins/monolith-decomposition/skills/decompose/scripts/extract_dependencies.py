#!/usr/bin/env python3
"""Phase 4 (fallback extractor): component-to-component import edges.

A language-agnostic, regex-based import scanner. It understands the import
syntax of the common languages and resolves each import to a component
using the source roots, namespace prefixes and import aliases in config.

It is deliberately honest about its limits: it sees *static imports only*.
Dependency injection, reflection, events, string-based lookups, framework
autoloading (Rails, Laravel facades) and dynamic imports are invisible or
partial. The output is marked confidence "low" so later phases treat it as
a lower bound. Prefer a language-native extractor from the adapter guides
and feed its edges to analyze_dependencies.py instead.

Usage:
  python3 extract_dependencies.py --workspace decomposition \
      [--components 01-sizing/components.json] [--out 04-dependencies/edges.json]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import posixpath
import re
import sys
import warnings
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (SCHEMA_VERSION, ComponentMapper, Workspace, comment_style,  # noqa: E402
                    iter_source_files, now_iso, posix, source_roots, strip_comments, write_json)

# --------------------------------------------------------------------------
# Import patterns. Each returns (kind, target) where kind is
#   "ns"   a dotted / namespaced name  (com.acme.billing.Invoice)
#   "path" a file-system-like path      (./billing/invoice, billing/invoice)
#   "dyn"  a dynamic import             (import('./x'))
# --------------------------------------------------------------------------
RX = {
    # Python fallback only (when ast cannot parse the file, e.g. Python 2 code)
    "py_import": re.compile(r"^[ \t]*import[ \t]+([\w\. \t,]+)", re.M),
    "py_from": re.compile(r"^[ \t]*from[ \t]+(\.*[\w\.]*)[ \t]+import[ \t]+(?:\(([^)]*)\)|([^\n;]+))", re.M),
    "js_from": re.compile(r"""(?:import|export)\s[^'"`;]*?\sfrom\s*['"]([^'"]+)['"]""", re.S),
    "js_side": re.compile(r"""^\s*import\s*['"]([^'"]+)['"]""", re.M),
    "js_require": re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    "js_dynamic": re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    "jvm_import": re.compile(r"^\s*import\s+(?:static\s+)?([\w\.]+)(?:\.\*)?\s*;?", re.M),
    "cs_using": re.compile(r"^\s*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w\.]+)\s*;", re.M),
    "go_single": re.compile(r"""^\s*import\s+(?:[\w\.]+\s+)?"([^"]+)\"""", re.M),
    "go_block": re.compile(r"""^\s*import\s*\((.*?)\)""", re.M | re.S),
    "go_line": re.compile(r"""(?:[\w\.]+\s+)?"([^"]+)\""""),
    "php_use": re.compile(r"^\s*use\s+(?:function\s+|const\s+)?([\w\\]+)", re.M),
    "rb_require": re.compile(r"""^\s*require\s+['"]([^'"]+)['"]""", re.M),
    "rb_relative": re.compile(r"""^\s*require_relative\s+['"]([^'"]+)['"]""", re.M),
    "rs_use": re.compile(r"^\s*(?:pub\s+)?use\s+((?:crate|super|self)(?:::\w+)+)", re.M),
    "ex_ref": re.compile(r"^\s*(?:alias|import|use|require)\s+([A-Z][\w\.]+)", re.M),
    "c_include": re.compile(r"""^\s*#\s*include\s+"([^"]+)\"""", re.M),
    "swift_import": re.compile(r"^\s*(?:@testable\s+)?import\s+(\w+)", re.M),
}


def _py_from(mod: str, names, out):
    names = [n for n in names if n and n != "*"]
    if mod.startswith("."):
        # relative: "from . import sub" -> sub may be a sub-package, so try both
        out.append(("pyrel", mod))
        for n in names:
            out.append(("pyrel", mod + ("" if mod.endswith(".") else ".") + n))
    else:
        out.append(("ns", mod))
        for n in names:
            out.append(("ns", f"{mod}.{n}"))


def python_imports_ast(text: str):
    """Exact Python imports via the standard library parser.

    Handles parenthesised multi-line imports, trailing comments, imports
    inside functions or `if TYPE_CHECKING:` blocks, and ignores docstrings.
    Returns None when the file does not parse with this interpreter.
    """
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # e.g. invalid escape sequences in old code
            tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [("ns", a.name) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            _py_from("." * (node.level or 0) + (node.module or ""), [a.name for a in node.names], out)
    return out


def python_imports_regex(text: str):
    """Fallback for files ast cannot parse; expects comments and strings already blanked."""
    out = []
    for m in RX["py_import"].finditer(text):
        for name in m.group(1).split(","):
            name = name.strip().split(" as ")[0].strip()
            if name:
                out.append(("ns", name))
    for m in RX["py_from"].finditer(text):
        body = m.group(2) if m.group(2) is not None else m.group(3)
        names = [n.strip().split(" as ")[0].strip() for n in body.replace("\\\n", " ").split(",")]
        _py_from(m.group(1), names, out)
    return out


def imports_for(language: str, text: str):
    out = []
    if language == "python":
        parsed = python_imports_ast(text)
        if parsed is not None:
            return parsed
        return python_imports_regex(strip_comments(text, comment_style("python"), blank_strings=True))
    text = strip_comments(text, "php" if language == "php" else comment_style(language))
    if language in ("typescript", "javascript"):
        for key in ("js_from", "js_side", "js_require"):
            out += [("path", m.group(1)) for m in RX[key].finditer(text)]
        out += [("dyn", m.group(1)) for m in RX["js_dynamic"].finditer(text)]
    elif language in ("java", "kotlin", "scala", "groovy", "dart"):
        out += [("ns", m.group(1)) for m in RX["jvm_import"].finditer(text)]
    elif language in ("csharp", "fsharp"):
        out += [("ns", m.group(1)) for m in RX["cs_using"].finditer(text)]
    elif language == "go":
        out += [("ns", m.group(1)) for m in RX["go_single"].finditer(text)]
        for block in RX["go_block"].finditer(text):
            out += [("ns", m.group(1)) for m in RX["go_line"].finditer(block.group(1))]
    elif language == "php":
        out += [("ns", m.group(1).replace("\\", ".")) for m in RX["php_use"].finditer(text)]
    elif language == "ruby":
        out += [("path", "./" + m.group(1)) for m in RX["rb_relative"].finditer(text)]
        out += [("rootpath", m.group(1)) for m in RX["rb_require"].finditer(text)]
    elif language == "rust":
        out += [("rust", m.group(1)) for m in RX["rs_use"].finditer(text)]
    elif language == "elixir":
        out += [("ns", m.group(1)) for m in RX["ex_ref"].finditer(text)]
    elif language in ("c", "cpp", "objc"):
        out += [("include", m.group(1)) for m in RX["c_include"].finditer(text)]
    elif language == "swift":
        out += [("ns", m.group(1)) for m in RX["swift_import"].finditer(text)]
    return out


# --------------------------------------------------------------------------
# Resolution
# --------------------------------------------------------------------------
class Resolver:
    def __init__(self, ws: Workspace, components: dict):
        self.ws = ws
        self.mapper = ComponentMapper(ws.config)
        self.aliases = ws.config.get("import_aliases") or {}
        self.roots = source_roots(ws.config)
        self.paths = {}       # component path -> id
        self.ns = {}          # namespace key -> id
        for c in components["components"]:
            p = c.get("path")
            if not p:
                continue
            self.paths[p] = c["id"]
            for r in self.roots:
                if r["path"] == ".":
                    inner = "" if p == "." else p
                elif p == r["path"] or p.startswith(r["path"] + "/"):
                    inner = p[len(r["path"]):].strip("/")
                else:
                    continue
                key = ".".join(x for x in [r["namespace_prefix"].replace("/", "."),
                                           inner.replace("/", ".")] if x)
                if key:
                    self.ns.setdefault(key.lower(), c["id"])
        self.ns_keys = sorted(self.ns, key=len, reverse=True)
        self.path_keys = sorted(self.paths, key=len, reverse=True)

    def by_path(self, target: str):
        """target: posix path relative to project root (file or dir, maybe without extension)."""
        target = posixpath.normpath(target)
        if target.startswith("../"):
            return None  # outside the project
        # path_keys is sorted longest first, so the deepest owning component wins
        for p in self.path_keys:
            if p == "." or target == p or target.startswith(p + "/"):
                return self.paths[p]
        return None

    def by_ns(self, name: str):
        n = name.lower().replace("/", ".").replace("::", ".").replace("\\", ".").strip(".")
        for k in self.ns_keys:
            if n == k or n.startswith(k + "."):
                return self.ns[k]
        return None

    def _exists(self, rel: str) -> bool:
        """True when rel (relative to the project root, extension optional) is a real file or folder."""
        full = self.ws.project_root / posixpath.normpath(rel)
        if full.exists():
            return True
        return full.parent.exists() and any(full.parent.glob(full.name + ".*"))

    def resolve(self, kind: str, target: str, from_file: str):
        here = posixpath.dirname(from_file)
        if kind in ("path", "dyn"):
            if target.startswith("."):
                return self.by_path(posixpath.join(here, target))
            for prefix, repl in sorted(self.aliases.items(), key=lambda kv: -len(kv[0])):
                if target.startswith(prefix):
                    return self.by_path(posixpath.normpath(repl.rstrip("/") + "/" +
                                                           target[len(prefix):].lstrip("/")))
            return None  # bare specifier: external package
        if kind == "include":
            # #include "x.h": relative to the including file first, then the source roots
            return (self.by_path(posixpath.join(here, target)) if self._exists(posixpath.join(here, target))
                    else None) or self.resolve("rootpath", target, from_file)
        if kind == "rootpath":
            # only count it when the file really exists under a source root,
            # otherwise `require "json"` would look like an internal import
            for r in self.roots:
                cand = posixpath.normpath(("" if r["path"] == "." else r["path"] + "/") + target)
                if self._exists(cand):
                    return self.by_path(cand)
            return None
        if kind == "pyrel":
            dots = len(target) - len(target.lstrip("."))
            base = here
            for _ in range(dots - 1):
                base = posixpath.dirname(base)
            rest = target[dots:].replace(".", "/")
            return self.by_path(posixpath.join(base, rest) if rest else base + "/__init__")
        if kind == "rust":
            parts = target.split("::")
            if parts[0] == "crate":
                return self.by_ns(".".join(parts[1:]))
            base = here
            for p in parts:
                if p == "super":
                    base = posixpath.dirname(base)
                elif p != "self":
                    break
            rest = [p for p in parts if p not in ("super", "self")]
            return self.by_path(posixpath.join(base, *rest)) if rest else None
        return self.by_ns(target)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workspace", default="decomposition")
    ap.add_argument("--components", help="components.json (default: newest of 03-flattening, 01-sizing)")
    ap.add_argument("--out", help="edges output (default: 04-dependencies/edges.json)")
    args = ap.parse_args()

    ws = Workspace(args.workspace)
    comp_path = Path(args.components) if args.components else next(
        (p for p in [ws.artifact(3, "components.json"), ws.artifact(1, "components.json")] if p.exists()),
        None)
    if comp_path is None:
        sys.exit("error: no components.json yet. Run size_components.py first.")
    components = json.loads(Path(comp_path).read_text(encoding="utf-8"))
    resolver = Resolver(ws, components)
    known = {c["id"] for c in components["components"]}

    edges = defaultdict(lambda: {"weight": 0, "kinds": set(), "samples": []})
    internal = defaultdict(int)
    stats = {"files": 0, "imports": 0, "resolved": 0, "external_or_unresolved": 0}
    for rel, lang in iter_source_files(ws.project_root, ws.config):
        mapped = resolver.mapper.map(rel)
        if not mapped or mapped[0] not in known:
            continue
        src = mapped[0]
        stats["files"] += 1
        text = (ws.project_root / rel).read_text(encoding="utf-8", errors="ignore")
        seen_here = set()
        for kind, target in imports_for(lang, text):
            stats["imports"] += 1
            dst = resolver.resolve(kind, target, rel)
            if not dst:
                stats["external_or_unresolved"] += 1
                continue
            stats["resolved"] += 1
            if dst in seen_here:
                continue  # weight = number of files in `src` that reference `dst`
            seen_here.add(dst)
            if dst == src:
                internal[src] += 1
                continue
            e = edges[(src, dst)]
            e["weight"] += 1
            e["kinds"].add("dynamic" if kind == "dyn" else "static")
            if len(e["samples"]) < 5:
                e["samples"].append(f"{rel} -> {target}")

    out = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_iso(),
        "generator": {"tool": "extract_dependencies.py", "method": "regex-static-imports",
                      "confidence": "low",
                      "blind_spots": ["dependency injection", "reflection", "events/messages",
                                      "framework autoloading", "string-based lookups",
                                      "shared database tables"]},
        "components_source": posix(os.path.relpath(Path(comp_path).resolve(), ws.dir)),
        "stats": stats,
        "internal_references": dict(sorted(internal.items())),
        "edges": [
            {"from": s, "to": d, "weight": e["weight"], "kinds": sorted(e["kinds"]),
             "samples": e["samples"]}
            for (s, d), e in sorted(edges.items())
        ],
    }
    dest = Path(args.out) if args.out else ws.artifact(4, "edges.json")
    write_json(dest, out)
    print(json.dumps({"written": posix(dest), "edges": len(out["edges"]), **stats}, indent=2))


if __name__ == "__main__":
    main()
