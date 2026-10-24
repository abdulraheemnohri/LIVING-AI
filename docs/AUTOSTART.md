# Automatic startup on Linux session start

Last reviewed: 2026-10-23

## Enable

After installing LIVING-AI and confirming it starts manually, run from the repository root:

```bash
bash scripts/enable_autostart.sh
```

The setup script:
- checks that the virtual environment exists;
- creates a private helper at `~/.config/living-ai/start-on-login.sh`;
- if an active systemd **user** manager is available, installs and enables `~/.config/systemd/user/living-ai.service`;
- configures restart-on-failure for the systemd service;
- otherwise explains how to connect the helper to the Linux terminal app's own startup/login feature.

The script does not change Android system settings or request root access.

## systemd service management

```bash
systemctl --user status living-ai.service
journalctl --user -u living-ai.service -f
systemctl --user restart living-ai.service
bash scripts/disable_autostart.sh
```

The app runs as the current Linux user, uses the repository's `.env` through `scripts/run.sh`, and keeps its normal local data directory. Protect `.env` and backups; do not run the service as root just to make autostart work.

## Important Android/Linux terminal limitation

Many Android Debian containers do not run systemd as PID 1 and do not have a persistent systemd user manager. In that case, the script only creates a helper; it cannot register an Android boot receiver. Configure the terminal app's supported startup/login command to run the helper, if the app offers that capability. Otherwise start it manually after opening the Linux environment.

Host reboot, Android battery restrictions, force-stop, terminal-app limitations, and container lifecycle can prevent a Linux process from starting at device boot. Do not claim device-boot startup is active unless the host integration has been configured and tested on that exact environment.

## Security and operation

- Keep the server bound to localhost unless remote access is deliberately secured.
- Set a strong `LIVING_AI_ADMIN_PASSWORD` in the private `.env` before using authenticated mutation endpoints.
- The systemd unit restarts on process failure, not after every configuration change.
- The setup does not install a scheduled GitHub auto-updater. Check updates with `bash scripts/check_github_updates.sh` and apply them deliberately with `bash scripts/update_android_debian.sh`.
- Disable service autostart with `bash scripts/disable_autostart.sh`; this does not delete the project, model files or database.

## Managed startup: opt-in automatic update and model download

The systemd user service now starts `scripts/start_managed.sh`. The wrapper starts the app normally by default. Large or code-changing network operations require explicit settings in the private `.env`:

```dotenv
LIVING_AI_AUTO_UPDATE=false
LIVING_AI_AUTO_DOWNLOAD_MODEL=false
```

To opt in, edit `.env` and set the chosen option to `true`. Then restart the service. Do not enable both without understanding the impact: the update step needs a clean `main` checkout, backs up data/config, and runs tests; the model downloader may consume several gigabytes and mobile data. Keep sufficient storage free.

Manual model download:

```bash
bash scripts/download_litert_model.sh
```

The downloader refuses to overwrite an existing model, uses a temporary `.part` file, supports resuming, checks free disk space and rejects obvious HTML error pages. It records a SHA-256 hash, but this hash is not publisher authentication by itself; verify against an official publisher checksum/signature when available. Confirm the repository and filename are correct for your target device before enabling automatic download.

The managed startup wrapper does not bypass update safety checks and does not fetch code if auto-update is disabled. If a network/download step fails, the service may exit and retry under systemd's restart policy. For Android containers without a systemd user manager, configure the terminal host's supported startup command to run `bash scripts/start_managed.sh`; the helper alone cannot force Android to start a container at device boot.

