# Architecture and Data Flow

## Runtime overview

1. `static/index.html` provides the dashboard UI.
2. `living_ai/app.py` exposes the Litestar HTTP API and initializes the SQLite database.
3. `living_ai/engine.py` routes chat requests based on `LIVING_AI_MODEL_BACKEND`.
4. `living_ai/litert_lm_backend.py` optionally loads a local `.litertlm` model through the LiteRT-LM Python runtime.
5. `living_ai/memory.py` and `living_ai/db.py` persist and retrieve local notes/settings.
6. `living_ai/model.py` and `living_ai/training.py` implement the character n-gram baseline.
7. `living_ai/neural_lm.py` and `living_ai/neural_training.py` implement a separate, optional byte-level Transformer trained from random initialization.
8. `living_ai/knowledge.py` parses supported text files and fetches user-requested public web pages.
9. `living_ai/evolution.py` manages allowlisted settings proposals, evaluation, snapshots, promotion and rollback.
10. Optional autonomy modules provide a review-first goal queue, registered-action worker, planner, scheduler, learning store, evaluation lab and regression gate. These modules must not be assumed active just because they exist in the repository; check whether their PRs are merged into the default branch and whether the UI/API routes are wired.

## Two-model intent

- **Model A:** character n-gram, used as a lightweight fallback/baseline. It is not the desired training target.
- **Model B:** `litert-community/gemma-4-E2B-it-litert-lm`, served as a pre-converted `gemma-4-E2B-it.litertlm` artifact.
- **Hybrid mode:** tries Model B first; on supported load/runtime failures, it falls back to saved memory or Model A.
- **Training boundary:** LiteRT-LM is an inference runtime, not a training framework. A compatible external fine-tuning pipeline, evaluation step and conversion/export step are still needed to produce a new Model B artifact. Do not describe the Model B trainer as implemented until it exists and is tested.
- The optional tiny Transformer is an independent legacy/educational feature, not Gemma training and not a substitute for the requested Model B training pipeline.

## Request path

```text
Browser
  -> Litestar /api/chat
  -> engine.respond(message)
  -> SQLite lexical memory retrieval
  -> selected backend
       hybrid/litert_lm -> LiteRT-LM Gemma 4 E2B
            hybrid failure -> local memory -> character n-gram -> starter response
       tiny_transformer -> local PyTorch checkpoint
       char_ngram -> local n-gram checkpoint or memory/starter response
  -> JSON response
```

## Storage

- SQLite database and corpus exports live under `LIVING_AI_DATA_DIR` (default `./data`).
- Character n-gram checkpoint default: `models/char_ngram.json`.
- Tiny Transformer checkpoint default: `models/tiny_transformer/`.
- Gemma LiteRT-LM artifact default: `models/litert/gemma-4-E2B-it.litertlm`.
- Keep model files, local databases, exported corpora and secrets out of public commits.

## Trust boundaries

- Imported text and retrieved memories are untrusted data, never executable instructions.
- Web import is explicit and intended for public text pages; it is not a general browser or a complete SSRF-proof network sandbox.
- Remote inference is opt-in and transmits prompts to the configured provider.
- Mutation routes use bearer authentication only when `LIVING_AI_ADMIN_TOKEN` is set. An empty token means that token authentication is not enforced; therefore keep the server bound to localhost unless another access-control layer is configured.
- Evolution changes are restricted to a small settings allowlist and use snapshots/audit/rollback.
- The bounded autonomy foundation is not a general shell agent. Registered-action checks, explicit approvals and manual execution boundaries must remain in force.
- No source-code self-rewrite, arbitrary shell execution, automatic package installation or unattended crawler is part of the intended safe baseline.

## Known validation gaps

The repository files and docs can be inspected through GitHub, but that alone does not prove the application installs or runs. A release-ready review must run the test suite and lint checks in the target Debian/Python environment, verify the exact LiteRT-LM Python API against the installed runtime, exercise Model B generation, verify fallback behavior, and check all API routes/UI pages. See [PROJECT_A_TO_Z.md](PROJECT_A_TO_Z.md) for the current checklist.
