#!/usr/bin/env bash
set -Eeuo pipefail

# Train both LIVING-AI model families from the same local corpus.
# Safe for Android Debian: the lightweight n-gram model is always attempted first.
# Transformer training is optional and skipped cleanly if PyTorch is unavailable.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -d data/corpus ]]; then
  echo "ERROR: data/corpus was not found."
  echo "Create it and put your saved UTF-8 .txt/.md training files inside:"
  echo "  mkdir -p data/corpus"
  exit 2
fi

if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

mkdir -p models logs

echo "[1/2] Training lightweight Character n-gram model..."
python -m living_ai.train --input data/corpus --output models/char_ngram.json
echo "Character n-gram model saved to models/char_ngram.json"

echo
echo "[2/2] Checking optional PyTorch support..."
if python -c 'import torch' >/dev/null 2>&1; then
  echo "PyTorch detected. Starting a small Android-friendly Transformer run."
  echo "You can stop this with Ctrl+C; the trained n-gram model remains saved."
  python -m living_ai.train_neural \
    --input data/corpus \
    --output models/tiny_transformer \
    --steps "${LIVING_AI_TRAIN_STEPS:-300}" \
    --batch-size "${LIVING_AI_BATCH_SIZE:-2}" \
    --width "${LIVING_AI_WIDTH:-64}" \
    --heads "${LIVING_AI_HEADS:-4}" \
    --layers "${LIVING_AI_LAYERS:-2}" \
    --block-size "${LIVING_AI_BLOCK_SIZE:-64}" \
    2>&1 | tee "logs/transformer-training.log"
  echo "Transformer training finished. Check models/tiny_transformer and logs/transformer-training.log."
else
  echo "PyTorch is not installed or cannot import on this Android Debian architecture."
  echo "Skipping Transformer training; the n-gram model is ready."
  echo "If you want to try the optional dependency, run:"
  echo "  python -m pip install -e '.[neural]'"
  echo "Then rerun: bash scripts/train_hybrid_android.sh"
fi

echo
echo "Training pass complete."
echo "Note: training both models does not automatically blend their generated text."
echo "The app's selected backend still controls inference; test each backend separately."
