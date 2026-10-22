# LIVING-AI Project A-to-Z Review

Last reviewed: 2026-10-23

This document separates confirmed repository design from features that still need implementation or runtime validation. Reading source or seeing a GitHub commit does not prove that dependencies install, tests pass, or inference works on a phone.

## 1. Project purpose

LIVING-AI is a local-first assistant workbench targeting Debian/Linux terminal environments on Android. Its current foundations include a Litestar API, browser dashboard, SQLite memory, text import, lightweight local model options, optional LiteRT-LM inference, and reversible settings evolution.

It is not a claim of consciousness or unrestricted autonomy. The default safety design should remain review-first and bounded.

## 2. Model architecture and responsibilities

| Component | Intended role | Current state |
|---|---|---|
| Model A: character n-gram | Lightweight fallback/baseline; not the requested training target | Existing trainer/inference code is present |
| Model B: Gemma 4 E2B Instruct LiteRT-LM | Primary local language model inference | Adapter/configuration exists; actual runtime compatibility and generation need a smoke test |
| Model B training | Fine-tune/train a compatible source model, evaluate it, export/convert to LiteRT-LM | **Not implemented** |
| Tiny byte-level Transformer | Separate educational model trained from random initialization | Existing optional trainer; not Gemma and not Model B |
| SQLite memory | Save and retrieve notes/imported chunks | Existing feature; not equivalent to model-weight training |
| Remote OpenAI-compatible endpoint | Optional remote fallback/provider | Opt-in; prompt data leaves device when enabled |

### Model B artifact

- Hugging Face repository: [litert-community/gemma-4-E2B-it-litert-lm](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm)
- Expected file: `gemma-4-E2B-it.litertlm`
- Expected local path: `models/litert/gemma-4-E2B-it.litertlm`
- File size is about 2.6 GB; memory varies by device and backend. A 6 GB phone may experience pressure.
- LiteRT-LM is an inference runtime. Do not promise training/fine-tuning directly through LiteRT-LM.

## 3. Installation and first run

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open `http://127.0.0.1:8000`. Python 3.11+ is specified by project metadata. Check the install script and target architecture before assuming every optional package is available.

To install LiteRT-LM integration:

```bash
python -m pip install -e '.[litert]'
mkdir -p models/litert
```

Download the model artifact separately or set `LIVING_AI_LITERTLM_MODEL_PATH` to the exact local file. The app does not automatically download 2.6 GB model files.

## 4. Configuration

| Variable | Purpose | Safe default |
|---|---|---|
| `LIVING_AI_HOST` | Server bind address | `127.0.0.1` |
| `LIVING_AI_PORT` | HTTP port | `8000` |
| `LIVING_AI_DATA_DIR` | SQLite/data/corpus directory | `./data` |
| `LIVING_AI_ADMIN_TOKEN` | Bearer token for guarded mutations | Set a strong value before network exposure |
| `LIVING_AI_MODEL_BACKEND` | `hybrid`, `litert_lm`, `char_ngram`, tiny-transformer aliases | `hybrid` in the example |
| `LIVING_AI_MODEL_PATH` | Character n-gram checkpoint | `models/char_ngram.json` |
| `LIVING_AI_LITERTLM_MODEL_PATH` | Local Gemma LiteRT-LM file | `models/litert/gemma-4-E2B-it.litertlm` |
| `LIVING_AI_LITERTLM_BACKEND` | LiteRT runtime backend | `cpu` |
| `LIVING_AI_ALLOW_REMOTE_PROVIDER` | Allow remote inference | `false` |
| `LIVING_AI_AUTO_PROMOTE` | Evolution auto-promotion flag | `false` |

Copy `.env.example` to `.env`; do not commit secrets. Review the exact behavior of every environment variable against the source before relying on it.

## 5. Main feature inventory

- Dashboard and Litestar API.
- Health/status and model-status endpoints.
- Chat routing across selected local/optional remote backends.
- SQLite memory creation, search and deletion.
- TXT/Markdown/JSON import and user-triggered public text-page import.
- Explicit export of saved memory to a corpus for human review.
- Character n-gram training.
- Optional from-scratch tiny Transformer training/inference.
- Settings proposals, evaluation, snapshots, promotion and rollback.
- Optional autonomy/planner/learning/evaluation modules across staged branches/PRs. Confirm branch/merge status and UI/API wiring before treating them as shipped features.
- Documentation and shell scripts for installation and training.

