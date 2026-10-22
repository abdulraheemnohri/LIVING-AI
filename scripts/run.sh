#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x .venv/bin/python ] || { echo "Run bash scripts/install_android_debian.sh first."; exit 1; }
. .venv/bin/activate
exec python -m living_ai
