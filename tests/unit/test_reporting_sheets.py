from scrapers.config import Settings
from scrapers.errors import ExportError
from scrapers.reporting import sheets


def test_sheets_requires_config(tmp_path):
    s = Settings(output_dir=str(tmp_path))
    try:
        sheets.export_to_sheets(s, [])
    except ExportError as exc:
        assert "SHEETS_SERVICE_ACCOUNT" in str(exc)
    else:
        raise AssertionError("expected ExportError")