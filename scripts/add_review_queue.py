"""One-time setup: add a Review_Queue tab (PRD FR-012 -- sorted by score descending).

Uses a live QUERY formula referencing the Lead tab, so it always reflects the current
state of the Lead tab without a separate write path to keep in sync. Safe to re-run.

Usage:
    python scripts/add_review_queue.py
"""
import os
import sys
from pathlib import Path

# scripts/ isn't on sys.path by default, so add src/ manually before importing sheets_io.
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import gspread
from dotenv import load_dotenv

import sheets_io

load_dotenv()  # reads .env into os.environ

CREDENTIALS_FILE = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "config/credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")

# Look up Status and Lead_Score's 1-indexed column positions from sheets_io's single
# source of truth (LEAD_COLUMNS), instead of hardcoding "column 27" / "column 21" and
# risking drift if the schema ever changes.
STATUS_COL_INDEX = sheets_io.LEAD_COLUMNS.index("Status") + 1
SCORE_COL_INDEX = sheets_io.LEAD_COLUMNS.index("Lead_Score") + 1

# Builds a Sheets QUERY formula string, e.g.:
#   =QUERY(Lead!A1:AH, "select * where Col27 = 'Ready_For_Review' order by Col21 desc", 1)
# rowcol_to_a1(1, N) converts column N to its letter (e.g. 34 -> "AH1"); [:-1] strips
# the trailing row number "1" to leave just the column letter.
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
        # Re-running just refreshes the formula in place -- doesn't create a duplicate tab.
        ws = spreadsheet.worksheet("Review_Queue")
        print("Review_Queue tab already exists -- refreshing its formula.")
    else:
        ws = spreadsheet.add_worksheet(title="Review_Queue", rows=1000, cols=len(sheets_io.LEAD_COLUMNS))
        print("Created Review_Queue tab.")

    # raw=False tells Sheets to interpret the string as a formula (because it starts
    # with "="), not to store it as literal text.
    ws.update(range_name="A1", values=[[QUERY_FORMULA]], raw=False)
    print(f"Wrote QUERY formula: {QUERY_FORMULA}")
    print("Review_Queue now shows every Ready_For_Review lead, sorted by Lead_Score descending (FR-012).")


if __name__ == "__main__":
    main()
