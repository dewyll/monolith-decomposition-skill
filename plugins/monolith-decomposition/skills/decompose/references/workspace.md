# Workspace, configuration and state

## Layout

```
decomposition/
├── config.json              mapping, thresholds, fitness rules
├── state.json               phase state machine and history
├── 00-assessment/           assessment.md, probe/, fork-plan.md (tactical forking)
├── 01-sizing/               components.json, components.md, report.md
├── 02-common-domain/        candidates.json/.md, common-domain.json, report.md
├── 03-flattening/           plan.md, plan.json, components.json/.md (re-measured), report.md
├── 04-dependencies/         edges.json, dependencies.json/.md/.mmd, report.md
├── 05-domains/              domains.json, domain-coupling.json/.md/.mmd, report.md
├── 06-services/             services.json, report.md
├── fitness/                 results-<phase>.json/.md, native rule snippets
└── rfcs/                    0001-*.md … and index.md
```

Each JSON artifact has a schema in `schemas/`. Every generated artifact
records its `generator` (tool, metric or method, confidence) so a reader
knows how much to trust it.

## config.json

| Field | Meaning |
|---|---|
| `project_root` | Path from the workspace to the project (default `..`). |
| `languages` | Detected languages, most files first. Informational. |
| `source_roots` | Strings or `{path, namespace_prefix}`. The prefix is prepended to folder-derived namespaces (Go module path, C# root namespace, PHP PSR-4 prefix). |
| `include` / `exclude` | Globs relative to the project root (`**` crosses folders, `*` does not). |
| `extensions` | Restrict to these file extensions; empty means all known source types. |
| `import_aliases` | Path aliases for path-style imports, e.g. `{"@/": "src/"}` (TS paths, webpack aliases). |
| `components.strategy` | `directory` (each folder with code is a component) or `explicit`. |
| `components.max_depth` | Collapse folders deeper than this below the source root. |
| `components.separator` | Separator in component ids (default `.`). |
| `components.explicit` | `[{name, paths: [globs]}]`, first match wins. |
| `metrics.size` | `auto` (scc if installed), `scc`, or `builtin`. |
| `thresholds.size_outlier_stddev` | z-score beyond which a component is flagged large/small (default 1.0). |
| `thresholds.max_component_percent` | Max share of the codebase per component (default 15). |
| `thresholds.max_efferent_coupling` | Optional cap on Ce for F4.2. |
| `thresholds.min_domain_cohesion` | Optional floor for F5.3 (0–1). |
| `thresholds.common_fan_in_ratio` | Fan-in share that flags a common candidate (default 0.3). |
| `common_keywords` | Words that suggest shared concerns. |
| `fitness.size_allowlist` | `{component: "reason (RFC-nnnn)"}` exempt from F1.2/F1.3. |
| `fitness.orphan_allowlist` | `{component: "reason"}` exempt from F3.1. |
| `fitness.allowed_cycles` | `[[a, b], ...]` cycles accepted by an RFC. |
| `fitness.forbidden_dependencies` | `[{from, to, level: domain or component, rfc}]`; `*` is a wildcard. |
| `workspace.rfc_dir` | Where RFCs live, relative to the workspace (default `rfcs`). |

## state.json

```
not_started → in_progress → awaiting_review → approved
                    ▲                              │
                    └──────────── reopen ──────────┘   (later phases become "stale")
```

Fields per phase: `status`, `iteration`, `rfcs`, `updated_at`,
`approved_by`, `approved_at`. `history` keeps every transition. Use
`state.py`; edit by hand only to repair a broken file.

## Neutral formats for external tools

Any tool can feed the pipeline if its output is converted:

- **Sizes** → `size_components.py --from-json raw.json` with
  `{"tool": "...", "metric": "...", "components": [{"id", "path", "files", "size"}]}`.
- **Edges** → `analyze_dependencies.py --edges edges.json` with
  `{"generator": {"tool": "...", "confidence": "high"}, "edges": [{"from", "to", "weight"}]}`.

Converters are usually ten lines of Python or `jq`; the adapters show the
shape of each tool's output. Map file paths to component ids with the same
rules as `config.json` (the `ComponentMapper` class in `scripts/common.py`
can be imported for that).
