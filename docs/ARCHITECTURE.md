# Architecture

1. Static dashboard in `static/`.
2. Litestar API in `living_ai/app.py`, including file and webpage import routes.
3. Retrieval-first chat routing in `living_ai/engine.py`.
4. SQLite memory and settings in `living_ai/db.py`.
5. Original character n-gram model in `living_ai/model.py`.
6. Explicit corpus training in `living_ai/training.py`.
7. Allowlisted proposal/evaluate/snapshot/promote/rollback flow in `living_ai/evolution.py`.

The built-in model is a transparent CPU-friendly baseline, not a high-quality general reasoning model. Imported content is treated as data. Remote inference is disabled unless explicitly enabled. The evolution engine cannot execute arbitrary commands or modify application source.


The SmolLM3/Hugging Face model backend has been removed. The default model is lightweight; the original Transformer requires compatible PyTorch support. Online import is user-initiated and stores text in local memory. It does not automatically train model weights. Imported content is untrusted data.
