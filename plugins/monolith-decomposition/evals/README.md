# Evals for the `decompose` skill

Behaviour tests run with `claude plugin eval` (Claude Code 2.1+).
The script tests in `tests/` prove the numbers are right; these prove the
agent *uses* the skill the way it is meant to:

| Case | What it checks |
|---|---|
| `01-assessment-stops-at-gate` | initialises, measures, writes the assessment, then stops at the gate |
| `02-sizes-come-from-scripts` | numbers come from `size_components.py`, not from estimates |
| `03-resume-workspace` | resumes from `state.py` without redoing approved phases |
| `04-no-refactor-without-asking` | proposes a cycle break grounded in the analysis, edits no source code |
| `05-neg-unrelated-task` | does not fire on unrelated coding requests |

Cases 01–04 copy `examples/tiny-monolith` into the sandbox with a
`scaffold.sh`, so run them from a repository checkout and pass `--scaffold`
(it runs that bash script as you; read it first):

```bash
claude plugin eval plugins/monolith-decomposition --scaffold --judge-model sonnet --no-publish
claude plugin eval plugins/monolith-decomposition --case '01-*' --runs 1 --scaffold --no-publish   # one case
```

Each case runs with and without the plugin; the headline number is the
difference. Results land in `evals/results/` (git-ignored).
