import pytest

import sheets_io


def test_lead_columns_match_schema_column_count():
    # docs/sheets_schema.md Tab 1 has 34 columns
    assert len(sheets_io.LEAD_COLUMNS) == 34


def test_evidence_columns_match_schema_column_count():
    assert len(sheets_io.EVIDENCE_COLUMNS) == 6


def test_lead_to_row_preserves_column_order():
    lead = {"Lead_ID": "L-000001", "Lead_Name": "Ozark Family Dental", "City": "Bentonville"}
    row = sheets_io._lead_to_row(lead)

    assert len(row) == len(sheets_io.LEAD_COLUMNS)
    assert row[sheets_io.LEAD_COLUMNS.index("Lead_ID")] == "L-000001"
    assert row[sheets_io.LEAD_COLUMNS.index("Lead_Name")] == "Ozark Family Dental"
    assert row[sheets_io.LEAD_COLUMNS.index("City")] == "Bentonville"


def test_lead_to_row_fills_missing_or_none_fields_with_empty_string():
    row = sheets_io._lead_to_row({"Lead_ID": "L-000001", "Notes": None})

    assert row[sheets_io.LEAD_COLUMNS.index("Notes")] == ""
    assert row[sheets_io.LEAD_COLUMNS.index("Phone")] == ""  # never set at all


def test_evidence_to_row_preserves_column_order():
    evidence = {"Evidence_ID": "E-000001", "Lead_ID": "L-000001", "Raw_Snippet": "test"}
    row = sheets_io._evidence_to_row(evidence)

    assert len(row) == len(sheets_io.EVIDENCE_COLUMNS)
    assert row[sheets_io.EVIDENCE_COLUMNS.index("Evidence_ID")] == "E-000001"
    assert row[sheets_io.EVIDENCE_COLUMNS.index("Raw_Snippet")] == "test"


def test_get_env_config_raises_when_missing(monkeypatch):
    monkeypatch.delenv("GOOGLE_PLACES_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_SHEETS_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("GOOGLE_SHEETS_SPREADSHEET_ID", raising=False)

    with pytest.raises(SystemExit):
        sheets_io.get_env_config()


def test_get_env_config_returns_values_when_present(monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_SHEETS_CREDENTIALS_JSON", "config/credentials.json")
    monkeypatch.setenv("GOOGLE_SHEETS_SPREADSHEET_ID", "sheet-id")

    config = sheets_io.get_env_config()

    assert config["GOOGLE_PLACES_API_KEY"] == "key"
    assert config["GOOGLE_SHEETS_SPREADSHEET_ID"] == "sheet-id"
