"""Per-source counters and run summaries."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class SourceMetrics:
    name: str
    status: str = "ok"
    requested: int = 0
    scraped: int = 0
    enriched: int = 0
    blocked: int = 0
    retried: int = 0
    failed: int = 0
    elapsed_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "requested": self.requested,
            "scraped": self.scraped,
            "enriched": self.enriched,
            "blocked": self.blocked,
            "retried": self.retried,
            "failed": self.failed,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass
class RunMetrics:
    mode: str = "mock"
    started_at: str = ""
    finished_at: str = ""
    sources: List[SourceMetrics] = field(default_factory=list)

    def for_source(self, name: str) -> SourceMetrics:
        for existing in self.sources:
            if existing.name == name:
                return existing
        metric = SourceMetrics(name=name)
        self.sources.append(metric)
        return metric

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "sources": [s.to_dict() for s in self.sources],
        }

    def exit_code(self) -> int:
        if not self.sources:
            return 0
        statuses = [s.status for s in self.sources]
        healthy = {"ok", "mock"}
        if all(st in healthy for st in statuses):
            return 0
        if any(st in {"failed", "blocked"} for st in statuses):
            if all(st in {"failed", "blocked"} for st in statuses):
                return 3
            return 1
        return 1