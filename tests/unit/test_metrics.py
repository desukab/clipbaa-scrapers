from scrapers.metrics import RunMetrics, SourceMetrics


def test_source_metrics_to_dict():
    sm = SourceMetrics(name="amazon", scraped=5, elapsed_ms=12)
    d = sm.to_dict()
    assert d["name"] == "amazon"
    assert d["scraped"] == 5
    assert d["elapsed_ms"] == 12
    assert d["status"] == "ok"


def test_run_metrics_tracks_sources():
    rm = RunMetrics(mode="live", started_at="t0")
    a = rm.for_source("amazon")
    a.scraped = 10
    b = rm.for_source("meesho")
    b.status = "mock-fallback"
    assert len(rm.sources) == 2
    d = rm.to_dict()
    assert d["mode"] == "live"
    assert d["sources"][0]["name"] == "amazon"


def test_exit_codes():
    ok = RunMetrics(sources=[SourceMetrics(name="a"), SourceMetrics(name="b")])
    assert ok.exit_code() == 0
    fall = RunMetrics(sources=[SourceMetrics(name="a", status="mock-fallback")])
    assert fall.exit_code() == 1
    failed = RunMetrics(sources=[SourceMetrics(name="a", status="failed"), SourceMetrics(name="b", status="ok")])
    assert failed.exit_code() == 1
    af = RunMetrics(sources=[SourceMetrics(name="a", status="failed"), SourceMetrics(name="b", status="blocked")])
    assert af.exit_code() == 3