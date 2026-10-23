# LIVING-AI Project A-to-Z Review

Last reviewed: 2026-10-23

This document distinguishes existing features from the intended architecture and features that still need implementation or runtime validation.

## 1. Project purpose

LIVING-AI is a local-first assistant workbench for Android Debian/Linux terminal environments. It combines a dashboard/API, local memory, trainable lightweight Model A, and a stronger optional Model B that can assist with preparing, reviewing and improving Model A's training data and training workflow.

The system is not a claim of consciousness or unrestricted autonomy. Model B must not silently alter code or model files; training jobs use explicit datasets, budgets, evaluation gates, checkpoints and rollback.

## 2. Correct two-model design

### Model A — trainable local model

Model A is the smaller, locally maintained model. It is the **training target** and may be updated from several selectable sources and methods:

1. **Manual upload:** user uploads supported TXT, Markdown, JSON, and (when a parser is implemented) CSV/JSONL datasets.
2. **Manual corpus folder:** user copies files into a configured training folder and starts a training job.
3. **Saved local memory:** user explicitly selects reviewed memories and exports them into a training corpus.
4. **Curated web knowledge:** user explicitly imports public pages or datasets, reviews provenance, then selects content for training.
5. **Model B-assisted dataset preparation:** Model B may classify, summarize, deduplicate, structure, label, generate examples, identify gaps, and propose corrections to the training dataset.
6. **Model B-generated synthetic examples:** optional and clearly marked as synthetic; require quality checks and preferably human review before inclusion.
7. **Evaluation-driven iteration:** failed evaluation cases can be converted into candidate training examples; they are not automatically accepted without configured review/gates.

Model A's existing character n-gram trainer is a lightweight baseline. It can learn character sequence statistics but does not perform instruction-following fine-tuning. If Model A is intended to become a capable instruction/chat model, its target architecture and trainer must support that objective. The existing optional tiny byte-level Transformer is separate and is not the same as the n-gram model.

### Model B — teacher/coach, not the training target

Model B is `litert-community/gemma-4-E2B-it-litert-lm`, served through LiteRT-LM for inference. It does **not** train or fine-tune itself in this architecture. It can assist the user and the training pipeline by:

- preparing and normalizing datasets;
- generating candidate instruction/response pairs or labels;
- checking examples for ambiguity, duplicates, formatting errors and contradictions;
- proposing improvements to Model A's training configuration;
- generating evaluation questions and expected-answer rubrics;
- explaining evaluation failures and suggesting candidate examples;
- helping prepare a training manifest and report.

Model B's output is untrusted candidate data. Validate structure, enforce size/resource limits, label synthetic content, prevent secrets/personal data leakage, and require human approval where appropriate. Do not let Model B execute shell commands, install packages, overwrite source code, or directly promote a checkpoint.

### Critical implementation status

The **teacher-assisted Model B → Model A pipeline is the intended architecture, but is not yet implemented end-to-end**. Current n-gram training exists; current memory import is not itself model training. LiteRT-LM is an inference runtime. It can generate assistance for Model A's dataset/training process, but does not provide Model B fine-tuning.

## 3. Runtime and storage

- Dashboard: `static/index.html`.
- API: `living_ai/app.py`.
- Routing: `living_ai/engine.py`.
- Model B inference adapter: `living_ai/litert_lm_backend.py`.
- Model A n-gram: `living_ai/model.py` and `living_ai/training.py`.
- Optional separate tiny Transformer: `living_ai/neural_lm.py` and `living_ai/neural_training.py`.
- Memory: SQLite modules under `living_ai/`.
- Model B expected artifact: `models/litert/gemma-4-E2B-it.litertlm`.
- Model A n-gram checkpoint: `models/char_ngram.json`.
- Training data should be stored in a configurable corpus directory and never committed by default.

## 4. Model B artifact and mobile resources

- Model card: [litert-community/gemma-4-E2B-it-litert-lm](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm)
- Expected artifact: `gemma-4-E2B-it.litertlm`, approximately 2.6 GB.
- A 6 GB Android device may face memory pressure. Run CPU-first and measure actual peak memory.
- The app must support clear states for missing model, missing optional dependency, model-load error, timeout, and fallback.

## 5. Installation

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Install optional LiteRT-LM support with:

```bash
python -m pip install -e '.[litert]'
mkdir -p models/litert
```

Download the official model artifact separately into the configured path. The application must not silently download a multi-gigabyte model.

## 6. Model A training workflow — intended end state

