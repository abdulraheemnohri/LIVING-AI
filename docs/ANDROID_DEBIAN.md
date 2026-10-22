# Android Debian/Linux and Pixel-class devices

LIVING AI targets a Debian userspace terminal on Android, including the Google Android Linux terminal environment. These steps are not Termux-specific. Python 3.11+ is required by project metadata.

## Setup

```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open `http://127.0.0.1:8000` in a browser reachable from the Linux environment.

## Model B: Gemma 4 E2B teacher model

Model B is `litert-community/gemma-4-E2B-it-litert-lm`, expected artifact `gemma-4-E2B-it.litertlm`, approximately 2.6 GB. [Official model card](https://huggingface.co/litert-community/gemma-4-E2B-it-litert-lm).

Install the optional runtime:

```bash
source .venv/bin/activate
python -m pip install -e '.[litert]'
mkdir -p models/litert
```

Download the model artifact separately into `models/litert/`, or configure `LIVING_AI_LITERTLM_MODEL_PATH` to the actual file. The app does not auto-download a multi-gigabyte model.

Model B is an inference-only teacher/coach in this design. It may help prepare data and candidate examples for Model A, but it does not train itself. A 6 GB phone may face memory pressure; start with CPU mode and measure real usage.

## Model A training sources

The intended training UI should support several selectable sources:

1. Upload a dataset/file manually.
2. Select files from a configured corpus directory.
3. Select and export reviewed local memories.
4. Select reviewed content from explicit public-web imports.
5. Ask Model B to normalize, classify, label, deduplicate, explain or propose synthetic training examples.
6. Convert evaluation failures into candidate examples for user review.

Training should start only after preview and explicit confirmation. Keep source/provenance metadata, show duplicate and malformed records, label Model B-generated content, and let the user exclude examples.

**Current limitation:** the existing n-gram trainer can train Model A from supported corpus files, but the complete multi-source teacher-assisted training UI/pipeline is not yet implemented. Importing memory or a webpage does not itself train a model. The optional tiny Transformer trainer is separate and does not fine-tune Gemma.

## Resource guidance

- Start tiny Transformer experiments at width 32–64, 2 layers, block size 32–64, batch size 1–2 and 100–300 steps.
- Training can consume CPU/RAM and heat the phone; stop if the device overheats.
- PyTorch support varies by Android Debian architecture/Python version.
- Keep several GB free for Model B, cache and datasets.
- Use training limits, versioned checkpoints, evaluation and rollback before replacing Model A's active checkpoint.

## Online/offline

Local file import and SQLite memory can work offline. Model B inference works offline only after the model artifact and runtime are installed. Public webpage import and model downloads require internet. Remote inference is a separate opt-in feature and sends prompts to the configured provider.