## 6. Important boundaries

- Memory import does not update model weights.
- Corpus export only prepares text; review provenance, rights, quality and sensitive data before training.
- Existing n-gram and tiny Transformer training do not train Gemma.
- Webpage import is not a continuous crawler or a fully isolated browser.
- LiteRT model-file presence does not prove the installed Python API is compatible or that enough RAM is available.
- Remote provider use transmits prompts to the configured endpoint.
- No arbitrary shell execution, source-code self-rewrite or autonomous package installation should be enabled by this project.
- A proposed or evaluated change is not automatically a safe promotion; keep rollback and human review.

## 7. A-to-Z validation checklist

### Repository and packaging
- [ ] Install the base package in a clean Python 3.11+ environment.
- [ ] Install the development extra and run tests.
- [ ] Run Ruff/lint and compile checks.
- [ ] Confirm all README links point to existing files.
- [ ] Confirm shell scripts use safe paths, fail on errors and are executable.
- [ ] Confirm optional dependencies do not break the base install.

### API and dashboard
- [ ] Start server and check `GET /api/health`, `GET /api/status`, `GET /api/model/status`.
- [ ] Exercise chat with each configured backend.
- [ ] Verify each mutation route's authentication behavior with and without an admin token.
- [ ] Test file type/size limits, malformed JSON, empty content and oversized inputs.
- [ ] Test webpage URL validation, redirects, non-public IP rejection and timeout handling.
- [ ] Check every dashboard navigation page and browser console errors.
- [ ] Confirm UI handles missing model, missing optional dependency and API error responses.

### Model A and Model B
- [ ] Train and load the n-gram checkpoint using a small fixture corpus.
- [ ] Confirm hybrid mode attempts Model B first and falls back on missing dependency, missing file and generation errors.
- [ ] Verify the installed LiteRT-LM Python API matches `living_ai/litert_lm_backend.py`.
- [ ] Run a real generation smoke test with the Gemma 4 E2B artifact.
- [ ] Verify `max_new_tokens` is actually enforced by the adapter/runtime.
- [ ] Measure peak memory, latency and stability on target Android Debian hardware.
- [ ] Verify strict `litert_lm` mode returns a clear error when unavailable.
- [ ] Do not claim Model B training until a source-model training/fine-tuning, evaluation and conversion pipeline is implemented and tested.

### Memory, data and safety
- [ ] Test SQLite initialization, persistence, search, deletion and export.
- [ ] Verify imported content remains inert data.
- [ ] Review exported corpora for personal data and licensing before training.
- [ ] Test settings proposal, evaluation, promotion, snapshot and rollback.
- [ ] Verify no secrets or model artifacts are tracked by Git.
- [ ] Keep remote inference off unless explicitly approved.

### Autonomy/evolution
- [ ] Confirm staged PRs are merged in the documented order before testing dependent modules.
- [ ] Confirm no worker/scheduler starts automatically.
- [ ] Verify unknown and non-reversible actions remain held/blocked.
- [ ] Verify approval is separate from execution.
- [ ] Test cycle budgets, pause/resume, audit persistence and failure paths.
- [ ] Regression gates only qualify for review; they must not silently deploy code or replace model weights.

## 8. Known gaps at this review

1. The Model B training/fine-tuning → evaluation → LiteRT-LM export pipeline is absent.
2. LiteRT-LM adapter API compatibility and real model generation have not been verified in this review environment.
3. The full test suite, lint checks, Android install and live inference were not executed as part of this documentation pass.
4. Staged autonomy/evaluation PRs may not be present on the default branch; review PR state and merge dependencies separately.
5. A model status file/dependency check is only a diagnostic, not an inference readiness guarantee.
6. Legacy training UI still refers to n-gram/tiny Transformer; keep it clearly labelled as not Model B training until the workflow is replaced.

## 9. Release criteria

Do not call the project “fully tested” until CI passes on the default branch and the target Debian environment has a successful install, API tests, UI smoke test, LiteRT-LM model generation test, hybrid fallback test, and a documented resource measurement. Keep the Model B trainer marked pending until that end-to-end workflow exists.
