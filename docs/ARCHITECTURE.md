# Architecture and Data Flow

## Runtime overview

1. `static/index.html` provides the dashboard UI.
2. `living_ai/app.py` exposes the Litestar HTTP API.
3. `living_ai/engine.py` routes user chat to the selected response backend.
4. `living_ai/litert_lm_backend.py` provides optional Model B inference using a local LiteRT-LM artifact.
5. `living_ai/memory.py` and `living_ai/db.py` store local memories and settings.
6. `living_ai/model.py` and `living_ai/training.py` implement trainable Model A as a character n-gram baseline.
7. `living_ai/neural_lm.py` and `living_ai/neural_training.py` implement a separate optional byte-level Transformer trained from random initialization.
8. `living_ai/knowledge.py` handles supported text import and user-requested public webpage import.
9. Optional evolution/autonomy modules provide bounded, review-first actions; check merge state and route/UI wiring before treating staged modules as shipped.

## Model roles

**Model A — training target:** the locally maintained model that users can train/update. The current character n-gram implementation is lightweight and can learn character sequence statistics; it is not a neural instruction-following model. The optional tiny Transformer is separate and does not share weights with the n-gram model.

**Model B — teacher/coach:** `litert-community/gemma-4-E2B-it-litert-lm`. It is loaded for inference and can help prepare, classify, label, deduplicate, explain or generate candidate training examples for Model A. Model B is not the training target and is not trained by this project.

**Important status:** the intended Model B → Model A teacher-assisted workflow is not yet implemented end-to-end. The existing Model A training code remains independently usable. LiteRT-LM is an inference runtime, not a fine-tuning engine.

## Intended Model A data sources

- User-uploaded text files/datasets.
- Files copied to the configured corpus directory.
- User-selected, reviewed local memory exports.
- User-selected, reviewed public-web imports.
- Model B-prepared or Model B-generated candidate examples, visibly labelled as synthetic/teacher-produced.
- Evaluation failures converted into candidate examples for review.

Every source should pass format/size validation and provenance/privacy checks. No data should train automatically merely because it was imported or saved as memory.

## Intended training pipeline

```text
Upload / corpus folder / selected memory / reviewed web data
                         |
                         v
              Parse + validate + preview
                         |
              Optional Model B assistance
                         |
                         v
         Deduplicate + provenance + human review
                         |
                         v
          Versioned dataset and training manifest
                         |
                         v
                Bounded Model A training
                         |
                         v
              Candidate checkpoint version
                         |
                         v
           Fixed evaluation + regression gate
                         |
                         v
                Human approval to promote
                         |
                  Rollback available
```

Model B output is untrusted candidate data. It must never be executed as code or allowed to overwrite active checkpoints directly.

## Chat request path

```text
Browser -> Litestar /api/chat -> engine
  -> optional local memory context
  -> Model B / LiteRT-LM when selected
  -> fallback to local memory or Model A when hybrid mode allows
  -> response
```

## Storage conventions

- SQLite and user data: `LIVING_AI_DATA_DIR` (default `./data`).
- Model A n-gram checkpoint: `models/char_ngram.json`.
- Optional tiny Transformer: `models/tiny_transformer/`.
- Model B artifact: `models/litert/gemma-4-E2B-it.litertlm`.
- Versioned datasets/checkpoints and audit records are intended additions for the full teacher-assisted training workflow; do not assume all are implemented.

## Trust and safety boundaries

- Uploaded/imported content and Model B output are untrusted data.
- Training is explicit and bounded; memory import never directly changes model weights.
- No arbitrary shell execution, package installation or source-code self-rewriting.
- Remote inference is opt-in and transmits prompts to the configured provider.
- Mutation endpoints are protected by the configured admin-token mechanism only where the shared auth guard is applied. Empty token means no token-based protection; keep the server local by default.
- Model B cannot approve its own candidate dataset or promote a checkpoint. Evaluation qualifies candidates for review; a human decides promotion.
