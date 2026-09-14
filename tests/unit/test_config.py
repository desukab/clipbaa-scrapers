import pytest

from scrapers.config import DEFAULT_AMAZON_BESTSELLERS_URLS, Settings, as_csv, parse_bool
from scrapers.errors import ConfigError

ENV = {
    "LOG_LEVEL": "debug",
    "LOG_FORMAT": "json",
    "SCRAPLING_ADAPTIVE": "1",
    "SCRAPLING_ADAPTIVE_PERCENTAGE": "60",
    "SCRAPLING_PROXY": "http://user:pass@host:8080",
    "AMAZON_BESTSELLERS_URLS": "https://a.in/x, https://a.in/y",
    "AMAZON_NODE_CATEGORIES": '{"1381": "storage"}',
    "MIN_CONFIDENCE": "0.65",
    "MIN_ABSOLUTE_MARGIN": "150",
    "DEODAP_MAX_PAGES": "5",
    "WEBHOOK_SECRET": "hunter2",
}


def test_from_env_parses():
    s = Settings.from_env(env=ENV)
    assert s.log_level == "DEBUG"
    assert s.log_format == "json"
    assert s.adaptive is True
    assert s.adaptive_percentage == 60
    assert s.proxy_url == "http://user:pass@host:8080"
    assert s.amazon_bestsellers_urls == ("https://a.in/x", "https://a.in/y")
    assert s.amazon_node_categories == {"1381": "storage"}
    assert s.min_confidence == 0.65
    assert s.min_absolute_margin == 150.0
    assert s.deodap_max_pages == 5


def test_from_env_defaults():
    s = Settings.from_env(env={})
    assert s.log_level == "INFO"
    assert s.deodap_max_pages == 3
    assert s.amazon_bestsellers_urls == DEFAULT_AMAZON_BESTSELLERS_URLS


def test_helpers():
    assert parse_bool("True") is True
    assert parse_bool("no") is False
    assert parse_bool(None) is False
    assert as_csv("a, b, c") == ("a", "b", "c")
    assert as_csv(None) == ()


def test_validation_fails_fast():
    with pytest.raises(ConfigError, match="LOG_LEVEL"):
        Settings.from_env(env={"LOG_LEVEL": "shouty"})
    with pytest.raises(ConfigError, match="SCRAPLING_ADAPTIVE_PERCENTAGE"):
        Settings.from_env(env={"SCRAPLING_ADAPTIVE_PERCENTAGE": "300"})
    with pytest.raises(ConfigError, match="MIN_CONFIDENCE"):
        Settings.from_env(env={"MIN_CONFIDENCE": "1.5"})
    with pytest.raises(ConfigError, match="SCRAPLING_PROXY"):
        Settings.from_env(env={"SCRAPLING_PROXY": "not a url"})


def test_to_dict_redacts_secrets():
    s = Settings.from_env(env={"WEBHOOK_SECRET": "hunter2", "SCRAPLING_PROXY": "http://user:pass@host:8080"})
    d = s.to_dict(redact=True)
    assert d["webhook_secret"] == "***"
    assert "pass" not in d["proxy_url"]