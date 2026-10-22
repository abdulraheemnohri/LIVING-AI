#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -f .venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python - <<'PY'
try:
    import torch
    print("PyTorch:", torch.__version__)
except ImportError:
    raise SystemExit("PyTorch is missing. Try: python -m pip install -e '.[neural]' (if a compatible Android/Debian wheel exists).")
PY
mkdir -p data/corpus models/tiny_transformer
if ! find data/corpus -type f \( -iname '*.txt' -o -iname '*.md' \) -size -5M -print -quit | grep -q .; then
  echo "Add UTF-8 .txt/.md training files (each <= 5 MB) to data/corpus first."
  exit 2
fi
STEPS="${STEPS:-300}"
BATCH_SIZE="${BATCH_SIZE:-2}"
WIDTH="${WIDTH:-64}"
BLOCK_SIZE="${BLOCK_SIZE:-64}"
LAYERS="${LAYERS:-2}"
python -m living_ai.train_neural \
  --input data/corpus --output models/tiny_transformer \
  --steps "$STEPS" --batch-size "$BATCH_SIZE" \
  --width "$WIDTH" --heads 4 --layers "$LAYERS" --block-size "$BLOCK_SIZE"
echo "Done. Set LIVING_AI_MODEL_BACKEND=tiny_transformer in .env and restart the server."
