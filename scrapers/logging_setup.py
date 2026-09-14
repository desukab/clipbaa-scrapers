"""Structured logging (console or JSON) with secret redaction."""
import json
import logging
import sys
from typing import Optional
from urllib.parse import urlparse


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


fmt_fn = {
    "console": logging.Formatter("%(asctime)s %(levelname)-7s [%(name)s] %(message)s", "%H:%M:%S"),
    "json": _JsonFormatter(),
}

_INSTALLED = False


def setup_logging(level: str, fmt: str = "console") -> None:
    global _INSTALLED
    root = logging.getLogger()
    root.setLevel(level.upper())
    if not _INSTALLED:
        root.addHandler(logging.StreamHandler(sys.stdout))
        _INSTALLED = True
    for handler in root.handlers:
        handler.setFormatter(fmt_fn.get(fmt, fmt_fn["console"]))


def _has_json_formatter(handlers):
    for h in handlers:
        formatter = getattr(h, "getFormatter", lambda: None)()
        if formatter is not None and formatter.__class__.__name__ == "_JsonFormatter":
            return True
    return False


def add_file_handler(path: str) -> None:
    root = logging.getLogger()
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(fmt_fn["json"] if _has_json_formatter(root.handlers) else fmt_fn["console"])
    handler.setLevel(root.level)
    root.addHandler(handler)


def redact_url(url: Optional[str]) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return f"{parsed.scheme}://{netloc}"