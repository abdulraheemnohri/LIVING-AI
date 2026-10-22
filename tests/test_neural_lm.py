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


def test_collect_text_accepts_utf8_and_ignores_other_extensions(tmp_path):
    from living_ai.neural_training import collect_text
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "urdu.txt").write_text("سلام دنیا " * 10, encoding="utf-8")
    (corpus / "ignored.json").write_text("not training data", encoding="utf-8")
    text, count = collect_text(corpus)
    assert "سلام" in text
    assert count == 1


def test_collect_text_rejects_too_small_corpus(tmp_path):
    from living_ai.neural_training import collect_text
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "small.txt").write_text("tiny", encoding="utf-8")
    with pytest.raises(ValueError, match="too small"):
        collect_text(corpus)
