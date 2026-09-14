"""Optional webhook summary push (HMAC-signed)."""
import hashlib
import hmac
import json
import urllib.request
from urllib.request import Request

from scrapers.errors import ExportError


def sign_payload(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_payload(summary: dict, top_winners: list) -> dict:
    return {"summary": summary, "winners": top_winners[:25]}


def post_webhook(url: str, secret: str, payload: dict) -> int:
    body = json.dumps(payload).encode("utf-8")
    request = Request(url, data=body, method="POST")
    request.headers["Content-Type"] = "application/json"
    request.headers["X-Pipeline-Signature"] = sign_payload(body, secret)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status
    except Exception as exc:
        raise ExportError(f"webhook POST to {url} failed: {exc}") from exc