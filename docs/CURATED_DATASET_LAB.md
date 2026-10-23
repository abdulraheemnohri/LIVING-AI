# Curated Learning Dataset Lab (Phase 13)

This module creates a human-reviewed dataset staging area for future local training. It does not automatically learn from raw memory, call a remote model, or train weights.

## Authentication

Configure `LIVING_AI_ADMIN_PASSWORD` in the private environment and send `X-Admin-Password: <password>`. All endpoints fail closed if the password is missing or incorrect.

## Workflow

1. Submit a candidate example: `POST /api/dataset/examples` with JSON `{"input":"...","expected_output":"...","source":"manual"}`.
2. Review pending examples: `GET /api/dataset/examples?status=pending&limit=100`.
3. Explicitly approve or reject: `POST /api/dataset/examples/{example_id}/review` with `{"decision":"approved"}`, `{"decision":"rejected"}`, or `{"decision":"pending"}`.
4. Export approved rows only: `POST /api/dataset/export`.
5. The export is written to `<LIVING_AI_DATA_DIR>/corpus/curated_training.jsonl` (default `./data/corpus/curated_training.jsonl`).

The API validates non-empty bounded input/output/source fields and deduplicates identical input/output pairs using SHA-256. The JSONL is UTF-8 with Unicode preserved. Exports are capped at 5,000 examples. Rejected and pending examples are never exported. Exporting does not start training.

## JSONL format

Each line contains `id`, `input`, `output`, `source`, and `created_at`. Treat this as a curated interchange format; the existing from-scratch trainer consumes text corpora, not this structured JSONL format directly. Convert or adapt it explicitly before training, and inspect all examples for privacy, rights, and quality.
