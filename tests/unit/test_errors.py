import pytest

from scrapers.errors import (
    BlockedDetected,
    ConfigError,
    DependencyError,
    ExportError,
    ParseError,
    PipelineError,
    SourceError,
)


def test_hierarchy():
    assert issubclass(ConfigError, PipelineError)
    assert issubclass(ConfigError, ValueError)
    assert issubclass(DependencyError, PipelineError)
    assert issubclass(BlockedDetected, SourceError)
    assert issubclass(ParseError, SourceError)
    assert issubclass(ExportError, PipelineError)


def test_source_error_carries_source():
    err = SourceError("amazon", "boom")
    assert err.source == "amazon"
    assert err.message == "boom"
    assert "amazon" in str(err)


def test_config_error_is_value_error():
    with pytest.raises(ValueError):
        raise ConfigError("bad config")