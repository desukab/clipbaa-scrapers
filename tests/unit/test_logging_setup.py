import io
import json
import logging

from scrapers.logging_setup import add_file_handler, fmt_fn, redact_url, setup_logging


def test_redact_url_strips_credentials():
    assert redact_url("http://user:pass@host:8080") == "http://host:8080"
    assert redact_url("http://host:8080") == "http://host:8080"
    assert redact_url(None) == ""


def _capture(fmt):
    logger = logging.getLogger(f"capture-{fmt}")
    logger.handlers.clear()
    logger.propagate = False
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(fmt_fn[fmt])
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info("hello %s", "world", extra={"fields": {"source": "amazon"}})
    return stream.getvalue()


def test_console_format():
    out = _capture("console")
    assert "hello world" in out


def test_json_format():
    out = _capture("json")
    record = json.loads(out)
    assert record["message"] == "hello world"
    assert record["level"] == "INFO"
    assert record["source"] == "amazon"


def test_add_file_handler(tmp_path):
    root = logging.getLogger()
    old_level = root.level
    root.setLevel(logging.INFO)
    try:
        logfile = tmp_path / "run.log"
        add_file_handler(str(logfile))
        logging.getLogger("file-adder").info("written")
        assert "written" in logfile.read_text()
    finally:
        root.setLevel(old_level)
        root.handlers = [h for h in root.handlers
                         if not isinstance(h, logging.FileHandler)
                         or getattr(h, "baseFilename", None) != str(logfile)]