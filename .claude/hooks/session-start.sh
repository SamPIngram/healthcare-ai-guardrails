#!/bin/bash
set -euo pipefail

# Only run in remote (Claude Code on the web) environments
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR}"

echo "==> Installing package with dev dependencies..."
pip install -e ".[dev]" --quiet

echo "==> Installing pre-commit hooks..."
pre-commit install

echo "==> Session start complete."
