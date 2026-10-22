from living_ai.hf_model import DEFAULT_MODEL_ID


def test_smollm3_default_model_id():
    assert DEFAULT_MODEL_ID == "HuggingFaceTB/SmolLM3-3B-Base"
