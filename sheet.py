"""Google Sheet: read what was saved before, add new jobs, sort. Never edits the Status column."""

import json

import gspread
from gspread.utils import rowcol_to_a1

from filters import job_key
from settings import PROJECT_DIR, env

HEADERS = [
    "Date found", "Company", "Job title", "Location", "Remote/Onsite", "Source",
    "Direct apply link", "Score", "Apply/Skip", "Matching skills", "Missing skills",
    "Cover letter", "Keywords to add", "Status",
]
COL_DATE, COL_COMPANY, COL_TITLE, COL_LINK, COL_SCORE = 1, 2, 3, 7, 8


def connect(config):
    """Open the worksheet (create it with headers the first time)."""
    sheet_id = env("GOOGLE_SHEET_ID")
    if not sheet_id:
        raise SystemExit("GOOGLE_SHEET_ID is missing. Add it to .env (or GitHub Secrets).")

    json_text = env("GOOGLE_SERVICE_ACCOUNT_JSON")       # GitHub: whole JSON in a secret
    if json_text:
        client = gspread.service_account_from_dict(json.loads(json_text))
    else:                                                # Your PC: path to the JSON file
        path = PROJECT_DIR / env("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
        if not path.exists():
            raise SystemExit(f"Service account file not found: {path}")
        client = gspread.service_account(filename=str(path))

    book = client.open_by_key(sheet_id)
    name = config.get("worksheet_name", "Jobs")
    try:
        ws = book.worksheet(name)
    except gspread.WorksheetNotFound:
        ws = book.add_worksheet(title=name, rows=1000, cols=len(HEADERS))

    if not ws.row_values(1):  # empty sheet -> write the header row
        ws.update([HEADERS], "A1")
        ws.freeze(rows=1)
        ws.format("A1:N1", {"textFormat": {"bold": True}})
    return ws


def already_saved(ws):
    """Keys and links of every job saved in earlier runs (to skip duplicates)."""
    keys, links = set(), set()
    for row in ws.get_all_values()[1:]:
        row += [""] * (len(HEADERS) - len(row))
        keys.add(job_key(row[COL_COMPANY - 1], row[COL_TITLE - 1]))
        if row[COL_LINK - 1]:
            links.add(row[COL_LINK - 1])
    return keys, links


def add_rows(ws, rows):
    """Append new rows at the bottom, then sort: newest date first, then highest score.
    Sorting moves whole rows, so your Status values always stay with their job."""
    if not rows:
        return
    # RAW = save text exactly as is (a cover letter starting with "=" is not a formula)
    ws.append_rows(rows, value_input_option="RAW", table_range="A1")
    last_row = len(ws.col_values(COL_DATE))
    if last_row > 2:
        last_cell = rowcol_to_a1(last_row, max(ws.col_count, len(HEADERS)))
        ws.sort((COL_DATE, "des"), (COL_SCORE, "des"), range=f"A2:{last_cell}")
