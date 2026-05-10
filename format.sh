#!/usr/bin/env bash
# Run all frontend code quality checks.
# Usage:
#   ./format.sh         — check formatting and lint
#   ./format.sh --fix   — auto-format files, then lint

set -e

cd "$(dirname "$0")/frontend"

if [ "$1" = "--fix" ]; then
    echo "Formatting frontend files..."
    npx prettier --write "**/*.{js,html,css}"
    echo "Running ESLint..."
    npx eslint "**/*.js"
else
    echo "Checking frontend formatting and lint..."
    npm run check
fi
