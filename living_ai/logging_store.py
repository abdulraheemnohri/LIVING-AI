"""Persistent local application logging for LIVING AI.

Logs are stored beneath LIVING_AI_DATA_DIR/logs and rotated to bound disk usage.
Never write passwords, API keys, chat bodies, or imported document contents to logs.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Lock

_lock = Lock()
_handler = None
_configured_path = None

def log_path() -> Path:
    root = Path(os.getenv("LIVING_AI_DATA_DIR", "./data")).expanduser()
    return root / "logs" / "living-ai.log"

def configure_logging(level: str | None = None) -> Path:
    global _handler, _configured_path
    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    chosen = (level or os.getenv("LIVING_AI_LOG_LEVEL", "INFO")).upper()
    if chosen not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        chosen = "INFO"
    with _lock:
        root = logging.getLogger("living_ai")
        root.setLevel(getattr(logging, chosen))
        root.propagate = False
        if _handler is None or _configured_path != str(path):
            if _handler is not None:
                root.removeHandler(_handler)
                try:
                    _handler.close()
                except OSError:
                    pass
            _handler = RotatingFileHandler(path, maxBytes=2_000_000, backupCount=5, encoding="utf-8")
            _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            root.addHandler(_handler)
            _configured_path = str(path)
        else:
            _handler.setLevel(logging.NOTSET)
    return path

def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger("living_ai." + name)

def read_logs(limit: int = 300, level: str = "") -> list[str]:
    path = configure_logging()
    if not path.exists():
        return []
    lines = []
    # Include rotated files from oldest to newest so the tail is chronological.
    for index in range(5, 0, -1):
        rotated = path.with_name(path.name + f".{index}")
        if rotated.exists():
            try:
                lines.extend(rotated.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
    try:
        lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        pass
    level = level.upper().strip()
    if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        lines = [line for line in lines if (" " + level + " ") in line]
    return lines[-max(1, min(int(limit), 2000)):]

def clear_logs() -> dict:
    path = configure_logging()
    with _lock:
        if path.exists():
            path.write_text("", encoding="utf-8")
        for index in range(1, 6):
            rotated = path.with_name(path.name + f".{index}")
            if rotated.exists():
                rotated.unlink()
    get_logger("audit").warning("Log files cleared by administrator")
    return {"cleared": True, "path": str(path)}

def current_level() -> str:
    return logging.getLevelName(logging.getLogger("living_ai").level)

def read_all_logs() -> list[str]:
    """Read all available current and rotated log lines for an explicit export."""
    path = configure_logging()
    lines = []
    for index in range(5, 0, -1):
        rotated = path.with_name(path.name + f".{index}")
        if rotated.exists():
            try:
                lines.extend(rotated.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
    try:
        lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        pass
    return lines
