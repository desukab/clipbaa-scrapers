import json
from unittest import mock

from scrapers.errors import ExportError
from scrapers.reporting import webhook


def test_sign_payload():
    sig = webhook.sign_payload(b"body", "secret")
    assert sig.startswith("sha256=")
    assert len(sig) == len("sha256=") + 64


def test_build_payload_limits_winners():
    payload = webhook.build_payload({"winners": 30}, [{"i": n} for n in range(50)])
    assert len(payload["winners"]) == 25


def test_post_webhook_sends_signed_request():
    class FakeResp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    with mock.patch("urllib.request.urlopen", return_value=FakeResp()) as mocked:
        code = webhook.post_webhook("https://hook.example/x", "secret", {"a": 1})
    req = mocked.call_args[0][0]
    assert code == 200
    assert req.get_header("Content-Type") == "application/json"
    assert req.get_header("X-Pipeline-Signature").startswith("sha256=")
    assert json.loads(req.data) == {"a": 1}


def test_post_webhook_raises_on_failure():
    with mock.patch("urllib.request.urlopen", side_effect=ConnectionError("down")):
        try:
            webhook.post_webhook("https://hook.example/x", "s", {})
        except ExportError:
            pass
        else:
            raise AssertionError("expected ExportError")