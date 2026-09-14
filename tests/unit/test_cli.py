import os
from pathlib import Path

from scrapers.cli import main
from scrapers.io import load_json


def test_list_sources_ok(capsys):
    assert main(["list-sources"]) == 0
    out = capsys.readouterr().out
    assert "amazon" in out and "deodap" in out


def test_validate_config_ok():
    assert main(["validate-config"]) == 0


def test_validate_config_bad_env():
    os.environ["LOG_LEVEL"] = "shouty"
    try:
        assert main(["validate-config"]) == 2
    finally:
        del os.environ["LOG_LEVEL"]


def test_run_mock_e2e(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = str(tmp_path / "data")
    code = main(["--output-dir", out, "run", "--mock",
                 "--sources", "amazon,meesho,flipkart,deodap"])
    assert code == 0
    assert load_json(os.path.join(out, "amazon_movers_raw.json"))
    assert load_json(os.path.join(out, "deodap_catalog_raw.json"))
    assert os.path.exists(os.path.join(out, "matched_products.json"))
    assert os.path.exists(os.path.join(out, "winners.md"))
    runs = list((Path(out) / "runs").iterdir())
    assert len(runs) == 1
    manifest = load_json(runs[0] / "manifest.json")
    assert manifest["mode"] == "mock"
    assert manifest["settings"].get("webhook_secret") in (None, "***")


def test_run_unknown_source_exit2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--output-dir", str(tmp_path / "d"), "run", "--mock", "--sources", "nope"]) == 2


def test_run_live_without_scrapling_exit4(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["--output-dir", str(tmp_path / "d"), "run", "--live", "--sources", "amazon"]) == 4