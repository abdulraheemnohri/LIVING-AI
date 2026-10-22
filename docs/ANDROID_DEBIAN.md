# Android Debian/Linux terminal

This targets a Debian userspace terminal environment on Android, not a Termux-specific setup.

- Python 3.11+ is required.
- The installer creates a local virtual environment and does not require root.
- Start with localhost binding.
- If the terminal and browser cannot reach the same localhost, use the environment's port-forwarding/networking feature.
- Keep corpora small; Android RAM, thermal headroom, and storage are limited.

## Optional SmolLM3 local inference

The normal install intentionally does not install PyTorch or Transformers. To attempt the 3B base model, run:

```bash
source .venv/bin/activate
python -m pip install -e '.[hf]'
export LIVING_AI_MODEL_BACKEND=transformers
export LIVING_AI_HF_MODEL_ID=HuggingFaceTB/SmolLM3-3B-Base
export LIVING_AI_HF_DEVICE=cpu
bash scripts/run.sh
```

Check available RAM and free storage first. A 3B model in FP32 can require around 12 GB for parameters alone, and additional runtime memory is needed. Installation may also be blocked by missing PyTorch wheels for the current Python/CPU architecture. See [SMOLLM3.md](SMOLLM3.md) for details and fallback options.
