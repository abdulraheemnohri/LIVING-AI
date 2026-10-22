#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] || { echo "Run bash scripts/install_android_debian.sh first."; exit 1; }
# Load local configuration for this process only. Keep .env private and never commit secrets.
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
. .venv/bin/activate
exec python -m living_ai
