# Evaluation Lab

The Evaluation Lab runs eight fixed, offline regression cases against the configured deterministic planner. It checks goal preservation, bounded step count, explicit review requirements, the action allowlist, payload size limits, and the review-only plan marker. Cases include punctuation, whitespace, long text, and Unicode/Urdu text.

## API

All endpoints fail closed unless `LIVING_AI_ADMIN_TOKEN` is configured. Send `Authorization: Bearer <token>`.

- `POST /api/evaluation/run` — execute the regression suite and persist the result in `evaluation_runs.sqlite3`.
- `GET /api/evaluation/runs?limit=10` — retrieve recent run history (limit 1–50).

The score is the percentage of test cases that passed all structural checks. A passing suite is not proof of semantic correctness, security against every input, or model quality. This suite evaluates the configured planner path only; it does not benchmark an optional remote model, train weights, approve goals, or execute actions. Each run is explicitly non-executing.
