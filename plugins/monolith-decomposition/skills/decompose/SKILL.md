---
name: decompose
description: Use when someone wants to break up, split, modularize or decompose a monolith, find service boundaries, plan a microservices migration, measure component size, coupling or co-change, or set up architecture fitness functions, in any programming language. Runs a phased, evidence-based workflow (component-based decomposition or tactical forking) where scripts measure the code and its git history, every decision becomes a numbered RFC guarded by a fitness function, and each phase stops at a human approval gate.
---

# Monolith decomposition

You are guiding a team through decomposing a monolithic codebase into
services, one phase at a time. The workflow follows the component-based
decomposition patterns described by Ford, Richards, Sadalage and Dehghani
in *Software Architecture: The Hard Parts* (O'Reilly, 2021), adapted so a
coding agent can run it on any language.

Three rules shape everything below:

1. **Numbers come from scripts, judgement comes from people.** Never estimate
   sizes, coupling or cycles yourself. Run the scripts in `scripts/` (or a
   language-native tool from `adapters/`) and interpret their output.
2. **Every phase ends at a gate.** Present the artifacts, propose decisions,
   and wait for the user's explicit approval before moving on. Domain
   boundaries are business decisions.
3. **Every decision is an RFC, and every RFC is protected by a fitness
   function.** If a decision cannot be checked automatically, say so in the
   RFC and say how it will be checked instead.

## Where things live

This skill lives in `${CLAUDE_SKILL_DIR}` (agents that do not fill that in:
the folder that contains this file). The references write it as
`$SKILL_DIR`; shell variables do not survive between commands, so put the
full path in every command: `python3 "${CLAUDE_SKILL_DIR}/scripts/<name>.py"`.
All scripts are Python 3.9+ with no dependencies, and `--help` on any of
them shows its options.

| Path | What it holds |
|---|---|
| `references/phase-N-*.md` | What to do in each phase, its outputs and its gate |
| `references/tactical-forking.md` | The alternative path for code with no usable structure |
| `references/fitness-functions.md` | Generic checks, CI wiring, per-phase guards |
| `references/rfc-process.md` | When to write an RFC, statuses, superseding |
| `references/workspace.md` | Workspace layout, `config.json` and `state.json` fields |
| `adapters/<ecosystem>.md` | What "component" means there, native extractors, fitness libraries |
| `schemas/*.schema.json` | Contracts for every artifact; the neutral format between tools |
| `templates/` | RFC and phase report templates |
| `scripts/` | measurement (`size_components`, `extract_dependencies`, `change_coupling`, `find_data_coupling`, `find_common_candidates`), analysis (`analyze_dependencies`, `suggest_domains`), guards (`check_fitness`, `run_guard`), bookkeeping (`init_workspace`, `new_rfc`, `state`, `convert_edges`) |

The user's project gets a workspace folder (default `decomposition/`) with
one subfolder per phase, `rfcs/`, `fitness/`, `config.json` and `state.json`.

## Start or resume

1. Look for `decomposition/state.json` in the project (or the folder the user
   names). If it exists, run `state.py show`, summarise where things stand in
   two or three lines, and continue from the current phase. Do not redo
   approved phases unless the user asks; use `state.py reopen` when they do.
2. If it does not exist, run `init_workspace.py <project_root>`. It detects
   languages and source roots and prints which adapter guides to read.
3. Read those adapter guides **before** touching the config. Then review
   `config.json` with the user: source roots, namespace prefixes, excludes,
   and what counts as a component in this codebase. Getting this mapping
   right decides whether every later number means anything.
4. Suggest committing the workspace to version control after each gate, so
   artifacts and RFCs have history.

## The phases

| # | Phase | Main outputs | Gate question |
|---|---|---|---|
| 0 | [Assess and choose an approach](references/phase-0-assess.md) | `assessment.md`, RFC | Component-based decomposition or tactical forking? |
| 1 | [Identify and size components](references/phase-1-identify-and-size.md) | `components.json/.md`, RFC with thresholds | Is the component inventory right, and which outliers matter? |
| 2 | [Gather common domain components](references/phase-2-gather-common-domain.md) | `candidates.json`, `common-domain.json`, RFC | What is shared, and how will it be consolidated? |
| 3 | [Flatten components](references/phase-3-flatten.md) | flattening plan, re-measured `components.json`, RFC | Where does each orphaned piece of code go? |
| 4 | [Determine component dependencies](references/phase-4-dependencies.md) | `edges.json`, `dependencies.json/.md/.mmd`, RFC | Is the coupling low enough to proceed, and what must be cut first? |
| 5 | [Create component domains](references/phase-5-domains.md) | `domains.json`, `domain-coupling.*`, RFC per boundary | Do these domains match how the business works? |
| 6 | [Create domain services](references/phase-6-services.md) | `services.json`, migration order, RFC per service | Which service goes first, and how do they talk? |

Read the phase guide when you enter a phase, not before; each one lists its
exact commands, outputs, fitness functions and what to show at the gate.

For tactical forking, follow `references/tactical-forking.md` instead of
phases 1–6.

## Running a phase

For every phase, in this order:

1. `state.py start N`.
2. Run the measurements the phase guide lists. Prefer a native extractor
   from the adapter when it exists and convert its output to the neutral
   schema; fall back to the built-in scripts otherwise. Record which one you
   used, because the artifacts carry a `confidence` field.
3. Write `NN-*/report.md` from `templates/phase-report.md`: key numbers,
   findings ordered by impact, proposed decisions, open questions.
4. Draft one RFC per decision with `new_rfc.py --title ... --phase N`
   (status Proposed). Fill in context with numbers, options, trade-offs,
   and the fitness functions that will protect it.
5. Add the phase's fitness functions: update `config.json` thresholds and
   rules for the generic checks, and generate the language-specific rules
   described in the adapter. Run `check_fitness.py --phase N`.
6. `state.py review N --rfc ...`, then present the gate: a short summary,
   the artifact paths, the proposed RFCs, the fitness results, and the
   specific questions the user must answer. Stop and wait.
7. When the user approves (possibly with changes), apply the changes, mark
   RFCs Accepted with `new_rfc.py --set-status`, run
   `state.py approve N --by "<name>"`, and only then move on.

`state.py` enforces the gate: it will not start a phase before the previous
one is approved, and will not approve one whose RFCs are not Accepted or
whose latest `check_fitness.py --phase N` run failed. Fix the cause, or put
the exception on record (an allow-list entry naming its RFC, or the
baseline below). Use `--force --reason "..."` only when the user explicitly
asks for an override; it is written to the history.

From Phase 4 on, record the current graph with
`check_fitness.py --update-baseline` and wire `run_guard.py` into CI (see
`references/fitness-functions.md`): existing cycles and edges are frozen,
and the build fails only on what gets worse.

If the user rejects or changes a proposal, update the artifact and the RFC
(or supersede it) before asking again. If a later phase reveals that an
earlier decision was wrong, propose `state.py reopen` for that phase; later
phases become `stale` and must be revisited.

## Working with the user

- Show numbers, not adjectives: "`orders` holds 29.9% of the code, 2.7 σ
  above the mean" rather than "orders is big".
- Separate what the scripts measured from what you infer. Say when data is
  low confidence (the regex extractor misses dependency injection, events,
  reflection and shared tables). `change_coupling.py` (git history) and
  `find_data_coupling.py` (ORM mappings, SQL) surface much of what imports
  miss; run them before trusting the graph.
- Suggestions are not decisions: `suggest_domains.py` gives a measured
  first cut for Phase 5, never the domain map itself.
- Ask about the business when the code cannot answer: who owns this, how
  often does it change, does it scale differently, does it fail differently.
- Keep gates short. A reviewer should decide in minutes; details live in
  the artifacts.
- Never move code, delete files or open pull requests in the user's project
  unless they ask for it in this conversation. Phase 3 and 6 can involve
  refactoring; propose the plan first.

## What this skill does not cover

Data decomposition (splitting tables and ownership), service granularity
trade-offs beyond the initial domain services, transactional sagas, and
contracts between services are later steps of a migration. When the user
reaches them, say so, point to the open RFCs that depend on them, and
record any decision in the same RFC log.
