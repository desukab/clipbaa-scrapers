"""Optional Google Sheets export of the winners list."""
from scrapers.errors import ExportError


def export_to_sheets(settings, winners_rows: list) -> None:
    if not (settings.sheets_service_account and settings.sheets_spreadsheet_id):
        raise ExportError("sheets export requires SHEETS_SERVICE_ACCOUNT and SHEETS_SPREADSHEET_ID")
    try:
        import gspread
    except ImportError as exc:
        raise ExportError("Google Sheets export requires: pip install -e '.[sheets]'") from exc
    try:
        gc = gspread.service_account(filename=settings.sheets_service_account)
        sheet = gc.open_by_key(settings.sheets_spreadsheet_id).sheet1
        sheet.clear()
        if winners_rows:
            header = list(winners_rows[0].keys())
            sheet.update([header] + [[r.get(c, "") for c in header] for r in winners_rows])
    except Exception as exc:
        raise ExportError(f"google sheets export failed: {exc}") from exc