"""Typed exceptions and classification for the pipeline."""


class PipelineError(Exception):
    """Base class for all pipeline errors."""


class ConfigError(PipelineError, ValueError):
    """Invalid configuration supplied."""


class DependencyError(PipelineError):
    """A required optional dependency is missing (e.g. scrapling for live mode)."""


class SourceError(PipelineError):
    """A single marketplace source failed; carries the source name."""

    def __init__(self, source: str, message: str) -> None:
        super().__init__(f"[{source}] {message}")
        self.source = source
        self.message = message


class BlockedDetected(SourceError):
    """A source appears to be blocking or bot-walling us."""


class ParseError(SourceError):
    """Failed to parse a product page."""


class ExportError(PipelineError):
    """Failed to write or export results."""