"""Atomic, crash-safe file IO and run manifest helpers."""
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def new_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_dir(path) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def atomic_write_text(path, text: str) -> None:
    p = Path(path)
    ensure_dir(p.parent)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix=".tmp-", suffix=".partial")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def atomic_write_json(path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def load_json(path, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def write_manifest(output_dir, run_id: str, manifest: dict) -> Path:
    path = Path(output_dir) / "runs" / run_id / "manifest.json"
    atomic_write_json(path, manifest)
    return path