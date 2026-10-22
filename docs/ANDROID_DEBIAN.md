# Android Debian/Linux and Google Pixel 6

LIVING AI targets a Debian userspace terminal on Android (not a Termux-specific install). Python 3.11+ is required.

## Setup
```bash
git clone https://github.com/abdulraheemnohri/LIVING-AI.git
cd LIVING-AI
bash scripts/install_android_debian.sh
source .venv/bin/activate
bash scripts/run.sh
```

Open `http://127.0.0.1:8000` in a browser reachable from the Linux environment. If localhost is isolated, use the environment's supported port forwarding.

## Mobile workflow
- Dashboard → Import Data → choose local TXT, Markdown or JSON files.
- Or paste a public webpage URL to import readable text into local SQLite memory.
- Dashboard → Memory to search or delete imported chunks.
- Dashboard → Training to train the character n-gram model or a tiny from-scratch Transformer.
- For neural training, first check whether PyTorch supports the exact Debian architecture and Python version on this device.

## Pixel 6 resource guidance
Start with width 32–64, 2 layers, sequence block 32–64, batch size 1–2, and 100–300 training steps. Training is CPU/RAM-intensive; monitor heat and stop if the phone throttles. No guarantee is made that a compatible PyTorch wheel exists for every Android Debian setup. If PyTorch is unavailable, file import, SQLite memory and the lightweight n-gram model still work.

## Offline and online data
TXT, Markdown and JSON files are imported locally. Public webpage fetching requires internet access and is explicit, not continuous. The fetcher accepts text content types, caps a page at 1 MB, blocks non-public IP addresses and does not follow redirects. Sites requiring login or JavaScript are unsupported. Imported online text is saved as local memory; it does not automatically train model weights.

The SmolLM3/Hugging Face backend has been removed. LIVING AI uses its own from-scratch model for optional neural inference.
