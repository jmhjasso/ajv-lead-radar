"""One-time setup: add a Review_Queue tab (PRD FR-012 -- sorted by score descending).

Uses a live QUERY formula referencing the Lead tab, so it always reflects the current
state of the Lead tab without a separate write path to keep in sync. Safe to re-run.

Usage:
    python scripts/add_review_queue.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import gspread
from dotenv import load_dotenv

import sheets_io

load_dotenv()

CREDENTIALS_FILE = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "config/credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")

# Status column is #27, Lead_Score is #21 in sheets_io.LEAD_COLUMNS (docs/sheets_schema.md).
STATUS_COL_INDEX = sheets_io.LEAD_COLUMNS.index("Status") + 1
SCORE_COL_INDEX = sheets_io.LEAD_COLUMNS.index("Lead_Score") + 1

QUERY_FORMULA = (
    f"=QUERY(Lead!A1:{gspread.utils.rowcol_to_a1(1, len(sheets_io.LEAD_COLUMNS))[:-1]}, "
    f'"select * where Col{STATUS_COL_INDEX} = \'Ready_For_Review\' '
    f'order by Col{SCORE_COL_INDEX} desc", 1)'
)


def main() -> None:
    if not SPREADSHEET_ID:
        sys.exit("GOOGLE_SHEETS_SPREADSHEET_ID is not set in .env")

    client = sheets_io.get_client(CREDENTIALS_FILE, "config/authorized_user.json")
    spreadsheet = sheets_io.get_spreadsheet(client, SPREADSHEET_ID)

    existing_titles = {ws.title for ws in spreadsheet.worksheets()}
    if "Review_Queue" in existing_titles:
        ws = spreadsheet.worksheet("Review_Queue")
        print("Review_Queue tab already exists -- refreshing its formula.")
    else:
        ws = spreadsheet.add_worksheet(title="Review_Queue", rows=1000, cols=len(sheets_io.LEAD_COLUMNS))
        print("Created Review_Queue tab.")

    ws.update(range_name="A1", values=[[QUERY_FORMULA]], raw=False)
    print(f"Wrote QUERY formula: {QUERY_FORMULA}")
    print("Review_Queue now shows every Ready_For_Review lead, sorted by Lead_Score descending (FR-012).")


if __name__ == "__main__":
    main()
