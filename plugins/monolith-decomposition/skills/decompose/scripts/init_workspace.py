#!/usr/bin/env python3
"""Create the decomposition workspace inside a project.

Detects languages and likely source roots, writes config.json and
state.json, and prints which adapter guides to read.

Usage:
  python3 init_workspace.py <project_root> [--dir decomposition] [--force]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (ALWAYS_EXCLUDED_DIRS, LANGUAGES, SCHEMA_VERSION, adapter_for,  # noqa: E402
                    now_iso, posix, write_json, write_text)

PHASES = {
    0: "Assess the monolith and choose an approach",
    1: "Identify and size components",
    2: "Gather common domain components",
    3: "Flatten components",
    4: "Determine component dependencies",
    5: "Create component domains",
    6: "Create domain services",
}

DEFAULT_EXCLUDE = [
    # tests are measured separately; they would distort component sizes
    "**/test/**", "**/tests/**", "**/__tests__/**", "**/spec/**", "**/testing/**",
    "**/*.test.*", "**/*.spec.*", "**/*_test.go", "**/test_*.py", "**/*_test.py",
    "**/*Test.java", "**/*Tests.java", "**/*Test.kt", "**/*Tests.cs", "**/*Test.php",
    # generated / vendored / build output
    "**/vendor/**", "**/dist/**", "**/build/**", "**/target/**", "**/out/**",
    "**/bin/**", "**/obj/**", "**/generated/**", "**/*.generated.*", "**/*.min.js",
    "**/migrations/**",
]

ROOT_CANDIDATES = [
    "src/main/java", "src/main/kotlin", "src/main/scala", "app", "lib", "src",
    "internal", "pkg",
]

COMMON_KEYWORDS = [
    "audit", "auditing", "log", "logging", "logger", "notification", "notifications",
    "notify", "email", "mail", "mailer", "sms", "util", "utils", "utility", "common",
    "shared", "helper", "helpers", "validation", "validator", "formatter", "security",
    "auth", "config", "cache", "messaging", "events", "i18n", "pdf", "report", "reporting",
]


def detect_languages(root: Path, limit: int = 200_000) -> Counter:
    counts: Counter = Counter()
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ALWAYS_EXCLUDED_DIRS
                       and d not in {"vendor", "dist", "build", "target", "bin", "obj"}]
        for name in filenames:
            ext = Path(name).suffix.lower()
            if ext in LANGUAGES:
                counts[LANGUAGES[ext][0]] += 1
            seen += 1
            if seen >= limit:
                return counts
    return counts


def go_module(root: Path) -> str:
    gomod = root / "go.mod"
    if gomod.exists():
        m = re.search(r"^module\s+(\S+)", gomod.read_text(encoding="utf-8", errors="ignore"), re.M)
        if m:
            return m.group(1)
    return ""


def composer_roots(root: Path) -> list:
    comp = root / "composer.json"
    if not comp.exists():
        return []
    try:
        data = json.loads(comp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    roots = []
    for prefix, paths in (data.get("autoload", {}).get("psr-4", {}) or {}).items():
        for p in ([paths] if isinstance(paths, str) else paths):
            roots.append({"path": posix(p).strip("/") or ".",
                          "namespace_prefix": prefix.strip("\\").replace("\\", ".")})
    return roots


def guess_source_roots(root: Path, languages: Counter) -> list:
    if "php" in languages and composer_roots(root):
        return composer_roots(root)
    if "go" in languages and go_module(root):
        return [{"path": ".", "namespace_prefix": go_module(root)}]
    found = []
    for cand in ROOT_CANDIDATES:
        p = root / cand
        if p.is_dir():
            if any(p2.suffix.lower() in LANGUAGES for p2 in p.rglob("*") if p2.is_file()):
                found.append(cand)
    # keep the most specific roots (src/main/java beats src)
    pruned = [r for r in found if not any(o != r and o.startswith(r + "/") for o in found)]
    return pruned or ["."]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_root")
    ap.add_argument("--dir", default="decomposition", help="workspace folder name (default: decomposition)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing config/state")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        sys.exit(f"error: {root} is not a directory")
    ws = root / args.dir
    if (ws / "config.json").exists() and not args.force:
        sys.exit(f"error: {ws}/config.json already exists (use --force to overwrite)")

    languages = detect_languages(root)
    if not languages:
        print("warning: no known source files found; edit config.json by hand", file=sys.stderr)
    roots = guess_source_roots(root, languages)

    config = {
        "schema_version": SCHEMA_VERSION,
        "project_root": "..",
        "languages": [lang for lang, _ in languages.most_common()],
        "source_roots": roots,
        "include": ["**/*"],
        "exclude": DEFAULT_EXCLUDE,
        "extensions": [],
        "import_aliases": {},
        "components": {
            "strategy": "directory",
            "max_depth": None,
            "separator": ".",
            "explicit": [],
        },
        "metrics": {"size": "auto"},
        "thresholds": {
            "size_outlier_stddev": 1.0,
            "max_component_percent": 15.0,
            "max_efferent_coupling": None,
            "min_domain_cohesion": None,
            "common_fan_in_ratio": 0.3,
        },
        "common_keywords": COMMON_KEYWORDS,
        "fitness": {
            "size_allowlist": {},
            "orphan_allowlist": {},
            "allowed_cycles": [],
            "forbidden_dependencies": [],
        },
        "workspace": {"rfc_dir": "rfcs"},
    }

    state = {
        "schema_version": SCHEMA_VERSION,
        "created_at": now_iso(),
        "approach": None,
        "current_phase": 0,
        "phases": {
            str(n): {"name": name, "status": "not_started", "iteration": 0,
                     "rfcs": [], "updated_at": None}
            for n, name in PHASES.items()
        },
        "history": [],
    }

    write_json(ws / "config.json", config)
    write_json(ws / "state.json", state)
    for d in ["00-assessment", "01-sizing", "02-common-domain", "03-flattening",
              "04-dependencies", "05-domains", "06-services", "fitness", "rfcs"]:
        (ws / d).mkdir(parents=True, exist_ok=True)
    index = ws / "rfcs" / "index.md"
    if not index.exists():
        write_text(index, "# Architecture RFCs\n\n| # | Title | Status | Phase | Date |\n|---|---|---|---|---|\n")

    adapters = sorted({adapter_for(lang) for lang in languages})
    print(json.dumps({
        "workspace": posix(ws),
        "languages": dict(languages.most_common()),
        "source_roots": roots,
        "adapters_to_read": [f"adapters/{a}.md" for a in adapters] or ["adapters/other.md"],
        "next": "Review config.json with the user, then start Phase 0.",
    }, indent=2))


if __name__ == "__main__":
    main()
