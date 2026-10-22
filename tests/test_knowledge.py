import json
import pytest
from living_ai.knowledge import parse_document, split_text, _assert_public_http_url

def test_txt_and_markdown_import():
    assert parse_document("notes.txt", "hello") == "hello"
    assert parse_document("guide.md", "# Hello\nWorld") == "# Hello\nWorld"

def test_json_is_pretty_printed_and_unicode_preserved():
    text = parse_document("facts.json", json.dumps({"city":"لاہور","n":3}, ensure_ascii=False))
    assert "لاہور" in text
    assert '"n": 3' in text

def test_invalid_json_and_extension_rejected():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_document("bad.json", "{")
    with pytest.raises(ValueError, match="Supported files"):
        parse_document("code.py", "print(1)")

def test_file_size_limit():
    with pytest.raises(ValueError, match="2 MB"):
        parse_document("large.txt", "x" * 2_000_001)

def test_chunks_are_bounded():
    chunks = split_text(("paragraph text " * 1000), chunk_chars=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)

def test_localhost_url_is_rejected():
    with pytest.raises(ValueError, match="Local hostnames"):
        _assert_public_http_url("http://localhost/admin")
