"""Shared helpers for the monolith-decomposition scripts.

Python 3.9+, standard library only, so the skill runs anywhere a Python
interpreter exists, whatever language the monolith itself is written in.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

SCHEMA_VERSION = 1

# --------------------------------------------------------------------------
# Language table: extension -> (language, comment style)
# --------------------------------------------------------------------------
C_STYLE = "c"          # // line and /* block */
HASH_STYLE = "hash"    # # line
RUBY_STYLE = "ruby"    # # line, =begin/=end block
LUA_STYLE = "lua"      # -- line
NONE_STYLE = "none"

LANGUAGES: Dict[str, Tuple[str, str]] = {
    ".java": ("java", C_STYLE), ".kt": ("kotlin", C_STYLE), ".kts": ("kotlin", C_STYLE),
    ".scala": ("scala", C_STYLE), ".groovy": ("groovy", C_STYLE),
    ".cs": ("csharp", C_STYLE), ".fs": ("fsharp", C_STYLE), ".vb": ("vb", NONE_STYLE),
    ".ts": ("typescript", C_STYLE), ".tsx": ("typescript", C_STYLE), ".mts": ("typescript", C_STYLE),
    ".cts": ("typescript", C_STYLE), ".js": ("javascript", C_STYLE), ".jsx": ("javascript", C_STYLE),
    ".mjs": ("javascript", C_STYLE), ".cjs": ("javascript", C_STYLE), ".vue": ("javascript", C_STYLE),
    ".py": ("python", HASH_STYLE),
    ".go": ("go", C_STYLE),
    ".php": ("php", C_STYLE),
    ".rb": ("ruby", RUBY_STYLE), ".rake": ("ruby", RUBY_STYLE),
    ".rs": ("rust", C_STYLE),
    ".ex": ("elixir", HASH_STYLE), ".exs": ("elixir", HASH_STYLE),
    ".c": ("c", C_STYLE), ".h": ("c", C_STYLE), ".cc": ("cpp", C_STYLE), ".cpp": ("cpp", C_STYLE),
    ".cxx": ("cpp", C_STYLE), ".hpp": ("cpp", C_STYLE), ".hh": ("cpp", C_STYLE),
    ".swift": ("swift", C_STYLE), ".m": ("objc", C_STYLE),
    ".dart": ("dart", C_STYLE),
    ".lua": ("lua", LUA_STYLE),
}

# Which adapter guide covers which language.
ADAPTER_FOR_LANGUAGE = {
    "java": "jvm", "kotlin": "jvm", "scala": "jvm", "groovy": "jvm",
    "csharp": "dotnet", "fsharp": "dotnet", "vb": "dotnet",
    "typescript": "typescript", "javascript": "typescript",
    "python": "python", "go": "go", "php": "php", "ruby": "ruby",
}


def adapter_for(language: str) -> str:
    return ADAPTER_FOR_LANGUAGE.get(language, "other")


# --------------------------------------------------------------------------
# Small utilities
# --------------------------------------------------------------------------
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def die(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def load_json(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        die(f"file not found: {path}")
    except json.JSONDecodeError as exc:
        die(f"invalid JSON in {path}: {exc}")
    return {}  # unreachable


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def posix(path: os.PathLike | str) -> str:
    return PurePosixPath(Path(path).as_posix()).as_posix()


def mean_stddev(values: List[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    m = sum(values) / len(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return m, math.sqrt(var)


def md_escape(text: str) -> str:
    return str(text).replace("|", "\\|")


# --------------------------------------------------------------------------
# Glob matching with ** support (fnmatch lets * cross "/", which is wrong here)
# --------------------------------------------------------------------------
_GLOB_CACHE: Dict[str, "re.Pattern[str]"] = {}


def glob_to_regex(pattern: str) -> "re.Pattern[str]":
    if pattern in _GLOB_CACHE:
        return _GLOB_CACHE[pattern]
    i, out = 0, []
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    rx = re.compile("^" + "".join(out) + "$")
    _GLOB_CACHE[pattern] = rx
    return rx


def static_prefix(pattern: str) -> str:
    """Folder part of a glob before the first wildcard: 'packs/billing/**' -> 'packs/billing'."""
    parts = []
    for seg in pattern.split("/"):
        if any(ch in seg for ch in "*?["):
            break
        parts.append(seg)
    return "/".join(parts) or "."


def matches_any(path: str, patterns: Iterable[str]) -> bool:
    return any(glob_to_regex(p).match(path) for p in patterns)


# --------------------------------------------------------------------------
# Workspace & config
# --------------------------------------------------------------------------
class Workspace:
    """The decomposition workspace (default: <project>/decomposition)."""

    def __init__(self, path: os.PathLike | str):
        self.dir = Path(path).resolve()
        self.config_path = self.dir / "config.json"
        self.state_path = self.dir / "state.json"
        if not self.config_path.exists():
            die(f"no config.json in {self.dir}. Run init_workspace.py first.")
        self.config = load_json(self.config_path)
        self.project_root = (self.dir / self.config.get("project_root", "..")).resolve()
        # Never analyse the workspace itself, whatever it is called.
        self.config["_workspace_dir_name"] = self.dir.name

    # Phase folders -------------------------------------------------------
    PHASE_DIRS = {
        0: "00-assessment", 1: "01-sizing", 2: "02-common-domain", 3: "03-flattening",
        4: "04-dependencies", 5: "05-domains", 6: "06-services",
    }

    def phase_dir(self, phase: int) -> Path:
        return self.dir / self.PHASE_DIRS[phase]

    def artifact(self, phase: int, name: str) -> Path:
        return self.phase_dir(phase) / name

    @property
    def rfc_dir(self) -> Path:
        return self.dir / self.config.get("workspace", {}).get("rfc_dir", "rfcs")

    @property
    def fitness_dir(self) -> Path:
        return self.dir / "fitness"

    # Config shortcuts ----------------------------------------------------
    def thresholds(self) -> dict:
        return self.config.get("thresholds", {})

    def fitness(self) -> dict:
        return self.config.get("fitness", {})


def source_roots(config: dict) -> List[dict]:
    """Normalise config.source_roots into [{path, namespace_prefix}]."""
    roots = config.get("source_roots") or ["."]
    result = []
    for r in roots:
        if isinstance(r, str):
            result.append({"path": posix(r).strip("/") or ".", "namespace_prefix": ""})
        else:
            result.append({
                "path": posix(r.get("path", ".")).strip("/") or ".",
                "namespace_prefix": r.get("namespace_prefix", "") or "",
            })
    return result


# --------------------------------------------------------------------------
# File discovery
# --------------------------------------------------------------------------
ALWAYS_EXCLUDED_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
                        ".idea", ".vscode", ".gradle", ".mvn", ".terraform", "decomposition"}


def iter_source_files(project_root: Path, config: dict) -> Iterator[Tuple[str, str]]:
    """Yield (relative posix path, language) for every source file in scope."""
    include = config.get("include") or ["**/*"]
    exclude = config.get("exclude") or []
    allowed_ext = set(config.get("extensions") or LANGUAGES.keys())
    ws_name = Path(config.get("_workspace_dir_name", "decomposition")).name
    for root in source_roots(config):
        base = (project_root / root["path"]).resolve()
        if not base.exists():
            print(f"warning: source root not found: {root['path']}", file=sys.stderr)
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames
                                 if d not in ALWAYS_EXCLUDED_DIRS and d != ws_name)
            for name in sorted(filenames):
                ext = Path(name).suffix.lower()
                if ext not in allowed_ext or ext not in LANGUAGES:
                    continue
                rel = posix(Path(dirpath, name).resolve().relative_to(project_root))
                if include and not matches_any(rel, include):
                    continue
                if exclude and matches_any(rel, exclude):
                    continue
                yield rel, LANGUAGES[ext][0]


# --------------------------------------------------------------------------
# Component mapping
# --------------------------------------------------------------------------
class ComponentMapper:
    """Maps a file path to a component id according to config.components.

    strategy "directory": every directory that holds source files is a
      component (a namespace / package), optionally collapsed at max_depth
      levels below its source root. This mirrors how the component-based
      decomposition patterns treat namespaces.
    strategy "explicit": the user lists components with path globs.
    """

    def __init__(self, config: dict):
        self.config = config
        comp = config.get("components") or {}
        self.strategy = comp.get("strategy", "directory")
        self.max_depth = comp.get("max_depth")
        self.separator = comp.get("separator", ".")
        self.explicit = comp.get("explicit") or []
        self.roots = sorted(source_roots(config), key=lambda r: -len(r["path"]))
        self.multi_root = len(self.roots) > 1

    def _root_for(self, rel: str) -> Optional[dict]:
        for r in self.roots:
            if r["path"] == "." or rel == r["path"] or rel.startswith(r["path"] + "/"):
                return r
        return None

    def map(self, rel: str) -> Optional[Tuple[str, str]]:
        """Return (component id, component path) or None when unassigned."""
        if self.strategy == "explicit":
            for c in self.explicit:
                if matches_any(rel, c.get("paths", [])):
                    return c["name"], c.get("path") or static_prefix(c["paths"][0])
            return None
        root = self._root_for(rel)
        if root is None:
            return None
        inner = rel if root["path"] == "." else rel[len(root["path"]) + 1:]
        parts = inner.split("/")[:-1]
        if self.max_depth is not None:
            parts = parts[: int(self.max_depth)]
        comp_path = "/".join(([] if root["path"] == "." else [root["path"]]) + parts) or "."
        ident = self.separator.join(parts) if parts else "(root)"
        if self.multi_root:
            label = root["path"].replace("/", self.separator)
            ident = f"{label}:{ident}"
        return ident, comp_path


# --------------------------------------------------------------------------
# Artifact loading helpers
# --------------------------------------------------------------------------
def load_components(path: Path) -> dict:
    data = load_json(path)
    if "components" not in data:
        die(f"{path} does not look like a components artifact")
    return data


def component_index(components: dict) -> Dict[str, dict]:
    return {c["id"]: c for c in components["components"]}
