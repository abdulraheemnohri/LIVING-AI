#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v python3 >/dev/null || { echo "Python 3 is required."; exit 1; }
python3 -m venv .venv || {
  echo "Could not create venv. On Debian, python3-venv may be missing."
  echo "Install it if your environment permits, then rerun this script."
  exit 1
}
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
mkdir -p data/corpus models backups
[ -f .env ] || cp .env.example .env
echo "Install complete. Run: source .venv/bin/activate && bash scripts/run.sh"
