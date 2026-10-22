# Android Debian/Linux and Pixel-class devices

LIVING AI targets a Debian userspace terminal on Android, including the Google Android Linux terminal environment. These steps are not Termux-specific. Python 3.11+ is required by `pyproject.toml`.

## Setup

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open `http://127.0.0.1:8000` in a browser reachable from the Linux environment. If localhost is isolated, use the terminal environment's supported port forwarding. The server binds to localhost by default.

## Model B: Gemma 4 E2B Instruct

The intended Model B artifact is `litert-community/gemma-4-E2B-it-litert-lm`, file `gemma-4-E2B-it.litertlm`. The file is approximately 2.6 GB on disk. See the [official model card](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm) for current device-specific performance and requirements.

```bash
source .venv/bin/activate
python -m pip install -e '.[litert]'
mkdir -p models/litert
# Download gemma-4-E2B-it.litertlm from the official Hugging Face repository
# into models/litert/, or configure LIVING_AI_LITERTLM_MODEL_PATH.
```

For an independent runtime smoke test, the official CLI documents:

```bash
python -m pip install -U litert-lm
litert-lm run --from-huggingface-repo=litert-community/gemma-4-E2B-it-litert-lm gemma-4-E2B-it.litertlm --prompt="Hello"
```

This CLI test is not the same as verifying the LIVING AI adapter. The app requires a readable local model file at the configured path. Use CPU mode first. The model card reports about 1.7 GB CPU memory on one tested Android flagship; this is not a guarantee for every device or Debian environment. A 6 GB phone may experience memory pressure when the OS, browser, Python process and model are all active.

## Environment

Set the following in a local `.env` file (copy `.env.example` first):

```dotenv
LIVING_AI_MODEL_BACKEND=hybrid
LIVING_AI_MODEL_PATH=models/char_ngram.json
LIVING_AI_LITERTLM_MODEL_PATH=models/litert/gemma-4-E2B-it.litertlm
LIVING_AI_LITERTLM_BACKEND=cpu
```

## Mobile workflow

- Dashboard → Import Data: import TXT, Markdown or JSON files, or explicitly fetch a public text webpage.
- Dashboard → Memory: search and delete saved memory chunks.
- Dashboard → Training: existing controls train the n-gram baseline and optional from-scratch tiny Transformer. They do **not** fine-tune Gemma.
- Model status: check the configured backend and whether the local LiteRT-LM artifact is present. A file-presence check does not prove runtime compatibility or available RAM.

## Resource advice

- Start tiny Transformer experiments at width 32–64, 2 layers, block size 32–64, batch size 1–2 and 100–300 steps.
- Neural training is CPU/RAM-intensive and may heat/throttle a phone. Stop if the device overheats.
- PyTorch wheels may not be available for every Android Debian architecture/Python version. The SQLite memory and n-gram features do not require PyTorch.
- Leave several GB of free storage for the Gemma artifact, cache and exported data.

## Online and offline behavior

TXT/Markdown/JSON import and SQLite retrieval can work locally. Public webpage import needs internet and is user-initiated. It does not continuously crawl sites or automatically train model weights. Review licensing and quality before using imported data as a training corpus.

The SmolLM3/Hugging Face Transformers backend has been removed. The Gemma LiteRT-LM artifact is a separate inference backend. The requested Model B fine-tuning, evaluation and conversion pipeline is still pending.
