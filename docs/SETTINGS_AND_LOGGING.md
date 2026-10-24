# Runtime settings and persistent logs

## Dashboard settings

Open **Settings** after saving the admin password for the current browser tab.

The UI can update these SQLite-backed settings at runtime:

- temperature (0–2): generation sampling setting used by the character n-gram path.
- max_reply_chars (100–12,000): response length cap.
- retrieval_limit (0–50): number of memory matches retrieved for chat.
- log_level: DEBUG, INFO, WARNING, ERROR, or CRITICAL.

These are not secrets. Values are validated by the API and persisted in the configured database. Server bind address, port, data directory, model backend, model paths, optional remote provider, auto-update and model download are environment-controlled in .env; changing those values requires a restart.

## Log storage

Application logs are written to $LIVING_AI_DATA_DIR/logs/living-ai.log. If LIVING_AI_DATA_DIR is unset, the default is ./data/logs/living-ai.log. The log rotates at approximately 2 MB and keeps five rotated files. The Settings page supports filtering, viewing, and exporting the current plus rotated logs. Export is a plain-text download. Clearing logs permanently removes the current and rotated files and requires a confirmation in the UI.

Protected endpoints:

- GET /api/logs?limit=300&level=WARNING
- GET /api/logs/export
- POST /api/logs/clear

All require X-Admin-Password. Limits are bounded. Logs intentionally exclude passwords, API keys, chat message bodies, and imported document contents. Auth failures record the method and path only. Avoid enabling DEBUG in long-running deployments unless you need it, because it can produce more records.

## Backups and limitations

Logs are diagnostic records, not a guaranteed compliance audit or tamper-proof security ledger. They rotate and can be deleted by the local administrator. Export logs before an update or investigation if you need a durable copy. The SQLite database, project backups, and application logs are separate stores and should be backed up separately.
