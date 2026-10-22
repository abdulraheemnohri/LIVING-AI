# Evaluation Lab

The Evaluation Lab records explicit human feedback in local SQLite so later planning can retrieve relevant experience. It is not an autonomous evaluator: a person supplies the score and outcome.

## Safety and privacy

- All `/api/evaluations` routes fail closed with HTTP 503 until `LIVING_AI_ADMIN_TOKEN` is configured; requests then require `Authorization: Bearer <token>`.
- Data is stored in `learning.sqlite3` under `LIVING_AI_DATA_DIR` (defaults to the application's data directory).
- Recording feedback does not run queued actions, start a worker, or train a model.
- The current retrieval method is lightweight lexical matching, not semantic embeddings.
- Avoid storing secrets or private personal information in feedback fields.

## API

- `GET /api/evaluations/summary` — count, average score and positive count.
- `GET /api/evaluations?q=urdu&limit=10` — search feedback; limit is clamped to 1–20.
- `POST /api/evaluations` — record `goal`, `score` (0–1), `outcome`, optional `feedback`, `plan_summary`, and up to 20 tags.

The UI's Evaluation Lab view can record a reviewed outcome, search prior evaluations, and display summary statistics. Imported content is not automatically treated as evaluation feedback.
