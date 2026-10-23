# Training Lab: multi-source Model A learning

## Model roles

- **Model A** is the target that may be trained from selected local text corpora.
- **Model B** is an optional frozen teacher (configured LiteRT-LM model). It is used only to prepare candidate text and does not itself get trained by this workflow.
- The current default Model A trainer is character n-gram. It learns character/text statistics; it is not a supervised instruction-following model. The optional byte-level Transformer is a separate architecture.

## API workflow

All mutation routes require the configured admin password when one is set; for network use, set a strong `LIVING_AI_ADMIN_PASSWORD`.

1. `POST /api/training/datasets` accepts UTF-8 TXT, Markdown, or JSON up to 2 MB. It hashes content, rejects duplicate content, and records source/provenance in `data/training_lab/manifest.json`.
2. `GET /api/training/datasets` lists staged datasets.
3. `POST /api/training/teacher-prepare` uses the configured local LiteRT-LM Model B to draft candidates. If Model B is unavailable, it fails without silently substituting Model A.
4. Candidates are stored in `data/training_lab/pending/` and are **not training data by default**.
5. `POST /api/training/teacher-approve/{candidate_id}` explicitly approves a candidate and copies it to `data/training_lab/approved/`. Human review is still required before moving it into `data/corpus/`.
6. `GET /api/training/history` shows teacher-preparation history.
7. `POST /api/training/train` runs the existing character n-gram corpus trainer on its configured input directory. Training remains an explicit operation; upload does not auto-train or auto-promote a model.

Teacher output is untrusted and can be wrong. Check factual accuracy, licensing, privacy, duplicates, and sensitive data before approving. The staging API does not yet provide a browser-based upload/review interface, automatic dataset mixing, supervised fine-tuning, benchmark-based checkpoint promotion, or rollback of model weights. Those features must not be described as complete until implemented and tested. Current settings evolution rollback covers settings, not model weights.
