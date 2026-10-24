#!/usr/bin/env bash
# Controlled startup orchestration. Risky/network-heavy operations are opt-in in .env.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd -P)"
if [[ -f .env ]]; then set -a; . ./.env; set +a; fi

case "${LIVING_AI_AUTO_UPDATE:-false}" in
  true|TRUE|1|yes|YES)
    echo "[startup] Automatic GitHub update is enabled."
    # Updater intentionally refuses dirty/diverged working trees and runs tests.
    bash "$ROOT/scripts/update_android_debian.sh"
    ;;
  *)
    echo "[startup] Automatic GitHub update is disabled. Set LIVING_AI_AUTO_UPDATE=true to opt in."
    ;;
esac

case "${LIVING_AI_AUTO_DOWNLOAD_MODEL:-false}" in
  true|TRUE|1|yes|YES)
    echo "[startup] Automatic LiteRT-LM model download is enabled."
    bash "$ROOT/scripts/download_litert_model.sh"
    ;;
  *)
    echo "[startup] Automatic model download is disabled. Set LIVING_AI_AUTO_DOWNLOAD_MODEL=true to opt in."
    ;;
esac

exec bash "$ROOT/scripts/run.sh"
