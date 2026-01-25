#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-8000}"

if command -v python3 >/dev/null 2>&1; then
  python3 -m http.server "$PORT"
elif command -v python >/dev/null 2>&1; then
  python -m http.server "$PORT"
else
  echo "Python is required to run the local server." >&2
  exit 1
fi
