import pytest
from living_ai.neural_lm import (
    VOCAB_SIZE, decode_tokens, encode_text, validate_config, default_config
)


def test_utf8_round_trip_english_and_urdu():
    text = "Living AI — سلام دنیا"
    assert decode_tokens(encode_text(text)) == text


def test_special_tokens_are_not_decoded():
    assert decode_tokens([1, 2, 3, 4, 5]) == "\x00\x01\x02"


def test_config_validation():
    config = validate_config(default_config())
    assert config["vocab_size"] == VOCAB_SIZE
    with pytest.raises(ValueError):
        validate_config({**config, "d_model": 127})
    with pytest.raises(ValueError):
        validate_config({**config, "block_size": 4})


def test_format_rejected():
    config = default_config()
    config["format_version"] = 999
    with pytest.raises(ValueError):
        validate_config(config)