1. Select a training source (upload, corpus folder, selected memories, reviewed web imports, or Model B-assisted examples).
2. Parse files with format and size limits; reject malformed inputs.
3. Show a dataset preview, source/provenance, document count, duplicate count, and sensitive-data warnings.
4. Let the user include/exclude records and optionally ask Model B to prepare or label candidates.
5. Save a versioned, immutable training manifest with hashes and source references.
6. Run a bounded training job with a configurable step/time/memory budget.
7. Save a new checkpoint to a temporary versioned path, never overwrite the current best model in place.
8. Evaluate before/after on a fixed regression set and user-defined examples.
9. Compare quality, regressions, runtime and size. A Model B-generated score alone is not proof of correctness.
10. Require user approval to promote the candidate checkpoint; keep rollback to the previous version.
11. Record audit details: dataset version, method, parameters, model version, metrics, start/end time, status and errors.

For a character n-gram model, training updates statistical counts and cannot directly learn semantic instruction-following the way a fine-tuned neural language model can. Model B may still improve the text corpus and candidate examples, but the capability of Model A is bounded by its architecture.

## 7. Configuration inventory

- `LIVING_AI_MODEL_BACKEND`: selected response backend.
- `LIVING_AI_MODEL_PATH`: Model A n-gram checkpoint.
- `LIVING_AI_LITERTLM_MODEL_PATH`: Model B artifact.
- `LIVING_AI_LITERTLM_BACKEND`: runtime backend, start with CPU.
- `LIVING_AI_DATA_DIR`: local SQLite/data directory.
- `LIVING_AI_ADMIN_PASSWORD`: password for guarded mutations; set before network exposure.
- `LIVING_AI_ALLOW_REMOTE_PROVIDER`: remote provider opt-in, false by default.
- `LIVING_AI_AUTO_PROMOTE`: promotion flag, false by default.

Any additional dataset, teacher-assist or training-job settings should be added to the real settings schema and UI before being documented as active configuration.

## 8. Security and safety

- Model B suggestions are candidate data, not trusted policy or code.
- Uploaded files and imported pages are untrusted content and must never execute.
- Training must be explicit; importing or saving memory must not automatically change model weights.
- Avoid training on secrets, private user data or unlicensed material.
- Apply dataset size/format limits and resource budgets.
- Use versioned checkpoints, fixed evaluations, audit history and rollback.
- Model B must not directly overwrite Model A's active checkpoint or promote its own suggestions.
- Keep remote inference off unless explicitly approved; prompts sent to a remote provider leave the device.
- No arbitrary shell execution, autonomous package installation or source-code self-rewriting.

## 9. A-to-Z validation checklist

### Packaging and UI/API
- [ ] Clean Python 3.11+ install and optional-dependency install.
- [ ] Run tests, compile checks and lint.
- [ ] Test all dashboard pages, API routes, authentication and error states.
- [ ] Verify import limits, malformed files, URL restrictions, memory persistence and deletion.
- [ ] Verify no secrets, private corpora or model artifacts are committed.

### Model B
- [ ] Verify installed LiteRT-LM API compatibility with the adapter.
- [ ] Load Gemma artifact and generate a real response.
- [ ] Verify output password limits, timeout and clear failure states.
- [ ] Measure latency and peak RAM on the target Android device.
- [ ] Confirm Model B is only used for inference/teacher assistance, not claimed to be self-trained.

### Model A and teacher-assisted training
- [ ] Test manual file upload and folder-based dataset ingestion.
- [ ] Test selected-memory export and reviewed web-import selection.
- [ ] Add format validation, preview, deduplication, provenance and privacy warnings.
- [ ] Add a Model B dataset-preparation/labeling interface with synthetic-data labels.
- [ ] Add training-job records, cancellation/resource budgets and versioned checkpoints.
- [ ] Add before/after evaluation, regression checks, human promotion and rollback.
- [ ] Test Model B unavailable: manual Model A training must still work.
- [ ] Test malformed/adversarial teacher output is rejected or safely treated as data.
- [ ] Confirm memory import alone never starts training.

### Autonomy and evolution
- [ ] Verify staged PR dependencies and merge state before assuming features are on main.
- [ ] Ensure worker/scheduler is not started unexpectedly.
- [ ] Unknown/non-reversible actions remain blocked or held for approval.
- [ ] Approval is separate from execution; evaluation success is not automatic promotion.

## 10. Release criteria and known gaps

The main outstanding work is the actual Model B-assisted Model A training workflow: multi-source dataset selection, dataset preview/versioning, teacher assistance, bounded training jobs, evaluation, checkpoint promotion and rollback. The LiteRT-LM adapter and real generation also need runtime validation. Do not label the project fully tested until the test suite, UI/API smoke tests and target-device model generation have passed.
