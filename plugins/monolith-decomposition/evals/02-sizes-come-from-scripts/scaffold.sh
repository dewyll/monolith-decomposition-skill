#!/usr/bin/env bash
# Copies the repository's example monolith into the eval sandbox (cwd).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
src="$here/../../../../examples/tiny-monolith"
[ -d "$src" ] || { echo "example not found at $src (run evals from a repository checkout)" >&2; exit 1; }
cp -R "$src/." .
rm -rf decomposition scratch
find . -name __pycache__ -type d -prune -exec rm -rf {} +
