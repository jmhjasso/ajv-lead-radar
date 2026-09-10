"""One-time setup: create the 4 tabs + header rows in the Lead datastore spreadsheet.

Schema source of truth: docs/sheets_schema.md (PRD §14/§14a). Run this once against a
blank spreadsheet; safe to re-run (it only creates missing tabs/headers, never deletes data).

Usage:
    python scripts/provision_sheet.py
"""
import os
import sys

import gspread
from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_FILE = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON", "config/credentials.json")
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEETS_SPREADSHEET_ID")
AUTHORIZED_USER_FILE = "config/authorized_user.json"

TABS = {
    "Lead": [
        "Lead_ID", "Discovered_Date", "Signal_ID", "Signal_Date", "Lead_Name", "Company",
        "Contact_Name", "Address", "City", "State", "ZIP", "Phone", "Email", "Website",
        "Property_Type", "Business_Type", "Lead_Source", "Source_URL", "Source_Evidence",
        "Recommended_Service", "Lead_Score", "Score_Breakdown", "Lead_Category",
        "AI_Confidence", "AI_Model_Used", "Prompt_Version", "Status", "Last_Contacted",
        "Next_Action", "Estimated_Value", "Notes", "Rejection_Reason", "Created_At",
        "Updated_At",
    ],
    "Source_Config": [
        "Source_ID", "Enabled", "Last_Run_At", "Last_Success_At", "Error_Count_7d",
        "Rate_Limit_Notes",
    ],
    "Evidence_Log": [
        "Evidence_ID", "Lead_ID", "Source_ID", "Source_URL", "Retrieved_At", "Raw_Snippet",
    ],
    "Status_History": [
        "History_ID", "Lead_ID", "From_Status", "To_Status", "Changed_By", "Changed_At",
        "Note",
    ],
}

# Pilot Slice: SRC-01 (Google Places) is the only enabled source (PRD §46a).
SOURCE_CONFIG_SEED_ROW = ["SRC-01", "TRUE", "", "", "0", ""]


def get_client() -> gspread.Client:
    return gspread.oauth(
        credentials_filename=CREDENTIALS_FILE,
        authorized_user_filename=AUTHORIZED_USER_FILE,
    )


def provision(spreadsheet: gspread.Spreadsheet) -> None:
    existing_titles = {ws.title for ws in spreadsheet.worksheets()}

    for tab_name, headers in TABS.items():
        if tab_name in existing_titles:
            ws = spreadsheet.worksheet(tab_name)
            print(f"Tab '{tab_name}' already exists — checking header row only.")
        else:
            ws = spreadsheet.add_worksheet(
                title=tab_name, rows=1000, cols=max(len(headers), 10)
            )
            print(f"Created tab '{tab_name}'.")

        current_header = ws.row_values(1)
        if current_header != headers:
            ws.update(range_name="A1", values=[headers])
            print(f"  Wrote {len(headers)} column headers to '{tab_name}'.")
        else:
            print(f"  Headers already correct on '{tab_name}'.")

    # Seed Source_Config with the SRC-01 row if it's empty (header-only).
    source_config_ws = spreadsheet.worksheet("Source_Config")
    if len(source_config_ws.get_all_values()) <= 1:
        source_config_ws.append_row(SOURCE_CONFIG_SEED_ROW)
        print("Seeded Source_Config with SRC-01 (Enabled=TRUE).")

    # Remove the default blank "Sheet1" if it's still there and untouched.
    default = next(
        (ws for ws in spreadsheet.worksheets() if ws.title == "Sheet1"), None
    )
    if default is not None and default.get_all_values() == []:
        spreadsheet.del_worksheet(default)
        print("Removed empty default 'Sheet1' tab.")


def main() -> None:
    if not SPREADSHEET_ID:
        sys.exit("GOOGLE_SHEETS_SPREADSHEET_ID is not set in .env")
    if not os.path.exists(CREDENTIALS_FILE):
        sys.exit(f"OAuth client file not found at {CREDENTIALS_FILE}")

    client = get_client()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    print(f"Opened spreadsheet: {spreadsheet.title}")
    provision(spreadsheet)
    print("Done.")


if __name__ == "__main__":
    main()
