#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."

say() { printf '\n[LIVING-AI installer] %s\n' "$*"; }
fail() { printf '[LIVING-AI installer] ERROR: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || fail "Python 3.11+ is required."
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit("Python 3.11+ is required; found " + sys.version.split()[0])
print("Python", sys.version.split()[0], "OK")
PY

for cmd in git curl df awk sha256sum; do
  command -v "$cmd" >/dev/null 2>&1 || fail "Required command '$cmd' is missing. Install it with your Debian package manager if permitted."
done

# On minimal Debian images, venv/SSL build prerequisites may need OS packages.
python3 -m venv .venv || {
  echo "Could not create the virtual environment." >&2
  echo "On Debian, install python3-venv and python3-dev using apt if your environment permits, then rerun." >&2
  exit 1
}
. .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
say "Installing application, tests, LiteRT-LM Python API, and LiteRT-LM CLI..."
python -m pip install -e ".[dev,litert]"

mkdir -p data/corpus data/logs models backups
if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env 2>/dev/null || true
  say "Created .env from .env.example. Set LIVING_AI_ADMIN_PASSWORD before using administrative features."
fi

# Model downloads can be multi-gigabyte. Default is enabled to satisfy the
# one-command setup request, but users can explicitly opt out in .env.
auto_download="${LIVING_AI_AUTO_DOWNLOAD_MODEL:-true}"
if [[ -f .env ]]; then
  env_value="$(grep -E '^LIVING_AI_AUTO_DOWNLOAD_MODEL=' .env | tail -n 1 | cut -d= -f2- | tr -d '[:space:]' || true)"
  [[ -n "$env_value" ]] && auto_download="$env_value"
fi
case "${auto_download,,}" in
  true|1|yes|on)
    say "Automatic LiteRT-LM model download is enabled. This may use several GB of storage and mobile data."
    bash scripts/download_litert_model.sh
    ;;
  false|0|no|off)
    say "Skipping model download because LIVING_AI_AUTO_DOWNLOAD_MODEL is disabled."
    ;;
  *)
    fail "LIVING_AI_AUTO_DOWNLOAD_MODEL must be true or false in .env."
    ;;
esac

say "Checking installed LiteRT-LM components..."
python - <<'PY'
import importlib.util
print("litert_lm Python API:", "available" if importlib.util.find_spec("litert_lm") else "not detected (API backend will be unavailable)")
PY
if command -v litert-lm >/dev/null 2>&1; then
  litert-lm --help >/dev/null
  echo "LiteRT-LM CLI: available"
else
  echo "WARNING: litert-lm CLI was not found. Check pip output and platform compatibility." >&2
fi

say "Running Python compilation and dashboard syntax checks..."
python -m compileall -q living_ai
if command -v node >/dev/null 2>&1; then
  for js in static/app.js static/projects.js; do [[ ! -f "$js" ]] || node --check "$js"; done
else
  echo "Node.js is not installed; skipped JavaScript syntax checks."
fi

say "Install steps completed. Start with: source .venv/bin/activate && bash scripts/run.sh"
