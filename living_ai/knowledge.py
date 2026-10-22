"""Local knowledge ingestion for TXT, Markdown, JSON, and explicitly requested web pages."""
from __future__ import annotations

import ipaddress
import json
import socket
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

MAX_FILE_BYTES = 2_000_000
MAX_URL_BYTES = 1_000_000
MAX_CHUNK_CHARS = 4000
ALLOWED_EXTENSIONS = {".txt", ".md", ".json"}


def _normalise_text(value: str) -> str:
    return value.replace("\x00", "").strip()


def _json_to_text(raw: str) -> str:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg} at line {exc.lineno}") from exc
    # Pretty-print JSON so structure and keys remain understandable to retrieval.
    return json.dumps(obj, ensure_ascii=False, indent=2)


def parse_document(filename: str, content: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Supported files are .txt, .md and .json")
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("File exceeds 2 MB limit")
    text = _json_to_text(content) if suffix == ".json" else content
    text = _normalise_text(text)
    if not text:
        raise ValueError("File is empty")
    return text


def split_text(text: str, chunk_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    if chunk_chars < 100:
        raise ValueError("chunk_chars must be at least 100")
    text = _normalise_text(text)
    chunks = []
    while text:
        if len(text) <= chunk_chars:
            piece, text = text, ""
        else:
            boundary = text.rfind("\n", 0, chunk_chars)
            if boundary < chunk_chars // 2:
                boundary = text.rfind(" ", 0, chunk_chars)
            if boundary < chunk_chars // 2:
                boundary = chunk_chars
            piece, text = text[:boundary], text[boundary:].lstrip()
        if piece.strip():
            chunks.append(piece.strip())
    return chunks


def _assert_public_http_url(url: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only absolute http:// or https:// URLs are supported")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing usernames/passwords are not allowed")
    host = parsed.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("Local hostnames are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ValueError(f"Could not resolve website hostname: {exc}") from exc
    if not addresses:
        raise ValueError("Website hostname did not resolve")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if not ip.is_global:
            raise ValueError("Private, loopback, link-local and non-public IP addresses are blocked")
    return parsed


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, "Redirect blocked; open the destination URL directly after review", headers, fp)


class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "svg", "canvas"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self.skip_depth += 1
        elif tag.lower() in {"p", "br", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")
    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1
        elif tag.lower() in {"p", "div", "li", "h1", "h2", "h3", "h4", "tr"}:
            self.parts.append("\n")
    def handle_data(self, data):
        if not self.skip_depth:
            cleaned = data.strip()
            if cleaned:
                self.parts.append(cleaned + " ")
    def text(self):
        return _normalise_text(" ".join(self.parts))


def fetch_public_page(url: str, timeout: int = 12) -> tuple[str, str]:
    parsed = _assert_public_http_url(url)
    opener = urllib.request.build_opener(_NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "LIVING-AI-KnowledgeImporter/1.0", "Accept": "text/html,text/plain,application/json"})
    try:
        with opener.open(request, timeout=timeout) as response:
            final_url = response.geturl()
            _assert_public_http_url(final_url)
            content_type = response.headers.get_content_type().lower()
            if content_type not in {"text/html", "text/plain", "application/json", "text/markdown"}:
                raise ValueError(f"Unsupported website content type: {content_type}")
            raw = response.read(MAX_URL_BYTES + 1)
            if len(raw) > MAX_URL_BYTES:
                raise ValueError("Website response exceeds 1 MB limit")
            charset = response.headers.get_content_charset() or "utf-8"
            decoded = raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            raise ValueError("Website redirected. For safety, review and import the destination URL separately.") from exc
        raise ValueError(f"Website returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ValueError(f"Could not fetch website: {exc.reason}") from exc

    if content_type == "text/html":
        parser = _TextExtractor()
        parser.feed(decoded)
        text = parser.text()
    elif content_type == "application/json":
        text = _json_to_text(decoded)
    else:
        text = decoded.strip()
    if not text:
        raise ValueError("No readable text found on that page")
    return text, parsed.geturl()
