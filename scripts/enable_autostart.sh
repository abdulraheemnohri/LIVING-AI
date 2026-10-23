#!/usr/bin/env bash
# Configure LIVING-AI to start automatically when the Linux user session starts.
# On systems with a working systemd user manager, install a user service.
# In Android Linux containers without systemd, create an explicit login-start helper.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd -P)"
USER_NAME="$(id -un)"
SERVICE_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
SERVICE_FILE="$SERVICE_DIR/living-ai.service"
AUTOSTART_DIR="$HOME/.config/living-ai"
LOGIN_SCRIPT="$AUTOSTART_DIR/start-on-login.sh"

[[ -x "$ROOT/.venv/bin/python" ]] || {
  echo "Virtual environment missing. Run: bash scripts/install_android_debian.sh" >&2
  exit 1
}
command -v git >/dev/null 2>&1 || { echo "Git is required." >&2; exit 1; }

mkdir -p "$AUTOSTART_DIR"
cat > "$LOGIN_SCRIPT" <<EOF
#!/usr/bin/env bash
set -Eeuo pipefail
cd "$ROOT"
exec bash "$ROOT/scripts/run.sh"
EOF
chmod 700 "$LOGIN_SCRIPT"

if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p "$SERVICE_DIR"
  cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=LIVING-AI local assistant
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT
ExecStart=/usr/bin/env bash $ROOT/scripts/run.sh
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
KillSignal=SIGINT
UMask=0077

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable --now living-ai.service
  echo "LIVING-AI systemd user service enabled and started."
  echo "Status: systemctl --user status living-ai.service"
  echo "Logs:   journalctl --user -u living-ai.service -f"
  echo "Stop:   systemctl --user disable --now living-ai.service"
  if command -v loginctl >/dev/null 2>&1; then
    echo "Boot persistence depends on a systemd user manager being started by the host."
    echo "Optional (requires admin permission and system policy): loginctl enable-linger $USER_NAME"
  fi
else
  echo "No active systemd user manager detected."
  echo "Created login-start helper: $LOGIN_SCRIPT"
  echo "This helper starts LIVING-AI when you run it; it does NOT itself register an Android boot receiver."
  echo "If your Linux terminal app offers a startup/login command, configure it to run:"
  echo "  bash \"$LOGIN_SCRIPT\""
  echo "Otherwise start manually with: bash \"$LOGIN_SCRIPT\""
  echo "Android containers usually cannot guarantee boot startup without host-app support."
fi
