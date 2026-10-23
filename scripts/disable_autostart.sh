#!/usr/bin/env bash
# Disable LIVING-AI user-session autostart without deleting project data.
set -Eeuo pipefail
SERVICE_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/living-ai.service"
LOGIN_SCRIPT="$HOME/.config/living-ai/start-on-login.sh"
if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  systemctl --user disable --now living-ai.service || true
  if [[ -f "$SERVICE_FILE" ]]; then rm -f "$SERVICE_FILE"; fi
  systemctl --user daemon-reload
  echo "Disabled and removed the LIVING-AI user service."
fi
if [[ -f "$LOGIN_SCRIPT" ]]; then
  rm -f "$LOGIN_SCRIPT"
  echo "Removed the generated login-start helper."
fi
echo "Project files, .env, models, and data were not removed."
