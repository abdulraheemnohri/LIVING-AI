# Runtime settings and application logs

The Settings page provides local runtime configuration, model/runtime visibility, and a protected log viewer.

## Persistent logs

- Log path: `$LIVING_AI_DATA_DIR/logs/living-ai.log` (default: `./data/logs/living-ai.log`).
- Rotation: 2 MB per file with up to five rotated backups.
- Supported levels: DEBUG, INFO, WARNING, ERROR, CRITICAL.
- Protected endpoints: `GET /api/logs`, `GET /api/logs/export`, and `POST /api/logs/clear`. All require the configured `X-Admin-Password`.
- The dashboard supports level filtering, refresh, export, and explicit clear with confirmation.
- Current application events include startup/module initialization, authentication failures (without credentials), chat request length/backend completion, chat failures, and runtime-setting changes.

Privacy: chat text, memory contents, imported file contents, passwords and API keys are intentionally excluded from application log messages. Logs are local operational records, not a complete transcript or immutable security audit. The existing database audit trail remains separate. Clearing logs is destructive and cannot be undone; export important records first.

## Runtime settings

The Settings page can persist these SQLite-backed controls without restart:
- `temperature`: 0–2.
- `max_reply_chars`: 100–12,000.
- `retrieval_limit`: 0–50.
- `log_level`: DEBUG, INFO, WARNING, ERROR, CRITICAL.

All changes require admin password authorization and are validated server-side. Settings remain on the device under `LIVING_AI_DATA_DIR`.

## Environment-only settings

The page displays, but does not silently rewrite, deployment-sensitive settings such as bind host, port, model backend, model path, automatic GitHub updates, and automatic model download. Change these in the private `.env` file and restart the app. Keep the host bound to `127.0.0.1` unless you understand the network exposure and have set a strong password.

## Limitations

This logging layer records selected operational events and exceptions; it does not yet capture every HTTP request or every internal model token. Rotating files bound storage, so older logs are eventually overwritten. For a durable compliance-grade archive, export logs to separately managed storage.
