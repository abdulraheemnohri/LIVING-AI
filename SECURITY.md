# Security model

- Bind to 127.0.0.1 by default.
- Set LIVING_AI_ADMIN_TOKEN before exposing the server beyond localhost.
- Mutation endpoints require bearer authentication when a token is configured.
- Remote inference is opt-in and transmits prompts to the configured provider.
- Evolution is restricted to an explicit settings allowlist.
- No arbitrary command execution, package installation, or source-code self-rewriting is provided.
- Keep .env, SQLite databases, backups, and model artifacts private.
- Imported text is data only and is never executed.


## Dashboard admin token

If `LIVING_AI_ADMIN_TOKEN` is configured, write operations require an
`Authorization: Bearer <token>` header. The dashboard Settings page lets you enter
the token; it is stored in the current browser tab's `sessionStorage` and cleared
when that tab's session ends. Do not paste the token into chat, source files, or
screenshots. If the token is empty in `.env`, write endpoints are not protected by
this token mechanism, so keep the service bound to localhost unless you configure
authentication and review the deployment boundary.

## Model diagnostics

`GET /api/model/status` reports the configured backend, selected model ID, device,
and whether the optional `torch` and `transformers` packages are importable. It
does not load model weights or guarantee that enough RAM is available to generate.

## From-scratch training boundary

The dashboard's native-model trainer reads from the configured data directory's corpus folder and writes only to the repository's models/tiny_transformer folder. Dashboard training inputs have conservative step, batch, sequence, width, and layer limits; CLI training remains more configurable. Training can still consume substantial CPU and memory, so use a small configuration on mobile hardware. The checkpoint is a local state dictionary, not an artifact to download from untrusted sources.

## Knowledge import

The mobile importer accepts TXT, Markdown and JSON text files up to 2 MB and stores extracted text in local memory. Public webpage import is user-initiated, accepts only text-oriented content types, limits response size, blocks obvious non-public destinations, and does not follow redirects. This is a best-effort defense, not a hardened general-purpose browser; keep the server bound to localhost and use an admin token before network exposure. Treat imported pages as untrusted data. Importing online content does not automatically train model weights.
