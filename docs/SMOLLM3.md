# SmolLM3-3B-Base integration

LIVING-AI supports optional local inference with the Hugging Face checkpoint
`HuggingFaceTB/SmolLM3-3B-Base`. Model card:
https://huggingface.co/HuggingFaceTB/SmolLM3-3B-Base

The checkpoint is Apache-2.0 licensed. It is the **base pretrained model**, not
the instruction-tuned `HuggingFaceTB/SmolLM3-3B` model. Base models continue text
and may not reliably follow chat instructions. This integration uses a simple
`User: ... Assistant:` continuation prompt.

## Install

First install the normal LIVING-AI dependencies. Then install the optional model
dependencies separately:

```bash
source .venv/bin/activate
python -m pip install -e '.[hf]'
```

For Android Debian, this may fail if a compatible PyTorch wheel is unavailable for
the exact Python/CPU architecture. In that case, keep the default lightweight
backend or configure an OpenAI-compatible inference endpoint. Do not assume CUDA
is available on Android.

## Configure

Edit `.env` or export these variables in the shell that starts LIVING-AI:

```bash
export LIVING_AI_MODEL_BACKEND=transformers
export LIVING_AI_HF_MODEL_ID=HuggingFaceTB/SmolLM3-3B-Base
export LIVING_AI_HF_DEVICE=cpu
export LIVING_AI_HF_DTYPE=auto
bash scripts/run.sh
```

The first run downloads the checkpoint and tokenizer from Hugging Face unless the
files are already cached. The model is several billion parameters; storage and RAM
requirements are substantial. FP32 weights alone can require roughly 12 GB just
for parameters, with additional memory needed for runtime and context. A typical
Android device may not have enough available RAM to load this checkpoint. Use a
quantized runtime/model or a remote endpoint if the device cannot load it.

To preload the model files without generating text, run:

```bash
python -c 'from transformers import AutoTokenizer, AutoModelForCausalLM; m="HuggingFaceTB/SmolLM3-3B-Base"; AutoTokenizer.from_pretrained(m); AutoModelForCausalLM.from_pretrained(m)'
```

## Notes

- The Transformers dependency is optional and does not affect the default install.
- The model is lazily loaded on the first chat request and kept in process memory.
- Set `LIVING_AI_HF_LOCAL_ONLY=true` to disable network downloads and use cached files only.
- Training/fine-tuning this 3B model is a separate workflow; this feature enables inference,
  not full pretraining. Use LoRA/QLoRA with a compatible training setup for fine-tuning.
