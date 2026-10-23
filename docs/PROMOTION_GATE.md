# Adaptive Learning & Regression Gate

The regression gate reviews **saved offline Evaluation Lab runs**. It is deliberately a promotion *gate*, not an auto-promoter.

## API

All endpoints fail closed unless `LIVING_AI_ADMIN_TOKEN` is configured. Send `Authorization: Bearer <token>`.

- `POST /api/evaluation/gate/check?window=3&min_score=1.0` — assess recent run history and persist a decision.
- `GET /api/evaluation/gate/history?limit=10` — retrieve previous decisions.

`window` is 1–10 (default 3); `min_score` is 0–1 (default 1.0). Missing history, scores below threshold, invalid result JSON, or a latest score below the prior baseline block eligibility. Failed case IDs and check names become remediation suggestions.

## Safety semantics

- A clean window means **eligible for human review only**.
- The gate does not promote a model, deploy code, train weights, approve goals, or start worker execution.
- Historical test scores are structural regression signals, not proof of semantic quality or security.
- The current evaluation suite tests the deterministic planner, not a remote provider or arbitrary candidate code.
