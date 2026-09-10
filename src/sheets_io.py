"""Google Sheets read/write layer -- the only module in this pilot that touches the
live datastore (PRD §15 physical architecture, §16 component list).

Column order here must match docs/sheets_schema.md exactly, since rows are written
positionally (gspread append_row takes a plain list).
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import gspread

LEAD_COLUMNS = [
    "Lead_ID", "Discovered_Date", "Signal_ID", "Signal_Date", "Lead_Name", "Company",
    "Contact_Name", "Address", "City", "State", "ZIP", "Phone", "Email", "Website",
    "Property_Type", "Business_Type", "Lead_Source", "Source_URL", "Source_Evidence",
    "Recommended_Service", "Lead_Score", "Score_Breakdown", "Lead_Category",
    "AI_Confidence", "AI_Model_Used", "Prompt_Version", "Status", "Last_Contacted",
    "Next_Action", "Estimated_Value", "Notes", "Rejection_Reason", "Created_At",
    "Updated_At",
]

EVIDENCE_COLUMNS = [
    "Evidence_ID", "Lead_ID", "Source_ID", "Source_URL", "Retrieved_At", "Raw_Snippet",
]


def get_client(credentials_filename: str, authorized_user_filename: str) -> gspread.Client:
    return gspread.oauth(
        credentials_filename=credentials_filename,
        authorized_user_filename=authorized_user_filename,
    )


def get_spreadsheet(client: gspread.Client, spreadsheet_id: str) -> gspread.Spreadsheet:
    return client.open_by_key(spreadsheet_id)


def read_leads(spreadsheet: gspread.Spreadsheet) -> list[dict[str, Any]]:
    return spreadsheet.worksheet("Lead").get_all_records()


def read_evidence(spreadsheet: gspread.Spreadsheet) -> list[dict[str, Any]]:
    return spreadsheet.worksheet("Evidence_Log").get_all_records()


def _lead_to_row(lead: dict[str, Any]) -> list[Any]:
    return [lead.get(col, "") if lead.get(col) is not None else "" for col in LEAD_COLUMNS]


def _evidence_to_row(evidence: dict[str, Any]) -> list[Any]:
    return [evidence.get(col, "") if evidence.get(col) is not None else "" for col in EVIDENCE_COLUMNS]


def append_leads(spreadsheet: gspread.Spreadsheet, leads: list[dict[str, Any]]) -> None:
    if not leads:
        return
    rows = [_lead_to_row(lead) for lead in leads]
    spreadsheet.worksheet("Lead").append_rows(rows, value_input_option="USER_ENTERED")


def append_evidence(spreadsheet: gspread.Spreadsheet, evidence_rows: list[dict[str, Any]]) -> None:
    if not evidence_rows:
        return
    rows = [_evidence_to_row(e) for e in evidence_rows]
    spreadsheet.worksheet("Evidence_Log").append_rows(rows, value_input_option="USER_ENTERED")


def touch_source_config(spreadsheet: gspread.Spreadsheet, source_id: str, now: datetime) -> None:
    """Updates Last_Run_At / Last_Success_At for one Source_Config row (FR-018/§16)."""
    ws = spreadsheet.worksheet("Source_Config")
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):  # row 1 is the header
        if row.get("Source_ID") == source_id:
            ws.update(range_name=f"C{i}:D{i}", values=[[now.isoformat(), now.isoformat()]])
            return


def get_env_config() -> dict[str, str]:
    required = ["GOOGLE_PLACES_API_KEY", "GOOGLE_SHEETS_CREDENTIALS_JSON", "GOOGLE_SHEETS_SPREADSHEET_ID"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise SystemExit(f"Missing required .env values: {', '.join(missing)}")
    return {key: os.environ[key] for key in required}
