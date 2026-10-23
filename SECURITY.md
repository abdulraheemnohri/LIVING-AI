# Security model

## Deployment

- Bind to `127.0.0.1` by default.
- Before exposing the service beyond localhost, set `LIVING_AI_ADMIN_PASSWORD` and put the app behind a suitable network access-control layer.
- Protected endpoints fail closed with HTTP 503 when `LIVING_AI_ADMIN_PASSWORD` is unset or empty. When configured, they require `X-Admin-Password: <password>` and reject incorrect passwords with HTTP 401.
- Keep `.env`, SQLite databases, exported corpora, backups and model artifacts private.
- Do not commit API keys or paste admin passwords into chats, screenshots or issue reports.

## Remote provider and privacy

Remote inference is disabled unless `LIVING_AI_ALLOW_REMOTE_PROVIDER=true`. If enabled, user prompts are sent to the configured provider URL; review that provider's privacy, retention and terms before enabling it. Local LiteRT-LM inference does not need to send prompts to a remote inference provider, but downloading the model requires network access.

## Model and training boundaries

- Model B is the pre-converted Gemma 4 E2B Instruct LiteRT-LM artifact. LiteRT-LM is an inference runtime, not the model's training framework.
- The repository does not yet implement a tested Model B fine-tuning/evaluation/conversion pipeline.
- Existing n-gram training and the optional tiny from-scratch Transformer trainer are separate legacy features; neither fine-tunes Gemma.
- Model status checks dependency imports and file presence; it does not load weights, prove generation works or guarantee sufficient RAM.
- Review licensing and provenance of every training corpus. Do not train on data you are not authorized to use.

## Knowledge import

The importer accepts TXT, Markdown and JSON text files up to the configured limit. Public webpage import is user-initiated, accepts text-oriented content, caps response size, blocks obvious non-public destinations and avoids following redirects. This is best-effort protection, not a hardened browser or a complete network sandbox. Keep the service local unless you have reviewed the threat model.

Imported pages and files are untrusted data. Do not treat their content as privileged instructions or execute embedded code. Imported memory is not automatically training data; the explicit corpus-export operation must be reviewed before training.

## Evolution and autonomy

- Settings evolution is restricted to an explicit allowlist and records proposals/evaluations/snapshots for rollback.
- The autonomy foundation is registered-action-based. Unknown and non-reversible actions must remain blocked or held for review.
- Human review eligibility is not the same as approval, execution or successful deployment.
- Do not enable background scheduling, unattended execution or automatic promotion unless the specific code path is present, reviewed and tested.
- The application is not allowed to execute arbitrary shell commands, install packages autonomously or rewrite its source code.

## Dashboard admin password

When configured, the dashboard sends the password for guarded writes and stores it in the current browser tab's `sessionStorage`; it should be cleared when that tab's session ends. Use a trusted device and do not share screenshots that expose the password.

## Verification checklist

Before any non-local deployment:
1. Configure a strong admin password and verify unauthenticated mutation requests fail.
2. Review every registered route for authentication and data exposure.
3. Run tests and lint in the target environment.
4. Confirm logs do not expose secrets.
5. Check upload limits, URL-import behavior and database file permissions.
6. Test rollback and backup restore.
7. Confirm remote inference is disabled unless explicitly approved.
8. Verify LiteRT-LM model path, runtime API compatibility and fallback behavior.
