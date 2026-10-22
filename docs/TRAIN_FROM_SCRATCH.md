# Train LIVING AI's own small language model

LIVING AI now includes a tiny byte-level causal Transformer that starts with random weights and learns next-byte prediction from local text. It does not download a pretrained checkpoint. UTF-8 bytes let it represent Urdu and other Unicode scripts, but byte-level representation is inefficient and does not imply strong Urdu understanding.

## Install

From the repository root, inside the project's virtual environment:

```bash
python -m pip install -e '.[neural]'
mkdir -p data/corpus
# Put your own or otherwise lawfully usable UTF-8 .txt/.md files in data/corpus/
python -m living_ai.train_neural --input data/corpus --steps 500 --batch-size 4 --width 64 --heads 4 --layers 2 --block-size 64
```

The `neural` extra requires PyTorch. PyTorch wheel availability is architecture-specific; some Android Debian environments do not have a compatible wheel. Start with small settings (width 64, 2 layers, block 64) and 100–500 steps. More steps do not guarantee better output.

## Run it

Set the backend before starting the server:

```bash
export LIVING_AI_MODEL_BACKEND=tiny_transformer
export LIVING_AI_TINY_MODEL_DIR=models/tiny_transformer
bash scripts/run.sh
```

A trained checkpoint consists of `config.json` and `weights.pt`. Treat checkpoints as local trusted artifacts. The trainer saves a state dictionary and inference loads it with PyTorch's restricted `weights_only=True` mode.

## Dataset and quality

- Only UTF-8 `.txt`, `.md`, and `.json` files are ingested, each at most 2 MB.
- Use text you own, public-domain text, or text whose license permits training. JSON is validated and pretty-printed before training.
- The trainer does not crawl the internet, fetch YouTube, parse PDFs, or fine-tune any pretrained model. Public webpages must be explicitly imported through the dashboard. Use the Import Data page's corpus-export action to include saved memory in `data/corpus/` for training.
- A small randomly initialized model trained on a small corpus generally produces poor, repetitive, or incoherent text. It is an educational baseline, not a capable assistant.
- CPU training can be slow and warm the phone. Monitor device temperature and stop if the device throttles or becomes uncomfortably hot. Keep steps and dimensions low.
- Memory needs scale roughly with parameter count, batch size, sequence length, and optimizer state. There is no universal safe configuration for every Android device.

The lightweight character n-gram model remains available as the default. The SmolLM3/Hugging Face backend has been removed from this project.
