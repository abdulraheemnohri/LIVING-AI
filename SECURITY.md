# Security model

- Bind to 127.0.0.1 by default.
- Set LIVING_AI_ADMIN_TOKEN before exposing the server beyond localhost.
- Mutation endpoints require bearer authentication when a token is configured.
- Remote inference is opt-in and transmits prompts to the configured provider.
- Evolution is restricted to an explicit settings allowlist.
- No arbitrary command execution, package installation, or source-code self-rewriting is provided.
- Keep .env, SQLite databases, backups, and model artifacts private.
- Imported text is data only and is never executed.
